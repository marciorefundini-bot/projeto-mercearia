from django.db import migrations
from django.utils import timezone


def copiar_fiados(apps, schema_editor):
    Fiado = apps.get_model('clientes', 'Fiado')
    Venda = apps.get_model('clientes', 'Venda')

    for fiado in Fiado.objects.select_related('produto', 'cliente').all():
        Venda.objects.create(
            produto=fiado.produto,
            cliente=fiado.cliente,
            quantidade=fiado.quantidade,
            valor_unitario=fiado.produto.preco,
            tipo='fiado',
            pago=fiado.pago,
            data=timezone.make_aware(
                timezone.datetime.combine(fiado.data, timezone.datetime.min.time())
            ) if timezone.is_naive(timezone.datetime.now()) else timezone.datetime(
                fiado.data.year, fiado.data.month, fiado.data.day,
                tzinfo=timezone.get_current_timezone()
            ),
        )


def reverter(apps, schema_editor):
    Venda = apps.get_model('clientes', 'Venda')
    Venda.objects.filter(tipo='fiado').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('clientes', '0007_venda_tipo_pago'),
    ]

    operations = [
        migrations.RunPython(copiar_fiados, reverter),
    ]
