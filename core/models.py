import uuid
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Empresa(models.Model):
    nome = models.CharField('nome da empresa', max_length=150)
    criada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'empresa'
        verbose_name_plural = 'empresas'

    def __str__(self):
        return self.nome


class PerfilEmpresa(models.Model):
    class Papel(models.TextChoices):
        PROPRIETARIO = 'proprietario', 'Proprietário'
        FINANCEIRO = 'financeiro', 'Financeiro'
        MANUTENCAO = 'manutencao', 'Gerente de Manutenção'

    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='perfis')
    papel = models.CharField(
        'perfil de acesso',
        max_length=20,
        choices=Papel.choices,
        default=Papel.PROPRIETARIO,
    )

    class Meta:
        verbose_name = 'perfil da empresa'
        verbose_name_plural = 'perfis da empresa'

    def __str__(self):
        return f'{self.usuario} - {self.empresa} ({self.get_papel_display()})'


class ConviteEmpresa(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='convites')
    email = models.EmailField('e-mail convidado')
    papel = models.CharField(
        'perfil de acesso',
        max_length=20,
        choices=[
            (PerfilEmpresa.Papel.FINANCEIRO, 'Financeiro'),
            (PerfilEmpresa.Papel.MANUTENCAO, 'Gerente de Manutenção'),
        ],
    )
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    convidado_por = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='convites_empresa_enviados',
    )
    criada_em = models.DateTimeField(auto_now_add=True)
    aceita_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-criada_em']
        verbose_name = 'convite para empresa'
        verbose_name_plural = 'convites para empresa'

    def __str__(self):
        return f'{self.email} - {self.empresa}'

    @property
    def expirado(self):
        return timezone.now() - self.criada_em > timedelta(days=7)


class MensagemContato(models.Model):
    nome = models.CharField('nome', max_length=100)
    email = models.EmailField('e-mail')
    mensagem = models.TextField('mensagem', max_length=5000)
    enviada_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-enviada_em']
        verbose_name = 'mensagem de contato'
        verbose_name_plural = 'mensagens de contato'

    def __str__(self):
        return f'{self.nome} - {self.email}'


class Dispositivo(models.Model):
    dono = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='dispositivos',
        null=True,
        blank=True,
    )
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='dispositivos')
    nome = models.CharField('nome do dispositivo', max_length=100)
    localizacao = models.CharField('localização', max_length=150, blank=True)
    limite_kwh = models.DecimalField(
        'limite de consumo (kWh)',
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    custo_reparo = models.DecimalField(
        'custo estimado do reparo preventivo (R$)',
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
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

    def save(self, *args, **kwargs):
        if not self.empresa_id and self.dono_id:
            self.empresa = self.dono.perfil.empresa
        super().save(*args, **kwargs)


class Leitura(models.Model):
    dispositivo = models.ForeignKey(Dispositivo, on_delete=models.CASCADE, related_name='leituras')
    id_externo = models.CharField(
        'identificador externo',
        max_length=100,
        null=True,
        blank=True,
    )
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
        constraints = [
            models.UniqueConstraint(
                fields=['dispositivo', 'id_externo'],
                name='leitura_dispositivo_id_externo_uniq',
            ),
        ]

    def __str__(self):
        return f'{self.dispositivo} - {self.valor_kwh} kWh'


class Parametro(models.Model):
    empresa = models.OneToOneField(Empresa, on_delete=models.CASCADE, related_name='parametro')
    tarifa_kwh = models.DecimalField(
        'tarifa de energia (R$/kWh)',
        max_digits=8,
        decimal_places=4,
        default=Decimal('0.8500'),
        validators=[MinValueValidator(Decimal('0.0001'))],
    )
    consumo_base_mensal_kwh = models.DecimalField(
        'consumo base mensal (kWh)',
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        blank=True,
        validators=[MinValueValidator(Decimal('0'))],
        help_text='Use zero quando ainda não houver uma linha de base definida.',
    )
    fator_emissao_co2 = models.DecimalField(
        'fator de emissão (kgCO2e/kWh)',
        max_digits=8,
        decimal_places=4,
        default=Decimal('0.0000'),
        blank=True,
        validators=[MinValueValidator(Decimal('0'))],
    )

    class Meta:
        verbose_name = 'parâmetro financeiro'
        verbose_name_plural = 'parâmetros financeiros'

    def __str__(self):
        return f'Parâmetros de {self.empresa}'


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
