import re
from decimal import Decimal


class User:
    # Saldo inicial de todo novo jogador (regra definida em um único lugar).
    INITIAL_BALANCE = Decimal("500.00")

    _EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

    def __init__(
            self,
            id,
            username,
            password,
            email,
            balance
    ):
        self._id = id
        self._username = username
        self._password = password
        self._email = email
        self.balance = balance

    # ----------------------------------------------------------
    # VALIDAÇÕES (limites iguais aos das colunas do banco)
    # ----------------------------------------------------------

    @staticmethod
    def validate_username(username):
        username = (username or "").strip()
        if not 3 <= len(username) <= 50:
            raise ValueError("O nome de usuário deve ter entre 3 e 50 caracteres.")
        return username

    @staticmethod
    def validate_email(email):
        email = (email or "").strip().lower()
        if len(email) > 100 or not User._EMAIL_REGEX.match(email):
            raise ValueError("Informe um e-mail válido.")
        return email

    @staticmethod
    def validate_password(password):
        if not password or len(password) < 6:
            raise ValueError("A senha deve ter pelo menos 6 caracteres.")
        return password

    # ----------------------------------------------------------
    # PROPRIEDADES
    # ----------------------------------------------------------

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, new_id):
        self._id = new_id

    @property
    def username(self):
        return self._username

    @username.setter
    def username(self, new_username):
        self._username = new_username

    @property
    def password(self):
        return self._password

    @password.setter
    def password(self, new_password):
        self._password = new_password

    @property
    def email(self):
        return self._email

    @email.setter
    def email(self, new_email):
        self._email = new_email

    @property
    def balance(self):
        return self._balance

    @balance.setter
    def balance(self, new_balance):
        # Decimal evita o erro "Decimal + float" ao mexer em dinheiro
        # (o MySQL devolve DECIMAL como Decimal).
        new_balance = Decimal(str(new_balance))
        if new_balance < 0:
            raise ValueError("O saldo não pode ficar negativo.")
        self._balance = new_balance

    def update_data(
        self,
        new_username,
        new_email
    ):
        # O saldo NÃO é editável pelo jogador: só muda por compra/venda.
        self._username = new_username
        self._email = new_email
