import sys
from pathlib import Path
from direct.showbase.ShowBase import ShowBase

# Garante que a raiz do projeto está no sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

# Imports dos gerenciadores e apenas da view de login por enquanto
from app.controller.view_manager import ViewManager
from app.view.login_register_view import LoginRegisterView

class CSGachaMain(ShowBase):
    def __init__(self):
        super().__init__()

        # Configurações de exibição do Panda3D
        self.disableMouse()
        self.win.setClearColor((0.05, 0.05, 0.07, 1.0))

        # 1. Instancia o ViewManager
        self.view_manager = ViewManager(self.render2d, self)

        # 2. Registra apenas a rota de login por enquanto
        self.registrar_rotas()

        # 3. Exibe a tela inicial de Login
        self.view_manager.mudar_tela_base("login")

    def registrar_rotas(self):
        """Registra exclusivamente o login até que as outras views sejam refatoradas."""
        self.view_manager.registrar_tela_base("login", LoginRegisterView)


if __name__ == "__main__":
    app = CSGachaMain()
    app.run()