use csgacha;

-- 1. CARGA DE RARIDADES (Obrigatório para o catálogo funcionar)
insert into rarities
	(id, name, probability)
values
	(1, 'Mil-Spec Grade', 0.7992),
	(2, 'Restricted', 0.1598),
	(3, 'Classified', 0.0320),
	(4, 'Covert', 0.0064),
	(5, 'Special Item', 0.0026);

-- 2. CRIAÇÃO DO USUÁRIO DE TESTES
-- Login: teste@teste.com  |  Senha: teste123
-- (a senha é guardada como hash no formato salt$sha256, igual ao Password_Utils)
insert into users
	(username, password, email, balance)
values
	('testes', '5e1c8a0b7d3f4926a1b0c3d4e5f60718$a48411d46574128cba7c164fa16eb5aced19d8292136dd284b11a34d8e342f7f', 'teste@teste.com', 500.00);

-- 3. CARGA DAS ARMAS BASES (DEFAULT / SEM SKIN)
insert into skins_catalog
	(name, base_weapon, collection_id, rarity_id, image_url, model_3d_url, min_float, max_float)
values
	('Glock-18 (Default)', 'Glock-18', null, 1, null, null, 0.000000000, 0.000000000),
	('USP-S (Default)', 'USP-S', null, 1, null, null, 0.000000000, 0.000000000),
	('P2000 (Default)', 'P2000', null, 1, null, null, 0.000000000, 0.000000000),
	('Dual Berettas (Default)', 'Dual Berettas', null, 1, null, null, 0.000000000, 0.000000000),
	('P250 (Default)', 'P250', null, 1, null, null, 0.000000000, 0.000000000),
	('Five-SeveN (Default)', 'Five-SeveN', null, 1, null, null, 0.000000000, 0.000000000),
	('Tec-9 (Default)', 'Tec-9', null, 1, null, null, 0.000000000, 0.000000000),
	('CZ75-Auto (Default)', 'CZ75-Auto', null, 1, null, null, 0.000000000, 0.000000000),
	('Desert Eagle (Default)', 'Desert Eagle', null, 1, null, null, 0.000000000, 0.000000000),
	('R8 Revolver (Default)', 'R8 Revolver', null, 1, null, null, 0.000000000, 0.000000000),
	('MAC-10 (Default)', 'MAC-10', null, 1, null, null, 0.000000000, 0.000000000),
	('MP9 (Default)', 'MP9', null, 1, null, null, 0.000000000, 0.000000000),
	('MP7 (Default)', 'MP7', null, 1, null, null, 0.000000000, 0.000000000),
	('MP5-SD (Default)', 'MP5-SD', null, 1, null, null, 0.000000000, 0.000000000),
	('UMP-45 (Default)', 'UMP-45', null, 1, null, null, 0.000000000, 0.000000000),
	('P90 (Default)', 'P90', null, 1, null, null, 0.000000000, 0.000000000),
	('PP-Bizon (Default)', 'PP-Bizon', null, 1, null, null, 0.000000000, 0.000000000),
	('Nova (Default)', 'Nova', null, 1, null, null, 0.000000000, 0.000000000),
	('XM1014 (Default)', 'XM1014', null, 1, null, null, 0.000000000, 0.000000000),
	('Sawed-Off (Default)', 'Sawed-Off', null, 1, null, null, 0.000000000, 0.000000000),
	('MAG-7 (Default)', 'MAG-7', null, 1, null, null, 0.000000000, 0.000000000),
	('M249 (Default)', 'M249', null, 1, null, null, 0.000000000, 0.000000000),
	('Negev (Default)', 'Negev', null, 1, null, null, 0.000000000, 0.000000000),
	('Galil Ar (Default)', 'Galil Ar', null, 1, null, null, 0.000000000, 0.000000000),
	('FAMAS (Default)', 'FAMAS', null, 1, null, null, 0.000000000, 0.000000000),
	('AK-47 (Default)', 'AK-47', null, 1, null, null, 0.000000000, 0.000000000),
	('M4A4 (Default)', 'M4A4', null, 1, null, null, 0.000000000, 0.000000000),
	('M4A1-S (Default)', 'M4A1-S', null, 1, null, null, 0.000000000, 0.000000000),
	('AUG (Default)', 'AUG', null, 1, null, null, 0.000000000, 0.000000000),
	('SG 553 (Default)', 'SG 553', null, 1, null, null, 0.000000000, 0.000000000),
	('SSG 08 (Default)', 'SSG 08', null, 1, null, null, 0.000000000, 0.000000000),
	('AWP (Default)', 'AWP', null, 1, null, null, 0.000000000, 0.000000000),
	('G3SG1 (Default)', 'G3SG1', null, 1, null, null, 0.000000000, 0.000000000),
	('SCAR-20 (Default)', 'SCAR-20', null, 1, null, null, 0.000000000, 0.000000000);

-- 4. VINCULAR AS ARMAS BASES AO INVENTÁRIO DO USUÁRIO DE TESTES
insert into skins_instance
	(skin_price, float_value, user_id, skin_catalog_id)
values
	(0.00, 0.000000000, 1, 1),
	(0.00, 0.000000000, 1, 2),
	(0.00, 0.000000000, 1, 3),
	(0.00, 0.000000000, 1, 4),
	(0.00, 0.000000000, 1, 5),
	(0.00, 0.000000000, 1, 6),
	(0.00, 0.000000000, 1, 7),
	(0.00, 0.000000000, 1, 8),
	(0.00, 0.000000000, 1, 9),
	(0.00, 0.000000000, 1, 10),
	(0.00, 0.000000000, 1, 11),
	(0.00, 0.000000000, 1, 12),
	(0.00, 0.000000000, 1, 13),
	(0.00, 0.000000000, 1, 14),
	(0.00, 0.000000000, 1, 15),
	(0.00, 0.000000000, 1, 16),
	(0.00, 0.000000000, 1, 17),
	(0.00, 0.000000000, 1, 18),
	(0.00, 0.000000000, 1, 19),
	(0.00, 0.000000000, 1, 20),
	(0.00, 0.000000000, 1, 21),
	(0.00, 0.000000000, 1, 22),
	(0.00, 0.000000000, 1, 23),
	(0.00, 0.000000000, 1, 24),
	(0.00, 0.000000000, 1, 25),
	(0.00, 0.000000000, 1, 26),
	(0.00, 0.000000000, 1, 27),
	(0.00, 0.000000000, 1, 28),
	(0.00, 0.000000000, 1, 29),
	(0.00, 0.000000000, 1, 30),
	(0.00, 0.000000000, 1, 31),
	(0.00, 0.000000000, 1, 32),
	(0.00, 0.000000000, 1, 33),
	(0.00, 0.000000000, 1, 34);
