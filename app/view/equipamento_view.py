from pathlib import Path
from direct.showbase.ShowBase import ShowBase
from direct.gui.DirectGui import DirectFrame, DirectButton, DirectLabel, DirectScrolledFrame
from panda3d.core import Point3, Vec3, Filename, DirectionalLight, AmbientLight, TransparencyAttrib, Vec4
import simplepbr


class LoadoutView(ShowBase):
    def __init__(self):
        super().__init__()

        # 1. PBR Setup
        self.pipeline = simplepbr.init(max_lights=8, use_normal_maps=True, exposure=0.3)
        self.setBackgroundColor(0.2, 0.4, 0.7, 1)

        # 2. Resolução de Caminhos de Arquivos
        self.project_root = Path(__file__).resolve().parent.parent.parent
        self.assets_dir = self.project_root / "app" / "Assets"

        map_path = self.assets_dir / "Maps" / "de_mirage.glb"
        panda_map_path = Filename.fromOsSpecific(str(map_path))

        # 3. Carregamento do Mapa 3D
        try:
            self.map_node = self.loader.loadModel(panda_map_path)
            self.map_node.reparentTo(self.render)
            self.map_node.setPos(0, 0, 0)
            self.map_node.setHpr(0, 90, 0)
            self.map_node.setTransparency(TransparencyAttrib.M_none, 1)
            self.map_node.setDepthWrite(True, 1)
            self.map_node.setColorScale(Vec4(0.85, 0.8, 0.75, 1.0), 1)
        except Exception as e:
            print(f"Aviso: Não foi possível carregar o mapa: {e}")

        # 4. Configuração da Câmera
        self.disableMouse()
        self.camera.setPos(Point3(-33.60, 19.90, -2.70))
        self.camera.setHpr(Vec3(130, 0, 0))
        self.camLens.setFov(80)

        # 5. Dados de Estado e Inventário Global
        self.current_team = "CT"
        self.selected_slot = (0, 0) # Slot ativo selecionado (coluna, linha)
        self.character_node = None
        self.grid_buttons = {}

        # Mapeamento do Loadout Ativo
        self.loadout_data = {
            "CT": [
                ["USP-S | Cyrex", "P250 | Ripple", "Five-SeveN", "Dual Berettas", "Desert Eagle"],
                ["MP9 | Bioleak", "UMP-45", "P90 | Grim", "PP-Bizon", "MP7"],
                ["M4A1-S | Briefing", "FAMAS", "AUG | Aristocrat", "SSG 08", "AWP | Atheris"]
            ],
            "TR": [
                ["Glock-18 | Water", "P250 | Valence", "Tec-9 | Isaac", "Dual Berettas", "Desert Eagle"],
                ["MAC-10 | Lapis", "UMP-45", "P90 | Grim", "PP-Bizon", "MP7"],
                ["AK-47 | Redline", "Galil AR", "SG 553", "SSG 08", "AWP | Atheris"]
            ]
        }

        # Itens disponíveis no Inventário (Geral)
        self.inventory_items = [
            "AK-47 | Redline", "M4A1-S | Briefing", "AWP | Atheris", 
            "USP-S | Cyrex", "Glock-18 | Water", "Desert Eagle | Printstream",
            "Karambit | Fade", "Specialist Gloves", "Service Medal 2024",
            "P250 | Ripple", "MP9 | Bioleak", "SSG 08 | Dragonfire"
        ]

        # 6. Inicialização de Elementos
        self.setup_lights()
        self.setup_ui_header()
        self.setup_ui_loadout()
        self.setup_ui_inventory()
        self.load_character(self.current_team)

    def setup_lights(self):
        alight = AmbientLight('alight')
        alight.setColor((0.05, 0.05, 0.08, 1))
        self.render.setLight(self.render.attachNewNode(alight))

        dlight = DirectionalLight('dlight')
        dlight.setColor((1.8, 1.3, 0.8, 1))
        dlnp = self.render.attachNewNode(dlight)
        dlnp.setHpr(-45, -35, 0)
        self.render.setLight(dlnp)

    def setup_ui_header(self):
        self.header_frame = DirectFrame(
            frameColor=(0.12, 0.14, 0.16, 0.85),
            frameSize=(-2.0, 2.0, -0.07, 0.07),
            pos=(0, 0, 0.93),
            parent=self.aspect2d
        )

        button_data = [
            ("INVENTÁRIO", self.open_inventory),
            ("EQUIPAMENTO", self.open_equipment),
            ("HOME", self.open_home),
            ("LOJA", self.open_shop),
            ("NOTÍCIAS", self.open_news)
        ]

        start_x, spacing = -0.56, 0.28
        for i, (text, cmd) in enumerate(button_data):
            pos_x = start_x + (i * spacing)
            DirectButton(
                text=text,
                text_scale=0.035,
                text_fg=(0.85, 0.85, 0.85, 1),
                frameColor=(0, 0, 0, 0),
                relief=None,
                pos=(pos_x, 0, -0.012),
                parent=self.header_frame,
                command=cmd
            )
            if i < len(button_data) - 1:
                DirectLabel(
                    text="|",
                    text_scale=0.035,
                    text_fg=(0.4, 0.4, 0.4, 1),
                    frameColor=(0, 0, 0, 0),
                    relief=None,
                    pos=(pos_x + (spacing / 2), 0, -0.012),
                    parent=self.header_frame
                )

    def setup_ui_loadout(self):
        # Grade Central
        self.grid_frame = DirectFrame(
            frameColor=(0.05, 0.07, 0.09, 0.65),
            frameSize=(-0.55, 0.55, -0.42, 0.42),
            pos=(0, 0, 0.22),
            parent=self.aspect2d
        )

        # Botão CT
        self.btn_ct = DirectButton(
            text="EQUIP CT",
            text_scale=0.035,
            text_fg=(1, 1, 1, 1),
            frameColor=(0.2, 0.4, 0.8, 0.6),
            frameSize=(-0.2, 0.2, -0.04, 0.04),
            pos=(-1.0, 0, 0.7),
            parent=self.aspect2d,
            command=self.switch_team,
            extraArgs=["CT"]
        )

        # Botão TR
        self.btn_tr = DirectButton(
            text="EQUIP TR",
            text_scale=0.035,
            text_fg=(1, 1, 1, 1),
            frameColor=(0.8, 0.4, 0.2, 0.6),
            frameSize=(-0.2, 0.2, -0.04, 0.04),
            pos=(1.0, 0, 0.7),
            parent=self.aspect2d,
            command=self.switch_team,
            extraArgs=["TR"]
        )

        # Slots da Grade (3x5)
        start_x, start_y = -0.36, 0.32
        step_x, step_y = 0.36, -0.155

        for row in range(5):
            for col in range(3):
                x = start_x + (col * step_x)
                y = start_y + (row * step_y)

                btn = DirectButton(
                    text="",
                    text_scale=0.022,
                    text_fg=(0.9, 0.9, 0.9, 1),
                    frameColor=(0.12, 0.15, 0.18, 0.85),
                    frameSize=(-0.16, 0.16, -0.065, 0.065),
                    pos=(x, 0, y),
                    parent=self.grid_frame,
                    command=self.select_slot,
                    extraArgs=[col, row]
                )
                self.grid_buttons[(col, row)] = btn

        self.update_grid_weapons()

    def setup_ui_inventory(self):
        # Frame de Rolagem do Inventário Inferior
        self.inv_frame = DirectScrolledFrame(
            frameColor=(0.08, 0.09, 0.11, 0.85),
            canvasSize=(0, 2.8, -0.18, 0.18),
            frameSize=(-1.3, 1.3, -0.22, 0.22),
            pos=(0, 0, -0.68),
            scrollBarWidth=0.03,
            horizontalScroll_frameColor=(0.2, 0.2, 0.2, 0.5),
            horizontalScroll_thumb_frameColor=(0.5, 0.5, 0.5, 0.8),
            parent=self.aspect2d
        )

        # Oculta a barra vertical (apenas rolagem horizontal)
        self.inv_frame.verticalScroll.hide()

        start_x = 0.15
        spacing_x = 0.23

        # Preenche o Inventário Inferior
        for idx, item_name in enumerate(self.inventory_items):
            x_pos = start_x + (idx * spacing_x)
            DirectButton(
                text=item_name,
                text_scale=0.02,
                text_fg=(0.9, 0.9, 0.9, 1),
                text_wordwrap=7,
                frameColor=(0.15, 0.18, 0.22, 0.9),
                frameSize=(-0.1, 0.1, -0.15, 0.15),
                pos=(x_pos, 0, 0),
                parent=self.inv_frame.getCanvas(),
                command=self.equip_item_to_slot,
                extraArgs=[item_name]
            )

    def load_character(self, team):
        if self.character_node:
            self.character_node.removeNode()

        char_filename = "ctm_spawnpoint.glb" if team == "CT" else "t_spawnpoint.glb"
        char_path = self.assets_dir / "Characters" / char_filename
        panda_path = Filename.fromOsSpecific(str(char_path))

        try:
            self.character_node = self.loader.loadModel(panda_path)
        except Exception as e:
            self.character_node = self.render.attachNewNode(f"placeholder_{team}")

        self.character_node.reparentTo(self.camera)
        self.character_node.setPos(0.1, 3.2, -1.2)
        self.character_node.setHpr(2, 90, 0)

    def switch_team(self, team):
        if self.current_team == team:
            return
        self.current_team = team
        self.load_character(team)
        self.update_grid_weapons()

    def select_slot(self, col, row):
        self.selected_slot = (col, row)
        # Destaque nos botões da grade
        for (c, r), btn in self.grid_buttons.items():
            if (c, r) == (col, row):
                btn["frameColor"] = (0.3, 0.5, 0.8, 0.9)
            else:
                btn["frameColor"] = (0.12, 0.15, 0.18, 0.85)

    def equip_item_to_slot(self, item_name):
        col, row = self.selected_slot
        self.loadout_data[self.current_team][col][row] = item_name
        self.update_grid_weapons()
        print(f"Equipado: '{item_name}' no slot [{col}, {row}] do {self.current_team}")

    def update_grid_weapons(self):
        weapons = self.loadout_data[self.current_team]
        for row in range(5):
            for col in range(3):
                item_name = weapons[col][row]
                btn = self.grid_buttons[(col, row)]
                btn["text"] = item_name

    def open_inventory(self): print("Abrindo Inventário...")
    def open_equipment(self): print("Abrindo Equipamento...")
    def open_home(self): print("Abrindo Home...")
    def open_shop(self): print("Abrindo Loja...")
    def open_news(self): print("Abrindo Notícias...")


if __name__ == "__main__":
    app = LoadoutView()
    app.run()