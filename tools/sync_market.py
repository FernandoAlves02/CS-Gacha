"""IMPORTADOR DO MERCADO (Fase 2): traz caixas, skins e preços REAIS do CS para o banco.

De onde vêm os dados
--------------------
1. CATÁLOGO (caixas, conteúdo de cada caixa, raridade, float mínimo/máximo,
   imagens): CSGO-API do ByMykel (arquivos JSON públicos no GitHub, sem chave).
2. PREÇOS em reais + médias de venda de 7 e 30 dias: API pública da Skinport
   (sem chave, limite de 8 chamadas a cada 5 minutos; usamos 2 por execução).
   A Skinport EXIGE compressão Brotli, por isso a biblioteca "brotli".

O jogo NUNCA acessa a internet: ele só lê o banco. Este script é rodado
antes (no seu PC e no do professor) para preencher/atualizar o banco.
Cada vez que roda, os preços mudam conforme o mercado real e uma linha nova
vai para price_history (o histórico de preços).

Como usar (na raiz do projeto, com o .venv ativado)
-----------------------------------------------------
    python tools/sync_market.py                 importa as caixas da lista CAIXAS_PADRAO
    python tools/sync_market.py --listar        mostra todas as caixas disponíveis na API
    python tools/sync_market.py --caixas "Chroma Case" "Fracture Case"
    python tools/sync_market.py --todas         importa TODAS as caixas (demora mais)
    python tools/sync_market.py --imagens       também baixa as imagens (app/assets/items)
    python tools/sync_market.py --sem-precos    só catálogo (preços estimados)

Pode rodar quantas vezes quiser: ele atualiza o que já existe (não duplica).
Se a internet ou a API falhar, usa a última cópia salva em tools/cache e,
para itens sem preço, um preço estimado (game_rules.estimated_price).
"""
import argparse
import difflib
import gzip
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from decimal import Decimal
from pathlib import Path

# Permite rodar "python tools/sync_market.py" a partir da raiz do projeto.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core import game_rules as rules                              # noqa: E402
from app.core.paths import ITEM_IMAGES_DIR, TOOLS_CACHE_DIR, item_image_path  # noqa: E402

try:
    import brotli          # pip install brotli (só este script usa)
except ImportError:
    brotli = None

CATALOG_URL = "https://raw.githubusercontent.com/ByMykel/CSGO-API/main/public/api/en/{arquivo}"
SKINPORT_ITEMS_URL = "https://api.skinport.com/v1/items?app_id=730&currency=BRL&tradable=0"
SKINPORT_HISTORY_URL = "https://api.skinport.com/v1/sales/history?app_id=730&currency=BRL"
USER_AGENT = "CSGacha/1.0 (projeto integrador SENAC)"

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


# ======================================================================
# 1. DOWNLOAD (com cópia local em tools/cache)
# ======================================================================

def download(url, cache_name, needs_brotli=False, timeout=120):
    """Baixa um JSON. Se falhar, usa a última cópia salva em tools/cache.

    Devolve (dados, origem) onde origem é "internet" ou "cache".
    Lança RuntimeError se não houver nem internet nem cópia local.
    """
    cache_file = TOOLS_CACHE_DIR / cache_name
    try:
        if needs_brotli and brotli is None:
            raise RuntimeError("biblioteca brotli não instalada (pip install brotli)")

        request = urllib.request.Request(url, headers={
            "User-Agent": USER_AGENT,
            "Accept-Encoding": "br" if needs_brotli else "gzip",
            "Accept": "application/json",
        })
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            encoding = (response.headers.get("Content-Encoding") or "").lower()

        if encoding == "br":
            raw = brotli.decompress(raw)
        elif encoding == "gzip":
            raw = gzip.decompress(raw)

        data = json.loads(raw.decode("utf-8"))
        TOOLS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(json.dumps(data), encoding="utf-8")
        return data, "internet"

    except Exception as error:   # sem internet, API fora do ar, JSON inválido, erro do brotli...
        motivo = _describe_error(error)
        if cache_file.exists():
            data_cache = datetime.fromtimestamp(cache_file.stat().st_mtime).strftime("%d/%m %H:%M")
            print(f"  ! Falha ao baixar ({motivo}). Usando a cópia local de {data_cache}.")
            return json.loads(cache_file.read_text(encoding="utf-8")), "cache"
        raise RuntimeError(f"Não foi possível baixar {url} ({motivo}) e não há cópia local.") from error


def _describe_error(error):
    """Mensagem curta e COMPLETA do erro, para sabermos exatamente o que a API respondeu."""
    if isinstance(error, urllib.error.HTTPError):
        if error.code == 429:
            return "HTTP 429: limite de chamadas da API; aguarde 5 minutos"
        detalhe = ""
        try:   # o corpo da resposta de erro costuma dizer o motivo
            corpo = error.read()
            codificacao = (error.headers.get("Content-Encoding") or "").lower()
            if codificacao == "br" and brotli is not None:
                corpo = brotli.decompress(corpo)
            elif codificacao == "gzip":
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
# 3. PREÇOS (função pura)
# ======================================================================

def index_prices(items_json, history_json):
    """Junta /v1/items e /v1/sales/history da Skinport em
    {market_hash_name: (preço atual, média 7 dias, média 30 dias)}.

    Preço atual = preço sugerido de mercado; se não houver, a mediana das
    vendas dos últimos 7 dias; depois a mediana e o menor preço dos anúncios.
    """
    history = {h.get("market_hash_name"): h for h in history_json or [] if h.get("market_hash_name")}
    prices = {}
    for item in items_json or []:
        name = item.get("market_hash_name")
        if not name:
            continue
        sales = history.get(name, {})
        last7 = sales.get("last_7_days") or {}
        last30 = sales.get("last_30_days") or {}
        price = _first_positive(
            item.get("suggested_price"), last7.get("median"), item.get("median_price"), item.get("min_price")
        )
        if price is None:
            continue
        prices[name] = (price, _first_positive(last7.get("avg")), _first_positive(last30.get("avg")))
    return prices


def _first_positive(*values):
    for value in values:
        if value is not None:
            money = rules.to_money(value)
            if money > 0:
                return money
    return None


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
            # caixa nova entra com preço estimado; o preço real vem em update_prices
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


def update_prices(database, prices):
    """Atualiza os preços de TODAS as skins e caixas que estão no banco.

    - Item com preço na API: grava o preço real e uma linha no histórico.
    - Item sem preço na API e que ainda não tem preço: grava o estimado.
    - Item sem preço na API que já tinha preço: mantém o antigo (não troca
      um preço real por um estimado só porque a API falhou desta vez).
    Devolve um dicionário com as contagens.
    """
    agora = datetime.now().replace(microsecond=0)
    total = {"reais": 0, "estimados": 0, "mantidos": 0, "caixas_reais": 0}

    connection = database.connect()
    cursor = connection.cursor(buffered=True)
    try:
        cursor.execute("SELECT skin_catalog_id, wear FROM skin_prices")
        ja_tem_preco = set(cursor.fetchall())

        cursor.execute(
            """
            SELECT s.id, s.market_name, s.min_float, s.max_float, r.name
            FROM skins_catalog s
            JOIN rarities r ON r.id = s.rarity_id
            WHERE s.market_name IS NOT NULL
            """
        )
        for skin_id, market_name, min_float, max_float, rarity_name in cursor.fetchall():
            for wear in rules.available_wears(min_float, max_float):
                found = prices.get(rules.market_hash_name(market_name, wear))
                if found:
                    price, avg_7d, avg_30d = found
                    source = rules.SOURCE_API
                    total["reais"] += 1
                elif (skin_id, wear) in ja_tem_preco:
                    total["mantidos"] += 1
                    continue
                else:
                    price, avg_7d, avg_30d = rules.estimated_price(rarity_name, wear), None, None
                    source = rules.SOURCE_ESTIMATED
                    total["estimados"] += 1

                cursor.execute(
                    """
                    INSERT INTO skin_prices
                        (skin_catalog_id, wear, price, avg_7d, avg_30d, source, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        price = VALUES(price),
                        avg_7d = VALUES(avg_7d),
                        avg_30d = VALUES(avg_30d),
                        source = VALUES(source),
                        updated_at = VALUES(updated_at)
                    """,
                    (skin_id, wear, price, avg_7d, avg_30d, source, agora)
                )
                if source == rules.SOURCE_API:
                    cursor.execute(
                        """
                        INSERT INTO price_history (skin_catalog_id, wear, price, source, captured_at)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (skin_id, wear, price, source, agora)
                    )

        cursor.execute("SELECT id, market_name FROM collections WHERE market_name IS NOT NULL")
        for case_id, market_name in cursor.fetchall():
            found = prices.get(market_name)
            if not found:
                continue
            price = found[0]
            cursor.execute(
                """
                UPDATE collections
                SET price_collection = %s, price_source = %s, price_updated_at = %s
                WHERE id = %s
                """,
                (price, rules.SOURCE_API, agora, case_id)
            )
            cursor.execute(
                """
                INSERT INTO price_history (collection_id, price, source, captured_at)
                VALUES (%s, %s, %s, %s)
                """,
                (case_id, price, rules.SOURCE_API, agora)
            )
            total["caixas_reais"] += 1

        connection.commit()
        return total
    except Exception:
        connection.rollback()
        raise
    finally:
        database.disconnect(cursor, connection)


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
    parser.add_argument("--sem-precos", action="store_true", help="não consulta a Skinport (preços estimados)")
    args = parser.parse_args(argv)

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

    # Import aqui (e não no topo) para o --listar funcionar mesmo sem banco configurado.
    from app.core.database import Database
    database = Database()

    print(f"2/4 Gravando {len(caixas)} caixas e {len(skins)} skins no banco...")
    save_catalog(database, caixas, skins, ligacoes)

    prices = {}
    if args.sem_precos:
        print("3/4 Preços: pulado (--sem-precos). Itens novos recebem preço estimado.")
    else:
        print("3/4 Baixando preços em R$ (Skinport)...")
        try:
            items_json, _ = download(SKINPORT_ITEMS_URL, "skinport_items.json", needs_brotli=True)
        except RuntimeError as error:
            items_json = None
            print(f"  ! Sem preços reais nesta execução: {error}")
        if items_json is not None:
            # O histórico só traz as médias de 7/30 dias: se falhar, os preços atuais continuam valendo.
            try:
                history_json, _ = download(SKINPORT_HISTORY_URL, "skinport_history.json", needs_brotli=True)
            except RuntimeError as error:
                history_json = []
                print(f"  ! Médias de 7/30 dias indisponíveis nesta execução: {error}")
            prices = index_prices(items_json, history_json)
    total = update_prices(database, prices)
    print(
        f"    skins: {total['reais']} preços reais | {total['estimados']} estimados | "
        f"{total['mantidos']} mantidos | caixas com preço real: {total['caixas_reais']}"
    )
    sem_preco_real = not args.sem_precos and total["reais"] == 0 and total["caixas_reais"] == 0

    if args.imagens:
        print("4/4 Baixando imagens (pode demorar alguns minutos)...")
        baixadas, puladas, falhas = download_images(database)
        print(f"    {baixadas} baixadas | {puladas} já existiam | {falhas} falharam")
    else:
        print("4/4 Imagens: pulado (use --imagens para baixar).")

    print("\nResumo do conteúdo importado:")
    for caixa in caixas:
        conteudo = [skins[s]["rarity_name"] for c, s in ligacoes if c == caixa["api_id"]]
        por_raridade = ", ".join(f"{n}: {conteudo.count(n)}" for n in dict.fromkeys(conteudo))
        print(f"  {caixa['name']}: {len(conteudo)} itens ({por_raridade})")

    if sem_preco_real:
        # Aviso bem visível: o catálogo foi importado, mas os preços NÃO são reais.
        print("\n" + "!" * 70)
        print("ATENÇÃO: nenhum preço real foi obtido nesta execução.")
        print("O catálogo foi importado, mas os itens novos estão com preço ESTIMADO.")
        print("O motivo está na linha 'Sem preços reais' acima.")
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
