from pathlib import Path
from direct.gui.DirectGui import DirectFrame, DirectEntry, DirectButton, OnscreenText
from panda3d.core import Filename, TextNode

class LoginRegisterView:
    def __init__(self, render2d, view_manager):
        self.render2d = render2d
        self.view_manager = view_manager
        self.elementos = []

    def construir_tela(self):
        # 1. Resolução do caminho da imagem usando Path absoluto
        project_root = Path(__file__).resolve().parent.parent.parent
        img_path = project_root / "app" / "assets" / "panels" / "login_register.png"

        # Fallback se a imagem não existir na pasta de assets
        if img_path.exists():
            panda_img_path = Filename.fromOsSpecific(str(img_path))
            self.card = DirectFrame(
                image=str(panda_img_path),
                image_scale=(0.8, 1, 0.9),
                frameSize=(-0.8, 0.8, -0.9, 0.9),
                pos=(0, 0, 0),
                parent=self.render2d
            )
        else:
            # Container sólido simples
            self.card = DirectFrame(
                frameColor=(0.1, 0.12, 0.15, 0.95),
                frameSize=(-0.6, 0.6, -0.7, 0.7),
                pos=(0, 0, 0),
                parent=self.render2d
            )
        self.elementos.append(self.card)

        # 2. Entradas corrigidas usando text_fg no lugar de textColor
        self.input_usuario = DirectEntry(
            scale=0.045,
            pos=(-0.4, 0, 0.15),
            initialText="",
            numLines=1,
            focus=1,
            width=18,
            text_fg=(1, 1, 1, 1),
            parent=self.card
        )

        self.input_senha = DirectEntry(
            scale=0.045,
            pos=(-0.4, 0, -0.05),
            initialText="",
            numLines=1,
            obscured=1,
            width=18,
            text_fg=(1, 1, 1, 1),
            parent=self.card
        )

        # Botão de Login
        self.btn_login = DirectButton(
            text="ENTRAR",
            scale=0.045,
            pos=(0, 0, -0.3),
            pad=(0.4, 0.15),
            command=self.fazer_login,
            parent=self.card
        )

    def fazer_login(self):
        print("Login acionado")

    def destruir(self):
        for elemento in self.elementos:
            elemento.destroy()
        self.elementos.clear()