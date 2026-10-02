# CS Gacha — Roadmap v2 e Tutorial de Integração (Fases 2 e 3)

> Atualizado em **02/10/2026**. Substitui o roadmap de 01/10.
> Base: Documentação do Projeto, branch `refactoring` e as respostas às decisões D1–D12.
> **Estado conferido em 02/10, 16h15:** o seu PC e o GitHub estão no mesmo commit, `bad0600` ("Fase 3", 12h41), sem nenhuma alteração pendente. Tudo o que veio depois (troca da Skinport pela Steam, coletor contínuo, README em UTF-8, cenário no login e Mirage recortada) está na **correção 4**, que é **cumulativa**: extraia só ela (as 2 partes) e ignore os ZIPs das correções anteriores.
> **Como usar:** siga as seções 7 e 8 na ordem. Cada tarefa tem **Passos**, **Validação** (só marque `[x]` quando passar) e **Se der erro**. A seção 9 explica o código para você conseguir apresentar.

---

## Sumário

1. [Onde estamos](#1-onde-estamos)
2. [Decisões fechadas (D1–D9)](#2-decisões-fechadas-d1d9)
3. [Documentação × Projeto](#3-documentação--projeto-matriz-atualizada)
4. [Arquitetura](#4-arquitetura)
5. [O que mudou no banco (v1 → v2)](#5-o-que-mudou-no-banco-v1--v2)
6. [Arquivos entregues](#6-arquivos-entregues)
7. [Tutorial — Fase 2 (dados reais no banco)](#7-tutorial--fase-2-dados-reais-no-banco)
8. [Tutorial — Fase 3 (backend do gacha + nova tela de login)](#8-tutorial--fase-3-backend-do-gacha--nova-tela-de-login)
9. [Entendendo o código (para a apresentação)](#9-entendendo-o-código-para-a-apresentação)
10. [Fases 4 a 7 (próximos passos)](#10-fases-4-a-7-próximos-passos)
11. [Calendário](#11-calendário)
12. [PC do professor](#12-pc-do-professor)
13. [Riscos e plano B](#13-riscos-e-plano-b)
14. [Solução de problemas](#14-solução-de-problemas)
15. [Fontes](#15-fontes)

---

## 1. Onde estamos

| Fase | Conteúdo | Situação |
|---|---|---|
| 0 | Refatoração, ambiente | ✅ concluída (01/10) |
| 1 | Login e cadastro funcionando no banco | ✅ concluída (01/10) |
| 2 | Catálogo real (caixas, skins, raridades, floats) e preços reais no banco | ✅ catálogo e imagens (02/10) · 🟦 preços reais pela Steam: T2.4 passo 3 |
| 3 | Backend do gacha (sorteio, comprar, abrir, vender, inventário) + nova tela de login | ✅ validada no seu PC (02/10): testes, autoteste 31/31, login |
| 4 | Tela do Mercado (caixas e skins avulsas) | ⏳ próxima |
| 5 | Inventário real, abertura com roleta, venda, detalhes | ⏳ |
| 6 | Home viva (animação), vitrine "equipar", Mirage otimizada | ✅ Mirage recortada e cenário carregando no login (correção 4, 02/10: T3.5) · ⏳ animação e vitrine (D12) |
| 7 | Testes de aceite, documentação, apresentação | ⏳ |
| — | Coletor de preços contínuo para o histórico (D10) | 🟦 **código pronto**: deixar rodando (T2.6) |

**Como o código das Fases 2 e 3 foi validado antes de chegar até você:**

- **66 testes automáticos** (regras, sorteio, controllers, importador e login) passando.
- **Simulação de 200.000 aberturas:** cada raridade ficou a menos de 0,07 ponto percentual da chance oficial, e a distribuição de desgaste saiu em 3/24/33/24/16%.
- **Fluxo completo dos DAOs** rodado num banco de conferência gerado a partir do `schema.sql`: comprar, abrir, vender, comprar skin, preço que mudou, saldo insuficiente, inventário em 1.000, skin de outro jogador, rollback sem consumir a caixa e conexões sempre fechadas. 45 de 45 verificações passaram.
- **Importador** testado com os **dados reais da CSGO-API** vindos do seu PC (6 caixas, 355 skins, 0 avisos) e com a Steam simulada (19 de 19): preço real, item sem anúncio, limite de consultas, sem internet, Ctrl+C e retomada.
- **Tela de login** comparada com o seu mockup (prévia com as mesmas medidas e fontes) e a lógica dela exercitada com um Panda3D simulado (30 de 30).
- **Correção 4 (cenário no login + Mirage recortada):** o carregamento em segundo plano foi exercitado com um Panda3D simulado (46 de 46: modelos terminando fora de ordem, arquivo faltando ou corrompido, jogador entrando antes do fim, envio à placa de vídeo dividido em vários quadros). O mapa recortado foi conferido arquivo por arquivo e comparado com o original em 4 posições de câmera.

### 1.1 Próximos passos (na ordem)

1. Extrair as **2 partes da correção 4** por cima do projeto e fazer a **T3.5** (testar o jogo, commit e push).
2. Deixar o **coletor de preços** rodando (**T2.6**). A primeira passada dele é a mesma etapa de preços da T2.4 (passo 3), então não precisa rodar as duas.
3. **PC do professor** (12.1).

> **O que eu NÃO consegui testar aqui** (meu ambiente não tem internet para pacotes nem MariaDB): a **janela real** do Panda3D, o **MariaDB do XAMPP** e as **APIs reais**. Por isso existem a tarefa **T3.2** (autoteste no seu banco) e a **T3.3** (checklist visual do login). Se algo falhar, copie a mensagem inteira e me mande.

---

## 2. Decisões fechadas (D1–D9)

Cada regra de jogo é **uma constante** em `app/core/game_rules.py`. Para mudar, altere só a linha indicada.

| # | Decisão | Como ficou | Onde muda |
|---|---|---|---|
| **D1** | Drops iguais ao CS | 1) sorteia a **raridade** entre as que existem **naquela caixa**: 79,92% / 15,98% / 3,20% / 0,64% / 0,26% (facas e luvas). Se a caixa não tem alguma raridade, as chances das outras são redistribuídas proporcionalmente. 2) sorteia a **skin**: dentro da raridade, todas têm chance igual. Uma mesma skin (ex.: as facas) pode estar em **várias caixas**: tabela `collection_items` (N:N). | probabilidades: tabela `rarities` |
| **D2** | Limite do inventário | **1.000 itens** (caixas + skins), o limite do CS. A compra é bloqueada com "Inventário cheio!". Abrir caixa continua permitido, porque sai 1 caixa e entra 1 skin (a regra do "−1" da documentação). | `INVENTORY_LIMIT` |
| **D3** | Mercado | Vende **caixas** e **skins avulsas**. Cada desgaste é um anúncio separado, como no mercado da Steam ("AK-47 \| Redline (Field-Tested)"). | — |
| **D4** | Preço real e volátil | Catálogo da **CSGO-API (ByMykel)** e preços **em R$** da **API pública do mercado da Steam** (`priceoverview`, a mesma usada pelo próprio mercado do CS). Preço = mediana das vendas das últimas 24 h ou, sem vendas no dia, o anúncio mais barato. Cada preço consultado atualiza o banco e entra uma linha em `price_history`. *(A Skinport foi descartada: ela bloqueia scripts com uma proteção anti-robô da Cloudflare.)* O jogo lê os preços **do banco**, então funciona **sem internet** na apresentação. Item sem preço na API recebe um **preço estimado** pela raridade e pelo desgaste. | `RARITY_BASE_PRICE`, `WEAR_PRICE_FACTOR` |
| **D5** | Float padrão do CS | Faixas oficiais: FN 0–0,07 · MW 0,07–0,15 · FT 0,15–0,38 · WW 0,38–0,45 · BS 0,45–1. Ao abrir uma caixa, o desgaste sai com **3% / 24% / 33% / 24% / 16%** (dados levantados pela comunidade; a Valve não publica a fórmula) e o valor é encaixado no float mínimo e máximo da skin. | `WEARS` |
| **D6** | Cortes | Fora do escopo: **EQUIPAMENTO, NOTÍCIAS, troca entre jogadores e gráficos avançados**. As armas padrão (do EQUIPAMENTO) continuam no catálogo como referência, mas **não entram mais no inventário** (no CS também não ocupam espaço). | — |
| **D7** (nova) | Chave para abrir caixa | No CS é preciso uma chave (US$ 2,49). Aqui custa **R$ 13,50**, cobrados na abertura. **Por quê:** sem a chave, abrir caixa dá lucro em média (o conteúdo vale mais que a caixa) e a economia quebra (persona José: "valor/custo consistente"). Para desligar: `Decimal("0.00")`. | `KEY_PRICE` |
| **D8** (nova) | Taxa de venda | **15%**, como a Steam. Uma skin de R$ 10,00 rende R$ 8,50. | `SELL_FEE_RATE` |
| **D9** (nova) | Login | O seu mockup tem o campo **"Usuário"**, então o login aceita **nome de usuário OU e-mail**: com "@" busca pelo e-mail, sem "@" busca pelo usuário. Por isso o nome de usuário não pode ter "@". | `Login_Controller.auth` |

### 2.1 Ideias de 02/10 (avaliadas)

| # | Ideia | Como fica | Por quê |
|---|---|---|---|
| **D10** | Histórico de mercado com gráfico e preços mais certos | **Coletor contínuo** (`--so-precos --continuo`) rodando o fim de semana inteiro no seu PC: cada passada (~1 h 20) grava um ponto novo de cada item em `price_history`. Em ~60 h são **~45 pontos por item**, de preço real da Steam. O gráfico entra no Mercado (Fase 4) desenhado com o próprio Panda3D (`LineSegs`), **sem biblioteca nova**. O banco já é o "arquivo" dos dados; não precisa de JSON intermediário. | **Várias instâncias ao mesmo tempo não aceleram:** a Steam limita por IP (cerca de 20 consultas por minuto). Duas instâncias dividem o mesmo limite e só fazem a Steam bloquear antes e por mais tempo. **Dois PCs da mesma casa também não:** a Steam enxerga o IP público da internet (o do roteador), não o da placa de rede, então os dois PCs contam como um só. A Steam tem um endpoint de histórico completo (`pricehistory`), mas ele exige o cookie de login da sua conta: isso contraria o "sem integração com a Steam" da documentação e arrisca a conta se o cookie vazar. **Descartado.** |
| **D11** | Telas mais fiéis ao CS2 + Mirage | As telas novas das Fases 4 e 5 (Mercado, Inventário, Abertura) **já nascem no estilo do CS2**: painéis escuros translúcidos, faixa de cor da raridade nos cards, tipografia e header no padrão da tela de login. Não vale refazer as telas antigas antes, porque elas vão ser substituídas. **Mirage:** eu otimizo o `de_mirage_d.glb`, recortando só a parte do mapa que a câmera do menu enxerga e reduzindo as 704 texturas. A meta é ficar abaixo de 100 MB no total, para **caber no Git** e carregar rápido no PC do professor. Não precisa me enviar: com a pasta liberada eu pego o arquivo direto. | Hoje o mapa tem 103 MB de geometria + 234 MB de texturas, e o Git recusa o arquivo. Carregar tudo isso num PC mais fraco é o maior risco de travar na apresentação. Para carregar `.glb` com animações de forma confiável, entra o `panda3d-gltf` (já listado como opcional no `requirements.txt`). |
| **D12** | Animação na Home e "equipar skin" | **Animação procedural**: câmera passeando devagar pelo cenário, o personagem com um leve movimento de respiração e balanço, e luz e poeira no ar. **Equipar:** no inventário, o botão EQUIPAR põe a skin numa **vitrine na Home** (imagem grande, nome, raridade, float), ao lado do personagem. **Bônus:** a AK-47 3D girando com a animação oficial de inspeção (`inventory_inspect`). | Os personagens `*_spawnpoint.glb` são **estátuas**: sem esqueleto e sem animações, com a arma "colada" no corpo. Animação de esqueleto não é possível neles. A **skin 3D real** na arma também não: a API só traz a imagem 2D de cada skin, e as texturas 3D (padrão + máscaras + desgaste) teriam de ser extraídas do jogo uma a uma. A vitrine entrega a mesma ideia ("minha skin em destaque na Home") com risco baixo. |

**Ordem de prioridade:** MVP (Fases 4 e 5, já no estilo CS2) → coletor rodando em paralelo (custo zero) → gráfico → Home viva (animação) → vitrine "equipar" → otimização da Mirage. Se o tempo apertar, os extras saem nessa ordem, de trás para frente.

### 2.2 Regras novas a partir de agora

- ⚠️ **Nunca mais rode o `schema.sql` no seu PC**: ele apaga o banco **e o histórico de preços** coletado. Mudanças no banco passam a vir como **migração incremental** (`app/migrations/003_....sql`, só `ALTER TABLE`/`CREATE TABLE`), que preserva os dados.
- **Backup antes de qualquer migração** (cmd): `C:\xampp\mysql\bin\mysqldump -u root -p --databases csgacha > backup_csgacha.sql`.
- **Ciclo de validação das telas:** eu não consigo abrir a janela do Panda3D aqui. Você roda e me manda print do que aparecer. *Opcional:* se no fim de semana você deixar o PC ligado com o app do Claude aberto e me der permissão de controle do computador, eu mesmo rodo o jogo e tiro os prints, o que acelera bastante os ajustes de tela.

**Moeda:** reais (R$), porque a Steam devolve os preços em BRL (`currency=7`). Saldo inicial R$ 500,00 (como antes).

**Fora do escopo por enquanto (Won't):** StatTrak™ (10% de chance no CS) e Souvenir. Dá para adicionar depois sem mudar a estrutura.

---

## 3. Documentação × Projeto (matriz atualizada)

Legenda: ✅ pronto · 🟦 pronto no backend (falta a tela) · ⏳ falta

| História da documentação | Backend | Banco | Tela |
|---|---|---|---|
| Criar conta (nome, e-mail, senha; e-mail único) | ✅ | ✅ | ✅ (novo layout) |
| Login | ✅ (usuário ou e-mail) | ✅ | ✅ (novo layout) |
| Ver/editar dados | ✅ `User_Controller.update` | ✅ | ⏳ (Could) |
| Cálculo de probabilidade (backend) | ✅ `drop_service` | ✅ | — |
| Abrir caixa: valida caixa, espaço (−1), "inventário cheio!", não consome se der erro | ✅ `Inventory_DAO.open_case` | ✅ | ⏳ Fase 5 |
| Mostrar só o resultado no front / abrir outra / aceitar | ✅ `Drop_Result` (`can_open_another`) | — | ⏳ Fase 5 |
| Salvar caixas não abertas e itens novos | ✅ | ✅ | — |
| Acessar mercado / ver itens / detalhes | ✅ `Market_Controller` | ✅ | ⏳ Fase 4 |
| Comprar: preço verde/vermelho, saldo, espaço, confirmação | ✅ `can_afford`, `check_purchase`, `buy_case`, `buy_skin` | ✅ | ⏳ Fase 4 |
| Ver inventário / não mostrar itens de outros | ✅ `Inventory_Controller.load` | ✅ | ⏳ Fase 5 |
| Detalhes do item (float, nome, desgaste) | ✅ `Skin_Instance.wear_label` etc. | ✅ | ⏳ Fase 5 |
| Saldo atualizado e nunca negativo | ✅ (transação + `CHECK`) | ✅ | 🟦 header já mostra |
| Vender com valor final e confirmação | ✅ `sale_quote`, `sell_skin` | ✅ | ⏳ Fase 5 |
| "Valores reais" (persona Douglas) | ✅ importador + histórico | ✅ | ⏳ Fase 4 |

---

## 4. Arquitetura

```
┌────────────┐   chama    ┌──────────────┐  usa   ┌──────────────────┐   SQL   ┌────────┐
│   VIEW     │ ─────────▶ │  CONTROLLER  │ ─────▶ │       DAO        │ ──────▶ │ BANCO  │
│ (Panda3D)  │ ◀───────── │ (regra da    │ ◀───── │ (acesso ao banco)│ ◀────── │MariaDB │
│ só desenha │ resultado  │  tela)       │        └──────────────────┘         └────────┘
└────────────┘            └──────┬───────┘                                         ▲
                                 │ usa                                              │
                          ┌──────▼───────┐                              ┌──────────┴──────┐
                          │    CORE      │                              │ tools/          │
                          │ game_rules   │                              │ sync_market.py  │
                          │ drop_service │                              │ (API → banco)   │
                          └──────────────┘                              └─────────────────┘
```

- **View**: só desenha e lê o que o jogador digitou/clicou. Nunca calcula nada.
- **Controller**: recebe a ação da tela, chama o sorteio e os DAOs, trata erros e devolve mensagem ou resultado.
- **Core**: regras puras do jogo (sem banco e sem tela), fáceis de testar.
- **DAO**: todo o SQL. O `Inventory_DAO` faz as operações de dinheiro e itens em **transação**.
- **tools/sync_market.py**: roda fora do jogo e alimenta o banco com dados reais.

**Fluxo de uma abertura de caixa** (o que a documentação pede: cálculo no backend, o front só recebe o resultado):

```mermaid
sequenceDiagram
    participant T as Tela (Fase 5)
    participant C as Inventory_Controller
    participant S as drop_service
    participant D as Inventory_DAO
    participant B as Banco
    T->>C: open_case(id da caixa)
    C->>B: tabela de drops (Collection_DAO.get_items) + probabilidades (Rarity_DAO)
    C->>S: draw_drop(itens, probabilidades)
    S-->>C: skin, float, desgaste
    C->>D: open_case(usuário, caixa, skin, float)
    D->>B: BEGIN · trava o usuário · confere caixa, espaço, chave, item e float
    D->>B: DELETE caixa · UPDATE saldo · INSERT skin · COMMIT
    D-->>C: id da skin, preço, novo saldo, caixas restantes
    C-->>T: Drop_Result (pronto)
    T->>T: anima a roleta parando no item recebido
```

---

## 5. O que mudou no banco (v1 → v2)

| Mudança | Por quê |
|---|---|
| Banco em `utf8mb4` e tabelas `InnoDB` | Nomes de skins têm "★" e "™"; `InnoDB` é necessário para transações e `FOR UPDATE` |
| `skins_catalog.collection_id` **removida** → tabela nova **`collection_items`** (caixa N:N skin) | No CS a mesma faca aparece em várias caixas; com 1:N teríamos de duplicar skins |
| `api_id` e `market_name` em `collections` e `skins_catalog` | Ligam nossos registros à API (importar de novo sem duplicar) e ao nome no mercado (buscar o preço) |
| `rarities.color` | Cor da raridade na interface (azul, roxo, rosa, vermelho, dourado) |
| Tabela **`skin_prices`** (preço atual por skin + desgaste; colunas de média reservadas, a Steam não informa) | Cada desgaste tem preço diferente no mercado real |
| Tabela **`price_history`** | Histórico a cada atualização (variação, gráfico) |
| `collections.price_source` / `price_updated_at` | Saber se o preço é real (`steam`) ou `estimado`, e de quando é |
| `acquired_at` nas instâncias | Ordenar o inventário do mais novo para o mais antigo (como no CS) |
| `CHECK (balance >= 0)` e `ON DELETE CASCADE` | O banco também impede saldo negativo; excluir a conta apaga os itens dela (antes dava erro de chave estrangeira) |
| Seed: armas padrão **fora** do inventário do usuário de teste | EQUIPAMENTO foi cortado; no CS as armas padrão não ocupam o inventário |

```mermaid
erDiagram
    users ||--o{ collections_instance : "tem caixas"
    users ||--o{ skins_instance : "tem skins"
    collections ||--o{ collections_instance : "instância de"
    collections ||--o{ collection_items : "contém"
    skins_catalog ||--o{ collection_items : "aparece em"
    rarities ||--o{ skins_catalog : "classifica"
    skins_catalog ||--o{ skins_instance : "instância de"
    skins_catalog ||--o{ skin_prices : "preço por desgaste"
    skins_catalog ||--o{ price_history : "histórico"
    collections ||--o{ price_history : "histórico"
```

---

## 6. Arquivos entregues

O ZIP espelha a estrutura do projeto: é só extrair **por cima** da pasta do projeto.

| Arquivo | Situação | O que é |
|---|---|---|
| `main.py` | ALTERADO | + janela 1280×720, título e `textures-power-2 none` (sem isso as imagens ficam borradas) |
| `README.md` | REESCRITO | O antigo estava em UTF-16 (o GitHub mostrava "C S - G a c h a"); agora UTF-8, com a instalação |
| `ROADMAP.md` | REESCRITO | Este documento |
| `requirements.txt` | ALTERADO | Comentários; **nenhuma biblioteca nova** (o `brotli` saiu com a Skinport) |
| `.gitignore` | ALTERADO | + `tools/cache/` |
| `app/migrations/schema.sql` | REESCRITO | Banco v2 (seção 5). **Apaga e recria o banco** |
| `app/migrations/seed_base.sql` | REESCRITO | Raridades com cor, usuário de teste, armas padrão |
| `app/core/paths.py` | NOVO | Caminhos das pastas em um lugar só |
| `app/core/game_rules.py` | NOVO | **Regras do jogo** (limite, chave, taxa, desgaste, preço estimado, formato R$) |
| `app/core/drop_service.py` | NOVO | **Sorteio**: tabela de drops, raridade, skin, float |
| `app/models/rarity.py` | NOVO | Raridade (nome, probabilidade, cor) |
| `app/models/collection.py` | NOVO | Caixa (nome, preço; `quantity` no inventário) |
| `app/models/skin_catalog.py` | NOVO | Ficha da skin (nome, raridade, float mínimo e máximo) |
| `app/models/skin_instance.py` | NOVO | Skin do jogador (float, desgaste, valor) |
| `app/models/market_price.py` | NOVO | Preço de mercado (atual, origem, data) |
| `app/models/drop_result.py` | NOVO | Resultado da abertura entregue à tela |
| `app/models/user.py` | ALTERADO | Nome de usuário não pode ter "@" (D9) |
| `app/dao/base_dao.py` | ALTERADO | + `Base_DAO` (conexão, cursor `buffered`) e `Read_Only_DAO` (catálogo). `DAO` continua igual para o `User_DAO` |
| `app/dao/user_dao.py` | ALTERADO | + `get_by_username` |
| `app/dao/rarity_dao.py` | NOVO | Lê raridades e probabilidades |
| `app/dao/collection_dao.py` | NOVO | Caixas, conteúdo (tabela de drops) e histórico |
| `app/dao/skin_catalog_dao.py` | NOVO | Skins, preços por desgaste, anúncios do mercado (busca e paginação) e histórico |
| `app/dao/inventory_dao.py` | NOVO | **Transações**: comprar caixa, abrir, comprar skin, vender; listar o inventário |
| `app/controller/login_controller.py` | ALTERADO | Login por usuário ou e-mail; mensagens novas |
| `app/controller/market_controller.py` | NOVO | Regras da tela do Mercado |
| `app/controller/inventory_controller.py` | NOVO | Regras do Inventário (abrir, vender) |
| `app/view/login_register_view.py` | REESCRITO | Tela no layout do mockup (login + cadastro) |
| `app/assets/ui/*` | NOVO | Fundo, campos, botão (4 estados) e ícones |
| `app/assets/fonts/*` | NOVO | Fonte Inter (Regular e Bold) + licença OFL |
| `tools/sync_market.py` | NOVO | **Importador** da API |
| `app/unit_tests/test_user_flow.py` | ALTERADO | Login por usuário ou e-mail |
| `app/unit_tests/test_gacha_rules.py` | NOVO | Testes de regras e sorteio |
| `app/unit_tests/test_gacha_controllers.py` | NOVO | Testes dos controllers |
| `app/unit_tests/test_sync_market.py` | NOVO | Testes do importador |
| `app/unit_tests/manual_gacha_flow.py` | NOVO | **Autoteste no banco real** |
| `erro_main.txt` | **APAGAR** | Não é erro: é a mensagem normal do Panda3D ao iniciar |

Arquivos **não alterados**: `view_manager.py`, `user_controller.py`, `database.py` (o seu `use_pure=True` foi mantido), `password_utils.py`, `home_view.py`, `inventory_view.py`, `game_view_base.py`, `scene_backdrop.py`, `tools/arma_view.py`, `tools/mapa_view.py` e o protótipo.

### 6.1 Correção 4 (02/10, tarde): cenário carregando no login + Mirage recortada

Entregue em **2 partes** (o arquivo único passava do limite de envio): `cs-gacha-correcao-4-parte1.zip` (código + `de_mirage_menu.glb`) e `cs-gacha-correcao-4-parte2.zip` (as 264 texturas do mapa). É **cumulativa** em relação ao commit `bad0600`: também traz as correções 2 e 3.

| Arquivo | Situação | O que é |
|---|---|---|
| `tools/sync_market.py` | ALTERADO (correções 2 e 3) | Preços pela **Steam** no lugar da Skinport (bloqueada pela Cloudflare), retomada, aviso `ATENÇÃO` só quando algo falhou de verdade e o modo `--continuo` (T2.6) |
| `app/unit_tests/test_sync_market.py` | ALTERADO (correções 2 e 3) | Testes da Steam e do modo contínuo |
| `app/core/game_rules.py` | ALTERADO (correção 2) | `SOURCE_API = "steam"` |
| `app/models/market_price.py` | ALTERADO (correção 2) | Comentário: a Steam não informa médias de 7/30 dias |
| `app/migrations/schema.sql` | ALTERADO (correção 2) | **Só comentários** (`'steam'` no lugar de `'skinport'`). **Não rode de novo** no seu PC (regra 2.2) |
| `README.md` | ALTERADO | Convertido para UTF-8 (o do GitHub ainda está em UTF-16) |
| `ROADMAP.md` | ALTERADO | Este documento |
| `app/assets/maps/mirage_menu/` | NOVO | **Mirage recortada** (265 arquivos, ~50 MB, contra 337 MB do original): só o que a câmera da Home enxerga (com folga para a animação da Fase 6), sem as malhas de ferramenta do editor e com texturas reduzidas (cor até 1024 px, detalhe até 512 px). **Vai no Git** (nenhum arquivo passa de 25 MB). |
| `app/view/scene_backdrop.py` | ALTERADO | Carrega mapa e personagem **em segundo plano** (`loadModel` com `callback`) e envia o cenário à placa de vídeo **aos poucos** enquanto o login está aberto. Usa a Mirage recortada; se ela não existir, cai no `de_mirage_d.glb` completo. |
| `app/view/login_register_view.py` | ALTERADO | Meio segundo depois de aparecer, pede o pré-carregamento do cenário (`TASK_PRECARREGAR`). |
| `app/view/home_view.py` | ALTERADO | Se o jogador entrar antes do fim, mostra **"Carregando cenário..."** até o mapa aparecer. |
| `requirements.txt` | ALTERADO | `panda3d-simplepbr` passa a ser instalado sempre: o `scene_backdrop.py` já usava, e sem ele o PC do professor mostraria o cenário com outra iluminação. |

---

## 7. Tutorial — Fase 2 (dados reais no banco)

### T2.1 Trazer os arquivos para o projeto (10 min)

**Passos**
1. Abra o terminal na pasta do projeto e confira que está tudo salvo:
   ```bat
   cd caminho\do\CS-Gacha
   git checkout refactoring
   git pull
   git status
   ```
   `git status` precisa dizer *nothing to commit, working tree clean*. Se não disser, faça commit do que tem antes.
2. Extraia o ZIP **por cima** da pasta do projeto: botão direito no `cs-gacha-fase2-3.zip` → **Extrair tudo...** → em *Destino*, **apague o final `\cs-gacha-fase2-3`** e deixe só a pasta do projeto (ex.: `C:\...\CS-Gacha`) → **Extrair** → **Substituir os arquivos no destino**. Por padrão o Windows cria uma subpasta, e aí os arquivos não entram no projeto. Depois de extrair, `main.py` e `README.md` devem estar na mesma pasta de antes, e não dentro de `cs-gacha-fase2-3\`.
3. Apague o log que foi para o Git por engano:
   ```bat
   git rm erro_main.txt
   ```
4. Veja o que mudou:
   ```bat
   git status
   ```

**Validação**
- [ ] `git status` mostra os arquivos da tabela da seção 6 (modificados e novos) e `erro_main.txt` como *deleted*.
- [ ] Existem as pastas `app/assets/ui` (12 arquivos) e `app/assets/fonts` (3 arquivos).

### T2.2 Instalar a dependência nova (2 min)

**Passos**
```bat
.venv\Scripts\activate
pip install -r requirements.txt
```
Nenhuma biblioteca nova é necessária. Se você instalou o `brotli` na versão anterior, pode remover: `pip uninstall brotli`.

**Validação**
- [ ] `python -c "import panda3d, mysql.connector, dotenv; print('ok')"` imprime `ok`.

### T2.3 Recriar o banco na versão 2 (10 min)

> ⚠️ O `schema.sql` **apaga** o banco `csgacha` e cria de novo. As contas criadas nos testes de ontem somem (o usuário `testes` volta pelo seed).

**Passos (DBeaver)**
1. Ligue o MySQL no painel do XAMPP.
2. No DBeaver, conecte como `root`, abra `app/migrations/schema.sql` e execute **o script inteiro** com **Alt+X** ("Executar script"). Ctrl+Enter executa só uma linha.
3. Abra `app/migrations/seed_base.sql` e execute com **Alt+X**.
4. Se o DBeaver estiver em modo de *commit manual*, clique em **Commit**.

*Alternativa (phpMyAdmin):* aba **Importar** → escolha o arquivo → **Executar**. Se aparecer "DROP DATABASE statements are disabled", apague o banco antes em *Operações → Remover o banco de dados* e importe de novo.

**Validação** (rode no DBeaver):
```sql
use csgacha;
show tables;                                   -- 9 tabelas
select name, probability, color from rarities; -- 5 linhas; soma = 1.0000
select username, email, balance from users;    -- testes | teste@teste.com | 500.00
select count(*) from skins_catalog;            -- 34 (armas padrão)
select count(*) from skins_instance;           -- 0  (o inventário começa vazio)
```
- [ ] Tudo igual aos comentários acima.

**Se der erro:** "Access denied" no jogo depois disso → o usuário do `.env` perdeu a permissão. Rode como root:
```sql
grant all privileges on csgacha.* to 'csgacha_app'@'localhost';
flush privileges;
```
(troque `csgacha_app` pelo usuário do seu `.env`; se você usa `root` no `.env`, não precisa).

### T2.4 Importar caixas, skins e preços reais (catálogo 5 min + preços ~1 h 20)

> **Se você já fez a T2.4 com a versão anterior (Skinport):** o catálogo e as imagens já estão certos no seu banco. Depois de extrair a correção 4 (que traz a troca para a Steam), rode **só** a etapa de preços (passo 3) ou já deixe a T2.6 rodando.

**Passos**
1. Veja os nomes das caixas disponíveis (opcional):
   ```bat
   python tools/sync_market.py --listar
   ```
2. Importe as caixas padrão **com as imagens**:
   ```bat
   python tools/sync_market.py --imagens --sem-precos
   ```
   As caixas padrão são: *CS:GO Weapon Case, Chroma Case, Glove Case, Fracture Case, Dreams & Nightmares Case, Kilowatt Case*. Para trocar, edite a lista `CAIXAS_PADRAO` no topo de `tools/sync_market.py` ou use `--caixas "Nome 1" "Nome 2"`. Todo item já fica com um **preço estimado**, então o jogo funciona a partir daqui.
3. Busque os **preços reais** na Steam:
   ```bat
   python tools/sync_market.py --so-precos
   ```
   - A Steam responde **um item por vez** e aceita cerca de 20 consultas por minuto, por isso o script espera 3,2 s entre elas. Para as 6 caixas são ~1.436 preços: **cerca de 1 h 20**.
   - A ordem foi pensada para o jogo: primeiro as **caixas**, depois as skins **mais comuns** (as que mais saem nas aberturas) e por último facas e luvas. Em **~25 min** as caixas e as ~420 skins de armas já estão com preço real.
   - Pode deixar rodando num terminal enquanto você trabalha em outra coisa.
   - **Ctrl+C para a qualquer momento sem perder nada:** o progresso é salvo a cada 10 itens, e rodar `--so-precos` de novo continua do que falta.
   - Se a Steam pedir uma pausa (HTTP 429), o script espera 65 s sozinho. Depois de 3 pausas seguidas ele para e salva, e aí é só rodar de novo depois de uns 10 minutos.
   - Para rodar em partes: `python tools/sync_market.py --so-precos --limite 300`.

**O que você vai ver** no passo 3 (os números variam):
```
1/4 Catálogo: pulado (--so-precos).
2/4 Gravação do catálogo: pulada.
3/4 Consultando 1436 preços em R$ no mercado da Steam (~77 min).
    Pode interromper com Ctrl+C a qualquer momento: o progresso fica salvo e
    a próxima execução continua do que falta.
  [10/1436] P90 | Grim (Battle-Scarred): R$ 1,05  (faltam ~79 min)
  [20/1436] ...
    1402 preços reais gravados | 34 sem anúncio na Steam | 0 falhas de rede
4/4 Imagens: pulado (use --imagens para baixar).

Pronto!
```
"Sem anúncio" é normal: alguns itens raros não têm nenhum à venda naquele momento e continuam com o preço estimado.

**Validação** (DBeaver):
```sql
-- 1) caixas, preço e quantidade de itens
select c.name, c.price_collection, c.price_source, count(ci.skin_catalog_id) as itens
from collections c left join collection_items ci on ci.collection_id = c.id
group by c.id, c.name, c.price_collection, c.price_source;

-- 2) quantos itens de cada raridade numa caixa
select r.name, count(*) as itens
from collection_items ci
join skins_catalog s on s.id = ci.skin_catalog_id
join rarities r on r.id = s.rarity_id
where ci.collection_id = (select id from collections where name = 'Chroma Case')
group by r.name;

-- 3) origem dos preços (depois da etapa da Steam, a maioria deve ser 'steam')
select source, count(*) from skin_prices group by source;

-- 4) histórico gravado
select count(*) from price_history;
```
- [ ] A saída da etapa de preços **não** tem `! Parou antes do fim` nem o aviso `ATENÇÃO`. Se tiver, me mande a linha inteira: ela traz o motivo exato.
- [ ] 6 caixas, todas com itens e `price_source = steam`. O preço da caixa fica **diferente** de 5,00, que é o valor estimado.
- [ ] A consulta 2 mostra as 5 raridades (ou menos, se a caixa não tiver alguma).
- [ ] A consulta 3 mostra principalmente `steam` (o resto, `estimado`, são itens sem anúncio).
- [ ] A pasta `app/assets/items` tem as imagens `.png` (361 com as caixas padrão).
- [ ] Rodar o importador **de novo** não duplica nada (repita a consulta 1) e o `price_history` cresce.

**Se der erro:** veja a seção 14.

### T2.5 Commit (2 min)

```bat
git add -A
git commit -m "Fase 2: banco v2, catalogo e precos reais via API, importador"
git push
```
- [ ] Push sem erro. As imagens de `app/assets/items` vão juntas: assim o PC do professor não precisa baixá-las.

---

### T2.6 Deixar o coletor de preços rodando no fim de semana (D10)

**Passos**
1. Em **Configurações do Windows > Sistema > Energia**, deixe o computador **sem suspender** (tela pode desligar).
2. Deixe o **MySQL do XAMPP ligado**.
3. Num terminal separado (com o `.venv` ativo), rode e deixe aberto:
   ```bat
   python tools/sync_market.py --so-precos --continuo
   ```
   Ele faz uma passada completa (~1 h 20), espera 5 min e começa outra. Se a Steam limitar, espera 15 min; se a internet cair, espera 5 min e continua sozinho. **Ctrl+C** encerra sem perder nada.
4. Pode trabalhar no projeto ao mesmo tempo (jogo, testes e autoteste usam o mesmo banco sem conflito). Só **não rode o `schema.sql`** (regra 2.2).

**Validação** (DBeaver, depois de algumas horas):
```sql
-- pontos de histórico por item (deve crescer a cada passada)
select s.name, h.wear, count(*) as pontos, min(h.price) as minimo, max(h.price) as maximo
from price_history h join skins_catalog s on s.id = h.skin_catalog_id
group by s.name, h.wear order by pontos desc limit 20;

-- histórico das caixas
select c.name, count(*) as pontos, min(h.captured_at), max(h.captured_at)
from price_history h join collections c on c.id = h.collection_id group by c.name;
```
- [ ] O número de pontos cresce a cada passada.
- [ ] As linhas `=== Passada N` aparecem no terminal com horário.

## 8. Tutorial — Fase 3 (backend do gacha + nova tela de login)

### T3.1 Testes automáticos (2 min)

**Passos** (na raiz do projeto, com o `.venv` ativo):
```bat
python -m unittest app.unit_tests.test_user_flow app.unit_tests.test_gacha_rules app.unit_tests.test_gacha_controllers app.unit_tests.test_sync_market
```
**Validação**
- [ ] Termina com `Ran 66 tests` e `OK`, sem nenhum traceback no meio.

> O teste `test_erro_inesperado_nao_derruba_a_tela` simula o banco caindo de propósito. Ele captura o log do erro com `assertLogs`, para o traceback não aparecer na saída como se fosse uma falha.

### T3.2 Autoteste no banco real (3 min)

**Passos**
```bat
python -m app.unit_tests.manual_gacha_flow
```
O script cria um usuário temporário, compra uma caixa, abre, vende, compra uma skin avulsa e testa saldo insuficiente, chave e inventário cheio. Depois mostra **10.000 sorteios simulados** comparados com as chances oficiais e apaga o usuário temporário.

**Validação**
- [ ] Última linha: `TUDO CERTO: 31 verificações passaram.` (o número pode variar um pouco).
- [ ] A tabela "esperado × obtido" mostra valores próximos. **Guarde um print para a apresentação.**
- [ ] Os preços do autoteste são reais: a caixa usada **não** custa R$ 5,00 e a skin do drop não custa exatamente o valor estimado (ex.: Mil-Spec FN = R$ 1,28; Special Item BS = R$ 1.125,00). Se custarem, os preços estão estimados: volte à T2.4.
- [ ] A linha "Desgaste" não precisa bater com 3/24/33/24/16%: cada skin tem float mínimo e máximo próprios, e o valor é encaixado nesse intervalo. Uma skin de 0,00 a 0,50, por exemplo, nunca sai Battle-Scarred.
- [ ] `select username from users;` mostra só as contas reais (o `autoteste_...` sumiu).

**Se der erro:** mande a saída **inteira**. A lista "FALHARAM" diz exatamente qual regra quebrou.

### T3.3 Conferir a nova tela de login (5 min)

**Passos**
```bat
python main.py
```
**Validação** (marque cada um):
- [ ] Janela 1280×720 com o fundo da arte, nítido, e o formulário embaixo do logo, igual ao mockup.
- [ ] O cursor já começa no campo **Usuário**, com borda laranja.
- [ ] Os textos de exemplo "Usuário" e "Senha" somem ao digitar e voltam ao apagar.
- [ ] **TAB** passa para o próximo campo; **Shift+TAB** volta.
- [ ] O **olho** mostra e esconde a senha.
- [ ] O botão **ENTRAR** muda de cor ao passar o mouse e ao clicar.
- [ ] Entrar com `testes` / `teste123` vai para a Home e mostra o saldo. Entrar com `teste@teste.com` também funciona.
- [ ] Senha errada mostra **"Usuário ou senha inválidos."** em vermelho.
- [ ] **Registrar** mostra 3 campos (Usuário, E-mail, Senha) e o botão **CADASTRAR**.
- [ ] Cadastro com senha curta mostra o erro; cadastro válido volta ao login com o usuário preenchido e a mensagem verde.
- [ ] Redimensionar ou maximizar a janela mantém o formulário alinhado ao logo.
- [ ] **SAIR** na Home volta ao login.

**Se algo estiver diferente:** tire um print e mande junto com o que apareceu no terminal (avisos começando com `WARNING` dizem qual imagem ou fonte não carregou).

### T3.4 Commit e tag (2 min)

```bat
git add -A
git commit -m "Fase 3: drop, transacoes de compra/abertura/venda, controllers e nova tela de login"
git push
git tag marco-3-backend
git push --tags
```
- [ ] Push sem erro.

### T3.5 Correção 4: cenário carregando no login + Mirage recortada (10 min)

**Passos**
1. Extraia **as duas partes** da correção 4 **por cima** do projeto (mesmo esquema da T2.1: em *Destino*, apague o final com o nome do ZIP). A ordem não importa. Confira:
   - `app\assets\maps\mirage_menu\` tem **265 arquivos**: o `de_mirage_menu.glb` (~23 MB) e 264 imagens;
   - `git status` mostra **11 arquivos alterados** e a pasta nova `app/assets/maps/mirage_menu/`.
2. Com o `.venv` ativo:
   ```bat
   pip install -r requirements.txt
   python main.py
   ```
3. Fique uns **10 segundos** na tela de login (é quando o cenário carrega) e depois entre.

**Validação**
- [ ] A tela de login aparece na hora e **não engasga** enquanto você digita.
- [ ] No terminal aparece `Cenário enviado à placa de vídeo em X s` (sinal de que o pré-carregamento terminou).
- [ ] Ao clicar em **ENTRAR**, a Home abre **sem travar**, com a Mirage e o personagem, no mesmo enquadramento de antes.
- [ ] Entrando **rápido** (logo que a janela abre), a Home mostra **"Carregando cenário..."** e o mapa aparece sozinho em seguida, sem congelar a janela.
- [ ] **SAIR** → login → entrar de novo: a Home abre instantaneamente (o cenário fica carregado).
- [ ] *(opcional)* Para o jogo usar só o mapa novo, renomeie temporariamente o `de_mirage_d.glb` e confira que tudo continua igual.

**Commit**
```bat
git add -A
git commit -m "Precos pela Steam, coletor continuo, cenario 3D carregado no login e Mirage recortada"
git push
```
- [ ] Push sem erro (são ~50 MB; pode levar alguns minutos).

**Se der erro:** mande o print e o terminal inteiro. Se a Home ficar em "Carregando cenário..." para sempre, procure no terminal por `Asset não encontrado` ou `Não foi possível carregar`.

---

## 9. Entendendo o código (para a apresentação)

### 9.1 O sorteio (`app/core/drop_service.py`)

1. **Tabela de drops**: `Collection_DAO.get_items(id)` traz todas as skins da caixa com a raridade de cada uma, que é a "tabela [item : probabilidade]" da documentação. `drop_table()` mostra a chance real de cada item.
2. **Raridade**: `draw_rarity()` usa `random.choices(raridades, weights=probabilidades)`. Os pesos são relativos, então se a caixa não tem alguma raridade as outras são redistribuídas sozinhas.
3. **Skin**: `random.choice()` entre as skins da raridade sorteada, com chance igual para todas.
4. **Float**: `draw_float()` sorteia a faixa (3/24/33/24/16%), um valor dentro dela de 0 a 1 e encaixa: `mínimo + valor × (máximo − mínimo)`.

Exemplo para explicar: numa caixa com 2 skins Covert, cada uma tem 0,64% ÷ 2 = **0,32%**.

### 9.2 Por que transação (`app/dao/inventory_dao.py`)

Abrir uma caixa mexe em 3 tabelas: apaga a caixa, desconta a chave e insere a skin. Se o programa caísse no meio, sem transação o jogador perderia a caixa sem ganhar a skin. Com transação, ou **tudo** é salvo (`commit`) ou **nada** (`rollback`). `SELECT ... FOR UPDATE` trava a linha do jogador até o fim, então duas operações ao mesmo tempo não gastam o mesmo dinheiro.

### 9.3 Por que `Decimal` e não `float`

`0.1 + 0.2` em `float` dá `0.30000000000000004`. Dinheiro e float da skin usam `Decimal`, igual ao `DECIMAL(10,2)` do banco.

### 9.4 Como o preço é "real"

O `tools/sync_market.py` monta o nome de mercado de cada item ("AK-47 | Redline (Field-Tested)"), consulta o **mercado da Steam** em R$ e grava no banco a mediana das vendas das últimas 24 h (ou o anúncio mais barato). Ele respeita o limite da Steam (uma consulta a cada 3,2 s), salva o progresso e continua de onde parou. O jogo só lê o banco: rápido e sem depender de internet. Cada preço consultado gera uma linha de histórico.

### 9.5 Perguntas prováveis da banca

| Pergunta | Resposta curta |
|---|---|
| Por que DAO? | Separa o SQL do resto. Se trocar de banco, só os DAOs mudam. |
| Como impede saldo negativo? | Três camadas: o controller confere, o DAO confere dentro da transação e o banco tem `CHECK (balance >= 0)`. |
| E se der erro no meio da abertura? | `rollback`: a caixa não é consumida (regra da documentação). Testado no autoteste. |
| O sorteio é justo? | Mesmas chances oficiais do CS. Mostre a tabela esperado × obtido do autoteste. |
| A tela calcula alguma coisa? | Não. A tela recebe um `Drop_Result` pronto e só anima. |
| Como a senha é guardada? | Hash SHA-256 com *salt* aleatório; a senha nunca fica salva em texto. |
| De onde vêm as skins? | CSGO-API (dados do jogo) e mercado da Steam (preços em R$), importados pelo `sync_market.py`. |
| E sem internet? | O jogo funciona: os dados já estão no banco. |

---

## 10. Fases 4 a 7 (próximos passos)

O backend das Fases 4 e 5 **já está pronto**: as telas só chamam os métodos abaixo. Eu escrevo o código das telas e você integra e valida, como fez hoje. Todas as telas novas seguem o **estilo CS2** (D11).

### Fase 4 — Tela do Mercado (`MarketView`, rota `"shop"`: o botão LOJA aparece sozinho no header)

| Tarefa | Métodos do backend | Validação |
|---|---|---|
| T4.1 Aba **CAIXAS**: grade com imagem (`item_image_path(api_id)`), nome e preço **verde/vermelho** | `list_cases()`, `can_afford(preço)` | Preço vermelho quando saldo < preço |
| T4.2 Clicar numa caixa: painel com o **conteúdo e a chance** de cada item | `case_contents(id)` | As chances somam 100% |
| T4.3 Comprar caixa: checagem → **"Deseja comprar por R$ X?"** → compra | `check_purchase(preço)`, `buy_case(caixa)` | Saldo do header atualiza; "Inventário cheio!" aparece |
| T4.4 Aba **SKINS**: busca, paginação, desgaste, preço e variação desde a passada anterior (▲▼) | `list_skins(busca, página)`, `price_history(...)` | Busca "AK" filtra |
| T4.5 Comprar skin avulsa (com confirmação) | `buy_skin(skin, anuncio)` | Skin aparece no inventário com o desgaste certo |
| T4.6 **Gráfico do histórico** (D10) no painel da caixa ou da skin, desenhado com `LineSegs` | `price_history(...)` | Linha com os pontos coletados no fim de semana |

### Fase 5 — Inventário, abertura e venda

| Tarefa | Métodos | Validação |
|---|---|---|
| T5.1 Inventário real (caixas agrupadas "x3" + skins), cards com faixa da cor da raridade e contador "37/1000" | `load()`, `status()` | Mostra só os itens do jogador |
| T5.2 Clicar na skin: destaque + botão **DETALHES** → pop-up (nome, float, desgaste, valor, fechar) | `Skin_Instance.float_value`, `wear_label`, `skin_price` | Pop-up fecha |
| T5.3 **Vender**: valor final → confirmação → venda | `sale_quote(id)`, `sell_skin(id)` | Item some e saldo sobe |
| T5.4 **Abrir caixa** com a roleta do protótipo (`prototypes/roleta_prototype.py`): chama `open_case` **antes** e monta a roleta parando no item recebido; cor por raridade (`rarity.color_rgba`) | `open_case(id)` → `Drop_Result` | Botões **ACEITAR** e **ABRIR OUTRA** (só se `can_open_another`) |

Filtros do inventário: sugiro trocar as 7 categorias atuais por **TUDO / CAIXAS / SKINS** (as outras eram do escopo cortado).

### Fase 6 — Home viva e extras (D11, D12)

| Tarefa | O que entra | Validação |
|---|---|---|
| T6.1 **Animação procedural da Home**: câmera passeando devagar, respiração e balanço do personagem, poeira/luz | `LerpInterval`/`Sequence` do Panda3D, sem biblioteca nova | Movimento suave, sem travar o FPS |
| T6.2 **Equipar skin**: botão EQUIPAR no inventário + **vitrine** na Home (imagem, nome, raridade, float) | Migração `003_equipar_skin.sql` (`users.equipped_skin_id`, preserva os dados) + método no `Inventory_DAO`/controller | Equipar, sair e entrar de novo: a vitrine continua |
| T6.3 *(bônus)* AK-47 3D com a animação oficial **`inventory_inspect`** na vitrine | `Actor` + `panda3d-gltf` | A arma gira como no "inspecionar" do jogo |
| T6.4 ✅ **Mirage otimizada** (correção 4): só a área vista pela câmera + texturas reduzidas, para caber no Git | Pasta `app/assets/maps/mirage_menu/` (~50 MB) | T3.5 |
| T6.5 *(opcional, depois da apresentação)* Tirar do Git as 704 imagens do mapa completo (`app/assets/maps/*.png`, 234 MB), que o jogo não usa mais | `git rm` das imagens antigas | O jogo abre igual; a pasta `mirage_menu` continua |

### Fase 7 — Fechamento
- [ ] Roteiro de aceite (abaixo) rodado do zero num banco limpo (no PC do professor via dump, seção 12.2).
- [ ] Prints, diagrama ER e de sequência (seções 4 e 5) e **o gráfico de preços** nos slides.
- [ ] Vídeo da demo gravado (plano B).

**Roteiro de aceite:** cadastrar → login → R$ 500,00 → comprar caixa → abrir (roleta) → ver o item no inventário → detalhes → equipar (vitrine na Home) → vender → saldo confere → fechar e abrir o jogo de novo → tudo persistiu.

---

## 11. Calendário

| Dia | Eu (código) | Você (integrar e validar) |
|---|---|---|
| **Sex 02/10** | Correção 3 (modo contínuo) ✅ · Correção 4 (cenário no login + Mirage recortada) ✅ | Extrair a correção 4 (2 partes; já inclui a 3) · T3.5 · push · **deixar o coletor contínuo rodando** (T2.6) · **PC do professor** (12.1) |
| **Sáb 03/10** | Fase 4 (Mercado estilo CS2 + gráfico) | Integrar a Fase 4 e mandar prints |
| **Dom 04/10** | Fase 5 (Inventário, abertura com roleta, venda) | Integrar → **MVP completo** |
| **Seg 05/10** | Fase 6: Home viva + vitrine "equipar" | Integrar à noite |
| **Ter–Qua 06–07/10** | Ajustes finos e correções; slides com você | Roteiro de aceite, slides, vídeo |
| **Qui 08/10** | **Congelar o código** | Dump do banco com o histórico → PC do professor (12.2) · ensaiar |
| **Sex 09/10** | — | Apresentação |

**Se o tempo apertar, corte nesta ordem:** AK com inspeção → vitrine "equipar" → animação da Home → gráfico → aba de skins avulsas → pop-up de detalhes. **Nunca corte:** comprar caixa, abrir com animação, vender.

---

## 12. PC do professor

### 12.1 Hoje (02/10): instalar a versão atual (com a Mirage)
Faça o **push da correção 4** (T3.5) antes de sair. No PC do professor, use a branch `refactoring` do mesmo jeito que você instalou no seu PC (XAMPP + DBeaver + `.venv` + `pip install -r requirements.txt` + `.env` + `schema.sql` + `seed_base.sql`). Lá o banco é novo, então **pode** rodar o `schema.sql` (a regra 2.2 vale só para o seu PC, que tem o histórico). O objetivo hoje é garantir que **Python, Panda3D, XAMPP, Git e o cenário 3D funcionam lá**. Os preços e o histórico entram na quinta (12.2).
```bat
git clone -b refactoring https://github.com/FernandoAlves02/CS-Gacha.git
:: ou, se o projeto já estiver lá:  git pull
```
- [ ] `python main.py` abre e o login funciona no PC do professor.
- [ ] A Home mostra a Mirage sem travar (checklist da T3.5). Se aparecer `simplepbr não instalado` no terminal, rode `pip install -r requirements.txt` de novo.
- [ ] Anote: versão do Python, placa de vídeo, se há internet e se você tem permissão de administrador.

### 12.2 Quinta (08/10): atualizar para a versão final
```bat
git pull
.venv\Scripts\activate
pip install -r requirements.txt
```
Depois leve o banco **pronto** do seu PC, que já tem os preços reais **e o histórico do fim de semana** (o gráfico depende dele). Use o **cmd**, não o PowerShell, por causa do `<`. O dump já recria o banco inteiro, então não precisa rodar o `schema.sql`:
  ```bat
  :: no SEU PC
  C:\xampp\mysql\bin\mysqldump -u root -p --databases csgacha > csgacha.sql
  :: no PC do PROFESSOR (copie o csgacha.sql por pendrive)
  C:\xampp\mysql\bin\mysql -u root -p < csgacha.sql
  ```
*Alternativa com internet lá:* `schema.sql` + `seed_base.sql`, depois `python tools/sync_market.py --sem-precos` (catálogo; as imagens vêm pelo Git) e `python tools/sync_market.py --so-precos` (deixe rodando).
- [ ] Rode o autoteste (T3.2) e o roteiro de aceite **no PC do professor**.

---

## 13. Riscos e plano B

| Risco | Plano |
|---|---|
| Internet ou API fora do ar no dia | O jogo não usa internet. O importador usa a cópia em `tools/cache` e mantém os preços anteriores. |
| PC do professor com problema | Apresentar do seu notebook e levar o **vídeo da demo**. |
| Mapa 3D | O jogo usa a **Mirage recortada** (`mirage_menu`, ~50 MB), que vai pelo Git. O `de_mirage_d.glb` completo (103 MB) continua fora do Git e **não é mais necessário** (só serve de reserva). O cenário é opcional: sem os arquivos o jogo funciona e só avisa no terminal. |
| PC do professor lento para o 3D | O cenário carrega durante o login; fique alguns segundos nele antes de entrar. Em último caso o jogo funciona sem o cenário. |
| Bug de última hora | Congelar na quinta; `git tag` em cada marco permite voltar (`git checkout marco-3-backend`). |

---

## 14. Solução de problemas

| Mensagem | Causa | O que fazer |
|---|---|---|
| `Unknown column 'api_id'` / `Table 'csgacha.collection_items' doesn't exist` | Banco ainda na versão 1 | Rode `schema.sql` + `seed_base.sql` (T2.3) |
| "Esta caixa não tem itens cadastrados. Rode o importador..." | Importador não rodou | `python tools/sync_market.py` |
| Importador: "a Steam pediu uma pausa; aguardando 65s" | Limite de consultas da Steam (HTTP 429) | Normal: ele espera sozinho e continua |
| Importador: "Parou antes do fim: a Steam limitou as consultas" | 3 pausas seguidas | Espere uns 10 minutos e rode `python tools/sync_market.py --so-precos` (continua do que falta) |
| Importador: "Parou antes do fim: 5 erros de rede seguidos" | Sem internet ou a Steam fora do ar | Confira a internet e rode `--so-precos` de novo |
| Importador: muitos itens "sem anúncio" | Itens raros sem nenhum à venda no momento | Normal: ficam com o preço estimado até aparecer anúncio |
| Importador: "Não foi possível baixar ... e não há cópia local" | Sem internet na primeira execução | Rode num PC com internet ou use a opção de exportar o banco (12.2) |
| Importador: "Caixa 'X' não encontrada. Você quis dizer: ...?" | Nome digitado diferente | Use o nome sugerido ou `--listar` |
| `Access denied for user` | Permissão do usuário do `.env` | `GRANT` da T2.3 |
| `Configuração do banco não encontrada` | Falta o `.env` | `copy .env.example .env` e preencha |
| Login com imagens borradas | `main.py` antigo | Confirme a linha `textures-power-2 none` |
| `WARNING ... Fonte não carregada` | Falta `app/assets/fonts` | Extraia o ZIP de novo (a tela funciona com a fonte padrão) |
| `WARNING ... Imagem não encontrada` | Falta `app/assets/ui` | Idem |
| "Saldo insuficiente para a chave (R$ 13,50)" | Regra D7 | Esperado; para desligar, `KEY_PRICE = Decimal("0.00")` |
| `WARNING ... simplepbr não instalado` | Falta o `panda3d-simplepbr` | `pip install -r requirements.txt` |
| Home presa em "Carregando cenário..." | Arquivo do mapa faltando ou que não abriu | Procure no terminal `Asset não encontrado` (extraia o ZIP de novo / `git pull`) ou `Não foi possível carregar` (mande o terminal) |
| Home com o mapa mas sem o personagem (ou o contrário) | Um dos dois `.glb` não abriu | Mesma busca no terminal; o jogo segue funcionando |

---

## 15. Fontes

- Chances oficiais por raridade, StatTrak e chave: [SteamDB — CS2 Case Opening Odds](https://steamdb.com/en/articles/cs2-case-opening-odds-explained)
- Faixas de float: [SteamDB — CS2 Float and Wear Guide](https://steamdb.com/en/articles/cs2-float-wear-guide)
- Distribuição de desgaste 3/24/33/24/16%: [case.oki.gg — Case Odds](https://case.oki.gg/case-odds)
- Limite de 1.000 itens no inventário: [Steam Community — discussão sobre o limite](https://steamcommunity.com/app/730/discussions/0/5251727781289261304/) e [csgoskins.gg — Storage Units](https://csgoskins.gg/updates/storage-units)
- Catálogo de caixas e skins: [CSGO-API (ByMykel)](https://github.com/ByMykel/CSGO-API)
- Preços: API pública do mercado da Steam (`https://steamcommunity.com/market/priceoverview/?appid=730&currency=7&market_hash_name=...`)
- Preço da chave (US$ 2,50): [tradeit.gg — Preço da Chave CS2](https://tradeit.gg/blog/pt/preco-chave-cs2/)
