import uuid

import django.core.validators
import django.db.models.deletion
from decimal import Decimal
from django.conf import settings
from django.db import migrations, models


def criar_empresas_para_usuarios_existentes(apps, schema_editor):
    User = apps.get_model(*settings.AUTH_USER_MODEL.split('.'))
    Empresa = apps.get_model('core', 'Empresa')
    PerfilEmpresa = apps.get_model('core', 'PerfilEmpresa')
    Dispositivo = apps.get_model('core', 'Dispositivo')
    Parametro = apps.get_model('core', 'Parametro')

    for usuario in User.objects.all().iterator():
        empresa = Empresa.objects.create(nome=f'Empresa de {usuario.username}'[:150])
        PerfilEmpresa.objects.create(
            usuario_id=usuario.pk,
            empresa_id=empresa.pk,
            papel='proprietario',
        )
        Dispositivo.objects.filter(dono_id=usuario.pk).update(empresa_id=empresa.pk)
        Parametro.objects.filter(usuario_id=usuario.pk).update(empresa_id=empresa.pk)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_ordemservico'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Empresa',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=150, verbose_name='nome da empresa')),
                ('criada_em', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'empresa',
                'verbose_name_plural': 'empresas',
                'ordering': ['nome'],
            },
        ),
        migrations.CreateModel(
            name='MensagemContato',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=100, verbose_name='nome')),
                ('email', models.EmailField(max_length=254, verbose_name='e-mail')),
                ('mensagem', models.TextField(max_length=5000, verbose_name='mensagem')),
                ('enviada_em', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'mensagem de contato',
                'verbose_name_plural': 'mensagens de contato',
                'ordering': ['-enviada_em'],
            },
        ),
        migrations.CreateModel(
            name='PerfilEmpresa',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('papel', models.CharField(choices=[('proprietario', 'Proprietário'), ('financeiro', 'Financeiro'), ('manutencao', 'Gerente de Manutenção')], default='proprietario', max_length=20, verbose_name='perfil de acesso')),
                ('empresa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='perfis', to='core.empresa')),
                ('usuario', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='perfil', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'perfil da empresa',
                'verbose_name_plural': 'perfis da empresa',
            },
        ),
        migrations.CreateModel(
            name='ConviteEmpresa',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('email', models.EmailField(max_length=254, verbose_name='e-mail convidado')),
                ('papel', models.CharField(choices=[('financeiro', 'Financeiro'), ('manutencao', 'Gerente de Manutenção')], max_length=20, verbose_name='perfil de acesso')),
                ('token', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('criada_em', models.DateTimeField(auto_now_add=True)),
                ('aceita_em', models.DateTimeField(blank=True, null=True)),
                ('convidado_por', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='convites_empresa_enviados', to=settings.AUTH_USER_MODEL)),
                ('empresa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='convites', to='core.empresa')),
            ],
            options={
                'verbose_name': 'convite para empresa',
                'verbose_name_plural': 'convites para empresa',
                'ordering': ['-criada_em'],
            },
        ),
        migrations.AddField(
            model_name='dispositivo',
            name='empresa',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='dispositivos', to='core.empresa'),
        ),
        migrations.AddField(
            model_name='dispositivo',
            name='custo_reparo',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True, validators=[django.core.validators.MinValueValidator(Decimal('0.01'))], verbose_name='custo estimado do reparo preventivo (R$)'),
        ),
        migrations.AddField(
            model_name='parametro',
            name='empresa',
            field=models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='parametro', to='core.empresa'),
        ),
        migrations.RunPython(
            criar_empresas_para_usuarios_existentes,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name='dispositivo',
            name='empresa',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='dispositivos', to='core.empresa'),
        ),
        migrations.AlterField(
            model_name='parametro',
            name='empresa',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='parametro', to='core.empresa'),
        ),
        migrations.RemoveField(
            model_name='parametro',
            name='usuario',
        ),
    ]
