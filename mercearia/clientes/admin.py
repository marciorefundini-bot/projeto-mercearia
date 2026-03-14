from django.contrib import admin
from .models import Cliente, Produto, Fiado


class FiadoInline(admin.TabularInline):
    model = Fiado
    extra = 0


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("nome", "telefone", "divida_total")
    readonly_fields = ("divida_total",)
    inlines = [FiadoInline]


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ("nome", "preco")


@admin.register(Fiado)
class FiadoAdmin(admin.ModelAdmin):
    list_display = ("cliente", "produto", "quantidade", "data", "total")
    list_filter = ("data", "cliente")