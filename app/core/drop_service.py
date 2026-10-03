"""Sistema matemático de drop (100% backend), no mesmo modelo do CS.

Como o CS decide o que sai de uma caixa:

1. RARIDADE: sorteia a raridade usando as probabilidades da tabela rarities
   (79,92% / 15,98% / 3,20% / 0,64% / 0,26%). Só entram as raridades que
   EXISTEM naquela caixa; se faltar alguma, as chances das outras são
   redistribuídas proporcionalmente (random.choices faz isso sozinho, porque
   os pesos são relativos).
2. SKIN: dentro da raridade sorteada, todas as skins têm a MESMA chance.
   Ex.: caixa com 2 skins Covert -> cada uma tem 0,64% / 2 = 0,32%.
3. FLOAT: sorteia a faixa de desgaste (3/24/33/24/16%), sorteia um valor
   dentro dessa faixa na escala 0-1 e "encaixa" esse valor no intervalo
   [float mínimo, float máximo] da skin. Por isso uma skin com float máximo
   0.08 quase sempre sai Factory New, como no jogo.

As funções recebem os dados prontos (lista de skins e probabilidades) e
devolvem o resultado. Não acessam banco nem tela. O parâmetro "rng" permite
passar um random.Random(semente) nos testes para ter resultado repetível.
"""
import random
from decimal import ROUND_DOWN, Decimal

from app.core.game_rules import FLOAT_STEP, NO_WEAR, WEARS, has_wear, wear_from_float, wear_range
from app.core.i18n import t


def group_by_rarity(items):
    """Agrupa as skins da caixa por raridade: {rarity_id: [skin, skin, ...]}."""
    grupos = {}
    for item in items:
        grupos.setdefault(item.rarity_id, []).append(item)
    return grupos


def _check_inputs(items, probabilities):
    """Valida os dados antes de sortear. Qualquer erro aqui impede que a caixa seja consumida."""
    if not items:
        raise ValueError(
            t("Esta caixa não tem itens cadastrados. Rode o importador: python tools/sync_market.py")
        )
    grupos = group_by_rarity(items)
    for rarity_id in grupos:
        if rarity_id not in probabilities:
            raise ValueError(t("A raridade {raridade} não tem probabilidade cadastrada.", raridade=rarity_id))
    if sum(Decimal(str(probabilities[r])) for r in grupos) <= 0:
        raise ValueError(t("As probabilidades desta caixa somam zero."))
    return grupos


def drop_table(items, probabilities):
    """Tabela de drops [item : probabilidade], como pede a documentação.

    Devolve uma lista de (skin, chance) com a chance REAL de cada skin
    nesta caixa (a soma de todas dá 1). Serve para mostrar ao jogador as
    chances e para explicar o algoritmo na apresentação.
    """
    grupos = _check_inputs(items, probabilities)
    total = sum(Decimal(str(probabilities[r])) for r in grupos)
    tabela = []
    for rarity_id, skins in grupos.items():
        chance_raridade = Decimal(str(probabilities[rarity_id])) / total
        for skin in skins:
            tabela.append((skin, chance_raridade / len(skins)))
    return tabela


def draw_rarity(grupos, probabilities, rng=random):
    """Passo 1: sorteia uma raridade entre as que existem na caixa."""
    raridades = list(grupos.keys())
    # random.choices não aceita Decimal como peso, por isso o float().
    pesos = [float(probabilities[r]) for r in raridades]
    return rng.choices(raridades, weights=pesos, k=1)[0]


def draw_skin(items, probabilities, rng=random):
    """Passos 1 e 2: sorteia a raridade e depois uma skin dessa raridade (chance igual)."""
    grupos = _check_inputs(items, probabilities)
    raridade = draw_rarity(grupos, probabilities, rng)
    return rng.choice(grupos[raridade])


def draw_float(min_float, max_float, rng=random):
    """Passo 3: sorteia o float da skin no padrão do CS (ver explicação no topo).

    Devolve Decimal com 9 casas, sempre dentro de [mínimo, máximo).
    Itens sem desgaste (faca vanilla) recebem 0.
    """
    minimo = Decimal(str(min_float))
    maximo = Decimal(str(max_float))
    if not has_wear(minimo, maximo):
        return Decimal("0")
    if minimo >= maximo:
        raise ValueError(t("Float inválido no catálogo (mínimo {minimo} >= máximo {maximo}).",
                           minimo=minimo, maximo=maximo))

    # a) sorteia a faixa de desgaste com os pesos 3/24/33/24/16
    faixa = rng.choices(WEARS, weights=[w[3] for w in WEARS], k=1)[0]
    inicio, fim = float(faixa[1]), float(faixa[2])
    # b) valor aleatório dentro da faixa, na escala geral de 0 a 1
    bruto = inicio + rng.random() * (fim - inicio)
    # c) encaixa no intervalo da skin: mínimo + bruto * (máximo - mínimo)
    valor = float(minimo) + bruto * (float(maximo) - float(minimo))
    return _clamp(Decimal(str(valor)), minimo, maximo)


def float_for_wear(min_float, max_float, wear, rng=random):
    """Float para uma skin comprada no mercado em um desgaste escolhido.

    Ex.: comprar "AK-47 | Redline (Field-Tested)" gera um float aleatório
    entre 0.15 e 0.38 (respeitando o mínimo/máximo da skin).
    """
    minimo = Decimal(str(min_float))
    maximo = Decimal(str(max_float))
    if wear == NO_WEAR:
        if has_wear(minimo, maximo):
            raise ValueError(t("Esta skin tem desgaste; escolha um desgaste válido."))
        return Decimal("0")
    if not has_wear(minimo, maximo):
        raise ValueError(t("Este item não tem desgaste."))

    inicio, fim = wear_range(wear)
    baixo = max(inicio, minimo)
    alto = min(fim, maximo)
    if baixo >= alto:
        raise ValueError(t("Esta skin não existe em {desgaste}.", desgaste=wear))
    valor = float(baixo) + rng.random() * (float(alto) - float(baixo))
    return _clamp(Decimal(str(valor)), baixo, alto)


def free_case_table(commons, rare, rare_chance):
    """Tabela de drops da CAIXA GRÁTIS: [(skin, chance)], somando 1.

    commons: skins baratas (dividem igualmente o que sobra da chance da rara);
    rare: a skin rara (ou None, se o catálogo não tiver uma).
    Ex.: 8 baratas + rara com 5% -> cada barata 11,875% e a rara 5%.
    """
    if not commons:
        raise ValueError(t("Esta caixa não tem itens cadastrados. Rode o importador: python tools/sync_market.py"))
    rare_chance = Decimal(str(rare_chance)) if rare is not None else Decimal("0")
    cada = (Decimal("1") - rare_chance) / len(commons)
    tabela = [(skin, cada) for skin in commons]
    if rare is not None:
        tabela.append((rare, rare_chance))
    return tabela


def draw_from_table(table, rng=random):
    """Sorteia direto de uma tabela [(skin, chance)] (caixa grátis): devolve (skin, float, desgaste)."""
    skins = [skin for skin, _chance in table]
    pesos = [float(chance) for _skin, chance in table]
    skin = rng.choices(skins, weights=pesos, k=1)[0]
    valor = draw_float(skin.min_float, skin.max_float, rng)
    return skin, valor, wear_from_float(valor, has_wear(skin.min_float, skin.max_float))


def draw_drop(items, probabilities, rng=random):
    """Sorteio completo de uma abertura: devolve (skin, float, desgaste)."""
    skin = draw_skin(items, probabilities, rng)
    valor = draw_float(skin.min_float, skin.max_float, rng)
    desgaste = wear_from_float(valor, has_wear(skin.min_float, skin.max_float))
    return skin, valor, desgaste


def _clamp(valor, minimo, maximo):
    """Arredonda para 9 casas e garante minimo <= valor < maximo."""
    valor = valor.quantize(FLOAT_STEP, rounding=ROUND_DOWN)
    if valor < minimo:
        valor = minimo.quantize(FLOAT_STEP, rounding=ROUND_DOWN)
    if valor >= maximo:
        valor = (maximo - FLOAT_STEP).quantize(FLOAT_STEP, rounding=ROUND_DOWN)
    return valor
