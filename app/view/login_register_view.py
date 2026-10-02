"""Tela de LOGIN e CADASTRO, no layout do mockup do grupo.

Como o layout funciona
----------------------
A arte de fundo (app/assets/ui/login_bg.jpg, 1671 x 941 px) já tem o logo.
Todas as posições abaixo foram MEDIDAS em pixels nessa arte e convertidas
para as unidades do Panda3D pela constante PX. Todos os elementos ficam
dentro de um nó "raiz" que é escalado junto com o fundo, então o formulário
continua alinhado embaixo do logo em qualquer tamanho de janela.

Unidades do Panda3D (aspect2d): a altura da janela vai de -1 (baixo) a +1
(topo). Como a arte tem 941 px de altura -> 1 px da arte = 2 / 941 unidades.

A tela tem dois modos:
  - "login":    Usuário + Senha            -> botão ENTRAR
  - "register": Usuário + E-mail + Senha   -> botão CADASTRAR
O link embaixo do botão alterna entre os dois.
"""
import logging

from direct.gui.DirectGui import DGG, DirectButton, DirectEntry
from direct.gui.OnscreenImage import OnscreenImage
from direct.gui.OnscreenText import OnscreenText
from direct.showbase.DirectObject import DirectObject
from panda3d.core import (
    Filename,
    SamplerState,
    TextNode,
    TextProperties,
    TextPropertiesManager,
    TransparencyAttrib,
)

from app.controller.login_controller import Login_Controller
from app.controller.user_controller import User_Controller
from app.core.paths import FONTS_DIR, UI_DIR

logger = logging.getLogger(__name__)

# ======================================================================
# MEDIDAS (em pixels da arte de fundo, tiradas do mockup)
# ======================================================================
ARTE_W, ARTE_H = 1671, 941
PX = 2.0 / ARTE_H                 # 1 pixel da arte em unidades do Panda3D
CENTRO_X = ARTE_W / 2             # o formulário fica no centro horizontal

CAMPO_W, CAMPO_H = 443, 54        # caixa de texto
BOTAO_W, BOTAO_H = 443, 51        # botão laranja
ICONE_TAM = 32                    # ícone (pessoa, cadeado, envelope)
OLHO_TAM = 28                     # ícone de olho (mostrar/esconder senha)
ICONE_DX = -189.5                 # centro do ícone, em relação ao centro do campo
TEXTO_DX = -157.5                 # onde o texto digitado começa
OLHO_DX = 190                     # centro do ícone de olho (mostrar senha)

FONTE_CAMPO = 18                  # tamanho das letras (px da arte)
FONTE_BOTAO = 18
FONTE_LINK = 15
FONTE_MSG = 14.5
BASE_CAMPO = 6.5                  # a linha de base do texto fica 6,5 px abaixo do centro
BASE_BOTAO = 6.5

# Centro vertical (px da arte) de cada elemento, em cada modo.
LAYOUT = {
    "login": {
        "campos": {"usuario": 529.5, "senha": 598.5},
        "botao": 673.5, "link": 732.5, "msg": 772,
    },
    "register": {
        "campos": {"usuario": 529.5, "email": 598.5, "senha": 667.5},
        "botao": 742.5, "link": 801.5, "msg": 841,
    },
}

# nome do campo: (texto de exemplo, ícone, é senha?)
CAMPOS = {
    "usuario": ("Usuário", "icon_user.png", False),
    "email": ("E-mail", "icon_mail.png", False),
    "senha": ("Senha", "icon_lock.png", True),
}

TEXTOS = {
    "login": ("ENTRAR", "Não tem uma conta? ", "Registrar"),
    "register": ("CADASTRAR", "Já tem uma conta? ", "Entrar"),
}

# Cores (r, g, b, a) de 0 a 1, medidas no mockup
COR_PLACEHOLDER = (0.58, 0.58, 0.58, 1)
COR_TEXTO = (0.93, 0.93, 0.93, 1)
COR_LINK = (0.60, 0.60, 0.60, 1)
COR_LINK_HOVER = (0.82, 0.82, 0.82, 1)
COR_LARANJA = (0.93, 0.55, 0.10, 1)
COR_BOTAO_TEXTO = (0.07, 0.07, 0.07, 1)
COR_BOTAO_RESERVA = (0.96, 0.55, 0.12, 1)
COR_ERRO = (1.0, 0.38, 0.38, 1)
COR_SUCESSO = (0.38, 0.85, 0.48, 1)

TASK_PLACEHOLDER = "login_atualizar_placeholders"

# O cenário 3D da Home começa a carregar em segundo plano logo depois que o
# login aparece (o atraso deixa a tela de login ser desenhada primeiro).
TASK_PRECARREGAR = "login_precarregar_cenario"
ATRASO_PRECARREGAR = 0.5          # segundos


def _z(y_px):
    """Converte a posição vertical da arte (px, de cima para baixo) em unidades do Panda3D."""
    return (ARTE_H / 2 - y_px) * PX


class LoginRegisterView:
    def __init__(self, ui_root, view_manager):
        self.ui_root = ui_root
        self.view_manager = view_manager
        self.app = view_manager.app
        self.elementos = []          # widgets que precisam de destroy()
        self.campos = {}             # nome -> {"no", "entry", "placeholder", "foco", "mostrando_ph"}
        self.modo = "login"
        self.raiz = None
        self.eventos = DirectObject()  # recebe eventos de teclado/janela desta tela

    # ==================================================================
    # CONSTRUÇÃO
    # ==================================================================

    def construir_tela(self):
        if self.view_manager.backdrop:
            self.view_manager.backdrop.ocultar()

        user_dao = self.view_manager.user_dao
        self.login_controller = Login_Controller(user_dao, self, self._ao_autenticar)
        self.user_controller = User_Controller(user_dao, self, self._ao_cadastrar)

        self.fonte = self._fonte("Inter-Regular.otf")
        self.fonte_bold = self._fonte("Inter-Bold.otf")
        if self.fonte_bold is None:
            self.fonte_bold = self.fonte

        # Tudo fica dentro da raiz, que é escalada junto com o fundo.
        self.raiz = self.ui_root.attachNewNode("tela_login")

        fundo = self._imagem("login_bg.jpg", self.raiz, ARTE_W, ARTE_H, transparente=False)
        if fundo is None:
            logger.warning("Fundo do login não encontrado em %s", UI_DIR)

        for nome in CAMPOS:
            self._criar_campo(nome)
        self._criar_botao()
        self._criar_link()

        self.msg = OnscreenText(
            text="",
            parent=self.raiz,
            pos=(0, 0),
            scale=FONTE_MSG * PX,
            fg=COR_ERRO,
            align=TextNode.ACenter,
            wordwrap=CAMPO_W / FONTE_MSG,
            font=self.fonte,
            mayChange=True
        )
        self.elementos.append(self.msg)

        self._definir_modo("login")
        self._ajustar_escala()
        self._focar("usuario")

        # Eventos: redimensionar janela, TAB entre campos e a atualização dos placeholders.
        self.eventos.accept("aspectRatioChanged", self._ajustar_escala)
        self.eventos.accept("tab", self._proximo_campo, [1])
        self.eventos.accept("shift-tab", self._proximo_campo, [-1])
        self.app.taskMgr.add(self._atualizar_placeholders, TASK_PLACEHOLDER)

        # Enquanto o jogador digita, o cenário 3D da Home vai sendo carregado.
        if self.view_manager.backdrop:
            self.app.taskMgr.doMethodLater(
                ATRASO_PRECARREGAR, self._precarregar_cenario, TASK_PRECARREGAR
            )

    def _criar_campo(self, nome):
        """Monta um campo: fundo arredondado, fundo de foco (laranja), ícone,
        texto de exemplo (placeholder) e a caixa de digitação (DirectEntry)."""
        texto_exemplo, icone, eh_senha = CAMPOS[nome]

        # Nó do campo: tudo é posicionado em relação ao CENTRO do campo.
        no = self.raiz.attachNewNode(f"campo_{nome}")

        self._imagem("field.png", no, CAMPO_W, CAMPO_H)
        fundo_foco = self._imagem("field_focus.png", no, CAMPO_W, CAMPO_H)
        if fundo_foco is not None:
            fundo_foco.hide()
        self._imagem(icone, no, ICONE_TAM, ICONE_TAM, x_px=ICONE_DX)

        placeholder = OnscreenText(
            text=texto_exemplo,
            parent=no,
            pos=(TEXTO_DX * PX, -BASE_CAMPO * PX),
            scale=FONTE_CAMPO * PX,
            fg=COR_PLACEHOLDER,
            align=TextNode.ALeft,
            font=self.fonte,
            mayChange=True
        )
        self.elementos.append(placeholder)

        # Largura da área de digitação (no campo de senha, para antes do olho).
        limite_direito = OLHO_DX - 22 if eh_senha else CAMPO_W / 2 - 16
        largura = (limite_direito - TEXTO_DX) / FONTE_CAMPO

        entry = DirectEntry(
            parent=no,
            pos=(TEXTO_DX * PX, 0, -BASE_CAMPO * PX),
            scale=FONTE_CAMPO * PX,
            width=largura,
            numLines=1,
            overflow=1,                       # texto longo rola para o lado
            focus=0,
            obscured=1 if eh_senha else 0,    # senha aparece como ****
            entryFont=self.fonte,
            text_fg=COR_TEXTO,
            relief=DGG.FLAT,
            frameColor=(0, 0, 0, 0),          # invisível: o desenho é a imagem do campo
            # Área clicável = o campo inteiro (medida em "letras", por isso / FONTE_CAMPO)
            frameSize=(
                (-CAMPO_W / 2 - TEXTO_DX) / FONTE_CAMPO,
                largura,
                (-CAMPO_H / 2 + BASE_CAMPO) / FONTE_CAMPO,
                (CAMPO_H / 2 + BASE_CAMPO) / FONTE_CAMPO,
            ),
            command=self._ao_apertar_enter,
            focusInCommand=self._ao_mudar_foco,
            focusInExtraArgs=[nome, True],
            focusOutCommand=self._ao_mudar_foco,
            focusOutExtraArgs=[nome, False],
        )
        # O DirectEntry recalcula a própria área no final da construção;
        # reaplicamos a nossa para o campo inteiro (inclusive o ícone) ser clicável.
        entry.setFrameSize()
        self.elementos.append(entry)

        if eh_senha:
            self.tex_olho = self._textura("icon_eye.png")
            self.tex_olho_fechado = self._textura("icon_eye_off.png")
            self.btn_olho = DirectButton(
                parent=no,
                image=self.tex_olho,
                image_scale=(OLHO_TAM / 2 * PX, 1, OLHO_TAM / 2 * PX),
                relief=None,
                frameSize=(-18 * PX, 18 * PX, -18 * PX, 18 * PX),
                pos=(OLHO_DX * PX, 0, 0),
                command=self._alternar_senha
            )
            self.btn_olho.setTransparency(TransparencyAttrib.MAlpha)
            self.elementos.append(self.btn_olho)

        self.campos[nome] = {
            "no": no,
            "entry": entry,
            "placeholder": placeholder,
            "foco": fundo_foco,
            "mostrando_ph": True,
        }

    def _criar_botao(self):
        texturas = [self._textura(n) for n in
                    ("button.png", "button_pressed.png", "button_hover.png", "button_disabled.png")]
        meia_l, meia_a = BOTAO_W / 2 * PX, BOTAO_H / 2 * PX

        opcoes = dict(
            parent=self.raiz,
            frameSize=(-meia_l, meia_l, -meia_a, meia_a),
            text="ENTRAR",
            text_font=self.fonte_bold,
            text_fg=COR_BOTAO_TEXTO,
            text_scale=FONTE_BOTAO * PX,
            text_pos=(0, -BASE_BOTAO * PX),
            pressEffect=0,                    # o "afundar" vem da imagem pressionada
            command=self._submeter,
        )
        if all(texturas):
            # estados do DirectButton: (normal, pressionado, mouse em cima, desabilitado)
            opcoes.update(image=tuple(texturas), image_scale=(meia_l, 1, meia_a), relief=None)
        else:
            opcoes.update(relief=DGG.FLAT, frameColor=COR_BOTAO_RESERVA)   # reserva sem imagens

        self.btn_principal = DirectButton(**opcoes)
        self.btn_principal.setTransparency(TransparencyAttrib.MAlpha)
        self.elementos.append(self.btn_principal)

    def _criar_link(self):
        # Texto com duas cores: "\1cs_destaque\1...\2" pinta só o trecho do meio
        # de laranja (recurso TextProperties do Panda3D).
        destaque = TextProperties()
        destaque.setTextColor(*COR_LARANJA)
        TextPropertiesManager.getGlobalPtr().setProperties("cs_destaque", destaque)

        self.btn_link = DirectButton(
            parent=self.raiz,
            text="",
            text_font=self.fonte,
            text_fg=COR_LINK,
            text2_fg=COR_LINK_HOVER,          # estado 2 = mouse em cima
            text_scale=FONTE_LINK * PX,
            relief=None,
            pressEffect=0,
            command=self._alternar_modo
        )
        self.elementos.append(self.btn_link)

    # ==================================================================
    # AJUDANTES DE CARREGAMENTO
    # ==================================================================

    def _textura(self, arquivo):
        """Carrega uma imagem de app/assets/ui com filtro suave (mipmap).
        Devolve None se o arquivo não existir (a tela continua funcionando)."""
        caminho = UI_DIR / arquivo
        if not caminho.exists():
            logger.warning("Imagem não encontrada: %s", caminho)
            return None
        textura = self.app.loader.loadTexture(Filename.fromOsSpecific(str(caminho)))
        textura.setMinfilter(SamplerState.FT_linear_mipmap_linear)
        textura.setMagfilter(SamplerState.FT_linear)
        return textura

    def _imagem(self, arquivo, pai, largura_px, altura_px, x_px=0, transparente=True):
        """Coloca uma imagem centralizada em (x_px, 0) do nó pai, no tamanho em px da arte."""
        textura = self._textura(arquivo)
        if textura is None:
            return None
        imagem = OnscreenImage(
            image=textura,
            parent=pai,
            pos=(x_px * PX, 0, 0),
            scale=(largura_px / 2 * PX, 1, altura_px / 2 * PX)
        )
        if transparente:
            imagem.setTransparency(TransparencyAttrib.MAlpha)
        self.elementos.append(imagem)
        return imagem

    def _fonte(self, arquivo):
        """Carrega uma fonte de app/assets/fonts. Se falhar, usa a fonte padrão do Panda3D."""
        caminho = FONTS_DIR / arquivo
        try:
            fonte = self.app.loader.loadFont(Filename.fromOsSpecific(str(caminho)))
        except Exception:
            logger.warning("Fonte não carregada: %s (usando a padrão)", caminho)
            return None
        if hasattr(fonte, "setPixelsPerUnit"):
            fonte.setPixelsPerUnit(48)        # letras mais nítidas
        return fonte

    # ==================================================================
    # MODOS, FOCO E TECLADO
    # ==================================================================

    def _definir_modo(self, modo):
        self.modo = modo
        layout = LAYOUT[modo]

        for nome, campo in self.campos.items():
            y = layout["campos"].get(nome)
            if y is None:
                campo["entry"].guiItem.setFocus(False)
                campo["entry"].enterText("")
                campo["no"].hide()
            else:
                campo["no"].setPos(0, 0, _z(y))
                campo["no"].show()

        # a senha nunca é mantida ao trocar de modo
        self.campos["senha"]["entry"].enterText("")

        texto_botao, texto_link, texto_destaque = TEXTOS[modo]
        self.btn_principal["text"] = texto_botao
        self.btn_principal.setPos(0, 0, _z(layout["botao"]))

        self.btn_link["text"] = f"{texto_link}\1cs_destaque\1{texto_destaque}\2"
        self.btn_link.setPos(0, 0, _z(layout["link"]))
        self.btn_link.resetFrameSize()    # área clicável acompanha o novo texto

        self.msg.setPos(0, _z(layout["msg"]))
        self.msg.setText("")

    def _alternar_modo(self):
        self._definir_modo("register" if self.modo == "login" else "login")
        self._focar("usuario")

    def _alternar_senha(self):
        """Ícone de olho: mostra/esconde a senha."""
        entry = self.campos["senha"]["entry"]
        vai_mostrar = bool(entry["obscured"])
        entry["obscured"] = 0 if vai_mostrar else 1
        imagem = self.tex_olho_fechado if vai_mostrar else self.tex_olho
        if imagem is not None:
            self.btn_olho["image"] = imagem
            self.btn_olho.setTransparency(TransparencyAttrib.MAlpha)

    def _ao_mudar_foco(self, nome, focado):
        """Borda laranja no campo que está recebendo a digitação."""
        foco = self.campos[nome]["foco"]
        if foco is not None:
            foco.show() if focado else foco.hide()

    def _focar(self, nome):
        self.campos[nome]["entry"].guiItem.setFocus(True)

    def _proximo_campo(self, direcao):
        """TAB vai para o próximo campo; SHIFT+TAB volta."""
        visiveis = list(LAYOUT[self.modo]["campos"])
        atual = next(
            (i for i, nome in enumerate(visiveis) if self.campos[nome]["entry"].guiItem.getFocus()),
            -1
        )
        self._focar(visiveis[(atual + direcao) % len(visiveis)])

    def _atualizar_placeholders(self, task):
        """Roda a cada quadro: o texto de exemplo aparece só com o campo vazio
        (como o placeholder de um formulário na web)."""
        for campo in self.campos.values():
            vazio = campo["entry"].get() == ""
            if vazio != campo["mostrando_ph"]:
                campo["placeholder"].show() if vazio else campo["placeholder"].hide()
                campo["mostrando_ph"] = vazio
        return task.cont

    def _precarregar_cenario(self, task):
        # Não trava a tela: o SceneBackdrop carrega os modelos numa thread.
        self.view_manager.backdrop.precarregar()
        return task.done

    def _ao_apertar_enter(self, _texto):
        self._submeter()

    def _submeter(self):
        if self.modo == "login":
            self.login_controller.auth()
        else:
            self.user_controller.save()

    # ==================================================================
    # CONTRATO COM OS CONTROLLERS
    # ==================================================================

    def read_login_data(self):
        # o campo "Usuário" aceita nome de usuário OU e-mail (o controller decide)
        return self.campos["usuario"]["entry"].get(), self.campos["senha"]["entry"].get()

    def read_register_data(self):
        return (
            self.campos["usuario"]["entry"].get(),
            self.campos["senha"]["entry"].get(),
            self.campos["email"]["entry"].get()
        )

    def show_message(self, message, success=True):
        self.msg.setText(message)
        self.msg.setFg(COR_SUCESSO if success else COR_ERRO)

    # ==================================================================
    # CALLBACKS
    # ==================================================================

    def _ao_autenticar(self, user):
        self.view_manager.usuario_logado = user
        self.view_manager.mudar_tela_base("home")

    def _ao_cadastrar(self, user):
        # Após o cadastro volta ao login já com o usuário preenchido.
        self._definir_modo("login")
        self.campos["usuario"]["entry"].enterText(user.username)
        self._focar("senha")
        self.show_message("Conta criada! Digite sua senha para entrar.")

    # ==================================================================
    # TAMANHO DA JANELA E DESTRUIÇÃO
    # ==================================================================

    def _ajustar_escala(self):
        """Faz o fundo COBRIR a janela inteira sem distorcer (corta as sobras),
        e o formulário acompanha porque está dentro da mesma raiz."""
        if self.raiz is None:
            return
        proporcao = self.app.getAspectRatio()
        if proporcao >= 1:
            meia_largura, meia_altura = proporcao, 1.0
        else:
            meia_largura, meia_altura = 1.0, 1.0 / proporcao
        escala = max(meia_largura / (ARTE_W / ARTE_H), meia_altura)
        self.raiz.setScale(escala)

    def destruir(self):
        self.eventos.ignoreAll()
        self.app.taskMgr.remove(TASK_PLACEHOLDER)
        self.app.taskMgr.remove(TASK_PRECARREGAR)
        for elemento in self.elementos:
            elemento.destroy()
        self.elementos.clear()
        self.campos.clear()
        if self.raiz is not None:
            self.raiz.removeNode()
            self.raiz = None
