from django import forms

from .models import Dispositivo, Parametro


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
