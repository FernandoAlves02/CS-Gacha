import logging

from app.core.i18n import t
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
            self.view.show_message(t("Erro: {mensagem}", mensagem=e), False)

        except Exception:
            logger.exception("Falha ao cadastrar usuário")
            self.view.show_message(
                t("Não foi possível cadastrar. Verifique a conexão com o banco."),
                False
            )

        else:
            self.view.show_message(t("Usuário cadastrado com sucesso!"))
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

            # Grava uma CÓPIA: o usuário da sessão só muda depois que o banco
            # aceitar (ex.: e-mail já usado por outra conta não altera a sessão).
            alterado = User(user.id, username, None, email, user.balance)
            if password:
                alterado.password = Password_Utils.to_hash(password)

            self.dao.update(alterado)

        except ValueError as e:
            self.view.show_message(t("Erro: {mensagem}", mensagem=e), False)

        except Exception:
            logger.exception("Falha ao atualizar usuário")
            self.view.show_message(t("Não foi possível atualizar os dados."), False)

        else:
            user.update_data(username, email)      # a senha (hash) nunca fica na sessão
            self.view.show_message(t("Usuário atualizado com sucesso!"))

    def delete(self, user):
        """Exclui a conta (o "D" do CRUD). Os itens dela saem junto (ON DELETE CASCADE
        no banco). Devolve True/False para a tela saber se volta ao login."""
        try:
            success = self.dao.delete(user.id)
            if success:
                self.view.show_message(t("Usuário excluído com sucesso!"))
            else:
                self.view.show_message(t("Usuário não encontrado."), False)
            return success
        except Exception:
            logger.exception("Falha ao excluir usuário")
            self.view.show_message(t("Problemas ao excluir usuário"), False)
            return False
