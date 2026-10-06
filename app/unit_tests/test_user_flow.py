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

    def get_by_username(self, username):
        for user in self.users.values():
            if user.username == username:
                return copy.copy(user)
        return None

    def update(self, user):
        self.users[user.email] = copy.copy(user)
        return True

    def delete(self, entity_id):
        for email, user in list(self.users.items()):
            if user.id == entity_id:
                del self.users[email]
                return True
        return False


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
            User.validate_username("ana@x")      # "@" é reservado para o login por e-mail
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


class UserDeleteTests(unittest.TestCase):
    """Minha conta -> EXCLUIR CONTA: o "D" do CRUD (como no projeto da aula)."""

    def test_excluir_conta(self):
        dao = FakeDAO()
        User_Controller(dao, FakeView(register_data=("ana", "segredo123", "ana@x.com"))).save()
        user = dao.get_by_email("ana@x.com")
        view = FakeView()
        self.assertTrue(User_Controller(dao, view).delete(user))
        self.assertIsNone(dao.get_by_email("ana@x.com"))
        self.assertEqual(view.messages[-1], ("Usuário excluído com sucesso!", True))
        self.assertFalse(User_Controller(dao, view).delete(user))          # já não existe
        self.assertEqual(view.messages[-1], ("Usuário não encontrado.", False))

    def test_banco_fora_do_ar_nao_derruba_a_tela(self):
        class DaoQuebrado:
            def delete(self, entity_id):
                raise RuntimeError("banco caiu")
        view = FakeView()
        with self.assertLogs("app.controller.user_controller", level="ERROR"):
            self.assertFalse(User_Controller(DaoQuebrado(), view).delete(User(1, "ana", None, "a@x.com", 0)))
        self.assertEqual(view.messages[-1], ("Problemas ao excluir usuário", False))


class UserUpdateTests(unittest.TestCase):
    """Minha conta: editar nome, e-mail e senha."""

    def setUp(self):
        self.dao = FakeDAO()
        for dados in (("ana", "segredo123", "ana@x.com"), ("bia", "segredo123", "bia@x.com")):
            User_Controller(self.dao, FakeView(register_data=dados)).save()

    def test_email_de_outra_conta_nao_altera_a_sessao(self):
        sessao = User(1, "ana", None, "ana@x.com", 500)
        self.dao.update = lambda user: (_ for _ in ()).throw(ValueError("Este e-mail já está cadastrado."))
        view = FakeView(profile_data=("ana", "", "bia@x.com"))
        User_Controller(self.dao, view).update(sessao)
        self.assertEqual(sessao.email, "ana@x.com")                 # sessão intacta
        self.assertFalse(view.messages[-1][1])

    def test_senha_nova_vai_para_o_banco_com_hash_e_nao_fica_na_sessao(self):
        gravados = []
        self.dao.update = gravados.append
        sessao = User(1, "ana", None, "ana@x.com", 500)
        User_Controller(self.dao, FakeView(profile_data=("ana", "novaSenha1", "ana@x.com"))).update(sessao)
        self.assertTrue(Password_Utils.check_password("novaSenha1", gravados[-1].password))
        self.assertIsNone(sessao.password)


class LoginControllerTests(unittest.TestCase):

    def setUp(self):
        self.dao = FakeDAO()
        User_Controller(
            self.dao, FakeView(register_data=("ana", "segredo123", "ana@x.com"))
        ).save()
        self.logados = []

    def _login(self, login, senha):
        view = FakeView(login_data=(login, senha))
        Login_Controller(self.dao, view, self.logados.append).auth()
        return view

    def test_login_por_email_entrega_usuario_sem_hash(self):
        self._login("  ANA@x.com ", "segredo123")
        self.assertEqual(len(self.logados), 1)
        self.assertEqual(self.logados[0].username, "ana")
        self.assertIsNone(self.logados[0].password)

    def test_login_por_nome_de_usuario(self):
        self._login(" ana ", "segredo123")
        self.assertEqual(len(self.logados), 1)
        self.assertEqual(self.logados[0].email, "ana@x.com")

    def test_senha_errada_ou_usuario_inexistente_dao_mesma_mensagem(self):
        v1 = self._login("ana@x.com", "errada")
        v2 = self._login("naoexiste@x.com", "segredo123")
        v3 = self._login("naoexiste", "segredo123")
        self.assertEqual(self.logados, [])
        self.assertEqual(v1.messages[-1], v2.messages[-1])
        self.assertEqual(v2.messages[-1], v3.messages[-1])
        self.assertEqual(v1.messages[-1], ("Usuário ou senha inválidos.", False))

    def test_campos_vazios(self):
        view = self._login("", "")
        self.assertEqual(view.messages[-1], ("Informe usuário e senha.", False))
        self.assertEqual(self.logados, [])


if __name__ == "__main__":
    unittest.main()
