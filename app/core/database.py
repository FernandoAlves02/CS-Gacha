import mysql.connector
import os
from dotenv import load_dotenv

class Database:

    load_dotenv()

    def connect(self):

        return mysql.connector.connect(
            host =      os.getenv("DB_HOST"),
            port =      os.getenv("DB_PORT"),
            database =  os.getenv("DB_NAME"),
            user =      os.getenv("DB_USER"),
            password =  os.getenv("DB_PASSWORD")
        )
    def disconnect(self, cursor=None, connection=None):
        if cursor:
            cursor.close()
        if connection and connection.is_connected():
            connection.close()