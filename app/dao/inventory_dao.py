import logging
from datetime import timedelta
from decimal import Decimal

from app.core.game_rules import (
    INVENTORY_LIMIT,
    KEY_PRICE,
    estimated_price,
    format_money,
    format_wait,
    free_case_wait,
    has_wear,
    sell_payout,
    to_money,
    wear_from_float,
)
from app.core.i18n import t
from app.dao.base_dao import Base_DAO
from app.dao.collection_dao import COLLECTION_COLUMNS, collection_from_row
from app.dao.skin_catalog_dao import SKIN_COLUMNS, skin_from_row
from app.models.player_stats import Player_Stats
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


# Tipos de movimentação gravados em user_transactions (migração 004).
# Cada compra, abertura e venda deixa uma linha: é daí que saem as estatísticas da Home.
KIND_BUY_CASE = "buy_case"        # compra de caixa(s) no mercado      (amount = total pago)
KIND_BUY_SKIN = "buy_skin"        # compra de skin(s) avulsa(s)        (amount = total pago)
KIND_OPEN_CASE = "open_case"      # abertura com chave                 (amount = preço da chave)
KIND_FREE_CASE = "free_case"      # abertura da caixa grátis           (amount = 0)
KIND_SELL_SKIN = "sell_skin"      # venda                              (amount = valor recebido)
KINDS_OPENING = (KIND_OPEN_CASE, KIND_FREE_CASE)
KINDS_SPENDING = (KIND_BUY_CASE, KIND_BUY_SKIN, KIND_OPEN_CASE)


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
            self._log(cursor, user_id, KIND_BUY_CASE, total, quantity)

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
            self._log(cursor, user_id, KIND_OPEN_CASE, KEY_PRICE, 1, skin_catalog_id, skin_price)

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
            self._log(cursor, user_id, KIND_BUY_SKIN, total, len(float_values), skin_catalog_id, price)

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
            # se era a skin em destaque da Home, a Home volta a mostrar a mais valiosa
            cursor.execute(
                "UPDATE users SET featured_skin_id = NULL WHERE id = %s AND featured_skin_id = %s",
                (user_id, skin_instance_id)
            )
            new_balance = balance + payout
            self._set_balance(cursor, user_id, new_balance)
            self._log(cursor, user_id, KIND_SELL_SKIN, payout, 1, instance.skin_catalog_id, price)

            connection.commit()
            return payout, new_balance

        except Exception:
            self._rollback(connection)
            raise

        finally:
            self.disconnect(cursor, connection)

    def open_free_case(self, user_id, skin_catalog_id, float_value, now):
        """Abre a CAIXA GRÁTIS: sem chave e sem caixa no inventário.

        O sorteio já foi feito (Inventory_Controller, com a tabela da caixa
        grátis). Aqui, dentro da transação, conferimos a regra de novo:
        1. o saldo NÃO paga a chave e já passaram 10 min desde a última;
        2. há espaço no inventário;
        3. o float é válido para a skin.
        now: hora atual (o controller passa datetime.now()).
        Devolve (id da nova skin, preço da skin, saldo).
        """
        connection, cursor = self.connect(buffered=True)

        try:
            cursor.execute("SELECT balance, last_free_case_at FROM users WHERE id = %s FOR UPDATE", (user_id,))
            data = cursor.fetchone()
            if data is None:
                raise ValueError(t("Usuário não encontrado."))
            balance = to_money(data[0])

            espera = free_case_wait(balance, data[1], now)
            if espera is None:
                raise ValueError(t("A caixa grátis é só para quem não tem saldo para a chave ({preco}).",
                                   preco=format_money(KEY_PRICE)))
            if espera > timedelta(0):
                raise ValueError(t("A próxima caixa grátis libera em {tempo}.", tempo=format_wait(espera)))

            self._check_space(cursor, user_id, entering=1, leaving=0)

            cursor.execute(
                f"""
                SELECT {SKIN_COLUMNS}
                FROM skins_catalog s
                JOIN rarities r ON r.id = s.rarity_id
                WHERE s.id = %s
                """,
                (skin_catalog_id,)
            )
            data = cursor.fetchone()
            if data is None:
                raise ValueError(t("O item sorteado não pertence a esta caixa."))
            skin = skin_from_row(data)
            float_value = Decimal(str(float_value))
            self._check_float(skin, float_value)
            skin_price = self._market_price(cursor, skin, wear_from_float(float_value, skin.has_wear))

            cursor.execute(
                """
                INSERT INTO skins_instance (skin_price, float_value, user_id, skin_catalog_id)
                VALUES (%s, %s, %s, %s)
                """,
                (skin_price, float_value, user_id, skin_catalog_id)
            )
            new_skin_id = cursor.lastrowid
            cursor.execute("UPDATE users SET last_free_case_at = %s WHERE id = %s", (now, user_id))
            self._log(cursor, user_id, KIND_FREE_CASE, Decimal("0.00"), 1, skin_catalog_id, skin_price)

            connection.commit()
            return new_skin_id, skin_price, balance

        except Exception:
            self._rollback(connection)
            raise

        finally:
            self.disconnect(cursor, connection)

    # ==========================================================
    # HOME: skin em destaque e estatísticas
    # ==========================================================

    def get_free_case_state(self, user_id):
        """(saldo, hora da última caixa grátis ou None): o controller aplica a regra."""
        connection, cursor = self.connect()

        try:
            cursor.execute("SELECT balance, last_free_case_at FROM users WHERE id = %s", (user_id,))
            data = cursor.fetchone()
            if data is None:
                raise ValueError(t("Usuário não encontrado."))
            return to_money(data[0]), data[1]

        finally:
            self.disconnect(cursor, connection)

    def set_featured_skin(self, user_id, skin_instance_id):
        """Escolhe a skin em destaque na Home (None = volta para a mais valiosa)."""
        connection, cursor = self.connect(buffered=True)

        try:
            if skin_instance_id is not None:
                self._find_owned_skin(cursor, user_id, skin_instance_id, lock=False)   # é mesmo do jogador?
            cursor.execute("UPDATE users SET featured_skin_id = %s WHERE id = %s", (skin_instance_id, user_id))
            connection.commit()

        except Exception:
            self._rollback(connection)
            raise

        finally:
            self.disconnect(cursor, connection)

    def get_featured_skin_id(self, user_id):
        """Id da skin escolhida para a Home (None = nenhuma escolhida)."""
        connection, cursor = self.connect()

        try:
            cursor.execute("SELECT featured_skin_id FROM users WHERE id = %s", (user_id,))
            data = cursor.fetchone()
            return data[0] if data else None

        finally:
            self.disconnect(cursor, connection)

    def get_featured_skin(self, user_id):
        """Skin do pedestal da Home: (Skin_Instance ou None, foi escolhida pelo jogador?).
        Sem escolha (ou se ela foi vendida), mostra a skin mais valiosa do inventário."""
        connection, cursor = self.connect(buffered=True)

        try:
            cursor.execute(
                f"""
                SELECT {INSTANCE_COLUMNS}
                FROM users u
                JOIN skins_instance i ON i.id = u.featured_skin_id AND i.user_id = u.id
                JOIN skins_catalog s ON s.id = i.skin_catalog_id
                JOIN rarities r ON r.id = s.rarity_id
                WHERE u.id = %s
                """,
                (user_id,)
            )
            data = cursor.fetchone()
            if data is not None:
                return instance_from_row(data), True

            cursor.execute(
                f"""
                SELECT {INSTANCE_COLUMNS}
                {INSTANCE_FROM}
                WHERE i.user_id = %s
                ORDER BY i.skin_price DESC, i.id DESC
                LIMIT 1
                """,
                (user_id,)
            )
            data = cursor.fetchone()
            return (instance_from_row(data) if data else None), False

        finally:
            self.disconnect(cursor, connection)

    def get_stats(self, user_id):
        """Estatísticas da Home (Player_Stats), somadas da tabela user_transactions."""
        connection, cursor = self.connect(buffered=True)

        try:
            abertura = ", ".join(["%s"] * len(KINDS_OPENING))
            gasto = ", ".join(["%s"] * len(KINDS_SPENDING))
            cursor.execute(
                f"""
                SELECT
                    COALESCE(SUM(CASE WHEN kind IN ({abertura}) THEN quantity ELSE 0 END), 0),
                    COALESCE(SUM(CASE WHEN kind = %s THEN quantity ELSE 0 END), 0),
                    COALESCE(SUM(CASE WHEN kind IN ({gasto}) THEN amount ELSE 0 END), 0),
                    COALESCE(SUM(CASE WHEN kind = %s THEN amount ELSE 0 END), 0)
                FROM user_transactions
                WHERE user_id = %s
                """,
                (*KINDS_OPENING, KIND_FREE_CASE, *KINDS_SPENDING, KIND_SELL_SKIN, user_id)
            )
            abertas, gratis, gastou, recebeu = cursor.fetchone()

            # melhor item que já saiu de caixa (mesmo que já tenha sido vendido)
            cursor.execute(
                f"""
                SELECT {SKIN_COLUMNS}, tr.item_value
                FROM user_transactions tr
                JOIN skins_catalog s ON s.id = tr.skin_catalog_id
                JOIN rarities r ON r.id = s.rarity_id
                WHERE tr.user_id = %s
                  AND tr.kind IN ({abertura})
                ORDER BY tr.item_value DESC, tr.id
                LIMIT 1
                """,
                (user_id, *KINDS_OPENING)
            )
            melhor = cursor.fetchone()

            cursor.execute(
                f"SELECT COALESCE(SUM(quantity), 0) FROM user_transactions WHERE kind IN ({abertura})",
                KINDS_OPENING
            )
            todos = cursor.fetchone()[0]

            return Player_Stats(
                cases_opened=int(abertas),
                free_cases_opened=int(gratis),
                spent=to_money(gastou),
                earned=to_money(recebeu),
                items=self._count_items(cursor, user_id),
                best_drop=skin_from_row(melhor) if melhor else None,
                best_drop_value=to_money(melhor[14]) if melhor else None,
                cases_opened_everyone=int(todos),
            )

        finally:
            self.disconnect(cursor, connection)

    # ==========================================================
    # AJUDANTES (sempre chamados com uma transação já aberta)
    # ==========================================================

    @staticmethod
    def _log(cursor, user_id, kind, amount, quantity=1, skin_catalog_id=None, item_value=None):
        """Registra a movimentação na mesma transação (se ela falhar, o registro some junto)."""
        cursor.execute(
            """
            INSERT INTO user_transactions (user_id, kind, quantity, amount, skin_catalog_id, item_value)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (user_id, kind, quantity, to_money(amount), skin_catalog_id,
             to_money(item_value) if item_value is not None else None)
        )

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
