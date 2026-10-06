from direct.showbase.ShowBase import ShowBase
from direct.gui.DirectGui import DirectButton, DirectFrame, DirectLabel
from direct.interval.IntervalGlobal import Sequence, Func, Wait
from panda3d.core import (
    TextNode,
    Vec4,
    NodePath,
    CardMaker,
    TransparencyAttrib,
)
import random
import os


# ============================================================
# CONFIGURACAO
# ============================================================

WIDTH = 1280
HEIGHT = 720

CARD_WIDTH = 0.20
CARD_HEIGHT = 0.34
CARD_GAP = 0.025
CARD_SPACING = CARD_WIDTH + CARD_GAP


# ============================================================
# SKINS
# ============================================================

SKINS = [
    {
        "name": "CRIMSON AK",
        "rarity": "LENDARIA",
        "color": (1.0, 0.18, 0.25, 1),
        "image": "assets/skins/crimson_ak.png",
    },
    {
        "name": "NEON M4",
        "rarity": "EPICA",
        "color": (0.65, 0.20, 1.0, 1),
        "image": "assets/skins/neon_m4.png",
    },
    {
        "name": "CYBER GLOCK",
        "rarity": "RARA",
        "color": (0.15, 0.45, 1.0, 1),
        "image": "assets/skins/cyber_glock.png",
    },
    {
        "name": "EMERALD USP",
        "rarity": "INCOMUM",
        "color": (0.10, 0.85, 0.40, 1),
        "image": "assets/skins/emerald_usp.png",
    },
    {
        "name": "SHADOW P250",
        "rarity": "COMUM",
        "color": (0.55, 0.60, 0.68, 1),
        "image": "assets/skins/shadow_p250.png",
    },
    {
        "name": "GOLDEN DEAGLE",
        "rarity": "LENDARIA",
        "color": (1.0, 0.65, 0.05, 1),
        "image": "assets/skins/golden_deagle.png",
    },
    {
        "name": "VIOLET AWP",
        "rarity": "EPICA",
        "color": (0.80, 0.10, 0.85, 1),
        "image": "assets/skins/violet_awp.png",
    },
    {
        "name": "ICE MP9",
        "rarity": "RARA",
        "color": (0.05, 0.75, 0.90, 1),
        "image": "assets/skins/ice_mp9.png",
    },
]


# ============================================================
# CAIXAS
# ============================================================

CASES = [
    {
        "name": "STARTER CASE",
        "info": "6 SKINS",
        "color": (0.15, 0.45, 1.0, 1),
    },
    {
        "name": "NEON CASE",
        "info": "8 SKINS",
        "color": (0.70, 0.20, 1.0, 1),
    },
    {
        "name": "LEGEND CASE",
        "info": "12 SKINS",
        "color": (1.0, 0.60, 0.05, 1),
    },
]


# ============================================================
# APLICACAO
# ============================================================

class CaseGame(ShowBase):

    def __init__(self):

        ShowBase.__init__(self)

        self.disableMouse()

        # Resolucao
        props = self.win.getProperties()

        if not props.hasSize():
            self.win.setSize(WIDTH, HEIGHT)

        self.win.setClearColor(
            Vec4(0.018, 0.024, 0.040, 1)
        )

        # Dados
        self.inventory = []
        self.history = []

        self.current_case = None
        self.current_result = None

        # Roleta
        self.roll_cards = []
        self.roll_sequence = None
        self.card_container = None

        # ====================================================
        # INTERFACE
        # ====================================================

        self.create_background()

        # IMPORTANTE:
        # paginas primeiro, sidebar depois.
        # Assim a sidebar fica por cima e recebe clique.
        self.create_pages()
        self.create_sidebar()

        self.show_home()


    # ========================================================
    # FUNDO
    # ========================================================

    def create_background(self):

        self.background = DirectFrame(
            frameColor=(0.018, 0.024, 0.040, 1),
            frameSize=(-1, 1, -1, 1),
        )

        self.background.reparentTo(self.aspect2d)


    # ========================================================
    # PAGINAS
    # ========================================================

    def create_pages(self):

        self.home_page = NodePath("home_page")
        self.inventory_page = NodePath("inventory_page")
        self.history_page = NodePath("history_page")
        self.open_page = NodePath("open_page")

        self.home_page.reparentTo(self.aspect2d)
        self.inventory_page.reparentTo(self.aspect2d)
        self.history_page.reparentTo(self.aspect2d)
        self.open_page.reparentTo(self.aspect2d)


    def clear_page(self, page):

        for child in page.getChildren():
            child.removeNode()


    def hide_all_pages(self):

        self.home_page.hide()
        self.inventory_page.hide()
        self.history_page.hide()
        self.open_page.hide()


    # ========================================================
    # SIDEBAR
    # ========================================================

    def create_sidebar(self):

        self.sidebar = DirectFrame(
            frameColor=(0.030, 0.038, 0.060, 1),
            frameSize=(-0.17, 0.17, -1, 1),
            pos=(-0.83, 0, 0),
        )

        # Logo
        DirectLabel(
            parent=self.sidebar,
            text="CS GACHA",
            scale=0.060,
            text_fg=(1, 0.25, 0.32, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            pos=(0, 0, 0.82),
        )

        DirectLabel(
            parent=self.sidebar,
            text="SKIN GACHA",
            scale=0.022,
            text_fg=(0.35, 0.40, 0.50, 1),
            text_align=TextNode.ACenter,
            frameColor=(0, 0, 0, 0),
            pos=(0, 0, 0.75),
        )

        # Menu
        self.create_menu_button(
            "INICIO",
            0.58,
            self.show_home
        )

        self.create_menu_button(
            "INVENTARIO",
            0.43,
            self.show_inventory
        )

        self.create_menu_button(
            "HISTORICO",
            0.28,
            self.show_history
        )

        # Coloca sidebar na frente
        self.sidebar.reparentTo(self.aspect2d)
        self.sidebar.show()


    def create_menu_button(
        self,
        text,
        z,
        command
    ):

        return DirectButton(
            parent=self.sidebar,

            text=text,

            scale=0.040,

            text_fg=(0.75, 0.78, 0.85, 1),

            text1_fg=(1, 1, 1, 1),

            frameColor=(
                (0.055, 0.070, 0.105, 1),
                (0.090, 0.110, 0.160, 1),
                (0.130, 0.150, 0.210, 1),
                (0.055, 0.070, 0.105, 1),
            ),

            frameSize=(
                -2.6,
                2.6,
                -0.68,
                0.68
            ),

            pos=(0, 0, z),

            command=command,
        )


    # ========================================================
    # TITULO
    # ========================================================

    def create_title(
        self,
        parent,
        title,
        description
    ):

        DirectLabel(
            parent=parent,

            text=title,

            scale=0.070,

            text_fg=(1, 1, 1, 1),

            text_align=TextNode.ALeft,

            frameColor=(0, 0, 0, 0),

            pos=(-0.48, 0, 0.72),
        )

        DirectLabel(
            parent=parent,

            text=description,

            scale=0.028,

            text_fg=(0.40, 0.45, 0.55, 1),

            text_align=TextNode.ALeft,

            frameColor=(0, 0, 0, 0),

            pos=(-0.48, 0, 0.64),
        )


    # ========================================================
    # HOME
    # ========================================================

    def show_home(self):

        # Para roleta se estiver rodando
        if self.roll_sequence:
            self.roll_sequence.finish()
            self.roll_sequence = None

        self.hide_all_pages()

        self.clear_page(
            self.home_page
        )

        self.create_title(
            self.home_page,
            "CAIXAS",
            "Escolha uma caixa para abrir"
        )

        positions = [
            (-0.25, 0.20),
            (0.05, 0.20),
            (0.35, 0.20),
        ]

        for i, case in enumerate(CASES):

            x, z = positions[i]

            self.create_case_card(
                self.home_page,
                case["name"],
                case["info"],
                x,
                z,
                case["color"],
            )

        self.home_page.show()


    # ========================================================
    # CARD DA CAIXA
    # ========================================================

    def create_case_card(
        self,
        parent,
        name,
        info,
        x,
        z,
        color
    ):

        card = DirectFrame(
            parent=parent,

            frameColor=(
                0.045,
                0.055,
                0.085,
                1
            ),

            frameSize=(
                -0.135,
                0.135,
                -0.30,
                0.30
            ),

            pos=(x, 0, z),
        )

        # Icone sem caractere Unicode
        DirectLabel(
            parent=card,

            text="[ CASE ]",

            scale=0.040,

            text_fg=color,

            frameColor=(0, 0, 0, 0),

            text_align=TextNode.ACenter,

            pos=(0, 0, 0.12),
        )

        DirectLabel(
            parent=card,

            text=name,

            scale=0.036,

            text_fg=(1, 1, 1, 1),

            frameColor=(0, 0, 0, 0),

            text_align=TextNode.ACenter,

            pos=(0, 0, -0.05),
        )

        DirectLabel(
            parent=card,

            text=info,

            scale=0.026,

            text_fg=(0.40, 0.45, 0.55, 1),

            frameColor=(0, 0, 0, 0),

            text_align=TextNode.ACenter,

            pos=(0, 0, -0.12),
        )

        DirectButton(
            parent=card,

            text="ABRIR",

            scale=0.037,

            text_fg=(1, 1, 1, 1),

            frameColor=(
                color,
                color,
                color,
                color,
            ),

            frameSize=(
                -2.0,
                2.0,
                -0.65,
                0.65
            ),

            pos=(0, 0, -0.22),

            command=self.open_case,

            extraArgs=[name],
        )


    # ========================================================
    # TELA DE ABERTURA
    # ========================================================

    def open_case(self, case_name):

        if self.roll_sequence:

            self.roll_sequence.finish()

            self.roll_sequence = None

        self.hide_all_pages()

        self.clear_page(
            self.open_page
        )

        self.current_case = case_name

        self.create_title(
            self.open_page,

            case_name,

            "Abra a caixa e tente conseguir uma skin rara"
        )

        # ====================================================
        # AREA DA ROLETA
        # ====================================================

        self.roll_frame = DirectFrame(
            parent=self.open_page,

            frameColor=(
                0.010,
                0.016,
                0.028,
                1
            ),

            frameSize=(
                -0.72,
                0.72,
                -0.27,
                0.27
            ),

            pos=(0.12, 0, 0.15),
        )

        # Borda superior
        DirectFrame(
            parent=self.roll_frame,

            frameColor=(0.08, 0.10, 0.15, 1),

            frameSize=(
                -0.72,
                0.72,
                -0.008,
                0.008
            ),

            pos=(0, 0, 0.27),
        )

        # Borda inferior
        DirectFrame(
            parent=self.roll_frame,

            frameColor=(0.08, 0.10, 0.15, 1),

            frameSize=(
                -0.72,
                0.72,
                -0.008,
                0.008
            ),

            pos=(0, 0, -0.27),
        )

        # ====================================================
        # MARCADOR CENTRAL
        # ====================================================

        DirectFrame(
            parent=self.roll_frame,

            frameColor=(
                1.0,
                0.16,
                0.20,
                1
            ),

            frameSize=(
                -0.006,
                0.006,
                -0.27,
                0.27
            ),

            pos=(0, 0, 0),
        )

        DirectLabel(
            parent=self.roll_frame,

            text="V",

            scale=0.040,

            text_fg=(
                1,
                0.20,
                0.25,
                1
            ),

            frameColor=(0, 0, 0, 0),

            pos=(0, 0, 0.30),
        )

        # ====================================================
        # CONTAINER
        # ====================================================

        self.card_container = NodePath(
            "card_container"
        )

        self.card_container.reparentTo(
            self.roll_frame
        )

        # ====================================================
        # BOTAO ABRIR
        # ====================================================

        self.open_button = DirectButton(
            parent=self.open_page,

            text="ABRIR CAIXA",

            scale=0.043,

            text_fg=(1, 1, 1, 1),

            frameColor=(
                (1, 0.18, 0.24, 1),
                (1, 0.28, 0.34, 1),
                (0.80, 0.10, 0.16, 1),
                (1, 0.18, 0.24, 1),
            ),

            frameSize=(
                -2.4,
                2.4,
                -0.75,
                0.75
            ),

            pos=(0.12, 0, -0.35),

            command=self.start_roll,
        )

        # ====================================================
        # BOTAO VOLTAR
        # ====================================================

        DirectButton(
            parent=self.open_page,

            text="VOLTAR",

            scale=0.038,

            text_fg=(
                0.70,
                0.74,
                0.82,
                1
            ),

            frameColor=(
                0.07,
                0.08,
                0.12,
                1
            ),

            frameSize=(
                -2.0,
                2.0,
                -0.70,
                0.70
            ),

            pos=(-0.40, 0, -0.35),

            command=self.show_home,
        )

        # ====================================================
        # RESULTADO
        # ====================================================

        self.result_label = DirectLabel(
            parent=self.open_page,

            text="",

            scale=0.038,

            text_fg=(1, 1, 1, 1),

            frameColor=(0, 0, 0, 0),

            text_align=TextNode.ACenter,

            pos=(0.12, 0, -0.47),
        )

        self.open_page.show()


    # ========================================================
    # CRIAR CARD DA ROLETA
    # ========================================================

    def create_roll_card(
        self,
        skin,
        x
    ):

        card = DirectFrame(
            parent=self.card_container,

            frameColor=(
                0.045,
                0.055,
                0.085,
                1
            ),

            frameSize=(
                -CARD_WIDTH / 2,
                CARD_WIDTH / 2,

                -CARD_HEIGHT / 2,
                CARD_HEIGHT / 2
            ),

            pos=(x, 0, 0),
        )

        # ----------------------------------------------------
        # BORDA COLORIDA
        # ----------------------------------------------------

        DirectFrame(
            parent=card,

            frameColor=skin["color"],

            frameSize=(
                -CARD_WIDTH / 2,
                CARD_WIDTH / 2,
                -0.008,
                0.008
            ),

            pos=(
                0,
                0,
                -CARD_HEIGHT / 2 + 0.008
            ),
        )

        # ----------------------------------------------------
        # IMAGEM
        # ----------------------------------------------------

        image_path = skin.get("image")

        if image_path and os.path.exists(image_path):

            try:

                cm = CardMaker(
                    "skin_image"
                )

                cm.setFrame(
                    -0.085,
                    0.085,
                    -0.10,
                    0.10
                )

                image_card = NodePath(
                    cm.generate()
                )

                image_card.reparentTo(
                    card
                )

                image_card.setPos(
                    0,
                    0,
                    0.04
                )

                texture = self.loader.loadTexture(
                    image_path
                )

                image_card.setTexture(
                    texture,
                    1
                )

                image_card.setTransparency(
                    TransparencyAttrib.MAlpha
                )

            except Exception:

                self.create_skin_placeholder(
                    card,
                    skin
                )

        else:

            self.create_skin_placeholder(
                card,
                skin
            )

        # ----------------------------------------------------
        # NOME
        # ----------------------------------------------------

        DirectLabel(
            parent=card,

            text=skin["name"],

            scale=0.025,

            text_fg=skin["color"],

            frameColor=(0, 0, 0, 0),

            text_align=TextNode.ACenter,

            pos=(0, 0, -0.105),
        )

        # ----------------------------------------------------
        # RARIDADE
        # ----------------------------------------------------

        DirectLabel(
            parent=card,

            text=skin["rarity"],

            scale=0.018,

            text_fg=(
                0.55,
                0.60,
                0.70,
                1
            ),

            frameColor=(0, 0, 0, 0),

            text_align=TextNode.ACenter,

            pos=(0, 0, -0.145),
        )


    # ========================================================
    # PLACEHOLDER
    # ========================================================

    def create_skin_placeholder(
        self,
        parent,
        skin
    ):

        DirectLabel(
            parent=parent,

            text="[ SKIN ]",

            scale=0.032,

            text_fg=skin["color"],

            frameColor=(0, 0, 0, 0),

            text_align=TextNode.ACenter,

            pos=(0, 0, 0.04),
        )


    # ========================================================
    # INICIAR ROLETA
    # ========================================================

    def start_roll(self):

        if self.roll_sequence:
            return

        self.open_button["state"] = "disabled"

        self.result_label["text"] = ""

        # ====================================================
        # RESULTADO
        # ====================================================

        self.current_result = random.choice(
            SKINS
        )

        # ====================================================
        # LIMPAR CARDS
        # ====================================================

        for child in self.card_container.getChildren():

            child.removeNode()

        # ====================================================
        # GERAR SEQUENCIA
        # ====================================================

        self.roll_cards = []

        total_cards = 65

        # Resultado fica no final da roleta
        winner_index = 55

        for i in range(total_cards):

            if i == winner_index:

                skin = self.current_result

            else:

                skin = random.choice(SKINS)

            self.roll_cards.append(
                skin
            )

        # ====================================================
        # POSICIONAR CARDS
        # ====================================================

        start_x = -1.45

        for i, skin in enumerate(
            self.roll_cards
        ):

            x = (
                start_x
                + i * CARD_SPACING
            )

            self.create_roll_card(
                skin,
                x
            )

        # ====================================================
        # POSICAO DO VENCEDOR
        # ====================================================

        winner_x = (
            start_x
            + winner_index * CARD_SPACING
        )

        # Centraliza vencedor
        target_x = -winner_x

        # ====================================================
        # ANIMACAO
        # ====================================================

        self.roll_sequence = Sequence(

            # Inicio
            Wait(0.20),

            # Movimento
            self.card_container.posInterval(
                5.5,

                (
                    target_x,
                    0,
                    0
                ),

                blendType="easeInOut",
            ),

            # Pequena pausa
            Wait(0.35),

            Func(
                self.finish_roll
            ),
        )

        self.roll_sequence.start()


    # ========================================================
    # RESULTADO
    # ========================================================

    def finish_roll(self):

        self.roll_sequence = None

        skin = self.current_result

        self.inventory.append(
            skin
        )

        self.history.append(
            skin
        )

        self.result_label["text"] = (
            "VOCE GANHOU: "
            + skin["name"]
            + "  ["
            + skin["rarity"]
            + "]"
        )

        self.result_label["text_fg"] = (
            skin["color"]
        )

        self.open_button["state"] = "normal"


    # ========================================================
    # INVENTARIO
    # ========================================================

    def show_inventory(self):

        if self.roll_sequence:

            self.roll_sequence.finish()
            self.roll_sequence = None

        self.hide_all_pages()

        self.clear_page(
            self.inventory_page
        )

        self.create_title(
            self.inventory_page,

            "INVENTARIO",

            "Skins obtidas"
        )

        if not self.inventory:

            DirectLabel(
                parent=self.inventory_page,

                text="Seu inventario esta vazio.",

                scale=0.045,

                text_fg=(
                    0.40,
                    0.45,
                    0.55,
                    1
                ),

                frameColor=(0, 0, 0, 0),

                pos=(0.10, 0, 0.20),
            )

        else:

            start_x = -0.40
            start_z = 0.45

            for i, skin in enumerate(
                self.inventory
            ):

                row = i // 3
                col = i % 3

                self.create_inventory_card(
                    self.inventory_page,
                    skin,
                    start_x + col * 0.30,
                    start_z - row * 0.28
                )

        self.inventory_page.show()


    # ========================================================
    # CARD INVENTARIO
    # ========================================================

    def create_inventory_card(
        self,
        parent,
        skin,
        x,
        z
    ):

        card = DirectFrame(
            parent=parent,

            frameColor=(
                0.045,
                0.055,
                0.085,
                1
            ),

            frameSize=(
                -0.135,
                0.135,
                -0.10,
                0.10
            ),

            pos=(x, 0, z),
        )

        DirectLabel(
            parent=card,

            text=skin["name"],

            scale=0.032,

            text_fg=skin["color"],

            frameColor=(0, 0, 0, 0),

            text_align=TextNode.ACenter,

            pos=(0, 0, 0.035),
        )

        DirectLabel(
            parent=card,

            text=skin["rarity"],

            scale=0.023,

            text_fg=(
                0.50,
                0.55,
                0.65,
                1
            ),

            frameColor=(0, 0, 0, 0),

            text_align=TextNode.ACenter,

            pos=(0, 0, -0.035),
        )


    # ========================================================
    # HISTORICO
    # ========================================================

    def show_history(self):

        if self.roll_sequence:

            self.roll_sequence.finish()
            self.roll_sequence = None

        self.hide_all_pages()

        self.clear_page(
            self.history_page
        )

        self.create_title(
            self.history_page,

            "HISTORICO",

            "Ultimas skins obtidas"
        )

        if not self.history:

            DirectLabel(
                parent=self.history_page,

                text="Nenhuma abertura realizada.",

                scale=0.045,

                text_fg=(
                    0.40,
                    0.45,
                    0.55,
                    1
                ),

                frameColor=(0, 0, 0, 0),

                pos=(0.10, 0, 0.20),
            )

        else:

            z = 0.48

            for skin in reversed(
                self.history
            ):

                DirectLabel(
                    parent=self.history_page,

                    text=(
                        skin["name"]
                        + "     -     "
                        + skin["rarity"]
                    ),

                    scale=0.038,

                    text_fg=skin["color"],

                    frameColor=(
                        0.045,
                        0.055,
                        0.085,
                        1
                    ),

                    frameSize=(
                        -5,
                        5,
                        -0.9,
                        0.9
                    ),

                    text_align=TextNode.ALeft,

                    pos=(0.05, 0, z),
                )

                z -= 0.12

        self.history_page.show()


# ============================================================
# INICIAR
# ============================================================

if __name__ == "__main__":

    game = CaseGame()

    game.run()
