from direct.gui.DirectGui import DirectLabel

from app.core.i18n import t
from app.view.game_view_base import GameViewBase

# Se o jogador entrar antes de o cenário 3D terminar de carregar (ele começa
# a carregar na tela de login), a Home mostra este aviso até o mapa aparecer.
TASK_AGUARDAR_CENARIO = "home_aguardar_cenario"


class HomeView(GameViewBase):

    ROTA = "home"

    def construir_conteudo(self):
        # Por enquanto a Home é só o cenário 3D + header, como no layout original.
        backdrop = self.view_manager.backdrop
        if backdrop and not backdrop.pronto:
            self.aviso_carregando = DirectLabel(
                text=t("Carregando cenário..."),
                text_scale=0.045,
                text_fg=(0.85, 0.85, 0.85, 1),
                frameColor=(0, 0, 0, 0),
                pos=(0, 0, 0),
                parent=self.ui_root
            )
            self.elementos.append(self.aviso_carregando)
            self.view_manager.app.taskMgr.add(self._aguardar_cenario, TASK_AGUARDAR_CENARIO)

    def _aguardar_cenario(self, task):
        # Confere a cada quadro; o cenário aparece sozinho quando fica pronto.
        if not self.view_manager.backdrop.pronto:
            return task.cont
        self.aviso_carregando.hide()
        return task.done

    def destruir(self):
        self.view_manager.app.taskMgr.remove(TASK_AGUARDAR_CENARIO)
        super().destruir()
