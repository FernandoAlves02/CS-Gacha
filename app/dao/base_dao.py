from abc import ABC, abstractmethod


class DAO(ABC):

    def __init__(self, database):
        self._database = database

    def connect(self):
        connection = self._database.connect()
        try:
            cursor = connection.cursor()
        except Exception:
            # Não deixa a conexão aberta se o cursor falhar.
            self._database.disconnect(None, connection)
            raise
        return connection, cursor

    def disconnect(self, cursor, connection):
        self._database.disconnect(cursor, connection)

    @abstractmethod
    def save(self, entity):
        pass

    @abstractmethod
    def get_all(self):
        pass

    @abstractmethod
    def get_by_id(self, entity_id):
        pass

    @abstractmethod
    def update(self, entity):
        pass

    @abstractmethod
    def delete(self, entity_id):
        pass
