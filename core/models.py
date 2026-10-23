import uuid
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Dispositivo(models.Model):
    dono = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dispositivos')
    nome = models.CharField('nome do dispositivo', max_length=100)
    localizacao = models.CharField('localização', max_length=150, blank=True)
    limite_kwh = models.DecimalField(
        'limite de consumo (kWh)',
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'dispositivo'
        verbose_name_plural = 'dispositivos'

    def __str__(self):
        return self.nome


class Leitura(models.Model):
    dispositivo = models.ForeignKey(Dispositivo, on_delete=models.CASCADE, related_name='leituras')
    valor_kwh = models.DecimalField(
        'consumo (kWh)',
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0'))],
    )
    registrado_em = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ['-registrado_em']
        verbose_name = 'leitura'
        verbose_name_plural = 'leituras'

    def __str__(self):
        return f'{self.dispositivo} - {self.valor_kwh} kWh'


class Parametro(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='parametro')
    tarifa_kwh = models.DecimalField(
        'tarifa de energia (R$/kWh)',
        max_digits=8,
        decimal_places=4,
        default=Decimal('0.8500'),
        validators=[MinValueValidator(Decimal('0.0001'))],
    )

    class Meta:
        verbose_name = 'parâmetro financeiro'
        verbose_name_plural = 'parâmetros financeiros'

    def __str__(self):
        return f'Parâmetros de {self.usuario}'
