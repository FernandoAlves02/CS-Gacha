"""Testes automáticos de usuário. Não precisam de banco nem de Panda3D.

Rodar da raiz do projeto:
    python -m unittest app.unit_tests.test_user_flow -v
"""
import copy
import unittest
from decimal import Decimal

from app.controller.login_controller import Login_Controller
from app.controller.user_controller import User_Controller
from app.core.password_utils import Password_Utils
from app.models.user import User


class FakeView:
    def __init__(self, login_data=None, register_data=None, profile_data=None):
        self.login_data = login_data
        self.register_data = register_data
        self.profile_data = profile_data
        self.messages = []

    def read_login_data(self):
        return self.login_data

    def read_register_data(self):
        return self.register_data

    def read_profile_data(self):
        return self.profile_data

    def show_message(self, message, success=True):
        self.messages.append((message, success))


class FakeDAO:
    """Imita o User_DAO em memória (inclui a regra de e-mail único)."""

    def __init__(self):
        self.users = {}

    def save(self, user):
        if user.email in self.users:
            raise ValueError("E-mail já cadastrado.")
        user.id = len(self.users) + 1
        self.users[user.email] = copy.copy(user)
        return user

    def get_by_email(self, email):
        user = self.users.get(email)
        return copy.copy(user) if user else None

    def update(self, user):
        self.users[user.email] = copy.copy(user)
        return True


class PasswordUtilsTests(unittest.TestCase):

    def test_hash_confere_com_a_senha_correta(self):
        stored = Password_Utils.to_hash("segredo123")
        self.assertTrue(Password_Utils.check_password("segredo123", stored))

    def test_senha_errada_e_negada(self):
        stored = Password_Utils.to_hash("segredo123")
        self.assertFalse(Password_Utils.check_password("outra", stored))

    def test_hash_malformado_ou_none_nao_estoura_erro(self):
        self.assertFalse(Password_Utils.check_password("x", "hash_senha_teste_123"))
        self.assertFalse(Password_Utils.check_password("x", None))
        self.assertFalse(Password_Utils.check_password("x", ""))

    def test_mesma_senha_gera_hashes_diferentes(self):
        self.assertNotEqual(
            Password_Utils.to_hash("segredo123"),
            Password_Utils.to_hash("segredo123"),
        )


class UserModelTests(unittest.TestCase):

    def test_saldo_vira_decimal(self):
        user = User(None, "ana", None, "ana@x.com", 500.00)
        self.assertEqual(user.balance, Decimal("500.00"))
        self.assertIsInstance(user.balance, Decimal)

    def test_saldo_negativo_e_recusado(self):
        user = User(None, "ana", None, "ana@x.com", 10)
        with self.assertRaises(ValueError):
            user.balance = -1

    def test_validacoes(self):
        self.assertEqual(User.validate_email("  ANA@X.com "), "ana@x.com")
        self.assertEqual(User.validate_username("  ana "), "ana")
        for invalido in ("", "ana", "ana@", "ana@x", "a b@x.com"):
            with self.assertRaises(ValueError):
                User.validate_email(invalido)
        with self.assertRaises(ValueError):
            User.validate_username("ab")
        with self.assertRaises(ValueError):
            User.validate_password("12345")


class UserControllerTests(unittest.TestCase):

    def setUp(self):
        self.dao = FakeDAO()
        self.registrados = []

    def _controller(self, view):
        return User_Controller(self.dao, view, self.registrados.append)

    def test_cadastro_ok_grava_saldo_inicial_e_senha_com_hash(self):
        view = FakeView(register_data=("ana", "segredo123", "ANA@x.com"))
        self._controller(view).save()

        user = self.dao.get_by_email("ana@x.com")
        self.assertIsNotNone(user)
        self.assertEqual(user.balance, Decimal("500.00"))
        self.assertNotEqual(user.password, "segredo123")
        self.assertTrue(Password_Utils.check_password("segredo123", user.password))
        self.assertEqual(view.messages[-1], ("Usuário cadastrado com sucesso!", True))
        self.assertEqual(len(self.registrados), 1)

    def test_email_duplicado_mostra_erro_e_nao_avanca(self):
        dados = ("ana", "segredo123", "ana@x.com")
        self._controller(FakeView(register_data=dados)).save()

        view = FakeView(register_data=("bia", "segredo123", "ana@x.com"))
        self._controller(view).save()

        self.assertFalse(view.messages[-1][1])
        self.assertIn("já cadastrado", view.messages[-1][0])
        self.assertEqual(len(self.registrados), 1)

    def test_dados_invalidos_mostram_erro(self):
        casos = [
            ("", "segredo123", "ana@x.com"),
            ("ana", "123", "ana@x.com"),
            ("ana", "segredo123", "email-invalido"),
        ]
        for caso in casos:
            view = FakeView(register_data=caso)
            self._controller(view).save()
            self.assertFalse(view.messages[-1][1], caso)
        self.assertEqual(self.registrados, [])

    def test_update_sem_senha_nao_mexe_na_senha(self):
        user = User(1, "ana", None, "ana@x.com", 500)
        view = FakeView(profile_data=("ana2", "", "ana2@x.com"))
        User_Controller(self.dao, view).update(user)

        self.assertEqual(user.username, "ana2")
        self.assertEqual(user.email, "ana2@x.com")
        self.assertIsNone(user.password)
        self.assertEqual(user.balance, Decimal("500"))
        self.assertTrue(view.messages[-1][1])


class LoginControllerTests(unittest.TestCase):

    def setUp(self):
        self.dao = FakeDAO()
        User_Controller(
            self.dao, FakeView(register_data=("ana", "segredo123", "ana@x.com"))
        ).save()
        self.logados = []

    def _login(self, email, senha):
        view = FakeView(login_data=(email, senha))
        Login_Controller(self.dao, view, self.logados.append).auth()
        return view

    def test_login_ok_entrega_usuario_sem_hash(self):
        self._login("  ANA@x.com ", "segredo123")
        self.assertEqual(len(self.logados), 1)
        self.assertEqual(self.logados[0].username, "ana")
        self.assertIsNone(self.logados[0].password)

    def test_senha_errada_ou_email_inexistente_dao_mesma_mensagem(self):
        v1 = self._login("ana@x.com", "errada")
        v2 = self._login("naoexiste@x.com", "segredo123")
        self.assertEqual(self.logados, [])
        self.assertEqual(v1.messages[-1], v2.messages[-1])
        self.assertEqual(v1.messages[-1], ("E-mail ou senha inválidos.", False))

    def test_campos_vazios(self):
        view = self._login("", "")
        self.assertEqual(view.messages[-1], ("Informe e-mail e senha.", False))
        self.assertEqual(self.logados, [])


if __name__ == "__main__":
    unittest.main()
