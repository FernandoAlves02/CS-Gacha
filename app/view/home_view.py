from pathlib import Path
from direct.showbase.ShowBase import ShowBase
from direct.gui.DirectGui import DirectFrame, DirectButton
from panda3d.core import Point3, Vec3, Filename, DirectionalLight, AmbientLight, TransparencyAttrib, Vec4
import simplepbr

class HomeView(ShowBase):
    def __init__(self):
        super().__init__()

        # 1. PBR com exposição reduzida para escurecer a imagem e dar contraste
        self.pipeline = simplepbr.init(
            max_lights=8,
            use_normal_maps=True,
            exposure=0.3
        )

        self.setBackgroundColor(0.2, 0.4, 0.7, 1)

        # 2. Assets
        project_root = Path(__file__).resolve().parent.parent.parent
        map_path = project_root / "app" / "Assets" / "Maps" / "de_mirage.glb"
        ct_path = project_root / "app" / "Assets" / "Characters" / "ctm_spawnpoint.glb"

        panda_map_path = Filename.fromOsSpecific(str(map_path))
        panda_ct_path = Filename.fromOsSpecific(str(ct_path))

        # 3. Carregamento dos modelos
        self.map_node = self.loader.loadModel(panda_map_path)
        self.map_node.reparentTo(self.render)
        self.map_node.setPos(0, 0, 0)
        self.map_node.setHpr(0, 90, 0)

        # Matar transparências e emissões estouradas
        self.map_node.setTransparency(TransparencyAttrib.M_none, 1)
        self.map_node.setDepthWrite(True, 1)
        self.map_node.setColorScale(Vec4(0.85, 0.8, 0.75, 1.0), 1) # Aplica filtro sutil de tom alaranjado/desértico no modelo

        

        # 4. Câmera
        self.disableMouse()  
        self.camera.setPos(Point3(-33.60, 19.90, -2.70))
        self.camera.setHpr(Vec3(130, 0, 0))
        self.camLens.setFov(80)

        self.ct_node = self.loader.loadModel(panda_ct_path)
        self.ct_node.reparentTo(self.camera)

        self.ct_node.setPos(0.1, 3.2, -1.2) 
        self.ct_node.setHpr(2, 90, 0)

        # 5. Iluminação de Alto Contraste
        self.setup_lights()

        # 6. UI
        self.setup_ui()

    def setup_lights(self):
        # Sombra fria e fechada
        alight = AmbientLight('alight')
        alight.setColor((0.05, 0.05, 0.08, 1))
        alnp = self.render.attachNewNode(alight)
        self.render.setLight(alnp)

        # Sol desértico concentrado
        dlight = DirectionalLight('dlight')
        dlight.setColor((1.8, 1.3, 0.8, 1))
        dlnp = self.render.attachNewNode(dlight)
        dlnp.setHpr(-45, -35, 0)
        self.render.setLight(dlnp)

    def setup_ui(self):
        # Barra de fundo escura e translúcida no topo de ponta a ponta
        self.header_frame = DirectFrame(
            frameColor=(0.12, 0.14, 0.16, 0.85),
            frameSize=(-2.0, 2.0, -0.07, 0.07),
            pos=(0, 0, 0.93),
            parent=self.aspect2d
        )

        # Itens do menu centralizados/alinhados à direita conforme a referência
        # Ordem: INVENTÁRIO | EQUIPAMENTO | HOME | LOJA | NOTÍCIAS
        
        button_data = [
            ("INVENTÁRIO", self.open_inventory),
            ("EQUIPAMENTO", self.open_equipment),
            ("HOME", self.open_home),
            ("LOJA", self.open_shop),
            ("NOTÍCIAS", self.open_news)
        ]

        start_x = -0.45
        spacing = 0.28

        for i, (text, cmd) in enumerate(button_data):
            pos_x = start_x + (i * spacing)
            
            # Botão de texto estilizado
            DirectButton(
                text=text,
                text_scale=0.035,
                text_fg=(0.85, 0.85, 0.85, 1),
                text_roll=0,
                frameColor=(0, 0, 0, 0), # Invisível para parecer apenas texto flutuante
                relief=None,
                pos=(pos_x, 0, -0.012),
                parent=self.header_frame,
                command=cmd
            )

            # Adiciona o separador vertical "|" exceto após o último item
            if i < len(button_data) - 1:
                DirectButton(
                    text="|",
                    text_scale=0.035,
                    text_fg=(0.4, 0.4, 0.4, 1),
                    frameColor=(0, 0, 0, 0),
                    relief=None,
                    pos=(pos_x + 0.14, 0, -0.012),
                    parent=self.header_frame,
                    state="disabled" # Apenas visual
                )

    def open_inventory(self):
        print("Abrindo Inventário...")

    def open_equipment(self):
        print("Abrindo Equipamento...")

    def open_home(self):
        print("Abrindo Home...")

    def open_shop(self):
        print("Abrindo Loja...")

    def open_news(self):
        print("Abrindo Notícias...")

if __name__ == "__main__":
    app = HomeView()
    app.run()