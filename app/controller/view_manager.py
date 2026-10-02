import logging

logger = logging.getLogger(__name__)


class ViewManager:
    """Controla qual tela está ativa.

    Contrato de uma tela (view): a classe recebe (ui_root, view_manager) no
    construtor e implementa construir_tela() e destruir().
    """

    ROTA_LOGIN = "login"

    def __init__(self, ui_root, app):
        self.ui_root = ui_root      # nó 2D onde as telas são desenhadas (aspect2d)
        self.app = app              # a instância do ShowBase

        # Dependências compartilhadas, preenchidas no main.py
        self.user_dao = None
        self.backdrop = None

        # Sessão: usuário logado (None = ninguém logado)
        self.usuario_logado = None

        self._telas = {}
        self._tela_atual = None

    def registrar_tela_base(self, nome, classe_view):
        self._telas[nome] = classe_view

    def tem_tela(self, nome):
        return nome in self._telas

    def mudar_tela_base(self, nome):
        if nome not in self._telas:
            logger.warning("Tela '%s' não registrada.", nome)
            return

        # Qualquer tela, exceto o login, exige usuário logado.
        if nome != self.ROTA_LOGIN and self.usuario_logado is None:
            nome = self.ROTA_LOGIN

        if self._tela_atual is not None:
            self._tela_atual.destruir()
            self._tela_atual = None

        self._tela_atual = self._telas[nome](self.ui_root, self)
        self._tela_atual.construir_tela()

    def sair(self):
        self.usuario_logado = None
        self.mudar_tela_base(self.ROTA_LOGIN)
