from direct.gui.DirectGui import DirectButton, DirectFrame, DirectLabel
from panda3d.core import TextNode

from app.core import i18n
from app.core.game_rules import format_money
from app.core.i18n import t
from app.view.ui_kit import COR_LARANJA, DIREITA, KitUI

# (texto do menu, nome da rota registrada no ViewManager)
# O botão só aparece se a rota existir. Para tirar um item do menu, apague a linha.
# O texto aparece traduzido (t) quando o jogo está em inglês.
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
        self.janela_conta = None                 # pop-up "Minha conta" (clique no nome)

    def construir_tela(self):
        if self.view_manager.backdrop:
            self.view_manager.backdrop.mostrar()
        self._construir_header()
        self.construir_conteudo()

    def construir_conteudo(self):
        raise NotImplementedError

    def destruir(self):
        if self.janela_conta is not None:
            self.janela_conta.fechar()
        for elemento in self.elementos:
            elemento.destroy()
        self.elementos.clear()
        self.ui.destruir()

    def modal_do_header_aberto(self):
        """True enquanto o pop-up "Minha conta" estiver aberto (as telas ignoram
        a roda do mouse e as setas nesse tempo)."""
        return self.janela_conta is not None and self.janela_conta.aberta

    def abrir_minha_conta(self):
        from app.view.account_window import JanelaMinhaConta   # import aqui: evita import circular
        if not self.modal_do_header_aberto():
            self.janela_conta = JanelaMinhaConta(self, ao_fechar=self._ao_fechar_conta)

    def _ao_fechar_conta(self):
        self.janela_conta = None

    def trocar_idioma(self, codigo):
        """PT | EN do header: troca o idioma e redesenha esta mesma tela."""
        i18n.definir_idioma(codigo)
        self.view_manager.mudar_tela_base(self.ROTA)

    def atualizar_saldo(self):
        """Reescreve "usuário | R$ saldo" no header (chamado depois de comprar, abrir ou vender)."""
        user = self.view_manager.usuario_logado
        self.lbl_usuario["text"] = f"{user.username}  |  {format_money(user.balance)}"
        self.lbl_usuario.resetFrameSize()          # área clicável acompanha o texto novo

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
            (t(texto), rota)
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

        # Nome + saldo: clicar abre "Minha conta" (ver e editar os dados)
        user = self.view_manager.usuario_logado
        self.lbl_usuario = DirectButton(
            text=f"{user.username}  |  {format_money(user.balance)}",
            text_scale=0.035,
            text_font=self.ui.fonte(escala=0.035),
            text_fg=COR_MENU,
            text2_fg=COR_LARANJA,                # mouse em cima: laranja (é clicável)
            text_align=TextNode.ALeft,
            frameColor=(0, 0, 0, 0),
            relief=None,
            pressEffect=0,
            pos=(-1.25, 0, -0.012),
            parent=self.header_frame,
            command=self.abrir_minha_conta
        )

        # Idioma (PT | EN), à esquerda do SAIR
        self.ui.seletor_idioma(self.header_frame, 0.98, -0.012, self.trocar_idioma,
                               escala=0.03, alinhar=DIREITA)

        DirectButton(
            text=t("SAIR"),
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
