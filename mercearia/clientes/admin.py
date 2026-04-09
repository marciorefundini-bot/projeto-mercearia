"""
Configuração do painel de administração Django — app 'clientes'.

Customizações:
  - ClienteAdmin: exibe saldo devedor com cor (vermelho/verde).
  - ProdutoAdmin: destaca estoque crítico; permite editar preço em lista.
  - VendaAdmin:   badges coloridos para tipo e situação; campos somente-leitura.
"""

from django.contrib import admin
from django.utils.html import format_html, mark_safe

from .models import Cliente, Produto, Venda

# ── Cabeçalhos do painel admin ────────────────────────────────────────────────
admin.site.site_header = "MERCEARIA DA NEUSA"
admin.site.index_title = "Painel de Controle de Vendas e Estoque"
admin.site.site_title = "Gestão Neusa"


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    """Admin de Clientes: mostra saldo devedor colorido na lista."""

    list_display = ('nome', 'telefone', 'endereco', 'saldo_devedor')
    search_fields = ('nome', 'telefone')
    ordering = ('nome',)

    def saldo_devedor(self, obj):
        """
        Exibe o saldo devedor do cliente com formatação colorida:
          - Vermelho em negrito: cliente tem dívida pendente.
          - Verde: cliente está em dia.

        Chama obj.divida_total() que usa SQL SUM — não gera N+1 queries.
        """
        divida = obj.divida_total()
        if divida > 0:
            return format_html(
                '<span style="color:#e74c3c; font-weight:bold;">R$ {}</span>',
                divida,
            )
        # mark_safe: string sem placeholders não aceita format_html no Django 6
        return mark_safe('<span style="color:#27ae60;">Em dia</span>')

    saldo_devedor.short_description = 'Saldo'


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    """
    Admin de Produtos: destaca visualmente produtos com estoque crítico.
    Permite editar o preço diretamente na lista (list_editable).
    """

    list_display = ('nome', 'preco', 'status_estoque')
    # list_editable: permite alterar o preço sem abrir a página de edição.
    # Use com cautela — não há log de auditoria para edições inline.
    list_editable = ('preco',)
    search_fields = ('nome',)
    ordering = ('nome',)

    def status_estoque(self, obj):
        """
        Exibe o estoque com badge colorido:
          - Vermelho "REPOR!": estoque crítico (≤ 3 unidades).
          - Verde:             estoque adequado.
        """
        if obj.estoque <= 3:
            return format_html(
                '<span style="background:#e74c3c; color:white; padding:4px 10px;'
                ' border-radius:4px; font-weight:bold;">{} — REPOR!</span>',
                obj.estoque,
            )
        return format_html(
            '<span style="background:#27ae60; color:white; padding:4px 10px;'
            ' border-radius:4px;">{}</span>',
            obj.estoque,
        )

    status_estoque.short_description = 'Estoque'


@admin.register(Venda)
class VendaAdmin(admin.ModelAdmin):
    """
    Admin de Vendas: exibe todas as informações relevantes com badges coloridos.

    Campos somente-leitura:
      - valor_unitario: definido no momento da venda; não deve ser alterado
        diretamente (afetaria o histórico financeiro).
      - data: preenchida automaticamente (auto_now_add).
    """

    list_display = (
        'produto', 'cliente', 'tipo_badge', 'quantidade',
        'valor_unitario', 'total_venda', 'situacao', 'data',
    )
    list_filter = ('tipo', 'pago', 'data', 'produto')
    search_fields = ('produto__nome', 'cliente__nome')
    ordering = ('-data',)
    # Impede alteração de campos históricos pelo admin
    readonly_fields = ('valor_unitario', 'data')

    def tipo_badge(self, obj):
        """Badge colorido para o tipo de venda (À Vista = verde, Fiado = vermelho)."""
        # mark_safe: strings literais sem placeholders — seguras pois não vêm do usuário
        if obj.tipo == Venda.TIPO_FIADO:
            return mark_safe(
                '<span style="background:#e74c3c; color:white; padding:3px 8px;'
                ' border-radius:4px;">Fiado</span>'
            )
        return mark_safe(
            '<span style="background:#27ae60; color:white; padding:3px 8px;'
            ' border-radius:4px;">À Vista</span>'
        )

    tipo_badge.short_description = 'Tipo'

    def situacao(self, obj):
        """
        Badge de situação do pagamento:
          - Azul "Pago":       venda à vista ou fiado já pago.
          - Vermelho "Pendente": fiado não pago.
        """
        if obj.tipo == Venda.TIPO_AVISTA or obj.pago:
            return mark_safe(
                '<span style="background:#2980b9; color:white; padding:3px 8px;'
                ' border-radius:4px;">Pago</span>'
            )
        return mark_safe(
            '<span style="background:#c0392b; color:white; padding:3px 8px;'
            ' border-radius:4px; font-weight:bold;">Pendente</span>'
        )

    situacao.short_description = 'Situação'

    def total_venda(self, obj):
        """Exibe o total da venda (quantidade × valor unitário) em negrito."""
        return format_html('<strong>R$ {}</strong>', obj.total())

    total_venda.short_description = 'Total'
