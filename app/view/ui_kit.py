"""Kit de interface no estilo do CS2, usado pelas telas do Mercado e do Inventário.

Por que este arquivo existe
---------------------------
As telas novas usam as mesmas peças: cartões de item com a cor da raridade,
botões, abas, paginação, janela de confirmação, aviso que some sozinho e o
gráfico de preços. Elas ficam aqui uma vez só, e as telas só montam o layout.

Como a interface do Panda3D funciona (resumo para a apresentação)
----------------------------------------------------------------
- As telas são desenhadas no "aspect2d": a altura da janela vai de -1 (baixo)
  a +1 (topo). Numa janela 16:9 (1280x720) a largura vai de -1,78 a +1,78.
- O que aparece por cima é o que foi criado (ou reposicionado) por último.
- Todo widget do DirectGUI (DirectFrame, DirectButton...) precisa de
  destroy() quando a tela fecha. Regra usada nas telas: cada parte da tela é
  um "container" (DirectFrame sem desenho). Destruir o container destrói junto
  todos os widgets filhos; textos e imagens (OnscreenText/OnscreenImage) somem
  junto porque são nós filhos dele.
"""
import logging
from datetime import datetime

from direct.gui.DirectGui import DGG, DirectButton, DirectEntry, DirectFrame
from direct.gui.OnscreenImage import OnscreenImage
from direct.gui.OnscreenText import OnscreenText
from panda3d.core import (
    Filename,
    Geom,
    GeomNode,
    GeomTriangles,
    GeomVertexData,
    GeomVertexFormat,
    GeomVertexWriter,
    LineSegs,
    SamplerState,
    TextNode,
    TransparencyAttrib,
)

from app.core.game_rules import WEARS, format_money
from app.core.paths import FONTS_DIR, item_image_path

logger = logging.getLogger(__name__)

# ======================================================================
# CORES (r, g, b, alfa) de 0 a 1, no padrão escuro do CS2
# ======================================================================
COR_VEU = (0.03, 0.035, 0.045, 0.86)        # véu escuro por cima do cenário 3D
COR_PAINEL = (0.085, 0.095, 0.115, 0.96)
COR_PAINEL_CLARO = (0.12, 0.13, 0.155, 0.97)
COR_CARD = (0.115, 0.13, 0.155, 0.97)
COR_CARD_HOVER = (0.165, 0.18, 0.215, 1)
COR_CARD_PRESS = (0.095, 0.105, 0.125, 1)
COR_LINHA = (0.22, 0.24, 0.28, 1)           # bordas e divisórias
COR_TEXTO = (0.93, 0.93, 0.93, 1)
COR_TEXTO_2 = (0.63, 0.65, 0.69, 1)         # texto secundário
COR_TEXTO_3 = (0.43, 0.45, 0.49, 1)         # texto apagado
COR_LARANJA = (0.93, 0.55, 0.10, 1)         # mesma cor do botão ENTRAR do login
COR_VERDE = (0.38, 0.85, 0.48, 1)
COR_VERMELHO = (1.0, 0.38, 0.38, 1)
COR_OURO = (0.89, 0.70, 0.24, 1)            # itens ★ (facas e luvas), como no CS2

# Cores da barra de desgaste (Nova de Fábrica ... Veterana de Guerra), como no CS2
CORES_DESGASTE = (
    (0.36, 0.72, 0.36, 1),
    (0.60, 0.77, 0.33, 1),
    (0.86, 0.77, 0.28, 1),
    (0.88, 0.56, 0.25, 1),
    (0.82, 0.31, 0.26, 1),
)

# Estados de um DirectButton: (normal, pressionado, mouse em cima, desabilitado)
CORES_BOTAO = {
    "primario": ((0.93, 0.55, 0.10, 1), (0.80, 0.45, 0.06, 1), (1.0, 0.65, 0.22, 1), (0.30, 0.27, 0.23, 1)),
    "secundario": ((0.19, 0.205, 0.24, 1), (0.14, 0.15, 0.18, 1), (0.27, 0.29, 0.34, 1), (0.13, 0.14, 0.16, 1)),
}
TEXTO_BOTAO = {
    "primario": ((0.07, 0.07, 0.07, 1), (0.55, 0.52, 0.48, 1)),     # (normal, desabilitado)
    "secundario": (COR_TEXTO, COR_TEXTO_3),
}

ESQUERDA, CENTRO, DIREITA = TextNode.ALeft, TextNode.ACenter, TextNode.ARight

# A linha de base do texto fica um pouco abaixo do centro: multiplicar a escala
# por este número centraliza o texto na vertical (altura das maiúsculas da Inter).
BASE_TEXTO = 0.36


def carregar_fonte(app, caminho, pixels_por_unidade=48):
    """Carrega uma fonte .otf/.ttf. Devolve None se não der (a tela usa a fonte padrão).

    Dois cuidados do Panda3D:
    - loader.loadFont só aceita o caminho como TEXTO (um Filename dá TypeError).
      getFullpath() converte o caminho do Windows ("D:\\Code\\...") para o formato
      do Panda3D ("/d/Code/...");
    - a fonte fica guardada num cache (FontPool): a 2ª tela recebe o MESMO objeto,
      já com letras desenhadas, e aí setPixelsPerUnit dá AssertionError. Por isso
      a nitidez só é ajustada enquanto a fonte ainda não desenhou nenhuma letra.
    """
    try:
        fonte = app.loader.loadFont(Filename.fromOsSpecific(str(caminho)).getFullpath())
    except Exception:
        logger.warning("Fonte não carregada: %s (usando a padrão)", caminho)
        return None
    if fonte is None or not fonte.isValid():
        logger.warning("Fonte inválida: %s (usando a padrão)", caminho)
        return None
    if hasattr(fonte, "setPixelsPerUnit") and fonte.getNumPages() == 0:
        fonte.setPixelsPerUnit(pixels_por_unidade)      # letras mais nítidas
    return fonte


# Resolução das letras conforme o tamanho do texto na tela.
# A fonte desenha cada letra numa imagem (pixels por unidade = "ppu") e a placa
# de vídeo reduz essa imagem até o tamanho do texto. Reduzir demais (letras de
# 48 px mostradas com 8 px) faz traços finos como "l" e "I" sumirem. Por isso
# cada faixa de tamanho usa uma CÓPIA da fonte com o ppu adequado.
ARQUIVOS_FONTE = {False: "Inter-Regular.otf", True: "Inter-Bold.otf"}
_FONTES = {}          # (negrito, ppu) -> fonte, compartilhada por todas as telas


def ppu_para_escala(escala):
    if escala is None or escala >= 0.05:
        return 48          # títulos
    if escala >= 0.033:
        return 32          # textos normais e botões
    return 24              # legendas, preços pequenos


def fonte_inter(app, negrito=False, escala=None):
    """Fonte Inter pronta para um texto de tamanho `escala` (None = títulos)."""
    ppu = ppu_para_escala(escala)
    chave = (negrito, ppu)
    if chave not in _FONTES:
        base = carregar_fonte(app, FONTS_DIR / ARQUIVOS_FONTE[negrito])
        if base is None or ppu == 48 or not hasattr(base, "makeCopy"):
            fonte = base
        else:
            fonte = base.makeCopy()          # a cópia começa sem letras desenhadas
            fonte.setPixelsPerUnit(ppu)
        _FONTES[chave] = fonte
    return _FONTES[chave]


def limpar_nome(nome):
    """Tira do nome os caracteres que a fonte Inter não tem (ex.: chinês).
    "M4A4 | 龍王 (Dragon King)" -> "M4A4 | Dragon King"."""
    limpo = "".join(c for c in nome if ord(c) < 0x2E80)
    limpo = " ".join(limpo.split())
    if " | (" in limpo and limpo.endswith(")") and limpo.count("(") == 1:
        limpo = limpo.replace(" | (", " | ")[:-1]
    return limpo


def nome_em_duas_linhas(nome):
    """"AK-47 | Redline" -> ("AK-47", "Redline"); "★ Karambit" -> ("★ Karambit", "")."""
    nome = limpar_nome(nome)
    if " | " in nome:
        arma, padrao = nome.split(" | ", 1)
        return arma, padrao
    return nome, ""


def formatar_variacao(variacao):
    """Decimal("2.3") -> "▲ 2,3%" | Decimal("-1.0") -> "▼ 1,0%" | 0 -> "= 0,0%"."""
    seta = "▲" if variacao > 0 else "▼" if variacao < 0 else "="
    return f"{seta} {abs(variacao):.1f}%".replace(".", ",")


def cor_variacao(variacao):
    return COR_VERDE if variacao > 0 else COR_VERMELHO if variacao < 0 else COR_TEXTO_2


def formatar_data(valor):
    """datetime -> "05/10 08:00" (o banco devolve datetime; texto fica como está)."""
    if isinstance(valor, datetime):
        return valor.strftime("%d/%m %H:%M")
    return str(valor or "")


def formatar_chance(chance):
    """Decimal entre 0 e 1 -> "0,64%" (até 3 casas para as chances bem pequenas)."""
    pct = float(chance) * 100
    casas = 2 if pct >= 0.1 else 3
    return f"{pct:.{casas}f}%".replace(".", ",")


class KitUI:
    """Fábrica das peças de interface. Cada tela cria um KitUI(app)."""

    def __init__(self, app):
        self.app = app
        self._texturas = {}
        self._medidor = TextNode("medidor_de_texto")

    # ==================================================================
    # FONTES E IMAGENS
    # ==================================================================

    def fonte(self, negrito=False, escala=None):
        """Fonte Inter (a mesma do login), na resolução certa para a escala do texto.
        Se não carregar, devolve None e o Panda3D usa a fonte padrão."""
        return fonte_inter(self.app, negrito, escala)

    def textura(self, caminho):
        """Carrega uma imagem com filtro suave. Devolve None se não existir."""
        chave = str(caminho)
        if chave not in self._texturas:
            textura = None
            if caminho.exists():
                try:
                    textura = self.app.loader.loadTexture(Filename.fromOsSpecific(chave))
                    textura.setMinfilter(SamplerState.FT_linear_mipmap_linear)
                    textura.setMagfilter(SamplerState.FT_linear)
                except Exception:
                    logger.warning("Imagem não carregada: %s", caminho)
                    textura = None
            self._texturas[chave] = textura
        return self._texturas[chave]

    def textura_item(self, api_id):
        """Imagem de uma skin/caixa baixada pelo importador (app/assets/items)."""
        if not api_id:
            return None
        return self.textura(item_image_path(api_id))

    # ==================================================================
    # TEXTO
    # ==================================================================

    def largura_texto(self, texto, escala, negrito=False):
        fonte = self.fonte(negrito, escala)
        if fonte is not None:
            self._medidor.setFont(fonte)
        return self._medidor.calcWidth(texto) * escala

    def cortar(self, texto, escala, largura_max, negrito=False):
        """Encurta o texto com "…" para caber na largura (nomes longos de skins)."""
        if self.largura_texto(texto, escala, negrito) <= largura_max:
            return texto
        while len(texto) > 1 and self.largura_texto(texto + "…", escala, negrito) > largura_max:
            texto = texto[:-1]
        return texto.rstrip() + "…"

    def texto(self, pai, texto, x, z, escala, cor=COR_TEXTO, alinhar=ESQUERDA, negrito=False,
              largura_max=None, quebra_em=None):
        """Texto simples (não clicável). z é a LINHA DE BASE do texto.
        largura_max: corta com "…"; quebra_em: largura para quebrar em várias linhas."""
        if largura_max is not None:
            texto = self.cortar(texto, escala, largura_max, negrito)
        return OnscreenText(
            text=texto,
            parent=pai,
            pos=(x, z),
            scale=escala,
            fg=cor,
            align=alinhar,
            font=self.fonte(negrito, escala),
            wordwrap=(quebra_em / escala) if quebra_em else None,
            mayChange=True,
        )

    # ==================================================================
    # CAIXAS, FAIXAS E IMAGENS
    # ==================================================================

    @staticmethod
    def container(pai, x=0, z=0):
        """Agrupador invisível: destruí-lo destrói tudo que estiver dentro."""
        return DirectFrame(parent=pai, relief=None, pos=(x, 0, z))

    @staticmethod
    def retangulo(pai, x1, x2, z1, z2, cor, clicavel=False):
        """Retângulo de cor sólida. clicavel=True faz ele "segurar" os cliques
        (usado no véu das janelas para não clicar no que está atrás)."""
        return DirectFrame(
            parent=pai,
            frameColor=cor,
            frameSize=(x1, x2, z1, z2),
            state=DGG.NORMAL if clicavel else DGG.DISABLED,
        )

    @staticmethod
    def gradiente(pai, x1, x2, z1, z2, cor_baixo, cor_cima, nome="gradiente"):
        """Retângulo com degradê vertical (o "brilho" da raridade nos cartões)."""
        formato = GeomVertexFormat.getV3c4()
        dados = GeomVertexData(nome, formato, Geom.UHStatic)
        dados.setNumRows(4)
        vertice = GeomVertexWriter(dados, "vertex")
        cor = GeomVertexWriter(dados, "color")
        for x, z, c in ((x1, z1, cor_baixo), (x2, z1, cor_baixo), (x2, z2, cor_cima), (x1, z2, cor_cima)):
            vertice.addData3(x, 0, z)
            cor.addData4(*c)
        triangulos = GeomTriangles(Geom.UHStatic)
        triangulos.addVertices(0, 1, 2)
        triangulos.addVertices(0, 2, 3)
        geom = Geom(dados)
        geom.addPrimitive(triangulos)
        no_geom = GeomNode(nome)
        no_geom.addGeom(geom)
        no = pai.attachNewNode(no_geom)
        no.setTransparency(TransparencyAttrib.MAlpha)
        return no

    def contorno(self, pai, x1, x2, z1, z2, cor=COR_LARANJA, espessura=0.006):
        """Borda de 4 lados (destaque do item selecionado)."""
        caixa = self.container(pai)
        e = espessura
        lados = ((x1, x2, z2 - e, z2), (x1, x2, z1, z1 + e), (x1, x1 + e, z1, z2), (x2 - e, x2, z1, z2))
        caixa.partes = [self.retangulo(caixa, *lado, cor) for lado in lados]   # para trocar a cor depois
        return caixa

    def imagem(self, pai, textura, x, z, largura_max, altura_max):
        """Imagem centralizada em (x, z), do maior tamanho que caiba na caixa
        sem distorcer. Sem textura, não desenha nada (devolve None)."""
        if textura is None:
            return None
        largura_img = textura.getOrigFileXSize() or textura.getXSize() or 1
        altura_img = textura.getOrigFileYSize() or textura.getYSize() or 1
        escala = min(largura_max / largura_img, altura_max / altura_img)
        imagem = OnscreenImage(
            image=textura,
            parent=pai,
            pos=(x, 0, z),
            scale=(largura_img * escala / 2, 1, altura_img * escala / 2),
        )
        imagem.setTransparency(TransparencyAttrib.MAlpha)
        return imagem

    def imagem_do_item(self, pai, api_id, x, z, largura_max, altura_max, cor_reserva=COR_TEXTO_3):
        """Imagem da skin/caixa; sem arquivo, mostra um "?" no lugar (a tela segue funcionando)."""
        imagem = self.imagem(pai, self.textura_item(api_id), x, z, largura_max, altura_max)
        if imagem is None:
            escala = min(largura_max, altura_max) * 0.45
            self.texto(pai, "?", x, z - escala * BASE_TEXTO, escala, cor_reserva, CENTRO, negrito=True)
        return imagem

    # ==================================================================
    # BOTÕES, ABAS E PAGINAÇÃO
    # ==================================================================

    def botao(self, pai, texto, x, z, largura, altura, comando, extra=None, tipo="primario",
              escala=0.034, ativo=True):
        """Botão retangular: "primario" (laranja) ou "secundario" (cinza)."""
        cores = CORES_BOTAO[tipo]
        texto_normal, texto_desabilitado = TEXTO_BOTAO[tipo]
        return DirectButton(
            parent=pai,
            text=texto,
            text_font=self.fonte(True, escala),
            text_scale=escala,
            text_fg=texto_normal,
            text3_fg=texto_desabilitado,          # estado 3 = desabilitado
            text_pos=(0, -escala * BASE_TEXTO),
            relief=DGG.FLAT,
            frameColor=cores,
            frameSize=(-largura / 2, largura / 2, -altura / 2, altura / 2),
            pressEffect=0,
            pos=(x, 0, z),
            command=comando,
            extraArgs=list(extra or []),
            state=DGG.NORMAL if ativo else DGG.DISABLED,
        )

    def botao_texto(self, pai, texto, x, z, escala, comando, extra=None, cor=COR_TEXTO_2,
                    cor_hover=COR_TEXTO, alinhar=CENTRO, negrito=True):
        """Botão só de texto (abas, links, setas da paginação)."""
        largura = self.largura_texto(texto, escala, negrito)
        if alinhar == CENTRO:
            x1, x2 = -largura / 2, largura / 2
        elif alinhar == ESQUERDA:
            x1, x2 = 0, largura
        else:
            x1, x2 = -largura, 0
        return DirectButton(
            parent=pai,
            text=texto,
            text_font=self.fonte(negrito, escala),
            text_scale=escala,
            text_fg=cor,
            text2_fg=cor_hover,                   # estado 2 = mouse em cima
            text3_fg=COR_TEXTO_3,
            text_align=alinhar,
            relief=DGG.FLAT,
            frameColor=(0, 0, 0, 0),              # área clicável invisível um pouco maior que o texto
            frameSize=(x1 - 0.02, x2 + 0.02, -escala * 0.45, escala * 1.05),
            pressEffect=0,
            pos=(x, 0, z),
            command=comando,
            extraArgs=list(extra or []),
        )

    def abas(self, pai, x, z, nomes, ativa, ao_trocar, escala=0.042, espaco=0.07):
        """Abas lado a lado (ex.: CAIXAS | SKINS). A ativa fica branca e sublinhada de laranja."""
        caixa = self.container(pai)
        for nome in nomes:
            largura = self.largura_texto(nome, escala, True)
            if nome == ativa:
                self.texto(caixa, nome, x, z, escala, COR_TEXTO, ESQUERDA, negrito=True)
                self.retangulo(caixa, x, x + largura, z - 0.03, z - 0.022, COR_LARANJA)
            else:
                self.botao_texto(caixa, nome, x, z, escala, ao_trocar, [nome], alinhar=ESQUERDA)
            x += largura + espaco
        return caixa

    def paginador(self, pai, x, z, pagina, total, ao_mudar, escala=0.034):
        """"◀  2 / 60  ▶". pagina começa em 0; ao_mudar(nova_pagina)."""
        caixa = self.container(pai)
        rotulo = f"{pagina + 1} / {max(total, 1)}"
        largura = max(self.largura_texto(rotulo, escala, True), 0.12)
        self.texto(caixa, rotulo, x, z, escala, COR_TEXTO_2, CENTRO, negrito=True)
        seta_esq = self.botao_texto(caixa, "◀", x - largura / 2 - 0.07, z, escala * 1.1, ao_mudar, [pagina - 1],
                                    cor=COR_TEXTO, cor_hover=COR_LARANJA)
        seta_dir = self.botao_texto(caixa, "▶", x + largura / 2 + 0.07, z, escala * 1.1, ao_mudar, [pagina + 1],
                                    cor=COR_TEXTO, cor_hover=COR_LARANJA)
        if pagina <= 0:
            seta_esq["state"] = DGG.DISABLED
        if pagina >= total - 1:
            seta_dir["state"] = DGG.DISABLED
        return caixa

    def campo_texto(self, pai, x, z, largura, altura, texto_exemplo, ao_mudar, ao_confirmar, escala=0.034):
        """Caixa de busca com texto de exemplo. ao_mudar() a cada tecla; ao_confirmar(texto) no Enter.
        Devolve (entry, atualizar_exemplo)."""
        caixa = self.container(pai, x, z)
        self.retangulo(caixa, 0, largura, -altura / 2, altura / 2, COR_PAINEL_CLARO)
        borda = self.contorno(caixa, 0, largura, -altura / 2, altura / 2, COR_LINHA, 0.004)
        margem = 0.025
        exemplo = self.texto(caixa, texto_exemplo, margem, -escala * BASE_TEXTO, escala, COR_TEXTO_3)
        entry = DirectEntry(
            parent=caixa,
            scale=escala,
            pos=(margem, 0, -escala * BASE_TEXTO),
            width=(largura - 2 * margem) / escala,
            numLines=1,
            overflow=1,
            focus=0,
            entryFont=self.fonte(escala=escala),
            text_fg=COR_TEXTO,
            relief=DGG.FLAT,
            frameColor=(0, 0, 0, 0),
            command=ao_confirmar,
        )

        def atualizar_exemplo(*_args):
            exemplo.show() if entry.get() == "" else exemplo.hide()

        def ao_digitar(*_args):
            atualizar_exemplo()
            ao_mudar()

        def ao_focar(focado):
            for parte in borda.partes:
                parte["frameColor"] = COR_LARANJA if focado else COR_LINHA

        entry.bind(DGG.TYPE, ao_digitar)
        entry.bind(DGG.ERASE, ao_digitar)
        entry["focusInCommand"] = ao_focar
        entry["focusInExtraArgs"] = [True]
        entry["focusOutCommand"] = ao_focar
        entry["focusOutExtraArgs"] = [False]
        return entry, atualizar_exemplo

    # ==================================================================
    # CARTÃO DE ITEM (mercado e inventário)
    # ==================================================================

    def cartao(self, pai, x, z, largura, altura, comando=None, extra=None, cor_raridade=None):
        """Cartão clicável com fundo escuro, brilho da cor da raridade embaixo
        e a faixa colorida no rodapé, como os itens do CS2. O conteúdo
        (imagem, nome, preço) é colocado por quem chama."""
        cartao = DirectButton(
            parent=pai,
            relief=DGG.FLAT,
            frameColor=(COR_CARD, COR_CARD_PRESS, COR_CARD_HOVER, COR_CARD),
            frameSize=(-largura / 2, largura / 2, -altura / 2, altura / 2),
            pressEffect=0,
            pos=(x, 0, z),
            command=comando,
            extraArgs=list(extra or []),
        )
        if cor_raridade is not None:
            r, g, b = cor_raridade[:3]
            self.gradiente(cartao, -largura / 2, largura / 2, -altura / 2, -altura / 2 + altura * 0.45,
                           (r, g, b, 0.22), (r, g, b, 0.0), "brilho_raridade")
            self.retangulo(cartao, -largura / 2, largura / 2, -altura / 2, -altura / 2 + 0.008, (r, g, b, 1))
        return cartao

    def selo(self, pai, texto, x, z, escala=0.026, cor_fundo=(0.05, 0.055, 0.07, 0.92), cor=COR_TEXTO):
        """Etiqueta pequena com fundo (ex.: "x3" nas caixas repetidas). (x, z) = canto superior direito."""
        largura = self.largura_texto(texto, escala, True) + 0.03
        altura = escala * 1.5
        caixa = self.container(pai, x - largura, z - altura)
        self.retangulo(caixa, 0, largura, 0, altura, cor_fundo)
        self.texto(caixa, texto, largura / 2, altura / 2 - escala * BASE_TEXTO, escala, cor, CENTRO, negrito=True)
        return caixa

    # ==================================================================
    # BARRA DE DESGASTE (float), como a do CS2
    # ==================================================================

    def barra_desgaste(self, pai, x1, x2, z, float_valor, float_min=0, float_max=1, altura=0.018):
        """Barra com as 5 faixas de desgaste e um marcador no float da skin.
        As partes fora do float mínimo/máximo da skin ficam apagadas."""
        caixa = self.container(pai)
        largura = x2 - x1
        f_min, f_max = float(float_min), float(float_max)
        for (_nome, inicio, fim, _chance, _pt), cor in zip(WEARS, CORES_DESGASTE):
            a, b = float(inicio), float(fim)
            self.retangulo(caixa, x1 + a * largura, x1 + b * largura, z, z + altura, cor[:3] + (0.25,))
            # parte possível para esta skin, em cor cheia
            a2, b2 = max(a, f_min), min(b, f_max)
            if a2 < b2:
                self.retangulo(caixa, x1 + a2 * largura, x1 + b2 * largura, z, z + altura, cor)
        marcador_x = x1 + min(max(float(float_valor), 0.0), 1.0) * largura
        self.retangulo(caixa, marcador_x - 0.003, marcador_x + 0.003, z - 0.012, z + altura + 0.012, COR_TEXTO)
        return caixa

    # ==================================================================
    # GRÁFICO DO HISTÓRICO DE PREÇOS (D10)
    # ==================================================================

    def grafico(self, pai, pontos, x1, x2, z1, z2, texto_vazio="Ainda sem histórico de preço."):
        """Gráfico de linha do preço no tempo, desenhado com LineSegs (do próprio
        Panda3D, sem biblioteca nova). pontos: [(data, preço)] do mais antigo
        para o mais novo. Eixo X = tempo real (respeita os intervalos sem coleta)."""
        caixa = self.container(pai)
        self.retangulo(caixa, x1, x2, z1, z2, (0.06, 0.065, 0.08, 0.9))
        if len(pontos) < 2:
            self.texto(caixa, texto_vazio, (x1 + x2) / 2, (z1 + z2) / 2 - 0.03 * BASE_TEXTO, 0.03,
                       COR_TEXTO_3, CENTRO)
            return caixa

        datas = [data for data, _preco in pontos]
        precos = [float(preco) for _data, preco in pontos]
        inicio = datas[0]
        duracao = max((datas[-1] - inicio).total_seconds(), 1.0)
        p_min, p_max = min(precos), max(precos)
        folga = (p_max - p_min) * 0.12 or max(p_max * 0.05, 0.01)
        p_min, p_max = max(p_min - folga, 0.0), p_max + folga

        # área útil: margem à esquerda para os valores e embaixo para as datas
        gx1, gx2, gz1, gz2 = x1 + 0.17, x2 - 0.03, z1 + 0.06, z2 - 0.03

        def px(data):
            return gx1 + (data - inicio).total_seconds() / duracao * (gx2 - gx1)

        def pz(preco):
            return gz1 + (preco - p_min) / (p_max - p_min) * (gz2 - gz1)

        # 3 linhas de grade com o valor ao lado
        grade = LineSegs("grade")
        grade.setThickness(1)
        grade.setColor(0.22, 0.24, 0.28, 1)
        for fracao in (0.0, 0.5, 1.0):
            valor = p_min + (p_max - p_min) * fracao
            z = pz(valor)
            grade.moveTo(gx1, 0, z)
            grade.drawTo(gx2, 0, z)
            self.texto(caixa, format_money(valor), gx1 - 0.015, z - 0.022 * BASE_TEXTO, 0.022, COR_TEXTO_3, DIREITA)
        caixa.attachNewNode(grade.create())

        subiu = precos[-1] >= precos[0]
        cor = COR_VERDE if subiu else COR_VERMELHO

        # área preenchida embaixo da linha (degradê transparente)
        formato = GeomVertexFormat.getV3c4()
        dados = GeomVertexData("area", formato, Geom.UHStatic)
        dados.setNumRows(len(pontos) * 2)
        vertice = GeomVertexWriter(dados, "vertex")
        cor_vertice = GeomVertexWriter(dados, "color")
        for data, preco in zip(datas, precos):
            x = px(data)
            vertice.addData3(x, 0, pz(preco))
            cor_vertice.addData4(cor[0], cor[1], cor[2], 0.22)
            vertice.addData3(x, 0, gz1)
            cor_vertice.addData4(cor[0], cor[1], cor[2], 0.0)
        triangulos = GeomTriangles(Geom.UHStatic)
        for i in range(len(pontos) - 1):
            a, b, c, d = 2 * i, 2 * i + 1, 2 * i + 2, 2 * i + 3
            triangulos.addVertices(a, b, c)
            triangulos.addVertices(c, b, d)
        geom = Geom(dados)
        geom.addPrimitive(triangulos)
        no_area = GeomNode("area")
        no_area.addGeom(geom)
        area = caixa.attachNewNode(no_area)
        area.setTransparency(TransparencyAttrib.MAlpha)

        linha = LineSegs("linha_preco")
        linha.setThickness(2)
        linha.setColor(*cor)
        linha.moveTo(px(datas[0]), 0, pz(precos[0]))
        for data, preco in zip(datas[1:], precos[1:]):
            linha.drawTo(px(data), 0, pz(preco))
        caixa.attachNewNode(linha.create())

        # ponto no preço mais recente
        ux, uz = px(datas[-1]), pz(precos[-1])
        self.retangulo(caixa, ux - 0.008, ux + 0.008, uz - 0.008, uz + 0.008, cor)

        self.texto(caixa, formatar_data(datas[0]), gx1, z1 + 0.02, 0.022, COR_TEXTO_3, ESQUERDA)
        self.texto(caixa, formatar_data(datas[-1]), gx2, z1 + 0.02, 0.022, COR_TEXTO_3, DIREITA)
        return caixa


# ======================================================================
# JANELA (pop-up) E AVISO
# ======================================================================

class Janela:
    """Pop-up no centro da tela, com véu escuro que impede clicar no que está atrás.

    O conteúdo é montado por quem abre, dentro de janela.painel, usando
    coordenadas a partir do centro do painel."""

    def __init__(self, kit, pai, largura, altura, titulo=None, ao_fechar=None):
        self.kit = kit
        self.largura, self.altura = largura, altura
        self.ao_fechar = ao_fechar
        self.veu = kit.retangulo(pai, -4, 4, -2, 2, (0, 0, 0, 0.62), clicavel=True)
        self.painel = kit.retangulo(self.veu, -largura / 2, largura / 2, -altura / 2, altura / 2,
                                    (0.10, 0.11, 0.135, 0.99), clicavel=True)
        kit.retangulo(self.painel, -largura / 2, largura / 2, altura / 2 - 0.008, altura / 2, COR_LARANJA)
        if titulo:
            kit.texto(self.painel, titulo, -largura / 2 + 0.06, altura / 2 - 0.10, 0.045, COR_TEXTO,
                      ESQUERDA, negrito=True)

    @property
    def aberta(self):
        return self.veu is not None

    def fechar(self):
        if self.veu is None:
            return
        self.veu.destroy()
        self.veu = None
        if self.ao_fechar:
            self.ao_fechar()


class Aviso:
    """Mensagem que aparece embaixo da tela e some sozinha (sucesso em verde, erro em vermelho)."""

    def __init__(self, kit, pai, nome_tarefa, z=-0.95):
        self.kit = kit
        self.pai = pai
        self.nome_tarefa = nome_tarefa
        self.z = z
        self.caixa = None

    def mostrar(self, mensagem, sucesso=True, segundos=3.5):
        self.esconder()
        escala = 0.034
        largura = min(self.kit.largura_texto(mensagem, escala) + 0.10, 3.2)
        cor = COR_VERDE if sucesso else COR_VERMELHO
        self.caixa = self.kit.container(self.pai, 0, self.z)
        self.kit.retangulo(self.caixa, -largura / 2, largura / 2, -0.04, 0.04, (0.06, 0.07, 0.085, 0.97))
        self.kit.retangulo(self.caixa, -largura / 2, -largura / 2 + 0.008, -0.04, 0.04, cor)
        self.kit.texto(self.caixa, mensagem, 0, -escala * BASE_TEXTO, escala, cor, CENTRO,
                       largura_max=largura - 0.06)
        self.kit.app.taskMgr.doMethodLater(segundos, self._sumir, self.nome_tarefa)

    def _sumir(self, task):
        self.esconder()
        return task.done

    def esconder(self):
        self.kit.app.taskMgr.remove(self.nome_tarefa)
        if self.caixa is not None:
            self.caixa.destroy()
            self.caixa = None


def abrir_janela_conteudo(kit, pai, nome_caixa, tabela, ao_fechar):
    """Janela com TODOS os itens de uma caixa e a chance de cada um (usada no
    Mercado e no Inventário). tabela: [(Skin_Catalog, chance)] do drop_table.
    ao_fechar: função do botão FECHAR (a tela fecha a janela)."""
    janela = Janela(kit, pai, 3.2, 1.72, f"CONTEÚDO  ·  {limpar_nome(nome_caixa)}")
    colunas, linhas = 8, 3
    por_pagina = colunas * linhas
    total_paginas = max(1, -(-len(tabela) // por_pagina))
    estado = {"pagina": 0, "area": None}

    def desenhar():
        if estado["area"] is not None:
            estado["area"].destroy()
        estado["area"] = area = kit.container(janela.painel)
        largura, altura, gap = 0.36, 0.40, 0.03
        x0 = -(colunas * largura + (colunas - 1) * gap) / 2 + largura / 2
        inicio = estado["pagina"] * por_pagina
        for i, (skin, chance) in enumerate(tabela[inicio:inicio + por_pagina]):
            x = x0 + (i % colunas) * (largura + gap)
            z = 0.48 - (i // colunas) * (altura + gap)
            cor = skin.rarity.color_rgba
            cartao = kit.cartao(area, x, z, largura, altura, cor_raridade=cor)
            cartao["state"] = DGG.DISABLED          # só para ver: não é clicável
            kit.imagem_do_item(cartao, skin.api_id, 0, 0.07, largura - 0.06, 0.20)
            arma, padrao = nome_em_duas_linhas(skin.name)
            kit.texto(cartao, arma, -largura / 2 + 0.025, -0.075, 0.024, COR_TEXTO_2, largura_max=largura - 0.05)
            kit.texto(cartao, padrao or "Vanilla", -largura / 2 + 0.025, -0.115, 0.027, COR_TEXTO,
                      largura_max=largura - 0.05)
            kit.texto(cartao, formatar_chance(chance), -largura / 2 + 0.025, -0.165, 0.026, cor, negrito=True)
        if total_paginas > 1:
            kit.paginador(area, 0, -0.62, estado["pagina"], total_paginas, mudar)

    def mudar(pagina):
        if 0 <= pagina < total_paginas:
            estado["pagina"] = pagina
            desenhar()

    desenhar()
    kit.texto(janela.painel, "Chance de cada item = chance da raridade ÷ quantidade de itens dessa raridade.",
              -1.52, -0.75, 0.025, COR_TEXTO_3)
    kit.botao(janela.painel, "FECHAR", 1.32, -0.74, 0.40, 0.085, ao_fechar, tipo="secundario", escala=0.03)
    return janela
