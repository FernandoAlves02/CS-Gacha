import os

import mysql.connector
from dotenv import load_dotenv

# Carrega o .env uma única vez, ao importar o módulo.
# O load_dotenv procura o arquivo a partir da pasta deste arquivo para cima,
# então funciona mesmo que o programa seja iniciado de outra pasta.
load_dotenv()


class Database:

    def connect(self):
        user = os.getenv("DB_USER")
        if not user:
            raise RuntimeError(
                "Configuração do banco não encontrada. "
                "Copie o arquivo .env.example para .env e preencha os dados."
            )

        return mysql.connector.connect(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", "3306")),
            database=os.getenv("DB_NAME", "csgacha"),
            user=user,
            password=os.getenv("DB_PASSWORD", ""),
            use_pure=True
        )

    def disconnect(self, cursor=None, connection=None):
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()
