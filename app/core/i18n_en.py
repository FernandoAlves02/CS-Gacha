"""Traduções para o inglês (usadas por app/core/i18n.py).

Chave = o texto em português, exatamente como está no código (inclusive
espaços e pontuação). Valor = o texto em inglês. Os {nomes} entre chaves
precisam ser os mesmos dos dois lados (o teste test_i18n confere).
Para traduzir um texto novo: use t("...") no código e acrescente a linha aqui.
"""
TEXTOS_EN = {
    # ------------------------------------------------------------------
    # Login e cadastro
    # ------------------------------------------------------------------
    "Usuário": "Username",
    "E-mail": "E-mail",
    "Senha": "Password",
    "ENTRAR": "SIGN IN",
    "Não tem uma conta? ": "Don't have an account? ",
    "Registrar": "Sign up",
    "CADASTRAR": "SIGN UP",
    "Já tem uma conta? ": "Already have an account? ",
    "Entrar": "Sign in",
    "Conta criada! Digite sua senha para entrar.": "Account created! Enter your password to sign in.",
    "Informe usuário e senha.": "Enter your username and password.",
    "Usuário ou senha inválidos.": "Invalid username or password.",
    "Não foi possível entrar. Verifique a conexão com o banco.":
        "Could not sign in. Check the database connection.",
    "Não foi possível cadastrar. Verifique a conexão com o banco.":
        "Could not sign up. Check the database connection.",
    "Usuário cadastrado com sucesso!": "Account created successfully!",
    "Usuário atualizado com sucesso!": "Account updated successfully!",
    "Usuário excluído com sucesso!": "Account deleted successfully!",
    "Usuário não encontrado.": "User not found.",
    "Problemas ao excluir usuário": "Could not delete the user",
    "Não foi possível atualizar os dados.": "Could not update your data.",
    "Erro: {mensagem}": "Error: {mensagem}",
    "Usuário já cadastrado.": "User already registered.",
    "E-mail já cadastrado.": "E-mail already registered.",
    "Nome de usuário já cadastrado.": "Username already taken.",
    "O nome de usuário deve ter entre 3 e 50 caracteres.": "The username must have 3 to 50 characters.",
    "O nome de usuário não pode conter @.": "The username cannot contain @.",
    "Informe um e-mail válido.": "Enter a valid e-mail.",
    "A senha deve ter pelo menos 6 caracteres.": "The password must have at least 6 characters.",
    "O saldo não pode ficar negativo.": "The balance cannot be negative.",

    # ------------------------------------------------------------------
    # Header, Home e "Minha conta"
    # ------------------------------------------------------------------
    "INVENTÁRIO": "INVENTORY",
    "EQUIPAMENTO": "LOADOUT",
    "HOME": "HOME",
    "MERCADO": "MARKET",
    "NOTÍCIAS": "NEWS",
    "SAIR": "LOG OUT",
    "Carregando cenário...": "Loading scene...",
    "MINHA CONTA": "MY ACCOUNT",
    "NOME DE USUÁRIO": "USERNAME",
    "Nome de usuário": "Username",
    "E-MAIL": "E-MAIL",
    "NOVA SENHA (deixe em branco para manter a atual)": "NEW PASSWORD (leave blank to keep the current one)",
    "Nova senha (opcional)": "New password (optional)",
    "SALDO": "BALANCE",
    "O saldo só muda comprando, abrindo caixas ou vendendo.":
        "The balance only changes by buying, opening cases or selling.",
    "FECHAR": "CLOSE",
    "SALVAR": "SAVE",

    # ------------------------------------------------------------------
    # Mercado
    # ------------------------------------------------------------------
    "CAIXAS": "CASES",
    "SKINS": "SKINS",
    "Todas": "All",
    "COMPRAR": "BUY",
    "COMPRAR {n}x": "BUY {n}x",
    "CANCELAR": "CANCEL",
    "ESTIMADO": "ESTIMATED",
    "estimado": "estimated",
    "SEM PINTURA": "NOT PAINTED",
    "Total": "Total",
    "{n} item": "{n} item",
    "{n} itens": "{n} items",
    "HISTÓRICO DE PREÇO": "PRICE HISTORY",
    "Ainda sem histórico: o coletor de preços (T2.6) cria esta linha.":
        "No history yet: the price collector (T2.6) draws this line.",
    "Ainda sem histórico de preço.": "No price history yet.",
    "CONTEÚDO  ·  {n} itens": "CONTENTS  ·  {n} items",
    "CONTEÚDO  ·  {caixa}": "CONTENTS  ·  {caixa}",
    "VER TODOS OS ITENS": "SEE ALL ITEMS",
    "Chance de cada item = chance da raridade ÷ quantidade de itens dessa raridade.":
        "Chance of each item = chance of the rarity ÷ number of items of that rarity.",
    "Para abrir, cada caixa precisa de uma chave de {preco} (cobrada na abertura).":
        "To open it, each case needs a {preco} key (charged when opening).",
    "Nenhuma caixa à venda ainda.": "No cases for sale yet.",
    "Rode o importador: python tools/sync_market.py": "Run the importer: python tools/sync_market.py",
    "Buscar skin (ex.: AK-47 Redline)": "Search skin (e.g. AK-47 Redline)",
    "Nenhuma skin encontrada para “{busca}”.": "No skin found for “{busca}”.",
    "Nenhuma skin à venda.": "No skins for sale.",
    "Página com {n} anúncios  ·  cada desgaste é um anúncio, como no mercado da Steam":
        "{n} listings on this page  ·  each wear is a listing, like on the Steam Market",
    "Item sem desgaste (float 0)": "Item without wear (float 0)",
    "{desgaste}  ·  float de {inicio} a {fim}": "{desgaste}  ·  float {inicio} to {fim}",
    "Ao comprar, o float é sorteado dentro da faixa do desgaste escolhido.":
        "When you buy, the float is drawn within the range of the chosen wear.",
    "Cada unidade recebe o seu float, sorteado dentro da faixa desse desgaste.":
        "Each unit gets its own float, drawn within the range of this wear.",
    "clique para ampliar": "click to enlarge",
    "clique, ENTER ou ESC para fechar": "click, ENTER or ESC to close",
    "Selecione um item para ver os detalhes.": "Select an item to see the details.",
    "Preço estimado (sem anúncio na Steam no momento)": "Estimated price (no Steam listing right now)",
    "Mercado da Steam  ·  atualizado em {data}": "Steam Market  ·  updated {data}",
    "{variacao} em {horas} h": "{variacao} in {horas} h",
    "CONFIRMAR COMPRA": "CONFIRM PURCHASE",
    "Preço unitário": "Unit price",
    "QUANTIDADE": "QUANTITY",
    "MÁX ({n})": "MAX ({n})",
    "Float {valor}": "Float {valor}",
    "{n} unidades, floats de {menor} a {maior}": "{n} units, floats from {menor} to {maior}",
    "{nome} comprada! {detalhe}  ·  Saldo: {saldo}": "{nome} purchased! {detalhe}  ·  Balance: {saldo}",
    "{nome} comprada! Saldo: {saldo}": "{nome} purchased! Balance: {saldo}",
    "Quantidade inválida (de 1 a {maximo} por compra).": "Invalid quantity (1 to {maximo} per purchase).",
    "Não foi possível carregar as caixas.": "Could not load the cases.",
    "Não foi possível carregar o mercado de skins.": "Could not load the skin market.",
    "Não foi possível carregar os preços.": "Could not load the prices.",
    "Não foi possível concluir a compra.": "Could not complete the purchase.",
    "Não foi possível verificar o inventário.": "Could not check the inventory.",

    # ------------------------------------------------------------------
    # Inventário e venda
    # ------------------------------------------------------------------
    "TUDO": "ALL",
    "ITENS NO INVENTÁRIO": "ITEMS IN INVENTORY",
    "Você não tem caixas.": "You have no cases.",
    "Você ainda não tem skins.": "You have no skins yet.",
    "Seu inventário está vazio.": "Your inventory is empty.",
    "Compre caixas e skins no MERCADO.": "Buy cases and skins in the MARKET.",
    "IR AO MERCADO": "GO TO MARKET",
    "Caixa": "Case",
    "ABRIR CAIXA": "OPEN CASE",
    "VER CONTEÚDO": "SEE CONTENTS",
    "DETALHES": "DETAILS",
    "VENDER": "SELL",
    "VENDER  ·  {valor}": "SELL  ·  {valor}",
    "DESGASTE": "WEAR",
    "float desta skin: {minimo} a {maximo}": "this skin's float: {minimo} to {maximo}",
    "Sem pintura: este item não tem desgaste (float 0).": "Not painted: this item has no wear (float 0).",
    "VALOR": "VALUE",
    "Preço de mercado hoje: {preco}": "Market price today: {preco}",
    "Vendendo agora você recebe {valor} (taxa de {taxa})": "Selling now you get {valor} ({taxa} fee)",
    "Valor quando você obteve: {valor}": "Value when you got it: {valor}",
    "Obtida em {data}": "Obtained on {data}",
    "CONFIRMAR VENDA": "CONFIRM SALE",
    "Vender {nome}?": "Sell {nome}?",
    "Preço de mercado": "Market price",
    "Taxa do mercado ({taxa})": "Market fee ({taxa})",
    "Você recebe": "You get",
    "Vendida por {valor}! Saldo: {saldo}": "Sold for {valor}! Balance: {saldo}",
    "Não foi possível carregar o inventário.": "Could not load the inventory.",
    "Não foi possível carregar o conteúdo da caixa.": "Could not load the case contents.",
    "Não foi possível abrir a caixa. Verifique a conexão com o banco.":
        "Could not open the case. Check the database connection.",
    "Não foi possível calcular o valor de venda.": "Could not calculate the sale value.",
    "Não foi possível concluir a venda.": "Could not complete the sale.",

    # ------------------------------------------------------------------
    # Abertura de caixa
    # ------------------------------------------------------------------
    "Você tem {n} caixa desta": "You have {n} of this case",
    "Você tem {n} caixas desta": "You have {n} of these cases",
    "ITENS QUE PODEM SAIR DESTA CAIXA": "ITEMS THAT CAN DROP FROM THIS CASE",
    "Item Especial Raro": "Rare Special Item",
    "{n} itens raros · {chance}": "{n} rare items · {chance}",
    "+ {n} itens": "+ {n} items",
    "VOLTAR": "BACK",
    "ABRIR CAIXA  ·  chave {preco}": "OPEN CASE  ·  key {preco}",
    "Clique na roleta ou aperte ESPAÇO para pular": "Click the roulette or press SPACE to skip",
    "VOCÊ GANHOU": "YOU GOT",
    "Valor: {valor}": "Value: {valor}",
    "VER DETALHES": "SEE DETAILS",
    "ABRIR OUTRA  ({n})": "OPEN ANOTHER  ({n})",
    "ACEITAR": "ACCEPT",

    # ------------------------------------------------------------------
    # Regras do banco (mensagens dos DAOs e do sorteio)
    # ------------------------------------------------------------------
    "Quantidade inválida.": "Invalid quantity.",
    "Saldo insuficiente.": "Insufficient balance.",
    "Saldo insuficiente para a chave ({preco}).": "Insufficient balance for the key ({preco}).",
    "Inventário cheio!": "Inventory full!",
    "Caixa não encontrada no mercado.": "Case not found in the market.",
    "Esta caixa está indisponível (sem conteúdo cadastrado).": "This case is unavailable (no contents registered).",
    "Você não tem essa caixa no inventário.": "You don't have this case in your inventory.",
    "O item sorteado não pertence a esta caixa.": "The drawn item does not belong to this case.",
    "Esse item não está à venda no mercado.": "This item is not for sale in the market.",
    "O float gerado não corresponde ao desgaste escolhido.": "The generated float does not match the chosen wear.",
    "Este item não pode ser vendido.": "This item cannot be sold.",
    "Item não encontrado no seu inventário.": "Item not found in your inventory.",
    "Este item não tem desgaste (float deve ser 0).": "This item has no wear (float must be 0).",
    "Float fora do intervalo permitido para esta skin.": "Float outside the range allowed for this skin.",
    "O preço mudou para {preco}. Confira e tente de novo.": "The price changed to {preco}. Check it and try again.",
    "Esta caixa não tem itens cadastrados. Rode o importador: python tools/sync_market.py":
        "This case has no items registered. Run the importer: python tools/sync_market.py",
    "A raridade {raridade} não tem probabilidade cadastrada.": "Rarity {raridade} has no probability registered.",
    "As probabilidades desta caixa somam zero.": "The probabilities of this case add up to zero.",
    "Float inválido no catálogo (mínimo {minimo} >= máximo {maximo}).":
        "Invalid float in the catalog (minimum {minimo} >= maximum {maximo}).",
    "Esta skin tem desgaste; escolha um desgaste válido.": "This skin has wear; choose a valid wear.",
    "Este item não tem desgaste.": "This item has no wear.",
    "Esta skin não existe em {desgaste}.": "This skin does not exist in {desgaste}.",
    "Desgaste desconhecido: {desgaste}": "Unknown wear: {desgaste}",
}
