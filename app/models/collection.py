from app.core.game_rules import SOURCE_ESTIMATED, to_money


class Collection:
    """Caixa do catálogo (tabela collections). Ex.: "Chroma Case", R$ 12,30.

    "quantity" só é preenchido quando listamos as caixas do INVENTÁRIO de um
    jogador (quantas daquela caixa ele tem). No mercado ele fica None.
    """

    def __init__(
            self,
            id,
            name,
            price,
            api_id=None,
            market_name=None,
            image_url=None,
            price_source=SOURCE_ESTIMATED,
            price_updated_at=None,
            quantity=None
    ):
        self._id = id
        self._name = name
        self._price = to_money(price)
        self._api_id = api_id
        self._market_name = market_name
        self._image_url = image_url
        self._price_source = price_source
        self._price_updated_at = price_updated_at
        self._quantity = quantity

    @property
    def id(self):
        return self._id

    @property
    def name(self):
        return self._name

    @property
    def price(self):
        return self._price

    @property
    def api_id(self):
        return self._api_id

    @property
    def market_name(self):
        return self._market_name

    @property
    def image_url(self):
        return self._image_url

    @property
    def price_source(self):
        return self._price_source

    @property
    def price_is_estimated(self):
        return self._price_source == SOURCE_ESTIMATED

    @property
    def price_updated_at(self):
        return self._price_updated_at

    @property
    def quantity(self):
        return self._quantity

    @quantity.setter
    def quantity(self, new_quantity):
        self._quantity = new_quantity

    def __repr__(self):
        return f"Collection({self._id}, {self._name!r}, {self._price})"
