from decimal import Decimal

from app.core.game_rules import to_money, wear_from_float, wear_label


class Skin_Instance:
    """Skin que um jogador possui (tabela skins_instance).

    "skin" é o Skin_Catalog correspondente (nome, raridade, imagem...),
    carregado junto pelo DAO para a tela não precisar consultar de novo.
    """

    def __init__(
            self,
            id,
            user_id,
            skin_catalog_id,
            float_value,
            skin_price,
            acquired_at=None,
            skin=None
    ):
        self._id = id
        self._user_id = user_id
        self._skin_catalog_id = skin_catalog_id
        self._float_value = Decimal(str(float_value))
        self._skin_price = to_money(skin_price)
        self._acquired_at = acquired_at
        self._skin = skin

    @property
    def id(self):
        return self._id

    @property
    def user_id(self):
        return self._user_id

    @property
    def skin_catalog_id(self):
        return self._skin_catalog_id

    @property
    def float_value(self):
        return self._float_value

    @property
    def skin_price(self):
        """Valor da skin no momento em que o jogador a obteve."""
        return self._skin_price

    @property
    def acquired_at(self):
        return self._acquired_at

    @property
    def skin(self):
        return self._skin

    @property
    def name(self):
        return self._skin.name if self._skin else f"Skin #{self._skin_catalog_id}"

    @property
    def wear(self):
        """Desgaste oficial calculado pelo float. Ex.: 0.21 -> "Field-Tested"."""
        item_has_wear = self._skin.has_wear if self._skin else True
        return wear_from_float(self._float_value, item_has_wear)

    @property
    def wear_label(self):
        """Desgaste em português. Ex.: "Testada em Campo"."""
        return wear_label(self.wear)

    def __repr__(self):
        return f"Skin_Instance({self._id}, {self.name!r}, float={self._float_value})"
