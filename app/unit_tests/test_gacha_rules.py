"""Testes das REGRAS DO JOGO e do SISTEMA DE DROP (sem banco e sem Panda3D).

Usamos random.Random(semente) para o resultado ser sempre o mesmo.

Rodar da raiz do projeto:
    python -m unittest app.unit_tests.test_gacha_rules -v
"""
import random
import unittest
from collections import Counter
from datetime import datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

from app.core import drop_service as drop
from app.core import game_rules as rules

# Probabilidades oficiais (iguais ao seed_base.sql)
PROBS = {
    1: Decimal("0.7992"),   # Mil-Spec
    2: Decimal("0.1598"),   # Restricted
    3: Decimal("0.0320"),   # Classified
    4: Decimal("0.0064"),   # Covert
    5: Decimal("0.0026"),   # Special Item (facas/luvas)
}


def skin(id, rarity_id, min_float="0", max_float="1"):
    """Skin "de mentira" com só os campos que o sorteio usa."""
    return SimpleNamespace(id=id, rarity_id=rarity_id,
                           min_float=Decimal(min_float), max_float=Decimal(max_float))


def caixa_completa():
    # 7 Mil-Spec, 5 Restricted, 3 Classified, 2 Covert, 10 facas (como uma caixa real)
    raridades = [1] * 7 + [2] * 5 + [3] * 3 + [4] * 2 + [5] * 10
    return [skin(i, r) for i, r in enumerate(raridades, start=1)]


class WearTests(unittest.TestCase):

    def test_faixas_oficiais(self):
        self.assertEqual(rules.wear_from_float("0.069999"), "Factory New")
        self.assertEqual(rules.wear_from_float("0.07"), "Minimal Wear")
        self.assertEqual(rules.wear_from_float("0.15"), "Field-Tested")
        self.assertEqual(rules.wear_from_float("0.38"), "Well-Worn")
        self.assertEqual(rules.wear_from_float("0.45"), "Battle-Scarred")
        self.assertEqual(rules.wear_from_float("1.00"), "Battle-Scarred")

    def test_item_sem_desgaste(self):
        self.assertFalse(rules.has_wear(0, 0))
        self.assertEqual(rules.wear_from_float(0, item_has_wear=False), rules.NO_WEAR)
        self.assertEqual(rules.available_wears(0, 0), [rules.NO_WEAR])

    def test_desgastes_disponiveis_respeitam_o_float_da_skin(self):
        self.assertEqual(rules.available_wears("0", "0.08"), ["Factory New", "Minimal Wear"])
        self.assertEqual(rules.available_wears("0.18", "1"),
                         ["Field-Tested", "Well-Worn", "Battle-Scarred"])

    def test_nome_no_mercado(self):
        self.assertEqual(rules.market_hash_name("AK-47 | Redline", "Field-Tested"),
                         "AK-47 | Redline (Field-Tested)")
        self.assertEqual(rules.market_hash_name("★ Karambit", rules.NO_WEAR), "★ Karambit")

    def test_nomes_em_portugues(self):
        self.assertEqual(rules.wear_label("Field-Tested"), "Testada em Campo")
        self.assertEqual(rules.wear_label(rules.NO_WEAR), "Sem pintura")


class MoneyTests(unittest.TestCase):

    def test_taxa_de_venda_arredonda_para_baixo(self):
        self.assertEqual(rules.sell_payout(Decimal("10.00")), Decimal("8.50"))
        self.assertEqual(rules.sell_payout(Decimal("0.03")), Decimal("0.02"))

    def test_formato_brasileiro(self):
        self.assertEqual(rules.format_money(Decimal("1234.5")), "R$ 1.234,50")

    def test_preco_estimado(self):
        self.assertEqual(rules.estimated_price("Covert", "Field-Tested"), Decimal("90.00"))
        self.assertGreater(rules.estimated_price("Covert", "Factory New"),
                           rules.estimated_price("Covert", "Battle-Scarred"))


class DropTableTests(unittest.TestCase):

    def test_tabela_soma_100_porcento(self):
        tabela = drop.drop_table(caixa_completa(), PROBS)
        self.assertAlmostEqual(float(sum(chance for _, chance in tabela)), 1.0, places=12)

    def test_chance_dividida_igualmente_dentro_da_raridade(self):
        tabela = dict((s.id, chance) for s, chance in drop.drop_table(caixa_completa(), PROBS))
        # 2 skins Covert -> cada uma 0,64% / 2 = 0,32%
        self.assertAlmostEqual(float(tabela[16]), 0.0032, places=10)

    def test_caixa_sem_alguma_raridade_redistribui(self):
        sem_facas = [s for s in caixa_completa() if s.rarity_id != 5]
        tabela = drop.drop_table(sem_facas, PROBS)
        self.assertAlmostEqual(float(sum(c for _, c in tabela)), 1.0, places=12)
        mil_spec = sum(c for s, c in tabela if s.rarity_id == 1)
        self.assertAlmostEqual(float(mil_spec), 0.7992 / 0.9974, places=10)

    def test_erros_nao_consomem_nada(self):
        with self.assertRaises(ValueError):
            drop.draw_skin([], PROBS)                       # caixa sem itens
        with self.assertRaises(ValueError):
            drop.draw_skin([skin(1, 99)], PROBS)            # raridade sem probabilidade


class DrawTests(unittest.TestCase):

    def test_distribuicao_das_raridades(self):
        rng = random.Random(2024)
        n = 100_000
        contagem = Counter(drop.draw_skin(caixa_completa(), PROBS, rng).rarity_id for _ in range(n))
        for rarity_id, prob in PROBS.items():
            # tolerância de 0,5 ponto percentual
            self.assertAlmostEqual(contagem[rarity_id] / n, float(prob), delta=0.005)

    def test_distribuicao_do_desgaste(self):
        rng = random.Random(7)
        n = 50_000
        contagem = Counter(rules.wear_from_float(drop.draw_float(0, 1, rng)) for _ in range(n))
        esperado = {nome: chance / 100 for nome, _i, _f, chance, _pt in rules.WEARS}
        for nome, chance in esperado.items():
            self.assertAlmostEqual(contagem[nome] / n, chance, delta=0.01)

    def test_float_respeita_minimo_e_maximo(self):
        rng = random.Random(1)
        for _ in range(5000):
            valor = drop.draw_float("0.06", "0.80", rng)
            self.assertTrue(Decimal("0.06") <= valor < Decimal("0.80"))

    def test_skin_com_float_baixo_quase_sempre_factory_new(self):
        rng = random.Random(3)
        desgastes = Counter(rules.wear_from_float(drop.draw_float("0", "0.08", rng)) for _ in range(5000))
        self.assertGreater(desgastes["Factory New"] / 5000, 0.9)
        self.assertEqual(set(desgastes), {"Factory New", "Minimal Wear"})

    def test_faca_vanilla_tem_float_zero(self):
        self.assertEqual(drop.draw_float(0, 0), Decimal("0"))

    def test_float_de_compra_fica_dentro_do_desgaste(self):
        rng = random.Random(5)
        for _ in range(2000):
            valor = drop.float_for_wear("0.06", "0.80", "Field-Tested", rng)
            self.assertTrue(Decimal("0.15") <= valor < Decimal("0.38"))
        with self.assertRaises(ValueError):
            drop.float_for_wear("0", "0.08", "Battle-Scarred", rng)

    def test_resultado_completo(self):
        rng = random.Random(9)
        item, valor, desgaste = drop.draw_drop(caixa_completa(), PROBS, rng)
        self.assertIn(item.id, [s.id for s in caixa_completa()])
        self.assertEqual(desgaste, rules.wear_from_float(valor))


class PriceChangeTests(unittest.TestCase):
    """Variação de preço do mercado (▲▼): último preço contra o de ~24 h antes."""

    INICIO = datetime(2026, 10, 3, 8, 0)

    def pontos(self, *precos, passo_min=80):
        return [(self.INICIO + timedelta(minutes=passo_min * i), Decimal(p)) for i, p in enumerate(precos)]

    def test_compara_com_o_ponto_de_24_horas_antes(self):
        # 25 pontos de 1 em 1 hora: o ponto de referência é o de 24 h antes do último
        historico = self.pontos(*(["10.00"] + ["50.00"] * 23 + ["12.00"]), passo_min=60)
        self.assertEqual(rules.price_change(historico), (Decimal("20.0"), 24))

    def test_historico_curto_usa_o_primeiro_ponto(self):
        historico = self.pontos("10.00", "10.50", "9.00")         # só 2 h 40 de histórico
        self.assertEqual(rules.price_change(historico), (Decimal("-10.0"), 3))

    def test_sem_pontos_suficientes(self):
        self.assertIsNone(rules.price_change([]))
        self.assertIsNone(rules.price_change(self.pontos("10.00")))
        self.assertIsNone(rules.price_change(self.pontos("0.00", "5.00")))


class FreeCaseTests(unittest.TestCase):
    """Caixa grátis (Extras 4): só sem saldo para a chave, 1 a cada 10 min, rara com 5%."""

    AGORA = datetime(2026, 10, 5, 20, 0, 0)

    def test_so_vale_sem_saldo_para_a_chave(self):
        self.assertIsNone(rules.free_case_wait(rules.KEY_PRICE, None, self.AGORA))
        self.assertEqual(rules.free_case_wait(Decimal("13.49"), None, self.AGORA), timedelta(0))

    def test_uma_a_cada_dez_minutos(self):
        ha_3_min = self.AGORA - timedelta(minutes=3)
        self.assertEqual(rules.free_case_wait(Decimal("0"), ha_3_min, self.AGORA), timedelta(minutes=7))
        ha_10_min = self.AGORA - rules.FREE_CASE_COOLDOWN
        self.assertEqual(rules.free_case_wait(Decimal("0"), ha_10_min, self.AGORA), timedelta(0))
        no_futuro = self.AGORA + timedelta(hours=1)          # relógio do PC voltou no tempo
        self.assertEqual(rules.free_case_wait(Decimal("0"), no_futuro, self.AGORA), rules.FREE_CASE_COOLDOWN)

    def test_formato_da_contagem(self):
        self.assertEqual(rules.format_wait(timedelta(minutes=7, seconds=5)), "07:05")
        self.assertEqual(rules.format_wait(timedelta(seconds=0.2)), "00:01")      # nunca 00:00 antes da hora
        self.assertEqual(rules.format_wait(timedelta(0)), "00:00")

    def test_tabela_soma_100_e_a_rara_tem_5(self):
        baratas = [skin(i, 1) for i in range(1, 9)]
        rara = skin(99, 4)
        tabela = drop.free_case_table(baratas, rara, rules.FREE_CASE_RARE_CHANCE)
        self.assertEqual(sum(c for _s, c in tabela), Decimal("1"))
        self.assertEqual(dict((s.id, c) for s, c in tabela)[99], Decimal("0.05"))
        self.assertEqual(len(drop.free_case_table(baratas, None, rules.FREE_CASE_RARE_CHANCE)), 8)
        with self.assertRaises(ValueError):
            drop.free_case_table([], rara, rules.FREE_CASE_RARE_CHANCE)

    def test_sorteio_respeita_a_chance_da_rara(self):
        rng = random.Random(11)
        tabela = drop.free_case_table([skin(i, 1) for i in range(1, 9)], skin(99, 4), Decimal("0.05"))
        n = 40_000
        raras = sum(1 for _ in range(n) if drop.draw_from_table(tabela, rng)[0].id == 99)
        self.assertAlmostEqual(raras / n, 0.05, delta=0.005)


if __name__ == "__main__":
    unittest.main()
