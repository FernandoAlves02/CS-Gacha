class User:
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
        self._balance = balance

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
        self._balance = new_balance

    def update_data(
        self,
        new_username,
        new_email,
        new_balance
    ):
        self._username = new_username
        self._email = new_email
        self._balance = new_balance