from app.dao.base_dao import Read_Only_DAO
from app.dao.skin_catalog_dao import SKIN_COLUMNS, skin_from_row
from app.models.collection import Collection

# Colunas padrão de uma caixa (sempre nesta ordem). Reaproveitadas pelo Inventory_DAO.
# Use sempre com: FROM collections c
COLLECTION_COLUMNS = """
    c.id, c.name, c.price_collection, c.api_id, c.market_name,
    c.image_url, c.price_source, c.price_updated_at
"""
COLLECTION_COLUMN_COUNT = 8


def collection_from_row(row, start=0, quantity=None):
    """Monta um Collection a partir de uma linha com COLLECTION_COLUMNS."""
    d = row[start:start + COLLECTION_COLUMN_COUNT]
    return Collection(d[0], d[1], d[2], d[3], d[4], d[5], d[6], d[7], quantity)


class Collection_DAO(Read_Only_DAO):
    """Leitura das caixas ("collections") e do conteúdo de cada uma."""

    def __init__(self, database):
        super().__init__(database)

    def get_all(self):
        """Caixas à venda no mercado: só as que têm conteúdo cadastrado
        (uma caixa sem itens não pode ser aberta)."""
        connection, cursor = self.connect()

        try:
            sql = f"""
                    SELECT {COLLECTION_COLUMNS}
                    FROM collections c
                    WHERE EXISTS (
                        SELECT 1
                        FROM collection_items ci
                        WHERE ci.collection_id = c.id
                    )
                    ORDER BY c.name
                  """

            cursor.execute(sql)

            return [collection_from_row(data) for data in cursor.fetchall()]

        finally:
            self.disconnect(cursor, connection)

    def get_by_id(self, entity_id):
        connection, cursor = self.connect()

        try:
            sql = f"""
                    SELECT {COLLECTION_COLUMNS}
                    FROM collections c
                    WHERE c.id = %s
                  """

            cursor.execute(sql, (entity_id,))

            data = cursor.fetchone()

            return collection_from_row(data) if data else None

        finally:
            self.disconnect(cursor, connection)

    def get_items(self, collection_id):
        """Tabela de drops da caixa: todas as skins que podem sair dela, já com
        a raridade (e a probabilidade da raridade) carregada.

        É a primeira etapa da abertura: "pegar a informação de qual coleção
        pertence a caixa (id) para pegar a tabela de drops correta".
        """
        connection, cursor = self.connect()

        try:
            sql = f"""
                    SELECT {SKIN_COLUMNS}
                    FROM collection_items ci
                    JOIN skins_catalog s ON s.id = ci.skin_catalog_id
                    JOIN rarities r ON r.id = s.rarity_id
                    WHERE ci.collection_id = %s
                    ORDER BY s.rarity_id, s.name
                  """

            cursor.execute(sql, (collection_id,))

            return [skin_from_row(data) for data in cursor.fetchall()]

        finally:
            self.disconnect(cursor, connection)

    def get_price_history(self, collection_id, limit=30):
        """Histórico de preço da caixa: lista de (data, preço), da mais antiga para a mais nova."""
        connection, cursor = self.connect()

        try:
            sql = """
                    SELECT captured_at, price
                    FROM price_history
                    WHERE collection_id = %s
                    ORDER BY captured_at DESC, id DESC
                    LIMIT %s
                  """

            cursor.execute(sql, (collection_id, int(limit)))

            return list(reversed(cursor.fetchall()))

        finally:
            self.disconnect(cursor, connection)
