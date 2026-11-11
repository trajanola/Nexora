from django.contrib import admin

from .models import (
    ConviteEmpresa,
    Dispositivo,
    Empresa,
    Leitura,
    MensagemContato,
    OcorrenciaCausal,
    OrdemServico,
    Parametro,
    PerfilEmpresa,
)


class LeituraInline(admin.TabularInline):
    model = Leitura
    extra = 0


@admin.register(Dispositivo)
class DispositivoAdmin(admin.ModelAdmin):
    list_display = (
        'nome',
        'empresa',
        'dono',
        'localizacao',
        'limite_kwh',
        'limite_ruido_db',
        'criado_em',
    )
    list_filter = ('empresa',)
    search_fields = ('nome', 'localizacao')
    readonly_fields = ('token',)
    inlines = [LeituraInline]


@admin.register(Leitura)
class LeituraAdmin(admin.ModelAdmin):
    list_display = (
        'dispositivo',
        'valor_kwh',
        'temperatura_c',
        'corrente_a',
        'ruido_db',
        'alerta_seguranca_nr12',
        'registrado_em',
    )
    list_filter = ('dispositivo', 'alerta_seguranca_nr12')


@admin.register(Parametro)
class ParametroAdmin(admin.ModelAdmin):
    list_display = ('empresa', 'tarifa_kwh')


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
    list_filter = ('severidade', 'norma')
    search_fields = ('dispositivo__nome', 'causa_raiz', 'mensagem_prescritiva')


@admin.register(MensagemContato)
class MensagemContatoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'email', 'enviada_em')
    list_filter = ('enviada_em',)
    search_fields = ('nome', 'email', 'mensagem')
    readonly_fields = ('nome', 'email', 'mensagem', 'enviada_em')


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    search_fields = ('nome',)


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
