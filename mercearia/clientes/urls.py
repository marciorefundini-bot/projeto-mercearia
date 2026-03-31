from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),

    path('clientes/', views.lista_clientes, name='lista_clientes'),
    path('clientes/novo/', views.criar_cliente, name='criar_cliente'),
    path('clientes/<int:pk>/', views.detalhe_cliente, name='detalhe_cliente'),
    path('clientes/<int:pk>/editar/', views.editar_cliente, name='editar_cliente'),
    path('clientes/<int:pk>/deletar/', views.deletar_cliente, name='deletar_cliente'),

    path('produtos/', views.lista_produtos, name='lista_produtos'),
    path('produtos/novo/', views.criar_produto, name='criar_produto'),
    path('produtos/<int:pk>/editar/', views.editar_produto, name='editar_produto'),
    path('produtos/<int:pk>/deletar/', views.deletar_produto, name='deletar_produto'),

    path('vendas/', views.lista_vendas, name='lista_vendas'),
    path('vendas/nova/', views.criar_venda, name='criar_venda'),
    path('vendas/<int:pk>/editar/', views.editar_venda, name='editar_venda'),
    path('vendas/<int:pk>/deletar/', views.deletar_venda, name='deletar_venda'),
    path('vendas/<int:pk>/pagar/', views.pagar_venda, name='pagar_venda'),
]
