from django.contrib import admin
from django.utils.html import format_html
from .models import Cliente, Produto, Venda

admin.site.site_header = "MERCEARIA DA NEUSA"
admin.site.index_title = "Painel de Controle de Vendas e Estoque"
admin.site.site_title = "Gestão Neusa"


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nome', 'telefone', 'endereco', 'saldo_devedor')
    search_fields = ('nome', 'telefone')
    ordering = ('nome',)

    def saldo_devedor(self, obj):
        divida = obj.divida_total()
        if divida > 0:
            return format_html('<span style="color:#e74c3c;font-weight:bold;">R$ {}</span>', divida)
        return format_html('<span style="color:#27ae60;">Em dia</span>')

    saldo_devedor.short_description = 'Saldo'


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'preco', 'status_estoque')
    list_editable = ('preco',)
    search_fields = ('nome',)
    ordering = ('nome',)

    def status_estoque(self, obj):
        if obj.estoque <= 3:
            return format_html(
                '<span style="background:#e74c3c;color:white;padding:4px 10px;border-radius:4px;font-weight:bold;">{} — REPOR!</span>',
                obj.estoque,
            )
        return format_html(
            '<span style="background:#27ae60;color:white;padding:4px 10px;border-radius:4px;">{}</span>',
            obj.estoque,
        )

    status_estoque.short_description = 'Estoque'


@admin.register(Venda)
class VendaAdmin(admin.ModelAdmin):
    list_display = ('produto', 'cliente', 'tipo_badge', 'quantidade', 'valor_unitario', 'total_venda', 'situacao', 'data')
    list_filter = ('tipo', 'pago', 'data', 'produto')
    list_editable = ('pago',) if False else ()
    search_fields = ('produto__nome', 'cliente__nome')
    ordering = ('-data',)
    readonly_fields = ('valor_unitario', 'data')

    def tipo_badge(self, obj):
        if obj.tipo == Venda.TIPO_FIADO:
            return format_html(
                '<span style="background:#e74c3c;color:white;padding:3px 8px;border-radius:4px;">Fiado</span>'
            )
        return format_html(
            '<span style="background:#27ae60;color:white;padding:3px 8px;border-radius:4px;">À Vista</span>'
        )

    tipo_badge.short_description = 'Tipo'

    def situacao(self, obj):
        if obj.tipo == Venda.TIPO_AVISTA:
            return format_html(
                '<span style="background:#2980b9;color:white;padding:3px 8px;border-radius:4px;">Pago</span>'
            )
        if obj.pago:
            return format_html(
                '<span style="background:#2980b9;color:white;padding:3px 8px;border-radius:4px;">Pago</span>'
            )
        return format_html(
            '<span style="background:#c0392b;color:white;padding:3px 8px;border-radius:4px;font-weight:bold;">Pendente</span>'
        )

    situacao.short_description = 'Situação'

    def total_venda(self, obj):
        return format_html('<strong>R$ {}</strong>', obj.total())

    total_venda.short_description = 'Total'
