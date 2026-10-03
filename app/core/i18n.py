"""Idiomas do jogo: português (padrão) e inglês. Item 8 dos extras.

Como funciona (sem biblioteca nova)
-----------------------------------
- O texto em PORTUGUÊS é a própria chave. t("Saldo insuficiente.") devolve o
  mesmo texto quando o idioma é "pt", e a tradução de i18n_en.TEXTOS_EN quando
  é "en". Assim o código continua legível em português.
- Textos com valores usam {nome}: t("Vendida por {valor}!", valor=...).
- Faltou a tradução? Mostra o português (o jogo não quebra) e avisa no log.
  O teste test_i18n confere que TODO t("...") do código tem tradução.
- Números e datas também mudam: 1.234,56 e 25/12 (pt) / 1,234.56 e 12/25 (en).
  O dinheiro (format_money, em game_rules.py) usa numero() daqui.
- O idioma escolhido fica salvo no computador, fora do projeto
  (pasta do usuário/.cs_gacha/idioma.txt): não vai para o git nem para o banco.
"""
import logging
from datetime import datetime
from pathlib import Path

from app.core.i18n_en import TEXTOS_EN

logger = logging.getLogger(__name__)

IDIOMAS = ("pt", "en")
PADRAO = "pt"
ARQUIVO_PREFERENCIA = Path.home() / ".cs_gacha" / "idioma.txt"

_idioma = PADRAO
_avisados = set()          # textos sem tradução já avisados no log (avisa uma vez só)


def idioma():
    """Idioma atual: "pt" ou "en"."""
    return _idioma


def definir_idioma(codigo, salvar=True):
    """Troca o idioma ("pt" ou "en"). salvar=True guarda a escolha para a próxima vez.
    Quem chama redesenha a tela (os textos são lidos na hora de desenhar)."""
    global _idioma
    if codigo not in IDIOMAS:
        logger.warning("Idioma desconhecido: %s", codigo)
        return
    _idioma = codigo
    if salvar:
        try:
            ARQUIVO_PREFERENCIA.parent.mkdir(parents=True, exist_ok=True)
            ARQUIVO_PREFERENCIA.write_text(codigo, encoding="utf-8")
        except OSError:
            logger.warning("Não foi possível salvar o idioma em %s", ARQUIVO_PREFERENCIA)


def carregar_preferencia():
    """Lê o idioma salvo (chamado uma vez no main.py). Sem arquivo, fica o português."""
    try:
        # utf-8-sig: aceita também o arquivo salvo pelo Bloco de Notas com BOM
        codigo = ARQUIVO_PREFERENCIA.read_text(encoding="utf-8-sig").strip()
    except (OSError, UnicodeError):
        return                      # sem arquivo (ou ilegível): fica o português
    if codigo in IDIOMAS:
        definir_idioma(codigo, salvar=False)


def t(texto, **valores):
    """Traduz um texto escrito em português. Ex.: t("Total") -> "Total";
    t("Página {n}", n=2) -> "Page 2" (em inglês)."""
    if _idioma == "en":
        traducao = TEXTOS_EN.get(texto)
        if traducao is None:
            if texto not in _avisados:
                _avisados.add(texto)
                logger.warning("Sem tradução para o inglês: %r", texto)
        else:
            texto = traducao
    return texto.format(**valores) if valores else texto


def numero(valor, casas=2):
    """Número com separadores do idioma: 1234.5 -> "1.234,50" (pt) | "1,234.50" (en)."""
    texto = f"{valor:,.{casas}f}"                      # padrão do Python: "1,234.50"
    if _idioma == "pt":
        texto = texto.replace(",", "X").replace(".", ",").replace("X", ".")
    return texto


def data(valor, com_ano=False):
    """datetime -> "25/12 08:00" (pt) | "12/25 08:00" (en). Texto/None ficam como estão."""
    if not isinstance(valor, datetime):
        return str(valor or "")
    dia_mes = "%d/%m" if _idioma == "pt" else "%m/%d"
    formato = f"{dia_mes}/%Y %H:%M" if com_ano else f"{dia_mes} %H:%M"
    return valor.strftime(formato)
