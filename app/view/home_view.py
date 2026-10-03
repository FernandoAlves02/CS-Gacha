"""HOME (Extras 4): o cenário 3D "vivo", para deixar aberto como wallpaper.

- janelinha de ESTATÍSTICAS flutuando devagar (como se fosse o vento);
- PEDESTAL girando com a skin em destaque (escolhida no inventário, ou a
  mais valiosa do jogador): ver vitrine_3d.py;
- a câmera do cenário "respira" (gira menos de 2 graus para os lados);
- tecla H: modo wallpaper (esconde o menu de cima); H ou ESC voltam.

Os números vêm do Home_Controller (tabela user_transactions, migração 004).
"""
import math
from datetime import datetime, timedelta

from direct.gui.DirectGui import DirectLabel
from direct.showbase.DirectObject import DirectObject
from panda3d.core import ClockObject

from app.controller.home_controller import Home_Controller
from app.core import preferencias
from app.core.game_rules import INVENTORY_LIMIT, format_money, format_wait, rarity_label
from app.core.i18n import numero, t
from app.view.game_view_base import GameViewBase
from app.view.ui_kit import (
    CENTRO,
    COR_LARANJA,
    COR_LINHA,
    COR_OURO,
    COR_TEXTO,
    COR_TEXTO_2,
    COR_TEXTO_3,
    COR_VERDE,
    DIREITA,
    Aviso,
    limpar_nome,
)
from app.view.vitrine_3d import Vitrine3D

# Se o jogador entrar antes de o cenário 3D terminar de carregar (ele começa
# a carregar na tela de login), a Home mostra este aviso até o mapa aparecer.
TASK_AGUARDAR_CENARIO = "home_aguardar_cenario"
TASK_ANIMAR = "home_animar"
TASK_AVISO = "home_aviso"

# Medidas (unidades do aspect2d numa janela 16:9; em janelas mais estreitas tudo diminui junto).
# O personagem do cenário fica no centro-direita, então o pedestal vai à esquerda
# e a janelinha de estatísticas no canto direito, acima da cabeça dele.
VITRINE = (-1.62, -0.72, -0.46, 0.66)          # x1, x2, z1, z2 da área do pedestal
PAINEL_X1, PAINEL_X2, PAINEL_TOPO = 0.98, 1.68, 0.66
LINHA = 0.062                                  # altura de cada linha do painel
COR_PAINEL_HOME = (0.06, 0.065, 0.08, 0.82)


class HomeView(GameViewBase):

    ROTA = "home"

    def construir_conteudo(self):
        vm = self.view_manager
        self.app = vm.app
        backdrop = vm.backdrop
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
            self.app.taskMgr.add(self._aguardar_cenario, TASK_AGUARDAR_CENARIO)

        self.controller = Home_Controller(vm.inventory_dao, vm.usuario_logado)
        self.raiz = self.ui.container(self.ui_root)
        self.elementos.append(self.raiz)
        self.aviso = Aviso(self.ui, self.raiz, TASK_AVISO, z=-0.93)
        self.animado = preferencias.obter("animacoes")    # CONFIGURAÇÕES: animações da Home
        self.vitrine = None
        self.wallpaper = False
        self.lbl_gratis = None
        self.gratis_libera_em = None
        self.tempo = 0.0

        self.painel = self.ui.container(self.raiz)      # a janelinha que "flutua"
        self._desenhar_estatisticas()
        self._desenhar_destaque()
        self.dica = self.ui.texto(self.raiz, t("H: modo wallpaper (esconde o menu)"), PAINEL_X2, -0.90, 0.024,
                                  COR_TEXTO_2, DIREITA)

        self.eventos = DirectObject()
        self.eventos.accept("h", self._alternar_wallpaper)
        self.eventos.accept("escape", self._sair_do_wallpaper)
        self.eventos.accept("aspectRatioChanged", self._ajustar_escala)
        self._ajustar_escala()
        self.app.taskMgr.add(self._animar, TASK_ANIMAR)
        if backdrop and self.animado:
            backdrop.iniciar_balanco()

    # ==================================================================
    # JANELINHA DE ESTATÍSTICAS
    # ==================================================================

    def _desenhar_estatisticas(self):
        ui = self.ui
        p = self.painel
        x1, x2 = PAINEL_X1, PAINEL_X2
        esq, dir_ = x1 + 0.04, x2 - 0.04
        stats = self.controller.stats()

        linhas = []                       # (rótulo, valor, cor do valor)
        if stats is not None:
            abertas = numero(stats.cases_opened, 0)
            if stats.free_cases_opened:
                abertas = t("{n} ({gratis} grátis)", n=abertas, gratis=numero(stats.free_cases_opened, 0))
            linhas = [
                (t("Caixas abertas"), abertas, COR_TEXTO),
                (t("Gasto no mercado"), format_money(stats.spent), COR_TEXTO),
                (t("Recebido em vendas"), format_money(stats.earned), COR_VERDE),
                (t("Valor movimentado"), format_money(stats.moved), COR_LARANJA),
                (t("Itens no inventário"), f"{numero(stats.items, 0)} / {numero(INVENTORY_LIMIT, 0)}", COR_TEXTO),
            ]

        # altura do painel conforme o conteúdo
        espera = self.controller.free_case_wait()
        altura = 0.13 + LINHA * len(linhas) + (0.20 if stats is not None else 0.10) + (0.10 if espera is not None
                                                                                      else 0.02)
        topo, base = PAINEL_TOPO, PAINEL_TOPO - altura
        ui.retangulo(p, x1, x2, base, topo, COR_PAINEL_HOME)
        ui.retangulo(p, x1, x2, topo - 0.006, topo, COR_LARANJA)
        ui.texto(p, t("SUAS ESTATÍSTICAS"), esq, topo - 0.07, 0.03, COR_TEXTO, negrito=True)

        z = topo - 0.145
        if stats is None:
            ui.texto(p, t("Estatísticas indisponíveis no momento."), esq, z, 0.026, COR_TEXTO_3)
            z -= 0.10
        for rotulo, valor, cor in linhas:
            ui.texto(p, rotulo, esq, z, 0.025, COR_TEXTO_2)
            ui.texto(p, valor, dir_, z, 0.027, cor, DIREITA, negrito=True)
            z -= LINHA

        if stats is not None:
            ui.retangulo(p, esq, dir_, z + 0.03, z + 0.033, COR_LINHA)
            ui.texto(p, t("MELHOR DROP"), esq, z - 0.015, 0.022, COR_TEXTO_3, negrito=True)
            if stats.best_drop is not None:
                skin = stats.best_drop
                cor = COR_OURO if skin.rarity and skin.rarity.name == "Special Item" else skin.rarity.color_rgba
                ui.texto(p, limpar_nome(skin.name), esq, z - 0.065, 0.026, cor, negrito=True,
                         largura_max=dir_ - esq - 0.20)
                ui.texto(p, format_money(stats.best_drop_value), dir_, z - 0.065, 0.026, COR_TEXTO, DIREITA)
            else:
                ui.texto(p, t("Abra uma caixa para aparecer aqui."), esq, z - 0.065, 0.024, COR_TEXTO_3)
            z -= 0.20
            ui.texto(p, t("Caixas abertas por todos os jogadores: {n}", n=numero(stats.cases_opened_everyone, 0)),
                     esq, z + 0.06, 0.021, COR_TEXTO_3)

        # Caixa grátis: atalho quando está pronta, contagem quando ainda falta
        if espera is not None:
            self.gratis_libera_em = datetime.now() + espera
            if espera <= timedelta(0):
                ui.botao(p, t("CAIXA GRÁTIS PRONTA"), (x1 + x2) / 2, base + 0.055, x2 - x1 - 0.08, 0.07,
                         self.view_manager.mudar_tela_base, ["inventory"], escala=0.024)
            else:
                self.lbl_gratis = ui.texto(p, "", (x1 + x2) / 2, base + 0.045, 0.024, COR_VERDE, CENTRO)
                self._atualizar_gratis()

    def _atualizar_gratis(self):
        if self.lbl_gratis is None:
            return
        espera = max(timedelta(0), self.gratis_libera_em - datetime.now())
        if espera > timedelta(0):
            self.lbl_gratis.setText(t("Próxima caixa grátis em {tempo}", tempo=format_wait(espera)))
            return
        # liberou: desenha a janelinha de novo, agora com o botão CAIXA GRÁTIS PRONTA
        self.lbl_gratis = None
        self.painel.destroy()
        self.painel = self.ui.container(self.raiz)
        self._desenhar_estatisticas()

    # ==================================================================
    # PEDESTAL COM A SKIN EM DESTAQUE
    # ==================================================================

    def _desenhar_destaque(self):
        ui = self.ui
        x1, x2, z1, z2 = VITRINE
        centro = (x1 + x2) / 2
        instancia, escolhida = self.controller.featured()
        if instancia is None:
            ui.texto(self.raiz, t("Abra uma caixa: sua melhor skin aparece aqui."), centro, (z1 + z2) / 2, 0.028,
                     COR_TEXTO_2, CENTRO, quebra_em=x2 - x1)
            return
        skin = instancia.skin
        cor = COR_OURO if skin.rarity.name == "Special Item" else skin.rarity.color_rgba
        if self.app.win is not None:
            self.vitrine = Vitrine3D(self.app, ui.textura_item(skin.api_id), cor, self._area_vitrine(),
                                     girar=self.animado)
        # plaquinha com o nome embaixo do pedestal (fundo escuro: legível sobre qualquer parte do mapa)
        placa = self.ui.container(self.raiz)
        ui.retangulo(placa, x1 - 0.06, x2 + 0.06, z1 - 0.235, z1 - 0.01, COR_PAINEL_HOME)
        ui.retangulo(placa, x1 - 0.06, x2 + 0.06, z1 - 0.235, z1 - 0.229, cor)
        rotulo = t("SKIN EM DESTAQUE") if escolhida else t("SUA SKIN MAIS VALIOSA")
        ui.texto(placa, rotulo, centro, z1 - 0.06, 0.022, COR_TEXTO_2, CENTRO, negrito=True)
        ui.texto(placa, limpar_nome(skin.name), centro, z1 - 0.125, 0.036, COR_TEXTO, CENTRO, negrito=True,
                 largura_max=x2 - x1 + 0.08)
        ui.texto(placa, f"{rarity_label(skin.rarity.name)}  ·  {instancia.wear_label}  ·  "
                        f"{format_money(instancia.skin_price)}", centro, z1 - 0.185, 0.024, cor, CENTRO,
                 largura_max=x2 - x1 + 0.08)

    def _area_vitrine(self):
        """A área do pedestal (unidades do aspect2d) em fração da janela, como a DisplayRegion pede."""
        proporcao = self.app.getAspectRatio()
        escala = self.raiz.getScale()[0]
        x1, x2, z1, z2 = VITRINE
        return ((x1 * escala / proporcao + 1) / 2, (x2 * escala / proporcao + 1) / 2,
                (z1 * escala + 1) / 2, (z2 * escala + 1) / 2)

    # ==================================================================
    # ANIMAÇÃO, WALLPAPER E TAMANHO DA JANELA
    # ==================================================================

    def _animar(self, task):
        """A janelinha balança devagar, como se fosse o vento (posição e um pouco de giro)."""
        segundo_antes = int(self.tempo)
        self.tempo += min(ClockObject.getGlobalClock().getDt(), 0.1)
        tt = self.tempo
        if self.animado:
            self.painel.setPos(0.012 * math.sin(tt * 0.7), 0, 0.010 * math.sin(tt * 1.1 + 1.3))
            self.painel.setR(0.35 * math.sin(tt * 0.5))
        if int(tt) != segundo_antes:
            self._atualizar_gratis()                     # contagem: uma vez por segundo
        return task.cont

    def _alternar_wallpaper(self):
        if self.modal_do_header_aberto():
            return                                       # digitando no "Minha conta"
        self.wallpaper = not self.wallpaper
        if self.wallpaper:
            self.header_frame.hide()
            self.dica.hide()
            self.aviso.mostrar(t("Modo wallpaper: aperte H ou ESC para voltar."), segundos=3.0, som=False)
        else:
            self.header_frame.show()
            self.dica.show()
            self.aviso.esconder()

    def _sair_do_wallpaper(self):
        if self.wallpaper and not self.modal_do_header_aberto():
            self._alternar_wallpaper()

    def _ajustar_escala(self):
        """Em janelas mais estreitas que 16:9 tudo diminui para caber (o pedestal junto)."""
        self.raiz.setScale(min(1.0, self.app.getAspectRatio() / (16 / 9)))
        if self.vitrine is not None:
            self.vitrine.mudar_area(self._area_vitrine())

    def _aguardar_cenario(self, task):
        # Confere a cada quadro; o cenário aparece sozinho quando fica pronto.
        if not self.view_manager.backdrop.pronto:
            return task.cont
        self.aviso_carregando.hide()
        return task.done

    def destruir(self):
        self.app.taskMgr.remove(TASK_AGUARDAR_CENARIO)
        self.app.taskMgr.remove(TASK_ANIMAR)
        self.eventos.ignoreAll()
        self.aviso.esconder()
        if self.vitrine is not None:
            self.vitrine.destruir()
            self.vitrine = None
        if self.view_manager.backdrop:
            self.view_manager.backdrop.parar_balanco()
        super().destruir()
