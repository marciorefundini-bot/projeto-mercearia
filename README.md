# Projeto Mercearia da Neusa

Sistema de controle de clientes, produtos e vendas feito em Django.
Suporta vendas à vista e a prazo (fiado) num único módulo unificado.

## Como rodar

```bash
pip install -r mercearia/requirements.txt
cd mercearia
python manage.py migrate
python manage.py runserver
```

Acessa em http://127.0.0.1:8000

Para usar o admin (`/admin/`) precisa criar um superusuário:
```bash
python manage.py createsuperuser
```

## Estrutura

- `clientes/models.py` — Cliente, Produto, Venda (com tipo: avista/fiado)
- `clientes/views.py` — todo o CRUD
- `clientes/forms.py` — validação dos formulários
- `clientes/admin.py` — painel admin customizado

## Observações

- Venda tem dois tipos: **à vista** (pago no ato) e **fiado** (a prazo)
- Para fiado, informar o cliente é obrigatório
- Ao registrar uma venda o estoque é descontado automaticamente
- Se não tiver estoque suficiente o sistema bloqueia o cadastro
- Produtos com 3 ou menos unidades aparecem com alerta vermelho
- O saldo de cada cliente é calculado somando as vendas a prazo em aberto

## Dependências

Ver `requirements.txt`. Usa Django 6.0.3 com SQLite.
