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


class OrdemServico(models.Model):
    class Status(models.TextChoices):
        RASCUNHO = 'rascunho', 'Rascunho'
        APROVADA = 'aprovada', 'Aprovada'
        EM_EXECUCAO = 'em_execucao', 'Em execução'
        CONCLUIDA = 'concluida', 'Concluída'

    dispositivo = models.ForeignKey(
        Dispositivo,
        on_delete=models.CASCADE,
        related_name='ordens_servico',
    )
    resumo = models.CharField('serviço solicitado', max_length=160)
    descricao = models.TextField('descrição', blank=True)
    status = models.CharField(
        'status',
        max_length=20,
        choices=Status.choices,
        default=Status.RASCUNHO,
    )
    criada_em = models.DateTimeField(auto_now_add=True)
    atualizada_em = models.DateTimeField(auto_now=True)
    aprovada_em = models.DateTimeField(null=True, blank=True)
    aprovada_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='ordens_servico_aprovadas',
        null=True,
        blank=True,
    )
    causa_confirmada = models.CharField('causa confirmada', max_length=255, blank=True)
    acao_realizada = models.TextField('ação realizada', blank=True)
    tempo_parada_minutos = models.PositiveIntegerField(
        'tempo de parada (minutos)',
        null=True,
        blank=True,
    )
    concluida_em = models.DateTimeField(null=True, blank=True)
    concluida_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='ordens_servico_concluidas',
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ['criada_em', 'pk']
        verbose_name = 'ordem de serviço'
        verbose_name_plural = 'ordens de serviço'

    def __str__(self):
        return f'OS #{self.pk} - {self.resumo}'
