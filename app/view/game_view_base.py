from direct.gui.DirectGui import DirectButton, DirectFrame, DirectLabel
from panda3d.core import TextNode

# (texto do menu, nome da rota registrada no ViewManager)
# O botão só aparece se a rota existir. Para tirar um item do menu, apague a linha.
MENU_ITEMS = [
    ("INVENTÁRIO", "inventory"),
    ("EQUIPAMENTO", "equipment"),
    ("HOME", "home"),
    ("LOJA", "shop"),
    ("NOTÍCIAS", "news"),
]

COR_MENU = (0.85, 0.85, 0.85, 1)
COR_SEPARADOR = (0.4, 0.4, 0.4, 1)


class GameViewBase:
    """Base das telas com cenário 3D + header (Home, Inventário, ...).

    Cada tela filha só implementa construir_conteudo().
    """

    def __init__(self, ui_root, view_manager):
        self.ui_root = ui_root
        self.view_manager = view_manager
        self.elementos = []

    def construir_tela(self):
        if self.view_manager.backdrop:
            self.view_manager.backdrop.mostrar()
        self._construir_header()
        self.construir_conteudo()

    def construir_conteudo(self):
        raise NotImplementedError

    def destruir(self):
        for elemento in self.elementos:
            elemento.destroy()
        self.elementos.clear()

    # ----------------------------------------------------------

    def _construir_header(self):
        # Barra de fundo escura e translúcida no topo de ponta a ponta
        self.header_frame = DirectFrame(
            frameColor=(0.12, 0.14, 0.16, 0.85),
            frameSize=(-2.0, 2.0, -0.07, 0.07),
            pos=(0, 0, 0.93),
            parent=self.ui_root
        )
        self.elementos.append(self.header_frame)

        itens = [
            (texto, rota)
            for texto, rota in MENU_ITEMS
            if self.view_manager.tem_tela(rota)
        ]

        start_x = -0.45
        spacing = 0.28

        for i, (texto, rota) in enumerate(itens):
            pos_x = start_x + (i * spacing)

            DirectButton(
                text=texto,
                text_scale=0.035,
                text_fg=COR_MENU,
                text_roll=0,
                frameColor=(0, 0, 0, 0),
                relief=None,
                pos=(pos_x, 0, -0.012),
                parent=self.header_frame,
                command=self.view_manager.mudar_tela_base,
                extraArgs=[rota]
            )

            # Separador vertical "|" (só visual) exceto após o último item
            if i < len(itens) - 1:
                DirectLabel(
                    text="|",
                    text_scale=0.035,
                    text_fg=COR_SEPARADOR,
                    frameColor=(0, 0, 0, 0),
                    pos=(pos_x + 0.14, 0, -0.012),
                    parent=self.header_frame
                )

        user = self.view_manager.usuario_logado
        DirectLabel(
            text=f"{user.username}  |  {user.balance:.2f}",
            text_scale=0.035,
            text_fg=COR_MENU,
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            pos=(-1.25, 0, -0.012),
            parent=self.header_frame
        )

        DirectButton(
            text="SAIR",
            text_scale=0.035,
            text_fg=COR_MENU,
            frameColor=(0, 0, 0, 0),
            relief=None,
            pos=(1.15, 0, -0.012),
            parent=self.header_frame,
            command=self.view_manager.sair
        )
