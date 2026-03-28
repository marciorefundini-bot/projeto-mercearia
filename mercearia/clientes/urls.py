from django.urls import path
from . import views

urlpatterns = [
    # O caminho vazio '' significa a página inicial do app
    path('', views.lista_clientes, name='lista_clientes'),
]