# CS Gacha — Diagnóstico e Roadmap até 09/10/2026

> Gerado em 01/10/2026. Base: Documentação do Projeto + repositório do GitHub + `main.py` e `login_register_view.py` locais (os mais atualizados).
> Como usar: trabalhe **na ordem das fases**. Cada tarefa tem **Passos** e **Validação**. Só marque `[x]` quando a validação passar. Faça um commit a cada tarefa concluída.

---

## 1. Diagnóstico em uma página

**Onde estamos (estimativa honesta: ~20–25% do MVP):**

- Pronto e aproveitável: estrutura MVC + DAO, modelo `User`, DAO de usuário, hash de senha, controllers de login/cadastro, banco modelado (DDL) com raridades carregadas, protótipo de roleta (animação) e esqueleto visual de Home/Inventário.
- Não existe ainda: **todo o coração do jogo** — DAOs de caixas/skins, algoritmo de drop no backend, abertura de caixa, mercado, inventário real, venda, regras de saldo/capacidade.
- O `main.py` local **não abria** (importava `view_manager` que não existe no repositório) e a tela de login era um esqueleto sem ação. Isso já foi corrigido na refatoração (seção 3).

**Maiores riscos (em ordem):**

1. **Instalação no PC do professor (02/10):** depende de Python, pacotes pip e um MySQL no computador dele. Se algo falhar lá, não há tempo de improvisar. → Fase 0 + Plano B (seção 9).
2. **Assets 3D possivelmente fora do GitHub:** o `.gitignore` tinha `Assets/` (sem barra inicial). No Windows o Git ignora maiúsculas/minúsculas e **pode estar ignorando `app/assets/`**. Confirme com: `git check-ignore -v app/assets/maps/de_mirage_d.glb`. Se imprimir uma regra, o arquivo não está no repositório.
3. **Escopo vs. tempo:** a documentação promete mais do que cabe em ~8 dias. → Seção 5 (cortes).
4. **Lógica de dinheiro sem transação:** compra/venda/abertura mexem em várias tabelas ao mesmo tempo; sem transação, um erro no meio corrompe saldo/inventário. → T3.3.

---

## 2. Matriz Documentação × Projeto

Legenda: ✅ pronto · 🟡 parcial · ❌ não existe

| Épico / História | Backend (model/DAO/controller) | Banco | Tela (UI) | Situação |
|---|---|---|---|---|
| **Usuário — criar conta** | ✅ (corrigido na refatoração) | ✅ | ✅ (refatoração) | Falta só validar no banco real |
| **Usuário — login** | ✅ | ✅ | ✅ (refatoração) | Idem |
| **Usuário — ver/editar dados** | 🟡 `update` corrigido | ✅ | ❌ | Tela de perfil não existe (Could) |
| **Gacha — tabela/cálculo de drop (backend)** | ❌ | 🟡 raridades ok; **sem coleções nem skins** | — | Fase 2 + 3 |
| **Gacha — abrir nova caixa** | ❌ | 🟡 | 🟡 protótipo de roleta (sorteia no front — **viola a doc**) | Fase 3 + 5 |
| **Gacha — inventário de caixas / "inventário cheio"** | ❌ | 🟡 `collections_instance` ok; sem limite definido | ❌ | Decisão D2 |
| **Mercado — acessar/visualizar itens** | ❌ | 🟡 `price_collection` ok | ❌ | Fase 4 |
| **Mercado — comprar itens** | ❌ | 🟡 | ❌ | Fase 4 |
| **Inventário — visualizar itens** | ❌ | ✅ `skins_instance` | 🟡 grade com cards fixos | Fase 5 |
| **Inventário — detalhes (float, nome, desgaste)** | ❌ | ✅ | ❌ | Fase 5 (Should) |
| **Moeda — saldo atualizado, nunca negativo** | 🟡 `balance` existe; sem operações | 🟡 sem CHECK | 🟡 saldo no header | Fase 3 |
| **Moeda — venda de itens** | ❌ | ✅ | ❌ | Fase 5 |
| **Infra — instalação/README/testes** | 🟡 testes de usuário criados | — | — | Fase 0 e 6 |

---

## 3. Erros encontrados e o que foi corrigido na refatoração

| # | Arquivo | Problema | Correção |
|---|---|---|---|
| 1 | `main.py` (local) | Importa `app.controller.view_manager`, que não existe no repo → app não abre | `view_manager.py` criado (contrato `construir_tela`/`destruir`, sessão, proteção de rota). **Se você já tem o seu localmente, me envie** |
| 2 | `main.py` | UI desenhada em `render2d` → elementos **esticados** em janelas não quadradas | Passa `aspect2d` |
| 3 | `user_dao.save` | Não gravava `balance` → todo usuário novo nascia com **0,00** (o controller dizia 500) | INSERT inclui o saldo |
| 4 | `user_dao.update` | Usuário carregado sem senha (`password=None`) gravava `NULL` na coluna `NOT NULL` | Só altera a senha se houver senha nova |
| 5 | DML (`users`) | Senha de teste `hash_senha_teste_123` não tem `$` → `check_password` estourava `ValueError` no login | `seed_base.sql` com hash válido (senha **teste123**) |
| 6 | `user_dao.save/update` | E-mail/usuário duplicado gerava `IntegrityError` não tratado (doc exige bloquear e-mail repetido) | Vira `ValueError` com mensagem amigável |
| 7 | `user_controller` | `read_user_data()` devolvia 3 valores no `save` e 4 no `update` (mesma view) | Métodos distintos: `read_register_data` / `read_profile_data` |
| 8 | `user_controller` | `save`/`update` chamavam `view.show_users`, que a tela real não tem | Removido; `save` aceita callback `when_registered` |
| 9 | `user_controller.update` | **Jogador podia editar o próprio saldo** | Saldo saiu do `update_data` |
| 10 | `user.py` | Saldo `float` × `Decimal` do MySQL → `TypeError` em compra/venda | Saldo sempre `Decimal`; negativo é recusado |
| 11 | `user_dao` | Tabela `USERS` em maiúsculas: **falha em MySQL no Linux** (nome de tabela é case-sensitive) | `users` |
| 12 | `database.py` | Sem `.env` → erro críptico; porta como texto/`None` | Defaults e mensagem clara |
| 13 | `password_utils` | Quebrava com hash inválido/`None`; comparação não constante | Retorna `False`; `compare_digest` |
| 14 | `login_controller` | Hash ficava no objeto da sessão; falha de banco derrubava a tela | Hash descartado; erro tratado |
| 15 | `login_register_view` | Só campo "Usuário" com `initialText="Usuário"` (seria lido como dado); botão só dava `print` | Tela completa: login + cadastro, senha oculta, rótulos fora do campo |
| 16 | `home_view`/`inventory_view` | Cada uma era um `ShowBase` (só pode existir **um** por programa), duplicavam ~90% do código, `simplepbr.init` e mapa carregados 2x | `GameViewBase` (header) + `SceneBackdrop` (cenário carregado 1x, opcional) |
| 17 | `inventory_view` | Botões do menu com `command=None` | Menu navega; só mostra botões de telas que existem |
| 18 | `view/arma_view.py` | Executa `app.run()` **ao importar**; `return` deixa janela vazia | Patch na seção 3.1 |
| 19 | `unit_tests/login_register_view.py` | Pede `input()` **ao importar**, nome igual ao da view real, `print(..., False)`, campos colados sem separador | Virou `manual_user_flow.py` + testes automáticos `test_user_flow.py` |
| 20 | `.gitignore` | `Assets/` pode ignorar `app/assets/` no Windows | `/Assets/` (só a raiz) |

**Não mexi de propósito** (não são erros, seriam mudança de escopo): nomes de classe com `_` (`User_DAO`), DDL, desenho do menu/filtros do inventário, e SHA-256+salt (funciona; PBKDF2 do próprio `hashlib` seria melhor, mas invalida hashes já gravados → fica como melhoria opcional na Fase 6).

### 3.1 Ajustes pequenos nos arquivos de bancada (fora do produto)

`view/mapa_view.py` e `view/arma_view.py` são ferramentas para inspecionar modelos. Mova-os para `tools/` e faça só isto:

- `mapa_view.py`: não tem `run()`. Acrescente no fim: `if __name__ == "__main__": MirageInspector().run()`
- `arma_view.py`: troque as duas últimas linhas (`app = WeaponInspector()` / `app.run()`) por `if __name__ == "__main__": WeaponInspector().run()`. No `if self.weapon.isEmpty():` troque `return` por `raise SystemExit("Modelo não carregou")`.
- Ambos carregam `models/...` relativo à pasta onde você roda; aponte para `app/assets/...` como no `SceneBackdrop`.

### 3.2 Protótipo antigo (`main.py` do GitHub)

Guarde-o como `prototypes/roleta_prototype.py` (`git mv`). Ele **não** vai para a entrega, mas a animação da roleta (`start_roll`) será reaproveitada na Fase 5. Problemas dele: sorteia com `random.choice` **no front** (a documentação manda calcular no backend), caminhos relativos (`assets/...`), dados só em memória.

---

## 4. Lacunas da documentação → decisões que o grupo precisa tomar (30 min, sábado cedo)

| Decisão | Problema | Recomendação |
|---|---|---|
| **D1 — Tabela de drops** | A doc fala em "[item : probabilidade]", mas o banco tem a probabilidade **por raridade** | Sortear a **raridade** pela tabela `rarities` e depois uma skin **aleatória uniforme** daquela raridade dentro da coleção (é como o CS faz). Não exige tabela nova |
| **D2 — Inventário cheio** | Doc não diz o tamanho. E se caixa e skin contam juntas, abrir uma caixa (−1 caixa, +1 skin) nunca estoura | Constante `MAX_INVENTORY` (sugestão 100) contando caixas + skins. Regra de abrir: `usados - 1 + 1 <= MAX` (mantém a doc). **A mensagem "inventário cheio!" aparece de verdade na compra** (`usados + 1 <= MAX`) |
| **D3 — O que o Mercado vende** | Doc diz "caixas/skins", mas só caixas têm preço (`price_collection`) | MVP: Mercado vende **somente caixas**. Compra de skins avulsas = Could |
| **D4 — Preço de skin (para vender)** | `skins_catalog` não tem preço | Adicionar `base_price` e calcular `skin_price = base_price × multiplicador do desgaste` (FN 1.00 · MW 0.85 · FT 0.65 · WW 0.50 · BS 0.35), gravado em `skins_instance.skin_price` na hora do drop |
| **D5 — Float "estático conforme documento oficial"** | Documento não citado | `float = min + random() × (max − min)` e desgaste por faixa: FN 0.00–0.07 · MW 0.07–0.15 · FT 0.15–0.38 · WW 0.38–0.45 · BS 0.45–1.00 |
| **D6 — Itens fora da doc** | Menu tem EQUIPAMENTO/NOTÍCIAS; persona cita gráficos de mercado; "troca" aparece sem história | **Cortar.** Não estão nos critérios de aceitação |

Anote as decisões no topo deste arquivo quando fechar.

---

## 5. Escopo (MoSCoW) e ordem de corte

- **Must (a demo depende disso):** login/cadastro → comprar caixa no Mercado → abrir caixa (sorteio no backend + animação) → ver skin no inventário → vender skin → saldo sempre correto.
- **Should:** "inventário cheio", popup de detalhes (float/nome/desgaste), confirmação de compra/venda, saldo verde/vermelho na compra.
- **Could:** cenário 3D de fundo, tela de perfil (editar dados), compra de skins avulsas.
- **Won't (não prometa na apresentação):** troca entre jogadores, gráficos de variação de mercado, EQUIPAMENTO, NOTÍCIAS, histórico.

**Se o tempo apertar, corte nesta ordem:** 3D → perfil → popup de detalhes → "inventário cheio" → venda. **Nunca corte:** backend do drop, transação, abertura com animação.

---

## 6. Calendário

| Dia | Foco | Entregável do dia |
|---|---|---|
| **Qui 01/10 (hoje)** | Fase 0 + Fase 1 | App abre, cadastra e loga no banco local. **Marco 1** |
| **Sex 02/10** | Instalação no PC do professor | Marco 1 rodando lá. Depois: Fase 2 (dados) à noite |
| **Sáb 03/10** | Fase 2 + Fase 3 | Drop + transação testados **sem tela**. **Marco 2** |
| **Dom 04/10** | Fase 4 + Fase 5 | Comprar → abrir → inventário → vender na tela. **Marco 3 (MVP)** |
| **Seg–Qua 05–07/10** | Fase 5 (Should) + Fase 6 | Bugs, "inventário cheio", popup, documentação |
| **Qui 08/10** | Congelar | Sem código novo. Atualizar o PC do professor, ensaiar, gravar vídeo da demo |
| **Sex 09/10** | Apresentação | — |

---

## 7. Roadmap detalhado

### Fase 0 — Aplicar a refatoração e preparar o ambiente (hoje, ~1 h)

- [ ] **T0.1 Aplicar os arquivos entregues**
  - Passos: (1) no repositório, `git mv main.py prototypes/roleta_prototype.py`; (2) `git mv view tools`; (3) copie os arquivos da pasta `cs-gacha/` entregue por cima do projeto, respeitando os mesmos caminhos; (4) apague `app/unit_tests/login_register_view.py` (substituído) e o `login_register_view.py` solto na raiz (a versão certa fica em `app/view/`); (5) `git status` para conferir.
  - Validação: `python -m py_compile main.py` sem erro; `git status` mostra só arquivos esperados.
- [ ] **T0.2 Dependências** — `pip install -r requirements.txt`. Validação: `python -c "import panda3d, mysql.connector, dotenv"` sem erro.
- [ ] **T0.3 Verificar assets no Git** — rode `git check-ignore -v app/assets/maps/de_mirage_d.glb`. Se imprimir algo, o arquivo está ignorado: corrija o `.gitignore` (já corrigido) e `git add app/assets`. Se algum `.glb` passar de 100 MB o GitHub recusa → nesse caso leve os assets por pendrive e documente.

### Fase 1 — Contas funcionando de ponta a ponta (hoje, ~2 h) → **Marco 1**

- [ ] **T1.1 Banco local**
  - Passos: (1) instale/ligue o MySQL; (2) no cliente `mysql`, rode `source <caminho>/database/schema.sql;` e depois `source <caminho>/database/seed_base.sql;`; (3) crie o usuário da aplicação (não use `root` no `.env`):
    ```sql
    create user 'csgacha_app'@'localhost' identified by 'troque_esta_senha';
    grant all privileges on csgacha.* to 'csgacha_app'@'localhost';
    ```
    (4) copie `.env.example` para `.env` e preencha.
  - Validação: `select count(*) from skins_catalog;` → **34**; `select email from users;` → `teste@teste.com`.
- [ ] **T1.2 Testes automáticos** — da raiz: `python -m unittest app.unit_tests.test_user_flow -v`. Validação: **14 testes OK**.
- [ ] **T1.3 Teste contra o banco real** — `python -m app.unit_tests.manual_user_flow`. Validação: login do `teste@teste.com` / `teste123` dá "Logado com sucesso"; cadastro cria linha em `users` com `balance = 500.00`.
- [ ] **T1.4 Rodar o jogo** — `python main.py`. Validação (cada item é um critério da doc):
  - [ ] Cadastrar `ana` / `ana@x.com` / `segredo123` → mensagem de sucesso e volta ao login com e-mail preenchido.
  - [ ] Cadastrar **o mesmo e-mail** de novo → "E-mail já cadastrado." (sem travar).
  - [ ] Login com senha errada → "E-mail ou senha inválidos."
  - [ ] Login correto → Home, com nome e saldo (500.00) no topo; **SAIR** volta ao login.
  - [ ] Banco desligado → mensagem amigável, **sem fechar** o programa.
- [ ] **T1.5 Commit** — `git add . && git commit -m "Refatora base, login e cadastro funcionando"` e `git push`.

> Se `python main.py` mostrar algum erro, copie o erro inteiro e me envie. Não consegui executar o Panda3D no meu ambiente (só validei sintaxe e a lógica sem tela), então a primeira execução real é sua.

### Fase 2 — Dados do jogo no banco (sex à noite / sáb cedo, ~3 h; pode ser feita por outra pessoa do grupo)

- [ ] **T2.1 Fechar D1–D6** (seção 4).
- [ ] **T2.2 Ajustar o schema** (acrescente também ao final de `schema.sql`):
  ```sql
  alter table skins_catalog add column base_price decimal(10,2) not null default 0.00;
  alter table users add constraint chk_users_balance check (balance >= 0);
  ```
  O `CHECK` só é aplicado a partir do MySQL 8.0.16 (antes é ignorado; a regra continua no código). Validação: `describe skins_catalog;` mostra `base_price`.
- [ ] **T2.3 Seed de uma coleção (caixa) completa** — crie `database/seed_collections.sql`. Estrutura (os nomes abaixo são **exemplo**; troque pela caixa real que o grupo escolher):
  ```sql
  use csgacha;
  insert into collections (id, name, price_collection) values (1, 'Demo Case', 25.00);

  insert into skins_catalog
    (name, base_weapon, collection_id, rarity_id, min_float, max_float, base_price)
  values
    ('P250 | Exemplo 1',   'P250',   1, 1, 0.00, 0.80,  2.00),
    ('MP9 | Exemplo 2',    'MP9',    1, 1, 0.00, 1.00,  2.50),
    ('Nova | Exemplo 3',   'Nova',   1, 1, 0.00, 0.70,  3.00),
    ('SSG 08 | Exemplo 4', 'SSG 08', 1, 2, 0.00, 0.80,  8.00),
    ('Galil Ar | Exemplo 5','Galil Ar',1,2, 0.00, 1.00, 10.00),
    ('M4A4 | Exemplo 6',   'M4A4',   1, 3, 0.00, 0.75, 30.00),
    ('AWP | Exemplo 7',    'AWP',    1, 3, 0.00, 0.70, 45.00),
    ('AK-47 | Exemplo 8',  'AK-47',  1, 4, 0.00, 0.80,120.00),
    ('Faca | Exemplo 9',   'Knife',  1, 5, 0.00, 0.80,800.00);
  ```
  Regras: **toda raridade precisa de pelo menos 1 skin na coleção** (senão o sorteio cai numa raridade vazia). Preços: deixe o valor esperado de uma caixa um pouco **abaixo** do preço dela, ou o jogador fica rico em minutos.
  Validação:
  ```sql
  select r.name, count(s.id) as skins
  from rarities r left join skins_catalog s on s.rarity_id = r.id and s.collection_id = 1
  group by r.id, r.name;
  ```
  Nenhuma linha pode ter `skins = 0`.
- [ ] **T2.4 Dar caixas ao usuário de teste** (para testar abertura antes do Mercado existir): `insert into collections_instance (user_id, collection_id) values (1, 1), (1, 1), (1, 1);`

### Fase 3 — Backend do gacha, **sem tela** (sáb, ~6–8 h) → **Marco 2**

Princípio da doc: **todo cálculo no backend; o front só recebe o resultado.**

- [ ] **T3.1 Models e DAOs novos** — `Rarity`, `Collection`, `SkinCatalog`, `SkinInstance`, `CollectionInstance` em `app/models/`, e seus DAOs em `app/dao/` seguindo o `User_DAO` (lembre: tabelas em minúsculas, `%s` nos parâmetros, `Decimal` em dinheiro). O `DAO` base exige os 5 métodos abstratos; nos DAOs de tabela só-leitura (ex.: `rarities`) implemente `get_all`/`get_by_id` e deixe os demais com `raise NotImplementedError`.
  Validação: um script manual lista raridades (soma das probabilidades = **1.0000**) e as 9 skins da coleção 1.
- [ ] **T3.2 Serviço de drop (funções puras, fáceis de testar)** — `app/core/drop_service.py`:
  ```python
  import random

  WEAR_RANGES = [
      ("Factory New", 0.00, 0.07), ("Minimal Wear", 0.07, 0.15),
      ("Field-Tested", 0.15, 0.38), ("Well-Worn", 0.38, 0.45),
      ("Battle-Scarred", 0.45, 1.00),
  ]

  def sortear_raridade(raridades, rng=random):
      # raridades = [(id, probabilidade), ...]. Converta Decimal -> float:
      # random.choices levanta TypeError com Decimal.
      ids = [r[0] for r in raridades]
      pesos = [float(r[1]) for r in raridades]
      return rng.choices(ids, weights=pesos, k=1)[0]

  def sortear_float(min_float, max_float, rng=random):
      return round(float(min_float) + rng.random() * (float(max_float) - float(min_float)), 9)

  def nome_desgaste(valor):
      for nome, inicio, fim in WEAR_RANGES:
          if valor < fim:
              return nome
      return WEAR_RANGES[-1][0]
  ```
  Validação (teste unitário em `app/unit_tests/test_drop_service.py`): com 100.000 sorteios a frequência de cada raridade fica a ±0,5 p.p. da probabilidade; `sortear_float` nunca sai de `[min, max]`; `nome_desgaste(0.07)` → Minimal Wear, `nome_desgaste(0.45)` → Battle-Scarred; raridade sem skins na coleção → **erro** (não sorteia outra).
- [ ] **T3.3 Transação "abrir caixa" (a tarefa mais importante)** — um método que usa **uma única conexão** do começo ao fim (as funções atuais abrem uma conexão por chamada e não dão atomicidade). Esqueleto:
  ```python
  connection = self._database.connect()
  try:
      cursor = connection.cursor()
      # 1) caixa existe e é do usuário? (FOR UPDATE trava a linha)
      cursor.execute("select id from collections_instance where id=%s and user_id=%s for update", (caixa_id, user_id))
      if cursor.fetchone() is None: raise ValueError("Caixa não encontrada no inventário.")
      # 2) conta itens (caixas + skins) e valida MAX_INVENTORY (D2)
      # 3) sorteia raridade -> skin -> float (drop_service); qualquer falha = ValueError
      # 4) delete da caixa + insert em skins_instance (skin_price por D4)
      connection.commit()
  except Exception:
      connection.rollback()
      raise
  finally:
      cursor.close(); connection.close()
  ```
  O método devolve **só o resultado** (nome, raridade, float, desgaste, preço). Validação: (a) abrir 1 caixa → `count(collections_instance)` cai **exatamente 1** e entra **1** linha em `skins_instance`; (b) apagar de propósito todas as skins de uma raridade e abrir até cair nela → erro e **a caixa continua** no inventário (rollback); (c) abrir sem caixa → erro e nada muda.
- [ ] **T3.4 Compra e venda (também transacionais)** — `comprar_caixa`: trava o saldo (`select balance from users where id=%s for update`), valida saldo (`>=` preço) e capacidade, desconta, insere `collections_instance`. `vender_skin`: confirma que a skin é do usuário, apaga, soma `skin_price` ao saldo. Validação: compra com saldo insuficiente → erro, saldo e inventário iguais; saldo **nunca** fica negativo; compra + venda repetidas 10× mantêm a conta fechando (saldo inicial − compras + vendas).
- [ ] **T3.5 Commit + tag** — `git tag marco-2`.

### Fase 4 — Mercado na tela (dom manhã, ~3 h)

- [ ] **T4.1 `MarketView`** (estende `GameViewBase`; registre a rota `"shop"` no `main.py` — o botão LOJA aparece sozinho). Lista as coleções com nome e preço; preço **verde** se saldo ≥ preço, **vermelho** se não.
- [ ] **T4.2 Fluxo de compra** — botão COMPRAR → confirmação ("Deseja comprar por X?") → chama `comprar_caixa` → mensagem de sucesso/erro e atualiza o saldo no header.
  Validação: critérios da história "Compra de Itens" — negado com saldo insuficiente, confirmação antes de debitar, saldo atualizado, caixa aparece no inventário.

### Fase 5 — Inventário real, abertura com animação e venda (dom tarde → seg, ~8 h) → **Marco 3 (MVP)**

- [ ] **T5.1 Inventário com dados reais** — `InventoryView` consulta caixas (agrupadas com contagem) e skins do usuário e preenche a grade (já existe a estrutura em `_criar_grid`). Validação: o que a tela mostra = o que o banco tem; usuário novo vê inventário vazio.
- [ ] **T5.2 `OpenCaseView` (abrir caixa)** — reaproveite a roleta de `prototypes/roleta_prototype.py`: ao clicar ABRIR, chame o backend (T3.3) **primeiro**; só depois monte a roleta usando o resultado recebido como vencedor (cards de enfeite podem ser aleatórios, é só visual). Erros (sem caixa, "inventário cheio!") aparecem na tela. Ao final: botão aceitar e, se houver mais caixas, "abrir outra".
  Validação: abrir 5 caixas seguidas → 5 skins novas no banco, 5 caixas a menos, nenhuma duplicada por clique duplo (desabilite o botão durante a animação — o protótipo já faz).
- [ ] **T5.3 Venda** — selecionar skin → mostrar valor → botão VENDER → confirmação → `vender_skin`. Validação: skin some do inventário, saldo sobe o valor exato.
- [ ] **T5.4 (Should) Popup de detalhes** — nome, float, desgaste, botão fechar. **T5.5 (Should)** "inventário cheio!" na compra (D2).
- [ ] **T5.6 Commit + tag** — `git tag marco-3-mvp`.

### Fase 6 — Fechamento (seg–qui)

- [ ] **T6.1 Roteiro de teste de aceite** (seção 8) executado do zero em banco limpo.
- [ ] **T6.2 Documentação para a banca:** diagrama ER (gere em Mermaid a partir do `schema.sql`), diagrama da arquitetura (View → Controller → DAO → Banco), lista das histórias entregues vs. cortadas, prints.
- [ ] **T6.3 README.md** com os comandos de instalação (seção 9) e o usuário de teste.
- [ ] **T6.4 (Could)** cenário 3D: `pip install panda3d-gltf panda3d-simplepbr` e confirme que os `.glb` carregam (sem o plugin, o jogo roda sem cenário e avisa no console).
- [ ] **T6.5 (Opcional)** trocar SHA-256 por PBKDF2 (`hashlib.pbkdf2_hmac`, sem lib nova) — só se sobrar tempo, e avisando que invalida senhas já gravadas.
- [ ] **T6.6 Congelamento (qui 08/10):** `git pull` no PC do professor, rodar o roteiro, **gravar vídeo da demo (plano B)**.

---

## 8. Roteiro de teste de aceite (banco limpo)

1. Cadastrar → login → saldo **500.00**.
2. E-mail repetido é bloqueado.
3. Mercado: caixa de 25.00 → comprar → saldo **475.00**, caixa no inventário.
4. Comprar com saldo insuficiente → negado, nada muda.
5. Abrir caixa → roleta → skin ganha (nome, raridade, float, desgaste) → caixa −1, skin +1.
6. Abrir sem caixa → erro, nada muda.
7. Vender a skin → some do inventário, saldo + `skin_price`.
8. Encerrar o programa, abrir de novo, logar → **tudo persistiu**.
9. Banco desligado → mensagem amigável, sem fechar.

---

## 9. Instalação no PC do professor (sex 02/10)

**Antes de sair:** confirme com o professor — Windows? Tenho permissão de administrador? Há internet? Já existe Python/MySQL?

Levar: notebook com tudo funcionando (Plano B), pendrive com a pasta `app/assets` e um instalador do MySQL, e a pasta do projeto zipada.

- [ ] **Python 64 bits** — use **3.12** (o Panda3D 1.10.14 adicionou suporte a ele; a versão estável atual é a 1.10.16). Se o PC tiver um Python bem mais novo, confira se `pip install panda3d` encontra pacote antes de seguir; se não encontrar, instale o 3.12 ao lado.
- [ ] **Projeto:** `git clone <url>` (ou descompacte o zip) e entre na pasta.
- [ ] **Ambiente virtual (Windows):**
  ```
  py -3.12 -m venv .venv
  .venv\Scripts\activate
  pip install -r requirements.txt
  ```
- [ ] **MySQL Server** instalado e rodando (precisa de administrador). Crie o banco com o cliente `mysql` (no PowerShell o `<` não funciona; use `source`):
  ```
  mysql -u root -p
  source C:/caminho/do/projeto/database/schema.sql;
  source C:/caminho/do/projeto/database/seed_base.sql;
  create user 'csgacha_app'@'localhost' identified by 'senha_forte';
  grant all privileges on csgacha.* to 'csgacha_app'@'localhost';
  ```
- [ ] **`.env`:** `copy .env.example .env` e preencha `DB_USER`/`DB_PASSWORD`.
- [ ] **Assets:** confirme que `app\assets\` existe (se o Git os ignorava, copie do pendrive).
- [ ] **Validar:** `python -m unittest app.unit_tests.test_user_flow` (14 OK) → `python main.py` → login `teste@teste.com` / `teste123`.
- [ ] **Atualizações depois:** `git pull` e, se mudou o banco, rodar de novo o SQL novo.

**Plano B (se não puder instalar o MySQL):** apresentar do seu notebook; levar o vídeo da demo gravado. XAMPP (MariaDB) pode servir de alternativa, mas **não testei** este schema em MariaDB — se for o caminho, valide o `schema.sql` antes.

---

## 10. Regras de trabalho até sexta

- Um commit por tarefa; mensagens curtas e claras.
- **Nenhuma biblioteca nova** além de `panda3d`, `mysql-connector-python`, `python-dotenv` (e, opcionais para o 3D, `panda3d-gltf` e `panda3d-simplepbr`).
- Regra de dinheiro/inventário **sempre no backend e dentro de transação**; a tela só chama e mostra.
- Se uma tarefa passar do dobro do tempo estimado, corte conforme a seção 5 — não estenda.
