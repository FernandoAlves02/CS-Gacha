"""Caminhos de pastas do projeto, definidos em um único lugar.

Todos os caminhos são calculados a partir da localização DESTE arquivo,
então funcionam não importa de qual pasta o programa for iniciado
(python main.py, python tools/sync_market.py, etc.).
"""
import re
from pathlib import Path

# app/core/paths.py -> sobe 2 níveis -> raiz do projeto
PROJECT_ROOT = Path(__file__).resolve().parents[2]

ASSETS_DIR = PROJECT_ROOT / "app" / "assets"
UI_DIR = ASSETS_DIR / "ui"            # imagens da interface (fundo, campos, botões, ícones)
FONTS_DIR = ASSETS_DIR / "fonts"      # fontes .otf usadas nos textos
ITEM_IMAGES_DIR = ASSETS_DIR / "items"  # imagens das skins/caixas baixadas pelo importador

TOOLS_CACHE_DIR = PROJECT_ROOT / "tools" / "cache"  # cópia local das respostas da API


def item_image_path(api_id):
    """Caminho da imagem local de uma skin/caixa (pode ainda não existir).

    O id da API pode ter caracteres que o Windows não aceita em nome de
    arquivo (ex.: "|"), então trocamos tudo que não for letra/número por "_".
    """
    nome_seguro = re.sub(r"[^A-Za-z0-9_-]", "_", str(api_id))
    return ITEM_IMAGES_DIR / f"{nome_seguro}.png"
