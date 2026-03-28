from django.shortcuts import render
from .models import Cliente

# O nome aqui DEVE ser lista_clientes
def lista_clientes(request):
    clientes = Cliente.objects.all()
    return render(request, 'clientes/lista_clientes.html', {'clientes': clientes})