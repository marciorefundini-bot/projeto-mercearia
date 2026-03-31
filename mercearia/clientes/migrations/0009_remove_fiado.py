from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('clientes', '0008_migrar_fiados_para_vendas'),
    ]

    operations = [
        migrations.DeleteModel(
            name='Fiado',
        ),
    ]
