from decimal import Decimal


class Rarity:
    """Raridade do CS (tabela rarities). Ex.: Covert, 0.0064, cor #eb4b4b."""

    def __init__(self, id, name, probability, color="#b0c3d9"):
        self._id = id
        self._name = name
        self._probability = Decimal(str(probability))
        self._color = color

    @property
    def id(self):
        return self._id

    @property
    def name(self):
        return self._name

    @property
    def probability(self):
        return self._probability

    @property
    def color(self):
        return self._color

    @property
    def color_rgba(self):
        """Cor no formato do Panda3D (r, g, b, a) de 0 a 1. Ex.: "#eb4b4b" -> (0.92, 0.29, 0.29, 1)."""
        hexa = (self._color or "#b0c3d9").lstrip("#")
        r, g, b = (int(hexa[i:i + 2], 16) / 255 for i in (0, 2, 4))
        return (r, g, b, 1)

    def __repr__(self):
        return f"Rarity({self._id}, {self._name!r}, {self._probability})"
