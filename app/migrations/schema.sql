create database if not exists csgacha;

use csgacha;

-- TABELAS SIMPLES (USUARIOS, COLEÇÕES E RARIDADE) --

create table if not exists users(
	id int not null auto_increment,
	username varchar(50) not null unique,
	password varchar(255) not null,
	email varchar(100) not null unique,
	balance decimal(10,2) not null default 0.00,
	primary key (id)
);

create table if not exists collections(
	id int not null auto_increment,
	name varchar(50) not null,
	price_collection decimal(10,2) not null,
	primary key (id)
);

create table if not exists rarities(
	id int not null auto_increment,
	name varchar(50) not null,
	probability decimal(6,4) not null,
	primary key (id)
);

-- SKIN PADRÃO --

create table if not exists skins_catalog(
	id int not null auto_increment,
	name varchar(50) not null,
	base_weapon varchar(50) not null,
	image_url varchar(500) null,
	model_3d_url varchar(500) null,
	min_float decimal(11,9) not null default 0.000000000,
	max_float decimal(11,9) not null default 1.000000000,
	collection_id int null,
	rarity_id int not null,
	primary key (id),
	constraint fk_collection_skin foreign key(collection_id) references collections(id),
	constraint fk_rarity_skin foreign key(rarity_id) references rarities(id)
);

-- INSTANCIAS / INVENTARIO --

create table if not exists collections_instance(
	id int not null auto_increment,
	user_id int not null,
	collection_id int not null,
	primary key (id),
	constraint fk_user_collection_instance foreign key(user_id) references users(id),
	constraint fk_collection_collection_instance foreign key(collection_id) references collections(id)
);

create table if not exists skins_instance(
	id int not null auto_increment,
	skin_price decimal(10,2) not null,
	float_value decimal(11,9) not null,
	user_id int not null,
	skin_catalog_id int not null,
	primary key (id),
	constraint fk_user_skin_instance foreign key(user_id) references users(id),
	constraint fk_skin_catalog_skin_instance foreign key(skin_catalog_id) references skins_catalog(id)
);
