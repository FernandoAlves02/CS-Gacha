"""PEDESTAL GIRATÓRIO da Home (Extras 4; refeito no Extras 6): a skin em destaque girando.

Como funciona (para a apresentação)
-----------------------------------
- A skin é uma PEÇA 3D feita a partir da imagem do mercado (skin_3d.py):
  frente, verso e laterais, iluminada de leve. Girando, ela parece sólida.
- Ela fica numa cena 3D PEQUENA e SEPARADA (Palco3D), com a sua própria
  "janelinha" na tela (DisplayRegion), desenhada por cima do cenário 3D da
  Home e por baixo da interface 2D. Assim não mexe na câmera nem na
  iluminação (PBR) do cenário.
- O pedestal é desenhado por código (cilindros) e usa TEXTURAS DA PRÓPRIA
  MIRAGE que já estão no projeto: pedra no degrau, mármore no corpo e no
  tampo e a faixa decorada das paredes da Mirage. As sombras são "pintadas"
  nos vértices (lado da luz mais claro, embaixo mais escuro), sem luz de
  verdade. Se as texturas faltarem, ele fica só com as cores (como antes).
"""
import math
from pathlib import Path

from panda3d.core import (
    CardMaker,
    ClockObject,
    Filename,
    Geom,
    GeomNode,
    GeomTriangles,
    GeomVertexData,
    GeomVertexFormat,
    GeomVertexWriter,
    NodePath,
    SamplerState,
    TransparencyAttrib,
)

from app.view.skin_3d import Palco3D, criar_skin_3d

TASK_GIRO = "home_vitrine_giro"
SEGUNDOS_POR_VOLTA = 9.0
LADOS = 48                       # "redondeza" dos cilindros
LARGURA_SKIN = 3.1               # largura da imagem inteira da skin (como o cartão do Extras 4)

TEXTURAS_MIRAGE = Path(__file__).resolve().parent.parent / "assets" / "maps" / "mirage_menu"
PEDRA = "stonestep01_color_psd_25c7b974.jpg"              # degrau de pedra gasta
MARMORE = "base_top_ver1_diffuse_color_psd_41ae5e62.jpg"   # mármore claro (corpo)
TAMPO = "de_mirage_marble_01_color_psd_7342b537.jpg"       # mármore da Mirage (tampo e degrau)
FAIXA = "dusandwlltrim3_color_psd_cc4cabea.jpg"            # faixa decorada das paredes da Mirage

ANGULO_LUZ = math.radians(-125)  # de onde vem a "luz pintada" (frente-esquerda de quem olha)

# Jeito de ler as texturas no pedestal (suave de longe e repetindo em volta). Vai junto
# do setTexture, sem mexer na textura: o MAPA usa os mesmos arquivos (e os mesmos
# objetos de textura, que o Panda3D guarda uma vez só) com o jeito dele.
AMOSTRADOR = SamplerState()
AMOSTRADOR.setMinfilter(SamplerState.FT_linear_mipmap_linear)
AMOSTRADOR.setMagfilter(SamplerState.FT_linear)
AMOSTRADOR.setWrapU(SamplerState.WM_repeat)
AMOSTRADOR.setWrapV(SamplerState.WM_repeat)


def _brilho(angulo, altura):
    """Sombra pintada: lado virado para a luz mais claro; embaixo um pouco mais escuro."""
    lado = 0.55 + 0.45 * max(0.0, math.cos(angulo - ANGULO_LUZ))
    return lado * (0.78 + 0.22 * altura)


def _cilindro(nome, raio_baixo, raio_cima, z1, z2, cor, textura=None, voltas_u=3.0, v=(0.0, 1.0),
              tampa=None, textura_tampa=None, escala_tampa=1.0, cor_cima=None, sombra=True):
    """Cilindro (ou tronco de cone) com sombra pintada e, se tiver, textura.

    cor: cor base (r, g, b, a) que multiplica a textura; cor_cima: outra cor no alto (degradê).
    voltas_u: quantas vezes a textura se repete em volta; v: faixa da textura na altura.
    tampa: cor da tampa de cima (None = sem tampa); textura_tampa: textura dela (vista de cima).
    sombra=False: cor igual em volta (anel e feixe são luz, não pedra).
    """
    dados = GeomVertexData(nome, GeomVertexFormat.getV3c4t2(), Geom.UHStatic)
    vertice = GeomVertexWriter(dados, "vertex")
    cor_v = GeomVertexWriter(dados, "color")
    uv = GeomVertexWriter(dados, "texcoord")
    tri = GeomTriangles(Geom.UHStatic)
    for i in range(LADOS + 1):
        angulo = 2 * math.pi * i / LADOS
        c, s = math.cos(angulo), math.sin(angulo)
        for raio, z, altura, vv, (r, g, b, a) in ((raio_baixo, z1, 0.0, v[0], cor),
                                                  (raio_cima, z2, 1.0, v[1], cor_cima or cor)):
            luz = _brilho(angulo, altura) if sombra else 1.0
            vertice.addData3(raio * c, raio * s, z)
            cor_v.addData4(r * luz, g * luz, b * luz, a)
            uv.addData2(voltas_u * i / LADOS, vv)
    for i in range(LADOS):
        b0, t0, b1, t1 = 2 * i, 2 * i + 1, 2 * i + 2, 2 * i + 3
        tri.addVertices(b0, b1, t1)
        tri.addVertices(b0, t1, t0)
    geom = Geom(dados)
    geom.addPrimitive(tri)
    no = GeomNode(nome)
    no.addGeom(geom)
    cilindro = NodePath(no)
    if textura is not None:
        cilindro.setTexture(textura, AMOSTRADOR)

    if tampa is not None:
        dados_t = GeomVertexData(nome + "_tampa", GeomVertexFormat.getV3c4t2(), Geom.UHStatic)
        vertice = GeomVertexWriter(dados_t, "vertex")
        cor_v = GeomVertexWriter(dados_t, "color")
        uv = GeomVertexWriter(dados_t, "texcoord")
        tri_t = GeomTriangles(Geom.UHStatic)
        vertice.addData3(0, 0, z2)
        cor_v.addData4(*tampa)
        uv.addData2(0.5, 0.5)
        for i in range(LADOS + 1):
            angulo = 2 * math.pi * i / LADOS
            c, s = math.cos(angulo), math.sin(angulo)
            vertice.addData3(raio_cima * c, raio_cima * s, z2)
            cor_v.addData4(*tampa[:3], tampa[3])
            uv.addData2(0.5 + 0.5 * c * escala_tampa, 0.5 + 0.5 * s * escala_tampa)
        for i in range(LADOS):
            tri_t.addVertices(0, 1 + i, 2 + i)
        geom_t = Geom(dados_t)
        geom_t.addPrimitive(tri_t)
        no_t = GeomNode(nome + "_tampa")
        no_t.addGeom(geom_t)
        tampa_np = cilindro.attachNewNode(no_t)
        if textura_tampa is not None:
            tampa_np.setTexture(textura_tampa, AMOSTRADOR, 1)
        elif textura is not None:
            tampa_np.setTextureOff(1)
    return cilindro


class Vitrine3D(Palco3D):
    """Pedestal com a skin girando numa área da janela.

    area: (esquerda, direita, baixo, cima) em FRAÇÃO da janela (0 a 1).
    textura: imagem da skin; cor: cor da raridade (r, g, b, a).
    """

    def __init__(self, app, textura, cor, area, girar=True):
        super().__init__(app, area, ordem=5, fov=21)
        self.camera.setPos(0, -9.5, 2.75)
        self.camera.lookAt(0, 0, 1.42)

        self.pedestal = self.cena.attachNewNode("pedestal")
        self.pedestal.setLightOff(1)              # sombras já pintadas nos vértices
        self.pedestal.setTwoSided(True)
        self._montar_pedestal(cor)

        # a skin em 3D, girando sobre o pedestal
        self.giro = self.cena.attachNewNode("giro")
        self.giro.setZ(1.5)
        peca = criar_skin_3d(textura)
        if peca is not None:
            no, _largura, _altura = peca
            no.setScale(LARGURA_SKIN)
            no.reparentTo(self.giro)
            self.iluminar(no)
        elif textura is not None:
            self._cartao_plano(textura)       # imagem sem transparência: o cartão do Extras 4

        self.tempo = 0.0
        if girar:
            app.taskMgr.add(self._girar, TASK_GIRO)
        else:
            self.giro.setH(25)              # animações desligadas (CONFIGURAÇÕES): parado, meio de lado

    def _cartao_plano(self, textura):
        """Reserva: a imagem num cartão (como no Extras 4), se não der para montar a peça 3D."""
        largura = textura.getOrigFileXSize() or textura.getXSize() or 1
        altura = textura.getOrigFileYSize() or textura.getYSize() or 1
        meia_l = LARGURA_SKIN / 2
        meia_a = meia_l * altura / largura
        cartao = CardMaker("skin")
        cartao.setFrame(-meia_l, meia_l, -meia_a, meia_a)
        no = self.giro.attachNewNode(cartao.generate())
        no.setTexture(textura)
        no.setTransparency(TransparencyAttrib.MAlpha)
        no.setTwoSided(True)
        no.setLightOff(1)

    def _textura(self, arquivo):
        """Textura da Mirage (None se o arquivo não estiver no projeto)."""
        caminho = TEXTURAS_MIRAGE / arquivo
        if not caminho.exists():
            return None
        return self.app.loader.loadTexture(Filename.fromOsSpecific(str(caminho)))

    def _montar_pedestal(self, cor):
        r, g, b = cor[:3]
        pedra, marmore, tampo, faixa = (self._textura(nome) for nome in (PEDRA, MARMORE, TAMPO, FAIXA))
        # cor que multiplica cada textura (sem textura, fica só a cor, num tom de pedra)
        areia = (0.92, 0.86, 0.76, 1) if pedra is None else (1, 1, 1, 1)
        claro = (0.85, 0.82, 0.76, 1) if marmore is None else (1, 1, 1, 1)

        partes = [
            # degrau de pedra largo, com tampo de mármore
            _cilindro("degrau", 1.05, 1.02, 0.0, 0.14, areia, pedra, voltas_u=3, v=(0.35, 0.62),
                      tampa=(0.80, 0.78, 0.74, 1), textura_tampa=tampo, escala_tampa=0.9),
            # corpo de mármore, afinando um pouco para cima
            _cilindro("corpo", 0.78, 0.74, 0.14, 0.30, claro, marmore, voltas_u=2, v=(0.0, 0.2)),
            # faixa decorada das paredes da Mirage (altura certa para o desenho não esticar)
            _cilindro("faixa", 0.75, 0.75, 0.30, 0.49, (1, 1, 1, 1), faixa, voltas_u=6, v=(0.0, 1.0)),
            # tampo de mármore
            _cilindro("tampo", 0.78, 0.78, 0.49, 0.545, claro, marmore, voltas_u=2, v=(0.4, 0.45),
                      tampa=(1, 1, 1, 1), textura_tampa=tampo, escala_tampa=0.7),
        ]
        for parte in partes:
            parte.reparentTo(self.pedestal)

        # anel brilhando na cor da raridade, na borda do tampo
        _cilindro("anel", 0.785, 0.785, 0.53, 0.56, (r, g, b, 1), sombra=False).reparentTo(self.pedestal)

        # feixe de luz da cor da raridade, sumindo para cima. Vai para o "fundo" (desenhado
        # antes de tudo e sem gravar profundidade): a skin aparece por cima, sem ficar tingida.
        feixe = _cilindro("feixe", 0.70, 0.85, 0.56, 2.8, (r, g, b, 0.26), cor_cima=(r, g, b, 0.0), sombra=False)
        feixe.setTransparency(TransparencyAttrib.MAlpha)
        feixe.setDepthWrite(False)
        feixe.setBin("background", 10)
        feixe.reparentTo(self.pedestal)

    def _girar(self, task):
        dt = min(ClockObject.getGlobalClock().getDt(), 0.1)
        self.tempo += dt
        self.giro.setH((self.tempo / SEGUNDOS_POR_VOLTA) * 360 % 360)
        self.giro.setZ(1.5 + 0.06 * math.sin(self.tempo * 2.0))     # "flutuando"
        return task.cont

    def destruir(self):
        self.app.taskMgr.remove(TASK_GIRO)
        super().destruir()
