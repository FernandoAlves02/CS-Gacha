from direct.gui.DirectGui import DirectButton, DirectFrame, DirectLabel
from panda3d.core import PGItem, TextNode

from app.core.game_rules import format_money
from app.core.i18n import t
from app.view.ui_kit import COR_LARANJA, KitUI, ampliar_area

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

# Área clicável dos botões do header: a altura TODA da barra (não só as letras).
# Medidas a partir da linha do texto, que fica 0,012 abaixo do centro da barra.
HEADER_Z1, HEADER_Z2 = -0.058, 0.082


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
        self.janela_config = None                # pop-up CONFIGURAÇÕES (Extras 5)

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
        if self.janela_config is not None:
            self.janela_config.fechar()
        for elemento in self.elementos:
            elemento.destroy()
        self.elementos.clear()
        self.ui.destruir()

    def modal_do_header_aberto(self):
        """True enquanto "Minha conta" ou CONFIGURAÇÕES estiver aberto (as telas
        ignoram teclado e roda do mouse nesse tempo)."""
        return ((self.janela_conta is not None and self.janela_conta.aberta)
                or (self.janela_config is not None and self.janela_config.aberta))

    def abrir_minha_conta(self):
        from app.view.account_window import JanelaMinhaConta   # import aqui: evita import circular
        if not self.modal_do_header_aberto():
            self.janela_conta = JanelaMinhaConta(self, ao_fechar=self._ao_fechar_conta)

    def _ao_fechar_conta(self):
        self.janela_conta = None

    def abrir_configuracoes(self):
        from app.view.settings_window import JanelaConfiguracoes   # import aqui: evita import circular
        if not self.modal_do_header_aberto():
            foco = PGItem.getFocusItem()           # ex.: a busca do mercado: as teclas não vão para ela
            if foco is not None:
                foco.setFocus(False)
            self.janela_config = JanelaConfiguracoes(self, ao_fechar=self._ao_fechar_config)

    def _ao_fechar_config(self):
        self.janela_config = None

    def recriar_com_configuracoes(self):
        """Idioma/moeda mudaram: desenha esta tela de novo e reabre as CONFIGURAÇÕES por cima."""
        self.view_manager.mudar_tela_base(self.ROTA)
        nova = self.view_manager.tela_atual
        if nova is not None and hasattr(nova, "abrir_configuracoes"):
            nova.abrir_configuracoes()


    def atualizar_saldo(self):
        """Reescreve "usuário | R$ saldo" no header (chamado depois de comprar, abrir ou vender)."""
        user = self.view_manager.usuario_logado
        self.lbl_usuario["text"] = f"{user.username}  |  {format_money(user.balance)}"
        ampliar_area(self.lbl_usuario, 0.03, HEADER_Z1, HEADER_Z2)   # área clicável acompanha o texto novo

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

            botao = DirectButton(
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
            # clique vale na altura toda do header e até a metade do espaço até o vizinho
            ampliar_area(botao, espaco / 2 - 0.005, HEADER_Z1, HEADER_Z2)

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
        ampliar_area(self.lbl_usuario, 0.03, HEADER_Z1, HEADER_Z2)

        # CONFIGURAÇÕES (idioma, moeda, tela cheia, sons...), à esquerda do SAIR
        configuracoes = DirectButton(
            text=t("CONFIGURAÇÕES"),
            text_scale=0.03,
            text_font=self.ui.fonte(negrito=True, escala=0.03),
            text_fg=COR_MENU,
            text2_fg=COR_LARANJA,
            text_align=TextNode.ARight,
            frameColor=(0, 0, 0, 0),
            relief=None,
            pressEffect=0,
            pos=(0.98, 0, -0.012),
            parent=self.header_frame,
            command=self.abrir_configuracoes
        )
        ampliar_area(configuracoes, 0.03, HEADER_Z1, HEADER_Z2)

        sair = DirectButton(
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
        ampliar_area(sair, 0.05, HEADER_Z1, HEADER_Z2)
