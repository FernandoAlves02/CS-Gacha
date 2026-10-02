"""Testes do importador (só as partes que não usam internet nem banco).

Os dados abaixo imitam o formato real da CSGO-API (crates.json / skins.json)
e da Skinport (/v1/items e /v1/sales/history).

Rodar da raiz do projeto:
    python -m unittest app.unit_tests.test_sync_market -v
"""
import io
import unittest
import urllib.error
from decimal import Decimal
from email.message import Message

from tools.sync_market import _describe_error, build_catalog, index_prices, index_skins, only_cases, select_cases

IMG = "https://community.akamai.steamstatic.com/economy/image/abc"


def _item(id, name, rarity, paint="1", phase=None):
    data = {"id": id, "name": name, "rarity": {"name": rarity}, "paint_index": paint, "image": IMG}
    if phase is not None:
        data["phase"] = phase
    return data


CRATES = [
    {
        "id": "crate-4001", "name": "CS:GO Weapon Case", "type": "Case",
        "market_hash_name": "CS:GO Weapon Case", "image": IMG, "first_sale_date": "2013/09/20",
        "contains": [
            _item("skin-mp7", "MP7 | Skulls", "Mil-Spec Grade"),
            _item("skin-aug", "AUG | Wings", "Mil-Spec Grade"),
            _item("skin-glock", "Glock-18 | Dragon Tattoo", "Restricted"),
            _item("skin-ak", "AK-47 | Case Hardened", "Classified"),
            _item("skin-awp", "AWP | Lightning Strike", "Covert"),
        ],
        "contains_rare": [
            _item("skin-vanilla-weapon_bayonet", "★ Bayonet", "Covert", paint=None, phase=None),
            _item("skin-bfade", "★ Bayonet | Fade", "Covert", paint="38"),
            _item("skin-kdop", "★ Karambit | Doppler", "Covert", paint="418", phase="Phase 1"),
            _item("skin-kdop", "★ Karambit | Doppler", "Covert", paint="419", phase="Phase 2"),
        ],
    },
    {"id": "crate-sticker", "name": "Sticker Capsule", "type": None, "contains": []},
    {
        "id": "crate-4061", "name": "Chroma Case", "type": "Case",
        "market_hash_name": "Chroma Case", "image": IMG, "first_sale_date": "2015/01/08",
        "contains": [
            _item("skin-mp7", "MP7 | Skulls", "Mil-Spec Grade"),
            _item("skin-nova", "Nova | Sand Dune", "Industrial Grade"),   # não existe em caixa: ignorado
        ],
        "contains_rare": [_item("skin-bfade", "★ Bayonet | Fade", "Covert", paint="38")],
    },
]

SKINS = [
    {"id": "skin-mp7", "name": "MP7 | Skulls", "min_float": 0.0, "max_float": 1.0, "weapon": {"name": "MP7"}},
    {"id": "skin-aug", "name": "AUG | Wings", "min_float": 0.0, "max_float": 0.4, "weapon": {"name": "AUG"}},
    {"id": "skin-glock", "name": "Glock-18 | Dragon Tattoo", "min_float": 0.0, "max_float": 0.08},
    {"id": "skin-ak", "name": "AK-47 | Case Hardened", "min_float": 0.0, "max_float": 1.0},
    {"id": "skin-awp", "name": "AWP | Lightning Strike", "min_float": 0.0, "max_float": 0.08},
    {"id": "skin-bfade", "name": "★ Bayonet | Fade", "min_float": 0.0, "max_float": 0.08,
     "weapon": {"name": "Bayonet"}},
    {"id": "skin-kdop", "name": "★ Karambit | Doppler", "min_float": 0.0, "max_float": 0.08},
]


class CatalogTests(unittest.TestCase):

    def setUp(self):
        self.cases = only_cases(CRATES)
        by_id, by_name = index_skins(SKINS)
        self.caixas, self.skins, self.ligacoes, self.avisos = build_catalog(self.cases, by_id, by_name)

    def test_so_caixas_de_armas(self):
        self.assertEqual([c["name"] for c in self.cases], ["CS:GO Weapon Case", "Chroma Case"])

    def test_selecao_por_nome_e_sugestao(self):
        escolhidas, avisos = select_cases(self.cases, ["chroma case", "Cromah Case"])
        self.assertEqual([c["name"] for c in escolhidas], ["Chroma Case"])
        self.assertEqual(len(avisos), 1)
        self.assertIn("Chroma Case", avisos[0])     # sugere o nome parecido

    def test_raridades(self):
        self.assertEqual(self.skins["skin-mp7"]["rarity_name"], "Mil-Spec Grade")
        self.assertEqual(self.skins["skin-awp"]["rarity_name"], "Covert")
        # facas vêm de contains_rare -> sempre "Special Item"
        self.assertEqual(self.skins["skin-bfade"]["rarity_name"], "Special Item")

    def test_item_fora_das_raridades_de_caixa_e_ignorado(self):
        self.assertNotIn("skin-nova", self.skins)
        self.assertTrue(any("Nova | Sand Dune" in a for a in self.avisos))

    def test_faca_compartilhada_entre_caixas_vira_uma_skin_so(self):
        caixas_da_faca = [c for c, s in self.ligacoes if s == "skin-bfade"]
        self.assertEqual(sorted(caixas_da_faca), ["crate-4001", "crate-4061"])

    def test_fases_da_doppler_sao_itens_separados_com_mesmo_nome_de_mercado(self):
        fases = [s for s in self.skins.values() if s["market_name"] == "★ Karambit | Doppler"]
        self.assertEqual(len(fases), 2)
        self.assertEqual({s["name"] for s in fases},
                         {"★ Karambit | Doppler (Phase 1)", "★ Karambit | Doppler (Phase 2)"})

    def test_floats(self):
        self.assertEqual(self.skins["skin-awp"]["max_float"], Decimal("0.08"))
        vanilla = self.skins["skin-vanilla-weapon_bayonet"]
        self.assertEqual((vanilla["min_float"], vanilla["max_float"]), (Decimal("0"), Decimal("0")))

    def test_nome_da_arma(self):
        self.assertEqual(self.skins["skin-mp7"]["base_weapon"], "MP7")
        self.assertEqual(self.skins["skin-glock"]["base_weapon"], "Glock-18")        # sem "weapon": usa o nome
        self.assertEqual(self.skins["skin-vanilla-weapon_bayonet"]["base_weapon"], "Bayonet")

    def test_sem_ligacoes_repetidas(self):
        self.assertEqual(len(self.ligacoes), len(set(self.ligacoes)))


class PriceTests(unittest.TestCase):

    def test_preco_sugerido_e_medias(self):
        items = [{"market_hash_name": "MP7 | Skulls (Field-Tested)", "suggested_price": 1.234,
                  "min_price": 1.10, "median_price": 1.20}]
        history = [{"market_hash_name": "MP7 | Skulls (Field-Tested)",
                    "last_7_days": {"avg": 1.1, "median": 1.15}, "last_30_days": {"avg": 1.0}}]
        prices = index_prices(items, history)
        self.assertEqual(prices["MP7 | Skulls (Field-Tested)"],
                         (Decimal("1.23"), Decimal("1.10"), Decimal("1.00")))

    def test_ordem_de_reserva_do_preco(self):
        items = [
            {"market_hash_name": "A", "suggested_price": None, "min_price": 9},
            {"market_hash_name": "B", "suggested_price": 0, "median_price": None, "min_price": None},
            {"market_hash_name": "C", "suggested_price": None},
        ]
        history = [{"market_hash_name": "C", "last_7_days": {"median": 3.5}}]
        prices = index_prices(items, history)
        self.assertEqual(prices["A"][0], Decimal("9.00"))
        self.assertNotIn("B", prices)                       # sem nenhum preço válido
        self.assertEqual(prices["C"], (Decimal("3.50"), None, None))

    def test_entradas_vazias(self):
        self.assertEqual(index_prices(None, None), {})


class ErrorMessageTests(unittest.TestCase):

    def _http_error(self, code, body):
        return urllib.error.HTTPError("https://api.skinport.com/v1/items", code, "Forbidden", Message(), io.BytesIO(body))

    def test_erro_http_mostra_codigo_e_resposta_da_api(self):
        texto = _describe_error(self._http_error(403, b'{"errors":[{"id":"forbidden","message":"Access denied"}]}'))
        self.assertIn("HTTP 403", texto)
        self.assertIn("Access denied", texto)

    def test_limite_de_chamadas(self):
        self.assertIn("aguarde 5 minutos", _describe_error(self._http_error(429, b"")))

    def test_erro_sem_http(self):
        self.assertIn("TimeoutError", _describe_error(TimeoutError("timed out")))


if __name__ == "__main__":
    unittest.main()
