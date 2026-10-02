import logging
from pathlib import Path

from panda3d.core import (
    AmbientLight,
    DirectionalLight,
    Filename,
    Point3,
    TransparencyAttrib,
    Vec3,
    Vec4,
)

logger = logging.getLogger(__name__)

ASSETS = Path(__file__).resolve().parent.parent / "assets"

COR_FUNDO_3D = (0.2, 0.4, 0.7, 1)
COR_FUNDO_UI = (0.05, 0.05, 0.07, 1)


class SceneBackdrop:
    """Cenário 3D (mapa + personagem) usado atrás das telas do jogo.

    Existe uma única instância por programa: o ShowBase só pode ter um
    simplepbr.init() e os modelos pesados são carregados uma vez só.
    É opcional: se faltar o asset ou o plugin .glb, o jogo segue sem o cenário.
    """

    def __init__(self, app):
        self.app = app
        self._carregado = False
        self._nos = []

    def mostrar(self):
        if not self._carregado:
            self._carregar()
        self.app.setBackgroundColor(*COR_FUNDO_3D)
        for no in self._nos:
            no.show()

    def ocultar(self):
        for no in self._nos:
            no.hide()
        self.app.setBackgroundColor(*COR_FUNDO_UI)

    # ----------------------------------------------------------

    def _carregar(self):
        self._carregado = True

        # PBR é opcional (pip install panda3d-simplepbr).
        try:
            import simplepbr
            simplepbr.init(max_lights=8, use_normal_maps=True, exposure=0.3)
        except ImportError:
            logger.warning("simplepbr não instalado: cenário sem PBR.")

        mapa = self._carregar_modelo(ASSETS / "maps" / "de_mirage_d.glb")
        if mapa is not None:
            mapa.reparentTo(self.app.render)
            mapa.setPos(0, 0, 0)
            mapa.setHpr(0, 90, 0)
            # Remove transparências e emissões estouradas.
            mapa.setTransparency(TransparencyAttrib.M_none, 1)
            mapa.setDepthWrite(True, 1)
            # Filtro sutil de tom alaranjado/desértico.
            mapa.setColorScale(Vec4(0.85, 0.8, 0.75, 1.0), 1)
            self._nos.append(mapa)

        self.app.camera.setPos(Point3(-33.60, 19.90, -1.70))
        self.app.camera.setHpr(Vec3(130, 0, 0))
        self.app.camLens.setFov(80)

        personagem = self._carregar_modelo(ASSETS / "characters" / "ctm_spawnpoint.glb")
        if personagem is not None:
            personagem.reparentTo(self.app.camera)
            personagem.setPos(1.2, 3.5, -1.7)
            personagem.setHpr(0, 90, 0)
            self._nos.append(personagem)

        self._criar_luzes()

    def _carregar_modelo(self, caminho):
        if not caminho.exists():
            logger.warning("Asset não encontrado: %s", caminho)
            return None
        try:
            return self.app.loader.loadModel(Filename.fromOsSpecific(str(caminho)))
        except OSError:
            # Normalmente: plugin .glb ausente (pip install panda3d-gltf).
            logger.warning("Não foi possível carregar %s (falta panda3d-gltf?).", caminho.name)
            return None

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
