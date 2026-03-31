from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clientes', '0006_alter_cliente_options_alter_fiado_options_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='venda',
            name='tipo',
            field=models.CharField(
                choices=[('avista', 'À Vista'), ('fiado', 'Fiado (A Prazo)')],
                default='avista',
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name='venda',
            name='pago',
            field=models.BooleanField(default=False),
        ),
    ]
