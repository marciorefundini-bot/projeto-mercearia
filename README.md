# Projeto Mercearia

Sistema de controle de clientes, produtos e fiados feito em Django.

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

- `clientes/models.py` — Cliente, Produto, Fiado
- `clientes/views.py` — todo o CRUD
- `clientes/forms.py` — validação dos formulários
- `clientes/admin.py` — painel admin customizado

## Observações

- Ao registrar um fiado o estoque é descontado automaticamente
- Se não tiver estoque suficiente o sistema bloqueia o cadastro
- Produtos com 3 ou menos unidades aparecem com alerta vermelho
- O saldo de cada cliente é calculado somando os fiados em aberto

## Dependências

Ver `requirements.txt`. Usa Django 6.0.3 com SQLite.
