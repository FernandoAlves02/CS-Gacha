"""Teste manual contra o banco REAL (precisa do .env e do MySQL no ar).

Rodar da raiz do projeto:
    python -m app.unit_tests.manual_user_flow
"""
from app.core.database import Database
from app.core.password_utils import Password_Utils
from app.dao.user_dao import User_DAO
from app.models.user import User


def listar_usuarios(user_dao):
    for user in user_dao.get_all():
        print(
            f"ID: {user.id} | "
            f"Username: {user.username} | "
            f"Email: {user.email} | "
            f"Balance: {user.balance}"
        )


def testar_login(user_dao):
    print("Log In")
    email = input("E-mail: ").strip().lower()
    password = input("Senha: ")

    user = user_dao.get_by_email(email)

    if user is None or not Password_Utils.check_password(password, user.password):
        print("E-mail ou senha inválidos.")
        return

    print(f"Logado com sucesso! {user.username}")


def testar_cadastro(user_dao):
    print("Cadastro")
    try:
        username = User.validate_username(input("Nome de usuário: "))
        email = User.validate_email(input("E-mail: "))
        password = User.validate_password(input("Senha: "))

        new_user = User(
            None,
            username,
            Password_Utils.to_hash(password),
            email,
            User.INITIAL_BALANCE
        )
        user_dao.save(new_user)
        print(f"Cadastrado com ID {new_user.id}")
    except ValueError as e:
        print(f"Erro: {e}")


def main():
    user_dao = User_DAO(Database())

    testar_login(user_dao)
    listar_usuarios(user_dao)
    testar_cadastro(user_dao)
    listar_usuarios(user_dao)


if __name__ == "__main__":
    main()
