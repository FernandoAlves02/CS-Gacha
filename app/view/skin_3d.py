"""SKIN EM 3D (Extras 6): a imagem da skin vira uma PEÇA SÓLIDA que gira.

Por que não "vestir" o modelo 3D da arma com a imagem?
------------------------------------------------------
A imagem do mercado é uma FOTO da arma pronta, de lado. O modelo 3D de uma
arma do CS é pintado por uma textura "desembrulhada" (o UV), que é outra
coisa e muda de skin para skin. Além disso só temos o modelo da AK e da AWP,
e as skins são mais de 1.800 em dezenas de armas.

Como funciona
-------------
1. Lemos a transparência (alfa) da imagem numa grade (de 2 em 2 pixels).
2. FRENTE e VERSO: a própria imagem, a uma pequena distância uma da outra
   (de costas aparece espelhada, como o outro lado de um objeto de verdade).
3. LATERAIS: achamos o contorno da arma ("marching squares": a borda passa
   entre os pontos da grade, onde a transparência cruza 50%) e em cada pedaço
   dele sobe uma "parede" ligando a frente ao verso, com a cor da arma ali.
4. Uma luz suave (de cima, à esquerda) deixa as laterais mais escuras que a
   frente: quando a peça gira, ela parece sólida em vez de sumir de lado.

Tudo com o Panda3D (PNMImage, Geom e luzes simples): sem arquivo novo e sem
biblioteca nova.

Neste arquivo também ficam:
- Palco3D: uma "janelinha" 3D própria (DisplayRegion), usada pelo pedestal da
  Home (vitrine_3d.py) e pela inspeção;
- Inspecao3D: a skin girando com o mouse, como a inspeção do CS (imagem
  ampliada do Mercado e DETALHES do inventário).
"""
import logging
import math
from itertools import count

from direct.gui import DirectGuiGlobals as DGG
from direct.gui.DirectGui import DirectFrame
from panda3d.core import (
    AmbientLight,
    Camera,
    ClockObject,
    DirectionalLight,
    Geom,
    GeomNode,
    GeomTriangles,
    GeomVertexData,
    GeomVertexFormat,
    GeomVertexWriter,
    MouseButton,
    NodePath,
    PerspectiveLens,
    PNMImage,
    Point3,
    TransparencyAttrib,
    Vec3,
)

logger = logging.getLogger(__name__)

PASSO = 2               # pixels da imagem por ponto da grade (256 px -> 128 pontos)
ESPESSURA = 0.045       # grossura da peça, em "larguras de imagem" (0,045 = 4,5% da largura)
LIMITE = 0.5            # transparência a partir da qual o pixel conta como "arma"
ESCURECER = 0.85        # laterais um pouco mais escuras que a cor da frente
COR_DENTRO = 3          # a cor da lateral vem de 3 pixels para dentro da borda
LUZ_AMBIENTE = 0.50     # luz que chega em tudo
LUZ_SOL = 0.60          # luz direcional (de cima, à esquerda de quem olha)

_moldes = {}            # imagem -> peça já montada (montar de novo a mesma skin é instantâneo)
_ids = count(1)         # nomes únicos para as tarefas de cada inspeção


# ======================================================================
# A PEÇA 3D
# ======================================================================

class _Malha:
    """Ajuda a montar uma malha de quadrados: com textura (uv) ou com cor nos vértices."""

    def __init__(self, nome, com_cor=False):
        formato = GeomVertexFormat.getV3n3c4() if com_cor else GeomVertexFormat.getV3n3t2()
        self.dados = GeomVertexData(nome, formato, Geom.UHStatic)
        self.vertice = GeomVertexWriter(self.dados, "vertex")
        self.normal = GeomVertexWriter(self.dados, "normal")
        self.extra = GeomVertexWriter(self.dados, "color" if com_cor else "texcoord")
        self.com_cor = com_cor
        self.triangulos = GeomTriangles(Geom.UHStatic)
        self.total = 0
        self.nome = nome

    def quadrado(self, cantos, normal, uvs=None, cor=None):
        """4 cantos em volta do quadrado. Acerta a ordem para a frente ficar do lado da normal."""
        a, b, c = (Vec3(*p) for p in cantos[:3])
        if (b - a).cross(c - a).dot(Vec3(*normal)) < 0:
            cantos = cantos[::-1]
            uvs = uvs[::-1] if uvs else uvs
        for i, ponto in enumerate(cantos):
            self.vertice.addData3(*ponto)
            self.normal.addData3(*normal)
            if self.com_cor:
                self.extra.addData4(*cor)
            else:
                self.extra.addData2(*uvs[i])
        i = self.total
        self.triangulos.addVertices(i, i + 1, i + 2)
        self.triangulos.addVertices(i, i + 2, i + 3)
        self.total += 4

    def no(self):
        geom = Geom(self.dados)
        geom.addPrimitive(self.triangulos)
        no = GeomNode(self.nome)
        no.addGeom(geom)
        return NodePath(no)


def _montar(caminho):
    """Monta a peça (frente/verso + laterais) a partir do arquivo da imagem. None se não der."""
    imagem = PNMImage()
    if not imagem.read(caminho) or not imagem.hasAlpha():
        return None
    largura, altura = imagem.getXSize(), imagem.getYSize()
    colunas, linhas = largura // PASSO, altura // PASSO
    meio = PASSO // 2
    # transparência em cada ponto da grade (0 = vazio, 1 = cheio)
    alfa = [[imagem.getAlpha(c * PASSO + meio, r * PASSO + meio) for c in range(colunas)] for r in range(linhas)]
    usadas = [(r, c) for r in range(linhas) for c in range(colunas) if alfa[r][c] > LIMITE]
    if not usadas:
        return None

    def gx(c):                  # ponto da grade -> pixel (centro do pixel)
        return c * PASSO + meio + 0.5

    def gy(r):
        return r * PASSO + meio + 0.5

    # retângulo da arma (com uma folga para a borda suave da imagem) e o centro dela,
    # que é em volta de onde a peça gira
    bx0 = max(0, (min(c for _, c in usadas) - 1) * PASSO)
    bx1 = min(largura, (max(c for _, c in usadas) + 2) * PASSO)
    by0 = max(0, (min(r for r, _ in usadas) - 1) * PASSO)
    by1 = min(altura, (max(r for r, _ in usadas) + 2) * PASSO)
    cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2

    def x(px):                  # pixel -> mundo (1 unidade = largura da imagem)
        return (px - cx) / largura

    def z(py):
        return (cy - py) / largura

    def u(px):
        return px / largura

    def v(py):
        return 1 - py / altura

    meia = ESPESSURA / 2

    # FRENTE (olhando de -Y) e VERSO (de +Y): um retângulo com a imagem cada
    faces = _Malha("skin_faces")
    uvs = [(u(bx0), v(by1)), (u(bx1), v(by1)), (u(bx1), v(by0)), (u(bx0), v(by0))]
    for y, normal in ((-meia, (0, -1, 0)), (meia, (0, 1, 0))):
        faces.quadrado([(x(bx0), y, z(by1)), (x(bx1), y, z(by1)), (x(bx1), y, z(by0)), (x(bx0), y, z(by0))],
                       normal, uvs)

    # LATERAIS: o contorno da arma é achado com "marching squares" (a borda passa
    # ENTRE os pontos da grade, no lugar exato onde a transparência cruza 50%):
    # assim as paredes seguem as curvas, sem degraus. A cor de cada parede vem de
    # um pouco PARA DENTRO da borda (a beirada das imagens da Steam tem um brilho
    # claro, que deixaria as paredes quase brancas).
    def cor_perto(px, py):
        soma_r = soma_g = soma_b = peso = 0.0
        for yy in range(max(0, int(py) - 1), min(altura, int(py) + 2)):
            for xx in range(max(0, int(px) - 1), min(largura, int(px) + 2)):
                a = imagem.getAlpha(xx, yy)
                if a > LIMITE:
                    cor = imagem.getXel(xx, yy)
                    soma_r += cor[0] * a
                    soma_g += cor[1] * a
                    soma_b += cor[2] * a
                    peso += a
        if peso == 0:
            return None
        return soma_r / peso * ESCURECER, soma_g / peso * ESCURECER, soma_b / peso * ESCURECER, 1.0

    def cruzamento(c1, r1, a1, c2, r2, a2):
        """Onde, entre dois pontos da grade, a transparência passa de 50%."""
        t = (LIMITE - a1) / (a2 - a1)
        return gx(c1) + (gx(c2) - gx(c1)) * t, gy(r1) + (gy(r2) - gy(r1)) * t

    lados = _Malha("skin_laterais", com_cor=True)
    for r in range(linhas - 1):
        for c in range(colunas - 1):
            a, b = alfa[r][c], alfa[r][c + 1]                  # cantos de cima (esquerda, direita)
            e, d = alfa[r + 1][c], alfa[r + 1][c + 1]          # cantos de baixo
            ca, cb, cd, ce = a > LIMITE, b > LIMITE, d > LIMITE, e > LIMITE
            if ca == cb == cd == ce:
                continue                                       # tudo cheio ou tudo vazio: sem borda aqui
            cima = cruzamento(c, r, a, c + 1, r, b) if ca != cb else None
            direita = cruzamento(c + 1, r, b, c + 1, r + 1, d) if cb != cd else None
            baixo = cruzamento(c, r + 1, e, c + 1, r + 1, d) if ce != cd else None
            esquerda = cruzamento(c, r, a, c, r + 1, e) if ca != ce else None
            pontos = [p for p in (cima, direita, baixo, esquerda) if p is not None]
            if len(pontos) == 2:
                segmentos = [pontos]
            elif ca == ((a + b + d + e) / 4 > LIMITE):         # "sela": cantos em diagonal
                segmentos = [(cima, direita), (baixo, esquerda)]
            else:
                segmentos = [(esquerda, cima), (direita, baixo)]

            for (px1, py1), (px2, py2) in segmentos:
                nx, ny = py2 - py1, -(px2 - px1)               # perpendicular à borda (em pixels)
                tamanho = math.hypot(nx, ny)
                if tamanho < 1e-6:
                    continue
                nx, ny = nx / tamanho, ny / tamanho
                mx, my = (px1 + px2) / 2, (py1 + py2) / 2

                def alfa_em(px, py):                           # transparência dentro desta célula
                    fx = min(1.0, max(0.0, (px - gx(c)) / PASSO))
                    fy = min(1.0, max(0.0, (py - gy(r)) / PASSO))
                    return (a * (1 - fx) * (1 - fy) + b * fx * (1 - fy) + e * (1 - fx) * fy + d * fx * fy)

                if alfa_em(mx + nx, my + ny) > alfa_em(mx - nx, my - ny):
                    nx, ny = -nx, -ny                          # a normal aponta para FORA (lado vazio)
                cor = (cor_perto(mx - nx * COR_DENTRO, my - ny * COR_DENTRO) or cor_perto(mx, my)
                       or (0.2, 0.2, 0.2, 1))
                lados.quadrado([(x(px1), -meia, z(py1)), (x(px2), -meia, z(py2)),
                                (x(px2), meia, z(py2)), (x(px1), meia, z(py1))],
                               (nx, 0, -ny), cor=cor)

    peca = NodePath("skin_3d")
    no_faces = faces.no()
    no_faces.setTransparency(TransparencyAttrib.MDual)   # bordas suaves da imagem, sem "serrilhado"
    no_faces.reparentTo(peca)
    no_lados = lados.no()
    no_lados.setTextureOff(1)                           # laterais: cor nos vértices, opacas
    no_lados.reparentTo(peca)
    return peca, (bx1 - bx0) / largura, (by1 - by0) / largura


def criar_skin_3d(textura):
    """Peça 3D da skin: (NodePath, largura, altura) ou None (sem imagem ou sem transparência).

    Medidas em "larguras da imagem" (1 = a largura do PNG inteiro): quem usa
    escolhe o tamanho com setScale.
    """
    if textura is None or not textura.hasFullpath():
        return None
    chave = textura.getFullpath().getFullpath()
    if chave not in _moldes:
        try:
            _moldes[chave] = _montar(textura.getFullpath())
        except Exception:
            logger.exception("Não foi possível montar a skin em 3D: %s", chave)
            _moldes[chave] = None
    molde = _moldes[chave]
    if molde is None:
        return None
    peca, largura, altura = molde
    copia = peca.copyTo(NodePath("skin"))
    copia.setTexture(textura, 1)
    return copia, largura, altura


# ======================================================================
# PALCO 3D: uma janelinha 3D própria
# ======================================================================

class Palco3D:
    """Cena 3D pequena e SEPARADA, desenhada numa área da janela (DisplayRegion).

    area: (esquerda, direita, baixo, cima) em FRAÇÃO da janela (0 a 1).
    ordem: em que camada desenha. O cenário da Home é 0 e a interface 2D é 10:
    5 fica entre os dois (pedestal); 20 fica por cima de tudo (inspeção, que
    abre dentro de uma janela da interface).
    Fundo transparente: o que está atrás aparece em volta da skin.
    """

    def __init__(self, app, area, ordem, fov):
        self.app = app
        self.cena = NodePath("palco_3d")
        self.regiao = app.win.makeDisplayRegion(*area)
        self.regiao.setSort(ordem)
        self.regiao.setClearColorActive(False)
        self.regiao.setClearDepthActive(True)
        self.lente = PerspectiveLens()
        self.lente.setFov(fov)
        self.camera = self.cena.attachNewNode(Camera("camera_palco", self.lente))
        self.regiao.setCamera(self.camera)
        self.ajustar_proporcao()

        # Luzes que acompanham a câmera (vêm sempre de cima, à esquerda de quem olha).
        # Só a skin usa luz (iluminar); o pedestal tem as sombras pintadas.
        ambiente = AmbientLight("ambiente")
        ambiente.setColor((LUZ_AMBIENTE, LUZ_AMBIENTE, LUZ_AMBIENTE, 1))
        sol = DirectionalLight("sol")
        sol.setColor((LUZ_SOL, LUZ_SOL * 0.97, LUZ_SOL * 0.93, 1))
        self.luz_ambiente = self.cena.attachNewNode(ambiente)
        self.luz_sol = self.camera.attachNewNode(sol)
        self.luz_sol.setHpr(-25, -30, 0)

    def iluminar(self, no):
        no.setLight(self.luz_ambiente)
        no.setLight(self.luz_sol)

    def ajustar_proporcao(self):
        """A lente precisa da proporção (largura/altura) da janelinha em pixels."""
        largura = self.regiao.getPixelWidth()
        altura = self.regiao.getPixelHeight()
        if largura > 0 and altura > 0:
            self.lente.setAspectRatio(largura / altura)

    def mudar_area(self, area):
        self.regiao.setDimensions(*area)
        self.ajustar_proporcao()

    def destruir(self):
        if self.regiao is not None:
            self.app.win.removeDisplayRegion(self.regiao)
            self.regiao = None
        self.cena.removeNode()


# ======================================================================
# INSPEÇÃO: girar a skin com o mouse
# ======================================================================

ORDEM_INSPECAO = 20             # por cima da interface (a inspeção fica dentro de uma janela dela)
FOV_INSPECAO = 24
DISTANCIA = 6.0
GRAUS_POR_TELA = 360            # arrastar a largura da tela inteira = uma volta
INCLINACAO_MAX = 40             # graus para cima/para baixo
GIRO_SOZINHO = 18               # graus por segundo quando ninguém mexe
ESPERA_GIRO_SOZINHO = 2.5       # segundos parado até voltar a girar sozinho
POSE_INICIAL = (-20, 8)         # (giro, inclinação): começa meio de lado, como no CS


class Inspecao3D(Palco3D):
    """A skin em 3D dentro de uma área da interface (ex.: janela da imagem ampliada).

    pai: nó da interface onde fica a área; x1, x2, z1, z2: a área, nas
    coordenadas do pai. Arrastar com o mouse gira (para os lados e um pouco
    para cima/baixo); solta e ela continua com o embalo e, parada, volta a
    girar devagar. Quando a janela fecha (o pai some), tudo se desfaz sozinho.
    """

    def __init__(self, app, pai, peca, x1, x2, z1, z2):
        self.app = app
        self.pai = pai
        self.retangulo = (x1, x2, z1, z2)
        self._area_atual = self._area()
        super().__init__(app, self._area_atual, ORDEM_INSPECAO, FOV_INSPECAO)
        self.camera.setPos(0, -DISTANCIA, 0)
        self.camera.lookAt(0, 0, 0)

        no, largura, altura = peca
        self.giro = self.cena.attachNewNode("giro")
        no.reparentTo(self.giro)
        self.iluminar(no)
        # tamanho: a arma ocupa ~85% da área (largura ou altura, o que limitar antes)
        visivel_l = 2 * DISTANCIA * math.tan(math.radians(FOV_INSPECAO / 2))
        visivel_a = visivel_l / max(self.lente.getAspectRatio(), 0.1)
        no.setScale(0.85 * min(visivel_l / largura, visivel_a / max(altura, 0.01)))

        self.h, self.p = POSE_INICIAL
        self.velocidade = 0.0           # embalo depois de soltar (graus/s)
        self.parado = ESPERA_GIRO_SOZINHO
        self.arrastando = None          # posição anterior do mouse enquanto arrasta

        # área "pegável" (invisível) por cima da imagem: arrastar aqui gira e não fecha a janela
        self.alca = DirectFrame(parent=pai, frameSize=(x1, x2, z1, z2), frameColor=(0, 0, 0, 0),
                                state=DGG.NORMAL)
        self.alca.bind(DGG.B1PRESS, self._pegar)
        self.alca.bind(DGG.B1RELEASE, self._soltar)
        self.tarefa = f"inspecao_3d_{next(_ids)}"
        app.taskMgr.add(self._atualizar, self.tarefa)
        self._aplicar_pose()

    def _area(self):
        """O retângulo da interface (coordenadas do pai) em fração da janela."""
        x1, x2, z1, z2 = self.retangulo
        tela = self.app.render2d
        a = tela.getRelativePoint(self.pai, Point3(x1, 0, z1))
        b = tela.getRelativePoint(self.pai, Point3(x2, 0, z2))

        def fracao(valor):
            return min(1.0, max(0.0, (valor + 1) / 2))

        return fracao(a.x), fracao(b.x), fracao(a.z), fracao(b.z)

    def _mouse(self):
        observador = self.app.mouseWatcherNode
        return observador.getMouse() if observador.hasMouse() else None

    def _pegar(self, _evento=None):
        mouse = self._mouse()
        if mouse is not None:
            self.arrastando = (mouse.x, mouse.y)
            self.velocidade = 0.0

    def _soltar(self, _evento=None):
        self.arrastando = None
        self.parado = 0.0

    def _aplicar_pose(self):
        self.giro.setHpr(self.h, self.p, 0)

    def _atualizar(self, task):
        if self.pai.isEmpty():                  # a janela fechou: some junto
            self.destruir()
            return task.done
        dt = min(ClockObject.getGlobalClock().getDt(), 0.1)

        area = self._area()                     # janela mudou de tamanho? acompanha
        if area != self._area_atual and area[0] < area[1] and area[2] < area[3]:
            self._area_atual = area
            self.mudar_area(area)

        if self.arrastando is not None:
            mouse = self._mouse()
            if mouse is None or not self.app.mouseWatcherNode.isButtonDown(MouseButton.one()):
                self._soltar()                  # soltou fora da área
            else:
                dx = mouse.x - self.arrastando[0]
                dy = mouse.y - self.arrastando[1]
                self.arrastando = (mouse.x, mouse.y)
                passo = dx / 2 * GRAUS_POR_TELA
                self.h += passo
                self.p = max(-INCLINACAO_MAX, min(INCLINACAO_MAX, self.p - dy / 2 * GRAUS_POR_TELA * 0.5))
                if dt > 0:
                    self.velocidade = 0.7 * self.velocidade + 0.3 * (passo / dt)
        else:
            self.parado += dt
            if abs(self.velocidade) > 1:        # embalo depois de soltar, diminuindo
                self.h += self.velocidade * dt
                self.velocidade *= math.exp(-3.0 * dt)
            elif self.parado >= ESPERA_GIRO_SOZINHO:
                self.h += GIRO_SOZINHO * dt     # ninguém mexendo: gira devagar
        self._aplicar_pose()
        return task.cont

    def destruir(self):
        if self.regiao is None:
            return
        self.app.taskMgr.remove(self.tarefa)
        if not self.alca.isEmpty():
            self.alca.destroy()
        super().destruir()


def inspecionar(app, pai, textura, x1, x2, z1, z2):
    """Abre a inspeção 3D na área (coordenadas de pai). None se não der (aí a tela usa a imagem plana)."""
    if app.win is None:
        return None
    peca = criar_skin_3d(textura)
    if peca is None:
        return None
    return Inspecao3D(app, pai, peca, x1, x2, z1, z2)
