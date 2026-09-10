from app.models.user import User
from app.core.password_utils import Password_Utils


class User_Controller:

    def __init__(self, dao, view):
        self.dao = dao
        self.view = view

    def save(self):
        try:
            username, password, email = self.view.read_user_data()
            if not password:
                raise ValueError("Informe uma senha para o novo usuário.")
            user = User(
                None,
                username,
                Password_Utils.to_hash(password),
                email,
                500.00
            )
            self.dao.save(user)
            self.get_all()
            self.view.show_message("Usuário cadastrado com sucesso!")
        except ValueError as e:
            self.view.show_message(f"Erro: {str(e)}", False)

    def get_all(self):
        users = self.dao.get_all()
        self.view.show_users(users)

    def update(self, user):
        try:
            username, password, email, balance = self.view.read_user_data()
            user.update_data(
                username,
                email,
                balance
            )
            if password:
                user.password = Password_Utils.to_hash(password)
            self.dao.update(user)
            self.get_all()
            self.view.show_message("Usuário atualizado com sucesso!")
        except ValueError as e:
            self.view.show_message(f"Erro: {str(e)}", False)

    def delete(self, user):
        try:
            success = self.dao.delete(user.id)
            if success:
                self.view.show_message("Usuário excluído com sucesso!")
            else:
                self.view.show_message("Usuário não encontrado.", False)
        except Exception as e:
            self.view.show_message("Problemas ao excluir usuário", False)