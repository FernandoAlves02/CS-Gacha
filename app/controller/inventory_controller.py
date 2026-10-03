import logging
import random
from datetime import datetime

from app.core.drop_service import draw_drop, draw_from_table, drop_table, free_case_table
from app.core.game_rules import (
    FREE_CASE_COMMON_COUNT,
    FREE_CASE_RARE_CHANCE,
    FREE_CASE_RARE_MIN_PRICE,
    INVENTORY_LIMIT,
    format_money,
    free_case_wait,
)
from app.core.i18n import t
from app.models.drop_result import Drop_Result
from app.models.skin_instance import Skin_Instance

logger = logging.getLogger(__name__)


class Inventory_Controller:
    """Regras do INVENTÁRIO: listar itens, abrir caixas e vender skins.

    Contrato com a tela (view): ela precisa ter
        show_message(message, success=True)
    Os métodos de listagem DEVOLVEM os dados; a tela chama e desenha.

    "user" é o usuário logado (view_manager.usuario_logado); o saldo dele é
    atualizado aqui depois de abrir caixa (chave) ou vender.
    """

    def __init__(self, inventory_dao, collection_dao, rarity_dao, view, user, rng=random, skin_catalog_dao=None,
                 clock=datetime.now):
        self.inventory_dao = inventory_dao
        self.collection_dao = collection_dao
        self.rarity_dao = rarity_dao
        self.skin_catalog_dao = skin_catalog_dao    # conteúdo da caixa grátis (preços atuais)
        self.view = view
        self.user = user
        self.rng = rng          # nos testes passamos random.Random(semente)
        self.clock = clock      # hora atual (nos testes, um relógio "de mentira")

    # ----------------------------------------------------------
    # LISTAGEM
    # ----------------------------------------------------------

    def load(self):
        """Itens do jogador: (caixas agrupadas com .quantity, skins)."""
        try:
            cases = self.inventory_dao.get_cases(self.user.id)
            skins = self.inventory_dao.get_skins(self.user.id)
            return cases, skins
        except Exception:
            logger.exception("Falha ao carregar inventário")
            self.view.show_message(t("Não foi possível carregar o inventário."), False)
            return [], []

    def status(self):
        """(itens usados, limite). Ex.: (37, 1000) para mostrar "37/1000"."""
        try:
            return self.inventory_dao.count_items(self.user.id), INVENTORY_LIMIT
        except Exception:
            logger.exception("Falha ao contar inventário")
            return 0, INVENTORY_LIMIT

    # ----------------------------------------------------------
    # ABRIR CAIXA
    # ----------------------------------------------------------

    def case_contents(self, collection_id):
        """O que pode sair da caixa, com a chance de cada item: lista de (Skin_Catalog, chance).
        Usado na tela de abertura (prévia do conteúdo e cartões da roleta)."""
        try:
            items = self.collection_dao.get_items(collection_id)
            return drop_table(items, {item.rarity_id: item.rarity.probability for item in items})
        except ValueError as e:
            self.view.show_message(str(e), False)
        except Exception:
            logger.exception("Falha ao carregar o conteúdo da caixa")
            self.view.show_message(t("Não foi possível carregar o conteúdo da caixa."), False)
        return []

    def open_case(self, collection_id):
        """Abre 1 caixa e devolve um Drop_Result (ou None se não deu certo).

        Passo a passo (tudo no backend):
        1. pega a tabela de drops da caixa (skins + raridade);
        2. pega as probabilidades oficiais (tabela rarities);
        3. sorteia raridade -> skin -> float (drop_service);
        4. o DAO valida (caixa existe, espaço, chave) e salva tudo numa transação.
        Se qualquer passo falhar, a caixa NÃO é consumida.

        Sucesso não mostra mensagem: a tela de abertura revela o item no fim
        da animação usando o Drop_Result.
        """
        try:
            items = self.collection_dao.get_items(collection_id)
            probabilities = self.rarity_dao.get_probabilities()
            skin, float_value, _wear = draw_drop(items, probabilities, self.rng)

            new_id, skin_price, new_balance, remaining = self.inventory_dao.open_case(
                self.user.id, collection_id, skin.id, float_value
            )

        except ValueError as e:
            self.view.show_message(str(e), False)
            return None

        except Exception:
            logger.exception("Falha ao abrir caixa")
            self.view.show_message(t("Não foi possível abrir a caixa. Verifique a conexão com o banco."), False)
            return None

        self.user.balance = new_balance
        instance = Skin_Instance(new_id, self.user.id, skin.id, float_value, skin_price, skin=skin)
        return Drop_Result(instance, collection_id, new_balance, remaining)

    # ----------------------------------------------------------
    # CAIXA GRÁTIS (saldo abaixo da chave; 1 a cada 10 minutos)
    # ----------------------------------------------------------

    def free_case_wait(self):
        """None = não vale agora (o saldo paga a chave); timedelta(0) = pode abrir;
        timedelta > 0 = quanto falta. A tela usa para mostrar o botão ou a contagem."""
        try:
            balance, last = self.inventory_dao.get_free_case_state(self.user.id)
        except Exception:
            logger.exception("Falha ao consultar a caixa grátis")
            return None
        return free_case_wait(balance, last, self.clock())

    def free_case_contents(self):
        """Tabela [(Skin_Catalog, chance)] da caixa grátis: skins baratas + 1 rara (5%)."""
        try:
            baratas, rara = self.skin_catalog_dao.get_free_case_pool(FREE_CASE_COMMON_COUNT,
                                                                     FREE_CASE_RARE_MIN_PRICE)
            return free_case_table(baratas, rara, FREE_CASE_RARE_CHANCE)
        except ValueError as e:
            self.view.show_message(str(e), False)
        except Exception:
            logger.exception("Falha ao montar a caixa grátis")
            self.view.show_message(t("Não foi possível carregar o conteúdo da caixa."), False)
        return []

    def open_free_case(self, table):
        """Abre a caixa grátis com a tabela mostrada na tela. Devolve Drop_Result ou None.
        Mesmo fluxo da caixa normal: sorteia aqui, o DAO confere a regra e salva."""
        try:
            skin, float_value, _wear = draw_from_table(table, self.rng)
            new_id, skin_price, balance = self.inventory_dao.open_free_case(
                self.user.id, skin.id, float_value, self.clock()
            )

        except ValueError as e:
            self.view.show_message(str(e), False)
            return None

        except Exception:
            logger.exception("Falha ao abrir a caixa grátis")
            self.view.show_message(t("Não foi possível abrir a caixa. Verifique a conexão com o banco."), False)
            return None

        self.user.balance = balance
        instance = Skin_Instance(new_id, self.user.id, skin.id, float_value, skin_price, skin=skin)
        return Drop_Result(instance, None, balance, 0)

    # ----------------------------------------------------------
    # SKIN EM DESTAQUE NA HOME
    # ----------------------------------------------------------

    def home_skin(self):
        """(id da skin que ESTÁ no pedestal da Home ou None, foi escolhida pelo jogador?).

        Extras 6: sem escolha, a Home mostra a skin mais valiosa; o inventário
        marca "NA HOME" nela também (antes só marcava a escolhida à mão).
        """
        try:
            instancia, escolhida = self.inventory_dao.get_featured_skin(self.user.id)
        except Exception:
            logger.exception("Falha ao consultar a skin em destaque")
            return None, False
        return (instancia.id if instancia is not None else None), escolhida

    def set_featured(self, skin_instance_id):
        """Coloca a skin no pedestal da Home (None tira). Devolve True/False."""
        try:
            self.inventory_dao.set_featured_skin(self.user.id, skin_instance_id)
        except ValueError as e:
            self.view.show_message(str(e), False)
            return False
        except Exception:
            logger.exception("Falha ao escolher a skin em destaque")
            self.view.show_message(t("Não foi possível salvar a skin em destaque."), False)
            return False
        if skin_instance_id is None:
            self.view.show_message(t("A Home volta a mostrar a sua skin mais valiosa."))
        else:
            self.view.show_message(t("Skin em destaque na Home!"))
        return True

    # ----------------------------------------------------------
    # VENDER SKIN
    # ----------------------------------------------------------

    def sale_quote(self, skin_instance_id):
        """Valor final ANTES de confirmar a venda: (preço de mercado, valor recebido) ou None."""
        try:
            return self.inventory_dao.get_sale_quote(self.user.id, skin_instance_id)
        except ValueError as e:
            self.view.show_message(str(e), False)
        except Exception:
            logger.exception("Falha ao calcular valor de venda")
            self.view.show_message(t("Não foi possível calcular o valor de venda."), False)
        return None

    def sell_skin(self, skin_instance_id):
        """Vende a skin (depois da confirmação na tela). Devolve o valor recebido ou None."""
        try:
            payout, new_balance = self.inventory_dao.sell_skin(self.user.id, skin_instance_id)

        except ValueError as e:
            self.view.show_message(str(e), False)
            return None

        except Exception:
            logger.exception("Falha ao vender skin")
            self.view.show_message(t("Não foi possível concluir a venda."), False)
            return None

        self.user.balance = new_balance
        self.view.show_message(
            t("Vendida por {valor}! Saldo: {saldo}", valor=format_money(payout), saldo=format_money(new_balance))
        )
        return payout
