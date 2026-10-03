import logging
import math
import time
from collections import deque
from pathlib import Path

from panda3d.core import (
    AmbientLight,
    ClockObject,
    DirectionalLight,
    Filename,
    Point3,
    TransparencyAttrib,
    Vec3,
    Vec4,
)

logger = logging.getLogger(__name__)

ASSETS = Path(__file__).resolve().parent.parent / "assets"

# Mirage recortada para o menu: só a parte que a câmera enxerga, com texturas
# reduzidas (~50 MB no total; vai no Git). Se ela não existir, usa o mapa
# completo exportado do jogo (337 MB; fica fora do Git).
MAPA_MENU = ASSETS / "maps" / "mirage_menu" / "de_mirage_menu.glb"
MAPA_COMPLETO = ASSETS / "maps" / "de_mirage_d.glb"
PERSONAGEM = ASSETS / "characters" / "ctm_spawnpoint.glb"

COR_FUNDO_3D = (0.2, 0.4, 0.7, 1)
COR_FUNDO_UI = (0.05, 0.05, 0.07, 1)

# Envio do cenário para a placa de vídeo AOS POUCOS (ver _preparar_gpu_aos_poucos).
# Por quadro: no máximo ~4 texturas novas e ~8 ms de processamento, para a
# tela de login continuar fluida enquanto isso acontece.
TASK_GPU = "cenario_preparar_gpu"
TEXTURAS_POR_QUADRO = 4
TEMPO_POR_QUADRO = 0.008

# Câmera da Home (e o leve balanço dela no "modo vivo" da Home, Extras 4)
CAMERA_POS = Point3(-33.60, 19.90, -1.70)
CAMERA_HPR = Vec3(130, 0, 0)
TASK_BALANCO = "cenario_balanco_camera"


class SceneBackdrop:
    """Cenário 3D (mapa + personagem) usado atrás das telas do jogo.

    Existe uma única instância por programa: o ShowBase só pode ter um
    simplepbr.init() e os modelos pesados são carregados uma vez só.

    CARREGAMENTO EM SEGUNDO PLANO: a tela de login chama precarregar(), que
    pede ao Panda3D para ler os modelos numa thread separada (loadModel com
    callback). Assim a janela não trava; quando o jogador entra, o cenário
    normalmente já está pronto. Se ele entrar antes, a Home aparece e o
    cenário surge sozinho quando terminar de carregar.

    Estados: "vazio" -> "carregando" -> "pronto".
    É opcional: se faltar o asset, o jogo segue sem o cenário.
    """

    def __init__(self, app):
        self.app = app
        self._estado = "vazio"
        self._pendentes = 0          # quantos modelos ainda estão carregando
        self._visivel = False        # a tela atual quer o cenário à mostra?
        self._nos = []
        self._fila_gpu = deque()     # partes do cenário ainda não enviadas à placa de vídeo
        self._inicio_gpu = None

    @property
    def pronto(self):
        """True quando o carregamento terminou (com ou sem sucesso)."""
        return self._estado == "pronto"

    # ----------------------------------------------------------
    # API usada pelas telas
    # ----------------------------------------------------------

    def precarregar(self):
        """Começa a carregar mapa e personagem em segundo plano (não trava a janela).

        Pode ser chamado mais de uma vez: só a primeira chamada faz algo.
        """
        if self._estado != "vazio":
            return
        self._estado = "carregando"

        # PBR é opcional (pip install panda3d-simplepbr).
        try:
            import simplepbr
            simplepbr.init(max_lights=8, use_normal_maps=True, exposure=0.3)
        except ImportError:
            logger.warning("simplepbr não instalado: cenário sem PBR.")

        self.app.camera.setPos(CAMERA_POS)
        self.app.camera.setHpr(CAMERA_HPR)
        self.app.camLens.setFov(80)
        self._criar_luzes()

        mapa = MAPA_MENU if MAPA_MENU.exists() else MAPA_COMPLETO
        pedidos = []
        for caminho, ao_terminar in ((mapa, self._ao_carregar_mapa),
                                     (PERSONAGEM, self._ao_carregar_personagem)):
            if caminho.exists():
                pedidos.append((caminho, ao_terminar))
            else:
                logger.warning("Asset não encontrado: %s", caminho)

        # Conta TODOS os pedidos antes de iniciar o primeiro: o Panda3D pode
        # chamar o callback na hora (ex.: modelo já em cache) e o cenário não
        # pode ser dado como "pronto" enquanto o outro modelo nem começou.
        self._pendentes = len(pedidos)
        if not pedidos:
            self._finalizar()
            return
        for caminho, ao_terminar in pedidos:
            self._carregar_em_segundo_plano(caminho, ao_terminar)

    def mostrar(self):
        self._visivel = True
        if self._estado == "vazio":
            self.precarregar()
        if self.pronto:
            self._aplicar_visibilidade()
        # Se ainda está carregando, _finalizar() mostra o cenário quando terminar.

    def ocultar(self):
        self._visivel = False
        self._aplicar_visibilidade()

    def iniciar_balanco(self):
        """Home: a câmera "respira" devagar (gira menos de 2 graus para os lados).
        O personagem está preso à câmera, então só o mapa ao fundo se move."""
        if not self.app.taskMgr.hasTaskNamed(TASK_BALANCO):
            self._tempo_balanco = 0.0
            self.app.taskMgr.add(self._balancar, TASK_BALANCO)

    def parar_balanco(self):
        self.app.taskMgr.remove(TASK_BALANCO)
        self.app.camera.setHpr(CAMERA_HPR)

    def _balancar(self, task):
        self._tempo_balanco += min(ClockObject.getGlobalClock().getDt(), 0.1)
        t = self._tempo_balanco
        self.app.camera.setHpr(CAMERA_HPR + Vec3(1.6 * math.sin(t * 0.21), 0.5 * math.sin(t * 0.13 + 1.0), 0))
        return task.cont

    # ----------------------------------------------------------
    # Carregamento
    # ----------------------------------------------------------

    def _carregar_em_segundo_plano(self, caminho, ao_terminar):
        try:
            # callback = carregamento assíncrono: o Panda3D lê o arquivo numa
            # thread e chama _ao_carregar no programa principal quando acabar.
            self.app.loader.loadModel(
                Filename.fromOsSpecific(str(caminho)),
                callback=self._ao_carregar,
                extraArgs=[ao_terminar, caminho.name],
            )
        except Exception:
            logger.exception("Não foi possível iniciar o carregamento de %s", caminho.name)
            self._um_pedido_a_menos()

    def _ao_carregar(self, modelo, ao_terminar, nome):
        """Chamado pelo Panda3D (no programa principal) quando um modelo termina de carregar."""
        try:
            if modelo is None or modelo.isEmpty():
                logger.warning("Não foi possível carregar %s.", nome)
            else:
                ao_terminar(modelo)
                self._agendar_envio_para_gpu(modelo)
        except Exception:
            logger.exception("Falha ao montar %s", nome)
        finally:
            self._um_pedido_a_menos()

    def _um_pedido_a_menos(self):
        self._pendentes -= 1
        if self._pendentes <= 0:
            self._finalizar()

    def _ao_carregar_mapa(self, mapa):
        mapa.reparentTo(self.app.render)
        mapa.setPos(0, 0, 0)
        mapa.setHpr(0, 90, 0)
        # Remove transparências e emissões estouradas.
        mapa.setTransparency(TransparencyAttrib.M_none, 1)
        mapa.setDepthWrite(True, 1)
        # Filtro sutil de tom alaranjado/desértico.
        mapa.setColorScale(Vec4(0.85, 0.8, 0.75, 1.0), 1)
        mapa.hide()
        self._nos.append(mapa)

    def _ao_carregar_personagem(self, personagem):
        personagem.reparentTo(self.app.camera)
        personagem.setPos(1.2, 3.5, -1.7)
        personagem.setHpr(0, 90, 0)
        personagem.hide()
        self._nos.append(personagem)

    def _finalizar(self):
        self._estado = "pronto"
        self._aplicar_visibilidade()

    def _aplicar_visibilidade(self):
        mostrar = self._visivel and self.pronto
        for no in self._nos:
            no.show() if mostrar else no.hide()
        self.app.setBackgroundColor(*(COR_FUNDO_3D if mostrar else COR_FUNDO_UI))

    # ----------------------------------------------------------
    # Envio para a placa de vídeo (enquanto o jogador está no login)
    # ----------------------------------------------------------

    def _agendar_envio_para_gpu(self, modelo):
        """Coloca as partes do modelo numa fila para irem à placa de vídeo aos poucos.

        Sem isto, o primeiro quadro da Home teria que enviar ~260 texturas e
        toda a geometria de uma vez, e o jogo congelaria nesse momento.
        """
        if self.app.win is None or self.app.win.getGsg() is None:
            return
        self._fila_gpu.extend(modelo.findAllMatches("**/+GeomNode"))
        if self._inicio_gpu is None:
            self._inicio_gpu = time.perf_counter()
        if not self.app.taskMgr.hasTaskNamed(TASK_GPU):
            self.app.taskMgr.add(self._preparar_gpu_aos_poucos, TASK_GPU)

    def _preparar_gpu_aos_poucos(self, task):
        """Roda a cada quadro até a fila esvaziar.

        prepareScene() de uma parte (GeomNode) deixa a geometria no formato da
        placa de vídeo e agenda o envio dela, das texturas e do shader para o
        próximo quadro. Fazemos poucas partes por quadro (limite de texturas
        novas e de tempo) para o login não engasgar.
        """
        janela = self.app.win
        gsg = janela.getGsg() if janela is not None else None
        if gsg is None:
            self._fila_gpu.clear()
            return task.done
        objetos = gsg.getPreparedObjects()

        inicio = time.perf_counter()
        texturas_novas = 0
        while self._fila_gpu:
            no = self._fila_gpu.popleft()
            if no.isEmpty():
                continue
            texturas_novas += sum(
                1 for textura in no.findAllTextures() if not textura.isPrepared(objetos)
            )
            no.prepareScene(gsg)
            if texturas_novas >= TEXTURAS_POR_QUADRO or time.perf_counter() - inicio >= TEMPO_POR_QUADRO:
                break  # continua no próximo quadro

        if self._fila_gpu:
            return task.cont
        logger.info("Cenário enviado à placa de vídeo em %.1f s.", time.perf_counter() - self._inicio_gpu)
        self._inicio_gpu = None
        return task.done

    def _criar_luzes(self):
        # Sombra fria e fechada
        alight = AmbientLight("alight")
        alight.setColor((0.05, 0.05, 0.08, 1))
        self.app.render.setLight(self.app.render.attachNewNode(alight))

        # Sol desértico concentrado
        dlight = DirectionalLight("dlight")
        dlight.setColor((1.8, 1.3, 0.8, 1))
        dlnp = self.app.render.attachNewNode(dlight)
        dlnp.setHpr(-45, -35, 0)
        self.app.render.setLight(dlnp)
