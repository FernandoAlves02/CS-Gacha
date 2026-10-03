import logging
import math
import random

from app.core.drop_service import drop_table, float_for_wear
from app.core.game_rules import INVENTORY_LIMIT, RARITY_ORDER, format_money, price_change
from app.core.i18n import t
from app.models.skin_instance import Skin_Instance

logger = logging.getLogger(__name__)

# Quantos anúncios de skin por página no mercado.
PAGE_SIZE = 24

# Máximo de unidades numa compra só (caixas ou skins iguais).
MAX_PER_PURCHASE = 50


class Market_Controller:
    """Regras da tela do MERCADO (comprar caixas e skins avulsas).

    Contrato com a tela (view): ela precisa ter
        show_message(message, success=True)
    Os métodos de listagem DEVOLVEM os dados; a tela chama e desenha.

    "user" é o usuário logado (view_manager.usuario_logado). O saldo dele é
    atualizado aqui depois de cada compra, para o header mostrar o valor novo.

    Fluxo de compra pedido na documentação:
        1. can_afford(preço)       -> preço em verde (True) ou vermelho (False)
        2. check_purchase(preço)   -> None = pode comprar | texto = motivo do bloqueio
        3. a tela pergunta "Deseja comprar por R$ X?"
        4. buy_case(...) / buy_skin(...) -> o DAO confere TUDO de novo dentro da transação
    """

    def __init__(self, collection_dao, skin_catalog_dao, inventory_dao, view, user, rng=random,
                 rarity_dao=None):
    def __init__(self, collection_dao, skin_catalog_dao, inventory_dao, view, user, rng=random,
                 rarity_dao=None):
        self.collection_dao = collection_dao
        self.skin_catalog_dao = skin_catalog_dao
        self.inventory_dao = inventory_dao
        self.view = view
        self.user = user
        self.rng = rng          # nos testes passamos random.Random(semente)
        self.rarity_dao = rarity_dao    # só para os filtros de raridade da aba SKINS
        self.rarity_dao = rarity_dao    # só para os filtros de raridade da aba SKINS

    # ----------------------------------------------------------
    # LISTAGENS
    # ----------------------------------------------------------

    def list_cases(self):
        """Caixas à venda (lista de Collection)."""
        try:
            return self.collection_dao.get_all()
        except Exception:
            logger.exception("Falha ao listar caixas")
            self.view.show_message(t("Não foi possível carregar as caixas."), False)
            return []

    def case_contents(self, collection_id):
        """O que pode sair da caixa e a chance de cada item: lista de (Skin_Catalog, chance).
        A chance é um Decimal entre 0 e 1 (multiplique por 100 para mostrar em %)."""
        try:
            items = self.collection_dao.get_items(collection_id)
            probabilities = {item.rarity_id: item.rarity.probability for item in items}
            return drop_table(items, probabilities)
        except ValueError as e:
            self.view.show_message(str(e), False)
        except Exception:
            logger.exception("Falha ao carregar o conteúdo da caixa")
            self.view.show_message(t("Não foi possível carregar o conteúdo da caixa."), False)
        return []

    def list_rarities(self):
        """Raridades para os filtros da aba SKINS (lista de Rarity, da mais comum para a mais rara)."""
        if self.rarity_dao is None:
            return []
        try:
            ordem = {nome: i for i, nome in enumerate(RARITY_ORDER)}
            return sorted(self.rarity_dao.get_all(), key=lambda r: (ordem.get(r.name, len(ordem)), r.id))
        except Exception:
            logger.exception("Falha ao listar raridades")
            return []

    def list_skins(self, search="", page=0, rarity_id=None):
        """Skins à venda, paginadas. Devolve (lista de (Skin_Catalog, Market_Price), total de páginas)."""
        try:
            total = self.skin_catalog_dao.count_market_listings(search, rarity_id)
            rows = self.skin_catalog_dao.get_market_listings(
                search, PAGE_SIZE, max(page, 0) * PAGE_SIZE, rarity_id
            )
            return rows, max(1, math.ceil(total / PAGE_SIZE))
        except Exception:
            logger.exception("Falha ao listar skins")
            self.view.show_message(t("Não foi possível carregar o mercado de skins."), False)
            return [], 1

    def skin_prices(self, skin_catalog_id):
        """Preço da skin em cada desgaste (lista de Market_Price)."""
        try:
            return self.skin_catalog_dao.get_prices(skin_catalog_id)
        except Exception:
            logger.exception("Falha ao carregar preços")
            self.view.show_message(t("Não foi possível carregar os preços."), False)
            return []

    def price_changes(self, listings):
        """Variação recente (▲▼) de cada anúncio da página.

        listings: o que list_skins devolveu [(Skin_Catalog, Market_Price)].
        Devolve {(skin_id, desgaste): (variação em %, horas)}; anúncio sem
        histórico suficiente fica de fora. Falha aqui não atrapalha a tela.
        """
        try:
            pares = [(skin.id, preco.wear) for skin, preco in listings]
            historico = self.skin_catalog_dao.get_history_for_listings(pares)
        except Exception:
            logger.exception("Falha ao carregar a variação dos preços")
            return {}
        variacoes = {}
        for par, pontos in historico.items():
            variacao = price_change(pontos)
            if variacao is not None:
                variacoes[par] = variacao
        return variacoes

    def price_changes(self, listings):
        """Variação recente (▲▼) de cada anúncio da página.

        listings: o que list_skins devolveu [(Skin_Catalog, Market_Price)].
        Devolve {(skin_id, desgaste): (variação em %, horas)}; anúncio sem
        histórico suficiente fica de fora. Falha aqui não atrapalha a tela.
        """
        try:
            pares = [(skin.id, preco.wear) for skin, preco in listings]
            historico = self.skin_catalog_dao.get_history_for_listings(pares)
        except Exception:
            logger.exception("Falha ao carregar a variação dos preços")
            return {}
        variacoes = {}
        for par, pontos in historico.items():
            variacao = price_change(pontos)
            if variacao is not None:
                variacoes[par] = variacao
        return variacoes

    def price_history(self, skin_catalog_id=None, wear=None, collection_id=None, limit=30):
        """Histórico (data, preço) de uma skin+desgaste OU de uma caixa (para gráfico)."""
        try:
            if collection_id is not None:
                return self.collection_dao.get_price_history(collection_id, limit)
            return self.skin_catalog_dao.get_price_history(skin_catalog_id, wear, limit)
        except Exception:
            logger.exception("Falha ao carregar histórico")
            return []

    # ----------------------------------------------------------
    # CHECAGENS ANTES DA COMPRA
    # ----------------------------------------------------------

    def can_afford(self, price):
        """True = mostrar o preço em VERDE; False = em VERMELHO."""
        return self.user.balance >= price

    @staticmethod
    def check_quantity(quantity):
        """None se a quantidade vale (1 a MAX_PER_PURCHASE); senão, a mensagem."""
        if isinstance(quantity, bool) or not isinstance(quantity, int) or not 1 <= quantity <= MAX_PER_PURCHASE:
            return t("Quantidade inválida (de 1 a {maximo} por compra).", maximo=MAX_PER_PURCHASE)
        return None

    def check_purchase(self, price, quantity=1):
        """Checagem antes de pedir confirmação. Devolve None se pode comprar,
        ou a mensagem do motivo ("Saldo insuficiente." / "Inventário cheio!")."""
        erro = self.check_quantity(quantity)
        if erro:
            return erro
        if not self.can_afford(price * quantity):
            return t("Saldo insuficiente.")
        try:
            if self.inventory_dao.count_items(self.user.id) + quantity > INVENTORY_LIMIT:
                return t("Inventário cheio!")
        except Exception:
            logger.exception("Falha ao contar o inventário")
            return t("Não foi possível verificar o inventário.")
        return None

    def max_quantity(self, price):
        """Quantas unidades dá para comprar agora: limite por compra, saldo e espaço livre."""
        try:
            livres = INVENTORY_LIMIT - self.inventory_dao.count_items(self.user.id)
        except Exception:
            logger.exception("Falha ao contar o inventário")
            return 1
        pelo_saldo = int(self.user.balance // price) if price > 0 else MAX_PER_PURCHASE
        return max(1, min(MAX_PER_PURCHASE, pelo_saldo, livres))

    # ----------------------------------------------------------
    # COMPRAS
    # ----------------------------------------------------------

    def buy_case(self, collection, quantity=1):
        """Compra caixa(s) (objeto Collection mostrado na tela). Devolve True/False."""
        erro = self.check_quantity(quantity)
        if erro:
            self.view.show_message(erro, False)
            return False
        try:
            new_balance = self.inventory_dao.buy_case(
                self.user.id, collection.id, expected_price=collection.price, quantity=quantity
            )

        except ValueError as e:
            self.view.show_message(str(e), False)
            return False

        except Exception:
            logger.exception("Falha ao comprar caixa")
            self.view.show_message(t("Não foi possível concluir a compra."), False)
            return False

        self.user.balance = new_balance
        quantas = f"{quantity}x " if quantity > 1 else ""
        self.view.show_message(
            t("{nome} comprada! Saldo: {saldo}", nome=quantas + collection.name, saldo=format_money(new_balance))
        )
        return True

    def buy_skin(self, skin, market_price):
        """Compra UMA skin avulsa. Devolve o Skin_Instance criado, ou None."""
        compradas = self.buy_skins(skin, market_price, 1)
        return compradas[0] if compradas else None

    def buy_skins(self, skin, market_price, quantity=1):
        """Compra skin(s) avulsa(s) no desgaste escolhido (tudo ou nada).

        skin: Skin_Catalog | market_price: Market_Price (o anúncio clicado).
        Cada unidade ganha o SEU float, sorteado dentro da faixa do desgaste
        (ex.: Field-Tested 0.15-0.38). Devolve a lista de Skin_Instance, ou [] se falhou.
        """
        erro = self.check_quantity(quantity)
        if erro:
            self.view.show_message(erro, False)
            return []
        try:
            floats = [float_for_wear(skin.min_float, skin.max_float, market_price.wear, self.rng)
                      for _ in range(quantity)]
            new_ids, price, new_balance = self.inventory_dao.buy_skins(
                self.user.id, skin.id, market_price.wear, floats,
                expected_price=market_price.price
            )

        except ValueError as e:
            self.view.show_message(str(e), False)
            return []

        except Exception:
            logger.exception("Falha ao comprar skin")
            self.view.show_message(t("Não foi possível concluir a compra."), False)
            return []

        self.user.balance = new_balance
        quantas = f"{quantity}x " if quantity > 1 else ""
        self.view.show_message(t("{nome} comprada! Saldo: {saldo}", nome=quantas + skin.name,
                                 saldo=format_money(new_balance)))
        return [Skin_Instance(new_id, self.user.id, skin.id, valor, price, skin=skin)
                for new_id, valor in zip(new_ids, floats)]
