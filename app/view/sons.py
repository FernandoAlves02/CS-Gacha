"""SONS E MÚSICA do jogo (Extras 5). Todos CC0: ver app/assets/sounds/CREDITOS.txt.

- Clique: vale para TODOS os botões (DirectButton) de uma vez, como som padrão
  do DirectGUI (DGG.setDefaultClickSound). Por isso o Sons é criado no main.py
  antes de qualquer tela.
- Efeitos com nome (tique da roleta, sucesso, erro, resultado, raro): as telas
  chamam tocar_som(app, "nome").
- Música do menu: toca em loop desde o login.
- Volume de 0 a 100, separado para efeitos e música (CONFIGURAÇÕES), com
  curva (Extras 6): ver preferencias.volume_real().

Sem placa de som (ou sem os arquivos), tudo vira "não faz nada": o jogo segue normal.
"""
import logging

from direct.gui import DirectGuiGlobals as DGG
from panda3d.core import Filename

from app.core import preferencias
from app.core.paths import ASSETS_DIR

logger = logging.getLogger(__name__)

PASTA_SONS = ASSETS_DIR / "sounds"
EFEITOS = ("clique", "tique", "sucesso", "erro", "resultado", "raro")
MUSICA = "musica_menu.ogg"


def tocar_som(app, nome):
    """Toca um efeito, se o jogo tiver sons (nos testes sem o main.py, não faz nada)."""
    sons = getattr(app, "sons", None)
    if sons is not None:
        sons.tocar(nome)


class Sons:

    def __init__(self, app):
        self.app = app
        self.efeitos = {}
        for nome in EFEITOS:
            som = self._carregar(app.loader.loadSfx, PASTA_SONS / f"{nome}.ogg")
            if som is not None:
                self.efeitos[nome] = som
        if "clique" in self.efeitos:
            DGG.setDefaultClickSound(self.efeitos["clique"])   # todo botão criado depois faz "clique"

        self.musica = self._carregar(app.loader.loadMusic, PASTA_SONS / MUSICA)
        self.aplicar_volumes()
        if self.musica is not None:
            self.musica.setLoop(True)
            self.musica.play()

    @staticmethod
    def _carregar(funcao, caminho):
        if not caminho.exists():
            logger.warning("Som não encontrado: %s", caminho)
            return None
        try:
            return funcao(Filename.fromOsSpecific(str(caminho)))
        except Exception:
            logger.warning("Não foi possível carregar o som %s", caminho.name)
            return None

    def aplicar_volumes(self):
        """Lê o volume das preferências (0 a 100) e aplica nos dois "canais", com a curva."""
        efeitos = preferencias.volume_real("volume_efeitos")
        musica = preferencias.volume_real("volume_musica")
        for gerente in getattr(self.app, "sfxManagerList", None) or []:
            gerente.setVolume(efeitos)
        gerente_musica = getattr(self.app, "musicManager", None)
        if gerente_musica is not None:
            gerente_musica.setVolume(musica)

    def tocar(self, nome):
        som = self.efeitos.get(nome)
        if som is not None and preferencias.obter("volume_efeitos") > 0:
            som.play()
