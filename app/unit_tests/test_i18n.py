"""Testes dos IDIOMAS (português e inglês), sem banco e sem Panda3D.

Os dois primeiros testes leem o CÓDIGO do projeto (sem executar as telas) e
conferem que todo texto passado para t("...") tem tradução, com os mesmos
{valores}, e que o dicionário não tem traduções sobrando.

Rodar da raiz do projeto:
    python -m unittest app.unit_tests.test_i18n -v
"""
import ast
import string
import tempfile
import unittest
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from unittest import mock

from app.controller.market_controller import MAX_PER_PURCHASE, Market_Controller
from app.core import game_rules as rules
from app.core import i18n
from app.core.i18n_en import TEXTOS_EN
from app.core.paths import PROJECT_ROOT

APP_DIR = PROJECT_ROOT / "app"

# Textos que chegam ao t() por variável (listas das telas): arquivo -> nomes das constantes
CONSTANTES_TRADUZIDAS = {
    "view/game_view_base.py": ["MENU_ITEMS"],         # (texto, rota)
    "view/market_view.py": ["ABAS"],
    "view/inventory_view.py": ["FILTROS"],
    "view/login_register_view.py": ["CAMPOS", "TEXTOS"],
}


def _textos_das_constantes():
    """Lê as constantes acima direto do código (ast) e devolve os textos em português."""
    textos = set()
    for arquivo, nomes in CONSTANTES_TRADUZIDAS.items():
        arvore = ast.parse((APP_DIR / arquivo).read_text(encoding="utf-8"))
        for no in arvore.body:
            if isinstance(no, ast.Assign) and isinstance(no.targets[0], ast.Name) and no.targets[0].id in nomes:
                valor = ast.literal_eval(no.value)
                if no.targets[0].id == "MENU_ITEMS":
                    textos.update(texto for texto, _rota in valor)
                elif no.targets[0].id == "CAMPOS":
                    textos.update(exemplo for exemplo, _icone, _senha in valor.values())
                elif no.targets[0].id == "TEXTOS":
                    textos.update(texto for trio in valor.values() for texto in trio)
                else:
                    textos.update(valor)
    return textos


def _textos_do_codigo():
    """Todos os t("texto literal", ...) do projeto -> {texto: "arquivo:linha"}."""
    achados = {}
    for caminho in sorted(APP_DIR.rglob("*.py")):
        if "unit_tests" in caminho.parts:
            continue
        for no in ast.walk(ast.parse(caminho.read_text(encoding="utf-8"))):
            if not isinstance(no, ast.Call) or not no.args:
                continue
            funcao = no.func
            nome = funcao.id if isinstance(funcao, ast.Name) else getattr(funcao, "attr", None)
            primeiro = no.args[0]
            if nome == "t" and isinstance(primeiro, ast.Constant) and isinstance(primeiro.value, str):
                achados.setdefault(primeiro.value, f"{caminho.relative_to(PROJECT_ROOT)}:{no.lineno}")
    return achados


def _campos(texto):
    return {campo for _literal, campo, _formato, _conversao in string.Formatter().parse(texto) if campo}


class TraducoesTests(unittest.TestCase):

    def test_todo_texto_do_codigo_tem_traducao_com_os_mesmos_valores(self):
        usados = dict(_textos_do_codigo())
        for texto in _textos_das_constantes():
            usados.setdefault(texto, "constante de tela")
        self.assertGreater(len(usados), 100)
        faltando = {texto: onde for texto, onde in usados.items() if texto not in TEXTOS_EN}
        self.assertEqual(faltando, {}, "Textos sem tradução em app/core/i18n_en.py")
        for texto in usados:
            self.assertEqual(_campos(texto), _campos(TEXTOS_EN[texto]), f"valores diferentes em {texto!r}")

    def test_dicionario_sem_traducao_sobrando(self):
        usados = set(_textos_do_codigo()) | _textos_das_constantes()
        self.assertEqual(sorted(set(TEXTOS_EN) - usados), [])


class IdiomaTests(unittest.TestCase):

    def setUp(self):
        # o arquivo do idioma vai para uma pasta temporária (não mexe na pasta do usuário)
        self.pasta = tempfile.TemporaryDirectory()
        self.arquivo_original = i18n.ARQUIVO_PREFERENCIA
        i18n.ARQUIVO_PREFERENCIA = Path(self.pasta.name) / ".cs_gacha" / "idioma.txt"
        i18n._avisados.clear()

    def tearDown(self):
        i18n.definir_idioma("pt", salvar=False)
        i18n.ARQUIVO_PREFERENCIA = self.arquivo_original
        self.pasta.cleanup()

    def test_portugues_e_o_padrao_e_o_texto_e_a_propria_chave(self):
        self.assertEqual(i18n.idioma(), "pt")
        self.assertEqual(i18n.t("Saldo insuficiente."), "Saldo insuficiente.")
        self.assertEqual(i18n.t("Vender {nome}?", nome="AK-47 | Redline"), "Vender AK-47 | Redline?")

    def test_ingles_traduz_e_preenche_os_valores(self):
        i18n.definir_idioma("en", salvar=False)
        self.assertEqual(i18n.t("Saldo insuficiente."), "Insufficient balance.")
        self.assertEqual(i18n.t("Vender {nome}?", nome="AK-47 | Redline"), "Sell AK-47 | Redline?")

    def test_texto_sem_traducao_mostra_o_portugues_e_avisa_no_log(self):
        i18n.definir_idioma("en", salvar=False)
        with self.assertLogs("app.core.i18n", level="WARNING"):
            self.assertEqual(i18n.t("Texto novo sem tradução"), "Texto novo sem tradução")

    def test_escolha_fica_salva_para_a_proxima_vez(self):
        i18n.definir_idioma("en")
        self.assertEqual(i18n.ARQUIVO_PREFERENCIA.read_text(encoding="utf-8"), "en")
        i18n.definir_idioma("pt", salvar=False)          # "fecha o jogo"
        i18n.carregar_preferencia()                      # "abre de novo"
        self.assertEqual(i18n.idioma(), "en")

    def test_arquivo_com_bom_ou_ilegivel_nao_impede_o_jogo_de_abrir(self):
        i18n.ARQUIVO_PREFERENCIA.parent.mkdir(parents=True)
        i18n.ARQUIVO_PREFERENCIA.write_text("en", encoding="utf-8-sig")       # Bloco de Notas com BOM
        i18n.carregar_preferencia()
        self.assertEqual(i18n.idioma(), "en")
        i18n.definir_idioma("pt", salvar=False)
        i18n.ARQUIVO_PREFERENCIA.write_bytes(b"\xff\xfee\x00n\x00\x80")     # UTF-16 / lixo
        i18n.carregar_preferencia()
        self.assertEqual(i18n.idioma(), "pt")

    def test_sem_arquivo_ou_idioma_desconhecido_fica_o_portugues(self):
        i18n.carregar_preferencia()                      # arquivo ainda não existe
        self.assertEqual(i18n.idioma(), "pt")
        with self.assertLogs("app.core.i18n", level="WARNING"):
            i18n.definir_idioma("es")
        self.assertEqual(i18n.idioma(), "pt")

    def test_numeros_e_datas_no_formato_de_cada_idioma(self):
        quando = datetime(2026, 10, 5, 8, 30)
        self.assertEqual(i18n.numero(Decimal("1234.5")), "1.234,50")
        self.assertEqual(i18n.numero(Decimal("0.123456789"), 9), "0,123456789")
        self.assertEqual(i18n.data(quando), "05/10 08:30")
        self.assertEqual(i18n.data(quando, com_ano=True), "05/10/2026 08:30")
        i18n.definir_idioma("en", salvar=False)
        self.assertEqual(i18n.numero(Decimal("1234.5")), "1,234.50")
        self.assertEqual(i18n.data(quando), "10/05 08:30")
        self.assertEqual(i18n.data(None), "")


class DinheiroENomesTests(unittest.TestCase):

    def tearDown(self):
        i18n.definir_idioma("pt", salvar=False)

    def setUp(self):
        # os números abaixo usam a cotação de 5,22; o teste não quebra se ela mudar em game_rules.py
        cotacao = mock.patch.object(rules, "BRL_PER_USD", Decimal("5.22"))
        cotacao.start()
        self.addCleanup(cotacao.stop)

    def test_dinheiro_em_reais_e_em_dolar_pela_cotacao(self):
        self.assertEqual(rules.format_money(Decimal("1234.5")), "R$ 1.234,50")
        i18n.definir_idioma("en", salvar=False)
        self.assertEqual(rules.format_money(rules.BRL_PER_USD * Decimal("1234.56")), "US$ 1,234.56")
        self.assertEqual(rules.format_money(Decimal("13.50")),
                         f"US$ {(Decimal('13.50') / rules.BRL_PER_USD).quantize(Decimal('0.01'))}")

    def test_conta_na_tela_fecha_tambem_em_dolar(self):
        preco = Decimal("7.55")                      # R$ 7,55 = US$ 1,4464 -> US$ 1.45
        self.assertEqual(rules.format_display(rules.display_value(preco) * 4), "R$ 30,20")
        i18n.definir_idioma("en", salvar=False)
        self.assertEqual(rules.format_money(preco), "US$ 1.45")
        self.assertEqual(rules.format_display(rules.display_value(preco) * 4), "US$ 5.80")   # e não 5.79

    def test_desgaste_e_raridade_no_idioma(self):
        self.assertEqual(rules.wear_label("Field-Tested"), "Testada em Campo")
        self.assertEqual(rules.wear_label_full("Field-Tested"), "Testada em Campo (Field-Tested)")
        self.assertEqual(rules.rarity_label("Covert"), "Covert")                 # nome oficial, como antes
        self.assertEqual(rules.rarity_short_label("Mil-Spec Grade"), "Mil-Spec")
        self.assertEqual(rules.rarity_label("Special Item"), "★ Item Especial Raro")
        self.assertEqual(rules.rarity_short_label("Special Item"), "★ Especiais")
        i18n.definir_idioma("en", salvar=False)
        self.assertEqual(rules.wear_label("Field-Tested"), "Field-Tested")
        self.assertEqual(rules.wear_label_full("Field-Tested"), "Field-Tested")
        self.assertEqual(rules.wear_label(rules.NO_WEAR), "Not Painted")
        self.assertEqual(rules.rarity_label("Covert"), "Covert")
        self.assertEqual(rules.rarity_short_label("Mil-Spec Grade"), "Mil-Spec")
        self.assertEqual(rules.rarity_short_label("Special Item"), "★ Special")

    def test_mensagem_do_controller_sai_no_idioma_escolhido(self):
        self.assertIn("Quantidade inválida", Market_Controller.check_quantity(0))
        i18n.definir_idioma("en", salvar=False)
        self.assertEqual(Market_Controller.check_quantity(0),
                         f"Invalid quantity (1 to {MAX_PER_PURCHASE} per purchase).")


if __name__ == "__main__":
    unittest.main()
