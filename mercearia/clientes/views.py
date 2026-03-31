from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Prefetch
from django.urls import reverse

from .models import Cliente, Produto, Venda
from .forms import ClienteForm, ProdutoForm, VendaForm


def dashboard(request):
    context = {
        'total_clientes': Cliente.objects.count(),
        'total_produtos': Produto.objects.count(),
        'fiados_pendentes': Venda.objects.filter(tipo=Venda.TIPO_FIADO, pago=False).count(),
        'produtos_criticos': Produto.objects.filter(estoque__lte=3).count(),
        'total_vendas': Venda.objects.count(),
    }
    return render(request, 'clientes/dashboard.html', context)


def lista_clientes(request):
    clientes = Cliente.objects.prefetch_related(
        Prefetch('venda_set', queryset=Venda.objects.select_related('produto'))
    )
    return render(request, 'clientes/lista_clientes.html', {'clientes': clientes})


def detalhe_cliente(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    vendas_prazo = cliente.venda_set.filter(tipo=Venda.TIPO_FIADO).select_related('produto').order_by('-data')
    return render(request, 'clientes/cliente_detalhe.html', {'cliente': cliente, 'vendas_prazo': vendas_prazo})


def criar_cliente(request):
    if request.method == 'POST':
        form = ClienteForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cliente cadastrado!')
            return redirect('lista_clientes')
    else:
        form = ClienteForm()
    return render(request, 'clientes/cliente_form.html', {'form': form, 'titulo': 'Novo Cliente'})


def editar_cliente(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    form = ClienteForm(request.POST or None, instance=cliente)
    if form.is_valid():
        form.save()
        messages.success(request, 'Cliente atualizado!')
        return redirect('lista_clientes')
    return render(request, 'clientes/cliente_form.html', {
        'form': form,
        'titulo': f'Editar: {cliente.nome}',
        'cliente': cliente,
    })


def deletar_cliente(request, pk):
    cliente = get_object_or_404(Cliente, pk=pk)
    if request.method == 'POST':
        cliente.delete()
        messages.success(request, 'Cliente removido.')
        return redirect('lista_clientes')
    return render(request, 'clientes/confirmar_deletar.html', {
        'objeto': cliente,
        'voltar_url': reverse('lista_clientes'),
    })


def lista_produtos(request):
    produtos = Produto.objects.all()
    return render(request, 'clientes/produtos_list.html', {'produtos': produtos})


def criar_produto(request):
    if request.method == 'POST':
        form = ProdutoForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Produto cadastrado!')
            return redirect('lista_produtos')
    else:
        form = ProdutoForm()
    return render(request, 'clientes/produto_form.html', {'form': form, 'titulo': 'Novo Produto'})


def editar_produto(request, pk):
    produto = get_object_or_404(Produto, pk=pk)
    form = ProdutoForm(request.POST or None, instance=produto)
    if form.is_valid():
        form.save()
        messages.success(request, 'Produto atualizado!')
        return redirect('lista_produtos')
    return render(request, 'clientes/produto_form.html', {
        'form': form,
        'titulo': f'Editar: {produto.nome}',
        'produto': produto,
    })


def deletar_produto(request, pk):
    produto = get_object_or_404(Produto, pk=pk)
    if request.method == 'POST':
        produto.delete()
        messages.success(request, 'Produto removido.')
        return redirect('lista_produtos')
    return render(request, 'clientes/confirmar_deletar.html', {
        'objeto': produto,
        'voltar_url': reverse('lista_produtos'),
    })


def lista_vendas(request):
    tipo = request.GET.get('tipo', '')
    qs = Venda.objects.select_related('produto', 'cliente').order_by('-data')
    if tipo == Venda.TIPO_AVISTA:
        qs = qs.filter(tipo=Venda.TIPO_AVISTA)
    elif tipo == Venda.TIPO_FIADO:
        qs = qs.filter(tipo=Venda.TIPO_FIADO)
    return render(request, 'clientes/vendas_list.html', {'vendas': qs, 'tipo_filtro': tipo})


def criar_venda(request):
    if request.method == 'POST':
        form = VendaForm(request.POST)
        if form.is_valid():
            venda = form.save(commit=False)
            venda.valor_unitario = venda.produto.preco
            if venda.tipo == Venda.TIPO_AVISTA:
                venda.pago = True
            try:
                venda.save()
                messages.success(request, 'Venda registrada!')
                return redirect('lista_vendas')
            except ValidationError as e:
                messages.error(request, e.message)
    else:
        form = VendaForm()
    return render(request, 'clientes/venda_form.html', {'form': form, 'titulo': 'Nova Venda'})


def editar_venda(request, pk):
    venda = get_object_or_404(Venda, pk=pk)
    form = VendaForm(request.POST or None, instance=venda)
    if form.is_valid():
        form.save()
        messages.success(request, 'Venda atualizada!')
        return redirect('lista_vendas')
    return render(request, 'clientes/venda_form.html', {
        'form': form,
        'titulo': 'Editar Venda',
        'venda': venda,
    })


def deletar_venda(request, pk):
    venda = get_object_or_404(Venda, pk=pk)
    if request.method == 'POST':
        venda.delete()
        messages.success(request, 'Venda removida.')
        return redirect('lista_vendas')
    return render(request, 'clientes/confirmar_deletar.html', {
        'objeto': venda,
        'voltar_url': reverse('lista_vendas'),
    })


def pagar_venda(request, pk):
    venda = get_object_or_404(Venda, pk=pk)
    if request.method == 'POST':
        venda.pago = True
        venda.save()
        messages.success(request, f'Fiado de {venda.cliente} marcado como pago!')
    return redirect(request.POST.get('next', reverse('lista_vendas')))
