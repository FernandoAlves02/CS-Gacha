class ViewManager:
    def __init__(self, render2d, app):
        self.render2d = render2d
        self.app = app
        
        # Rotas registradas (mapeia 'nome_da_rota': classe_da_view)
        self.rotas_base = {}
        self.rotas_overlay = {}

        # Instâncias ativas na tela
        self.tela_base_atual = None
        self.overlay_atual = None

    def registrar_tela_base(self, nome, classe_view):
        """Registra uma classe de View como tela base."""
        self.rotas_base[nome] = classe_view

    def registrar_overlay(self, nome, classe_view):
        """Registra uma classe de View como overlay."""
        self.rotas_overlay[nome] = classe_view

    def mudar_tela_base(self, nome_rota):
        """Destrói a tela base atual (e qualquer overlay) e abre a nova tela base."""
        # 1. Limpa overlays ativos, se houver
        self.fechar_overlay()

        # 2. Destrói a tela base atual se ela existir
        if self.tela_base_atual:
            self.tela_base_atual.destruir()
            self.tela_base_atual = None

        # 3. Instancia e constrói a nova tela base
        if nome_rota in self.rotas_base:
            classe_view = self.rotas_base[nome_rota]
            self.tela_base_atual = classe_view(self.render2d, self)
            self.tela_base_atual.construir_tela()
        else:
            raise KeyError(f"Rota de tela base '{nome_rota}' não registrada no ViewManager.")

    def abrir_overlay(self, nome_rota):
        """Abre uma view em camada por cima da tela base atual."""
        if self.overlay_atual:
            self.overlay_atual.destruir()
            self.overlay_atual = None

        if nome_rota in self.rotas_overlay:
            classe_view = self.rotas_overlay[nome_rota]
            self.overlay_atual = classe_view(self.render2d, self)
            self.overlay_atual.construir_tela()
        else:
            raise KeyError(f"Rota de overlay '{nome_rota}' não registrada no ViewManager.")

    def fechar_overlay(self):
        """Fecha o overlay ativo mantendo a tela base intacta."""
        if self.overlay_atual:
            self.overlay_atual.destruir()
            self.overlay_atual = None