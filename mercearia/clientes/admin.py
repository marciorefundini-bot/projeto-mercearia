from django.contrib import admin
from .models import Cliente, Produto, Fiado


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("nome", "telefone", "divida_total")


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ("nome", "preco")


@admin.register(Fiado)
class FiadoAdmin(admin.ModelAdmin):
    list_display = ("cliente", "produto", "quantidade", "data", "total")