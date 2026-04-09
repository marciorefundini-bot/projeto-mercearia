"""
Views do app 'clientes'.

Todas as views exigem autenticação (@login_required).
Usuários não autenticados são redirecionados para LOGIN_URL (settings.py).

Padrão adotado:
  - Funções simples (FBV) — adequado para a escala deste projeto.
  - Paginação de 20 itens por página nas listagens.
  - Formulários validam dados; models gerenciam regras de negócio (estoque).
  - Mensagens de feedback (messages framework) em todas as operações.
"""

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Prefetch
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import ClienteForm, ProdutoForm, VendaForm
from .models import Cliente, Produto, Venda

# Logger específico deste módulo
logger = logging.getLogger(__name__)

# Número de itens por página nas listagens
ITENS_POR_PAGINA = 20


# ── Dashboard ─────────────────────────────────────────────────────────────────

@login_required
def dashboard(request):
    """
    Página inicial do sistema com estatísticas resumidas.

    Cada valor é calculado com uma query COUNT simples para manter o
    carregamento rápido, independentemente do volume de dados.
    """
    context = {
        'total_clientes': Cliente.objects.count(),
        'total_produtos': Produto.objects.count(),
        # Fiados pendentes: vendas a prazo ainda não pagas
        'fiados_pendentes': Venda.objects.filter(tipo=Venda.TIPO_FIADO, pago=False).count(),
        # Estoque crítico: produtos com 3 ou menos unidades disponíveis
        'produtos_criticos': Produto.objects.filter(estoque__lte=3).count(),
        'total_vendas': Venda.objects.count(),
    }
    return render(request, 'clientes/dashboard.html', context)


# ── Clientes ──────────────────────────────────────────────────────────────────

@login_required
def lista_clientes(request):
    """
    Lista todos os clientes com paginação.

    Usa prefetch_related para carregar as vendas de cada cliente em uma
    única query extra, evitando N+1 ao exibir o saldo devedor na tabela.
    O select_related('produto') dentro do Prefetch evita mais N+1 ao
    acessar venda.produto no template.
    """
    clientes_qs = Cliente.objects.prefetch_related(
        Prefetch('venda_set', queryset=Venda.objects.select_related('produto'))
    )
    paginator = Paginator(clientes_qs, ITENS_POR_PAGINA)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'clientes/lista_clientes.html', {'page_obj': page_obj})


@login_required
def detalhe_cliente(request, pk):
    """
    Exibe os dados e o histórico de fiados de um cliente específico.

    Filtra apenas vendas do tipo 'fiado' para o histórico; vendas à vista
    não aparecem aqui pois já estão quitadas no momento da compra.
    """
    cliente = get_object_or_404(Cliente, pk=pk)
    # Carrega somente as vendas a prazo, ordenadas da mais recente para a mais antiga
    vendas_prazo = (
        cliente.venda_set
        .filter(tipo=Venda.TIPO_FIADO)
        .select_related('produto')
        .order_by('-data')
    )
    return render(request, 'clientes/cliente_detalhe.html', {
        'cliente': cliente,
        'vendas_prazo': vendas_prazo,
    })


@login_required
def criar_cliente(request):
    """Exibe e processa o formulário de cadastro de novo cliente."""
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cliente cadastrado com sucesso!')
            return redirect('lista_clientes')
    else:
        form = ClienteForm()
    return render(request, 'clientes/cliente_form.html', {
        'form': form,
        'titulo': 'Novo Cliente',
    })


@login_required
def editar_cliente(request, pk):
    """Exibe e processa o formulário de edição de cliente existente."""
    cliente = get_object_or_404(Cliente, pk=pk)
    # request.POST or None: evita instanciar form com dados em GET (exibiria erros)
    form = ClienteForm(request.POST or None, instance=cliente)
    if form.is_valid():
        form.save()
        messages.success(request, 'Cliente atualizado com sucesso!')
        return redirect('lista_clientes')
    return render(request, 'clientes/cliente_form.html', {
        'form': form,
        'titulo': f'Editar: {cliente.nome}',
        'cliente': cliente,
    })


@login_required
def deletar_cliente(request, pk):
    """
    Confirma e executa a exclusão de um cliente.

    GET  → exibe página de confirmação.
    POST → executa a exclusão e redireciona.

    Atenção: a exclusão do cliente NÃO remove suas vendas (on_delete=SET_NULL),
    mas o histórico de vendas fica sem cliente associado.
    """
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == 'POST':
        cliente.delete()
        messages.success(request, f'Cliente "{cliente.nome}" removido.')
        return redirect('lista_clientes')
    return render(request, 'clientes/confirmar_deletar.html', {
        'objeto': cliente,
        'voltar_url': reverse('lista_clientes'),
    })


# ── Produtos ──────────────────────────────────────────────────────────────────

@login_required
def lista_produtos(request):
    """Lista todos os produtos com paginação."""
    produtos_qs = Produto.objects.all()
    paginator = Paginator(produtos_qs, ITENS_POR_PAGINA)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'clientes/produtos_list.html', {'page_obj': page_obj})


@login_required
def criar_produto(request):
    """Exibe e processa o formulário de cadastro de novo produto."""
    if request.method == 'POST':
        form = ProdutoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Produto cadastrado com sucesso!')
            return redirect('lista_produtos')
    else:
        form = ProdutoForm()
    return render(request, 'clientes/produto_form.html', {
        'form': form,
        'titulo': 'Novo Produto',
    })


@login_required
def editar_produto(request, pk):
    """Exibe e processa o formulário de edição de produto existente."""
    produto = get_object_or_404(Produto, pk=pk)
    form = ProdutoForm(request.POST or None, instance=produto)
    if form.is_valid():
        form.save()
        messages.success(request, 'Produto atualizado com sucesso!')
        return redirect('lista_produtos')
    return render(request, 'clientes/produto_form.html', {
        'form': form,
        'titulo': f'Editar: {produto.nome}',
        'produto': produto,
    })


@login_required
def deletar_produto(request, pk):
    """
    Confirma e executa a exclusão de um produto.

    Atenção: por causa do on_delete=CASCADE em Venda.produto, deletar um
    produto também deleta TODAS as vendas associadas. O template de confirmação
    deve alertar o usuário sobre isso.
    """
    produto = get_object_or_404(Produto, pk=pk)
    if request.method == 'POST':
        produto.delete()
        messages.success(request, f'Produto "{produto.nome}" removido.')
        return redirect('lista_produtos')
    return render(request, 'clientes/confirmar_deletar.html', {
        'objeto': produto,
        'voltar_url': reverse('lista_produtos'),
    })


# ── Vendas ────────────────────────────────────────────────────────────────────

@login_required
def lista_vendas(request):
    """
    Lista vendas com filtro por tipo (avista/fiado) e paginação.

    O parâmetro de query 'tipo' é validado contra os valores permitidos;
    valores inválidos são ignorados (mostra todas as vendas).
    """
    tipo = request.GET.get('tipo', '')

    qs = Venda.objects.select_related('produto', 'cliente').order_by('-data')

    # Aplica filtro somente para valores válidos — evita queries com dados externos
    if tipo == Venda.TIPO_AVISTA:
        qs = qs.filter(tipo=Venda.TIPO_AVISTA)
    elif tipo == Venda.TIPO_FIADO:
        qs = qs.filter(tipo=Venda.TIPO_FIADO)
    else:
        tipo = ''  # Normaliza valor inválido para exibição no template

    paginator = Paginator(qs, ITENS_POR_PAGINA)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'clientes/vendas_list.html', {
        'page_obj': page_obj,
        'tipo_filtro': tipo,
    })


@login_required
def criar_venda(request):
    """
    Registra uma nova venda.

    O valor_unitario é capturado do preço atual do produto no momento da
    venda — preservando o histórico caso o preço mude no futuro.

    Vendas à vista são marcadas como pagas automaticamente.

    Erros de estoque insuficiente são capturados da ValidationError lançada
    pelo Venda.save() e exibidos como mensagem de erro para o usuário.
    """
    if request.method == 'POST':
        form = VendaForm(request.POST)
        if form.is_valid():
            # commit=False: cria o objeto sem salvar para que possamos
            # definir o valor_unitario antes de persistir
            venda = form.save(commit=False)

            # Captura o preço atual do produto para o histórico
            venda.valor_unitario = venda.produto.preco

            # Vendas à vista são sempre consideradas pagas imediatamente
            if venda.tipo == Venda.TIPO_AVISTA:
                venda.pago = True

            try:
                venda.save()
                messages.success(request, 'Venda registrada com sucesso!')
                return redirect('lista_vendas')
            except ValidationError as e:
                # Estoque insuficiente: exibe a mensagem definida em Venda.save()
                messages.error(request, e.message)
    else:
        form = VendaForm()

    return render(request, 'clientes/venda_form.html', {
        'form': form,
        'titulo': 'Nova Venda',
    })


@login_required
def editar_venda(request, pk):
    """
    Edita uma venda existente.

    Ao alterar o produto ou a quantidade, o estoque é ajustado automaticamente
    pelo Venda.save() (devolve qty antiga ao produto antigo, desconta nova qty
    do produto novo). Erros de estoque insuficiente são capturados e exibidos.

    O valor_unitario é recalculado com base no preço atual do produto escolhido,
    para manter consistência caso o produto mude durante a edição.
    """
    venda = get_object_or_404(Venda, pk=pk)
    form = VendaForm(request.POST or None, instance=venda)

    if form.is_valid():
        venda_editada = form.save(commit=False)

        # Recalcula o valor unitário com o preço atual do produto selecionado
        # Isso garante consistência se o produto foi trocado na edição
        venda_editada.valor_unitario = venda_editada.produto.preco

        try:
            venda_editada.save()
            messages.success(request, 'Venda atualizada com sucesso!')
            return redirect('lista_vendas')
        except ValidationError as e:
            messages.error(request, e.message)

    return render(request, 'clientes/venda_form.html', {
        'form': form,
        'titulo': 'Editar Venda',
        'venda': venda,
    })


@login_required
def deletar_venda(request, pk):
    """
    Confirma e executa a exclusão de uma venda.

    O estoque do produto é restaurado automaticamente pelo Venda.delete()
    (definido no model) dentro de uma transação atômica.
    """
    venda = get_object_or_404(Venda, pk=pk)
    if request.method == 'POST':
        venda.delete()
        messages.success(request, 'Venda removida e estoque restaurado.')
        return redirect('lista_vendas')
    return render(request, 'clientes/confirmar_deletar.html', {
        'objeto': venda,
        'voltar_url': reverse('lista_vendas'),
    })


@login_required
@require_POST
def criar_cliente_rapido(request):
    """
    Cadastra um cliente apenas com o nome, sem telefone nem endereço.

    Usado no modal de cadastro rápido dentro do formulário de venda, para
    não interromper o fluxo de registro. O cliente fica com cadastro
    incompleto até que telefone e endereço sejam preenchidos.

    Retorna JSON:
      - sucesso: {"id": <pk>, "nome": "<nome>"}
      - erro:    {"erro": "<mensagem>"}, status 400
    """
    nome = request.POST.get('nome', '').strip()
    if not nome:
        return JsonResponse({'erro': 'O nome é obrigatório.'}, status=400)

    cliente = Cliente.objects.create(nome=nome, telefone='', endereco='')
    return JsonResponse({'id': cliente.pk, 'nome': cliente.nome})


@login_required
@require_POST  # Bloqueia acesso via GET — esta ação muda dados, só aceita POST
def pagar_venda(request, pk):
    """
    Marca uma venda do tipo 'fiado' como paga.

    Restrições:
      - Aceita apenas método POST (require_POST retorna 405 para GET).
      - Busca somente vendas do tipo fiado e ainda não pagas (get_object_or_404
        com esses filtros retorna 404 se a venda já estiver paga ou for à vista).
      - O parâmetro 'next' (URL de retorno) é validado para aceitar apenas
        URLs do mesmo domínio, prevenindo open redirect.

    Args:
        pk: Chave primária da Venda a ser marcada como paga.
    """
    # Filtra por tipo e pago=False: evita marcar "à vista" ou fiado já pago
    venda = get_object_or_404(Venda, pk=pk, tipo=Venda.TIPO_FIADO, pago=False)

    venda.pago = True
    # Salva apenas o campo 'pago' — evita disparar o ajuste de estoque
    # para uma mudança que não afeta produto nem quantidade
    venda.save(update_fields=['pago'])

    messages.success(request, f'Fiado de {venda.cliente} marcado como pago!')

    # ── Redirecionamento seguro ────────────────────────────────────────────────
    # O parâmetro 'next' vem do corpo do POST (ex.: página de detalhe do cliente).
    # Validamos que é uma URL relativa ao mesmo host para evitar open redirect.
    next_url = request.POST.get('next', '')
    if next_url and url_has_allowed_host_and_scheme(
        url=next_url,
        allowed_hosts={request.get_host()},
    ):
        return redirect(next_url)

    return redirect(reverse('lista_vendas'))
