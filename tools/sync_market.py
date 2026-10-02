"""IMPORTADOR DO MERCADO (Fase 2): traz caixas, skins e preços REAIS do CS para o banco.

De onde vêm os dados
--------------------
1. CATÁLOGO (caixas, conteúdo de cada caixa, raridade, float mínimo/máximo,
   imagens): CSGO-API do ByMykel (arquivos JSON públicos no GitHub, sem chave).
2. PREÇOS em reais: API pública de preços do MERCADO DA STEAM (priceoverview),
   sem chave, já em R$. É o preço oficial do mercado do CS.
   A Steam limita as consultas (cerca de 20 por minuto) e responde UM item por
   vez, por isso a atualização completa demora (~1 h para as 6 caixas padrão).
   O script consulta primeiro o que importa mais (caixas, depois skins comuns),
   salva o progresso a cada 10 itens e pode ser interrompido com Ctrl+C e
   continuado depois: na próxima execução ele começa pelo que ainda falta.

O jogo NUNCA acessa a internet: ele só lê o banco. Este script é rodado
antes (no seu PC e no do professor) para preencher/atualizar o banco.
Cada preço novo também vai para price_history (o histórico de preços).

Como usar (na raiz do projeto, com o .venv ativado)
-----------------------------------------------------
    python tools/sync_market.py                 catálogo das CAIXAS_PADRAO + preços
    python tools/sync_market.py --listar        mostra todas as caixas disponíveis na API
    python tools/sync_market.py --caixas "Chroma Case" "Fracture Case"
    python tools/sync_market.py --todas         importa TODAS as caixas (demora muito mais)
    python tools/sync_market.py --imagens       também baixa as imagens (app/assets/items)
    python tools/sync_market.py --so-precos     só atualiza preços (não baixa o catálogo)
    python tools/sync_market.py --limite 100    consulta no máximo 100 preços nesta execução
    python tools/sync_market.py --so-precos --continuo   repete sem parar (histórico para o gráfico)
    python tools/sync_market.py --sem-precos    só catálogo (itens novos com preço estimado)

Pode rodar quantas vezes quiser: ele atualiza o que já existe (não duplica).
Enquanto um item não tem preço real, ele usa um preço estimado
(game_rules.estimated_price), então o jogo sempre funciona.
"""
import argparse
import difflib
import gzip
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

# Permite rodar "python tools/sync_market.py" a partir da raiz do projeto.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core import game_rules as rules                              # noqa: E402
from app.core.paths import ITEM_IMAGES_DIR, TOOLS_CACHE_DIR, item_image_path  # noqa: E402

CATALOG_URL = "https://raw.githubusercontent.com/ByMykel/CSGO-API/main/public/api/en/{arquivo}"
# currency=7 -> Real brasileiro (R$) | appid=730 -> Counter-Strike
STEAM_PRICE_URL = "https://steamcommunity.com/market/priceoverview/?appid=730&currency=7&market_hash_name={nome}"
USER_AGENT = "CSGacha/1.0 (projeto integrador SENAC)"

STEAM_INTERVALO = 3.2        # segundos entre consultas (a Steam aceita ~20 por minuto)
STEAM_PAUSA_LIMITE = 65      # segundos de pausa quando a Steam responde "muitas consultas" (429)
STEAM_MAX_PAUSAS = 3         # pausas seguidas antes de parar (o progresso fica salvo)
STEAM_MAX_FALHAS = 5         # erros de rede seguidos antes de parar (provavelmente sem internet)
SALVAR_A_CADA = 10           # commit no banco a cada N preços

# Modo contínuo (--continuo): passa por todos os itens, espera e começa de novo.
# Cada passada grava um ponto novo no histórico de cada item (para o gráfico).
PAUSA_ENTRE_PASSADAS = 5 * 60    # segundos entre uma passada e a próxima
PAUSA_APOS_LIMITE = 15 * 60      # se a Steam limitou, espera mais antes de continuar
PAUSA_APOS_REDE = 5 * 60         # se a internet caiu, espera e tenta de novo

# Caixas importadas quando nenhuma é informada. Troque à vontade
# (use --listar para ver os nomes exatos).
CAIXAS_PADRAO = [
    "CS:GO Weapon Case",
    "Chroma Case",
    "Glove Case",
    "Fracture Case",
    "Dreams & Nightmares Case",
    "Kilowatt Case",
]


class SteamLimite(Exception):
    """A Steam respondeu 429: muitas consultas seguidas, precisa esperar."""


# ======================================================================
# 1. DOWNLOAD DO CATÁLOGO (com cópia local em tools/cache)
# ======================================================================

def download(url, cache_name, timeout=120):
    """Baixa um JSON. Se falhar, usa a última cópia salva em tools/cache.

    Devolve (dados, origem) onde origem é "internet" ou "cache".
    Lança RuntimeError se não houver nem internet nem cópia local.
    """
    cache_file = TOOLS_CACHE_DIR / cache_name
    try:
        request = urllib.request.Request(url, headers={
            "User-Agent": USER_AGENT,
            "Accept-Encoding": "gzip",
            "Accept": "application/json",
        })
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            encoding = (response.headers.get("Content-Encoding") or "").lower()
        if encoding == "gzip":
            raw = gzip.decompress(raw)

        data = json.loads(raw.decode("utf-8"))
        TOOLS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(data), encoding="utf-8")
        return data, "internet"

    except Exception as error:   # sem internet, site fora do ar, JSON inválido...
        motivo = _describe_error(error)
        if cache_file.exists():
            data_cache = datetime.fromtimestamp(cache_file.stat().st_mtime).strftime("%d/%m %H:%M")
            print(f"  ! Falha ao baixar ({motivo}). Usando a cópia local de {data_cache}.")
            return json.loads(cache_file.read_text(encoding="utf-8")), "cache"
        raise RuntimeError(f"Não foi possível baixar {url} ({motivo}) e não há cópia local.") from error


def _describe_error(error):
    """Mensagem curta e COMPLETA do erro, para sabermos exatamente o que o site respondeu."""
    if isinstance(error, urllib.error.HTTPError):
        detalhe = ""
        try:   # o corpo da resposta de erro costuma dizer o motivo
            corpo = error.read()
            if (error.headers.get("Content-Encoding") or "").lower() == "gzip":
                corpo = gzip.decompress(corpo)
            detalhe = " ".join(corpo.decode("utf-8", "replace").split())[:300]
        except Exception:
            pass
        return f"HTTP {error.code} {error.reason}" + (f" | resposta: {detalhe}" if detalhe else "")
    return f"{error.__class__.__name__}: {error}"


# ======================================================================
# 2. CATÁLOGO (funções puras: recebem os JSON e devolvem listas prontas)
# ======================================================================

def only_cases(crates):
    """Da lista de "crates" da API, fica só com as CAIXAS de armas (type == "Case")."""
    return [crate for crate in crates if crate.get("type") == "Case"]


def index_skins(skins_json):
    """Índices do skins.json da API: por id e por nome (para achar o float de cada skin)."""
    by_id, by_name = {}, {}
    for skin in skins_json or []:
        if skin.get("id"):
            by_id[skin["id"]] = skin
        if skin.get("name"):
            by_name.setdefault(skin["name"], skin)
    return by_id, by_name


def select_cases(all_cases, wanted_names):
    """Escolhe as caixas pelo nome (sem diferenciar maiúsculas). Devolve (escolhidas, avisos)."""
    by_lower = {case["name"].lower(): case for case in all_cases}
    selected, warnings = [], []
    for name in wanted_names:
        case = by_lower.get(name.strip().lower())
        if case:
            if case not in selected:
                selected.append(case)
        else:
            parecidas = difflib.get_close_matches(name, [c["name"] for c in all_cases], n=3)
            dica = f" Você quis dizer: {', '.join(parecidas)}?" if parecidas else ""
            warnings.append(f"Caixa '{name}' não encontrada na API.{dica}")
    return selected, warnings


def build_catalog(cases, skins_by_id, skins_by_name):
    """Monta tudo o que vai para o banco a partir das caixas escolhidas.

    Devolve (caixas, skins, ligacoes, avisos):
      caixas   -> lista de dict (api_id, name, market_name, image_url)
      skins    -> dict {api_id: dict(api_id, name, market_name, base_weapon,
                                     image_url, min_float, max_float, rarity_name)}
      ligacoes -> lista de (api_id da caixa, api_id da skin) = conteúdo de cada caixa
    """
    caixas, skins, ligacoes, avisos = [], {}, [], []

    for crate in cases:
        caixas.append({
            "api_id": crate["id"],
            "name": crate["name"],
            "market_name": crate.get("market_hash_name") or crate["name"],
            "image_url": crate.get("image"),
        })

        # Itens normais: raridade vem da própria skin (Mil-Spec ... Covert)
        for entry in crate.get("contains") or []:
            api_rarity = (entry.get("rarity") or {}).get("name")
            rarity_name = rules.API_RARITY_TO_DB.get(api_rarity)
            if rarity_name is None:
                avisos.append(f"{crate['name']}: '{entry.get('name')}' ignorado (raridade {api_rarity}).")
                continue
            key = _add_skin(skins, entry, rarity_name, skins_by_id, skins_by_name, avisos)
            ligacoes.append((crate["id"], key))

        # Itens raros (facas e luvas): sempre a raridade "Special Item" (0,26%)
        for entry in crate.get("contains_rare") or []:
            key = _add_skin(skins, entry, rules.SPECIAL_RARITY_NAME, skins_by_id, skins_by_name, avisos)
            ligacoes.append((crate["id"], key))

    # remove ligações repetidas mantendo a ordem
    ligacoes = list(dict.fromkeys(ligacoes))
    return caixas, skins, ligacoes, avisos


def _add_skin(skins, entry, rarity_name, skins_by_id, skins_by_name, avisos):
    base_id = entry["id"]
    phase = entry.get("phase")                     # fases da Doppler (Phase 1, Ruby...)
    key = f"{base_id}_{phase}".replace(" ", "_") if phase and phase not in base_id else base_id
    if key in skins:
        if skins[key]["rarity_name"] != rarity_name:
            avisos.append(f"'{entry.get('name')}' aparece com raridades diferentes; mantida {skins[key]['rarity_name']}.")
        return key

    name = entry.get("name") or base_id
    details = skins_by_id.get(base_id) or skins_by_name.get(name) or {}

    # Faca "vanilla" (sem pintura) não tem desgaste: float 0 a 0.
    is_vanilla = entry.get("paint_index") in (None, "", "0") or "vanilla" in base_id
    if is_vanilla:
        min_float, max_float = Decimal("0"), Decimal("0")
    elif details.get("min_float") is not None and details.get("max_float") is not None:
        min_float = Decimal(str(details["min_float"]))
        max_float = Decimal(str(details["max_float"]))
    else:
        min_float, max_float = Decimal("0"), Decimal("1")
        avisos.append(f"'{name}' sem float na API; usando 0.00-1.00.")

    weapon = (details.get("weapon") or {}).get("name") or name.split(" | ")[0].replace("★", "").strip()

    skins[key] = {
        "api_id": key,
        "name": f"{name} ({phase})" if phase else name,  # nome exibido mostra a fase
        "market_name": name,                              # no mercado a fase não aparece
        "base_weapon": weapon[:50],
        "image_url": entry.get("image") or details.get("image"),
        "min_float": min_float,
        "max_float": max_float,
        "rarity_name": rarity_name,
    }
    return key


# ======================================================================
# 3. PREÇOS DA STEAM (funções puras + consulta)
# ======================================================================

def parse_brl(texto):
    """Converte o preço da Steam em Decimal. Ex.: "R$ 1.234,56" -> Decimal("1234.56").
    Devolve None se não houver número (ex.: None, "", "--")."""
    if not texto:
        return None
    numeros = "".join(c for c in str(texto) if c.isdigit() or c in ",.")
    if not numeros:
        return None
    numeros = numeros.replace(".", "").replace(",", ".")    # padrão brasileiro
    try:
        valor = Decimal(numeros)
    except InvalidOperation:
        return None
    return rules.to_money(valor) if valor > 0 else None


def pick_steam_price(data):
    """Escolhe o preço de mercado da resposta da Steam.

    median_price = mediana das vendas das últimas 24 h (mais estável);
    se não houver vendas no dia, usa lowest_price (o anúncio mais barato agora).
    """
    if not data or not data.get("success"):
        return None
    return parse_brl(data.get("median_price")) or parse_brl(data.get("lowest_price"))


def fetch_steam_price(market_hash_name, timeout=30):
    """Consulta UM item no mercado da Steam.

    Devolve o JSON da Steam (dict). Item inexistente ou sem anúncio devolve
    {"success": False}. Lança SteamLimite (429) ou RuntimeError (rede).
    """
    url = STEAM_PRICE_URL.format(nome=urllib.parse.quote(market_hash_name, safe=""))
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8") or "null") or {"success": False}
    except urllib.error.HTTPError as error:
        if error.code == 429:
            raise SteamLimite() from error
        if error.code in (400, 404, 500):
            return {"success": False}      # a Steam responde 500 para nome que não existe
        raise RuntimeError(_describe_error(error)) from error
    except Exception as error:             # sem internet, tempo esgotado, JSON inválido
        raise RuntimeError(_describe_error(error)) from error


def plan_price_updates(case_rows, skin_rows, existing_skin_prices):
    """Ordem das consultas (função pura, testada em test_sync_market).

    case_rows:  [(id, market_name, price_source, price_updated_at)]
    skin_rows:  [(id, market_name, min_float, max_float, rarity_id)]
    existing_skin_prices: {(skin_id, wear): (source, updated_at)}

    Devolve uma lista de tarefas (tipo, id, desgaste, nome_no_mercado):
      1º itens que AINDA NÃO têm preço real: caixas, depois skins da raridade
         mais comum para a mais rara (são as que mais saem nas aberturas);
      2º itens que já têm preço real, do mais desatualizado para o mais novo.
    """
    pendentes, atualizar = [], []

    for case_id, market_name, source, updated_at in case_rows:
        tarefa = ("caixa", case_id, None, market_name)
        if source == rules.SOURCE_API:
            atualizar.append((updated_at, tarefa))
        else:
            pendentes.append(tarefa)

    ordenadas = sorted(skin_rows, key=lambda r: (r[4], r[1]))
    for skin_id, market_name, min_float, max_float, _rarity in ordenadas:
        for wear in rules.available_wears(min_float, max_float):
            tarefa = ("skin", skin_id, wear, rules.market_hash_name(market_name, wear))
            source, updated_at = existing_skin_prices.get((skin_id, wear), (None, None))
            if source == rules.SOURCE_API:
                atualizar.append((updated_at, tarefa))
            else:
                pendentes.append(tarefa)

    atualizar.sort(key=lambda par: str(par[0] or ""))
    return pendentes + [tarefa for _data, tarefa in atualizar]


# ======================================================================
# 4. GRAVAÇÃO NO BANCO
# ======================================================================

def save_catalog(database, caixas, skins, ligacoes):
    """Grava caixas, skins e o conteúdo das caixas numa ÚNICA transação."""
    connection = database.connect()
    cursor = connection.cursor(buffered=True)
    try:
        cursor.execute("SELECT id, name FROM rarities")
        rarity_ids = {name: rid for rid, name in cursor.fetchall()}
        faltando = {s["rarity_name"] for s in skins.values()} - set(rarity_ids)
        if faltando:
            raise RuntimeError(f"Raridades ausentes no banco: {faltando}. Rode o seed_base.sql.")

        for caixa in caixas:
            # caixa nova entra com preço estimado; o preço real vem da Steam depois
            cursor.execute(
                """
                INSERT INTO collections
                    (api_id, name, market_name, image_url, price_collection, price_source)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    name = VALUES(name),
                    market_name = VALUES(market_name),
                    image_url = VALUES(image_url)
                """,
                (caixa["api_id"], caixa["name"][:100], caixa["market_name"], caixa["image_url"],
                 rules.ESTIMATED_CASE_PRICE, rules.SOURCE_ESTIMATED)
            )

        for skin in skins.values():
            cursor.execute(
                """
                INSERT INTO skins_catalog
                    (api_id, name, market_name, base_weapon, image_url, min_float, max_float, rarity_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    name = VALUES(name),
                    market_name = VALUES(market_name),
                    base_weapon = VALUES(base_weapon),
                    image_url = VALUES(image_url),
                    min_float = VALUES(min_float),
                    max_float = VALUES(max_float),
                    rarity_id = VALUES(rarity_id)
                """,
                (skin["api_id"], skin["name"][:100], skin["market_name"], skin["base_weapon"],
                 skin["image_url"], skin["min_float"], skin["max_float"], rarity_ids[skin["rarity_name"]])
            )

        cursor.execute("SELECT id, api_id FROM collections WHERE api_id IS NOT NULL")
        case_ids = {api_id: cid for cid, api_id in cursor.fetchall()}
        cursor.execute("SELECT id, api_id FROM skins_catalog WHERE api_id IS NOT NULL")
        skin_ids = {api_id: sid for sid, api_id in cursor.fetchall()}

        # refaz o conteúdo das caixas importadas (a lista oficial pode mudar)
        for caixa in caixas:
            cursor.execute("DELETE FROM collection_items WHERE collection_id = %s", (case_ids[caixa["api_id"]],))
        for case_api_id, skin_api_id in ligacoes:
            cursor.execute(
                "INSERT INTO collection_items (collection_id, skin_catalog_id) VALUES (%s, %s)",
                (case_ids[case_api_id], skin_ids[skin_api_id])
            )

        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        database.disconnect(cursor, connection)


def fill_missing_estimates(database):
    """Garante que TODA skin, em todo desgaste possível, tenha um preço
    (estimado), para o jogo funcionar antes de a Steam terminar. Rápido: não usa internet."""
    agora = datetime.now().replace(microsecond=0)
    connection = database.connect()
    cursor = connection.cursor(buffered=True)
    try:
        cursor.execute("SELECT skin_catalog_id, wear FROM skin_prices")
        ja_tem = set(cursor.fetchall())
        cursor.execute(
            """
            SELECT s.id, s.min_float, s.max_float, r.name
            FROM skins_catalog s
            JOIN rarities r ON r.id = s.rarity_id
            WHERE s.market_name IS NOT NULL
            """
        )
        novos = 0
        for skin_id, min_float, max_float, rarity_name in cursor.fetchall():
            for wear in rules.available_wears(min_float, max_float):
                if (skin_id, wear) in ja_tem:
                    continue
                cursor.execute(
                    """
                    INSERT INTO skin_prices (skin_catalog_id, wear, price, source, updated_at)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (skin_id, wear, rules.estimated_price(rarity_name, wear), rules.SOURCE_ESTIMATED, agora)
                )
                novos += 1
        connection.commit()
        return novos
    except Exception:
        connection.rollback()
        raise
    finally:
        database.disconnect(cursor, connection)


def load_price_plan(database):
    """Lê do banco o que precisa de preço e devolve a lista ordenada de tarefas."""
    connection = database.connect()
    cursor = connection.cursor(buffered=True)
    try:
        cursor.execute(
            "SELECT id, market_name, price_source, price_updated_at FROM collections WHERE market_name IS NOT NULL"
        )
        case_rows = cursor.fetchall()
        cursor.execute(
            "SELECT id, market_name, min_float, max_float, rarity_id FROM skins_catalog WHERE market_name IS NOT NULL"
        )
        skin_rows = cursor.fetchall()
        cursor.execute("SELECT skin_catalog_id, wear, source, updated_at FROM skin_prices")
        existing = {(sid, wear): (source, updated) for sid, wear, source, updated in cursor.fetchall()}
    finally:
        database.disconnect(cursor, connection)
    return plan_price_updates(case_rows, skin_rows, existing)


def update_prices_from_steam(database, tarefas, fetch=None, sleep=None):
    """Consulta a Steam item por item e grava cada preço real (com histórico).

    Salva a cada SALVAR_A_CADA itens: se a execução for interrompida (Ctrl+C,
    queda de internet, limite da Steam), o que já foi consultado não se perde.
    Devolve um dicionário com as contagens e o motivo da parada (se houver).
    """
    fetch = fetch or fetch_steam_price      # nos testes dá para trocar por uma Steam "de mentira"
    sleep = sleep or time.sleep
    total = {"reais": 0, "sem_anuncio": 0, "falhas": 0, "consultados": 0, "parada": None, "motivo": None}
    connection = database.connect()
    cursor = connection.cursor(buffered=True)
    falhas_seguidas = 0
    inicio = time.time()
    try:
        for numero, (tipo, item_id, wear, nome) in enumerate(tarefas, start=1):
            # --- consulta (com pausas automáticas se a Steam pedir) ---
            dados, pausas = None, 0
            while True:
                try:
                    dados = fetch(nome)
                    falhas_seguidas = 0
                    break
                except SteamLimite:
                    pausas += 1
                    if pausas > STEAM_MAX_PAUSAS:
                        total["parada"] = "a Steam limitou as consultas; rode de novo daqui a uns 10 minutos"
                        total["motivo"] = "limite"
                        break
                    print(f"  ... a Steam pediu uma pausa; aguardando {STEAM_PAUSA_LIMITE}s "
                          f"({pausas}/{STEAM_MAX_PAUSAS})")
                    connection.commit()
                    sleep(STEAM_PAUSA_LIMITE)
                except RuntimeError as error:
                    falhas_seguidas += 1
                    total["falhas"] += 1
                    if falhas_seguidas >= STEAM_MAX_FALHAS:
                        total["parada"] = f"{STEAM_MAX_FALHAS} erros de rede seguidos ({error})"
                        total["motivo"] = "rede"
                    break
            if total["parada"]:
                break
            total["consultados"] += 1

            # --- gravação ---
            preco = pick_steam_price(dados)
            agora = datetime.now().replace(microsecond=0)
            if preco is None:
                if dados is not None:
                    total["sem_anuncio"] += 1      # fica com o preço que já tinha (estimado ou real)
            elif tipo == "caixa":
                cursor.execute(
                    """
                    UPDATE collections
                    SET price_collection = %s, price_source = %s, price_updated_at = %s
                    WHERE id = %s
                    """,
                    (preco, rules.SOURCE_API, agora, item_id)
                )
                cursor.execute(
                    "INSERT INTO price_history (collection_id, price, source, captured_at) VALUES (%s, %s, %s, %s)",
                    (item_id, preco, rules.SOURCE_API, agora)
                )
                total["reais"] += 1
            else:
                cursor.execute(
                    """
                    INSERT INTO skin_prices
                        (skin_catalog_id, wear, price, avg_7d, avg_30d, source, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        price = VALUES(price),
                        source = VALUES(source),
                        updated_at = VALUES(updated_at)
                    """,
                    (item_id, wear, preco, None, None, rules.SOURCE_API, agora)
                )
                cursor.execute(
                    """
                    INSERT INTO price_history (skin_catalog_id, wear, price, source, captured_at)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (item_id, wear, preco, rules.SOURCE_API, agora)
                )
                total["reais"] += 1

            if numero % SALVAR_A_CADA == 0 or numero == len(tarefas):
                connection.commit()
                restante = (time.time() - inicio) / numero * (len(tarefas) - numero) / 60
                preco_txt = rules.format_money(preco) if preco else "sem anúncio"
                print(f"  [{numero}/{len(tarefas)}] {nome}: {preco_txt}  (faltam ~{restante:.0f} min)")

            if numero < len(tarefas):
                sleep(STEAM_INTERVALO)

        connection.commit()
        return total

    except KeyboardInterrupt:
        connection.commit()                 # salva o que já foi consultado
        total["parada"] = "interrompido pelo usuário (Ctrl+C); o progresso foi salvo"
        total["motivo"] = "ctrlc"
        return total
    except Exception:
        connection.rollback()
        raise
    finally:
        database.disconnect(cursor, connection)


def wait_before_next_pass(total):
    """Modo contínuo: quantos segundos esperar antes da próxima passada.
    Devolve None quando é para encerrar (o usuário apertou Ctrl+C)."""
    motivo = total.get("motivo")
    if motivo == "ctrlc":
        return None
    if motivo == "limite":
        return PAUSA_APOS_LIMITE
    if motivo == "rede":
        return PAUSA_APOS_REDE
    return PAUSA_ENTRE_PASSADAS


# ======================================================================
# 5. IMAGENS (opcional)
# ======================================================================

def download_images(database):
    """Baixa a imagem de cada caixa/skin para app/assets/items (pula as que já existem)."""
    connection = database.connect()
    cursor = connection.cursor(buffered=True)
    try:
        cursor.execute(
            """
            SELECT api_id, image_url FROM collections WHERE api_id IS NOT NULL AND image_url IS NOT NULL
            UNION ALL
            SELECT api_id, image_url FROM skins_catalog WHERE api_id IS NOT NULL AND image_url IS NOT NULL
            """
        )
        rows = cursor.fetchall()
    finally:
        database.disconnect(cursor, connection)

    ITEM_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    baixadas = puladas = falhas = 0
    for api_id, url in rows:
        destino = item_image_path(api_id)
        if destino.exists():
            puladas += 1
            continue
        # Imagens da Steam aceitam um sufixo de tamanho: 256x256 é suficiente e leve.
        if "/economy/image/" in url and not url.rstrip("/").endswith("f"):
            url = url.rstrip("/") + "/256fx256f"
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=30) as response:
                destino.write_bytes(response.read())
            baixadas += 1
            time.sleep(0.05)   # gentileza com o servidor
        except (urllib.error.URLError, TimeoutError, OSError):
            falhas += 1
    return baixadas, puladas, falhas


def _print_total(total):
    print(
        f"    {total['reais']} preços reais gravados | {total['sem_anuncio']} sem anúncio na Steam | "
        f"{total['falhas']} falhas de rede"
    )
    if total["parada"]:
        print(f"  ! Parou antes do fim: {total['parada']}.")


def run_continuous(database, limite=None, sleep=None, max_passadas=None):
    """--continuo: repete as passadas de preço até o usuário apertar Ctrl+C.

    Cada passada consulta todos os itens (primeiro os sem preço real, depois
    os mais desatualizados) e grava um ponto novo em price_history. Deixando
    rodando um fim de semana, cada item ganha dezenas de pontos no histórico.
    Se a Steam limitar ou a internet cair, ele espera e continua sozinho.
    max_passadas existe só para os testes.
    """
    sleep = sleep or time.sleep
    passada = 0
    print("3/4 Modo contínuo: atualizando preços sem parar. Ctrl+C encerra (o progresso fica salvo).")
    print("    Deixe o XAMPP ligado e o computador sem suspender (Configurações > Energia).")
    while True:
        passada += 1
        tarefas = load_price_plan(database)
        if limite:
            tarefas = tarefas[:limite]
        inicio = datetime.now().strftime("%d/%m %H:%M")
        print(f"\n=== Passada {passada} ({inicio}): {len(tarefas)} preços, "
              f"~{len(tarefas) * STEAM_INTERVALO / 60:.0f} min ===")
        total = update_prices_from_steam(database, tarefas, sleep=sleep)
        _print_total(total)

        espera = wait_before_next_pass(total)
        if espera is None or (max_passadas and passada >= max_passadas):
            print(f"\nModo contínuo encerrado depois de {passada} passada(s).")
            return passada
        print(f"    Próxima passada em {espera // 60} min (Ctrl+C para encerrar).")
        try:
            sleep(espera)
        except KeyboardInterrupt:
            print(f"\nModo contínuo encerrado depois de {passada} passada(s).")
            return passada


# ======================================================================
# 6. PROGRAMA PRINCIPAL
# ======================================================================

def main(argv=None):
    try:
        sys.stdout.reconfigure(errors="replace")   # evita erro com "★" em consoles antigos
    except (AttributeError, ValueError):
        pass

    parser = argparse.ArgumentParser(description="Importa caixas, skins e preços reais do CS para o banco.")
    parser.add_argument("--listar", action="store_true", help="lista as caixas disponíveis na API e sai")
    parser.add_argument("--caixas", nargs="+", metavar="NOME", help="nomes das caixas a importar")
    parser.add_argument("--todas", action="store_true", help="importa todas as caixas da API")
    parser.add_argument("--imagens", action="store_true", help="baixa as imagens para app/assets/items")
    parser.add_argument("--sem-precos", action="store_true", help="não consulta a Steam (preços estimados)")
    parser.add_argument("--so-precos", action="store_true", help="só atualiza preços (não baixa o catálogo)")
    parser.add_argument("--limite", type=int, metavar="N", help="consulta no máximo N preços nesta execução")
    parser.add_argument("--continuo", action="store_true",
                        help="repete a consulta de preços sem parar (para montar o histórico); Ctrl+C encerra")
    args = parser.parse_args(argv)

    caixas, skins, ligacoes = [], {}, []
    if not args.so_precos:
        print("1/4 Baixando catálogo (CSGO-API)...")
        crates, _ = download(CATALOG_URL.format(arquivo="crates.json"), "crates.json")
        all_cases = only_cases(crates)

        if args.listar:
            print(f"\n{len(all_cases)} caixas disponíveis:")
            for case in sorted(all_cases, key=lambda c: c.get("first_sale_date") or ""):
                print(f"  {case.get('first_sale_date') or '----/--/--'}  {case['name']}")
            return 0

        if args.todas:
            selected, warnings = all_cases, []
        else:
            selected, warnings = select_cases(all_cases, args.caixas or CAIXAS_PADRAO)
        for warning in warnings:
            print(f"  ! {warning}")
        if not selected:
            print("Nenhuma caixa selecionada. Use --listar para ver os nomes.")
            return 1

        skins_json, _ = download(CATALOG_URL.format(arquivo="skins.json"), "skins.json")
        by_id, by_name = index_skins(skins_json)
        caixas, skins, ligacoes, avisos = build_catalog(selected, by_id, by_name)
        for aviso in avisos[:15]:
            print(f"  ! {aviso}")
        if len(avisos) > 15:
            print(f"  ! ... e mais {len(avisos) - 15} avisos")
    else:
        print("1/4 Catálogo: pulado (--so-precos).")

    # Import aqui (e não no topo) para o --listar funcionar mesmo sem banco configurado.
    from app.core.database import Database
    database = Database()

    if caixas:
        print(f"2/4 Gravando {len(caixas)} caixas e {len(skins)} skins no banco...")
        save_catalog(database, caixas, skins, ligacoes)
    else:
        print("2/4 Gravação do catálogo: pulada.")
    estimados = fill_missing_estimates(database)
    if estimados:
        print(f"    {estimados} preços estimados criados para itens novos (até a Steam responder).")

    total, n_tarefas = None, 0
    if args.sem_precos:
        print("3/4 Preços: pulado (--sem-precos).")
    elif args.continuo:
        run_continuous(database, args.limite)
        return 0
    else:
        tarefas = load_price_plan(database)
        if args.limite:
            tarefas = tarefas[:args.limite]
        n_tarefas = len(tarefas)
        minutos = n_tarefas * STEAM_INTERVALO / 60
        print(f"3/4 Consultando {len(tarefas)} preços em R$ no mercado da Steam (~{minutos:.0f} min).")
        print("    Pode interromper com Ctrl+C a qualquer momento: o progresso fica salvo e")
        print("    a próxima execução continua do que falta.")
        total = update_prices_from_steam(database, tarefas)
        _print_total(total)

    if args.imagens:
        print("4/4 Baixando imagens (pode demorar alguns minutos)...")
        baixadas, puladas, falhas = download_images(database)
        print(f"    {baixadas} baixadas | {puladas} já existiam | {falhas} falharam")
    else:
        print("4/4 Imagens: pulado (use --imagens para baixar).")

    if caixas:
        print("\nResumo do conteúdo importado:")
        for caixa in caixas:
            conteudo = [skins[s]["rarity_name"] for c, s in ligacoes if c == caixa["api_id"]]
            por_raridade = ", ".join(f"{n}: {conteudo.count(n)}" for n in dict.fromkeys(conteudo))
            print(f"  {caixa['name']}: {len(conteudo)} itens ({por_raridade})")

    if total is not None and n_tarefas and total["reais"] == 0 and (total["parada"] or total["falhas"]):
        # Aviso bem visível: houve problema (limite da Steam, rede ou interrupção) e nada foi atualizado.
        print("\n" + "!" * 70)
        print("ATENÇÃO: nenhum preço real foi obtido nesta execução.")
        print("O jogo funciona com os preços estimados, mas veja o motivo acima ('Parou antes do fim').")
        print("!" * 70)
        return 2
    print("\nPronto!")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nCancelado.")
        sys.exit(1)
    except Exception as error:   # mensagem amigável em vez de traceback gigante
        print(f"\nERRO: {error}")
        sys.exit(1)
