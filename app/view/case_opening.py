"""Tela de ABERTURA DE CAIXA (Fase 5): a roleta do CS2, desenhada por cima do inventário.

Regra da documentação: "o front só recebe o resultado"
------------------------------------------------------
Ao clicar em ABRIR, a tela chama Inventory_Controller.open_case(). O backend
sorteia raridade, skin e float, cobra a chave e salva tudo no banco ANTES de
qualquer animação. Só depois a roleta é montada, já sabendo onde vai parar:
o item sorteado é colocado na posição VENCEDOR e a roleta desliza até ele.

Os outros cartões da roleta são só enfeite: são escolhidos com as chances
reais da caixa (mesma tabela do mercado), mas não decidem nada.

Como no CS2, facas e luvas aparecem na roleta como um cartão dourado
"★ Item Especial Raro"; qual é a faca só aparece no resultado.

Fluxo:  prévia (conteúdo + ABRIR) -> roleta girando (~6,5 s; clique ou ESPAÇO pula)
        -> resultado (ACEITAR | ABRIR OUTRA | VER DETALHES)

A CAIXA GRÁTIS (Extras 4) usa a mesma tela com gratis=True: sem chave, sem
"ABRIR OUTRA" (a próxima só daqui a 10 min) e o sorteio vem da tabela dela.
"""
import random

from direct.interval.IntervalGlobal import Func, LerpFunc, Sequence
from panda3d.core import Point3

from app.core.game_rules import KEY_PRICE, format_money, rarity_label
from app.core.i18n import numero, t
from app.view.sons import tocar_som
from app.view.ui_kit import (
    CENTRO,
    COR_CARD,
    COR_LARANJA,
    COR_LINHA,
    COR_OURO,
    COR_TEXTO,
    COR_TEXTO_2,
    COR_TEXTO_3,
    DIREITA,
    formatar_chance,
    limpar_nome,
    nome_em_duas_linhas,
)

# Faixa da roleta (unidades do aspect2d)
ROLETA_X1, ROLETA_X2 = -1.50, 1.50
ROLETA_Z1, ROLETA_Z2 = 0.04, 0.48
CARTAO_L, CARTAO_A = 0.30, 0.36
CARTAO_ESPACO = 0.02
PASSO = CARTAO_L + CARTAO_ESPACO

TOTAL_CARTOES = 60
VENCEDOR = 52                # posição do item sorteado na fila de cartões
DURACAO_GIRO = 6.5           # segundos

RARIDADE_ESPECIAL = "Special Item"
RARIDADES_COM_SOM_RARO = ("Covert", "Contraband", RARIDADE_ESPECIAL)   # resultado com som especial


def desacelerar(t):
    """Curva da roleta: começa rápido e vai parando devagar (como no CS2)."""
    return 1 - (1 - t) ** 4


def e_especial(skin):
    return skin.rarity is not None and skin.rarity.name == RARIDADE_ESPECIAL


class AberturaDeCaixa:
    """Overlay da abertura. A tela do inventário cria, e é avisada pelos callbacks:

    ao_sair(): o jogador clicou ACEITAR/VOLTAR (o inventário recarrega);
    ao_ver_detalhes(skin_instance): abrir o pop-up de detalhes do item ganho;
    ao_mudar_saldo(): atualizar o saldo do header (a chave foi cobrada).
    """

    def __init__(self, kit, pai, controller, caixa, tabela, ao_sair, ao_ver_detalhes, ao_mudar_saldo,
                 gratis=False):
        self.kit = kit
        self.gratis = gratis            # caixa grátis: abre sem chave (controller.open_free_case)
        self.controller = controller
        self.caixa = caixa
        self.quantidade = caixa.quantity or 1
        self.ao_sair = ao_sair
        self.ao_ver_detalhes = ao_ver_detalhes
        self.ao_mudar_saldo = ao_mudar_saldo
        self.sorteio_visual = random.Random()      # só para os cartões de enfeite
        self.sequencia = None
        self.resultado = None
        self.estado = "previa"                      # previa -> girando -> resultado

        self.tabela = tabela            # [(Skin_Catalog, chance)]: o inventário só abre esta tela se houver itens

        # Véu que cobre a tela inteira (inclusive o header) e segura os cliques
        self.veu = kit.retangulo(pai, -4, 4, -2, 2, (0.025, 0.03, 0.04, 0.97), clicavel=True)
        self.raiz = kit.container(self.veu)
        self.area_baixo = None
        self.area_titulo = None
        self._desenhar_titulo()
        self._desenhar_faixa()
        self._preencher_roleta(None)
        self._desenhar_previa()

    # ==================================================================
    # PARTES FIXAS
    # ==================================================================

    def _desenhar_titulo(self):
        if self.area_titulo is not None:
            self.area_titulo.destroy()
        self.area_titulo = area = self.kit.container(self.raiz)
        self.kit.texto(area, limpar_nome(self.caixa.name), 0, 0.74, 0.07, COR_TEXTO, CENTRO, negrito=True)
        if self.gratis:
            restam = t("Sem chave · 1 grátis a cada 10 minutos")
        elif self.quantidade == 1:
            restam = t("Você tem {n} caixa desta", n=self.quantidade)
        else:
            restam = t("Você tem {n} caixas desta", n=self.quantidade)
        self.kit.texto(area, restam, 0, 0.665, 0.03, COR_TEXTO_2, CENTRO)

    def _desenhar_faixa(self):
        """Faixa escura da roleta, com o marcador laranja no meio."""
        kit = self.kit
        kit.retangulo(self.raiz, ROLETA_X1, ROLETA_X2, ROLETA_Z1, ROLETA_Z2, (0.045, 0.05, 0.065, 1))
        kit.retangulo(self.raiz, ROLETA_X1, ROLETA_X2, ROLETA_Z2, ROLETA_Z2 + 0.006, COR_LINHA)
        kit.retangulo(self.raiz, ROLETA_X1, ROLETA_X2, ROLETA_Z1 - 0.006, ROLETA_Z1, COR_LINHA)

        # Os cartões ficam num nó com "scissor": nada aparece fora da faixa.
        self.janela_roleta = kit.container(self.raiz)
        self.janela_roleta.setScissor(Point3(ROLETA_X1, 0, ROLETA_Z1), Point3(ROLETA_X2, 0, ROLETA_Z2))
        self.fila = None

        # Botão invisível do tamanho da faixa: clicar pula a animação
        self.botao_pular = kit.botao_texto(self.raiz, "", 0, ROLETA_Z1, 0.03, self.pular)
        self.botao_pular["frameSize"] = (ROLETA_X1, ROLETA_X2, 0, ROLETA_Z2 - ROLETA_Z1)

        # Marcador central (por cima dos cartões)
        meio = (ROLETA_Z1 + ROLETA_Z2) / 2
        kit.retangulo(self.raiz, -0.004, 0.004, ROLETA_Z1 - 0.02, ROLETA_Z2 + 0.02, COR_LARANJA)
        kit.texto(self.raiz, "▼", 0, ROLETA_Z2 + 0.02, 0.05, COR_LARANJA, CENTRO)
        kit.texto(self.raiz, "▲", 0, ROLETA_Z1 - 0.065, 0.05, COR_LARANJA, CENTRO)
        self._meio_faixa = meio

    # ==================================================================
    # CARTÕES DA ROLETA
    # ==================================================================

    def _sortear_enfeite(self):
        """Um item de enfeite, com as chances reais da caixa."""
        skins = [skin for skin, _chance in self.tabela]
        pesos = [float(chance) for _skin, chance in self.tabela]
        return self.sorteio_visual.choices(skins, weights=pesos, k=1)[0]

    def _preencher_roleta(self, vencedor_skin):
        """Monta a fila de cartões. vencedor_skin=None: só enfeite (tela de prévia)."""
        if self.fila is not None:
            self.fila.destroy()
        self.fila = self.kit.container(self.janela_roleta, 0, self._meio_faixa)
        if not self.tabela:
            return
        for i in range(TOTAL_CARTOES):
            skin = vencedor_skin if (i == VENCEDOR and vencedor_skin is not None) else self._sortear_enfeite()
            self._cartao_roleta(self.fila, i * PASSO, skin)
        # posição inicial: os primeiros cartões preenchendo a faixa
        self.x_inicio = ROLETA_X1 + CARTAO_L / 2 + CARTAO_ESPACO
        self.fila.setX(self.x_inicio)

    def _cartao_roleta(self, pai, x, skin):
        kit = self.kit
        if e_especial(skin):
            cartao = kit.container(pai, x, 0)
            kit.retangulo(cartao, -CARTAO_L / 2, CARTAO_L / 2, -CARTAO_A / 2, CARTAO_A / 2, COR_CARD)
            r, g, b = COR_OURO[:3]
            kit.gradiente(cartao, -CARTAO_L / 2, CARTAO_L / 2, -CARTAO_A / 2, CARTAO_A / 2,
                          (r, g, b, 0.45), (r, g, b, 0.08))
            kit.retangulo(cartao, -CARTAO_L / 2, CARTAO_L / 2, -CARTAO_A / 2, -CARTAO_A / 2 + 0.012, COR_OURO)
            kit.texto(cartao, "★", 0, 0.0, 0.16, COR_OURO, CENTRO)
            kit.texto(cartao, t("Item Especial Raro"), 0, -0.12, 0.024, COR_TEXTO, CENTRO, negrito=True)
            return cartao
        cor = skin.rarity.color_rgba
        cartao = kit.container(pai, x, 0)
        kit.retangulo(cartao, -CARTAO_L / 2, CARTAO_L / 2, -CARTAO_A / 2, CARTAO_A / 2, COR_CARD)
        kit.gradiente(cartao, -CARTAO_L / 2, CARTAO_L / 2, -CARTAO_A / 2, CARTAO_A * 0.1,
                      cor[:3] + (0.35,), cor[:3] + (0.0,))
        kit.retangulo(cartao, -CARTAO_L / 2, CARTAO_L / 2, -CARTAO_A / 2, -CARTAO_A / 2 + 0.012, cor)
        kit.imagem_do_item(cartao, skin.api_id, 0, 0.03, CARTAO_L - 0.03, 0.24)
        return cartao

    # ==================================================================
    # PRÉVIA (antes de abrir)
    # ==================================================================

    def _desenhar_previa(self):
        kit = self.kit
        area = self._nova_area_baixo()
        kit.texto(area, t("ITENS QUE PODEM SAIR DESTA CAIXA"), ROLETA_X1, -0.10, 0.026, COR_TEXTO_2, negrito=True)

        # Itens normais (como no CS2, as facas/luvas aparecem juntas num só cartão dourado)
        normais = [(s, c) for s, c in self.tabela if not e_especial(s)]
        especiais = [(s, c) for s, c in self.tabela if e_especial(s)]
        cartoes = normais[:17] + ([("especial", sum(c for _s, c in especiais))] if especiais else [])
        largura, altura, gap = 0.30, 0.20, 0.022
        colunas = 9
        for i, (item, chance) in enumerate(cartoes):
            x = ROLETA_X1 + largura / 2 + (i % colunas) * (largura + gap)
            z = -0.25 - (i // colunas) * (altura + gap)
            if item == "especial":
                cartao = kit.cartao(area, x, z, largura, altura, cor_raridade=COR_OURO)
                kit.texto(cartao, "★", 0, 0.0, 0.08, COR_OURO, CENTRO)
                kit.texto(cartao, t("{n} itens raros · {chance}", n=len(especiais), chance=formatar_chance(chance)),
                          0, -0.07, 0.019,
                          COR_TEXTO, CENTRO)
            else:
                cartao = kit.cartao(area, x, z, largura, altura, cor_raridade=item.rarity.color_rgba)
                kit.imagem_do_item(cartao, item.api_id, 0, 0.02, largura - 0.06, 0.13)
                _arma, padrao = nome_em_duas_linhas(item.name)
                kit.texto(cartao, padrao or limpar_nome(item.name), 0, -0.075, 0.019, COR_TEXTO, CENTRO,
                          largura_max=largura - 0.03)
            cartao["state"] = "disabled"
        if len(normais) > 17:
            kit.texto(area, t("+ {n} itens", n=len(normais) - 17), ROLETA_X2, -0.10, 0.024, COR_TEXTO_3, DIREITA)

        kit.botao(area, t("VOLTAR"), -0.30, -0.80, 0.44, 0.095, self.sair, tipo="secundario", escala=0.032)
        if self.gratis:
            texto_abrir = t("ABRIR GRÁTIS")
        else:
            texto_abrir = t("ABRIR CAIXA  ·  chave {preco}", preco=format_money(KEY_PRICE))
        kit.botao(area, texto_abrir, 0.30, -0.80, 0.66, 0.095, self.abrir, escala=0.032, ativo=bool(self.tabela))

    # ==================================================================
    # ABRIR E GIRAR
    # ==================================================================

    def abrir(self):
        """1) backend sorteia e salva; 2) só então a roleta é montada e gira."""
        if self.estado == "girando" or not self.tabela:
            return
        if self.gratis:
            resultado = self.controller.open_free_case(self.tabela)
        else:
            resultado = self.controller.open_case(self.caixa.id)
        if resultado is None:
            return                              # o controller já mostrou o motivo (saldo, caixa...)
        self.resultado = resultado
        self.quantidade = resultado.remaining_cases
        self.ao_mudar_saldo()
        self.estado = "girando"

        area = self._nova_area_baixo()
        self.kit.texto(area, t("Clique na roleta ou aperte ESPAÇO para pular"), 0, -0.12, 0.026, COR_TEXTO_3, CENTRO)

        self._preencher_roleta(resultado.skin)
        # Para no cartão VENCEDOR, num ponto aleatório dentro dele (fica mais natural)
        desvio = self.sorteio_visual.uniform(-0.40, 0.40) * CARTAO_L
        self.x_final = -(VENCEDOR * PASSO + desvio)
        self.cartao_no_marcador = self._cartao_no_meio(self.x_inicio)   # "tique" a cada cartão que passa
        self.sequencia = Sequence(
            LerpFunc(self._mover_fila, fromData=0.0, toData=1.0, duration=DURACAO_GIRO),
            Func(self._mostrar_resultado),
        )
        self.sequencia.start()

    def _mover_fila(self, t):
        self.fila.setX(self.x_inicio + (self.x_final - self.x_inicio) * desacelerar(t))
        # "tique" quando um cartão novo chega ao marcador do meio (rápido no começo, devagar no fim)
        cartao = self._cartao_no_meio(self.fila.getX())
        if cartao != self.cartao_no_marcador:
            self.cartao_no_marcador = cartao
            tocar_som(self.kit.app, "tique")

    @staticmethod
    def _cartao_no_meio(x_fila):
        """Índice do cartão que está em cima do marcador (o marcador fica no x = 0)."""
        return int(-x_fila / PASSO + 0.5)

    def pular(self):
        """Clique na roleta / ESPAÇO: vai direto para o resultado."""
        if self.estado == "girando" and self.sequencia is not None:
            self.sequencia.finish()            # leva a roleta ao fim e chama _mostrar_resultado

    # ==================================================================
    # RESULTADO
    # ==================================================================

    def _mostrar_resultado(self):
        self.estado = "resultado"
        self.sequencia = None
        kit = self.kit
        instancia = self.resultado.skin_instance
        skin = instancia.skin
        cor = COR_OURO if e_especial(skin) else skin.rarity.color_rgba
        self._desenhar_titulo()
        raro = skin.rarity is not None and skin.rarity.name in RARIDADES_COM_SOM_RARO
        tocar_som(self.kit.app, "raro" if raro else "resultado")

        area = self._nova_area_baixo()
        # cartão grande com o item ganho
        kit.retangulo(area, -1.0, 1.0, -0.66, -0.05, (0.075, 0.085, 0.105, 1))
        kit.gradiente(area, -1.0, 1.0, -0.66, -0.25, cor[:3] + (0.30,), cor[:3] + (0.0,))
        kit.retangulo(area, -1.0, 1.0, -0.66, -0.648, cor)
        kit.imagem_do_item(area, skin.api_id, -0.52, -0.36, 0.80, 0.52)
        arma, padrao = nome_em_duas_linhas(skin.name)
        kit.texto(area, t("VOCÊ GANHOU"), 0.02, -0.12, 0.026, COR_TEXTO_2, negrito=True)
        kit.texto(area, arma, 0.02, -0.18, 0.034, COR_TEXTO_2, largura_max=0.95)
        kit.texto(area, padrao or "Vanilla", 0.02, -0.25, 0.055, COR_TEXTO, negrito=True, largura_max=0.95)
        kit.texto(area, rarity_label(skin.rarity.name), 0.02, -0.31, 0.03, cor, negrito=True)
        float_texto = numero(instancia.float_value, 9)
        kit.texto(area, f"{instancia.wear_label}  ·  float {float_texto}", 0.02, -0.38, 0.03, COR_TEXTO)
        kit.texto(area, t("Valor: {valor}", valor=format_money(instancia.skin_price)), 0.02, -0.45, 0.04, COR_TEXTO, negrito=True)

        # Botões centralizados: VER DETALHES | ABRIR OUTRA (se ainda houver caixa) | ACEITAR
        botoes = [(t("VER DETALHES"), self.ao_ver_detalhes, [instancia], "secundario")]
        if self.resultado.can_open_another:
            botoes.append((t("ABRIR OUTRA  ({n})", n=self.resultado.remaining_cases), self.abrir_outra, [],
                           "secundario"))
        botoes.append((t("ACEITAR"), self.sair, [], "primario"))
        largura, espaco = 0.50, 0.04
        x = -(len(botoes) * largura + (len(botoes) - 1) * espaco) / 2 + largura / 2
        for texto, comando, extra, tipo in botoes:
            kit.botao(area, texto, x, -0.80, largura, 0.095, comando, extra, tipo=tipo, escala=0.03)
            x += largura + espaco

    def abrir_outra(self):
        self.abrir()

    # ==================================================================
    # TECLADO E SAÍDA
    # ==================================================================

    def tecla_espaco(self):
        self.pular()

    def tecla_esc(self):
        if self.estado == "girando":
            self.pular()
        else:
            self.sair()

    def tecla_enter(self):
        if self.estado == "previa":
            self.abrir()
        elif self.estado == "resultado":
            self.sair()

    def sair(self):
        if self.estado == "girando":
            return                            # termina a animação antes (o item já é seu)
        self.destruir()
        self.ao_sair()

    def destruir(self):
        if self.sequencia is not None:
            self.sequencia.pause()            # para a animação antes de apagar os cartões
            self.sequencia = None
        if self.veu is not None:
            self.veu.destroy()
            self.veu = None

    @property
    def aberta(self):
        return self.veu is not None

    def _nova_area_baixo(self):
        if self.area_baixo is not None:
            self.area_baixo.destroy()
        self.area_baixo = self.kit.container(self.raiz)
        return self.area_baixo
