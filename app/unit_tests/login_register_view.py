from app.core.database import Database
from app.core.password_utils import Password_Utils
from app.dao.user_dao import User_DAO
from app.controller.login_controller import Login_Controller
from app.controller.user_controller import User_Controller
from app.models.user import User

_database = Database()
user_dao = User_DAO(_database)


def login():
        print("Log In")
        email = input("E-mail: ")
        password = input("Password: ")

        user_login = user_dao.get_by_email(email)

        if user_login is None or not Password_Utils.check_password(password, user_login.password):
            print("E-mail ou senha inválidos.", False)
            return

        print(f"Logado com sucesso! {user_login.username}")

login()
users = user_dao.get_all()

for user in users:
    print(
        f"ID: {user.id}"
        f"Username: {user.username}"
        f"Email: {user.email}"
        f"Password: {user.password}"
        f"Balance: {user.balance}"
    )

username = input("Informe um nome de usuario: ")
password = Password_Utils.to_hash(input("Informe uma senha: "))
email = input("Informe um e-mail: ")

new_user = User(None, username, password, email, 500.00)
user_dao.save(new_user)

users2 = user_dao.get_all()
for user in users2:
    print(
        f"ID: {user.id}"
        f"Username: {user.username}"
        f"Email: {user.email}"
        f"Password: {user.password}"
        f"Balance: {user.balance}"
    )

