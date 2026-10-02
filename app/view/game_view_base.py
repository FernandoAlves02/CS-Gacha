from direct.gui.DirectGui import DirectButton, DirectFrame, DirectLabel
from panda3d.core import TextNode

from app.core.game_rules import format_money
from app.view.ui_kit import COR_LARANJA, KitUI

# (texto do menu, nome da rota registrada no ViewManager)
# O botão só aparece se a rota existir. Para tirar um item do menu, apague a linha.
MENU_ITEMS = [
    ("INVENTÁRIO", "inventory"),
    ("EQUIPAMENTO", "equipment"),
    ("HOME", "home"),
    ("MERCADO", "shop"),
    ("NOTÍCIAS", "news"),
]

COR_MENU = (0.85, 0.85, 0.85, 1)
COR_MENU_ATIVO = (1, 1, 1, 1)
COR_SEPARADOR = (0.4, 0.4, 0.4, 1)


class GameViewBase:
    """Base das telas com cenário 3D + header (Home, Inventário, ...).

    Cada tela filha só implementa construir_conteudo() e informa a sua ROTA
    (o item do menu dessa tela fica destacado).
    """

    ROTA = None

    def __init__(self, ui_root, view_manager):
        self.ui_root = ui_root
        self.view_manager = view_manager
        self.elementos = []
        self.ui = KitUI(view_manager.app)        # fontes e peças no estilo CS2

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

    def atualizar_saldo(self):
        """Reescreve "usuário | R$ saldo" no header (chamado depois de comprar, abrir ou vender)."""
        user = self.view_manager.usuario_logado
        self.lbl_usuario["text"] = f"{user.username}  |  {format_money(user.balance)}"

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

        # Menu centralizado: cada item ocupa a largura do seu texto + um espaço fixo
        espaco = 0.12
        fonte = self.ui.fonte(negrito=True, escala=0.035)
        larguras = [self.ui.largura_texto(texto, 0.035, negrito=True) for texto, _rota in itens]
        x = -(sum(larguras) + espaco * (len(itens) - 1)) / 2

        for i, (texto, rota) in enumerate(itens):
            pos_x = x + larguras[i] / 2
            x += larguras[i] + espaco
            ativo = rota == self.ROTA

            DirectButton(
                text=texto,
                text_scale=0.035,
                text_font=fonte,
                text_fg=COR_MENU_ATIVO if ativo else COR_MENU,
                text2_fg=COR_MENU_ATIVO,             # estado 2 = mouse em cima
                text_roll=0,
                frameColor=(0, 0, 0, 0),
                relief=None,
                pos=(pos_x, 0, -0.012),
                parent=self.header_frame,
                command=self.view_manager.mudar_tela_base,
                extraArgs=[rota]
            )

            # Tela atual: sublinhado laranja embaixo do item do menu
            if ativo:
                largura = larguras[i]
                DirectFrame(
                    frameColor=COR_LARANJA,
                    frameSize=(-largura / 2, largura / 2, -0.004, 0.004),
                    pos=(pos_x, 0, -0.045),
                    parent=self.header_frame
                )

            # Separador vertical "|" (só visual) exceto após o último item
            if i < len(itens) - 1:
                DirectLabel(
                    text="|",
                    text_scale=0.035,
                    text_fg=COR_SEPARADOR,
                    frameColor=(0, 0, 0, 0),
                    pos=(x - espaco / 2, 0, -0.012),
                    parent=self.header_frame
                )

        user = self.view_manager.usuario_logado
        self.lbl_usuario = DirectLabel(
            text=f"{user.username}  |  {format_money(user.balance)}",
            text_scale=0.035,
            text_font=self.ui.fonte(escala=0.035),
            text_fg=COR_MENU,
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            pos=(-1.25, 0, -0.012),
            parent=self.header_frame
        )

        DirectButton(
            text="SAIR",
            text_scale=0.035,
            text_font=fonte,
            text_fg=COR_MENU,
            text2_fg=COR_MENU_ATIVO,
            frameColor=(0, 0, 0, 0),
            relief=None,
            pos=(1.15, 0, -0.012),
            parent=self.header_frame,
            command=self.view_manager.sair
        )
