-- =====================================================================
-- CS GACHA - MIGRAÇÃO 004: Home viva e caixa grátis (Extras 4)
-- Rode UMA vez no banco que você já tem (não apaga nada; pode rodar de novo
-- sem problema). Necessária antes de abrir o jogo com o Extras 4: sem ela,
-- comprar, abrir e vender dão erro (as movimentações vão para a tabela nova).
-- Feita para o MariaDB do XAMPP ("add column if not exists" é do MariaDB).
--
-- 1. user_transactions: cada compra, abertura e venda passa a deixar uma
--    linha aqui (estatísticas da Home: caixas abertas, valores movimentados,
--    melhor drop). O que aconteceu ANTES desta migração não entra na conta.
-- 2. users.featured_skin_id: a skin do pedestal da Home (null = a mais valiosa).
-- 3. users.last_free_case_at: hora da última caixa grátis (1 a cada 10 min).
-- =====================================================================
use csgacha;

create table if not exists user_transactions(
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

alter table users
	add column if not exists featured_skin_id int null after balance,
	add column if not exists last_free_case_at datetime null after featured_skin_id;

-- Conferência: devem aparecer as 2 colunas novas e a tabela (com 0 linhas).
show columns from users like '%free%';
show columns from users like 'featured%';
select count(*) as movimentacoes from user_transactions;
