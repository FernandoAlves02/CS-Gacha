"""Testes das PREFERÊNCIAS deste PC (Extras 5) e da moeda mostrada na tela.

Rodar da raiz do projeto:
    python -m unittest app.unit_tests.test_preferencias -v
"""
import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest import mock

from app.core import game_rules as rules
from app.core import i18n, preferencias


class PreferenciasTests(unittest.TestCase):

    def setUp(self):
        # o arquivo vai para uma pasta temporária (não mexe na pasta do usuário)
        self.pasta = tempfile.TemporaryDirectory()
        self.original = preferencias.ARQUIVO
        preferencias.ARQUIVO = Path(self.pasta.name) / ".cs_gacha" / "config.json"
        preferencias.carregar()

    def tearDown(self):
        preferencias.ARQUIVO = Path(self.pasta.name) / "nao_existe.json"
        preferencias.carregar()                                  # volta tudo ao padrão
        preferencias.ARQUIVO = self.original
        i18n.definir_idioma("pt", salvar=False)
        self.pasta.cleanup()

    def test_sem_arquivo_valem_os_padroes(self):
        for chave, valor in preferencias.PADROES.items():
            self.assertEqual(preferencias.obter(chave), valor)

    def test_salva_e_le_de_novo(self):
        self.assertTrue(preferencias.definir("tela_cheia", True))
        self.assertTrue(preferencias.definir("volume_musica", 0))
        self.assertTrue(preferencias.definir("moeda", "BRL"))
        preferencias.carregar()                                  # "abre o jogo de novo"
        self.assertTrue(preferencias.obter("tela_cheia"))
        self.assertEqual(preferencias.obter("volume_musica"), 0)
        self.assertEqual(preferencias.obter("moeda"), "BRL")

    def test_volume_com_curva_ao_cubo(self):
        """Extras 6: 10% fica quase mudo; a barra inteira faz diferença."""
        for porcentagem, esperado in ((0, 0.0), (10, 0.001), (40, 0.064), (70, 0.343), (100, 1.0)):
            preferencias.definir("volume_musica", porcentagem, salvar_agora=False)
            self.assertAlmostEqual(preferencias.volume_real("volume_musica"), esperado)
        preferencias.definir("volume_musica", 1, salvar_agora=False)
        self.assertLess(preferencias.volume_real("volume_musica"), 0.00001)   # 1%: ajuste bem fino

    def test_barra_arrastando_so_grava_no_fim(self):
        """Arrastar a barra muda a memória várias vezes; o arquivo só é gravado com salvar()."""
        for valor in (39, 38, 37):
            self.assertTrue(preferencias.definir("volume_efeitos", valor, salvar_agora=False))
        self.assertFalse(preferencias.ARQUIVO.exists())
        self.assertEqual(preferencias.obter("volume_efeitos"), 37)
        preferencias.salvar()
        preferencias.carregar()
        self.assertEqual(preferencias.obter("volume_efeitos"), 37)

    def test_valor_invalido_e_ignorado(self):
        with self.assertLogs("app.core.preferencias", level="WARNING"):
            self.assertFalse(preferencias.definir("volume_efeitos", 150))
            self.assertFalse(preferencias.definir("moeda", "EUR"))
            self.assertFalse(preferencias.definir("tela_cheia", "sim"))
            self.assertFalse(preferencias.definir("nao_existe", 1))
        self.assertEqual(preferencias.obter("volume_efeitos"), preferencias.PADROES["volume_efeitos"])

    def test_arquivo_estragado_nao_impede_o_jogo_de_abrir(self):
        preferencias.ARQUIVO.parent.mkdir(parents=True)
        preferencias.ARQUIVO.write_text("{isso não é json", encoding="utf-8")
        preferencias.carregar()
        self.assertEqual(preferencias.obter("moeda"), "auto")
        # valores errados um por um: o resto do arquivo continua valendo
        preferencias.ARQUIVO.write_text(json.dumps({"moeda": "EUR", "volume_musica": 10, "animacoes": "x"}),
                                        encoding="utf-8-sig")
        preferencias.carregar()
        self.assertEqual((preferencias.obter("moeda"), preferencias.obter("volume_musica"),
                          preferencias.obter("animacoes")), ("auto", 10, True))

    @mock.patch.object(rules, "BRL_PER_USD", Decimal("5.22"))
    def test_moeda_automatica_fixa_em_reais_ou_dolar(self):
        valor = Decimal("52.20")                                 # = US$ 10.00 na cotação 5,22
        self.assertEqual(rules.format_money(valor), "R$ 52,20")  # automática + português
        i18n.definir_idioma("en", salvar=False)
        self.assertEqual(rules.format_money(valor), "US$ 10.00")  # automática + inglês
        preferencias.definir("moeda", "BRL")
        self.assertEqual(rules.format_money(valor), "R$ 52.20")  # inglês com R$ (ponto do inglês)
        i18n.definir_idioma("pt", salvar=False)
        preferencias.definir("moeda", "USD")
        self.assertEqual(rules.format_money(valor), "US$ 10,00")  # português com US$
        self.assertEqual(rules.format_display(rules.display_value(Decimal("7.55")) * 4), "US$ 5,80")


if __name__ == "__main__":
    unittest.main()
