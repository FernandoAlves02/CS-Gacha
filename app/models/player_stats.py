from decimal import Decimal


class Player_Stats:
    """Números da "janelinha" de estatísticas da Home.

    Vêm da tabela user_transactions (cada compra, abertura e venda deixa uma
    linha lá, desde a migração 004) e do inventário atual.
    """

    def __init__(self, cases_opened=0, free_cases_opened=0, spent=Decimal("0.00"), earned=Decimal("0.00"),
                 items=0, best_drop=None, best_drop_value=None, cases_opened_everyone=0):
        self.cases_opened = cases_opened              # caixas abertas (com as grátis)
        self.free_cases_opened = free_cases_opened    # só as grátis
        self.spent = spent                            # gasto: caixas, skins e chaves
        self.earned = earned                          # recebido nas vendas
        self.items = items                            # itens no inventário agora
        self.best_drop = best_drop                    # Skin_Catalog do item mais valioso que saiu de caixa
        self.best_drop_value = best_drop_value        # valor dele quando saiu
        self.cases_opened_everyone = cases_opened_everyone   # caixas abertas por TODOS os jogadores

    @property
    def moved(self):
        """Valor movimentado no mercado: o que entrou + o que saiu."""
        return self.spent + self.earned

    def __repr__(self):
        return f"Player_Stats(caixas={self.cases_opened}, gasto={self.spent}, recebido={self.earned})"
