"""Testes dos controllers do MERCADO e do INVENTÁRIO, com DAOs "de mentira".

Aqui conferimos a lógica dos controllers (mensagens, saldo da sessão,
sorteio enviado ao DAO). As transações em si são conferidas no banco real
pelo script app/unit_tests/manual_gacha_flow.py.

Rodar da raiz do projeto:
    python -m unittest app.unit_tests.test_gacha_controllers -v
"""
import random
import unittest
from decimal import Decimal

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


class FakeSkinCatalogDAO:
    def count_market_listings(self, search="", rarity_id=None):
        return 50

    def get_market_listings(self, search="", limit=24, offset=0, rarity_id=None):
        self.ultimo = (search, limit, offset)
        return []


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

    def buy_case(self, user_id, collection_id, expected_price=None):
        self.chamadas.append(("buy_case", collection_id, expected_price))
        self._talvez_erro()
        return Decimal("490.00")

    def buy_skin(self, user_id, skin_id, wear, float_value, expected_price=None):
        self.chamadas.append(("buy_skin", skin_id, wear, float_value, expected_price))
        self._talvez_erro()
        return 99, expected_price, Decimal("400.00")

    def open_case(self, user_id, collection_id, skin_id, float_value):
        self.chamadas.append(("open_case", collection_id, skin_id, float_value))
        self._talvez_erro()
        return 77, Decimal("3.20"), Decimal("486.50"), 2

    def get_sale_quote(self, user_id, skin_instance_id):
        return Decimal("10.00"), Decimal("8.50")

    def sell_skin(self, user_id, skin_instance_id):
        self._talvez_erro()
        return Decimal("8.50"), Decimal("508.50")


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

    def test_conteudo_da_caixa_com_chances(self):
        tabela = self._controller().case_contents(1)
        self.assertEqual(len(tabela), 2)
        self.assertAlmostEqual(float(sum(c for _, c in tabela)), 1.0, places=12)

    def test_paginacao(self):
        c = self._controller()
        _, paginas = c.list_skins("ak", page=2)
        self.assertEqual(paginas, 3)                     # 50 anúncios / 24 por página
        self.assertEqual(self.catalogo.ultimo, ("ak", 24, 48))


class InventoryControllerTests(unittest.TestCase):

    def _controller(self, inv=None):
        self.view = FakeView()
        self.inv = inv or FakeInventoryDAO()
        self.user = novo_usuario()
        return Inventory_Controller(self.inv, FakeCollectionDAO(), FakeRarityDAO(), self.view, self.user,
                                    random.Random(4))

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

    def test_vender(self):
        c = self._controller()
        self.assertEqual(c.sale_quote(5), (Decimal("10.00"), Decimal("8.50")))
        self.assertEqual(c.sell_skin(5), Decimal("8.50"))
        self.assertEqual(self.user.balance, Decimal("508.50"))
        self.assertTrue(self.view.last[1])


if __name__ == "__main__":
    unittest.main()
