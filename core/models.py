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


class TipoSensor(models.Model):
    nome = models.CharField('tipo de sensor', max_length=80, unique=True)
    grandeza = models.CharField('grandeza física', max_length=60, default='energia')
    unidade = models.CharField('unidade de medida', max_length=20, default='kWh')

    class Meta:
        ordering = ['nome']
        verbose_name = 'tipo de sensor'
        verbose_name_plural = 'tipos de sensor'

    def __str__(self):
        return f'{self.nome} ({self.unidade})'


class Dispositivo(models.Model):
    dono = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='dispositivos',
        null=True,
        blank=True,
    )
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name='dispositivos')
    tipo_sensor = models.ForeignKey(
        TipoSensor,
        on_delete=models.SET_NULL,
        related_name='dispositivos',
        null=True,
        blank=True,
        verbose_name='tipo de sensor',
    )
    nome = models.CharField('nome do dispositivo', max_length=100)
    localizacao = models.CharField('localização', max_length=150, blank=True)
    limite_kwh = models.DecimalField(
        'limite de consumo (kWh)',
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    limite_temperatura_c = models.DecimalField(
        'limite de temperatura (°C)',
        max_digits=6,
        decimal_places=2,
        default=Decimal('80.00'),
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    limite_corrente_a = models.DecimalField(
        'limite de corrente (A)',
        max_digits=8,
        decimal_places=2,
        default=Decimal('50.00'),
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    limite_ruido_db = models.DecimalField(
        'limite de ruído NR-15 (dB)',
        max_digits=6,
        decimal_places=2,
        default=Decimal('85.00'),
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
    temperatura_c = models.DecimalField(
        'temperatura (°C)',
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
    )
    corrente_a = models.DecimalField(
        'corrente elétrica (A)',
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
    )
    ruido_db = models.DecimalField(
        'nível de ruído (dB)',
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
    )
    vibracao_mm_s = models.DecimalField(
        'vibração (mm/s)',
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
    )
    falha_seguranca_nr12 = models.BooleanField(
        'acionamento/violação de segurança NR-12',
        default=False,
    )
    registrado_em = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ['-registrado_em']
        verbose_name = 'leitura'
        verbose_name_plural = 'leituras'
        indexes = [
            models.Index(
                fields=['dispositivo', '-registrado_em'],
                name='leitura_disp_reg_idx',
            ),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['dispositivo', 'id_externo'],
                name='leitura_dispositivo_id_externo_uniq',
            ),
        ]

    def __str__(self):
        return f'{self.dispositivo} - {self.valor_kwh} kWh'


LeituraTelemetria = Leitura


class Parametro(models.Model):
    empresa = models.OneToOneField(Empresa, on_delete=models.CASCADE, related_name='parametro')
    tarifa_kwh = models.DecimalField(
        'tarifa de energia (R$/kWh)',
        max_digits=8,
        decimal_places=4,
        default=Decimal('0.8500'),
        validators=[MinValueValidator(Decimal('0.0001'))],
    )
    fator_emissao_co2 = models.DecimalField(
        'fator de emissão de carbono (kg CO2e/kWh)',
        max_digits=8,
        decimal_places=4,
        default=Decimal('0.0817'),
        validators=[MinValueValidator(Decimal('0.0001'))],
    )
    taxa_base_bndes_aa = models.DecimalField(
        'taxa base de financiamento (% a.a.)',
        max_digits=5,
        decimal_places=2,
        default=Decimal('11.50'),
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    spread_maximo_desconto_aa = models.DecimalField(
        'redução máxima de spread ESG (% a.a.)',
        max_digits=5,
        decimal_places=2,
        default=Decimal('1.50'),
        validators=[MinValueValidator(Decimal('0.01'))],
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


class OcorrenciaCausal(models.Model):
    class Severidade(models.TextChoices):
        BAIXA = 'baixa', 'Baixa'
        MEDIA = 'media', 'Média'
        ALTA = 'alta', 'Alta'
        CRITICA = 'critica', 'Crítica'

    class Norma(models.TextChoices):
        NENHUMA = 'nenhuma', 'Operacional'
        NR12 = 'nr12', 'NR-12 (Segurança no Trabalho em Máquinas)'
        NR15 = 'nr15', 'NR-15 (Atividades Insalubres / Ruído)'
        NR12_NR15 = 'nr12_nr15', 'NR-12 e NR-15'

    dispositivo = models.ForeignKey(
        Dispositivo,
        on_delete=models.CASCADE,
        related_name='ocorrencias_causais',
    )
    causa_raiz = models.CharField('diagnóstico de causa raiz', max_length=255)
    mensagem_prescritiva = models.TextField('mensagem prescritiva')
    sinais_correlacionados = models.CharField('sinais correlacionados', max_length=255)
    quantidade_eventos = models.PositiveIntegerField('eventos correlacionados', default=1)
    severidade = models.CharField(
        'severidade',
        max_length=20,
        choices=Severidade.choices,
        default=Severidade.MEDIA,
    )
    norma = models.CharField(
        'conformidade regulatória',
        max_length=20,
        choices=Norma.choices,
        default=Norma.NENHUMA,
    )
    ordem_servico = models.ForeignKey(
        OrdemServico,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ocorrencias_origem',
    )
    resolvida = models.BooleanField('resolvida', default=False)
    detectada_em = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        ordering = ['-detectada_em']
        verbose_name = 'ocorrência causal'
        verbose_name_plural = 'ocorrências causais'

    def __str__(self):
        return f'{self.dispositivo} - {self.causa_raiz}'


class MissaoOperacional(models.Model):
    class Status(models.TextChoices):
        PENDENTE = 'pendente', 'Pendente'
        CONCLUIDA = 'concluida', 'Concluída'

    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='missoes',
    )
    codigo = models.CharField('código da missão', max_length=60)
    titulo = models.CharField('título da missão', max_length=160)
    descricao = models.TextField('passo a passo prático')
    pontos_ganho = models.PositiveIntegerField('ganho estimado em pontos', default=15)
    prioridade = models.PositiveSmallIntegerField('ordem de prioridade', default=1)
    status = models.CharField(
        'status',
        max_length=20,
        choices=Status.choices,
        default=Status.PENDENTE,
    )
    concluida_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['prioridade', 'pk']
        verbose_name = 'missão operacional'
        verbose_name_plural = 'missões operacionais'
        constraints = [
            models.UniqueConstraint(
                fields=['empresa', 'codigo'],
                name='missao_empresa_codigo_uniq',
            ),
        ]

    def __str__(self):
        return f'{self.titulo} (+{self.pontos_ganho} pts)'


class DossieAuditoria(models.Model):
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name='dossies',
    )
    gerado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='dossies_gerados',
    )
    carimbo_data_hora = models.DateTimeField('carimbo de data/hora imutável', default=timezone.now, editable=False)
    hash_sha256 = models.CharField('hash criptográfico SHA-256', max_length=64, unique=True, editable=False)
    assinatura_hmac = models.CharField('assinatura criptográfica HMAC', max_length=64, editable=False)
    nota_maturidade = models.PositiveSmallIntegerField('nota de maturidade (0-100)')
    estagio_maturidade = models.CharField('estágio de maturidade', max_length=40)
    payload_json = models.TextField('evidências serializadas (JSON canônico)', editable=False)

    class Meta:
        ordering = ['-carimbo_data_hora']
        verbose_name = 'dossiê digital auditável'
        verbose_name_plural = 'dossiês digitais auditáveis'

    def __str__(self):
        return f'Dossiê #{self.pk} - {self.empresa} ({self.hash_sha256[:12]})'

