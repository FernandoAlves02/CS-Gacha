class Drop_Result:
    """Resultado de uma abertura de caixa.

    Todo o cálculo (raridade, skin, float, preço) é feito no backend; a tela
    de abertura recebe só este objeto pronto e apenas desenha a animação
    (regra da documentação: "o front só recebe o resultado").
    """

    def __init__(self, skin_instance, collection_id, new_balance, remaining_cases):
        self._skin_instance = skin_instance      # Skin_Instance já salvo no banco
        self._collection_id = collection_id      # caixa que foi aberta
        self._new_balance = new_balance          # saldo depois de pagar a chave
        self._remaining_cases = remaining_cases  # quantas caixas iguais ainda restam

    @property
    def skin_instance(self):
        return self._skin_instance

    @property
    def skin(self):
        return self._skin_instance.skin

    @property
    def collection_id(self):
        return self._collection_id

    @property
    def new_balance(self):
        return self._new_balance

    @property
    def remaining_cases(self):
        return self._remaining_cases

    @property
    def can_open_another(self):
        """Mostra o botão "abrir outra" só se ainda houver caixa igual."""
        return self._remaining_cases > 0

    def __repr__(self):
        return f"Drop_Result({self._skin_instance!r}, restam={self._remaining_cases})"
