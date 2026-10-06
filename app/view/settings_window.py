"""Pop-up CONFIGURAÇÕES (Extras 5): abre pelo botão CONFIGURAÇÕES do header.

Junta num lugar só: Minha conta, idioma, moeda (Automática / R$ / US$),
tela cheia, volume dos efeitos e da música e as animações da Home.
As escolhas ficam salvas NESTE computador (app/core/preferencias.py e o
idioma.txt do i18n); a conta do jogador no banco não muda.

Idioma, moeda e animações mudam textos e valores da tela inteira: nesses
casos a tela é desenhada de novo e esta janela abre de novo por cima.
"""
from direct.gui import DirectGuiGlobals as DGG
from direct.gui.DirectSlider import DirectSlider
from direct.showbase.DirectObject import DirectObject

from app.core import i18n, preferencias
from app.core.game_rules import BRL_PER_USD
from app.core.i18n import numero, t
from app.view.sons import tocar_som
from app.view.ui_kit import CENTRO, COR_LARANJA, COR_LINHA, COR_TEXTO, COR_TEXTO_2, COR_TEXTO_3, ESQUERDA, Janela

PASSO_VOLUME = 1                  # − e + (a barra de arrastar também anda de 1 em 1)
ESPERA_SALVAR = 0.4               # segundos parado antes de gravar o volume no arquivo
TASK_SALVAR_VOLUME = "config_salvar_"


class JanelaConfiguracoes:

    LARGURA, ALTURA = 2.2, 1.62

    def __init__(self, tela, ao_fechar=None):
        """tela: a GameViewBase que abriu (header, kit de interface e ViewManager)."""
        self.tela = tela
        self.app = tela.view_manager.app
        self.ao_fechar = ao_fechar
        self.janela = Janela(tela.ui, tela.ui_root, self.LARGURA, self.ALTURA, t("CONFIGURAÇÕES"),
                             ao_fechar=self._ao_fechar)
        self.area = None
        self.volumes = {}         # chave -> (barra, parte laranja, rótulo "37%", x1, x2)
        self._desenhar()
        self.eventos = DirectObject()
        self.eventos.accept("escape", self.fechar)
        self.eventos.accept("f11", self._desenhar)    # F11 (main.py) troca a tela cheia: atualiza o botão

    # ==================================================================
    # DESENHO
    # ==================================================================

    def _desenhar(self):
        """(Re)desenha o conteúdo: o botão da opção escolhida fica laranja."""
        ui = self.tela.ui
        if self.area is not None:
            self.area.destroy()
        self.area = area = ui.container(self.janela.painel)
        x_rotulo = -self.LARGURA / 2 + 0.08
        x_opcoes = -0.30
        z = self.ALTURA / 2 - 0.24

        def linha(rotulo, dica=None):
            nonlocal z
            ui.texto(area, rotulo, x_rotulo, z - 0.012, 0.026, COR_TEXTO_2, ESQUERDA, negrito=True)
            if dica:
                ui.texto(area, dica, x_opcoes, z - 0.085, 0.021, COR_TEXTO_3, ESQUERDA)
            linha_z = z
            z -= 0.18 if dica else 0.135
            return linha_z

        def opcoes(z_linha, escolhas, atual, ao_escolher, largura=0.36):
            x = x_opcoes + largura / 2
            for valor, rotulo in escolhas:
                ui.botao(area, rotulo, x, z_linha, largura, 0.075, ao_escolher, [valor],
                         tipo="primario" if valor == atual else "secundario", escala=0.026)
                x += largura + 0.03

        def volume(z_linha, chave):
            """[−] ======o====== [+]  37%   (barra de arrastar; − e + mudam de 1 em 1)"""
            valor = preferencias.obter(chave)
            x1, x2 = x_opcoes + 0.12, x_opcoes + 0.80                   # trilho da barra
            ui.botao(area, "−", x_opcoes + 0.045, z_linha, 0.09, 0.075, self._passo_volume, [chave, -PASSO_VOLUME],
                     tipo="secundario", escala=0.04)
            ui.retangulo(area, x1, x2, z_linha - 0.005, z_linha + 0.005, COR_LINHA)
            cheio = ui.retangulo(area, x1, x1 + (x2 - x1) * valor / 100, z_linha - 0.005, z_linha + 0.005,
                                 COR_LARANJA)
            barra = DirectSlider(
                parent=area, range=(0, 100), value=valor, pageSize=5, scrollSize=PASSO_VOLUME,
                pos=((x1 + x2) / 2, 0, z_linha),
                # área de clique alta e invisível; o trilho que aparece é o retângulo de cima
                frameSize=(-(x2 - x1) / 2, (x2 - x1) / 2, -0.035, 0.035),
                frameColor=(0, 0, 0, 0), relief=DGG.FLAT,
                thumb_relief=DGG.FLAT, thumb_frameSize=(-0.014, 0.014, -0.032, 0.032), thumb_frameColor=COR_LARANJA,
            )
            ui.botao(area, "+", x2 + 0.075, z_linha, 0.09, 0.075, self._passo_volume, [chave, PASSO_VOLUME],
                     tipo="secundario", escala=0.04)
            rotulo = ui.texto(area, "", x2 + 0.24, z_linha - 0.03 * 0.36, 0.03, COR_TEXTO, CENTRO, negrito=True)
            self.volumes[chave] = (barra, cheio, rotulo, x1, x2)
            barra["command"] = self._arrastar_volume
            barra["extraArgs"] = [chave]
            self._mostrar_volume(chave)

        z_conta = linha(t("CONTA"))
        ui.botao(area, t("MINHA CONTA"), x_opcoes + 0.18, z_conta, 0.36, 0.075, self._abrir_minha_conta,
                 tipo="secundario", escala=0.026)

        opcoes(linha(t("IDIOMA")), [("pt", "PORTUGUÊS"), ("en", "ENGLISH")], i18n.idioma(), self._mudar_idioma)

        cotacao = f"R$ {numero(BRL_PER_USD)}"
        z_moeda = linha(t("MOEDA"), t("Automática: R$ em português e US$ em inglês (US$ 1 = {cotacao}).",
                                      cotacao=cotacao))
        opcoes(z_moeda, [("auto", t("AUTOMÁTICA")), ("BRL", "R$"), ("USD", "US$")], preferencias.obter("moeda"),
               self._mudar_moeda, largura=0.30)

        z_tela = linha(t("TELA"), t("Atalho: F11"))
        opcoes(z_tela, [(False, t("JANELA")), (True, t("TELA CHEIA"))], preferencias.obter("tela_cheia"),
               self._mudar_tela_cheia)

        volume(linha(t("EFEITOS SONOROS")), "volume_efeitos")
        volume(linha(t("MÚSICA")), "volume_musica")

        opcoes(linha(t("ANIMAÇÕES DA HOME")), [(True, t("LIGADAS")), (False, t("DESLIGADAS"))],
               preferencias.obter("animacoes"), self._mudar_animacoes)

        base = -self.ALTURA / 2
        ui.retangulo(area, x_rotulo, self.LARGURA / 2 - 0.08, base + 0.155, base + 0.158, COR_LINHA)
        ui.texto(area, t("Sons: Kenney (CC0)  ·  Música: Alex McCulloch (CC0)"), x_rotulo, base + 0.07, 0.021,
                 COR_TEXTO_3, ESQUERDA)
        ui.botao(area, t("FECHAR"), self.LARGURA / 2 - 0.30, base + 0.08, 0.40, 0.09, self.fechar,
                 tipo="secundario", escala=0.03)

    # ==================================================================
    # AÇÕES
    # ==================================================================

    def _abrir_minha_conta(self):
        tela = self.tela
        self.fechar()
        tela.abrir_minha_conta()

    def _mudar_idioma(self, codigo):
        if codigo != i18n.idioma():
            i18n.definir_idioma(codigo)
            self.tela.recriar_com_configuracoes()     # textos de toda a tela mudam

    def _mudar_moeda(self, moeda):
        if moeda != preferencias.obter("moeda"):
            preferencias.definir("moeda", moeda)
            self.tela.recriar_com_configuracoes()     # todos os valores da tela mudam

    def _mudar_tela_cheia(self, ligar):
        if ligar != preferencias.obter("tela_cheia"):
            preferencias.definir("tela_cheia", ligar)
            if hasattr(self.app, "aplicar_tela_cheia"):
                self.app.aplicar_tela_cheia(ligar)
            self._desenhar()

    # ---- volume (Extras 6: barra de arrastar, de 1 em 1%) -------------

    def _arrastar_volume(self, chave):
        """Chamado pela barra a cada movimento (várias vezes por segundo ao arrastar)."""
        barra = self.volumes[chave][0]
        valor = int(round(barra["value"]))
        if valor != preferencias.obter(chave):
            self._aplicar_volume(chave, valor)

    def _passo_volume(self, chave, passo):
        """Botões − e +: 1% para cada lado."""
        valor = max(0, min(100, preferencias.obter(chave) + passo))
        self.volumes[chave][0]["value"] = valor          # a bolinha vai junto
        self._aplicar_volume(chave, valor)

    def _aplicar_volume(self, chave, valor):
        """Muda o volume NA HORA; o arquivo só é gravado quando o jogador para de mexer."""
        preferencias.definir(chave, valor, salvar_agora=False)
        sons = getattr(self.app, "sons", None)
        if sons is not None:
            sons.aplicar_volumes()
        self._mostrar_volume(chave)
        tarefa = TASK_SALVAR_VOLUME + chave
        self.app.taskMgr.remove(tarefa)
        self.app.taskMgr.doMethodLater(ESPERA_SALVAR, self._salvar_volume, tarefa, extraArgs=[chave])

    def _salvar_volume(self, chave):
        preferencias.salvar()
        if chave == "volume_efeitos":
            tocar_som(self.app, "clique")                # para ouvir como ficou o volume novo

    def _mostrar_volume(self, chave):
        _barra, cheio, rotulo, x1, x2 = self.volumes[chave]
        valor = preferencias.obter(chave)
        rotulo.setText(t("Sem som") if valor == 0 else f"{valor}%")
        x_fim = x1 + (x2 - x1) * valor / 100
        cheio["frameSize"] = (x1, max(x_fim, x1 + 0.0001), *cheio["frameSize"][2:])

    def _salvar_volumes_pendentes(self):
        """Fechou a janela no meio da espera: grava já (sem o som de teste)."""
        pendente = False
        for chave in ("volume_efeitos", "volume_musica"):
            if self.app.taskMgr.hasTaskNamed(TASK_SALVAR_VOLUME + chave):
                self.app.taskMgr.remove(TASK_SALVAR_VOLUME + chave)
                pendente = True
        if pendente:
            preferencias.salvar()

    def _mudar_animacoes(self, ligar):
        if ligar != preferencias.obter("animacoes"):
            preferencias.definir("animacoes", ligar)
            if self.tela.ROTA == "home":
                self.tela.recriar_com_configuracoes()  # a Home liga/desliga o movimento ao ser montada
            else:
                self._desenhar()

    # ==================================================================

    @property
    def aberta(self):
        return self.janela is not None and self.janela.aberta

    def fechar(self):
        if self.janela is not None:
            self.janela.fechar()                       # chama _ao_fechar

    def _ao_fechar(self):
        self.eventos.ignoreAll()
        self._salvar_volumes_pendentes()
        self.janela = None
        if self.ao_fechar:
            self.ao_fechar()
