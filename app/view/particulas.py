"""POEIRA E NÉVOA da Home (Extras 6): o "ar" do menu do CS.

- POEIRA: grãozinhos claros flutuando devagar na frente da câmera, piscando
  de leve, como poeira pegando sol.
- NÉVOA: algumas nuvens grandes e bem fracas passando devagar.

Como funciona
-------------
- Tudo numa cena SEPARADA, desenhada por cima do mapa (DisplayRegion de ordem
  3: depois do cenário, que é 0, e antes do pedestal, 5). Assim a poeira não
  recebe a iluminação PBR do mapa (ficaria escura) e não mexe no cenário.
- A câmera desta cena copia a câmera do cenário a cada quadro (posição e
  lente): no balanço da câmera, a poeira se move junto com o mapa.
- As imagens (bolinha e fumaça) são geradas por código (PNMImage e o ruído
  Perlin do Panda3D): sem arquivo novo e sem biblioteca nova.
- Segue a opção ANIMAÇÕES DA HOME: com elas desligadas, a Home nem cria isto.
"""
import math
import random

from panda3d.core import (
    Camera,
    CardMaker,
    ClockObject,
    ColorBlendAttrib,
    NodePath,
    PerlinNoise2,
    PNMImage,
    Texture,
    TransparencyAttrib,
)

TASK_PARTICULAS = "home_particulas"
ORDEM = 3                       # depois do cenário (0), antes do pedestal (5) e da interface (10)

QTD_POEIRA = 110
PERTO, LONGE = 1.0, 3.2         # distância da câmera (m): a poeira fica entre a câmera e o personagem
TAMANHO_POEIRA = (0.003, 0.010)
COR_POEIRA = (1.0, 0.90, 0.72)
QTD_NEVOA = 7
COR_NEVOA = (0.86, 0.80, 0.72)

_texturas = {}


def _textura_ponto():
    """Bolinha macia (transparência que some para as bordas)."""
    if "ponto" not in _texturas:
        tam = 32
        imagem = PNMImage(tam, tam, 4)
        imagem.fill(1, 1, 1)
        for y in range(tam):
            for x in range(tam):
                d = math.hypot(x + 0.5 - tam / 2, y + 0.5 - tam / 2) / (tam / 2)
                imagem.setAlpha(x, y, max(0.0, 1 - d) ** 2)
        textura = Texture("poeira")
        textura.load(imagem)
        _texturas["ponto"] = textura
    return _texturas["ponto"]


def _textura_fumaca():
    """Nuvem de fumaça: ruído Perlin (manchas irregulares) que some para as bordas."""
    if "fumaca" not in _texturas:
        tam = 64
        ruido = PerlinNoise2(18, 18, 256, 7)
        ruido_fino = PerlinNoise2(7, 7, 256, 11)
        imagem = PNMImage(tam, tam, 4)
        imagem.fill(1, 1, 1)
        for y in range(tam):
            for x in range(tam):
                d = math.hypot(x + 0.5 - tam / 2, y + 0.5 - tam / 2) / (tam / 2)
                manchas = 0.5 + 0.35 * ruido.noise(x, y) + 0.15 * ruido_fino.noise(x, y)
                imagem.setAlpha(x, y, max(0.0, min(1.0, manchas)) * max(0.0, 1 - d) ** 1.5)
        textura = Texture("nevoa")
        textura.load(imagem)
        _texturas["fumaca"] = textura
    return _texturas["fumaca"]


def _cartao(pai, textura):
    """Quadradinho sempre virado para a câmera (billboard) com a imagem."""
    cartao = CardMaker("particula")
    cartao.setFrame(-1, 1, -1, 1)
    no = pai.attachNewNode("billboard")
    no.setBillboardPointEye()
    imagem = no.attachNewNode(cartao.generate())
    imagem.setTexture(textura)
    return no, imagem


class ParticulasHome:
    """Poeira e névoa na frente da câmera da Home.

    camera_pos / camera_hpr: a câmera PARADA do cenário (a poeira é espalhada
    no que ela enxerga; depois fica parada no mundo, como o mapa).
    """

    def __init__(self, app, camera_pos, camera_hpr, semente=None):
        self.app = app
        self.sorteio = random.Random(semente)
        self.cena = NodePath("particulas_home")
        self.cena.setDepthWrite(False)
        self.cena.setLightOff(1)
        self.regiao = app.win.makeDisplayRegion()
        self.regiao.setSort(ORDEM)
        self.regiao.setClearColorActive(False)       # transparente: o mapa aparece atrás
        self.regiao.setClearDepthActive(True)
        self.camera = self.cena.attachNewNode(Camera("camera_particulas", app.camLens))   # mesma lente
        self.regiao.setCamera(self.camera)
        self.ancora = self.cena.attachNewNode("ancora")
        self.ancora.setPos(camera_pos)
        self.ancora.setHpr(camera_hpr)

        self._medir_tela()

        # poeira: soma luz (brilha sobre o mapa, como poeira pegando sol)
        self.poeira = []
        aditivo = ColorBlendAttrib.make(ColorBlendAttrib.MAdd, ColorBlendAttrib.OIncomingAlpha,
                                        ColorBlendAttrib.OOne)
        for _ in range(QTD_POEIRA):
            no, imagem = _cartao(self.ancora, _textura_ponto())
            imagem.setAttrib(aditivo)
            imagem.setColor(*COR_POEIRA, 1)
            y = self.sorteio.uniform(PERTO, LONGE)
            no.setScale(self.sorteio.uniform(*TAMANHO_POEIRA))
            p = {
                "no": no,
                "x": self.sorteio.uniform(-1, 1) * self.tg_x * y,
                "y": y,
                "z": self.sorteio.uniform(-1, 1) * self.tg_z * y,
                "vx": self.sorteio.uniform(-0.025, 0.010),         # um "ventinho" para a esquerda
                "vz": self.sorteio.uniform(0.002, 0.018),          # subindo devagar
                "fase": self.sorteio.uniform(0, 2 * math.pi),
                "pisca": self.sorteio.uniform(0.6, 1.6),
                "brilho": self.sorteio.uniform(0.25, 0.65),
            }
            self.poeira.append(p)

        # névoa: nuvens grandes e bem fracas, mais para baixo e mais longe
        self.nevoa = []
        for _ in range(QTD_NEVOA):
            no, imagem = _cartao(self.ancora, _textura_fumaca())
            imagem.setTransparency(TransparencyAttrib.MAlpha)
            y = self.sorteio.uniform(3.5, 7.0)
            no.setScale(self.sorteio.uniform(1.2, 2.4))
            imagem.setR(self.sorteio.uniform(0, 360))
            n = {
                "no": no,
                "imagem": imagem,
                "x": self.sorteio.uniform(-1, 1) * self.tg_x * y,
                "y": y,
                "z": self.sorteio.uniform(-0.9, 0.1) * self.tg_z * y,
                "vx": self.sorteio.uniform(-0.06, -0.02),
                "giro": self.sorteio.uniform(-3, 3),               # graus por segundo
                "alfa": self.sorteio.uniform(0.04, 0.08),
                "fase": self.sorteio.uniform(0, 2 * math.pi),
            }
            imagem.setColor(*COR_NEVOA, n["alfa"])
            self.nevoa.append(n)

        self.tempo = 0.0
        app.taskMgr.add(self._atualizar, TASK_PARTICULAS)
        self._atualizar(None)

    def _medir_tela(self):
        """Quanto a câmera enxerga para os lados e para cima (muda com F11 / outra proporção)."""
        lente = self.app.camLens
        self.tg_x = math.tan(math.radians(lente.getHfov() / 2)) * 1.05
        self.tg_z = math.tan(math.radians(lente.getVfov() / 2)) * 1.05

    def _atualizar(self, task):
        dt = min(ClockObject.getGlobalClock().getDt(), 0.1) if task is not None else 0.0
        self.tempo += dt
        t = self.tempo
        # a câmera desta cena copia a do cenário (o balanço da Home vale aqui também)
        self.camera.setMat(self.app.camera.getMat(self.app.render))
        self._medir_tela()

        for p in self.poeira:
            y = p["y"]
            limite_x, limite_z = self.tg_x * y, self.tg_z * y
            p["x"] += p["vx"] * dt
            p["z"] += p["vz"] * dt
            if p["x"] < -limite_x:                     # saiu por um lado: volta pelo outro
                p["x"] = limite_x
            elif p["x"] > limite_x:
                p["x"] = -limite_x
            if p["z"] > limite_z:
                p["z"] = -limite_z
            elif p["z"] < -limite_z:                   # (a janela ficou mais baixa)
                p["z"] = -limite_z
            ondula = 0.03 * math.sin(t * 0.7 + p["fase"])
            p["no"].setPos(p["x"] + ondula, y, p["z"] + 0.5 * ondula)
            p["no"].setAlphaScale(p["brilho"] * (0.55 + 0.45 * math.sin(t * p["pisca"] + p["fase"])))

        for n in self.nevoa:
            y = n["y"]
            limite_x = self.tg_x * y + n["no"].getScale().x
            n["x"] += n["vx"] * dt
            if n["x"] < -limite_x:
                n["x"] = limite_x
            n["no"].setPos(n["x"], y, n["z"] + 0.05 * math.sin(t * 0.3 + n["fase"]))
            n["imagem"].setR(n["imagem"].getR() + n["giro"] * dt)
        return task.cont if task is not None else None

    def destruir(self):
        self.app.taskMgr.remove(TASK_PARTICULAS)
        if self.regiao is not None:
            self.app.win.removeDisplayRegion(self.regiao)
            self.regiao = None
        self.cena.removeNode()
