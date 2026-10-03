import logging
from decimal import Decimal

from app.core.game_rules import (
    INVENTORY_LIMIT,
    KEY_PRICE,
    estimated_price,
    format_money,
    has_wear,
    sell_payout,
    to_money,
    wear_from_float,
)
from app.core.i18n import t
from app.dao.base_dao import Base_DAO
from app.dao.collection_dao import COLLECTION_COLUMNS, collection_from_row
from app.dao.skin_catalog_dao import SKIN_COLUMNS, skin_from_row
from app.models.skin_instance import Skin_Instance

logger = logging.getLogger(__name__)

# Colunas de uma skin do jogador + a ficha da skin (SKIN_COLUMNS começa na posição 6).
INSTANCE_COLUMNS = f"""
    i.id, i.user_id, i.skin_catalog_id, i.float_value, i.skin_price, i.acquired_at,
    {SKIN_COLUMNS}
"""
INSTANCE_FROM = """
    FROM skins_instance i
    JOIN skins_catalog s ON s.id = i.skin_catalog_id
    JOIN rarities r ON r.id = s.rarity_id
"""


def instance_from_row(row):
    return Skin_Instance(row[0], row[1], row[2], row[3], row[4], row[5], skin_from_row(row, 6))


class Inventory_DAO(Base_DAO):
    """Tudo que mexe no INVENTÁRIO e no SALDO do jogador.

    As operações de compra, abertura e venda alteram várias tabelas ao mesmo
    tempo (users + collections_instance + skins_instance). Por isso cada uma
    roda em UMA transação: se qualquer passo falhar, o rollback desfaz tudo e
    nada fica pela metade (ex.: caixa consumida sem a skin entrar).

    Ordem de bloqueio usada em todas as transações (evita travamentos):
    primeiro a linha do usuário (SELECT ... FOR UPDATE), depois o item.

    Erros de regra (saldo insuficiente, inventário cheio...) são lançados como
    ValueError com a mensagem pronta para o jogador, igual ao User_DAO.
    """

    def __init__(self, database):
        super().__init__(database)

    # ==========================================================
    # LEITURA
    # ==========================================================

    def count_items(self, user_id):
        """Quantos itens o jogador tem (caixas + skins)."""
        connection, cursor = self.connect(buffered=True)

        try:
            return self._count_items(cursor, user_id)

        finally:
            self.disconnect(cursor, connection)

    def get_cases(self, user_id):
        """Caixas do jogador AGRUPADAS por tipo: lista de Collection com .quantity."""
        connection, cursor = self.connect()

        try:
            sql = f"""
                    SELECT {COLLECTION_COLUMNS}, COUNT(ci.id)
                    FROM collections_instance ci
                    JOIN collections c ON c.id = ci.collection_id
                    WHERE ci.user_id = %s
                    GROUP BY {COLLECTION_COLUMNS}
                    ORDER BY c.name
                  """

            cursor.execute(sql, (user_id,))

            return [collection_from_row(data, quantity=int(data[8])) for data in cursor.fetchall()]

        finally:
            self.disconnect(cursor, connection)

    def get_skins(self, user_id):
        """Skins do jogador, das mais novas para as mais antigas (como no CS)."""
        connection, cursor = self.connect()

        try:
            sql = f"""
                    SELECT {INSTANCE_COLUMNS}
                    {INSTANCE_FROM}
                    WHERE i.user_id = %s
                    ORDER BY i.acquired_at DESC, i.id DESC
                  """

            cursor.execute(sql, (user_id,))

            return [instance_from_row(data) for data in cursor.fetchall()]

        finally:
            self.disconnect(cursor, connection)

    def get_skin(self, user_id, skin_instance_id):
        """Uma skin do jogador (None se não existir ou for de outra pessoa)."""
        connection, cursor = self.connect()

        try:
            sql = f"""
                    SELECT {INSTANCE_COLUMNS}
                    {INSTANCE_FROM}
                    WHERE i.id = %s
                      AND i.user_id = %s
                  """

            cursor.execute(sql, (skin_instance_id, user_id))

            data = cursor.fetchone()

            return instance_from_row(data) if data else None

        finally:
            self.disconnect(cursor, connection)

    def get_sale_quote(self, user_id, skin_instance_id):
        """Valor de venda ANTES de confirmar: devolve (preço de mercado, valor que o jogador recebe)."""
        connection, cursor = self.connect(buffered=True)

        try:
            instance = self._find_owned_skin(cursor, user_id, skin_instance_id, lock=False)
            price = self._market_price(cursor, instance.skin, instance.wear)
            return price, sell_payout(price)

        finally:
            self.disconnect(cursor, connection)

    # ==========================================================
    # TRANSAÇÕES (dinheiro + itens)
    # ==========================================================

    def buy_case(self, user_id, collection_id, expected_price=None, quantity=1):
        """Compra caixa(s) no mercado (quantity unidades, tudo ou nada). Devolve o novo saldo.

        expected_price: preço que o jogador viu ao confirmar. Se o importador
        mudou o preço nesse meio tempo, a compra é recusada (ele confirma de novo).
        """
        quantity = int(quantity)
        if quantity < 1:
            raise ValueError(t("Quantidade inválida."))
        connection, cursor = self.connect(buffered=True)

        try:
            balance = self._lock_balance(cursor, user_id)

            cursor.execute(
                """
                SELECT c.price_collection,
                       (SELECT COUNT(*) FROM collection_items ci WHERE ci.collection_id = c.id)
                FROM collections c
                WHERE c.id = %s
                """,
                (collection_id,)
            )
            data = cursor.fetchone()
            if data is None:
                raise ValueError(t("Caixa não encontrada no mercado."))
            if int(data[1]) == 0:
                raise ValueError(t("Esta caixa está indisponível (sem conteúdo cadastrado)."))

            price = to_money(data[0])
            self._check_expected_price(price, expected_price)

            total = price * quantity
            if balance < total:
                raise ValueError(t("Saldo insuficiente."))
            self._check_space(cursor, user_id, entering=quantity, leaving=0)

            new_balance = balance - total
            self._set_balance(cursor, user_id, new_balance)
            cursor.executemany(
                "INSERT INTO collections_instance (user_id, collection_id) VALUES (%s, %s)",
                [(user_id, collection_id)] * quantity
            )

            connection.commit()
            return new_balance

        except Exception:
            self._rollback(connection)
            raise

        finally:
            self.disconnect(cursor, connection)

    def open_case(self, user_id, collection_id, skin_catalog_id, float_value):
        """Abre 1 caixa: consome a caixa, cobra a chave e salva a skin sorteada.

        O SORTEIO já foi feito antes (drop_service). Aqui só validamos e salvamos:
        1. a caixa existe no inventário do jogador;
        2. há espaço (a caixa sai -1 e a skin entra +1);
        3. há saldo para a chave (KEY_PRICE);
        4. a skin sorteada pertence mesmo a essa caixa e o float é válido.
        Se qualquer validação falhar, nada é salvo e a caixa NÃO é consumida.

        Devolve (id da nova skin, preço da skin, novo saldo, caixas iguais restantes).
        """
        connection, cursor = self.connect(buffered=True)

        try:
            balance = self._lock_balance(cursor, user_id)

            # 1. caixa no inventário (pega a mais antiga daquele tipo)
            cursor.execute(
                """
                SELECT id
                FROM collections_instance
                WHERE user_id = %s
                  AND collection_id = %s
                ORDER BY id
                LIMIT 1
                FOR UPDATE
                """,
                (user_id, collection_id)
            )
            data = cursor.fetchone()
            if data is None:
                raise ValueError(t("Você não tem essa caixa no inventário."))
            case_instance_id = data[0]

            # 2. espaço: sai 1 caixa e entra 1 skin
            self._check_space(cursor, user_id, entering=1, leaving=1)

            # 3. chave
            if balance < KEY_PRICE:
                raise ValueError(t("Saldo insuficiente para a chave ({preco}).", preco=format_money(KEY_PRICE)))

            # 4. a skin sorteada é mesmo dessa caixa?
            cursor.execute(
                f"""
                SELECT {SKIN_COLUMNS}
                FROM collection_items ci
                JOIN skins_catalog s ON s.id = ci.skin_catalog_id
                JOIN rarities r ON r.id = s.rarity_id
                WHERE ci.collection_id = %s
                  AND ci.skin_catalog_id = %s
                """,
                (collection_id, skin_catalog_id)
            )
            data = cursor.fetchone()
            if data is None:
                raise ValueError(t("O item sorteado não pertence a esta caixa."))
            skin = skin_from_row(data)
            float_value = Decimal(str(float_value))
            self._check_float(skin, float_value)

            wear = wear_from_float(float_value, skin.has_wear)
            skin_price = self._market_price(cursor, skin, wear)

            # tudo validado: consome a caixa, cobra a chave e entrega a skin
            cursor.execute("DELETE FROM collections_instance WHERE id = %s", (case_instance_id,))
            new_balance = balance - KEY_PRICE
            self._set_balance(cursor, user_id, new_balance)
            cursor.execute(
                """
                INSERT INTO skins_instance (skin_price, float_value, user_id, skin_catalog_id)
                VALUES (%s, %s, %s, %s)
                """,
                (skin_price, float_value, user_id, skin_catalog_id)
            )
            new_skin_id = cursor.lastrowid

            cursor.execute(
                "SELECT COUNT(*) FROM collections_instance WHERE user_id = %s AND collection_id = %s",
                (user_id, collection_id)
            )
            remaining = int(cursor.fetchone()[0])

            connection.commit()
            return new_skin_id, skin_price, new_balance, remaining

        except Exception:
            self._rollback(connection)
            raise

        finally:
            self.disconnect(cursor, connection)

    def buy_skin(self, user_id, skin_catalog_id, wear, float_value, expected_price=None):
        """Compra UMA skin avulsa no mercado. Devolve (id da nova skin, preço pago, novo saldo)."""
        ids, price, new_balance = self.buy_skins(user_id, skin_catalog_id, wear, [float_value], expected_price)
        return ids[0], price, new_balance

    def buy_skins(self, user_id, skin_catalog_id, wear, float_values, expected_price=None):
        """Compra várias unidades da mesma skin/desgaste (uma por float), tudo ou nada.
        Devolve (lista de ids das novas skins, preço unitário, novo saldo)."""
        float_values = [Decimal(str(valor)) for valor in float_values]
        if not float_values:
            raise ValueError(t("Quantidade inválida."))
        connection, cursor = self.connect(buffered=True)

        try:
            balance = self._lock_balance(cursor, user_id)

            cursor.execute(
                f"""
                SELECT {SKIN_COLUMNS}, p.price
                FROM skin_prices p
                JOIN skins_catalog s ON s.id = p.skin_catalog_id
                JOIN rarities r ON r.id = s.rarity_id
                WHERE p.skin_catalog_id = %s
                  AND p.wear = %s
                """,
                (skin_catalog_id, wear)
            )
            data = cursor.fetchone()
            if data is None:
                raise ValueError(t("Esse item não está à venda no mercado."))
            skin = skin_from_row(data)
            price = to_money(data[14])

            for float_value in float_values:
                self._check_float(skin, float_value)
                if wear_from_float(float_value, skin.has_wear) != wear:
                    raise ValueError(t("O float gerado não corresponde ao desgaste escolhido."))

            self._check_expected_price(price, expected_price)
            total = price * len(float_values)
            if balance < total:
                raise ValueError(t("Saldo insuficiente."))
            self._check_space(cursor, user_id, entering=len(float_values), leaving=0)

            new_balance = balance - total
            self._set_balance(cursor, user_id, new_balance)
            new_ids = []
            for float_value in float_values:
                cursor.execute(
                    """
                    INSERT INTO skins_instance (skin_price, float_value, user_id, skin_catalog_id)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (price, float_value, user_id, skin_catalog_id)
                )
                new_ids.append(cursor.lastrowid)

            connection.commit()
            return new_ids, price, new_balance

        except Exception:
            self._rollback(connection)
            raise

        finally:
            self.disconnect(cursor, connection)

    def sell_skin(self, user_id, skin_instance_id):
        """Vende uma skin pelo preço ATUAL do mercado, menos a taxa (SELL_FEE_RATE).
        Devolve (valor recebido, novo saldo)."""
        connection, cursor = self.connect(buffered=True)

        try:
            balance = self._lock_balance(cursor, user_id)

            # confirma que o item existe e é do jogador (e trava a linha)
            instance = self._find_owned_skin(cursor, user_id, skin_instance_id, lock=True)
            if not instance.skin.market_name:
                raise ValueError(t("Este item não pode ser vendido."))

            price = self._market_price(cursor, instance.skin, instance.wear)
            payout = sell_payout(price)

            cursor.execute("DELETE FROM skins_instance WHERE id = %s", (skin_instance_id,))
            new_balance = balance + payout
            self._set_balance(cursor, user_id, new_balance)

            connection.commit()
            return payout, new_balance

        except Exception:
            self._rollback(connection)
            raise

        finally:
            self.disconnect(cursor, connection)

    # ==========================================================
    # AJUDANTES (sempre chamados com uma transação já aberta)
    # ==========================================================

    def _lock_balance(self, cursor, user_id):
        """Lê o saldo e TRAVA a linha do usuário até o commit/rollback.
        Assim duas operações ao mesmo tempo não usam o mesmo dinheiro duas vezes."""
        cursor.execute("SELECT balance FROM users WHERE id = %s FOR UPDATE", (user_id,))
        data = cursor.fetchone()
        if data is None:
            raise ValueError(t("Usuário não encontrado."))
        return to_money(data[0])

    def _set_balance(self, cursor, user_id, new_balance):
        if new_balance < 0:
            # Proteção extra: a regra já foi checada antes e o banco tem CHECK.
            raise ValueError(t("Saldo insuficiente."))
        cursor.execute("UPDATE users SET balance = %s WHERE id = %s", (to_money(new_balance), user_id))

    def _count_items(self, cursor, user_id):
        cursor.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM collections_instance WHERE user_id = %s)
              + (SELECT COUNT(*) FROM skins_instance WHERE user_id = %s)
            """,
            (user_id, user_id)
        )
        return int(cursor.fetchone()[0])

    def _check_space(self, cursor, user_id, entering, leaving):
        """Regra do inventário: total depois da operação não pode passar do limite."""
        total_depois = self._count_items(cursor, user_id) - leaving + entering
        if total_depois > INVENTORY_LIMIT:
            raise ValueError(t("Inventário cheio!"))

    def _find_owned_skin(self, cursor, user_id, skin_instance_id, lock):
        sql = f"""
                SELECT {INSTANCE_COLUMNS}
                {INSTANCE_FROM}
                WHERE i.id = %s
                  AND i.user_id = %s
              """
        if lock:
            sql += " FOR UPDATE"
        cursor.execute(sql, (skin_instance_id, user_id))
        data = cursor.fetchone()
        if data is None:
            raise ValueError(t("Item não encontrado no seu inventário."))
        return instance_from_row(data)

    def _market_price(self, cursor, skin, wear):
        """Preço atual da skin naquele desgaste; se não houver, usa o preço estimado."""
        cursor.execute(
            "SELECT price FROM skin_prices WHERE skin_catalog_id = %s AND wear = %s",
            (skin.id, wear)
        )
        data = cursor.fetchone()
        if data is not None:
            return to_money(data[0])
        rarity_name = skin.rarity.name if skin.rarity else None
        return estimated_price(rarity_name, wear)

    @staticmethod
    def _check_float(skin, float_value):
        """Defesa: o float tem de estar dentro do intervalo da skin."""
        if not has_wear(skin.min_float, skin.max_float):
            if float_value != 0:
                raise ValueError(t("Este item não tem desgaste (float deve ser 0)."))
            return
        if not (skin.min_float <= float_value < skin.max_float):
            raise ValueError(t("Float fora do intervalo permitido para esta skin."))

    @staticmethod
    def _check_expected_price(price, expected_price):
        if expected_price is not None and to_money(expected_price) != price:
            raise ValueError(t("O preço mudou para {preco}. Confira e tente de novo.", preco=format_money(price)))

    @staticmethod
    def _rollback(connection):
        """Desfaz a transação. Se a própria conexão caiu, só registra no log
        (o erro original continua sendo lançado)."""
        try:
            connection.rollback()
        except Exception:
            logger.exception("Falha ao executar rollback")
