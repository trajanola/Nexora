from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Empresa, PerfilEmpresa


@receiver(post_save, sender=User)
def criar_empresa_do_usuario(sender, instance, created, **kwargs):
    if created:
        empresa = Empresa.objects.create(nome=f'Empresa de {instance.username}'[:150])
        PerfilEmpresa.objects.create(
            usuario=instance,
            empresa=empresa,
            papel=PerfilEmpresa.Papel.PROPRIETARIO,
        )
