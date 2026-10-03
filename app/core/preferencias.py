"""PREFERÊNCIAS do jogador neste computador (Extras 5): moeda, tela cheia, sons e animações.

Ficam num arquivo JSON fora do projeto (pasta do usuário/.cs_gacha/config.json),
junto do idioma.txt do i18n: não vão para o git nem para o banco, porque são
do computador, não da conta (no PC do professor, cada um escolhe as suas).

Arquivo faltando, ilegível ou com valor estranho: vale o padrão e o jogo abre normal.
"""
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

ARQUIVO = Path.home() / ".cs_gacha" / "config.json"

MOEDAS = ("auto", "BRL", "USD")      # auto = segue o idioma (português: R$; inglês: US$)

PADROES = {
    "moeda": "auto",
    "tela_cheia": False,
    "volume_efeitos": 70,            # 0 a 100 (0 = sem som)
    "volume_musica": 40,
    "animacoes": True,               # Home: câmera, janelinha e pedestal se mexendo
}

_valores = dict(PADROES)


def _valido(chave, valor):
    """Confere o tipo e o intervalo de cada preferência."""
    if chave == "moeda":
        return valor in MOEDAS
    if chave in ("tela_cheia", "animacoes"):
        return isinstance(valor, bool)
    if chave in ("volume_efeitos", "volume_musica"):
        return isinstance(valor, int) and not isinstance(valor, bool) and 0 <= valor <= 100
    return False


def carregar():
    """Lê o arquivo (chamado uma vez no main.py). O que faltar ou vier errado fica no padrão."""
    _valores.clear()
    _valores.update(PADROES)
    try:
        dados = json.loads(ARQUIVO.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return                                   # sem arquivo (primeira vez) ou ilegível
    if not isinstance(dados, dict):
        return
    for chave, valor in dados.items():
        if chave in PADROES and _valido(chave, valor):
            _valores[chave] = valor


def obter(chave):
    return _valores[chave]


def definir(chave, valor):
    """Muda uma preferência e salva o arquivo. Valor inválido é ignorado (devolve False)."""
    if chave not in PADROES or not _valido(chave, valor):
        logger.warning("Preferência inválida: %s = %r", chave, valor)
        return False
    _valores[chave] = valor
    try:
        ARQUIVO.parent.mkdir(parents=True, exist_ok=True)
        ARQUIVO.write_text(json.dumps(_valores, indent=2), encoding="utf-8")
    except OSError:
        logger.warning("Não foi possível salvar as preferências em %s", ARQUIVO)
    return True
