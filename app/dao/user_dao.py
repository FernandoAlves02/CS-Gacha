import mysql.connector

from app.dao.base_dao import DAO
from app.models.user import User

# Código de erro do MySQL para "valor duplicado em coluna UNIQUE".
MYSQL_DUPLICATE_ENTRY = 1062


class User_DAO(DAO):

    def __init__(self, database):
        super().__init__(database)

    @staticmethod
    def _duplicate_message(error):
        # A mensagem do MySQL termina com: ... for key 'users.email'
        key = (error.msg or "").lower().rsplit("for key", 1)[-1]
        if "email" in key:
            return "E-mail já cadastrado."
        if "username" in key:
            return "Nome de usuário já cadastrado."
        return "Usuário já cadastrado."

    def save(self, user):
        connection, cursor = self.connect()

        try:
            sql = """
                    INSERT INTO users
                    (
                        username,
                        password,
                        email,
                        balance
                    )
                    VALUES
                    (
                        %s,
                        %s,
                        %s,
                        %s
                    )
                  """

            cursor.execute(
                sql,
                (
                    user.username,
                    user.password,
                    user.email,
                    user.balance
                )
            )

            connection.commit()

            user.id = cursor.lastrowid

            return user

        except mysql.connector.IntegrityError as error:
            connection.rollback()
            if error.errno == MYSQL_DUPLICATE_ENTRY:
                raise ValueError(self._duplicate_message(error)) from error
            raise

        except Exception:
            connection.rollback()
            raise

        finally:
            self.disconnect(cursor, connection)

    def get_all(self):

        connection, cursor = self.connect()

        try:

            sql = """
                    SELECT
                        id,
                        username,
                        email,
                        balance
                    FROM
                        users
                  """

            cursor.execute(sql)

            # A senha nunca sai nas listagens (password = None).
            return [
                User(data[0], data[1], None, data[2], data[3])
                for data in cursor.fetchall()
            ]

        finally:
            self.disconnect(cursor, connection)

    def get_by_id(self, entity_id):

        connection, cursor = self.connect()

        try:

            sql = """
                    SELECT
                        id,
                        username,
                        email,
                        balance
                    FROM
                        users
                    WHERE
                        id = %s
                  """

            cursor.execute(sql, (entity_id,))

            data = cursor.fetchone()

            if data is None:
                return None

            return User(data[0], data[1], None, data[2], data[3])

        finally:
            self.disconnect(cursor, connection)

    def get_by_email(self, email):

        connection, cursor = self.connect()

        try:

            sql = """
                    SELECT
                        id,
                        username,
                        password,
                        email,
                        balance
                    FROM
                        users
                    WHERE
                        email = %s
                  """

            cursor.execute(sql, (email,))

            data = cursor.fetchone()

            if data is None:
                return None

            return User(data[0], data[1], data[2], data[3], data[4])

        finally:
            self.disconnect(cursor, connection)

    def get_by_username(self, username):
        # Usado no login pelo nome de usuário (a tela pede "Usuário").
        # Traz a senha (hash) porque o login precisa conferir.

        connection, cursor = self.connect()

        try:

            sql = """
                    SELECT
                        id,
                        username,
                        password,
                        email,
                        balance
                    FROM
                        users
                    WHERE
                        username = %s
                  """

            cursor.execute(sql, (username,))

            data = cursor.fetchone()

            if data is None:
                return None

            return User(data[0], data[1], data[2], data[3], data[4])

        finally:
            self.disconnect(cursor, connection)

    def update(self, user):
        # Atualiza nome e e-mail. A senha só é gravada quando o objeto
        # traz uma senha nova (user.password diferente de None); assim um
        # usuário carregado sem senha não tem o hash apagado no banco.
        # O saldo NÃO é alterado aqui: só compra/venda mexem nele.

        connection, cursor = self.connect()

        try:

            if user.password is None:
                sql = """
                        UPDATE users
                        SET
                            username = %s,
                            email = %s
                        WHERE
                            id = %s
                      """
                params = (user.username, user.email, user.id)
            else:
                sql = """
                        UPDATE users
                        SET
                            username = %s,
                            email = %s,
                            password = %s
                        WHERE
                            id = %s
                      """
                params = (user.username, user.email, user.password, user.id)

            cursor.execute(sql, params)

            connection.commit()

            return cursor.rowcount > 0

        except mysql.connector.IntegrityError as error:
            connection.rollback()
            if error.errno == MYSQL_DUPLICATE_ENTRY:
                raise ValueError(self._duplicate_message(error)) from error
            raise

        except Exception:
            connection.rollback()
            raise

        finally:
            self.disconnect(cursor, connection)

    def delete(self, entity_id):

        connection, cursor = self.connect()

        try:

            sql = """
                    DELETE
                    FROM users
                    WHERE
                        id = %s
                  """

            cursor.execute(sql, (entity_id,))

            connection.commit()

            return cursor.rowcount > 0

        except Exception:
            connection.rollback()
            raise

        finally:
            self.disconnect(cursor, connection)
