"""AUTOTESTE no banco REAL (XAMPP): confere todas as regras da Fase 3.

Precisa de: .env configurado, banco criado (schema.sql + seed_base.sql) e o
importador já executado (python tools/sync_market.py).

Rodar da raiz do projeto:
    python -m app.unit_tests.manual_gacha_flow

O que ele faz:
  1. cria um usuário temporário "autoteste_..." com saldo alto;
  2. testa compra de caixa, abertura (chave, float, conteúdo), venda,
     compra de skin avulsa, saldo insuficiente, caixa inexistente e
     inventário cheio (1000 itens);
  3. mostra a estatística de 10.000 sorteios simulados (sem gravar nada),
     comparando com as chances oficiais (bom para a apresentação);
  4. APAGA o usuário temporário e tudo dele no final (mesmo se algo falhar).
Termina com "TUDO CERTO" ou com a lista do que falhou.
"""
import random
import sys
import time
from collections import Counter
from decimal import Decimal

from app.controller.inventory_controller import Inventory_Controller
from app.controller.market_controller import Market_Controller
from app.core import game_rules as rules
from app.core.database import Database
from app.core.drop_service import draw_drop, drop_table
from app.core.password_utils import Password_Utils
from app.dao.collection_dao import Collection_DAO
from app.dao.inventory_dao import Inventory_DAO
from app.dao.rarity_dao import Rarity_DAO
from app.dao.skin_catalog_dao import Skin_Catalog_DAO
from app.dao.user_dao import User_DAO
from app.models.user import User

SALDO_TESTE = Decimal("100000.00")
resultados = []


def check(condicao, descricao):
    resultados.append((bool(condicao), descricao))
    print(f"  [{'OK' if condicao else 'FALHOU'}] {descricao}")
    return condicao


class ConsoleView:
    """Tela "de mentira" que só guarda e imprime as mensagens dos controllers."""

    def __init__(self):
        self.messages = []

    def show_message(self, message, success=True):
        self.messages.append((message, success))
        print(f"        mensagem: {message}")

    @property
    def last(self):
        return self.messages[-1] if self.messages else ("", True)


def sql(database, comando, params=(), many=False):
    """Executa SQL direto (só para PREPARAR cenários do teste)."""
    connection = database.connect()
    cursor = connection.cursor(buffered=True)
    try:
        if many:
            for p in params:
                cursor.execute(comando, p)
        else:
            cursor.execute(comando, params)
        rows = cursor.fetchall() if cursor.description else None
        connection.commit()
        return rows
    finally:
        database.disconnect(cursor, connection)


def saldo_no_banco(database, user_id):
    return rules.to_money(sql(database, "SELECT balance FROM users WHERE id = %s", (user_id,))[0][0])


def estatistica_de_drops(collection_dao, rarity_dao, caixa):
    print(f"\n== Estatística: 10.000 aberturas SIMULADAS de '{caixa.name}' (nada é gravado)")
    itens = collection_dao.get_items(caixa.id)
    probs = rarity_dao.get_probabilities()
    raridades = {r.id: r.name for r in rarity_dao.get_all()}
    tabela = drop_table(itens, probs)
    esperado = Counter()
    for skin, chance in tabela:
        esperado[skin.rarity_id] += chance
    rng = random.Random()
    n = 10_000
    sorteios = [draw_drop(itens, probs, rng) for _ in range(n)]
    obtido = Counter(skin.rarity_id for skin, _f, _w in sorteios)
    print(f"  {'Raridade':<16}{'esperado':>10}{'obtido':>10}")
    for rarity_id in sorted(esperado):
        print(f"  {raridades.get(rarity_id, rarity_id):<16}{float(esperado[rarity_id]) * 100:>9.2f}%"
              f"{obtido[rarity_id] / n * 100:>9.2f}%")
    desgastes = Counter(w for _s, _f, w in sorteios)
    print("  Desgaste: " + " | ".join(f"{rules.wear_label(w)} {c / n * 100:.1f}%"
                                      for w, c in desgastes.most_common()))


def main():
    try:
        sys.stdout.reconfigure(errors="replace")
    except (AttributeError, ValueError):
        pass

    database = Database()
    user_dao = User_DAO(database)
    inventory_dao = Inventory_DAO(database)
    collection_dao = Collection_DAO(database)
    skin_dao = Skin_Catalog_DAO(database)
    rarity_dao = Rarity_DAO(database)

    print("== Pré-requisitos")
    caixas = collection_dao.get_all()
    if not check(caixas, f"existem caixas com conteúdo no banco ({len(caixas)})"):
        print("\nRode antes: python tools/sync_market.py")
        return 1

    usuario = User(None, f"autoteste_{int(time.time())}", Password_Utils.to_hash("autoteste123"),
                   f"autoteste{int(time.time())}@teste.local", SALDO_TESTE)
    user_dao.save(usuario)
    usuario.password = None
    print(f"  usuário temporário criado: {usuario.username} (id {usuario.id})")

    try:
        view = ConsoleView()
        market = Market_Controller(collection_dao, skin_dao, inventory_dao, view, usuario)
        inventario = Inventory_Controller(inventory_dao, collection_dao, rarity_dao, view, usuario)
        caixa = min(caixas, key=lambda c: c.price)   # a mais barata
        print(f"  caixa usada nos testes: {caixa.name} ({rules.format_money(caixa.price)})")

        print("\n== Comprar caixa")
        check(market.check_purchase(caixa.price) is None, "checagem antes da compra libera")
        check(market.buy_case(caixa), "compra concluída")
        esperado = SALDO_TESTE - caixa.price
        check(usuario.balance == esperado == saldo_no_banco(database, usuario.id),
              f"saldo descontado na sessão e no banco ({rules.format_money(esperado)})")
        pilhas = inventory_dao.get_cases(usuario.id)
        check(len(pilhas) == 1 and pilhas[0].quantity == 1, "caixa apareceu no inventário")

        print("\n== Abrir caixa")
        resultado = inventario.open_case(caixa.id)
        if check(resultado is not None, "abertura concluída"):
            s = resultado.skin_instance
            print(f"        drop: {s.name} | {s.skin.rarity.name} | float {s.float_value} | "
                  f"{s.wear_label} | {rules.format_money(s.skin_price)}")
            check(s.skin.id in [i.id for i in collection_dao.get_items(caixa.id)], "item sorteado pertence à caixa")
            dentro = (not s.skin.has_wear and s.float_value == 0) or (s.skin.min_float <= s.float_value < s.skin.max_float)
            check(dentro, "float dentro do intervalo da skin")
            check(resultado.remaining_cases == 0 and not resultado.can_open_another, "caixa consumida (restam 0)")
            esperado -= rules.KEY_PRICE
            check(usuario.balance == esperado == saldo_no_banco(database, usuario.id),
                  f"chave cobrada ({rules.format_money(rules.KEY_PRICE)})")
            check(inventory_dao.get_cases(usuario.id) == [] and len(inventory_dao.get_skins(usuario.id)) == 1,
                  "inventário: 0 caixas, 1 skin")

            print("\n== Vender skin")
            preco, recebe = inventario.sale_quote(s.id)
            check(recebe == rules.sell_payout(preco), f"valor final mostrado antes ({rules.format_money(recebe)})")
            pago = inventario.sell_skin(s.id)
            esperado += recebe
            check(pago == recebe and usuario.balance == esperado == saldo_no_banco(database, usuario.id),
                  "saldo creditado (preço - taxa)")
            check(inventory_dao.get_skins(usuario.id) == [], "skin saiu do inventário")
            check(inventario.sell_skin(s.id) is None, "vender a mesma skin de novo é bloqueado")

        print("\n== Abrir caixa que o jogador não tem")
        antes = saldo_no_banco(database, usuario.id)
        check(inventario.open_case(caixa.id) is None and not view.last[1], "erro mostrado")
        check(saldo_no_banco(database, usuario.id) == antes, "saldo não mudou")

        print("\n== Comprar skin avulsa no mercado")
        anuncios, _paginas = market.list_skins()
        if check(anuncios, f"mercado de skins tem anúncios ({len(anuncios)} na 1ª página)"):
            skin, anuncio = min(anuncios, key=lambda a: a[1].price)
            nova = market.buy_skin(skin, anuncio)
            if check(nova is not None, f"comprou {skin.name} ({anuncio.wear_label})"):
                check(rules.wear_from_float(nova.float_value, skin.has_wear) == anuncio.wear,
                      "float gerado combina com o desgaste comprado")
                esperado -= anuncio.price
                check(usuario.balance == esperado == saldo_no_banco(database, usuario.id), "saldo descontado")

        print("\n== Saldo insuficiente")
        sql(database, "UPDATE users SET balance = %s WHERE id = %s", (Decimal("0.01"), usuario.id))
        usuario.balance = Decimal("0.01")
        itens_antes = inventory_dao.count_items(usuario.id)
        check(not market.can_afford(caixa.price), "preço apareceria em vermelho")
        check(market.buy_case(caixa) is False and view.last == ("Saldo insuficiente.", False), "compra negada")
        check(inventory_dao.count_items(usuario.id) == itens_antes, "inventário não mudou")
        sql(database, "INSERT INTO collections_instance (user_id, collection_id) VALUES (%s, %s)", (usuario.id, caixa.id))
        if rules.KEY_PRICE > 0:
            check(inventario.open_case(caixa.id) is None and "chave" in view.last[0], "sem saldo para a chave: não abre")
            check(len(inventory_dao.get_cases(usuario.id)) == 1, "caixa NÃO foi consumida")

        print("\n== Inventário cheio (1000 itens)")
        sql(database, "UPDATE users SET balance = %s WHERE id = %s", (SALDO_TESTE, usuario.id))
        usuario.balance = SALDO_TESTE
        faltam = rules.INVENTORY_LIMIT - inventory_dao.count_items(usuario.id)
        sql(database, "INSERT INTO collections_instance (user_id, collection_id) VALUES (%s, %s)",
            [(usuario.id, caixa.id)] * faltam, many=True)
        check(inventory_dao.count_items(usuario.id) == rules.INVENTORY_LIMIT, "inventário com 1000 itens")
        check(market.check_purchase(caixa.price) == "Inventário cheio!", "checagem avisa 'Inventário cheio!'")
        check(market.buy_case(caixa) is False and view.last == ("Inventário cheio!", False), "compra bloqueada")
        check(inventario.open_case(caixa.id) is not None, "abrir continua permitido (sai 1 caixa, entra 1 skin)")
        check(inventory_dao.count_items(usuario.id) == rules.INVENTORY_LIMIT, "continua com 1000 itens")

        estatistica_de_drops(collection_dao, rarity_dao, caixa)

    finally:
        user_dao.delete(usuario.id)   # ON DELETE CASCADE apaga caixas e skins dele
        print(f"\n  usuário temporário {usuario.username} apagado.")

    falhas = [d for ok, d in resultados if not ok]
    print("\n" + ("=" * 60))
    if falhas:
        print(f"FALHARAM {len(falhas)} de {len(resultados)} verificações:")
        for descricao in falhas:
            print(f"  - {descricao}")
        return 1
    print(f"TUDO CERTO: {len(resultados)} verificações passaram.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
