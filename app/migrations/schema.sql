-- =====================================================================
-- CS GACHA - SCRIPT DDL (CRIAÇÃO DO BANCO) - VERSÃO 2 (Fases 2 e 3)
-- =====================================================================
-- ATENÇÃO: este script APAGA o banco "csgacha" inteiro e cria de novo.
--          Todas as contas e itens de teste são perdidos.
--          Depois dele, rode o seed_base.sql e o importador
--          (python tools/sync_market.py).
--
-- Compatível com: MariaDB 10.4+ (XAMPP) e MySQL 8.0.16+
--
-- O que mudou em relação à versão 1 (documentação original):
--  1. Banco em utf8mb4: nomes de skins usam "★" e "™".
--  2. skins_catalog perdeu a coluna collection_id e ganhou a tabela
--     collection_items: no CS a mesma skin (ex.: as facas) aparece em
--     várias caixas, então a relação caixa <-> skin é N:N.
--  3. Novas tabelas skin_prices (preço atual por desgaste) e
--     price_history (histórico de preços a cada atualização da API).
--  4. api_id / market_name: ligam nossos registros aos da API e do mercado.
--  5. CHECK de saldo >= 0 e ON DELETE CASCADE nos itens do usuário.
--  6. (Extras 4, migração 004) users.featured_skin_id e users.last_free_case_at,
--     e a tabela user_transactions (estatísticas da Home).
-- =====================================================================

drop database if exists csgacha;

create database csgacha
	default character set utf8mb4
	collate utf8mb4_unicode_ci;

use csgacha;

-- ---------------------------------------------------------------------
-- USUÁRIOS
-- ---------------------------------------------------------------------
create table users(
	id int not null auto_increment,
	username varchar(50) not null unique,
	password varchar(255) not null,
	email varchar(100) not null unique,
	balance decimal(10,2) not null default 0.00,
	featured_skin_id int null,                    -- skin do pedestal da Home (null = a mais valiosa)
	last_free_case_at datetime null,              -- última caixa grátis aberta (1 a cada 10 min)
	primary key (id),
	-- o saldo nunca pode ficar negativo (a regra também está no código)
	constraint chk_users_balance check (balance >= 0)
) engine=InnoDB;

-- ---------------------------------------------------------------------
-- RARIDADES (probabilidade oficial do CS por raridade)
-- ---------------------------------------------------------------------
create table rarities(
	id int not null auto_increment,
	name varchar(50) not null unique,
	probability decimal(6,4) not null,
	color char(7) not null default '#b0c3d9',     -- cor da raridade na interface
	primary key (id)
) engine=InnoDB;

-- ---------------------------------------------------------------------
-- CAIXAS ("collections" = caixa à venda no mercado)
-- ---------------------------------------------------------------------
create table collections(
	id int not null auto_increment,
	api_id varchar(64) null,                      -- id na CSGO-API (ex.: crate-4001)
	name varchar(100) not null,
	market_name varchar(150) null,                -- nome no mercado (ex.: Chroma Case)
	image_url varchar(500) null,
	price_collection decimal(10,2) not null,      -- preço ATUAL da caixa
	price_source varchar(20) not null default 'estimado',
	price_updated_at datetime null,
	primary key (id),
	unique key uk_collections_api (api_id)
) engine=InnoDB;

-- ---------------------------------------------------------------------
-- CATÁLOGO DE SKINS (o "molde" de cada skin)
-- min_float = max_float = 0 significa item SEM desgaste (faca vanilla)
-- ---------------------------------------------------------------------
create table skins_catalog(
	id int not null auto_increment,
	api_id varchar(64) null,                      -- id na CSGO-API (null = arma padrão)
	name varchar(100) not null,                   -- nome exibido (pode ter a fase da Doppler)
	market_name varchar(150) null,                -- nome no mercado, SEM o desgaste
	base_weapon varchar(50) not null,
	image_url varchar(500) null,
	model_3d_url varchar(500) null,
	min_float decimal(11,9) not null default 0.000000000,
	max_float decimal(11,9) not null default 1.000000000,
	rarity_id int not null,
	primary key (id),
	unique key uk_skins_api (api_id),
	constraint fk_rarity_skin foreign key(rarity_id) references rarities(id)
) engine=InnoDB;

-- ---------------------------------------------------------------------
-- CONTEÚDO DE CADA CAIXA (tabela de drops: caixa N <-> N skin)
-- ---------------------------------------------------------------------
create table collection_items(
	collection_id int not null,
	skin_catalog_id int not null,
	primary key (collection_id, skin_catalog_id),
	constraint fk_items_collection foreign key(collection_id) references collections(id),
	constraint fk_items_skin foreign key(skin_catalog_id) references skins_catalog(id)
) engine=InnoDB;

-- ---------------------------------------------------------------------
-- PREÇO ATUAL de cada skin em cada desgaste (atualizado pelo importador)
-- ---------------------------------------------------------------------
create table skin_prices(
	skin_catalog_id int not null,
	wear varchar(20) not null,                    -- Factory New, Minimal Wear, ... ou Not Painted
	price decimal(10,2) not null,
	avg_7d decimal(10,2) null,                    -- reservado: média de 7 dias (a Steam não informa; fica null)
	avg_30d decimal(10,2) null,                   -- reservado: média de 30 dias (idem)
	source varchar(20) not null,                  -- 'steam' ou 'estimado'
	updated_at datetime not null,
	primary key (skin_catalog_id, wear),
	constraint fk_price_skin foreign key(skin_catalog_id) references skins_catalog(id),
	constraint chk_price_positive check (price >= 0)
) engine=InnoDB;

-- ---------------------------------------------------------------------
-- HISTÓRICO DE PREÇOS (uma linha por item a cada atualização da API)
-- skin_catalog_id preenchido = preço de skin | collection_id = preço de caixa
-- ---------------------------------------------------------------------
create table price_history(
	id int not null auto_increment,
	skin_catalog_id int null,
	collection_id int null,
	wear varchar(20) null,
	price decimal(10,2) not null,
	source varchar(20) not null,
	captured_at datetime not null default current_timestamp,
	primary key (id),
	key idx_history_skin (skin_catalog_id, wear, captured_at),
	key idx_history_collection (collection_id, captured_at),
	constraint fk_history_skin foreign key(skin_catalog_id) references skins_catalog(id),
	constraint fk_history_collection foreign key(collection_id) references collections(id)
) engine=InnoDB;

-- ---------------------------------------------------------------------
-- INVENTÁRIO: caixas e skins que cada jogador possui
-- (ON DELETE CASCADE: ao excluir a conta, os itens dela também saem)
-- ---------------------------------------------------------------------
create table collections_instance(
	id int not null auto_increment,
	user_id int not null,
	collection_id int not null,
	acquired_at datetime not null default current_timestamp,
	primary key (id),
	key idx_ci_user (user_id, collection_id),
	constraint fk_user_collection_instance foreign key(user_id) references users(id) on delete cascade,
	constraint fk_collection_collection_instance foreign key(collection_id) references collections(id)
) engine=InnoDB;

create table skins_instance(
	id int not null auto_increment,
	skin_price decimal(10,2) not null,            -- valor da skin no momento em que foi obtida
	float_value decimal(11,9) not null,
	user_id int not null,
	skin_catalog_id int not null,
	acquired_at datetime not null default current_timestamp,
	primary key (id),
	key idx_si_user (user_id),
	constraint fk_user_skin_instance foreign key(user_id) references users(id) on delete cascade,
	constraint fk_skin_catalog_skin_instance foreign key(skin_catalog_id) references skins_catalog(id)
) engine=InnoDB;

-- ---------------------------------------------------------------------
-- MOVIMENTAÇÕES (Extras 4): uma linha por compra, abertura e venda.
-- É daí que saem as estatísticas da Home (caixas abertas, valores
-- movimentados, melhor drop). Gravada na MESMA transação da operação.
-- ---------------------------------------------------------------------
create table user_transactions(
	id int not null auto_increment,
	user_id int not null,
	kind varchar(20) not null,                    -- buy_case | buy_skin | open_case | free_case | sell_skin
	quantity int not null default 1,
	amount decimal(10,2) not null default 0.00,   -- dinheiro movimentado (sempre positivo)
	skin_catalog_id int null,                     -- skin obtida (abertura/compra) ou vendida
	item_value decimal(10,2) null,                -- valor dessa skin no momento
	created_at datetime not null default current_timestamp,
	primary key (id),
	key idx_tr_user (user_id, kind),
	constraint fk_user_transactions foreign key(user_id) references users(id) on delete cascade,
	constraint fk_skin_transactions foreign key(skin_catalog_id) references skins_catalog(id)
) engine=InnoDB;
