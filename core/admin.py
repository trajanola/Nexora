from django.contrib import admin

from .models import (
    ConviteEmpresa,
    Dispositivo,
    DossieAuditoria,
    Empresa,
    Leitura,
    MensagemContato,
    MissaoOperacional,
    OcorrenciaCausal,
    OrdemServico,
    Parametro,
    PerfilEmpresa,
    TipoSensor,
)


class LeituraInline(admin.TabularInline):
    model = Leitura
    extra = 0


class DispositivoInline(admin.TabularInline):
    model = Dispositivo
    extra = 1
    max_num = 200
    fields = (
        'nome',
        'tipo_sensor',
        'localizacao',
        'limite_kwh',
        'limite_temperatura_c',
        'limite_corrente_a',
        'limite_ruido_db',
        'custo_reparo',
    )


@admin.register(TipoSensor)
class TipoSensorAdmin(admin.ModelAdmin):
    list_display = ('nome', 'grandeza', 'unidade')
    search_fields = ('nome', 'grandeza', 'unidade')


@admin.register(Dispositivo)
class DispositivoAdmin(admin.ModelAdmin):
    list_display = (
        'nome',
        'empresa',
        'tipo_sensor',
        'dono',
        'localizacao',
        'limite_kwh',
        'limite_ruido_db',
        'criado_em',
    )
    list_filter = ('empresa', 'tipo_sensor')
    search_fields = ('nome', 'localizacao')
    readonly_fields = ('token',)
    list_per_page = 100
    inlines = [LeituraInline]


@admin.register(Leitura)
class LeituraAdmin(admin.ModelAdmin):
    list_display = (
        'dispositivo',
        'valor_kwh',
        'temperatura_c',
        'corrente_a',
        'ruido_db',
        'falha_seguranca_nr12',
        'registrado_em',
    )
    list_filter = ('dispositivo', 'falha_seguranca_nr12')


@admin.register(Parametro)
class ParametroAdmin(admin.ModelAdmin):
    list_display = (
        'empresa',
        'tarifa_kwh',
        'fator_emissao_co2',
        'taxa_base_bndes_aa',
        'spread_maximo_desconto_aa',
    )


@admin.register(OrdemServico)
class OrdemServicoAdmin(admin.ModelAdmin):
    list_display = ('id', 'resumo', 'dispositivo', 'status', 'criada_em', 'aprovada_por')
    list_filter = ('status', 'dispositivo__dono')
    search_fields = ('resumo', 'dispositivo__nome')
    readonly_fields = (
        'status',
        'criada_em',
        'atualizada_em',
        'aprovada_em',
        'aprovada_por',
        'concluida_em',
        'concluida_por',
    )


@admin.register(OcorrenciaCausal)
class OcorrenciaCausalAdmin(admin.ModelAdmin):
    list_display = (
        'dispositivo',
        'causa_raiz',
        'severidade',
        'norma',
        'quantidade_eventos',
        'ordem_servico',
        'detectada_em',
    )
    list_filter = ('severidade', 'norma', 'resolvida')
    search_fields = ('dispositivo__nome', 'causa_raiz', 'mensagem_prescritiva')


@admin.register(MissaoOperacional)
class MissaoOperacionalAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'empresa', 'pontos_ganho', 'prioridade', 'status', 'concluida_em')
    list_filter = ('status', 'empresa')
    search_fields = ('titulo', 'codigo', 'empresa__nome')


@admin.register(DossieAuditoria)
class DossieAuditoriaAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'empresa',
        'nota_maturidade',
        'estagio_maturidade',
        'hash_sha256',
        'carimbo_data_hora',
    )
    list_filter = ('empresa', 'estagio_maturidade')
    readonly_fields = (
        'empresa',
        'gerado_por',
        'carimbo_data_hora',
        'hash_sha256',
        'assinatura_hmac',
        'nota_maturidade',
        'estagio_maturidade',
        'payload_json',
    )


@admin.register(MensagemContato)
class MensagemContatoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'email', 'enviada_em')
    list_filter = ('enviada_em',)
    search_fields = ('nome', 'email', 'mensagem')
    readonly_fields = ('nome', 'email', 'mensagem', 'enviada_em')


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'criada_em')
    search_fields = ('nome',)
    inlines = [DispositivoInline]


@admin.register(PerfilEmpresa)
class PerfilEmpresaAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'empresa', 'papel')
    list_filter = ('papel', 'empresa')
    search_fields = ('usuario__username', 'usuario__email', 'empresa__nome')


@admin.register(ConviteEmpresa)
class ConviteEmpresaAdmin(admin.ModelAdmin):
    list_display = ('email', 'empresa', 'papel', 'criada_em', 'aceita_em')
    list_filter = ('papel', 'empresa', 'aceita_em')
    search_fields = ('email', 'empresa__nome')
    readonly_fields = ('token', 'convidado_por', 'criada_em', 'aceita_em')
