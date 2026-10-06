from abc import ABC, abstractmethod


class Base_DAO:
    """Parte comum a todos os DAOs: abrir e fechar a conexão com o banco."""

    def __init__(self, database):
        self._database = database

    def connect(self, buffered=False):
        """Abre a conexão e um cursor.

        buffered=True faz o cursor ler TODAS as linhas do resultado na hora.
        Use em transações com várias consultas seguidas no mesmo cursor:
        sem isso o mysql-connector reclama de "Unread result found".
        """
        connection = self._database.connect()
        try:
            cursor = connection.cursor(buffered=True) if buffered else connection.cursor()
        except Exception:
            # Não deixa a conexão aberta se o cursor falhar.
            self._database.disconnect(None, connection)
            raise
        return connection, cursor

    def disconnect(self, cursor, connection):
        self._database.disconnect(cursor, connection)


class DAO(Base_DAO, ABC):
    """DAO de uma ENTIDADE: obriga a ter o CRUD completo (ex.: User_DAO)."""

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


class Read_Only_DAO(DAO):
    """DAO de tabelas que o JOGO apenas lê (catálogo de caixas, skins, raridades).

    Quem grava nessas tabelas é o importador (tools/sync_market.py), em lote e
    numa transação só. Por isso save/update/delete aqui avisam com erro.
    As classes filhas implementam apenas get_all e get_by_id (e consultas extras).
    """

    def save(self, entity):
        raise NotImplementedError("Tabela de catálogo: os dados vêm do importador (tools/sync_market.py).")

    def update(self, entity):
        raise NotImplementedError("Tabela de catálogo: os dados vêm do importador (tools/sync_market.py).")

    def delete(self, entity_id):
        raise NotImplementedError("Tabela de catálogo: os dados vêm do importador (tools/sync_market.py).")
