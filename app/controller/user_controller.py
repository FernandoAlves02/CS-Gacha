import logging

from app.core.password_utils import Password_Utils
from app.models.user import User

logger = logging.getLogger(__name__)


class User_Controller:

    def __init__(self, dao, view, when_registered=None):
        self.dao = dao
        self.view = view
        self.when_registered = when_registered

    def save(self):
        try:
            username, password, email = self.view.read_register_data()

            username = User.validate_username(username)
            email = User.validate_email(email)
            User.validate_password(password)

            user = User(
                None,
                username,
                Password_Utils.to_hash(password),
                email,
                User.INITIAL_BALANCE
            )
            self.dao.save(user)

        except ValueError as e:
            # Erros de validação e e-mail/usuário já cadastrado.
            self.view.show_message(f"Erro: {str(e)}", False)

        except Exception:
            logger.exception("Falha ao cadastrar usuário")
            self.view.show_message(
                "Não foi possível cadastrar. Verifique a conexão com o banco.",
                False
            )

        else:
            self.view.show_message("Usuário cadastrado com sucesso!")
            if self.when_registered:
                self.when_registered(user)

    def get_all(self):
        users = self.dao.get_all()
        self.view.show_users(users)

    def update(self, user):
        try:
            username, password, email = self.view.read_profile_data()

            username = User.validate_username(username)
            email = User.validate_email(email)
            if password:
                User.validate_password(password)

            # Só altera o objeto depois que tudo foi validado.
            user.update_data(username, email)
            if password:
                user.password = Password_Utils.to_hash(password)

            self.dao.update(user)

        except ValueError as e:
            self.view.show_message(f"Erro: {str(e)}", False)

        except Exception:
            logger.exception("Falha ao atualizar usuário")
            self.view.show_message("Não foi possível atualizar os dados.", False)

        else:
            self.view.show_message("Usuário atualizado com sucesso!")

    def delete(self, user):
        try:
            success = self.dao.delete(user.id)
            if success:
                self.view.show_message("Usuário excluído com sucesso!")
            else:
                self.view.show_message("Usuário não encontrado.", False)
        except Exception:
            logger.exception("Falha ao excluir usuário")
            self.view.show_message("Problemas ao excluir usuário", False)
