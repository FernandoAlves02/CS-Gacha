"""PEDESTAL GIRATÓRIO da Home (Extras 4): a skin em destaque girando num pedestal.

Como funciona (para a apresentação)
-----------------------------------
- A skin é uma imagem (a mesma do mercado). Para parecer um objeto girando,
  ela vai num "cartão" dentro de uma cena 3D PEQUENA e SEPARADA, com câmera
  em perspectiva: girando o cartão, a perspectiva faz o efeito de rotação
  (de costas, aparece o outro lado da arma).
- Essa cena tem a sua própria "janelinha" na tela (DisplayRegion), desenhada
  por cima do cenário 3D da Home e por baixo da interface 2D. Assim ela não
  mexe na câmera nem na iluminação (PBR) do cenário.
- O pedestal é desenhado por código (cilindros com cores nos vértices) e não
  usa luz: sem arquivo novo e sem biblioteca nova.
"""
import math

from panda3d.core import (
    Camera,
    CardMaker,
    ClockObject,
    Geom,
    GeomNode,
    GeomTriangles,
    GeomVertexData,
    GeomVertexFormat,
    GeomVertexWriter,
    NodePath,
    PerspectiveLens,
    TransparencyAttrib,
)

TASK_GIRO = "home_vitrine_giro"
SEGUNDOS_POR_VOLTA = 9.0
LADOS = 48                       # "redondeza" dos cilindros


def _cilindro(nome, raio_baixo, raio_cima, z1, z2, cor_baixo, cor_cima, tampa=None):
    """Cilindro (ou tronco de cone) com cor nos vértices. tampa: cor da tampa de cima (None = sem tampa)."""
    formato = GeomVertexFormat.getV3c4()
    dados = GeomVertexData(nome, formato, Geom.UHStatic)
    vertice = GeomVertexWriter(dados, "vertex")
    cor = GeomVertexWriter(dados, "color")
    tri = GeomTriangles(Geom.UHStatic)
    for i in range(LADOS + 1):
        a = 2 * math.pi * i / LADOS
        c, s = math.cos(a), math.sin(a)
        vertice.addData3(raio_baixo * c, raio_baixo * s, z1)
        cor.addData4(*cor_baixo)
        vertice.addData3(raio_cima * c, raio_cima * s, z2)
        cor.addData4(*cor_cima)
    for i in range(LADOS):
        b0, t0, b1, t1 = 2 * i, 2 * i + 1, 2 * i + 2, 2 * i + 3
        tri.addVertices(b0, b1, t1)
        tri.addVertices(b0, t1, t0)
    if tampa is not None:
        centro = (LADOS + 1) * 2
        vertice.addData3(0, 0, z2)
        cor.addData4(*tampa)
        for i in range(LADOS + 1):
            a = 2 * math.pi * i / LADOS
            vertice.addData3(raio_cima * math.cos(a), raio_cima * math.sin(a), z2)
            cor.addData4(*tampa[:3], tampa[3] * 0.85)
        for i in range(LADOS):
            tri.addVertices(centro, centro + 1 + i, centro + 2 + i)
    geom = Geom(dados)
    geom.addPrimitive(tri)
    no = GeomNode(nome)
    no.addGeom(geom)
    return NodePath(no)


class Vitrine3D:
    """Cena 3D do pedestal numa área da janela.

    area: (esquerda, direita, baixo, cima) em FRAÇÃO da janela (0 a 1).
    textura: imagem da skin; cor: cor da raridade (r, g, b, a).
    """

    def __init__(self, app, textura, cor, area, girar=True):
        self.app = app
        self.cena = NodePath("vitrine_3d")
        self.cena.setLightOff(1)                  # cores prontas nos vértices: sem luz
        self.cena.setTwoSided(True)

        # Janelinha própria, entre o cenário (ordem 0) e a interface 2D (ordem 10)
        self.regiao = app.win.makeDisplayRegion(*area)
        self.regiao.setSort(5)
        self.regiao.setClearColorActive(False)    # transparente: o cenário aparece atrás
        self.regiao.setClearDepthActive(True)
        self.lente = PerspectiveLens()
        self.lente.setFov(21)
        camera = Camera("camera_vitrine", self.lente)
        self.camera = self.cena.attachNewNode(camera)
        self.camera.setPos(0, -9.5, 2.75)
        self.camera.lookAt(0, 0, 1.42)
        self.regiao.setCamera(self.camera)
        self.ajustar_proporcao()

        r, g, b = cor[:3]
        # base escura + pedestal + anel da cor da raridade
        _cilindro("base", 1.05, 1.05, 0.0, 0.10, (0.05, 0.05, 0.06, 1), (0.10, 0.10, 0.12, 1),
                  tampa=(0.13, 0.13, 0.15, 1)).reparentTo(self.cena)
        _cilindro("pedestal", 0.80, 0.72, 0.10, 0.52, (0.07, 0.07, 0.09, 1), (0.22, 0.22, 0.26, 1),
                  tampa=(0.30, 0.30, 0.34, 1)).reparentTo(self.cena)
        _cilindro("anel", 0.735, 0.735, 0.50, 0.55, (r, g, b, 1), (r, g, b, 1)).reparentTo(self.cena)
        # feixe de luz da cor da raridade, sumindo para cima. Vai para o "fundo" (desenhado
        # antes de tudo e sem gravar profundidade): a skin aparece por cima, sem ficar tingida.
        feixe = _cilindro("feixe", 0.70, 0.85, 0.55, 2.8, (r, g, b, 0.26), (r, g, b, 0.0))
        feixe.setTransparency(TransparencyAttrib.MAlpha)
        feixe.setDepthWrite(False)
        feixe.setBin("background", 10)
        feixe.reparentTo(self.cena)

        # cartão com a imagem da skin, girando sobre o pedestal
        self.giro = self.cena.attachNewNode("giro")
        self.giro.setZ(1.5)
        if textura is not None:
            largura = textura.getOrigFileXSize() or textura.getXSize() or 1
            altura = textura.getOrigFileYSize() or textura.getYSize() or 1
            meia_l = 1.55
            meia_a = meia_l * altura / largura
            cartao = CardMaker("skin")
            cartao.setFrame(-meia_l, meia_l, -meia_a, meia_a)
            no_cartao = self.giro.attachNewNode(cartao.generate())
            no_cartao.setTexture(textura)
            no_cartao.setTransparency(TransparencyAttrib.MAlpha)

        self.tempo = 0.0
        if girar:
            app.taskMgr.add(self._girar, TASK_GIRO)
        else:
            self.giro.setH(25)              # animações desligadas (CONFIGURAÇÕES): parado, meio de lado

    def ajustar_proporcao(self):
        """A lente precisa da proporção (largura/altura) da janelinha em pixels."""
        largura = self.regiao.getPixelWidth()
        altura = self.regiao.getPixelHeight()
        if largura > 0 and altura > 0:
            self.lente.setAspectRatio(largura / altura)

    def mudar_area(self, area):
        self.regiao.setDimensions(*area)
        self.ajustar_proporcao()

    def _girar(self, task):
        dt = min(ClockObject.getGlobalClock().getDt(), 0.1)
        self.tempo += dt
        self.giro.setH((self.tempo / SEGUNDOS_POR_VOLTA) * 360 % 360)
        self.giro.setZ(1.5 + 0.06 * math.sin(self.tempo * 2.0))     # "flutuando"
        return task.cont

    def destruir(self):
        self.app.taskMgr.remove(TASK_GIRO)
        if self.regiao is not None:
            self.app.win.removeDisplayRegion(self.regiao)
            self.regiao = None
        self.cena.removeNode()
