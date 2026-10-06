from app.dao.base_dao import Read_Only_DAO
from app.models.rarity import Rarity


class Rarity_DAO(Read_Only_DAO):
    """Leitura da tabela rarities (probabilidade oficial de cada raridade)."""

    def __init__(self, database):
        super().__init__(database)

    def get_all(self):
        connection, cursor = self.connect()

        try:
            sql = """
                    SELECT
                        id,
                        name,
                        probability,
                        color
                    FROM
                        rarities
                    ORDER BY
                        id
                  """

            cursor.execute(sql)

            return [Rarity(data[0], data[1], data[2], data[3]) for data in cursor.fetchall()]

        finally:
            self.disconnect(cursor, connection)

    def get_by_id(self, entity_id):
        connection, cursor = self.connect()

        try:
            sql = """
                    SELECT
                        id,
                        name,
                        probability,
                        color
                    FROM
                        rarities
                    WHERE
                        id = %s
                  """

            cursor.execute(sql, (entity_id,))

            data = cursor.fetchone()

            if data is None:
                return None

            return Rarity(data[0], data[1], data[2], data[3])

        finally:
            self.disconnect(cursor, connection)

    def get_probabilities(self):
        """Dicionário {id da raridade: probabilidade}, usado no sorteio do drop."""
        return {rarity.id: rarity.probability for rarity in self.get_all()}
