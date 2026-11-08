from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_dispositivo_dono_set_null'),
    ]

    operations = [
        migrations.AddField(
            model_name='leitura',
            name='id_externo',
            field=models.CharField(
                blank=True,
                max_length=100,
                null=True,
                verbose_name='identificador externo',
            ),
        ),
        migrations.AddConstraint(
            model_name='leitura',
            constraint=models.UniqueConstraint(
                fields=('dispositivo', 'id_externo'),
                name='leitura_dispositivo_id_externo_uniq',
            ),
        ),
    ]
