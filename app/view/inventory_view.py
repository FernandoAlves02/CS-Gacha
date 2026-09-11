from pathlib import Path
from direct.showbase.ShowBase import ShowBase
from direct.gui.DirectGui import DirectFrame, DirectButton
from panda3d.core import Point3, Vec3, Filename, DirectionalLight, AmbientLight, TransparencyAttrib, Vec4
import simplepbr

class InventoryView(ShowBase):
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
        map_path = project_root / "app" / "assets" / "maps" / "de_mirage_d.glb"
        ct_path = project_root / "app" / "assets" / "characters" / "ctm_spawnpoint.glb"

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
        self.camera.setPos(Point3(-33.60, 19.90, -1.70))
        self.camera.setHpr(Vec3(130, 0, 0))
        self.camLens.setFov(80)

        self.ct_node = self.loader.loadModel(panda_ct_path)
        self.ct_node.reparentTo(self.camera)

        self.ct_node.setPos(1.2, 3.5, -1.7) 
        self.ct_node.setHpr(0, 90, 0)

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
        # 1. Header Principal (Global)
        self.header_frame = DirectFrame(
            frameColor=(0.12, 0.14, 0.16, 0.85),
            frameSize=(-2.0, 2.0, -0.07, 0.07),
            pos=(0, 0, 0.93),
            parent=self.aspect2d
        )

        button_data = [
            ("INVENTÁRIO", None),
            ("EQUIPAMENTO", None),
            ("HOME", None),
            ("LOJA", None),
            ("NOTÍCIAS", None)
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

        # 2. Máscara Escura do Inventário (Efeito de vidro esfumaçado escuro)
        self.inventory_mask = DirectFrame(
            frameColor=(0.08, 0.09, 0.11, 0.80),
            frameSize=(-2.0, 2.0, -2.80, 0.82),
            pos=(0, 0, 0.05),
            parent=self.aspect2d
        )

        # 3. Sub-header de Filtros do Inventário
        categories = ["TUDO", "EQUIPAMENTO", "ARTES GRÁFICAS", "RECIPIENTES", "DECORAÇÃO", "CONTRATO DE TROCA", "MERCADO"]
        sub_start_x = -0.85
        for i, cat in enumerate(categories):
            DirectButton(
                text=cat,
                text_scale=0.025,
                text_fg=(0.7, 0.7, 0.7, 1),
                frameColor=(0, 0, 0, 0),
                relief=None,
                pos=(sub_start_x + (i * 0.25), 0, 0.70),
                parent=self.inventory_mask
            )

        # 4. Grid de Cards de Itens (Exemplo estrutural com loop)
        self.create_item_grid()

    def create_item_grid(self):
        # Configuração inicial de uma grade 4x3 simulada para os cards de itens
        columns = 5
        rows = 3
        spacing_x = 0.35
        spacing_y = 0.32
        start_x = -0.75
        start_y = 0.45

        for r in range(rows):
            for c in range(columns):
                pos_x = start_x + (c * spacing_x)
                pos_y = start_y - (r * spacing_y)

                # Card individual do item
                DirectFrame(
                    frameColor=(0.18, 0.20, 0.23, 0.9),
                    frameSize=(-0.15, 0.15, -0.13, 0.13),
                    pos=(pos_x, 0, pos_y),
                    parent=self.inventory_mask
                )

if __name__ == "__main__":
    app = InventoryView()
    app.run()