-- =====================================================================
-- CS GACHA - SCRIPT DML (CARGA INICIAL) - VERSÃO 2
-- Rode DEPOIS do schema.sql. As caixas, skins e preços NÃO ficam aqui:
-- eles vêm da API pelo importador (python tools/sync_market.py).
-- =====================================================================
use csgacha;

-- 1. RARIDADES (probabilidades oficiais do CS + cor usada na interface)
--    A soma das probabilidades é 1.0000 (100%).
insert into rarities
	(id, name, probability, color)
values
	(1, 'Mil-Spec Grade', 0.7992, '#4b69ff'),
	(2, 'Restricted',     0.1598, '#8847ff'),
	(3, 'Classified',     0.0320, '#d32ce6'),
	(4, 'Covert',         0.0064, '#eb4b4b'),
	(5, 'Special Item',   0.0026, '#e4ae39');

--    Raridades que só existem nas coleções de mapa (não saem de caixa, por
--    isso a chance é 0): as skins delas aparecem só no mercado. (migração 003)
insert into rarities
	(id, name, probability, color)
values
	(6, 'Consumer Grade',   0.0000, '#b0c3d9'),
	(7, 'Industrial Grade', 0.0000, '#5e98d9'),
	(8, 'Contraband',       0.0000, '#e4ae39');

-- 2. USUÁRIO DE TESTES
--    Login: testes (ou teste@teste.com)  |  Senha: teste123
--    A senha fica guardada como hash no formato salt$sha256 (Password_Utils).
insert into users
	(username, password, email, balance)
values
	('testes', '5e1c8a0b7d3f4926a1b0c3d4e5f60718$a48411d46574128cba7c164fa16eb5aced19d8292136dd284b11a34d8e342f7f', 'teste@teste.com', 500.00);

-- 3. ARMAS BASE (DEFAULT / SEM SKIN)
--    Ficam no catálogo como referência (eram do EQUIPAMENTO, que foi cortado).
--    Não pertencem a nenhuma caixa e não têm preço: nunca saem em drop
--    e nunca aparecem no mercado. Também NÃO entram mais no inventário
--    do usuário de testes (no CS as armas padrão não ocupam o inventário).
insert into skins_catalog
	(name, base_weapon, rarity_id, image_url, model_3d_url, min_float, max_float)
values
	('Glock-18 (Default)', 'Glock-18', 1, null, null, 0.000000000, 0.000000000),
	('USP-S (Default)', 'USP-S', 1, null, null, 0.000000000, 0.000000000),
	('P2000 (Default)', 'P2000', 1, null, null, 0.000000000, 0.000000000),
	('Dual Berettas (Default)', 'Dual Berettas', 1, null, null, 0.000000000, 0.000000000),
	('P250 (Default)', 'P250', 1, null, null, 0.000000000, 0.000000000),
	('Five-SeveN (Default)', 'Five-SeveN', 1, null, null, 0.000000000, 0.000000000),
	('Tec-9 (Default)', 'Tec-9', 1, null, null, 0.000000000, 0.000000000),
	('CZ75-Auto (Default)', 'CZ75-Auto', 1, null, null, 0.000000000, 0.000000000),
	('Desert Eagle (Default)', 'Desert Eagle', 1, null, null, 0.000000000, 0.000000000),
	('R8 Revolver (Default)', 'R8 Revolver', 1, null, null, 0.000000000, 0.000000000),
	('MAC-10 (Default)', 'MAC-10', 1, null, null, 0.000000000, 0.000000000),
	('MP9 (Default)', 'MP9', 1, null, null, 0.000000000, 0.000000000),
	('MP7 (Default)', 'MP7', 1, null, null, 0.000000000, 0.000000000),
	('MP5-SD (Default)', 'MP5-SD', 1, null, null, 0.000000000, 0.000000000),
	('UMP-45 (Default)', 'UMP-45', 1, null, null, 0.000000000, 0.000000000),
	('P90 (Default)', 'P90', 1, null, null, 0.000000000, 0.000000000),
	('PP-Bizon (Default)', 'PP-Bizon', 1, null, null, 0.000000000, 0.000000000),
	('Nova (Default)', 'Nova', 1, null, null, 0.000000000, 0.000000000),
	('XM1014 (Default)', 'XM1014', 1, null, null, 0.000000000, 0.000000000),
	('Sawed-Off (Default)', 'Sawed-Off', 1, null, null, 0.000000000, 0.000000000),
	('MAG-7 (Default)', 'MAG-7', 1, null, null, 0.000000000, 0.000000000),
	('M249 (Default)', 'M249', 1, null, null, 0.000000000, 0.000000000),
	('Negev (Default)', 'Negev', 1, null, null, 0.000000000, 0.000000000),
	('Galil Ar (Default)', 'Galil Ar', 1, null, null, 0.000000000, 0.000000000),
	('FAMAS (Default)', 'FAMAS', 1, null, null, 0.000000000, 0.000000000),
	('AK-47 (Default)', 'AK-47', 1, null, null, 0.000000000, 0.000000000),
	('M4A4 (Default)', 'M4A4', 1, null, null, 0.000000000, 0.000000000),
	('M4A1-S (Default)', 'M4A1-S', 1, null, null, 0.000000000, 0.000000000),
	('AUG (Default)', 'AUG', 1, null, null, 0.000000000, 0.000000000),
	('SG 553 (Default)', 'SG 553', 1, null, null, 0.000000000, 0.000000000),
	('SSG 08 (Default)', 'SSG 08', 1, null, null, 0.000000000, 0.000000000),
	('AWP (Default)', 'AWP', 1, null, null, 0.000000000, 0.000000000),
	('G3SG1 (Default)', 'G3SG1', 1, null, null, 0.000000000, 0.000000000),
	('SCAR-20 (Default)', 'SCAR-20', 1, null, null, 0.000000000, 0.000000000);
