from django.shortcuts import render
from .models import Cliente  # Importa a tabela que você criou no models.py

def lista_clientes(request):
    # Pega todos os registros da tabela Cliente
    dados_clientes = Cliente.objects.all()
    
    # Monta o "pacote" que será enviado para o HTML
    contexto = {
        'clientes': dados_clientes
    }
    
    # Renderiza a página passando os dados
    return render(request, 'clientes/lista_clientes.html', contexto)