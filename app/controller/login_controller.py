import logging

from app.core.password_utils import Password_Utils

logger = logging.getLogger(__name__)


class Login_Controller:
    def __init__(self, user_dao, view, when_auth):
        self.user_dao = user_dao
        self.view = view
        self.when_auth = when_auth

    def auth(self):
        try:
            email, password = self.view.read_login_data()
            email = (email or "").strip().lower()

            if not email or not password:
                self.view.show_message("Informe e-mail e senha.", False)
                return

            user = self.user_dao.get_by_email(email)

        except Exception:
            logger.exception("Falha ao autenticar")
            self.view.show_message(
                "Não foi possível entrar. Verifique a conexão com o banco.",
                False
            )
            return

        # Mesma mensagem para "e-mail não existe" e "senha errada".
        if user is None or not Password_Utils.check_password(password, user.password):
            self.view.show_message("E-mail ou senha inválidos.", False)
            return

        # O hash só serve para conferir a senha; não fica na sessão.
        user.password = None
        self.when_auth(user)
