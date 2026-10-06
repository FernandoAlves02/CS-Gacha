from decimal import Decimal

from app.core.game_rules import SOURCE_ESTIMATED, to_money, wear_label


class Market_Price:
    """Preço atual de uma skin em um desgaste (tabela skin_prices).

    Ex.: "AK-47 | Redline" em Field-Tested custa R$ 75,00 (source "steam").
    avg_7d/avg_30d são colunas reservadas: a Steam não informa médias, então
    ficam None (e variation_7d também). A variação de preço pode ser
    calculada pelo histórico (price_history).
    """

    def __init__(
            self,
            skin_catalog_id,
            wear,
            price,
            avg_7d=None,
            avg_30d=None,
            source=SOURCE_ESTIMATED,
            updated_at=None
    ):
        self._skin_catalog_id = skin_catalog_id
        self._wear = wear
        self._price = to_money(price)
        self._avg_7d = to_money(avg_7d)
        self._avg_30d = to_money(avg_30d)
        self._source = source
        self._updated_at = updated_at

    @property
    def skin_catalog_id(self):
        return self._skin_catalog_id

    @property
    def wear(self):
        return self._wear

    @property
    def wear_label(self):
        return wear_label(self._wear)

    @property
    def price(self):
        return self._price

    @property
    def avg_7d(self):
        return self._avg_7d

    @property
    def avg_30d(self):
        return self._avg_30d

    @property
    def source(self):
        return self._source

    @property
    def is_estimated(self):
        return self._source == SOURCE_ESTIMATED

    @property
    def updated_at(self):
        return self._updated_at

    @property
    def variation_7d(self):
        """Variação (%) do preço atual contra a média de 7 dias. None se não houver média."""
        if not self._avg_7d:
            return None
        variacao = (self._price - self._avg_7d) / self._avg_7d * Decimal("100")
        return variacao.quantize(Decimal("0.1"))

    def __repr__(self):
        return f"Market_Price({self._skin_catalog_id}, {self._wear!r}, {self._price})"
