"""
Models do app 'clientes'.

Entidades:
  Cliente  — pessoa que compra na mercearia (pode ter fiado)
  Produto  — item vendido, com preço e controle de estoque
  Venda    — registro de cada venda (à vista ou a prazo/fiado)

Regras de negócio implementadas aqui (fat model):
  - Ao criar uma Venda, o estoque do Produto é decrementado atomicamente.
  - Ao editar quantidade/produto de uma Venda, o delta é ajustado no estoque.
  - Ao deletar uma Venda, o estoque é restaurado.
  - Todas as operações de estoque usam SELECT FOR UPDATE para evitar
    race conditions sob requisições concorrentes.
"""

import logging

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models, transaction
from django.db.models import DecimalField, ExpressionWrapper, F, Sum

# Logger específico deste módulo (aparece nos logs como 'clientes.models')
logger = logging.getLogger(__name__)


class Cliente(models.Model):
    """
    Representa um cliente da mercearia.

    Pode ter vendas do tipo 'fiado' (a prazo) associadas a ele.
    Vendas à vista não exigem cliente vinculado.
    """

    nome = models.CharField(max_length=100, verbose_name='Nome')
    # blank=True: telefone e endereço são opcionais para permitir cadastro
    # rápido durante o registro de uma venda. Um alerta é exibido na interface
    # enquanto esses campos estiverem em branco.
    telefone = models.CharField(max_length=20, blank=True, verbose_name='Telefone')
    endereco = models.CharField(max_length=200, blank=True, verbose_name='Endereço')

    class Meta:
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'
        ordering = ['nome']  # Lista sempre em ordem alfabética

    def __str__(self):
        return self.nome

    def divida_total(self):
        """
        Retorna o valor total da dívida do cliente: soma de todas as vendas
        do tipo 'fiado' que ainda não foram pagas.

        Usa agregação no banco de dados (SUM) em vez de iterar em Python,
        evitando o carregamento desnecessário de registros em memória.

        Returns:
            Decimal: valor total em aberto; 0 se não houver dívida.
        """
        resultado = self.venda_set.filter(
            tipo=Venda.TIPO_FIADO,
            pago=False,
        ).aggregate(
            total=Sum(
                ExpressionWrapper(
                    F('quantidade') * F('valor_unitario'),
                    output_field=DecimalField(max_digits=10, decimal_places=2),
                )
            )
        )
        # aggregate retorna None quando não há registros; substitui por 0
        return resultado['total'] or 0


class Produto(models.Model):
    """
    Representa um produto vendido na mercearia.

    O campo 'estoque' é gerenciado automaticamente pela model Venda:
    decrementado na criação, ajustado na edição e restaurado na exclusão.
    """

    nome = models.CharField(max_length=100, verbose_name='Nome')
    preco = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name='Preço (R$)',
        # Garante que o preço nunca seja negativo, inclusive via API/admin
        validators=[MinValueValidator(0)],
    )
    estoque = models.IntegerField(
        default=0,
        verbose_name='Estoque',
        validators=[MinValueValidator(0)],
    )

    class Meta:
        verbose_name = 'Produto'
        verbose_name_plural = 'Produtos'
        ordering = ['nome']

    def __str__(self):
        return self.nome


class Venda(models.Model):
    """
    Representa uma venda realizada na mercearia.

    Tipos de venda:
      - À Vista (avista): pagamento imediato; 'pago' é True automaticamente.
      - Fiado   (fiado):  crédito; requer Cliente; 'pago' começa como False.

    O campo 'valor_unitario' é definido pela view no momento da venda e
    preservado mesmo se o preço do produto mudar depois — garantindo o
    histórico financeiro correto.
    """

    # ── Constantes de tipo de venda ───────────────────────────────────────────
    TIPO_AVISTA = 'avista'
    TIPO_FIADO = 'fiado'
    TIPO_CHOICES = [
        (TIPO_AVISTA, 'À Vista'),
        (TIPO_FIADO, 'Fiado (A Prazo)'),
    ]

    produto = models.ForeignKey(
        Produto,
        on_delete=models.CASCADE,  # Deleta as vendas se o produto for removido
        verbose_name='Produto',
    )
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.SET_NULL,  # Mantém o histórico mesmo se o cliente for removido
        null=True,
        blank=True,
        verbose_name='Cliente',
    )
    quantidade = models.IntegerField(
        verbose_name='Quantidade',
        validators=[MinValueValidator(1)],  # Quantidade mínima de 1 unidade
    )
    # valor_unitario: preço no momento da venda (não muda se o produto mudar de preço)
    valor_unitario = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        verbose_name='Valor Unitário (R$)',
        validators=[MinValueValidator(0)],
    )
    tipo = models.CharField(
        max_length=10,
        choices=TIPO_CHOICES,
        default=TIPO_AVISTA,
        verbose_name='Tipo',
        db_index=True,  # Índice para acelerar filtros por tipo (lista de vendas)
    )
    pago = models.BooleanField(
        default=False,
        verbose_name='Pago?',
        db_index=True,  # Índice para acelerar contagem de fiados pendentes
    )
    data = models.DateTimeField(auto_now_add=True, verbose_name='Data')

    class Meta:
        verbose_name = 'Venda'
        verbose_name_plural = 'Vendas'
        ordering = ['-data']  # Mais recentes primeiro

    def __str__(self):
        return f"Venda {self.pk} — {self.produto.nome} ({self.get_tipo_display()})"

    def total(self):
        """Retorna o valor total da venda: quantidade × valor unitário."""
        return self.quantidade * self.valor_unitario

    # ── Gerenciamento de estoque ──────────────────────────────────────────────

    def save(self, *args, **kwargs):
        """
        Sobrescreve save() para gerenciar o estoque automaticamente:

        Criação (self.pk is None):
          - Verifica e decrementa o estoque dentro de uma transação atômica.
          - Usa SELECT FOR UPDATE para bloquear a linha do produto e evitar
            race conditions quando dois usuários vendem o mesmo item ao mesmo
            tempo.

        Edição (self.pk existe):
          - Se nem o produto nem a quantidade mudaram, faz save simples
            (ex.: só marcar como pago).
          - Caso contrário, devolve a quantidade antiga ao produto anterior e
            desconta a nova quantidade do produto novo, tudo atomicamente.
        """
        if not self.pk:
            # ── NOVA VENDA ────────────────────────────────────────────────────
            self._decrementar_estoque_novo()
        else:
            # ── EDIÇÃO DE VENDA EXISTENTE ─────────────────────────────────────
            self._ajustar_estoque_edicao(*args, **kwargs)

    def _decrementar_estoque_novo(self):
        """Cria a venda e decrementa o estoque do produto atomicamente."""
        with transaction.atomic():
            # select_for_update() bloqueia a linha do produto até o commit,
            # impedindo que outra transação concurrent leia o mesmo estoque
            # e venda mais do que há disponível.
            produto = Produto.objects.select_for_update().get(pk=self.produto_id)

            if produto.estoque < self.quantidade:
                raise ValidationError(
                    f"Estoque insuficiente! '{produto.nome}' "
                    f"tem apenas {produto.estoque} unidade(s)."
                )

            produto.estoque -= self.quantidade
            # update_fields evita reescrever campos desnecessários
            produto.save(update_fields=['estoque'])

            # Atualiza self.produto para refletir o estado pós-decremento
            self.produto = produto

            logger.debug(
                "Nova venda: produto '%s' | estoque %d → %d",
                produto.nome,
                produto.estoque + self.quantidade,
                produto.estoque,
            )
            super().save()

    def _ajustar_estoque_edicao(self, *args, **kwargs):
        """
        Ajusta o estoque ao editar uma venda.

        Compara com os valores antes da edição para calcular o delta.
        Se apenas campos como 'pago' ou 'cliente' mudaram, faz save simples.

        Dois casos distintos de ajuste de estoque:

        Caso A — mesmo produto, quantidade diferente:
          Usa delta (nova_qty - antiga_qty) em um único objeto.
          Não pode carregar dois objetos Python da mesma linha: o segundo
          sobrescreveria o save do primeiro com o valor em memória desatualizado.

        Caso B — produto diferente:
          Restaura a quantidade antiga ao produto antigo e desconta a nova
          quantidade do produto novo. São linhas diferentes, sem risco de
          sobrescrita entre os dois objetos.
        """
        # Carrega o estado anterior da venda para comparar
        venda_anterior = Venda.objects.get(pk=self.pk)

        produto_mudou = venda_anterior.produto_id != self.produto_id
        qtd_mudou = venda_anterior.quantidade != self.quantidade

        if not produto_mudou and not qtd_mudou:
            # Nenhuma mudança afeta o estoque — save direto (ex.: pagar fiado)
            super().save(*args, **kwargs)
            return

        with transaction.atomic():

            if not produto_mudou:
                # ── Caso A: mesmo produto, quantidade mudou ───────────────
                # Carrega UMA única instância e aplica o delta.
                produto = Produto.objects.select_for_update().get(pk=self.produto_id)
                delta = self.quantidade - venda_anterior.quantidade  # pode ser negativo

                if delta > 0 and produto.estoque < delta:
                    raise ValidationError(
                        f"Estoque insuficiente para edição! "
                        f"'{produto.nome}' tem apenas {produto.estoque} unidade(s)."
                    )

                produto.estoque -= delta
                produto.save(update_fields=['estoque'])

                logger.debug(
                    "Edição de venda %d (mesmo produto): '%s' qty %d→%d | estoque %d→%d",
                    self.pk,
                    produto.nome,
                    venda_anterior.quantidade,
                    self.quantidade,
                    produto.estoque + delta,  # valor antes
                    produto.estoque,
                )

            else:
                # ── Caso B: produto diferente ─────────────────────────────
                # Dois objetos distintos → sem risco de sobrescrita.
                produto_antigo = Produto.objects.select_for_update().get(
                    pk=venda_anterior.produto_id
                )
                produto_novo = Produto.objects.select_for_update().get(
                    pk=self.produto_id
                )

                # 1. Devolve a quantidade anterior ao produto antigo
                produto_antigo.estoque += venda_anterior.quantidade
                produto_antigo.save(update_fields=['estoque'])

                # 2. Verifica e desconta do produto novo
                if produto_novo.estoque < self.quantidade:
                    # atomic() faz rollback ao sair com exceção
                    raise ValidationError(
                        f"Estoque insuficiente para edição! "
                        f"'{produto_novo.nome}' tem apenas "
                        f"{produto_novo.estoque} unidade(s) disponíveis."
                    )

                produto_novo.estoque -= self.quantidade
                produto_novo.save(update_fields=['estoque'])
                self.produto = produto_novo

                logger.debug(
                    "Edição de venda %d: '%s' +%d | '%s' -%d",
                    self.pk,
                    produto_antigo.nome,
                    venda_anterior.quantidade,
                    produto_novo.nome,
                    self.quantidade,
                )

            super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """
        Sobrescreve delete() para restaurar o estoque do produto ao excluir
        uma venda. Usa transação atômica para garantir que o estoque seja
        sempre restaurado junto com a exclusão — sem estados intermediários.
        """
        with transaction.atomic():
            produto = Produto.objects.select_for_update().get(pk=self.produto_id)
            produto.estoque += self.quantidade
            produto.save(update_fields=['estoque'])

            logger.debug(
                "Venda %d excluída: estoque de '%s' restaurado +%d (total: %d)",
                self.pk,
                produto.nome,
                self.quantidade,
                produto.estoque,
            )
            super().delete(*args, **kwargs)
