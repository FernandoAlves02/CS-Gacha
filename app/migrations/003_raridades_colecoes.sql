-- =====================================================================
-- CS GACHA - MIGRAÇÃO 003: raridades das coleções de mapa
-- Rode UMA vez no banco que você já tem (não apaga nada; pode rodar de novo
-- sem problema). Necessária antes de: python tools/sync_market.py --todas --colecoes
--
-- As skins das coleções de mapa (que não saem de caixa) usam 3 raridades que
-- as caixas não têm. A chance é 0 porque elas nunca saem em abertura: as
-- skins dessas raridades aparecem só no MERCADO.
-- =====================================================================
use csgacha;

insert into rarities
	(name, probability, color)
values
	('Consumer Grade',   0.0000, '#b0c3d9'),
	('Industrial Grade', 0.0000, '#5e98d9'),
	('Contraband',       0.0000, '#e4ae39')
on duplicate key update
	color = values(color);

-- Conferência: devem aparecer 8 raridades.
select id, name, probability, color from rarities order by id;
