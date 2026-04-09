# Mercearia da Neusa

Sistema web para gerenciamento de uma mercearia: controle de clientes, produtos, estoque e vendas. 
Desenvolvido com Python e Django.

## Sobre o sistema

O sistema permite registrar dois tipos de venda:

- **À vista** — paga no ato, nenhum cliente precisa ser informado
- **Fiado** — a prazo, exige um cliente vinculado e fica como pendente até ser marcada como paga

O estoque é controlado automaticamente: é descontado ao registrar uma venda, ajustado ao editar e restaurado ao excluir. Produtos com 3 ou menos unidades recebem um alerta visual.

Todas as páginas exigem login. O primeiro acesso é feito com um superusuário criado via terminal.

---

## Instalação

### Requisitos

- Python 3.12 ou superior
- pip

### Passo a passo

```bash
# 1. Clone o repositório
git clone <url-do-repositorio>
cd projeto-mercearia

# 2. Crie e ative o ambiente virtual
python -m venv venv
source venv/bin/activate      # Linux/macOS
venv\Scripts\activate         # Windows

# 3. Instale as dependências
pip install -r mercearia/requirements.txt

# 4. Entre na pasta do projeto
cd mercearia

# 5. Configure as variáveis de ambiente
cp .env.example .env
# Edite o .env e preencha o DJANGO_SECRET_KEY com uma chave gerada por:
# python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

# 6. Aplique as migrações
python manage.py migrate

# 7. Crie o usuário administrador
python manage.py createsuperuser

# 8. Inicie o servidor
python manage.py runserver
```

Acesse em **http://127.0.0.1:8000** e faça login com o usuário criado.

---

## Como usar

### Clientes
Acesse **Clientes** no menu lateral para cadastrar, editar ou excluir clientes. Ao clicar no nome de um cliente, você vê o histórico de fiados e o saldo devedor total em aberto.

### Produtos
Acesse **Produtos** para gerenciar o catálogo. Produtos com estoque crítico (≤ 3 unidades) aparecem com um badge vermelho "REPOR!".

### Vendas
Acesse **Vendas** para registrar uma nova venda. Informe o tipo (à vista ou fiado), o produto e a quantidade. Para fiado, o cliente é obrigatório. Na listagem é possível filtrar por tipo e marcar fiados pendentes como pagos.

### Painel Admin
Acesse `/admin/` para uma visão administrativa completa com filtros, busca e edição direta dos registros.

---

## Arquitetura

O projeto segue a estrutura padrão do Django com um único app chamado `clientes`.

```
mercearia/
├── manage.py
├── requirements.txt
├── .env.example
├── mercearia/              ← configuração do projeto
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
└── clientes/               ← app principal
    ├── models.py           ← Cliente, Produto, Venda
    ├── views.py            ← CRUD das três entidades
    ├── forms.py            ← validação dos formulários
    ├── admin.py            ← painel admin customizado
    ├── urls.py             ← rotas
    ├── tests.py            ← testes automatizados
    ├── migrations/
    └── templates/clientes/ ← templates HTML
```

**Models:**
- `Cliente` — nome, telefone, endereço
- `Produto` — nome, preço, estoque
- `Venda` — produto, cliente (opcional), quantidade, valor unitário, tipo (avista/fiado), pago, data

A lógica de estoque fica no model `Venda`: ao salvar, editar ou excluir uma venda, o estoque do produto é ajustado dentro de uma transação atômica.

---

## Rodando os testes

```bash
cd mercearia
python manage.py test clientes
```

---

## Dependências

- Django 6.0.3
- asgiref 3.11.1
- sqlparse 0.5.5
- tzdata 2025.3
