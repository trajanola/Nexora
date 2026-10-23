from django.contrib import admin

from .models import Dispositivo, Leitura, Parametro


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
