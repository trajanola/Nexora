from django import forms

from .models import Dispositivo, OrdemServico, Parametro


class DispositivoForm(forms.ModelForm):
    class Meta:
        model = Dispositivo
        fields = ['nome', 'localizacao', 'limite_kwh']
        widgets = {
            'limite_kwh': forms.NumberInput(attrs={'step': '0.01', 'min': '0.01'}),
        }


class ParametroForm(forms.ModelForm):
    class Meta:
        model = Parametro
        fields = ['tarifa_kwh']
        widgets = {
            'tarifa_kwh': forms.NumberInput(attrs={'step': '0.0001', 'min': '0.0001'}),
        }


class OrdemServicoForm(forms.ModelForm):
    class Meta:
        model = OrdemServico
        fields = ['resumo', 'descricao']


class ConclusaoOrdemServicoForm(forms.Form):
    causa_confirmada = forms.CharField(
        label='Causa confirmada',
        max_length=255,
    )
    acao_realizada = forms.CharField(
        label='Ação realizada',
        widget=forms.Textarea(attrs={'rows': 4}),
    )
    tempo_parada_minutos = forms.IntegerField(
        label='Tempo de parada (minutos)',
        min_value=0,
    )
