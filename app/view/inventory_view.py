from direct.gui.DirectGui import DirectButton, DirectFrame

from app.view.game_view_base import GameViewBase

CATEGORIAS = [
    "TUDO",
    "EQUIPAMENTO",
    "ARTES GRÁFICAS",
    "RECIPIENTES",
    "DECORAÇÃO",
    "CONTRATO DE TROCA",
    "MERCADO",
]


class InventoryView(GameViewBase):

    def construir_conteudo(self):
        # Máscara escura do inventário (efeito de vidro esfumaçado escuro)
        self.inventory_mask = DirectFrame(
            frameColor=(0.08, 0.09, 0.11, 0.80),
            frameSize=(-2.0, 2.0, -2.80, 0.82),
            pos=(0, 0, 0.05),
            parent=self.ui_root
        )
        self.elementos.append(self.inventory_mask)

        # Sub-header de filtros do inventário
        sub_start_x = -0.85
        for i, categoria in enumerate(CATEGORIAS):
            DirectButton(
                text=categoria,
                text_scale=0.025,
                text_fg=(0.7, 0.7, 0.7, 1),
                frameColor=(0, 0, 0, 0),
                relief=None,
                pos=(sub_start_x + (i * 0.25), 0, 0.70),
                parent=self.inventory_mask
            )

        self._criar_grid()

    def _criar_grid(self):
        # Grade 5x3 de cards de itens.
        # TODO (roadmap, Fase 5): trocar os cards fixos pelas skins/caixas
        # reais do usuário, vindas do banco.
        columns = 5
        rows = 3
        spacing_x = 0.35
        spacing_y = 0.32
        start_x = -0.75
        start_y = 0.45

        for r in range(rows):
            for c in range(columns):
                DirectFrame(
                    frameColor=(0.18, 0.20, 0.23, 0.9),
                    frameSize=(-0.15, 0.15, -0.13, 0.13),
                    pos=(start_x + (c * spacing_x), 0, start_y - (r * spacing_y)),
                    parent=self.inventory_mask
                )
