from decimal import Decimal

from app.core.game_rules import available_wears, has_wear


class Skin_Catalog:
    """Molde de uma skin (tabela skins_catalog). Ex.: "AK-47 | Redline".

    Não é a skin de um jogador: é a "ficha" da skin (nome, raridade, float
    mínimo e máximo). A skin que o jogador possui é o Skin_Instance.
    """

    def __init__(
            self,
            id,
            name,
            base_weapon,
            rarity_id,
            min_float=0,
            max_float=1,
            api_id=None,
            market_name=None,
            image_url=None,
            model_3d_url=None,
            rarity=None
    ):
        self._id = id
        self._name = name
        self._base_weapon = base_weapon
        self._rarity_id = rarity_id
        self._min_float = Decimal(str(min_float))
        self._max_float = Decimal(str(max_float))
        self._api_id = api_id
        self._market_name = market_name
        self._image_url = image_url
        self._model_3d_url = model_3d_url
        self._rarity = rarity          # objeto Rarity (quando o DAO carrega junto)

    @property
    def id(self):
        return self._id

    @property
    def name(self):
        return self._name

    @property
    def base_weapon(self):
        return self._base_weapon

    @property
    def rarity_id(self):
        return self._rarity_id

    @property
    def rarity(self):
        return self._rarity

    @property
    def min_float(self):
        return self._min_float

    @property
    def max_float(self):
        return self._max_float

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
    def model_3d_url(self):
        return self._model_3d_url

    @property
    def has_wear(self):
        """False para itens sem desgaste (faca vanilla: min = max = 0)."""
        return has_wear(self._min_float, self._max_float)

    @property
    def available_wears(self):
        """Desgastes em que esta skin existe (respeitando min/max float)."""
        return available_wears(self._min_float, self._max_float)

    def __repr__(self):
        return f"Skin_Catalog({self._id}, {self._name!r}, rarity={self._rarity_id})"
