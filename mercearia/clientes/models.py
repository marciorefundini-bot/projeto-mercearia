from django.db import models, transaction
from django.core.exceptions import ValidationError


class Cliente(models.Model):
    nome = models.CharField(max_length=100)
    telefone = models.CharField(max_length=20)
    endereco = models.CharField(max_length=200)

    class Meta:
        verbose_name_plural = 'Clientes'
        ordering = ['nome']

    def __str__(self):
        return self.nome

    def divida_total(self):
        # soma apenas os fiados em aberto; usa cache do prefetch quando disponível
        return sum(
            f.quantidade * f.produto.preco
            for f in self.fiado_set.all()
            if not f.pago
        )


class Produto(models.Model):
    nome = models.CharField(max_length=100)
    preco = models.DecimalField(max_digits=8, decimal_places=2)
    estoque = models.IntegerField(default=0)

    class Meta:
        verbose_name_plural = 'Produtos'
        ordering = ['nome']

    def __str__(self):
        return self.nome


class Fiado(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE)
    quantidade = models.IntegerField()
    data = models.DateField(auto_now_add=True)
    pago = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = 'Fiados'
        ordering = ['-data']

    def total(self):
        return self.quantidade * self.produto.preco

    def save(self, *args, **kwargs):
        if not self.pk:
            if self.produto.estoque < self.quantidade:
                raise ValidationError(
                    f"Estoque insuficiente! '{self.produto.nome}' "
                    f"tem apenas {self.produto.estoque} unidade(s)."
                )
            with transaction.atomic():
                self.produto.estoque -= self.quantidade
                self.produto.save()
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.cliente} - {self.produto}"


class Venda(models.Model):
    produto = models.ForeignKey(Produto, on_delete=models.CASCADE)
    cliente = models.ForeignKey(Cliente, on_delete=models.SET_NULL, null=True, blank=True)
    quantidade = models.IntegerField()
    valor_unitario = models.DecimalField(max_digits=8, decimal_places=2)
    data = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'Vendas'
        ordering = ['-data']

    def total(self):
        return self.quantidade * self.valor_unitario

    def save(self, *args, **kwargs):
        if not self.pk:
            if self.produto.estoque < self.quantidade:
                raise ValidationError(
                    f"Estoque insuficiente! '{self.produto.nome}' "
                    f"tem apenas {self.produto.estoque} unidade(s)."
                )
            with transaction.atomic():
                self.produto.estoque -= self.quantidade
                self.produto.save()
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return f"Venda {self.pk} - {self.produto.nome}"
