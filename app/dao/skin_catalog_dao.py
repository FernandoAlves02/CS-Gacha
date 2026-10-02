from app.core.game_rules import WEAR_ORDER
from app.dao.base_dao import Read_Only_DAO
from app.models.market_price import Market_Price
from app.models.rarity import Rarity
from app.models.skin_catalog import Skin_Catalog

# ----------------------------------------------------------------------
# Colunas padrão de uma skin + sua raridade (sempre nesta ordem).
# Reaproveitadas pelo Collection_DAO e pelo Inventory_DAO, para que todas as
# consultas montem o objeto Skin_Catalog do mesmo jeito.
# Use sempre com: FROM skins_catalog s JOIN rarities r ON r.id = s.rarity_id
# ----------------------------------------------------------------------
SKIN_COLUMNS = """
    s.id, s.name, s.base_weapon, s.rarity_id, s.min_float, s.max_float,
    s.api_id, s.market_name, s.image_url, s.model_3d_url,
    r.id, r.name, r.probability, r.color
"""
SKIN_COLUMN_COUNT = 14


def skin_from_row(row, start=0):
    """Monta um Skin_Catalog (com Rarity) a partir de uma linha com SKIN_COLUMNS."""
    d = row[start:start + SKIN_COLUMN_COUNT]
    rarity = Rarity(d[10], d[11], d[12], d[13])
    return Skin_Catalog(d[0], d[1], d[2], d[3], d[4], d[5], d[6], d[7], d[8], d[9], rarity)


# Ordena os desgastes do melhor para o pior (Factory New ... Battle-Scarred).
WEAR_ORDER_SQL = "CASE p.wear " + " ".join(
    f"WHEN '{wear}' THEN {posicao}" for posicao, wear in enumerate(WEAR_ORDER)
) + f" ELSE {len(WEAR_ORDER)} END"

PRICE_COLUMNS = "p.skin_catalog_id, p.wear, p.price, p.avg_7d, p.avg_30d, p.source, p.updated_at"


def price_from_row(row, start=0):
    d = row[start:start + 7]
    return Market_Price(d[0], d[1], d[2], d[3], d[4], d[5], d[6])


class Skin_Catalog_DAO(Read_Only_DAO):
    """Leitura do catálogo de skins e dos preços do mercado."""

    def __init__(self, database):
        super().__init__(database)

    def get_all(self):
        connection, cursor = self.connect()

        try:
            sql = f"""
                    SELECT {SKIN_COLUMNS}
                    FROM skins_catalog s
                    JOIN rarities r ON r.id = s.rarity_id
                    ORDER BY s.name
                  """

            cursor.execute(sql)

            return [skin_from_row(data) for data in cursor.fetchall()]

        finally:
            self.disconnect(cursor, connection)

    def get_by_id(self, entity_id):
        connection, cursor = self.connect()

        try:
            sql = f"""
                    SELECT {SKIN_COLUMNS}
                    FROM skins_catalog s
                    JOIN rarities r ON r.id = s.rarity_id
                    WHERE s.id = %s
                  """

            cursor.execute(sql, (entity_id,))

            data = cursor.fetchone()

            return skin_from_row(data) if data else None

        finally:
            self.disconnect(cursor, connection)

    # ----------------------------------------------------------
    # PREÇOS
    # ----------------------------------------------------------

    def get_prices(self, skin_catalog_id):
        """Preço atual da skin em cada desgaste, do melhor para o pior."""
        connection, cursor = self.connect()

        try:
            sql = f"""
                    SELECT {PRICE_COLUMNS}
                    FROM skin_prices p
                    WHERE p.skin_catalog_id = %s
                    ORDER BY {WEAR_ORDER_SQL}
                  """

            cursor.execute(sql, (skin_catalog_id,))

            return [price_from_row(data) for data in cursor.fetchall()]

        finally:
            self.disconnect(cursor, connection)

    def get_price(self, skin_catalog_id, wear):
        """Preço atual de UM desgaste (ou None se a skin não está à venda nele)."""
        connection, cursor = self.connect()

        try:
            sql = f"""
                    SELECT {PRICE_COLUMNS}
                    FROM skin_prices p
                    WHERE p.skin_catalog_id = %s
                      AND p.wear = %s
                  """

            cursor.execute(sql, (skin_catalog_id, wear))

            data = cursor.fetchone()

            return price_from_row(data) if data else None

        finally:
            self.disconnect(cursor, connection)

    def get_market_listings(self, search="", limit=50, offset=0, rarity_id=None):
        """Skins à venda no mercado: lista de (Skin_Catalog, Market_Price).

        Cada desgaste é um anúncio separado, como no mercado da Steam
        ("AK-47 | Redline (Field-Tested)" e "(Minimal Wear)" são itens diferentes).
        search: filtra pelo nome (parte do texto). limit/offset: paginação.
        """
        connection, cursor = self.connect()

        try:
            filtros = ["s.name LIKE %s"]
            params = [f"%{(search or '').strip()}%"]
            if rarity_id is not None:
                filtros.append("s.rarity_id = %s")
                params.append(rarity_id)

            sql = f"""
                    SELECT {SKIN_COLUMNS}, {PRICE_COLUMNS}
                    FROM skin_prices p
                    JOIN skins_catalog s ON s.id = p.skin_catalog_id
                    JOIN rarities r ON r.id = s.rarity_id
                    WHERE {" AND ".join(filtros)}
                    ORDER BY s.name, {WEAR_ORDER_SQL}
                    LIMIT %s OFFSET %s
                  """
            params.extend([int(limit), int(offset)])

            cursor.execute(sql, tuple(params))

            return [
                (skin_from_row(data), price_from_row(data, SKIN_COLUMN_COUNT))
                for data in cursor.fetchall()
            ]

        finally:
            self.disconnect(cursor, connection)

    def count_market_listings(self, search="", rarity_id=None):
        """Quantos anúncios existem (para calcular o número de páginas)."""
        connection, cursor = self.connect()

        try:
            filtros = ["s.name LIKE %s"]
            params = [f"%{(search or '').strip()}%"]
            if rarity_id is not None:
                filtros.append("s.rarity_id = %s")
                params.append(rarity_id)

            sql = f"""
                    SELECT COUNT(*)
                    FROM skin_prices p
                    JOIN skins_catalog s ON s.id = p.skin_catalog_id
                    WHERE {" AND ".join(filtros)}
                  """

            cursor.execute(sql, tuple(params))

            return int(cursor.fetchone()[0])

        finally:
            self.disconnect(cursor, connection)

    def get_price_history(self, skin_catalog_id, wear, limit=30):
        """Histórico de preço de uma skin em um desgaste: lista de (data, preço),
        da mais antiga para a mais nova (pronta para desenhar um gráfico)."""
        connection, cursor = self.connect()

        try:
            sql = """
                    SELECT captured_at, price
                    FROM price_history
                    WHERE skin_catalog_id = %s
                      AND wear = %s
                    ORDER BY captured_at DESC, id DESC
                    LIMIT %s
                  """

            cursor.execute(sql, (skin_catalog_id, wear, int(limit)))

            return list(reversed(cursor.fetchall()))

        finally:
            self.disconnect(cursor, connection)

    def get_history_for_listings(self, listings, points_per_listing=60):
        """Histórico RECENTE de vários anúncios numa consulta só (para o ▲▼ de uma página do mercado).

        listings: lista de (skin_catalog_id, desgaste).
        Devolve {(skin_catalog_id, desgaste): [(data, preço), ...]}, do mais antigo
        para o mais novo, com no máximo `points_per_listing` pontos por anúncio
        (60 passadas do coletor ~ 3 dias: sobra para a variação de 24 h e a
        consulta não fica mais lenta à medida que o histórico cresce).
        Anúncio sem histórico fica com lista vazia.
        """
        pares = list(dict.fromkeys(listings))       # sem repetidos, mantendo a ordem
        if not pares:
            return {}
        ids = sorted({skin_id for skin_id, _wear in pares})
        wears = sorted({wear for _skin_id, wear in pares})

        connection, cursor = self.connect()

        try:
            # ROW_NUMBER() numera os pontos de cada anúncio do mais novo (1) para o
            # mais antigo; o SELECT de fora fica só com os N mais novos de cada um.
            sql = f"""
                    SELECT skin_catalog_id, wear, captured_at, price
                    FROM (
                        SELECT skin_catalog_id, wear, captured_at, price, id,
                               ROW_NUMBER() OVER (
                                   PARTITION BY skin_catalog_id, wear
                                   ORDER BY captured_at DESC, id DESC
                               ) AS ordem
                        FROM price_history
                        WHERE skin_catalog_id IN ({", ".join(["%s"] * len(ids))})
                          AND wear IN ({", ".join(["%s"] * len(wears))})
                    ) recentes
                    WHERE ordem <= %s
                    ORDER BY captured_at, id
                  """

            cursor.execute(sql, tuple(ids) + tuple(wears) + (int(points_per_listing),))

            historico = {par: [] for par in pares}
            for skin_id, wear, data, preco in cursor.fetchall():
                pontos = historico.get((skin_id, wear))
                if pontos is not None:              # ignora combinações que não estão na página
                    pontos.append((data, preco))
            return historico

        finally:
            self.disconnect(cursor, connection)
