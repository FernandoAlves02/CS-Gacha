from app.core.password_utils import Password_Utils

class Login_Controller:
    def __init__(self, user_dao, view, when_auth):
        self.user_dao = user_dao
        self.view = view
        self.when_auth = when_auth

    def auth(self):
        email, password = self.view.read_user_data()

        if not email or not password:
            self.view.show_message("Informe e-mail e senha.", False)
            return

        user = self.user_dao.get_by_email(email)

        if user is None or not Password_Utils.check_password(password, user.password):
            self.view.show_message("E-mail ou senha inválidos.", False)
            return

        self.when_auth(user)
