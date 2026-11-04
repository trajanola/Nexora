from django.contrib import admin

from .models import Dispositivo, Leitura, OrdemServico, Parametro


class LeituraInline(admin.TabularInline):
    model = Leitura
    extra = 0


@admin.register(Dispositivo)
class DispositivoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'dono', 'localizacao', 'limite_kwh', 'criado_em')
    list_filter = ('dono',)
    search_fields = ('nome', 'localizacao')
    readonly_fields = ('token',)
    inlines = [LeituraInline]


@admin.register(Leitura)
class LeituraAdmin(admin.ModelAdmin):
    list_display = ('dispositivo', 'valor_kwh', 'registrado_em')
    list_filter = ('dispositivo',)


@admin.register(Parametro)
class ParametroAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'tarifa_kwh')


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
