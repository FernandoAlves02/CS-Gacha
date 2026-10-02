from pathlib import Path

from direct.gui.DirectGui import DirectButton, DirectEntry, DirectFrame, DirectLabel
from panda3d.core import Filename, TextNode, TransparencyAttrib

from app.controller.login_controller import Login_Controller
from app.controller.user_controller import User_Controller

COR_ERRO = (1.0, 0.4, 0.4, 1)
COR_SUCESSO = (0.4, 1.0, 0.5, 1)
COR_TEXTO = (0.85, 0.85, 0.85, 1)

# Posição vertical (z) de cada campo em cada modo da tela.
LAYOUT = {
    "login": {"email": 0.18, "password": -0.02},
    "register": {"username": 0.28, "email": 0.08, "password": -0.12},
}


class LoginRegisterView:
    def __init__(self, ui_root, view_manager):
        self.ui_root = ui_root
        self.view_manager = view_manager
        self.elementos = []
        self.modo = "login"
        self.campos = {}

    # ----------------------------------------------------------
    # CONSTRUÇÃO
    # ----------------------------------------------------------

    def construir_tela(self):
        if self.view_manager.backdrop:
            self.view_manager.backdrop.ocultar()

        user_dao = self.view_manager.user_dao
        self.login_controller = Login_Controller(user_dao, self, self._ao_autenticar)
        self.user_controller = User_Controller(user_dao, self, self._ao_cadastrar)

        self._criar_card()

        DirectLabel(
            text="CS GACHA",
            scale=0.08,
            text_fg=(1, 0.25, 0.32, 1),
            frameColor=(0, 0, 0, 0),
            pos=(0, 0, 0.5),
            parent=self.card
        )

        self._criar_campo("username", "Usuário")
        self._criar_campo("email", "E-mail")
        self._criar_campo("password", "Senha", obscured=True)

        self.lbl_mensagem = DirectLabel(
            text="",
            scale=0.035,
            text_fg=COR_ERRO,
            text_wordwrap=28,
            frameColor=(0, 0, 0, 0),
            pos=(0, 0, -0.27),
            parent=self.card
        )

        self.btn_principal = DirectButton(
            text="ENTRAR",
            scale=0.045,
            pos=(0, 0, -0.42),
            pad=(0.4, 0.15),
            command=self._submeter,
            parent=self.card
        )

        self.btn_alternar = DirectButton(
            text="Não tem conta? CRIAR CONTA",
            scale=0.035,
            text_fg=COR_TEXTO,
            frameColor=(0, 0, 0, 0),
            relief=None,
            pos=(0, 0, -0.55),
            command=self._alternar_modo,
            parent=self.card
        )

        self._definir_modo("login")

    def _criar_card(self):
        project_root = Path(__file__).resolve().parent.parent.parent
        img_path = project_root / "app" / "assets" / "panels" / "login_register.png"

        if img_path.exists():
            self.card = DirectFrame(
                image=str(Filename.fromOsSpecific(str(img_path))),
                image_scale=(0.8, 1, 0.9),
                frameSize=(-0.8, 0.8, -0.9, 0.9),
                frameColor=(0, 0, 0, 0),
                pos=(0, 0, 0),
                parent=self.ui_root
            )
            self.card.setTransparency(TransparencyAttrib.MAlpha)
        else:
            # Fallback: container sólido se a arte não estiver na pasta de assets.
            self.card = DirectFrame(
                frameColor=(0.1, 0.12, 0.15, 0.95),
                frameSize=(-0.6, 0.6, -0.7, 0.7),
                pos=(0, 0, 0),
                parent=self.ui_root
            )
        self.elementos.append(self.card)

    def _criar_campo(self, nome, rotulo, obscured=False):
        # O rótulo fica fora do campo: o texto digitado é sempre o dado real
        # (antes o "Usuário" do initialText seria enviado como se fosse o nome).
        label = DirectLabel(
            text=rotulo,
            scale=0.035,
            text_fg=COR_TEXTO,
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            parent=self.card
        )
        entry = DirectEntry(
            scale=0.045,
            width=14,
            numLines=1,
            focus=0,
            initialText="",
            frameColor=(0.2, 0.2, 0.2, 1),
            text_fg=(1, 1, 1, 1),
            obscured=1 if obscured else 0,
            command=self._ao_apertar_enter,
            parent=self.card
        )
        self.campos[nome] = (label, entry)

    # ----------------------------------------------------------
    # MODOS (login / cadastro)
    # ----------------------------------------------------------

    def _definir_modo(self, modo):
        self.modo = modo

        for nome, (label, entry) in self.campos.items():
            z = LAYOUT[modo].get(nome)
            if z is None:
                label.hide()
                entry.hide()
            else:
                label.setPos(-0.32, 0, z + 0.065)
                entry.setPos(-0.32, 0, z)
                label.show()
                entry.show()

        if modo == "login":
            self.btn_principal["text"] = "ENTRAR"
            self.btn_alternar["text"] = "Não tem conta? CRIAR CONTA"
        else:
            self.btn_principal["text"] = "CADASTRAR"
            self.btn_alternar["text"] = "Já tem conta? ENTRAR"

        self.lbl_mensagem["text"] = ""

    def _alternar_modo(self):
        self._definir_modo("register" if self.modo == "login" else "login")

    def _ao_apertar_enter(self, _texto):
        self._submeter()

    def _submeter(self):
        if self.modo == "login":
            self.login_controller.auth()
        else:
            self.user_controller.save()

    # ----------------------------------------------------------
    # CONTRATO COM OS CONTROLLERS
    # ----------------------------------------------------------

    def read_login_data(self):
        return self.campos["email"][1].get(), self.campos["password"][1].get()

    def read_register_data(self):
        return (
            self.campos["username"][1].get(),
            self.campos["password"][1].get(),
            self.campos["email"][1].get()
        )

    def show_message(self, message, success=True):
        self.lbl_mensagem["text"] = message
        self.lbl_mensagem["text_fg"] = COR_SUCESSO if success else COR_ERRO

    # ----------------------------------------------------------
    # CALLBACKS
    # ----------------------------------------------------------

    def _ao_autenticar(self, user):
        self.view_manager.usuario_logado = user
        self.view_manager.mudar_tela_base("home")

    def _ao_cadastrar(self, user):
        # Após o cadastro o jogador volta ao login já com o e-mail preenchido.
        self._definir_modo("login")
        self.campos["email"][1].enterText(user.email)
        self.campos["password"][1].enterText("")
        self.campos["username"][1].enterText("")
        self.show_message("Conta criada! Faça login para entrar.")

    def destruir(self):
        for elemento in self.elementos:
            elemento.destroy()
        self.elementos.clear()
        self.campos.clear()
