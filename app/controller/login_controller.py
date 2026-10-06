import logging

from app.core.i18n import t
from app.core.password_utils import Password_Utils

logger = logging.getLogger(__name__)


class Login_Controller:
    def __init__(self, user_dao, view, when_auth):
        self.user_dao = user_dao
        self.view = view
        self.when_auth = when_auth

    def auth(self):
        try:
            login, password = self.view.read_login_data()
            login = (login or "").strip()

            if not login or not password:
                self.view.show_message(t("Informe usuário e senha."), False)
                return

            # O campo aceita nome de usuário OU e-mail:
            # tem "@" -> procura pelo e-mail; não tem -> procura pelo usuário.
            if "@" in login:
                user = self.user_dao.get_by_email(login.lower())
            else:
                user = self.user_dao.get_by_username(login)

        except Exception:
            logger.exception("Falha ao autenticar")
            self.view.show_message(
                t("Não foi possível entrar. Verifique a conexão com o banco."),
                False
            )
            return

        # Mesma mensagem para "usuário não existe" e "senha errada"
        # (não revela quais contas existem).
        if user is None or not Password_Utils.check_password(password, user.password):
            self.view.show_message(t("Usuário ou senha inválidos."), False)
            return

        # O hash só serve para conferir a senha; não fica na sessão.
        user.password = None
        self.when_auth(user)
