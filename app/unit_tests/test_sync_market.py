"""Testes do importador (só as partes que não usam internet nem banco).

Os dados abaixo imitam o formato real da CSGO-API (crates.json / skins.json)
e da API de preços do mercado da Steam (priceoverview).

Rodar da raiz do projeto:
    python -m unittest app.unit_tests.test_sync_market -v
"""
import io
import unittest
import urllib.error
from decimal import Decimal
from email.message import Message
from unittest import mock

import tools.sync_market as sync
from tools.sync_market import (
    SteamLimite,
    _describe_error,
    add_market_only_skins,
    build_catalog,
    fetch_steam_price,
    index_skins,
    market_only_skins,
    only_cases,
    parse_brl,
    pick_steam_price,
    plan_price_updates,
    select_cases,
)

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
    # skins que não saem de caixa (coleções de mapa): só entram com --colecoes
    {"id": "skin-nova", "name": "Nova | Sand Dune", "min_float": 0.0, "max_float": 0.5,
     "rarity": {"name": "Industrial Grade"}, "paint_index": "99", "weapon": {"name": "Nova"}},
    {"id": "skin-p250", "name": "P250 | Sand Dune", "min_float": 0.0, "max_float": 0.8,
     "rarity": {"name": "Consumer Grade"}, "paint_index": "99"},
    {"id": "skin-howl", "name": "M4A4 | Howl", "min_float": 0.0, "max_float": 0.4,
     "rarity": {"name": "Contraband"}, "paint_index": "309"},
    {"id": "skin-luva", "name": "★ Driver Gloves | Garden", "min_float": 0.06, "max_float": 0.8,
     "rarity": {"name": "Extraordinary"}, "paint_index": "10"},
    {"id": "skin-estranha", "name": "Arma | Nova Raridade", "rarity": {"name": "Raridade Futura"}, "paint_index": "1"},
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


class MarketOnlySkinsTests(unittest.TestCase):
    """--colecoes: skins de coleções de mapa entram só no mercado."""

    def setUp(self):
        self.cases = only_cases(CRATES)
        self.by_id, self.by_name = index_skins(SKINS)
        self.caixas, self.skins, self.ligacoes, self.avisos = build_catalog(self.cases, self.by_id, self.by_name)

    def test_so_entram_skins_que_nao_saem_de_caixa(self):
        extras = market_only_skins(SKINS, self.cases)
        self.assertEqual({s["id"] for s in extras},
                         {"skin-p250", "skin-howl", "skin-luva", "skin-estranha"})   # skin-nova está numa caixa
        self.assertNotIn("skin-mp7", {s["id"] for s in extras})

    def test_raridades_das_colecoes(self):
        extras = market_only_skins(SKINS, self.cases)
        novas = add_market_only_skins(self.skins, extras, self.by_id, self.by_name, self.avisos)
        self.assertEqual(novas, 3)
        self.assertEqual(self.skins["skin-p250"]["rarity_name"], "Consumer Grade")
        self.assertEqual(self.skins["skin-howl"]["rarity_name"], "Contraband")
        self.assertEqual(self.skins["skin-luva"]["rarity_name"], "Special Item")       # luvas = ★
        self.assertNotIn("skin-estranha", self.skins)
        self.assertTrue(any("Raridade Futura" in a for a in self.avisos))

    def test_skins_de_colecao_nao_ganham_ligacao_com_caixa(self):
        antes = list(self.ligacoes)
        add_market_only_skins(self.skins, market_only_skins(SKINS, self.cases), self.by_id, self.by_name, self.avisos)
        self.assertEqual(self.ligacoes, antes)


class SteamPriceTests(unittest.TestCase):

    def test_converte_preco_em_reais(self):
        self.assertEqual(parse_brl("R$ 31,82"), Decimal("31.82"))
        self.assertEqual(parse_brl("R$ 1.234,56"), Decimal("1234.56"))
        self.assertEqual(parse_brl("R$\xa012.345,00"), Decimal("12345.00"))   # espaço "duro" da Steam
        for vazio in (None, "", "--", "R$ 0,00"):
            self.assertIsNone(parse_brl(vazio))

    def test_usa_mediana_e_depois_menor_anuncio(self):
        resposta = {"success": True, "lowest_price": "R$ 31,82", "volume": "745", "median_price": "R$ 35,61"}
        self.assertEqual(pick_steam_price(resposta), Decimal("35.61"))
        self.assertEqual(pick_steam_price({"success": True, "lowest_price": "R$ 31,82"}), Decimal("31.82"))
        self.assertIsNone(pick_steam_price({"success": True}))          # sem anúncio
        self.assertIsNone(pick_steam_price({"success": False}))
        self.assertIsNone(pick_steam_price(None))

    def _http_error(self, code):
        return urllib.error.HTTPError("https://steamcommunity.com/market/priceoverview/", code, "erro",
                                      Message(), io.BytesIO(b"null"))

    def test_limite_da_steam_vira_steamlimite(self):
        with mock.patch.object(sync.urllib.request, "urlopen", side_effect=self._http_error(429)):
            with self.assertRaises(SteamLimite):
                fetch_steam_price("AK-47 | Redline (Field-Tested)")

    def test_item_inexistente_nao_e_erro_de_rede(self):
        with mock.patch.object(sync.urllib.request, "urlopen", side_effect=self._http_error(500)):
            self.assertEqual(fetch_steam_price("Item Que Nao Existe"), {"success": False})

    def test_respostas_de_erro_sao_fechadas(self):
        # Sem fechar, o Python 3.14 mostra "ResourceWarning: Implicitly cleaning up <HTTPError ...>"
        for code in (429, 500, 403):
            corpo = io.BytesIO(b"null")
            erro = urllib.error.HTTPError("https://steamcommunity.com/market/priceoverview/", code, "erro",
                                          Message(), corpo)
            with mock.patch.object(sync.urllib.request, "urlopen", side_effect=erro):
                try:
                    fetch_steam_price("AK-47 | Redline (Field-Tested)")
                except (SteamLimite, RuntimeError):
                    pass
            self.assertTrue(corpo.closed, f"HTTP {code} ficou aberto")

    def test_sem_internet_vira_runtimeerror(self):
        with mock.patch.object(sync.urllib.request, "urlopen", side_effect=urllib.error.URLError("sem rede")):
            with self.assertRaises(RuntimeError):
                fetch_steam_price("AK-47 | Redline (Field-Tested)")

    def test_nome_com_caracteres_especiais_vai_codificado_na_url(self):
        resposta = mock.MagicMock()
        resposta.__enter__.return_value.read.return_value = b'{"success":true,"lowest_price":"R$ 10,00"}'
        with mock.patch.object(sync.urllib.request, "urlopen", return_value=resposta) as urlopen:
            fetch_steam_price("★ Karambit | Doppler (Factory New)")
        url = urlopen.call_args[0][0].full_url
        self.assertIn("currency=7", url)                                  # R$
        self.assertIn("%E2%98%85%20Karambit%20%7C%20Doppler", url)         # ★, espaço e | codificados


class PricePlanTests(unittest.TestCase):

    def test_ordem_das_consultas(self):
        caixas = [(1, "Chroma Case", "estimado", None), (2, "Glove Case", "steam", "2026-10-01 10:00:00")]
        skins = [
            (10, "★ Karambit", Decimal("0"), Decimal("0"), 5),                 # faca vanilla
            (11, "AWP | Teste", Decimal("0"), Decimal("0.08"), 4),             # só FN e MW
            (12, "P250 | Teste", Decimal("0"), Decimal("1"), 1),
        ]
        existentes = {(12, "Field-Tested"): ("steam", "2026-09-01 10:00:00")}
        plano = plan_price_updates(caixas, skins, existentes)
        nomes = [t[3] for t in plano]
        # 1º pendentes: caixa sem preço real, depois skins da raridade mais comum para a mais rara
        self.assertEqual(nomes[0], "Chroma Case")
        self.assertEqual(nomes[1:5], ["P250 | Teste (Factory New)", "P250 | Teste (Minimal Wear)",
                                      "P250 | Teste (Well-Worn)", "P250 | Teste (Battle-Scarred)"])
        self.assertEqual(nomes[5:8], ["AWP | Teste (Factory New)", "AWP | Teste (Minimal Wear)", "★ Karambit"])
        # 2º os que já têm preço real, do mais antigo para o mais novo
        self.assertEqual(nomes[8:], ["P250 | Teste (Field-Tested)", "Glove Case"])
        self.assertEqual(plano[0][:3], ("caixa", 1, None))
        self.assertEqual(plano[-3][2], "Not Painted")


class _BancoFalso:
    """Banco "de mentira" para o update_prices_from_steam (só anota os comandos)."""

    def __init__(self):
        self.comandos, self.commits = [], 0

    def connect(self):
        banco = self

        class Cursor:
            def execute(self, sql, params=None):
                banco.comandos.append(sql)

            def close(self):
                pass

        class Conexao:
            def cursor(self, buffered=False):
                return Cursor()

            def commit(self):
                banco.commits += 1

            def rollback(self):
                pass

        return Conexao()

    def disconnect(self, cursor, connection):
        pass


class SteamLimitTests(unittest.TestCase):
    """Extras 7: na primeira recusa da Steam (429) a passada para, sem insistir."""

    def test_para_na_primeira_recusa_e_guarda_o_que_ja_veio(self):
        consultas, esperas = [], []

        def steam(nome):
            consultas.append(nome)
            if len(consultas) == 3:
                raise SteamLimite()
            return {"success": True, "median_price": "R$ 10,00"}

        tarefas = [("caixa", i, None, f"Caixa {i}") for i in range(1, 7)]
        banco = _BancoFalso()
        with mock.patch("builtins.print"):
            total = sync.update_prices_from_steam(banco, tarefas, fetch=steam, sleep=esperas.append)
        self.assertEqual(len(consultas), 3)                       # não tentou de novo nem seguiu adiante
        self.assertEqual((total["reais"], total["motivo"]), (2, "limite"))
        self.assertEqual(esperas, [sync.STEAM_INTERVALO] * 2)     # só o intervalo normal entre consultas
        self.assertGreaterEqual(banco.commits, 1)                 # os 2 preços que vieram ficaram salvos

    def test_intervalo_configuravel(self):
        esperas = []
        tarefas = [("caixa", i, None, f"Caixa {i}") for i in range(1, 4)]
        with mock.patch("builtins.print"):
            sync.update_prices_from_steam(_BancoFalso(), tarefas, fetch=lambda nome: {"success": False},
                                          sleep=esperas.append, intervalo=30)
        self.assertEqual(esperas, [30, 30])


class ContinuousModeTests(unittest.TestCase):

    def test_espera_entre_passadas(self):
        self.assertEqual(sync.wait_before_next_pass({"motivo": None}), sync.PAUSA_ENTRE_PASSADAS)
        self.assertEqual(sync.wait_before_next_pass({"motivo": "limite"}), sync.PAUSA_APOS_LIMITE)
        self.assertEqual(sync.wait_before_next_pass({"motivo": "rede"}), sync.PAUSA_APOS_REDE)
        self.assertIsNone(sync.wait_before_next_pass({"motivo": "ctrlc"}))

    def test_espera_dobra_a_cada_recusa_seguida(self):
        horas = [sync.wait_before_next_pass({"motivo": "limite"}, n) / 3600 for n in range(1, 6)]
        self.assertEqual(horas, [1, 2, 4, 6, 6])                  # 1 h, 2 h, 4 h e no máximo 6 h

    def test_passada_tem_todas_as_caixas_e_completa_com_skins(self):
        tarefas = [("skin", 10, "Factory New", "A"), ("caixa", 1, None, "C1"), ("skin", 11, "Minimal Wear", "B"),
                   ("caixa", 2, None, "C2"), ("skin", 12, "Field-Tested", "C")]
        self.assertEqual([t[3] for t in sync.tasks_for_pass(tarefas, 4)], ["C1", "C2", "A", "B"])
        self.assertEqual([t[3] for t in sync.tasks_for_pass(tarefas, 1)], ["C1", "C2"])   # caixas sempre entram

    def test_repete_ate_ctrl_c_e_espera_mais_quando_a_steam_limita(self):
        resultados = [
            {"reais": 10, "sem_anuncio": 0, "falhas": 0, "parada": None, "motivo": None},
            {"reais": 3, "sem_anuncio": 0, "falhas": 0, "parada": "limite", "motivo": "limite"},
            {"reais": 0, "sem_anuncio": 0, "falhas": 0, "parada": "limite", "motivo": "limite"},
            {"reais": 4, "sem_anuncio": 0, "falhas": 0, "parada": None, "motivo": None},
            {"reais": 0, "sem_anuncio": 0, "falhas": 0, "parada": "limite", "motivo": "limite"},
            {"reais": 5, "sem_anuncio": 0, "falhas": 0, "parada": "ctrl+c", "motivo": "ctrlc"},
        ]
        esperas = []
        with mock.patch.object(sync, "load_price_plan", return_value=[("caixa", 1, None, "X")]), \
                mock.patch.object(sync, "update_prices_from_steam", side_effect=resultados), \
                mock.patch("builtins.print"):
            passadas = sync.run_continuous(database=None, sleep=esperas.append)
        self.assertEqual(passadas, 6)
        # recusa seguida dobra a espera; uma passada boa zera a contagem
        self.assertEqual(esperas, [sync.PAUSA_ENTRE_PASSADAS, sync.PAUSA_APOS_LIMITE, 2 * sync.PAUSA_APOS_LIMITE,
                                   sync.PAUSA_ENTRE_PASSADAS, sync.PAUSA_APOS_LIMITE])


class ErrorMessageTests(unittest.TestCase):

    def test_erro_http_mostra_codigo_e_resposta(self):
        erro = urllib.error.HTTPError("https://exemplo", 403, "Forbidden", Message(),
                                      io.BytesIO(b"<title>Just a moment...</title>"))
        texto = _describe_error(erro)
        self.assertIn("HTTP 403", texto)
        self.assertIn("Just a moment", texto)
        self.assertTrue(erro.fp is None or erro.fp.closed)   # leu o motivo e fechou

    def test_erro_sem_http(self):
        self.assertIn("TimeoutError", _describe_error(TimeoutError("timed out")))


if __name__ == "__main__":
    unittest.main()
