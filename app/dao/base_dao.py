from abc import ABC, abstractmethod
class DAO(ABC):

    def __init__(self, database):
        self._database = database

    def connect(self):
        connection = self._database.connect()
        cursor = connection.cursor()
        return connection, cursor
    
    def disconnect(self, cursor, connection):
        self._database.disconnect(cursor, connection)

    @abstractmethod
    def save(self, object):
        pass

    @abstractmethod
    def get_all(self):
        pass
    @abstractmethod
    def get_by_id(self, id):
        pass

    @abstractmethod
    def update(self, object):
        pass

    @abstractmethod
    def delete(self, id):
        pass