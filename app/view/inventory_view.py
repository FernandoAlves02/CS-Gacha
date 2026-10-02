"""Tela do INVENTÁRIO (Fase 5): itens do jogador, detalhes, venda e abertura de caixa.

O que a documentação pede e onde está aqui
------------------------------------------
- mostrar só os itens do jogador ................ Inventory_Controller.load()
- clicar numa skin dá um "pequeno aumento" e aparece o botão de detalhes
                                                  ... _selecionar() + menu ao lado do cartão
- pop-up de detalhes com nome, float e estado ... _abrir_detalhes(), com botão FECHAR
- venda mostrando o valor final + confirmação ... _vender() -> sale_quote() -> janela -> sell_skin()
- abrir caixa com animação; resultado vem pronto do backend
                                                  ... case_opening.AberturaDeCaixa
- contador "37 / 1000" (limite do inventário do CS)

Layout (16:9): título + filtros TUDO / CAIXAS / SKINS em cima, grade de 7 x 3
cartões, paginação embaixo.
"""
from direct.showbase.DirectObject import DirectObject

from app.controller.inventory_controller import Inventory_Controller
from app.core.game_rules import SELL_FEE_RATE, format_money
from app.view.case_opening import AberturaDeCaixa
from app.view.game_view_base import GameViewBase
from app.view.ui_kit import (
    CENTRO,
    COR_LARANJA,
    COR_OURO,
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
    limpar_nome,
    nome_em_duas_linhas,
)

# Filtros (o resto das categorias antigas era do escopo cortado, D6)
FILTROS = ("TUDO", "CAIXAS", "SKINS")

# Grade: 7 colunas x 3 linhas
GRADE_X1, GRADE_X2 = -1.70, 1.70
GRADE_TOPO, GRADE_BASE = 0.60, -0.78
COLUNAS, LINHAS = 7, 3
POR_PAGINA = COLUNAS * LINHAS
ESPACO = 0.035
PAGINADOR_Z = -0.875

AUMENTO_SELECIONADO = 1.06          # "pequeno aumento" do item clicado
MENU_LARGURA, MENU_ALTURA = 0.46, 0.075

COR_CAIXA = (0.62, 0.64, 0.68, 1)   # caixas não têm raridade: faixa cinza

TASK_AVISO = "inventario_aviso"


class InventoryView(GameViewBase):

    ROTA = "inventory"

    # ==================================================================
    # CONSTRUÇÃO
    # ==================================================================

    def construir_conteudo(self):
        vm = self.view_manager
        self.app = vm.app
        self.controller = Inventory_Controller(
            vm.inventory_dao, vm.collection_dao, vm.rarity_dao, self, vm.usuario_logado
        )

        self.veu = self.ui.retangulo(self.ui_root, -4, 4, -1.5, 0.86, COR_VEU)
        self.elementos.append(self.veu)
        self.raiz = self.ui.container(self.ui_root)
        self.elementos.append(self.raiz)
        self.ui.texto(self.raiz, "INVENTÁRIO", GRADE_X1, 0.70, 0.075, COR_TEXTO, negrito=True)

        self.area_topo = None
        self.area_grade = None
        self.area_menu = None
        self.janela = None
        self.abertura = None
        self.acao_enter = None
        self.aviso = Aviso(self.ui, self.raiz, TASK_AVISO)

        self.filtro = "TUDO"
        self.pagina = 0
        self.itens = []                  # [("caixa", Collection) | ("skin", Skin_Instance)]
        self.cartoes = {}                # índice na lista -> cartão
        self.selecionado = None          # índice do item selecionado

        self.eventos = DirectObject()
        self.eventos.accept("escape", self._tecla_esc)
        self.eventos.accept("enter", self._tecla_enter)
        self.eventos.accept("space", self._tecla_espaco)
        self.eventos.accept("wheel_up", self._mudar_pagina_relativa, [-1])
        self.eventos.accept("wheel_down", self._mudar_pagina_relativa, [1])
        self.eventos.accept("arrow_left", self._mudar_pagina_relativa, [-1])
        self.eventos.accept("arrow_right", self._mudar_pagina_relativa, [1])
        self.eventos.accept("aspectRatioChanged", self._ajustar_escala)
        self._ajustar_escala()

        self._carregar()

    def destruir(self):
        self.eventos.ignoreAll()
        if self.abertura is not None:
            self.abertura.destruir()
            self.abertura = None
        self.aviso.esconder()
        super().destruir()

    def _ajustar_escala(self):
        self.raiz.setScale(min(1.0, self.app.getAspectRatio() / (16 / 9)))

    # ==================================================================
    # CONTRATO COM O CONTROLLER
    # ==================================================================

    def show_message(self, message, success=True):
        self.aviso.mostrar(message, success)

    # ==================================================================
    # CARREGAR E DESENHAR
    # ==================================================================

    def _carregar(self):
        """Busca os itens do jogador no banco e redesenha a tela."""
        caixas, skins = self.controller.load()
        self.todos = [("caixa", c) for c in caixas] + [("skin", s) for s in skins]
        self.usados, self.limite = self.controller.status()
        self._aplicar_filtro()

    def _aplicar_filtro(self):
        if self.filtro == "CAIXAS":
            self.itens = [item for item in self.todos if item[0] == "caixa"]
        elif self.filtro == "SKINS":
            self.itens = [item for item in self.todos if item[0] == "skin"]
        else:
            self.itens = list(self.todos)
        total = self._total_paginas()
        self.pagina = min(max(self.pagina, 0), total - 1)
        self.selecionado = None
        self._desenhar_topo()
        self._desenhar_grade()

    def _desenhar_topo(self):
        topo = self._recriar("area_topo")
        self.ui.abas(topo, -1.07, 0.71, FILTROS, self.filtro, self._trocar_filtro)
        cor = COR_VERMELHO if self.usados >= self.limite else COR_TEXTO
        contador = f"{self.usados} / {self.limite:,}".replace(",", ".")
        self.ui.texto(topo, contador, GRADE_X2, 0.71, 0.045, cor, DIREITA, negrito=True)
        self.ui.texto(topo, "ITENS NO INVENTÁRIO", GRADE_X2, 0.655, 0.022, COR_TEXTO_3, DIREITA, negrito=True)

    def _desenhar_grade(self):
        grade = self._recriar("area_grade")
        self._fechar_menu()
        ui = self.ui
        if not self.itens:
            vazio = {"CAIXAS": "Você não tem caixas.", "SKINS": "Você ainda não tem skins."}
            ui.texto(grade, vazio.get(self.filtro, "Seu inventário está vazio."), 0, 0.08, 0.042,
                     COR_TEXTO_2, CENTRO)
            ui.texto(grade, "Compre caixas e skins no MERCADO.", 0, 0.0, 0.03, COR_TEXTO_3, CENTRO)
            ui.botao(grade, "IR AO MERCADO", 0, -0.13, 0.46, 0.09,
                     self.view_manager.mudar_tela_base, ["shop"], escala=0.032)
            return

        largura = (GRADE_X2 - GRADE_X1 - (COLUNAS - 1) * ESPACO) / COLUNAS
        altura = (GRADE_TOPO - GRADE_BASE - (LINHAS - 1) * ESPACO) / LINHAS
        self.tamanho_cartao = (largura, altura)
        inicio = self.pagina * POR_PAGINA
        for n, (tipo, item) in enumerate(self.itens[inicio:inicio + POR_PAGINA]):
            x = GRADE_X1 + largura / 2 + (n % COLUNAS) * (largura + ESPACO)
            z = GRADE_TOPO - altura / 2 - (n // COLUNAS) * (altura + ESPACO)
            indice = inicio + n
            if tipo == "caixa":
                cartao = self._cartao_caixa(grade, x, z, largura, altura, item, indice)
            else:
                cartao = self._cartao_skin(grade, x, z, largura, altura, item, indice)
            self.cartoes[indice] = cartao

        total = self._total_paginas()
        if total > 1:
            ui.paginador(grade, 0, PAGINADOR_Z, self.pagina, total, self._ir_para_pagina)

    def _cartao_caixa(self, pai, x, z, largura, altura, caixa, indice):
        ui = self.ui
        cartao = ui.cartao(pai, x, z, largura, altura, self._selecionar, [indice], cor_raridade=COR_CAIXA)
        ui.imagem_do_item(cartao, caixa.api_id, 0, altura / 2 - 0.14, largura - 0.08, 0.25)
        ui.texto(cartao, "Caixa", -largura / 2 + 0.03, -0.085, 0.024, COR_TEXTO_2)
        ui.texto(cartao, limpar_nome(caixa.name), -largura / 2 + 0.03, -0.13, 0.031, COR_TEXTO,
                 largura_max=largura - 0.06)
        if (caixa.quantity or 0) > 1:
            ui.selo(cartao, f"x{caixa.quantity}", largura / 2 - 0.015, altura / 2 - 0.015, 0.028)
        return cartao

    def _cartao_skin(self, pai, x, z, largura, altura, skin_instancia, indice):
        ui = self.ui
        skin = skin_instancia.skin
        especial = skin.rarity.name == "Special Item"
        cor = COR_OURO if especial else skin.rarity.color_rgba
        cartao = ui.cartao(pai, x, z, largura, altura, self._selecionar, [indice], cor_raridade=cor)
        ui.imagem_do_item(cartao, skin.api_id, 0, altura / 2 - 0.14, largura - 0.08, 0.25)
        arma, padrao = nome_em_duas_linhas(skin.name)
        esq = -largura / 2 + 0.03
        ui.texto(cartao, arma, esq, -0.085, 0.024, COR_TEXTO_2, largura_max=largura - 0.06)
        ui.texto(cartao, padrao or "Vanilla", esq, -0.13, 0.031, COR_TEXTO, largura_max=largura - 0.06)
        ui.texto(cartao, skin_instancia.wear_label, esq, -0.172, 0.022, COR_TEXTO_3, largura_max=largura - 0.06)
        return cartao

    # ==================================================================
    # SELEÇÃO E MENU DO ITEM
    # ==================================================================

    def _selecionar(self, indice):
        """Clique no cartão: aumenta um pouco, borda laranja e o menu de ações ao lado."""
        anterior = self.cartoes.get(self.selecionado)
        if anterior is not None:
            anterior.setScale(1.0)
            if getattr(anterior, "contorno", None) is not None:
                anterior.contorno.destroy()
                anterior.contorno = None
        if self.selecionado == indice:
            self.selecionado = None            # clicar de novo desmarca
            self._fechar_menu()
            return
        cartao = self.cartoes.get(indice)
        if cartao is None:
            return
        self.selecionado = indice
        cartao.setScale(AUMENTO_SELECIONADO)
        cartao.reparentTo(self.area_grade)     # vai para a frente dos vizinhos
        x1, x2, z1, z2 = cartao["frameSize"]
        cartao.contorno = self.ui.contorno(cartao, x1, x2, z1, z2, COR_LARANJA, 0.007)
        self._mostrar_menu(indice, cartao)

    def _mostrar_menu(self, indice, cartao):
        menu = self._recriar("area_menu")
        tipo, item = self.itens[indice]
        if tipo == "caixa":
            acoes = [("ABRIR CAIXA", self._abrir_caixa, [item], "primario"),
                     ("VER CONTEÚDO", self._ver_conteudo, [item], "secundario")]
        else:
            cotacao = self.controller.sale_quote(item.id)
            texto_venda = f"VENDER  ·  {format_money(cotacao[1])}" if cotacao else "VENDER"
            acoes = [("DETALHES", self._abrir_detalhes, [item], "primario"),
                     (texto_venda, self._vender, [item], "secundario")]

        # Menu ao lado direito do cartão (ou à esquerda, se não couber)
        largura, altura = self.tamanho_cartao
        x_cartao, _y, z_cartao = cartao.getPos()
        meia = largura / 2 * AUMENTO_SELECIONADO
        x = x_cartao + meia + 0.02 + MENU_LARGURA / 2
        if x + MENU_LARGURA / 2 > GRADE_X2 + 0.05:
            x = x_cartao - meia - 0.02 - MENU_LARGURA / 2
        z = z_cartao + altura / 2 * AUMENTO_SELECIONADO - MENU_ALTURA / 2
        for texto, comando, extra, tipo_botao in acoes:
            self.ui.botao(menu, texto, x, z, MENU_LARGURA, MENU_ALTURA, comando, extra, tipo=tipo_botao,
                          escala=0.028)
            z -= MENU_ALTURA + 0.012

    def _fechar_menu(self):
        if self.area_menu is not None:
            self.area_menu.destroy()
            self.area_menu = None

    # ==================================================================
    # DETALHES DA SKIN (pop-up)
    # ==================================================================

    def _abrir_detalhes(self, instancia, permitir_venda=True):
        ui = self.ui
        skin = instancia.skin
        especial = skin.rarity.name == "Special Item"
        cor = COR_OURO if especial else skin.rarity.color_rgba
        janela = self._abrir_janela(2.9, 1.5, None)
        p = janela.painel

        # lado esquerdo: imagem grande com o brilho da raridade
        ui.retangulo(p, -1.40, -0.08, -0.62, 0.66, (0.07, 0.08, 0.10, 1))
        ui.gradiente(p, -1.40, -0.08, -0.62, 0.10, cor[:3] + (0.32,), cor[:3] + (0.0,))
        ui.retangulo(p, -1.40, -0.08, -0.62, -0.606, cor)
        ui.imagem_do_item(p, skin.api_id, -0.74, 0.04, 1.20, 0.80)

        # lado direito: informações
        x = 0.04
        arma, padrao = nome_em_duas_linhas(skin.name)
        ui.texto(p, arma, x, 0.55, 0.036, COR_TEXTO_2, largura_max=1.30)
        ui.texto(p, padrao or "Vanilla", x, 0.465, 0.062, COR_TEXTO, negrito=True, largura_max=1.30)
        ui.texto(p, "★ Item Especial Raro" if especial else skin.rarity.name, x, 0.40, 0.03, cor, negrito=True)

        ui.texto(p, "DESGASTE", x, 0.30, 0.024, COR_TEXTO_3, negrito=True)
        if skin.has_wear:
            ui.texto(p, f"{instancia.wear_label}  ({instancia.wear})", x, 0.25, 0.034, COR_TEXTO)
            ui.texto(p, "FLOAT", x, 0.165, 0.024, COR_TEXTO_3, negrito=True)
            ui.texto(p, f"{instancia.float_value:.9f}".replace(".", ","), x, 0.105, 0.046, COR_TEXTO, negrito=True)
            ui.barra_desgaste(p, x, 1.34, 0.035, instancia.float_value, skin.min_float, skin.max_float)
            ui.texto(p, "0", x, -0.012, 0.022, COR_TEXTO_3)
            ui.texto(p, "1", 1.34, -0.012, 0.022, COR_TEXTO_3, DIREITA)
            faixa = f"float desta skin: {skin.min_float:.2f} a {skin.max_float:.2f}".replace(".", ",")
            ui.texto(p, faixa, (x + 1.34) / 2, -0.012, 0.022, COR_TEXTO_3, CENTRO)
        else:
            ui.texto(p, "Sem pintura: este item não tem desgaste (float 0).", x, 0.25, 0.03, COR_TEXTO)

        ui.texto(p, "VALOR", x, -0.10, 0.024, COR_TEXTO_3, negrito=True)
        cotacao = self.controller.sale_quote(instancia.id) if permitir_venda else None
        if cotacao:
            preco, recebe = cotacao
            ui.texto(p, f"Preço de mercado hoje: {format_money(preco)}", x, -0.155, 0.034, COR_TEXTO)
            ui.texto(p, f"Vendendo agora você recebe {format_money(recebe)} (taxa de {SELL_FEE_RATE:.0%})",
                     x, -0.205, 0.026, COR_VERDE)
        ui.texto(p, f"Valor quando você obteve: {format_money(instancia.skin_price)}", x, -0.255, 0.024,
                 COR_TEXTO_2)
        if instancia.acquired_at is not None and hasattr(instancia.acquired_at, "strftime"):
            ui.texto(p, f"Obtida em {instancia.acquired_at.strftime('%d/%m/%Y %H:%M')}", x, -0.30, 0.024,
                     COR_TEXTO_2)

        ui.botao(p, "FECHAR", 1.12, -0.60, 0.40, 0.09, self._fechar_janela, tipo="secundario", escala=0.03)
        if permitir_venda and cotacao:
            ui.botao(p, "VENDER", 0.66, -0.60, 0.40, 0.09, self._vender, [instancia], escala=0.032)
        self.acao_enter = (self._fechar_janela, [])

    # ==================================================================
    # VENDA (valor final -> confirmação -> venda)
    # ==================================================================

    def _vender(self, instancia):
        cotacao = self.controller.sale_quote(instancia.id)
        if cotacao is None:
            return                              # o controller já mostrou o motivo
        preco, recebe = cotacao
        ui = self.ui
        janela = self._abrir_janela(1.72, 0.92, "CONFIRMAR VENDA")
        p = janela.painel
        ui.imagem_do_item(p, instancia.skin.api_id, -0.58, 0.02, 0.40, 0.32)
        x = -0.30
        ui.texto(p, f"Vender {limpar_nome(instancia.name)}?", x, 0.22, 0.034, COR_TEXTO, largura_max=1.12)
        ui.texto(p, instancia.wear_label, x, 0.165, 0.026, COR_TEXTO_2)
        ui.texto(p, "Preço de mercado", x, 0.08, 0.028, COR_TEXTO_2)
        ui.texto(p, format_money(preco), 0.80, 0.08, 0.028, COR_TEXTO, DIREITA)
        ui.texto(p, f"Taxa do mercado ({SELL_FEE_RATE:.0%})", x, 0.025, 0.028, COR_TEXTO_2)
        ui.texto(p, f"− {format_money(preco - recebe)}", 0.80, 0.025, 0.028, COR_VERMELHO, DIREITA)
        ui.retangulo(p, x, 0.80, -0.005, -0.001, COR_TEXTO_3)
        ui.texto(p, "Você recebe", x, -0.06, 0.034, COR_TEXTO, negrito=True)
        ui.texto(p, format_money(recebe), 0.80, -0.06, 0.04, COR_VERDE, DIREITA, negrito=True)
        ui.botao(p, "CANCELAR", 0.16, -0.33, 0.40, 0.09, self._fechar_janela, tipo="secundario", escala=0.03)
        ui.botao(p, "VENDER", 0.60, -0.33, 0.40, 0.09, self._efetuar_venda, [instancia], escala=0.032)
        self.acao_enter = (self._efetuar_venda, [instancia])

    def _efetuar_venda(self, instancia):
        self._fechar_janela()
        if self.controller.sell_skin(instancia.id) is not None:
            self.atualizar_saldo()
        self._carregar()                       # o item sai da grade (ou volta ao estado real se falhou)

    # ==================================================================
    # CAIXAS: conteúdo e abertura
    # ==================================================================

    def _ver_conteudo(self, caixa):
        tabela = self.controller.case_contents(caixa.id)
        if tabela:
            self._fechar_janela()
            self.janela = abrir_janela_conteudo(self.ui, self.raiz, caixa.name, tabela, self._fechar_janela)
            self.acao_enter = (self._fechar_janela, [])

    def _abrir_caixa(self, caixa):
        tabela = self.controller.case_contents(caixa.id)
        if not tabela:
            return                              # o controller já mostrou o motivo; a roleta nem abre
        self._fechar_menu()
        self.aviso.esconder()                  # aviso antigo (ex.: saldo) não fica atrás da roleta
        self.abertura = AberturaDeCaixa(
            self.ui, self.raiz, self.controller, caixa, tabela,
            ao_sair=self._ao_sair_da_abertura,
            ao_ver_detalhes=lambda instancia: self._abrir_detalhes(instancia, permitir_venda=False),
            ao_mudar_saldo=self.atualizar_saldo,
        )

    def _ao_sair_da_abertura(self):
        self.abertura = None
        self._carregar()

    # ==================================================================
    # JANELAS, PÁGINAS E TECLADO
    # ==================================================================

    def _abrir_janela(self, largura, altura, titulo):
        self._fechar_janela()
        self.janela = Janela(self.ui, self.raiz, largura, altura, titulo)
        return self.janela

    def _fechar_janela(self):
        if self.janela is not None:
            self.janela.fechar()
            self.janela = None
        self.acao_enter = None

    def _janela_aberta(self):
        return self.janela is not None and self.janela.aberta

    def _abertura_ativa(self):
        return self.abertura is not None and self.abertura.aberta

    def _trocar_filtro(self, filtro):
        self.filtro = filtro
        self.pagina = 0
        self._aplicar_filtro()

    def _total_paginas(self):
        return max(1, -(-len(self.itens) // POR_PAGINA))

    def _ir_para_pagina(self, pagina):
        if 0 <= pagina < self._total_paginas():
            self.pagina = pagina
            self.selecionado = None
            self._desenhar_grade()

    def _mudar_pagina_relativa(self, passo):
        if self._janela_aberta() or self._abertura_ativa():
            return
        self._ir_para_pagina(self.pagina + passo)

    def _tecla_esc(self):
        if self._janela_aberta():
            self._fechar_janela()
        elif self._abertura_ativa():
            self.abertura.tecla_esc()
        elif self.selecionado is not None:
            self._selecionar(self.selecionado)      # desmarca

    def _tecla_enter(self):
        if self._janela_aberta():
            if self.acao_enter:
                funcao, extra = self.acao_enter
                funcao(*extra)
        elif self._abertura_ativa():
            self.abertura.tecla_enter()

    def _tecla_espaco(self):
        if self._abertura_ativa() and not self._janela_aberta():
            self.abertura.tecla_espaco()

    def _recriar(self, nome):
        antigo = getattr(self, nome)
        if antigo is not None:
            antigo.destroy()
        novo = self.ui.container(self.raiz)
        setattr(self, nome, novo)
        if nome == "area_grade":
            self.cartoes = {}
        return novo
