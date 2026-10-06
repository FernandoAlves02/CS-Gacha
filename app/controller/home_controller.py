import logging
from datetime import datetime

from app.core.game_rules import free_case_wait

logger = logging.getLogger(__name__)


class Home_Controller:
    """Dados da HOME: estatísticas da janelinha flutuante e a skin do pedestal.

    Contrato com a tela (view): ela só chama e desenha. Se o banco falhar, a
    Home continua de pé (o cenário 3D é o principal): devolvemos "vazio" e
    registramos o erro no log, sem mensagem na tela.
    """

    def __init__(self, inventory_dao, user, clock=datetime.now):
        self.inventory_dao = inventory_dao
        self.user = user
        self.clock = clock      # hora atual (nos testes, um relógio "de mentira")

    def stats(self):
        """Player_Stats do jogador logado (ou None se não deu para consultar)."""
        try:
            return self.inventory_dao.get_stats(self.user.id)
        except Exception:
            logger.exception("Falha ao carregar as estatísticas da Home")
            return None

    def free_case_wait(self):
        """Caixa grátis: None (não vale), timedelta(0) (pronta) ou quanto falta."""
        try:
            balance, last = self.inventory_dao.get_free_case_state(self.user.id)
        except Exception:
            logger.exception("Falha ao consultar a caixa grátis")
            return None
        return free_case_wait(balance, last, self.clock())

    def featured(self):
        """(Skin_Instance ou None, foi escolhida pelo jogador?) para o pedestal."""
        try:
            return self.inventory_dao.get_featured_skin(self.user.id)
        except Exception:
            logger.exception("Falha ao carregar a skin em destaque")
            return None, False
