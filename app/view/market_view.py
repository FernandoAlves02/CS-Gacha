"""Tela do MERCADO (Fase 4): comprar caixas e skins avulsas, no estilo do CS2.

Layout (janela 16:9, unidades do aspect2d)
------------------------------------------
    header (menu, saldo, SAIR) ...................................... z 0,86 a 1
    MERCADO   CAIXAS  SKINS ............................................ z 0,72
    +------------- grade de cartões -------------+  +---- painel ----+
    | x de -1,70 a 0,40                          |  | x 0,48 a 1,70  |
    |                                            |  | detalhes,      |
    |                                            |  | gráfico e      |
    +--------------------------------------------+  | COMPRAR        |
                 ◀ 1 / 3 ▶                          +----------------+

Fluxo de compra (pedido na documentação)
----------------------------------------
1. o preço aparece em VERDE se o saldo dá, em VERMELHO se não dá (can_afford);
2. COMPRAR -> check_purchase: saldo e espaço no inventário (mensagem de erro se não);
3. janela "Deseja comprar ... por R$ X?";
4. buy_case / buy_skin: o DAO confere tudo de novo dentro da transação.
Depois da compra o saldo do header e as cores dos preços são atualizados.

Toda regra fica no Market_Controller; esta tela só desenha e repassa os cliques.
"""
from direct.showbase.DirectObject import DirectObject

from app.controller.market_controller import Market_Controller
from app.core.game_rules import (
    KEY_PRICE,
    NO_WEAR,
    display_value,
    format_display,
    format_money,
    price_change,
    rarity_label,
    rarity_short_label,
    wear_label,
    wear_label_full,
    wear_range,
)
from app.core.i18n import numero, t
from app.view.game_view_base import GameViewBase
from app.view.ui_kit import (
    BASE_TEXTO,
    CENTRO,
    COR_LARANJA,
    COR_LINHA,
    COR_PAINEL,
    COR_TEXTO,
    COR_TEXTO_2,
    COR_TEXTO_3,
    COR_VERDE,
    COR_VERMELHO,
    COR_VEU,
    DIREITA,
    Aviso,
    Janela,
    abrir_janela_conteudo,
    cor_variacao,
    formatar_chance,
    formatar_data,
    formatar_variacao,
    limpar_nome,
    nome_em_duas_linhas,
)

# ----------------------------------------------------------------------
# Medidas do layout
# ----------------------------------------------------------------------
GRADE_X1, GRADE_X2 = -1.70, 0.40          # área dos cartões
PAINEL_X1, PAINEL_X2 = 0.48, 1.70         # painel de detalhes
PAINEL_Z1, PAINEL_Z2 = -0.92, 0.62
PAINEL_CX = (PAINEL_X1 + PAINEL_X2) / 2
PAINEL_ESQ = PAINEL_X1 + 0.06             # margem interna do painel
PAINEL_DIR = PAINEL_X2 - 0.06

# Aba CAIXAS: 4 x 3 cartões (com todas as caixas da API são várias páginas)
CAIXAS_COLUNAS, CAIXAS_LINHAS = 4, 3
CAIXAS_TOPO, CAIXAS_BASE = 0.62, -0.80

# Aba SKINS: 6 x 4 cartões (24 = PAGE_SIZE do Market_Controller)
SKINS_COLUNAS, SKINS_LINHAS = 6, 4
SKINS_TOPO, SKINS_BASE = 0.445, -0.80
BUSCA_Z = 0.585                           # linha da caixa de busca
FILTROS_Z = 0.505                         # linha dos filtros de raridade

PAGINADOR_Z = -0.875
ESPACO = 0.035                            # espaço entre os cartões

ABAS = ("CAIXAS", "SKINS")                # chaves das abas (o texto na tela passa por t())

# Nomes curtos dos desgastes (como nos sites de skins; iguais nos dois idiomas)
SIGLAS_DESGASTE = {
    "Factory New": "FN", "Minimal Wear": "MW", "Field-Tested": "FT",
    "Well-Worn": "WW", "Battle-Scarred": "BS",
}

TASK_AVISO = "mercado_aviso"
TASK_BUSCA = "mercado_busca"
ATRASO_BUSCA = 0.4                        # busca enquanto digita, depois de uma pausa curta
LIMITE_HISTORICO = 500                    # pontos do gráfico (um fim de semana ~ 45)


class MarketView(GameViewBase):

    ROTA = "shop"

    # ==================================================================
    # CONSTRUÇÃO
    # ==================================================================

    def construir_conteudo(self):
        vm = self.view_manager
        self.app = vm.app
        self.controller = Market_Controller(
            vm.collection_dao, vm.skin_catalog_dao, vm.inventory_dao, self, vm.usuario_logado,
            rarity_dao=vm.rarity_dao,
        )

        # Véu escuro por cima do cenário 3D (fica fora da "raiz" para cobrir a
        # tela inteira mesmo quando a raiz é reduzida em janelas mais estreitas).
        self.veu = self.ui.retangulo(self.ui_root, -4, 4, -1.5, 0.86, COR_VEU)
        self.elementos.append(self.veu)

        self.raiz = self.ui.container(self.ui_root)
        self.elementos.append(self.raiz)
        self.ui.texto(self.raiz, t("MERCADO"), GRADE_X1, 0.70, 0.075, COR_TEXTO, negrito=True)

        self.area_abas = None
        self.area_filtros = None
        self.area_grade = None
        self.area_painel = None
        self.contorno_sel = None
        self.janela = None
        self.acao_enter = None            # o que o Enter confirma quando há janela aberta
        self.mudar_quantidade = None      # setas ↑ ↓ na janela de compra
        self.campo_busca = None
        self.sel_indice_anuncio = 0
        self.aviso = Aviso(self.ui, self.raiz, TASK_AVISO)

        # estado da tela
        self.aba = None
        self.caixas = self.controller.list_cases()
        self.pagina_caixas = 0
        self.raridades = self.controller.list_rarities()
        self.busca = ""
        self.raridade_id = None
        self.pagina_skins = 0
        self.total_paginas_skins = 1
        self.anuncios = []
        self.variacoes = {}
        self.cartoes = {}                 # índice do item na página -> cartão
        self.sel_caixa = None
        self.sel_anuncio = None           # (Skin_Catalog, Market_Price)

        # teclado e mouse
        self.eventos = DirectObject()
        self.eventos.accept("escape", self._tecla_esc)
        self.eventos.accept("enter", self._tecla_enter)
        self.eventos.accept("wheel_up", self._mudar_pagina_relativa, [-1])
        self.eventos.accept("wheel_down", self._mudar_pagina_relativa, [1])
        self.eventos.accept("arrow_left", self._mudar_pagina_relativa, [-1, True])
        self.eventos.accept("arrow_right", self._mudar_pagina_relativa, [1, True])
        self.eventos.accept("arrow_up", self._tecla_quantidade, [1])
        self.eventos.accept("arrow_down", self._tecla_quantidade, [-1])
        self.eventos.accept("aspectRatioChanged", self._ajustar_escala)
        self._ajustar_escala()

        self._trocar_aba("CAIXAS")

    def destruir(self):
        self.eventos.ignoreAll()
        self.app.taskMgr.remove(TASK_BUSCA)
        self.aviso.esconder()
        super().destruir()

    def _ajustar_escala(self):
        """Em janelas mais estreitas que 16:9 a tela inteira diminui para caber."""
        self.raiz.setScale(min(1.0, self.app.getAspectRatio() / (16 / 9)))

    # ==================================================================
    # CONTRATO COM O CONTROLLER
    # ==================================================================

    def show_message(self, message, success=True):
        self.aviso.mostrar(message, success)

    # ==================================================================
    # ABAS
    # ==================================================================

    def _trocar_aba(self, aba):
        if aba == self.aba:
            return
        self.aba = aba
        self.app.taskMgr.remove(TASK_BUSCA)
        self._recriar("area_abas")
        self.ui.abas(self.area_abas, -1.12, 0.71, ABAS, aba, self._trocar_aba)
        self._recriar("area_filtros")
        if aba == "CAIXAS":
            self._desenhar_caixas()
            if self.caixas and self.sel_caixa is None:
                self._selecionar_caixa(0)
            elif self.sel_caixa is not None:
                self._mostrar_painel_caixa()
        else:
            self._desenhar_filtros()
            self._carregar_skins()

    def _recriar(self, nome):
        """Destrói uma parte da tela (e tudo dentro dela) e cria um container vazio no lugar."""
        antigo = getattr(self, nome)
        if antigo is not None:
            antigo.destroy()
        novo = self.ui.container(self.raiz)
        setattr(self, nome, novo)
        if nome == "area_grade":
            self.contorno_sel = None
            self.cartoes = {}
        if nome == "area_filtros":
            self.campo_busca = None           # a caixa de busca antiga foi destruída junto
        return novo

    # ==================================================================
    # ABA CAIXAS
    # ==================================================================

    def _desenhar_caixas(self):
        grade = self._recriar("area_grade")
        if not self.caixas:
            self.ui.texto(grade, t("Nenhuma caixa à venda ainda."), (GRADE_X1 + GRADE_X2) / 2, 0.05, 0.04,
                          COR_TEXTO_2, CENTRO)
            self.ui.texto(grade, t("Rode o importador: python tools/sync_market.py"),
                          (GRADE_X1 + GRADE_X2) / 2, -0.03, 0.03, COR_TEXTO_3, CENTRO)
            self._mostrar_painel_vazio()
            return

        por_pagina = CAIXAS_COLUNAS * CAIXAS_LINHAS
        total = max(1, -(-len(self.caixas) // por_pagina))
        self.pagina_caixas = min(max(self.pagina_caixas, 0), total - 1)
        inicio = self.pagina_caixas * por_pagina
        largura, altura, posicoes = self._grade(CAIXAS_COLUNAS, CAIXAS_LINHAS, CAIXAS_TOPO, CAIXAS_BASE)

        for i, caixa in enumerate(self.caixas[inicio:inicio + por_pagina]):
            x, z = posicoes[i]
            cartao = self.ui.cartao(grade, x, z, largura, altura, self._selecionar_caixa, [inicio + i])
            self.cartoes[inicio + i] = cartao
            self.ui.imagem_do_item(cartao, caixa.api_id, 0, altura / 2 - 0.15, largura - 0.10, 0.25)
            self.ui.texto(cartao, limpar_nome(caixa.name), 0, -altura / 2 + 0.115, 0.031, COR_TEXTO, CENTRO,
                          negrito=True, largura_max=largura - 0.05)
            self.ui.texto(cartao, format_money(caixa.price), 0, -altura / 2 + 0.05, 0.036,
                          self._cor_preco(caixa.price), CENTRO, negrito=True)
            if caixa.price_is_estimated:
                self.ui.selo(cartao, t("ESTIMADO"), largura / 2 - 0.02, altura / 2 - 0.02, 0.022, cor=COR_TEXTO_2)

        if total > 1:
            self.ui.paginador(grade, (GRADE_X1 + GRADE_X2) / 2, PAGINADOR_Z, self.pagina_caixas, total,
                              self._ir_para_pagina)
        if self.sel_caixa is not None:
            self._marcar_selecionado(self.caixas.index(self.sel_caixa) if self.sel_caixa in self.caixas else None)

    def _selecionar_caixa(self, indice):
        if not 0 <= indice < len(self.caixas):
            return
        self.sel_caixa = self.caixas[indice]
        self._marcar_selecionado(indice)
        self._mostrar_painel_caixa()

    def _mostrar_painel_caixa(self):
        caixa = self.sel_caixa
        painel = self._novo_painel()
        ui = self.ui

        self._imagem_ampliavel(painel, caixa.api_id, 0.41, 0.70, 0.38, limpar_nome(caixa.name), None, None)
        ui.texto(painel, limpar_nome(caixa.name), PAINEL_ESQ, 0.175, 0.046, COR_TEXTO, negrito=True,
                 largura_max=PAINEL_DIR - PAINEL_ESQ)

        historico = self.controller.price_history(collection_id=caixa.id, limit=LIMITE_HISTORICO)
        self._bloco_preco(painel, caixa.price, caixa.price_is_estimated, caixa.price_updated_at, historico,
                          z=0.075)
        ui.botao(painel, t("COMPRAR"), PAINEL_DIR - 0.21, 0.095, 0.42, 0.095, self._comprar_caixa,
                 escala=0.036)

        ui.texto(painel, t("HISTÓRICO DE PREÇO"), PAINEL_ESQ, -0.035, 0.026, COR_TEXTO_2, negrito=True)
        ui.grafico(painel, historico, PAINEL_ESQ, PAINEL_DIR, -0.38, -0.06,
                   t("Ainda sem histórico: o coletor de preços (T2.6) cria esta linha."))

        # Resumo do conteúdo: chance de cada raridade (a soma dá 100%)
        tabela = self.controller.case_contents(caixa.id)
        grupos = {}
        for skin, chance in tabela:
            nome, cor, total, qtd = grupos.get(skin.rarity_id, (skin.rarity.name, skin.rarity.color_rgba, 0, 0))
            grupos[skin.rarity_id] = (nome, cor, total + chance, qtd + 1)
        ui.texto(painel, t("CONTEÚDO  ·  {n} itens", n=len(tabela)), PAINEL_ESQ, -0.45, 0.026, COR_TEXTO_2,
                 negrito=True)
        z = -0.51
        for rarity_id in sorted(grupos):
            nome, cor, chance, qtd = grupos[rarity_id]
            ui.retangulo(painel, PAINEL_ESQ, PAINEL_ESQ + 0.012, z - 0.008, z + 0.028, cor)
            ui.texto(painel, rarity_label(nome), PAINEL_ESQ + 0.03, z, 0.028, COR_TEXTO)
            itens = t("{n} item", n=qtd) if qtd == 1 else t("{n} itens", n=qtd)
            ui.texto(painel, itens, PAINEL_CX + 0.12, z, 0.026,
                     COR_TEXTO_2, DIREITA)
            ui.texto(painel, formatar_chance(chance), PAINEL_DIR, z, 0.028, cor, DIREITA, negrito=True)
            z -= 0.055
        if tabela:
            total = sum(chance for _skin, chance in tabela)
            ui.retangulo(painel, PAINEL_ESQ, PAINEL_DIR, z + 0.035, z + 0.038, COR_LINHA)
            ui.texto(painel, t("Total"), PAINEL_ESQ + 0.03, z - 0.005, 0.026, COR_TEXTO_2)
            ui.texto(painel, formatar_chance(total), PAINEL_DIR, z - 0.005, 0.026, COR_TEXTO_2, DIREITA)
            ui.botao(painel, t("VER TODOS OS ITENS"), PAINEL_CX, -0.86, 0.62, 0.075, self._abrir_conteudo,
                     [caixa, tabela], tipo="secundario", escala=0.028)

    def _comprar_caixa(self):
        caixa = self.sel_caixa
        if caixa is None:
            return
        motivo = self.controller.check_purchase(caixa.price)
        if motivo:
            self.show_message(self._com_dica_gratis(motivo), False)
            return
        self._janela_compra(
            limpar_nome(caixa.name), None, caixa.api_id, caixa.price,
            t("Para abrir, cada caixa precisa de uma chave de {preco} (cobrada na abertura).",
              preco=format_money(KEY_PRICE)),
            lambda quantidade: self._efetuar_compra_caixa(caixa, quantidade),
        )

    def _efetuar_compra_caixa(self, caixa, quantidade=1):
        self._fechar_janela()
        if self.controller.buy_case(caixa, quantidade):
            self.atualizar_saldo()
        else:
            # o preço pode ter mudado (coletor rodando): recarrega a lista
            self.caixas = self.controller.list_cases()
            self.sel_caixa = next((c for c in self.caixas if c.id == caixa.id), None)
        self._desenhar_caixas()
        if self.sel_caixa is not None:
            self._mostrar_painel_caixa()
        else:
            self._mostrar_painel_vazio()

    def _abrir_conteudo(self, caixa, tabela):
        """Janela com todos os itens da caixa e a chance de cada um."""
        self._abrir_janela_pronta(lambda: abrir_janela_conteudo(self.ui, self.raiz, caixa.name, tabela,
                                                                self._fechar_janela))

    # ==================================================================
    # ABA SKINS
    # ==================================================================

    def _desenhar_filtros(self):
        filtros = self.area_filtros
        ui = self.ui
        self.campo_busca, atualizar_exemplo = ui.campo_texto(
            filtros, GRADE_X1, BUSCA_Z, 0.90, 0.075, t("Buscar skin (ex.: AK-47 Redline)"),
            self._ao_digitar_busca, self._ao_confirmar_busca,
        )
        if self.busca:
            self.campo_busca.enterText(self.busca)
        atualizar_exemplo()

        # Filtros de raridade numa linha própria (são até 9 com as coleções de mapa)
        opcoes = [(t("Todas"), None)] + [(rarity_short_label(r.name), r.id) for r in self.raridades]
        escala, espaco = 0.024, 0.012
        larguras = [ui.largura_texto(rotulo, escala, True) + 0.045 for rotulo, _id in opcoes]
        # se não couber na largura da grade, aperta o espaço interno dos botões
        sobra = (GRADE_X2 - GRADE_X1) - sum(larguras) - espaco * (len(opcoes) - 1)
        if sobra < 0:
            larguras = [l + sobra / len(larguras) for l in larguras]
        x = GRADE_X1
        for (rotulo, rarity_id), largura in zip(opcoes, larguras):
            ativo = rarity_id == self.raridade_id
            ui.botao(filtros, rotulo, x + largura / 2, FILTROS_Z, largura, 0.06, self._filtrar_raridade,
                     [rarity_id], tipo="primario" if ativo else "secundario", escala=escala)
            x += largura + espaco

    def _ao_digitar_busca(self):
        # espera uma pausa na digitação antes de consultar o banco
        self.app.taskMgr.remove(TASK_BUSCA)
        self.app.taskMgr.doMethodLater(ATRASO_BUSCA, self._aplicar_busca_tarefa, TASK_BUSCA)

    def _aplicar_busca_tarefa(self, task):
        if self.janela is not None and self.janela.aberta:
            return task.done                    # não redesenha a tela por baixo de uma janela
        self._aplicar_busca(self.campo_busca.get())
        return task.done

    def _ao_confirmar_busca(self, texto):
        self.app.taskMgr.remove(TASK_BUSCA)
        self._aplicar_busca(texto)

    def _aplicar_busca(self, texto):
        texto = (texto or "").strip()
        if texto == self.busca:
            return
        self.busca = texto
        self.pagina_skins = 0
        self._carregar_skins()

    def _filtrar_raridade(self, rarity_id):
        if rarity_id == self.raridade_id:
            return
        self.app.taskMgr.remove(TASK_BUSCA)
        self.busca = self.campo_busca.get().strip()     # vale o que está digitado na caixa
        self.raridade_id = rarity_id
        self.pagina_skins = 0
        self._recriar("area_filtros")                   # redesenha os botões (o ativo fica laranja)
        self._desenhar_filtros()
        self._carregar_skins()

    def _carregar_skins(self):
        """Consulta a página atual no banco (anúncios + variação ▲▼) e redesenha."""
        self.anuncios, self.total_paginas_skins = self.controller.list_skins(
            self.busca, self.pagina_skins, self.raridade_id
        )
        self.variacoes = self.controller.price_changes(self.anuncios)
        self._desenhar_skins()
        if self.anuncios:
            self._selecionar_anuncio(0)
        else:
            self.sel_anuncio = None
            self._mostrar_painel_vazio()

    def _desenhar_skins(self):
        grade = self._recriar("area_grade")
        ui = self.ui
        if not self.anuncios:
            if self.busca:
                msg = t("Nenhuma skin encontrada para “{busca}”.", busca=self.busca)
            else:
                msg = t("Nenhuma skin à venda.")
            ui.texto(grade, msg, (GRADE_X1 + GRADE_X2) / 2, 0.05, 0.036, COR_TEXTO_2, CENTRO)
            return

        largura, altura, posicoes = self._grade(SKINS_COLUNAS, SKINS_LINHAS, SKINS_TOPO, SKINS_BASE)
        esq = -largura / 2 + 0.022
        dir_ = largura / 2 - 0.022
        for i, (skin, preco) in enumerate(self.anuncios[:len(posicoes)]):
            x, z = posicoes[i]
            cor = skin.rarity.color_rgba
            cartao = ui.cartao(grade, x, z, largura, altura, self._selecionar_anuncio, [i], cor_raridade=cor)
            self.cartoes[i] = cartao
            ui.imagem_do_item(cartao, skin.api_id, 0, altura / 2 - 0.078, largura - 0.05, 0.14)
            arma, padrao = nome_em_duas_linhas(skin.name)
            ui.texto(cartao, arma, esq, -0.012, 0.023, COR_TEXTO_2, largura_max=largura - 0.044)
            ui.texto(cartao, padrao or "Vanilla", esq, -0.048, 0.027, COR_TEXTO, largura_max=largura - 0.044)
            ui.texto(cartao, wear_label(preco.wear), esq, -0.083, 0.021, COR_TEXTO_3,
                     largura_max=largura - 0.044)
            ui.texto(cartao, format_money(preco.price), esq, -altura / 2 + 0.03, 0.028,
                     self._cor_preco(preco.price), negrito=True)
            variacao = self.variacoes.get((skin.id, preco.wear))
            if variacao is not None:
                ui.texto(cartao, formatar_variacao(variacao[0]), dir_, -altura / 2 + 0.03, 0.021,
                         cor_variacao(variacao[0]), DIREITA)
            elif preco.is_estimated:
                ui.texto(cartao, t("estimado"), dir_, -altura / 2 + 0.03, 0.019, COR_TEXTO_3, DIREITA)

        ui.texto(grade, t("Página com {n} anúncios  ·  cada desgaste é um anúncio, como no mercado da Steam",
                          n=len(self.anuncios)), GRADE_X1, PAGINADOR_Z - 0.012, 0.022, COR_TEXTO_3)
        if self.total_paginas_skins > 1:
            ui.paginador(grade, GRADE_X2 - 0.25, PAGINADOR_Z, self.pagina_skins, self.total_paginas_skins,
                         self._ir_para_pagina)

    def _selecionar_anuncio(self, indice, preco_escolhido=None):
        if not 0 <= indice < len(self.anuncios):
            return
        skin, preco = self.anuncios[indice]
        self.sel_anuncio = (skin, preco_escolhido or preco)
        self.sel_indice_anuncio = indice
        self._marcar_selecionado(indice)
        self._mostrar_painel_skin()

    def _mostrar_painel_skin(self):
        skin, preco = self.sel_anuncio
        painel = self._novo_painel()
        ui = self.ui
        cor = skin.rarity.color_rgba

        ui.gradiente(painel, PAINEL_X1, PAINEL_X2, 0.20, 0.62, cor[:3] + (0.0,), cor[:3] + (0.16,))
        self._imagem_ampliavel(painel, skin.api_id, 0.43, 0.86, 0.36, limpar_nome(skin.name),
                               wear_label(preco.wear), cor)
        arma, padrao = nome_em_duas_linhas(skin.name)
        ui.texto(painel, arma, PAINEL_ESQ, 0.215, 0.03, COR_TEXTO_2, largura_max=PAINEL_DIR - PAINEL_ESQ)
        ui.texto(painel, padrao or "Vanilla", PAINEL_ESQ, 0.16, 0.046, COR_TEXTO, negrito=True,
                 largura_max=PAINEL_DIR - PAINEL_ESQ)
        ui.texto(painel, rarity_label(skin.rarity.name), PAINEL_ESQ, 0.115, 0.026, cor, negrito=True)

        # Um botão por desgaste à venda (troca o anúncio mostrado)
        precos = self.controller.skin_prices(skin.id) or [preco]
        x = PAINEL_ESQ
        for opcao in precos:
            sigla = SIGLAS_DESGASTE.get(opcao.wear) or (t("SEM PINTURA") if opcao.wear == NO_WEAR else opcao.wear)
            largura = max(ui.largura_texto(sigla, 0.026, True) + 0.07, 0.16)
            ativo = opcao.wear == preco.wear
            ui.botao(painel, sigla, x + largura / 2, 0.045, largura, 0.065, self._escolher_desgaste, [opcao],
                     tipo="primario" if ativo else "secundario", escala=0.026)
            x += largura + 0.015

        historico = self.controller.price_history(skin.id, preco.wear, limit=LIMITE_HISTORICO)
        self._bloco_preco(painel, preco.price, preco.is_estimated, preco.updated_at, historico, z=-0.075)
        ui.botao(painel, t("COMPRAR"), PAINEL_DIR - 0.21, -0.055, 0.42, 0.095, self._comprar_skin, escala=0.036)

        if preco.wear == NO_WEAR:
            faixa = t("Item sem desgaste (float 0)")
        else:
            inicio, fim = wear_range(preco.wear)
            inicio, fim = max(inicio, skin.min_float), min(fim, skin.max_float)
            faixa = t("{desgaste}  ·  float de {inicio} a {fim}", desgaste=wear_label_full(preco.wear),
                      inicio=numero(inicio), fim=numero(fim))
        ui.texto(painel, faixa, PAINEL_ESQ, -0.17, 0.024, COR_TEXTO_2, largura_max=PAINEL_DIR - PAINEL_ESQ)

        ui.texto(painel, t("HISTÓRICO DE PREÇO"), PAINEL_ESQ, -0.255, 0.026, COR_TEXTO_2, negrito=True)
        ui.grafico(painel, historico, PAINEL_ESQ, PAINEL_DIR, -0.62, -0.28,
                   t("Ainda sem histórico: o coletor de preços (T2.6) cria esta linha."))
        ui.texto(painel, t("Ao comprar, o float é sorteado dentro da faixa do desgaste escolhido."),
                 PAINEL_ESQ, -0.70, 0.024, COR_TEXTO_3, quebra_em=PAINEL_DIR - PAINEL_ESQ)

    def _escolher_desgaste(self, preco):
        skin, _atual = self.sel_anuncio
        self.sel_anuncio = (skin, preco)
        self._mostrar_painel_skin()

    def _comprar_skin(self):
        if self.sel_anuncio is None:
            return
        skin, preco = self.sel_anuncio
        motivo = self.controller.check_purchase(preco.price)
        if motivo:
            self.show_message(self._com_dica_gratis(motivo), False)
            return
        self._janela_compra(
            limpar_nome(skin.name), wear_label(preco.wear), skin.api_id, preco.price,
            t("Cada unidade recebe o seu float, sorteado dentro da faixa desse desgaste."),
            lambda quantidade: self._efetuar_compra_skin(skin, preco, quantidade),
        )

    def _efetuar_compra_skin(self, skin, preco, quantidade=1):
        self._fechar_janela()
        compradas = self.controller.buy_skins(skin, preco, quantidade)
        if compradas:
            self.atualizar_saldo()
            # mensagem mais completa que a do controller: mostra o(s) float(s) sorteado(s)
            floats = sorted(c.float_value for c in compradas)
            if len(floats) == 1:
                detalhe = t("Float {valor}", valor=numero(floats[0], 4))
            else:
                detalhe = t("{n} unidades, floats de {menor} a {maior}", n=len(floats),
                            menor=numero(floats[0], 4), maior=numero(floats[-1], 4))
            self.show_message(t("{nome} comprada! {detalhe}  ·  Saldo: {saldo}", nome=limpar_nome(skin.name),
                                detalhe=detalhe, saldo=format_money(self.view_manager.usuario_logado.balance)))
            self._desenhar_skins()
            self._selecionar_anuncio(self.sel_indice_anuncio, preco)
        else:
            self._carregar_skins()           # preço pode ter mudado: recarrega a página

    # ==================================================================
    # PAINEL DE DETALHES (comum às duas abas)
    # ==================================================================

    def _novo_painel(self):
        painel = self._recriar("area_painel")
        self.ui.retangulo(painel, PAINEL_X1, PAINEL_X2, PAINEL_Z1, PAINEL_Z2, COR_PAINEL)
        return painel

    def _imagem_ampliavel(self, painel, api_id, z, largura, altura, nome, detalhe, cor):
        """Imagem do painel; clicar nela abre a imagem grande (ou ENTER/ESC/clique fecham)."""
        ui = self.ui
        ui.imagem_do_item(painel, api_id, PAINEL_CX, z, largura, altura)
        botao = ui.botao_texto(painel, "", PAINEL_CX, z, 0.03, self._ampliar, [api_id, nome, detalhe, cor])
        botao["frameSize"] = (-largura / 2, largura / 2, -altura / 2, altura / 2)
        ui.texto(painel, t("clique para ampliar"), PAINEL_DIR, z - altura / 2 + 0.01, 0.021, COR_TEXTO_3, DIREITA)

    def _ampliar(self, api_id, nome, detalhe, cor):
        ui = self.ui
        janela = self._abrir_janela(3.0, 1.70, nome)
        p = janela.painel
        if cor is not None:
            ui.gradiente(p, -1.5, 1.5, -0.85, -0.05, cor[:3] + (0.28,), cor[:3] + (0.0,))
            ui.retangulo(p, -1.5, 1.5, -0.85, -0.838, cor)
        # as imagens da Steam têm 256 px: até ~1,4x maior ainda fica nítido
        ui.imagem_do_item(p, api_id, 0, -0.03, 2.0, 1.05)
        if detalhe:
            ui.texto(p, detalhe, 1.44, 0.735, 0.03, COR_TEXTO_2, DIREITA)
        fechar = ui.botao_texto(p, "", 0, 0, 0.03, self._fechar_janela)      # clicar em qualquer lugar fecha
        fechar["frameSize"] = (-1.5, 1.5, -0.85, 0.85)
        ui.texto(p, t("clique, ENTER ou ESC para fechar"), 0, -0.80, 0.022, COR_TEXTO_3, CENTRO)
        self.acao_enter = (self._fechar_janela, [])

    def _mostrar_painel_vazio(self):
        painel = self._novo_painel()
        self.ui.texto(painel, t("Selecione um item para ver os detalhes."), PAINEL_CX, 0, 0.03, COR_TEXTO_3,
                      CENTRO)

    def _bloco_preco(self, painel, preco, estimado, atualizado_em, historico, z):
        """Preço grande (verde/vermelho), variação no período e de onde veio o preço."""
        ui = self.ui
        ui.texto(painel, format_money(preco), PAINEL_ESQ, z - 0.02, 0.06, self._cor_preco(preco), negrito=True)
        if estimado:
            origem = t("Preço estimado (sem anúncio na Steam no momento)")
        else:
            origem = t("Mercado da Steam  ·  atualizado em {data}", data=formatar_data(atualizado_em))
        variacao = price_change(historico)
        largura_preco = ui.largura_texto(format_money(preco), 0.06, True)
        if variacao is not None:
            ui.texto(painel, t("{variacao} em {horas} h", variacao=formatar_variacao(variacao[0]), horas=variacao[1]),
                     PAINEL_ESQ + largura_preco + 0.03,
                     z - 0.012, 0.026, cor_variacao(variacao[0]), negrito=True)
        ui.texto(painel, origem, PAINEL_ESQ, z - 0.065, 0.022, COR_TEXTO_3, largura_max=0.62)

    # ==================================================================
    # AJUDANTES
    # ==================================================================

    def _com_dica_gratis(self, motivo):
        """Sem saldo nem para a chave: lembra que a CAIXA GRÁTIS está no inventário."""
        if motivo == t("Saldo insuficiente.") and self.view_manager.usuario_logado.balance < KEY_PRICE:
            return t("Saldo insuficiente. Sem dinheiro? Abra a CAIXA GRÁTIS no INVENTÁRIO.")
        return motivo

    def _cor_preco(self, preco):
        return COR_VERDE if self.controller.can_afford(preco) else COR_VERMELHO

    @staticmethod
    def _grade(colunas, linhas, topo, base):
        """Tamanho dos cartões e a posição (centro) de cada um, preenchendo a área da grade."""
        largura = (GRADE_X2 - GRADE_X1 - (colunas - 1) * ESPACO) / colunas
        altura = (topo - base - (linhas - 1) * ESPACO) / linhas
        posicoes = []
        for linha in range(linhas):
            for coluna in range(colunas):
                x = GRADE_X1 + largura / 2 + coluna * (largura + ESPACO)
                z = topo - altura / 2 - linha * (altura + ESPACO)
                posicoes.append((x, z))
        return largura, altura, posicoes

    def _marcar_selecionado(self, indice):
        """Borda laranja em volta do cartão escolhido."""
        if self.contorno_sel is not None:
            self.contorno_sel.destroy()
            self.contorno_sel = None
        cartao = self.cartoes.get(indice)
        if cartao is None:
            return
        x1, x2, z1, z2 = cartao["frameSize"]
        self.contorno_sel = self.ui.contorno(cartao, x1, x2, z1, z2, COR_LARANJA, 0.007)

    def _ir_para_pagina(self, pagina):
        if self.aba == "CAIXAS":
            self.pagina_caixas = pagina
            self._desenhar_caixas()
        elif 0 <= pagina < self.total_paginas_skins:
            self.pagina_skins = pagina
            self._carregar_skins()

    def _mudar_pagina_relativa(self, passo, so_sem_digitar=False):
        if (self.janela is not None and self.janela.aberta) or self.modal_do_header_aberto():
            return
        if so_sem_digitar and self.campo_busca is not None and self.campo_busca.guiItem.getFocus():
            return                         # setas movem o cursor do texto, não a página
        if self.aba == "CAIXAS":
            total = max(1, -(-len(self.caixas) // (CAIXAS_COLUNAS * CAIXAS_LINHAS)))
            if 0 <= self.pagina_caixas + passo < total:
                self._ir_para_pagina(self.pagina_caixas + passo)
        else:
            if 0 <= self.pagina_skins + passo < self.total_paginas_skins:
                self._ir_para_pagina(self.pagina_skins + passo)

    # ==================================================================
    # JANELAS (confirmação e conteúdo)
    # ==================================================================

    def _abrir_janela(self, largura, altura, titulo):
        return self._abrir_janela_pronta(lambda: Janela(self.ui, self.raiz, largura, altura, titulo))

    def _abrir_janela_pronta(self, criar):
        """Fecha a janela anterior, tira o foco da busca e abre a nova."""
        self._fechar_janela()
        self.app.taskMgr.remove(TASK_BUSCA)     # busca pendente não roda com a janela aberta
        if self.campo_busca is not None:
            self.campo_busca["focus"] = 0       # Enter/Esc vão para a janela, não para a busca
        self.janela = criar()
        return self.janela

    def _fechar_janela(self):
        if self.janela is not None:
            self.janela.fechar()
            self.janela = None
        self.acao_enter = None
        self.mudar_quantidade = None

    def _tecla_quantidade(self, passo):
        if self.janela is not None and self.janela.aberta and self.mudar_quantidade:
            self.mudar_quantidade(passo)

    def _janela_compra(self, nome, detalhe, api_id, preco, nota, efetuar):
        """Janela "Deseja comprar...?" com QUANTIDADE (− / + / MÁX), total e confirmação.

        efetuar(quantidade) faz a compra. O máximo respeita o saldo, o espaço
        livre no inventário e o limite por compra (MAX_PER_PURCHASE).
        Setas ↑ ↓ do teclado também mudam a quantidade; ENTER confirma; ESC cancela.
        """
        ui = self.ui
        maximo = self.controller.max_quantity(preco)
        janela = self._abrir_janela(1.76, 0.98, t("CONFIRMAR COMPRA"))
        p = janela.painel
        ui.imagem_do_item(p, api_id, -0.60, 0.04, 0.40, 0.34)
        x, direita = -0.34, 0.80
        ui.texto(p, nome, x, 0.24, 0.036, COR_TEXTO, negrito=True, largura_max=direita - x)
        if detalhe:
            ui.texto(p, detalhe, x, 0.185, 0.026, COR_TEXTO_2)
        ui.texto(p, t("Preço unitário"), x, 0.115, 0.027, COR_TEXTO_2)
        ui.texto(p, format_money(preco), direita, 0.115, 0.027, COR_TEXTO, DIREITA)
        ui.texto(p, t("QUANTIDADE"), x, 0.035, 0.024, COR_TEXTO_3, negrito=True)
        ui.texto(p, nota, x, -0.30, 0.022, COR_TEXTO_3, quebra_em=direita - x)
        estado = {"quantidade": 1, "area": None}

        def desenhar():
            if estado["area"] is not None:
                estado["area"].destroy()
            estado["area"] = area = ui.container(p)
            qtd = estado["quantidade"]
            z = -0.035
            ui.botao(area, "−", x + 0.045, z, 0.09, 0.07, mudar, [-1], tipo="secundario", escala=0.04, ativo=qtd > 1)
            ui.texto(area, str(qtd), x + 0.165, z - 0.04 * BASE_TEXTO, 0.04, COR_TEXTO, CENTRO, negrito=True)
            ui.botao(area, "+", x + 0.285, z, 0.09, 0.07, mudar, [1], tipo="secundario", escala=0.04,
                     ativo=qtd < maximo)
            ui.botao(area, t("MÁX ({n})", n=maximo), x + 0.48, z, 0.24, 0.07, definir, [maximo], tipo="secundario",
                     escala=0.024, ativo=qtd < maximo)
            total = preco * qtd
            ui.retangulo(area, x, direita, -0.105, -0.101, COR_LINHA)
            ui.texto(area, t("Total"), x, -0.18, 0.032, COR_TEXTO, negrito=True)
            # total = preço da unidade (como aparece na tela) x quantidade: a conta fecha também em dólar
            ui.texto(area, format_display(display_value(preco) * qtd), direita, -0.18, 0.044, self._cor_preco(total),
                     DIREITA, negrito=True)
            texto_ok = t("COMPRAR {n}x", n=qtd) if qtd > 1 else t("COMPRAR")
            ui.botao(area, t("CANCELAR"), 0.16, -0.40, 0.40, 0.09, self._fechar_janela, tipo="secundario", escala=0.03)
            ui.botao(area, texto_ok, 0.60, -0.40, 0.40, 0.09, efetuar, [qtd], escala=0.03)
            self.acao_enter = (efetuar, [qtd])

        def definir(quantidade):
            estado["quantidade"] = max(1, min(maximo, quantidade))
            desenhar()

        def mudar(passo):
            definir(estado["quantidade"] + passo)

        self.mudar_quantidade = mudar
        desenhar()

    def _tecla_esc(self):
        if self.modal_do_header_aberto():
            return                                  # o ESC é do pop-up "Minha conta"
        if self.janela is not None and self.janela.aberta:
            self._fechar_janela()

    def _tecla_enter(self):
        if self.modal_do_header_aberto():
            return                                  # o ENTER salva o "Minha conta"
        if self.janela is not None and self.janela.aberta and self.acao_enter:
            funcao, extra = self.acao_enter
            funcao(*extra)
