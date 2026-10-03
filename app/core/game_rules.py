"""Regras do jogo: números e fórmulas que imitam o CS.

Tudo o que é "regra de negócio" e pode precisar de ajuste fica AQUI, em um só
lugar. Os DAOs, controllers e telas apenas usam estas constantes e funções.

Nada neste arquivo acessa o banco ou a tela: são funções puras, fáceis de
testar (veja app/unit_tests/test_gacha_rules.py).

Dinheiro usa Decimal (nunca float) para não ter erro de arredondamento,
igual à coluna DECIMAL(10,2) do banco.

Os nomes mostrados na tela (dinheiro, desgaste, raridade) seguem o idioma
escolhido (app/core/i18n.py); os valores guardados no banco não mudam.
"""
from datetime import timedelta
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal

from app.core import i18n

CENT = Decimal("0.01")                 # precisão do dinheiro (2 casas)
FLOAT_STEP = Decimal("0.000000001")    # precisão do float (9 casas, coluna DECIMAL(11,9))

# ======================================================================
# INVENTÁRIO
# ======================================================================

# Limite de itens do inventário do CS (caixas + skins contam juntas).
INVENTORY_LIMIT = 1000

# ======================================================================
# ECONOMIA
# ======================================================================

CURRENCY_SYMBOL = "R$"

# Em inglês os valores aparecem em dólar, convertidos por esta cotação.
# O banco continua em reais: só a EXIBIÇÃO muda. Ajuste quando quiser
# (dólar comercial de 01/10/2026: R$ 5,22).
CURRENCY_SYMBOL_USD = "US$"
BRL_PER_USD = Decimal("5.22")

# Preço da chave cobrada ao ABRIR uma caixa. No CS a chave custa US$ 2,49;
# aqui usamos um valor aproximado em reais. Coloque Decimal("0.00") para
# desligar a cobrança da chave.
KEY_PRICE = Decimal("13.50")

# Taxa descontada na VENDA de uma skin (a Steam cobra cerca de 15%).
# Ex.: skin de R$ 10,00 -> o jogador recebe R$ 8,50.
SELL_FEE_RATE = Decimal("0.15")

# ======================================================================
# RARIDADES
# ======================================================================

# Nome (igual ao da tabela rarities) da raridade das facas e luvas.
# Na API essas skins vêm na lista "contains_rare" de cada caixa.
SPECIAL_RARITY_NAME = "Special Item"

# Nomes de raridade usados pela API -> nomes da nossa tabela rarities.
# Itens com raridade fora desta lista (ex.: Consumer Grade, que só existe em
# coleções e não em caixas) são ignorados pelo importador.
API_RARITY_TO_DB = {
    "Mil-Spec Grade": "Mil-Spec Grade",
    "Restricted": "Restricted",
    "Classified": "Classified",
    "Covert": "Covert",
}

# Raridades que só existem nas COLEÇÕES de mapa (não saem de nenhuma caixa).
# Skins delas entram só no MERCADO (importador com --colecoes; migração 003).
MARKET_ONLY_RARITIES = {
    "Consumer Grade": "Consumer Grade",
    "Industrial Grade": "Industrial Grade",
    "Contraband": "Contraband",
}

# Ordem das raridades na interface (da mais comum para a mais rara).
RARITY_ORDER = [
    "Consumer Grade", "Industrial Grade", "Mil-Spec Grade", "Restricted",
    "Classified", "Covert", "Contraband", SPECIAL_RARITY_NAME,
]

# Na tela as raridades aparecem com o nome oficial do jogo (o mesmo do banco), nos
# dois idiomas. Só o grupo das facas e luvas tem nome próprio: (nome, nome curto dos filtros)
SPECIAL_RARITY_LABELS = {
    "pt": ("★ Item Especial Raro", "★ Especiais"),
    "en": ("★ Rare Special Item", "★ Special"),
}

# ======================================================================
# DESGASTE (FLOAT)
# ======================================================================

# (nome oficial, início, fim, chance no unboxing em %, nome em português)
# - Faixas oficiais do CS: FN 0.00-0.07 | MW 0.07-0.15 | FT 0.15-0.38 |
#   WW 0.38-0.45 | BS 0.45-1.00
# - Chances ao abrir caixa (dados levantados pela comunidade, a Valve não
#   publica a fórmula): 3% / 24% / 33% / 24% / 16%
# O nome oficial em inglês é o usado no mercado ("AK-47 | Redline (Field-Tested)").
WEARS = (
    ("Factory New", Decimal("0.00"), Decimal("0.07"), 3, "Nova de Fábrica"),
    ("Minimal Wear", Decimal("0.07"), Decimal("0.15"), 24, "Pouco Usada"),
    ("Field-Tested", Decimal("0.15"), Decimal("0.38"), 33, "Testada em Campo"),
    ("Well-Worn", Decimal("0.38"), Decimal("0.45"), 24, "Bem Desgastada"),
    ("Battle-Scarred", Decimal("0.45"), Decimal("1.00"), 16, "Veterana de Guerra"),
)

# Itens sem desgaste (faca "vanilla", sem pintura). No banco eles têm
# min_float = max_float = 0.
NO_WEAR = "Not Painted"
NO_WEAR_LABEL = "Sem pintura"

# Ordem de exibição dos desgastes (do melhor para o pior).
WEAR_ORDER = [w[0] for w in WEARS] + [NO_WEAR]

# ======================================================================
# PREÇO ESTIMADO (usado só quando a API não tem o preço)
# ======================================================================

RARITY_BASE_PRICE = {
    "Consumer Grade": Decimal("0.10"),
    "Industrial Grade": Decimal("0.30"),
    "Contraband": Decimal("8000.00"),
    "Mil-Spec Grade": Decimal("0.80"),
    "Restricted": Decimal("4.00"),
    "Classified": Decimal("20.00"),
    "Covert": Decimal("90.00"),
    "Special Item": Decimal("1500.00"),
}
WEAR_PRICE_FACTOR = {
    "Factory New": Decimal("1.60"),
    "Minimal Wear": Decimal("1.20"),
    "Field-Tested": Decimal("1.00"),
    "Well-Worn": Decimal("0.85"),
    "Battle-Scarred": Decimal("0.75"),
    NO_WEAR: Decimal("1.00"),
}
ESTIMATED_CASE_PRICE = Decimal("5.00")

# Origem do preço (coluna "source" no banco)
SOURCE_API = "steam"          # preço real do mercado da Steam
SOURCE_ESTIMATED = "estimado"


# ======================================================================
# FUNÇÕES
# ======================================================================

def to_money(value):
    """Converte qualquer número (Decimal, float, int, texto) para dinheiro com 2 casas."""
    if value is None:
        return None
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


def format_money(value):
    """Valor do banco (sempre em reais) pronto para a tela, no idioma atual.
    pt: Decimal("1234.5") -> "R$ 1.234,50"
    en: convertido pela cotação BRL_PER_USD -> "US$ 236.49"."""
    return format_display(display_value(value))


def display_value(value):
    """Valor do banco (em reais) na moeda da tela, com 2 casas (em inglês, já em dólar)."""
    if i18n.idioma() == "en":
        return to_money(Decimal(str(value)) / BRL_PER_USD)
    return to_money(value)


def format_display(amount):
    """Formata um valor que JÁ está na moeda da tela.

    Serve para contas feitas com valores convertidos, para fecharem na tela:
    format_display(display_value(preco) * 4) -> 4 x US$ 1.45 = "US$ 5.80"
    (convertendo o total em reais daria US$ 5.79, por causa do arredondamento)."""
    simbolo = CURRENCY_SYMBOL_USD if i18n.idioma() == "en" else CURRENCY_SYMBOL
    return f"{simbolo} {i18n.numero(to_money(amount))}"


def has_wear(min_float, max_float):
    """Item tem desgaste? Itens com min = max = 0 (faca vanilla) não têm."""
    return not (Decimal(str(min_float)) == 0 and Decimal(str(max_float)) == 0)


def wear_from_float(float_value, item_has_wear=True):
    """Nome oficial do desgaste a partir do float. Ex.: 0.20 -> "Field-Tested"."""
    if not item_has_wear:
        return NO_WEAR
    valor = Decimal(str(float_value))
    for nome, _inicio, fim, _chance, _pt in WEARS:
        if valor < fim:
            return nome
    return WEARS[-1][0]   # 1.00 exato também é Battle-Scarred


def wear_range(wear):
    """Faixa (início, fim) de um desgaste. Ex.: "Minimal Wear" -> (0.07, 0.15)."""
    for nome, inicio, fim, _chance, _pt in WEARS:
        if nome == wear:
            return inicio, fim
    raise ValueError(i18n.t("Desgaste desconhecido: {desgaste}", desgaste=wear))


def wear_label(wear):
    """Nome do desgaste para a tela: em português ("Testada em Campo") ou,
    em inglês, o nome oficial ("Field-Tested")."""
    if i18n.idioma() == "en":
        return wear
    if wear == NO_WEAR:
        return NO_WEAR_LABEL
    for nome, _inicio, _fim, _chance, pt in WEARS:
        if nome == wear:
            return pt
    return wear


def wear_label_full(wear):
    """Em português também mostra o nome oficial: "Testada em Campo (Field-Tested)".
    Em inglês os dois são iguais, então aparece só "Field-Tested"."""
    rotulo = wear_label(wear)
    return rotulo if rotulo == wear else f"{rotulo} ({wear})"


def rarity_label(rarity_name):
    """Nome da raridade para a tela: o oficial ("Covert"); facas e luvas viram
    "★ Item Especial Raro" (pt) / "★ Rare Special Item" (en)."""
    if rarity_name == SPECIAL_RARITY_NAME:
        return SPECIAL_RARITY_LABELS[i18n.idioma()][0]
    return rarity_name


def rarity_short_label(rarity_name):
    """Nome curto (botões de filtro): "Mil-Spec Grade" -> "Mil-Spec"; facas e luvas -> "★ Especiais"."""
    if rarity_name == SPECIAL_RARITY_NAME:
        return SPECIAL_RARITY_LABELS[i18n.idioma()][1]
    return rarity_name.replace(" Grade", "")


def available_wears(min_float, max_float):
    """Desgastes possíveis para uma skin, respeitando o float mínimo/máximo dela.

    Ex.: uma skin com float de 0.00 a 0.08 só existe em Factory New e
    Minimal Wear. Uma faca vanilla (0 a 0) só existe "Sem pintura".
    """
    minimo = Decimal(str(min_float))
    maximo = Decimal(str(max_float))
    if not has_wear(minimo, maximo):
        return [NO_WEAR]
    # A faixa do desgaste precisa ter algum pedaço dentro de [mínimo, máximo).
    return [nome for nome, inicio, fim, _c, _pt in WEARS if inicio < maximo and fim > minimo]


def market_hash_name(market_name, wear):
    """Nome do item no mercado. Ex.: ("AK-47 | Redline", "Field-Tested") ->
    "AK-47 | Redline (Field-Tested)". Itens sem desgaste ficam sem o parêntese."""
    if wear == NO_WEAR:
        return market_name
    return f"{market_name} ({wear})"


def sell_payout(price):
    """Quanto o jogador recebe ao vender (preço menos a taxa), arredondado para baixo."""
    bruto = Decimal(str(price)) * (Decimal("1") - SELL_FEE_RATE)
    return bruto.quantize(CENT, rounding=ROUND_DOWN)


def estimated_price(rarity_name, wear):
    """Preço de reserva quando a API não tem o item (ou está sem internet)."""
    base = RARITY_BASE_PRICE.get(rarity_name, RARITY_BASE_PRICE["Mil-Spec Grade"])
    fator = WEAR_PRICE_FACTOR.get(wear, Decimal("1.00"))
    return to_money(base * fator)


def price_change(history, hours=24):
    """Variação do preço para o ▲▼ do mercado.

    history: lista de (data, preço) do mais antigo para o mais novo (como os
    DAOs devolvem). Compara o ÚLTIMO preço com o ponto mais recente que tenha
    pelo menos `hours` horas a menos. Se o histórico ainda for mais curto que
    isso, compara com o PRIMEIRO ponto (e as horas devolvidas mostram o período real).

    Devolve (variação em %, horas entre os dois pontos), ou None quando há
    menos de 2 pontos ou o preço de referência é zero.
    Ex.: [(sex 08h, 10.00), (sáb 08h, 11.00)] -> (Decimal("10.0"), 24)
    """
    if not history or len(history) < 2:
        return None
    ultima_data, ultimo_preco = history[-1]
    limite = ultima_data - timedelta(hours=hours)
    ref_data, ref_preco = history[0]
    for data, preco in history[:-1]:
        if data > limite:
            break
        ref_data, ref_preco = data, preco      # o mais recente que ainda está fora da janela
    ref_preco = Decimal(str(ref_preco))
    if ref_preco <= 0:
        return None
    variacao = (Decimal(str(ultimo_preco)) - ref_preco) / ref_preco * Decimal("100")
    horas = int(round((ultima_data - ref_data).total_seconds() / 3600))
    return variacao.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP), horas
