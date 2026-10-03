"""Testes dos controllers do MERCADO e do INVENTÁRIO, com DAOs "de mentira".

Aqui conferimos a lógica dos controllers (mensagens, saldo da sessão,
sorteio enviado ao DAO). As transações em si são conferidas no banco real
pelo script app/unit_tests/manual_gacha_flow.py.

Rodar da raiz do projeto:
    python -m unittest app.unit_tests.test_gacha_controllers -v
"""
import random
import unittest
from datetime import datetime, timedelta
from decimal import Decimal

from app.controller.home_controller import Home_Controller
from app.controller.inventory_controller import Inventory_Controller
from app.controller.market_controller import Market_Controller
from app.core import game_rules as rules
from app.models.collection import Collection
from app.models.market_price import Market_Price
from app.models.rarity import Rarity
from app.models.skin_catalog import Skin_Catalog
from app.models.user import User

RARIDADES = {
    1: Rarity(1, "Mil-Spec Grade", "0.7992"),
    5: Rarity(5, "Special Item", "0.0026"),
}
SKINS = [
    Skin_Catalog(10, "P250 | Teste", "P250", 1, "0", "1", "s10", "P250 | Teste", rarity=RARIDADES[1]),
    Skin_Catalog(11, "★ Karambit", "Karambit", 5, "0", "0", "s11", "★ Karambit", rarity=RARIDADES[5]),
]


class FakeView:
    def __init__(self):
        self.messages = []

    def show_message(self, message, success=True):
        self.messages.append((message, success))

    @property
    def last(self):
        return self.messages[-1]


class FakeCollectionDAO:
    def get_all(self):
        return [Collection(1, "Caixa Teste", "10.00")]

    def get_items(self, collection_id):
        return SKINS if collection_id == 1 else []

    def get_price_history(self, collection_id, limit=30):
        return []


class FakeRarityDAO:
    def get_probabilities(self):
        return {r.id: r.probability for r in RARIDADES.values()}

    def get_all(self):
        return list(RARIDADES.values())


class FakeSkinCatalogDAO:
    def count_market_listings(self, search="", rarity_id=None):
        return 50

    def get_market_listings(self, search="", limit=24, offset=0, rarity_id=None):
        self.ultimo = (search, limit, offset)
        return []

    def get_history_for_listings(self, listings):
        agora = datetime(2026, 10, 5, 8, 0)
        historico = {par: [] for par in listings}
        historico[(10, "Field-Tested")] = [(agora - timedelta(hours=24), Decimal("2.00")),
                                           (agora, Decimal("2.50"))]
        return historico


class FakeInventoryDAO:
    """Guarda os argumentos recebidos e devolve respostas prontas."""

    def __init__(self, itens=0, erro=None):
        self.itens = itens
        self.erro = erro
        self.chamadas = []

    def count_items(self, user_id):
        return self.itens

    def _talvez_erro(self):
        if self.erro:
            raise self.erro

    def buy_case(self, user_id, collection_id, expected_price=None, quantity=1):
        self.chamadas.append(("buy_case", collection_id, expected_price) + ((quantity,) if quantity != 1 else ()))
        self._talvez_erro()
        return Decimal("490.00")

    def buy_skins(self, user_id, skin_id, wear, float_values, expected_price=None):
        if len(float_values) == 1:
            self.chamadas.append(("buy_skin", skin_id, wear, float_values[0], expected_price))
        else:
            self.chamadas.append(("buy_skins", skin_id, wear, list(float_values), expected_price))
        self._talvez_erro()
        return list(range(99, 99 + len(float_values))), expected_price, Decimal("400.00")

    def open_case(self, user_id, collection_id, skin_id, float_value):
        self.chamadas.append(("open_case", collection_id, skin_id, float_value))
        self._talvez_erro()
        return 77, Decimal("3.20"), Decimal("486.50"), 2

    def get_sale_quote(self, user_id, skin_instance_id):
        return Decimal("10.00"), Decimal("8.50")

    def sell_skin(self, user_id, skin_instance_id):
        self._talvez_erro()
        return Decimal("8.50"), Decimal("508.50")

    # caixa grátis e skin em destaque (Extras 4)
    estado_gratis = (Decimal("5.00"), None)

    def get_free_case_state(self, user_id):
        return self.estado_gratis

    def open_free_case(self, user_id, skin_id, float_value, now):
        self.chamadas.append(("open_free_case", skin_id, float_value, now))
        self._talvez_erro()
        return 78, Decimal("1.10"), Decimal("5.00")

    def set_featured_skin(self, user_id, skin_instance_id):
        self.chamadas.append(("set_featured", skin_instance_id))
        self._talvez_erro()


class FakeCatalogoGratis:
    def get_free_case_pool(self, common_count, rare_min_price):
        self.pedido = (common_count, rare_min_price)
        return [SKINS[0]], SKINS[1]


def novo_usuario(saldo="500.00"):
    return User(1, "ana", None, "ana@x.com", saldo)


class MarketControllerTests(unittest.TestCase):

    def _controller(self, inv=None, user=None):
        self.view = FakeView()
        self.inv = inv or FakeInventoryDAO()
        self.user = user or novo_usuario()
        self.catalogo = FakeSkinCatalogDAO()
        return Market_Controller(FakeCollectionDAO(), self.catalogo, self.inv, self.view, self.user,
                                 random.Random(1))

    def test_preco_verde_ou_vermelho(self):
        c = self._controller(user=novo_usuario("10.00"))
        self.assertTrue(c.can_afford(Decimal("10.00")))
        self.assertFalse(c.can_afford(Decimal("10.01")))

    def test_checagem_antes_da_compra(self):
        self.assertIsNone(self._controller().check_purchase(Decimal("10")))
        self.assertEqual(self._controller(user=novo_usuario("5")).check_purchase(Decimal("10")),
                         "Saldo insuficiente.")
        cheio = FakeInventoryDAO(itens=rules.INVENTORY_LIMIT)
        self.assertEqual(self._controller(inv=cheio).check_purchase(Decimal("10")), "Inventário cheio!")

    def test_compra_de_caixa_atualiza_saldo_da_sessao(self):
        c = self._controller()
        self.assertTrue(c.buy_case(Collection(1, "Caixa Teste", "10.00")))
        self.assertEqual(self.user.balance, Decimal("490.00"))
        self.assertEqual(self.inv.chamadas[-1], ("buy_case", 1, Decimal("10.00")))  # manda o preço visto
        self.assertTrue(self.view.last[1])

    def test_erro_de_regra_vira_mensagem_e_nao_mexe_no_saldo(self):
        c = self._controller(inv=FakeInventoryDAO(erro=ValueError("Saldo insuficiente.")))
        self.assertFalse(c.buy_case(Collection(1, "Caixa Teste", "10.00")))
        self.assertEqual(self.view.last, ("Saldo insuficiente.", False))
        self.assertEqual(self.user.balance, Decimal("500.00"))

    def test_erro_inesperado_nao_derruba_a_tela(self):
        # Simula o banco caindo no meio da compra. O controller precisa:
        # 1) registrar o erro no log (assertLogs confere e "engole" o traceback,
        #    para ele não aparecer na saída dos testes como se fosse uma falha);
        # 2) mostrar uma mensagem amigável em vez de fechar o jogo.
        c = self._controller(inv=FakeInventoryDAO(erro=RuntimeError("banco caiu")))
        with self.assertLogs("app.controller.market_controller", level="ERROR"):
            self.assertFalse(c.buy_case(Collection(1, "Caixa Teste", "10.00")))
        self.assertFalse(self.view.last[1])

    def test_compra_de_skin_gera_float_dentro_do_desgaste(self):
        c = self._controller()
        anuncio = Market_Price(10, "Field-Tested", "12.00")
        instancia = c.buy_skin(SKINS[0], anuncio)
        _, skin_id, wear, float_value, preco = self.inv.chamadas[-1]
        self.assertEqual((skin_id, wear, preco), (10, "Field-Tested", Decimal("12.00")))
        self.assertTrue(Decimal("0.15") <= float_value < Decimal("0.38"))
        self.assertEqual(instancia.wear, "Field-Tested")
        self.assertEqual(self.user.balance, Decimal("400.00"))

    def test_compra_de_varias_unidades(self):
        c = self._controller()
        self.assertTrue(c.buy_case(Collection(1, "Caixa Teste", "10.00"), quantity=3))
        self.assertEqual(self.inv.chamadas[-1], ("buy_case", 1, Decimal("10.00"), 3))
        self.assertIn("3x Caixa Teste", self.view.last[0])
        anuncio = Market_Price(10, "Field-Tested", "12.00")
        compradas = c.buy_skins(SKINS[0], anuncio, 4)
        _, _, _, floats, _ = self.inv.chamadas[-1]
        self.assertEqual(len(compradas), 4)
        self.assertEqual(len(set(floats)), 4)                         # cada unidade com o seu float
        self.assertTrue(all(Decimal("0.15") <= f < Decimal("0.38") for f in floats))

    def test_quantidade_fora_do_limite_nem_chega_no_banco(self):
        c = self._controller()
        chamadas_antes = len(self.inv.chamadas)
        anuncio = Market_Price(10, "Field-Tested", "12.00")
        for invalida in (0, -1, 51, 2.5, "3"):
            self.assertFalse(c.buy_case(Collection(1, "Caixa Teste", "10.00"), quantity=invalida))
            self.assertEqual(c.buy_skins(SKINS[0], anuncio, invalida), [])
            self.assertIn("Quantidade inválida", self.view.last[0])
            self.assertIsNotNone(c.check_purchase(Decimal("1.00"), invalida))
        self.assertEqual(len(self.inv.chamadas), chamadas_antes)       # o DAO nem foi chamado
        self.assertEqual(self.user.balance, Decimal("500.00"))
        self.assertIsNone(c.check_quantity(50))

    def test_quantidade_maxima(self):
        c = self._controller(inv=FakeInventoryDAO(itens=995), user=novo_usuario("100.00"))
        self.assertEqual(c.max_quantity(Decimal("10.00")), 5)        # só 5 vagas no inventário
        c = self._controller(inv=FakeInventoryDAO(itens=0), user=novo_usuario("25.00"))
        self.assertEqual(c.max_quantity(Decimal("10.00")), 2)        # o saldo dá para 2
        self.assertEqual(c.max_quantity(Decimal("0.01")), 50)        # limite por compra
        self.assertEqual(c.check_purchase(Decimal("10.00"), 3), "Saldo insuficiente.")

    def test_conteudo_da_caixa_com_chances(self):
        tabela = self._controller().case_contents(1)
        self.assertEqual(len(tabela), 2)
        self.assertAlmostEqual(float(sum(c for _, c in tabela)), 1.0, places=12)

    def test_variacao_dos_anuncios_da_pagina(self):
        c = self._controller()
        anuncios = [(SKINS[0], Market_Price(10, "Field-Tested", "2.50")),
                    (SKINS[0], Market_Price(10, "Minimal Wear", "3.00"))]
        variacoes = c.price_changes(anuncios)
        self.assertEqual(variacoes, {(10, "Field-Tested"): (Decimal("25.0"), 24)})   # sem histórico: fica de fora

    def test_variacao_com_banco_fora_do_ar_nao_derruba_a_tela(self):
        c = self._controller()
        c.skin_catalog_dao.get_history_for_listings = lambda pares: 1 / 0
        with self.assertLogs("app.controller.market_controller", level="ERROR"):
            self.assertEqual(c.price_changes([(SKINS[0], Market_Price(10, "Field-Tested", "2.50"))]), {})

    def test_raridades_para_os_filtros(self):
        self.assertEqual(self._controller().list_rarities(), [])          # sem rarity_dao: sem filtros
        c = Market_Controller(FakeCollectionDAO(), FakeSkinCatalogDAO(), FakeInventoryDAO(), FakeView(),
                              novo_usuario(), rarity_dao=FakeRarityDAO())
        self.assertEqual([r.name for r in c.list_rarities()], ["Mil-Spec Grade", "Special Item"])
        # ordem da interface: da mais comum para a mais rara (não pelo id do banco)
        c.rarity_dao.get_all = lambda: [Rarity(5, "Special Item", "0.0026"), Rarity(6, "Consumer Grade", "0"),
                                        Rarity(1, "Mil-Spec Grade", "0.7992")]
        self.assertEqual([r.name for r in c.list_rarities()], ["Consumer Grade", "Mil-Spec Grade", "Special Item"])

    def test_paginacao(self):
        c = self._controller()
        _, paginas = c.list_skins("ak", page=2)
        self.assertEqual(paginas, 3)                     # 50 anúncios / 24 por página
        self.assertEqual(self.catalogo.ultimo, ("ak", 24, 48))


class MarketSearchTests(unittest.TestCase):
    """Busca do mercado: cada palavra em qualquer ordem (testada num SQLite em memória)."""

    NOMES = ["AK-47 | Inheritance", "AK-47 | Redline", "M4A4 | Inheritance", "★ Karambit | Doppler (Phase 2)",
             "AWP | Asiimov"]

    def buscar(self, texto):
        import sqlite3
        from contextlib import closing
        from app.dao.skin_catalog_dao import search_filters
        # closing(): fecha o banco no fim (o Python 3.13+ avisa ResourceWarning se ficar aberto)
        with closing(sqlite3.connect(":memory:")) as banco:
            banco.execute("CREATE TABLE s (name TEXT)")
            banco.executemany("INSERT INTO s VALUES (?)", [(n,) for n in self.NOMES])
            filtros, params = search_filters(texto)
            sql = "SELECT name FROM s s WHERE " + (" AND ".join(filtros) or "1 = 1")
            return sorted(n for (n,) in banco.execute(sql.replace("%s", "?"), params))

    def test_palavras_em_qualquer_ordem(self):
        for texto in ("inheritance", "ak inheritance", "ak-47 inheritance", "Inheritance AK", "ak47 inheritance"):
            esperado = ["AK-47 | Inheritance"] if "ak" in texto.lower() else ["AK-47 | Inheritance", "M4A4 | Inheritance"]
            self.assertEqual(self.buscar(texto), esperado, texto)

    def test_nome_com_barra_e_vazio(self):
        self.assertEqual(self.buscar("AK-47 | Redline"), ["AK-47 | Redline"])
        self.assertEqual(self.buscar("karambit phase 2"), ["★ Karambit | Doppler (Phase 2)"])
        self.assertEqual(len(self.buscar("   ")), len(self.NOMES))


class InventoryControllerTests(unittest.TestCase):

    def _controller(self, inv=None):
        self.view = FakeView()
        self.inv = inv or FakeInventoryDAO()
        self.user = novo_usuario()
        return Inventory_Controller(self.inv, FakeCollectionDAO(), FakeRarityDAO(), self.view, self.user,
                                    random.Random(4))

    def test_conteudo_da_caixa_para_a_roleta(self):
        tabela = self._controller().case_contents(1)
        self.assertEqual([s.id for s, _ in tabela], [10, 11])
        self.assertAlmostEqual(float(sum(c for _, c in tabela)), 1.0, places=12)
        self.assertEqual(self._controller().case_contents(99), [])       # caixa sem itens
        self.assertFalse(self.view.last[1])                               # avisa o jogador

    def test_abrir_caixa_devolve_resultado_pronto_para_a_tela(self):
        c = self._controller()
        resultado = c.open_case(1)
        self.assertIsNotNone(resultado)
        _, collection_id, skin_id, float_value = self.inv.chamadas[-1]
        self.assertEqual(collection_id, 1)
        self.assertIn(skin_id, (10, 11))                       # skin sorteada é da caixa
        self.assertEqual(resultado.skin_instance.id, 77)
        self.assertEqual(resultado.skin_instance.float_value, float_value)
        self.assertEqual(resultado.remaining_cases, 2)
        self.assertTrue(resultado.can_open_another)
        self.assertEqual(self.user.balance, Decimal("486.50"))  # chave descontada
        self.assertEqual(self.view.messages, [])                # sucesso: a tela revela o item

    def test_inventario_cheio_ao_abrir(self):
        c = self._controller(inv=FakeInventoryDAO(erro=ValueError("Inventário cheio!")))
        self.assertIsNone(c.open_case(1))
        self.assertEqual(self.view.last, ("Inventário cheio!", False))
        self.assertEqual(self.user.balance, Decimal("500.00"))

    def test_caixa_sem_itens_nao_chama_o_dao(self):
        c = self._controller()
        self.assertIsNone(c.open_case(999))
        self.assertEqual(self.inv.chamadas, [])                # nada foi consumido
        self.assertFalse(self.view.last[1])

    def _controller_gratis(self, inv=None, agora=datetime(2026, 10, 5, 20, 0)):
        self.view = FakeView()
        self.inv = inv or FakeInventoryDAO()
        self.user = novo_usuario("5.00")
        return Inventory_Controller(self.inv, FakeCollectionDAO(), FakeRarityDAO(), self.view, self.user,
                                    random.Random(4), skin_catalog_dao=FakeCatalogoGratis(), clock=lambda: agora)

    def test_caixa_gratis_conteudo_e_abertura(self):
        c = self._controller_gratis()
        self.assertEqual(c.free_case_wait(), timedelta(0))          # saldo R$ 5,00 e nunca abriu
        tabela = c.free_case_contents()
        self.assertEqual([(s.id, ch) for s, ch in tabela], [(10, Decimal("0.95")), (11, Decimal("0.05"))])
        resultado = c.open_free_case(tabela)
        nome, skin_id, _float, quando = self.inv.chamadas[-1]
        self.assertEqual((nome, quando), ("open_free_case", datetime(2026, 10, 5, 20, 0)))
        self.assertIn(skin_id, (10, 11))
        self.assertEqual(resultado.skin_instance.id, 78)
        self.assertFalse(resultado.can_open_another)                 # a próxima só daqui a 10 min
        self.assertEqual(self.view.messages, [])

    def test_caixa_gratis_recusada_pelo_banco_mostra_o_motivo(self):
        c = self._controller_gratis(inv=FakeInventoryDAO(erro=ValueError("A próxima caixa grátis libera em 09:59.")))
        self.assertIsNone(c.open_free_case(c.free_case_contents()))
        self.assertEqual(self.view.last, ("A próxima caixa grátis libera em 09:59.", False))

    def test_skin_em_destaque(self):
        c = self._controller()
        self.assertTrue(c.set_featured(5))
        self.assertEqual(self.inv.chamadas[-1], ("set_featured", 5))
        self.assertEqual(self.view.last, ("Skin em destaque na Home!", True))
        self.assertTrue(c.set_featured(None))
        self.assertTrue(self.view.last[1])

    def test_vender(self):
        c = self._controller()
        self.assertEqual(c.sale_quote(5), (Decimal("10.00"), Decimal("8.50")))
        self.assertEqual(c.sell_skin(5), Decimal("8.50"))
        self.assertEqual(self.user.balance, Decimal("508.50"))
        self.assertTrue(self.view.last[1])


class HomeControllerTests(unittest.TestCase):
    """Home (Extras 4): se o banco falhar, a Home continua de pé (sem estatísticas)."""

    def test_banco_fora_do_ar_nao_derruba_a_home(self):
        class DaoQuebrado:
            def __getattr__(self, nome):
                def falha(*_args):
                    raise RuntimeError("banco caiu")
                return falha
        c = Home_Controller(DaoQuebrado(), novo_usuario())
        with self.assertLogs("app.controller.home_controller", level="ERROR"):
            self.assertIsNone(c.stats())
            self.assertEqual(c.featured(), (None, False))
            self.assertIsNone(c.free_case_wait())

    def test_contagem_da_caixa_gratis(self):
        dao = FakeInventoryDAO()
        dao.estado_gratis = (Decimal("2.00"), datetime(2026, 10, 5, 19, 55))
        c = Home_Controller(dao, novo_usuario("2.00"), clock=lambda: datetime(2026, 10, 5, 20, 0))
        self.assertEqual(c.free_case_wait(), timedelta(minutes=5))


if __name__ == "__main__":
    unittest.main()
