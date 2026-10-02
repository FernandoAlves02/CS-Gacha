import logging
import sys
from pathlib import Path

from direct.showbase.ShowBase import ShowBase
from panda3d.core import loadPrcFileData

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

        # 4. Tela inicial
        self.view_manager.mudar_tela_base("login")

    def registrar_rotas(self):
        self.view_manager.registrar_tela_base("login", LoginRegisterView)
        self.view_manager.registrar_tela_base("home", HomeView)
        self.view_manager.registrar_tela_base("inventory", InventoryView)
        self.view_manager.registrar_tela_base("shop", MarketView)      # botão MERCADO do header


if __name__ == "__main__":
    app = CSGachaMain()
    app.run()
