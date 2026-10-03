import logging
import sys
from pathlib import Path

from direct.showbase.ShowBase import ShowBase
from panda3d.core import WindowProperties, loadPrcFileData

# Configurações da janela. Precisam vir ANTES de criar o ShowBase.
loadPrcFileData("", "\n".join([
    "window-title CS Gacha",
    "win-size 1280 720",            # 16:9, mesma proporção da arte da tela de login
    # Sem isto o Panda3D reduz as imagens para potência de 2 (ex.: 1671 px -> 1024 px)
    # e a interface fica borrada.
    "textures-power-2 none",
]))

# Garante que a raiz do projeto está no sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from app.controller.view_manager import ViewManager
from app.core import i18n, preferencias
from app.core.database import Database
from app.dao.collection_dao import Collection_DAO
from app.dao.inventory_dao import Inventory_DAO
from app.dao.rarity_dao import Rarity_DAO
from app.dao.skin_catalog_dao import Skin_Catalog_DAO
from app.dao.user_dao import User_DAO
from app.view.home_view import HomeView
from app.view.inventory_view import InventoryView
from app.view.login_register_view import LoginRegisterView
from app.view.market_view import MarketView
from app.view.scene_backdrop import SceneBackdrop
from app.view.sons import Sons

logging.basicConfig(level=logging.INFO)


class CSGachaMain(ShowBase):
    def __init__(self):
        super().__init__()

        # Configurações de exibição do Panda3D
        self.disableMouse()
        self.setBackgroundColor(0.05, 0.05, 0.07, 1.0)

        # 1. ViewManager desenha em aspect2d (mantém a proporção dos elementos;
        #    em render2d tudo ficaria esticado em janelas que não são quadradas)
        self.view_manager = ViewManager(self.aspect2d, self)

        # 2. Dependências compartilhadas entre as telas (todos os DAOs usam o mesmo banco)
        database = Database()
        self.view_manager.user_dao = User_DAO(database)
        self.view_manager.collection_dao = Collection_DAO(database)
        self.view_manager.skin_catalog_dao = Skin_Catalog_DAO(database)
        self.view_manager.inventory_dao = Inventory_DAO(database)
        self.view_manager.rarity_dao = Rarity_DAO(database)
        self.view_manager.backdrop = SceneBackdrop(self)

        # 3. Rotas
        self.registrar_rotas()

        # 4. Preferências deste PC (idioma, moeda, tela cheia, sons, animações),
        #    sons e música (antes das telas: o clique vale para todos os botões) e a tela inicial
        i18n.carregar_preferencia()
        preferencias.carregar()
        self.sons = Sons(self)
        if preferencias.obter("tela_cheia"):
            self.aplicar_tela_cheia(True)
        self.accept("f11", self.alternar_tela_cheia)          # atalho; também está nas CONFIGURAÇÕES
        self.view_manager.mudar_tela_base("login")

    def aplicar_tela_cheia(self, ligar):
        """Tela cheia (na resolução do monitor) ou janela de 1280x720 no centro da tela."""
        if self.win is None or not hasattr(self.win, "requestProperties"):
            return                                   # janela fora da tela (testes)
        propriedades = WindowProperties()
        propriedades.setFullscreen(ligar)
        if ligar:
            largura, altura = self.pipe.getDisplayWidth(), self.pipe.getDisplayHeight()
            if largura > 0 and altura > 0:
                propriedades.setSize(largura, altura)
        else:
            propriedades.setSize(1280, 720)
            propriedades.setOrigin(-2, -2)           # -2 = centralizada
        self.win.requestProperties(propriedades)
        if ligar:
            # se o Windows recusar a tela cheia, volta para a janela normal e guarda isso
            self.taskMgr.doMethodLater(0.5, self._conferir_tela_cheia, "conferir_tela_cheia")

    def _conferir_tela_cheia(self, task):
        if self.win is not None and not self.win.getProperties().getFullscreen():
            logging.getLogger(__name__).warning("O Windows não aceitou a tela cheia; voltando para a janela.")
            preferencias.definir("tela_cheia", False)
            self.aplicar_tela_cheia(False)
        return task.done

    def alternar_tela_cheia(self):
        """F11 (ou CONFIGURAÇÕES): liga/desliga a tela cheia e lembra a escolha."""
        ligar = not preferencias.obter("tela_cheia")
        preferencias.definir("tela_cheia", ligar)
        self.aplicar_tela_cheia(ligar)

    def registrar_rotas(self):
        self.view_manager.registrar_tela_base("login", LoginRegisterView)
        self.view_manager.registrar_tela_base("home", HomeView)
        self.view_manager.registrar_tela_base("inventory", InventoryView)
        self.view_manager.registrar_tela_base("shop", MarketView)      # botão MERCADO do header


if __name__ == "__main__":
    app = CSGachaMain()
    app.run()
