from app.dao.base_dao import DAO
from app.models.user import User

class User_DAO(DAO):
    def __init__(self, database):
        super().__init__(database)

    def save(self, user):
        connection, cursor = self.connect()

        try:
            sql = """
                    INSERT INTO USUER
                    (
                        USERNAME,
                        PASSWORD,
                        EMAIL
                    )
                    VALUES
                    (
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
                    user.email
                )
            )

            connection.commit()

            user.id = cursor.lastrowid

            return user

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
                        ID,
                        USERNAME,
                        EMAIL,
                        BALANCE,
                    FROM
                        USER
                    ORDER BY
                        NOME
                  """

            cursor.execute(sql)

            datas = cursor.fetchall()

            users = []

            for data in datas:

                users.append(

                    User(
                        data[0],
                        data[1],
                        None,
                        data[2],
                        data[3]
                    )

                )

            return users

        finally:
            self.disconnect(cursor, connection)

    def get_by_id(self, id):

        connection, cursor = self.connect()

        try:

            sql = """
                    SELECT
                        ID,
                        USERNAME,
                        EMAIL,
                        BALANCE
                    FROM
                        USER
                    WHERE
                        ID = %s
                  """

            cursor.execute(sql, (id,))

            data = cursor.fetchone()

            if data is None:
                return None

            return User(
                data[0],
                data[1],
                None,
                data[2],
                data[3]
            )

        finally:
            self.disconnect(cursor, connection)

    def update(self, user):

        connection, cursor = self.connect()

        try:

            sql = """
                    UPDATE USER
                    SET
                        USERNAME = %s,
                        PASSWORD = %s,
                        EMAIL = %s,
                        BALANCE = %s
                    WHERE
                        ID = %s
                  """

            cursor.execute(
                sql,
                (
                    user.username,
                    user.password,
                    user.email,
                    user.balance,
                    user.id
                )
            )

            connection.commit()

            return cursor.rowcount > 0

        except Exception:
            connection.rollback()
            raise

        finally:
            self.disconnect(cursor, connection)

    def delete(self, id):

        connection, cursor = self.connect()

        try:

            sql = """
                    DELETE
                    FROM USER
                    WHERE
                        ID = %s
                  """

            cursor.execute(sql, (id,))

            connection.commit()

            return cursor.rowcount > 0

        except Exception:
            connection.rollback()
            raise

        finally:
            self.disconnect(cursor, connection)
