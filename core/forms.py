from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import (
    ConviteEmpresa,
    Dispositivo,
    MensagemContato,
    OrdemServico,
    Parametro,
    TipoSensor,
)


class CadastroForm(forms.Form):
    nome_usuario = forms.CharField(label='Nome de usuário', max_length=150)
    email_usuario = forms.EmailField(label='E-mail')
    senha_usuario = forms.CharField(label='Senha', widget=forms.PasswordInput)
    confirmar_senha = forms.CharField(label='Confirmar senha', widget=forms.PasswordInput)
    nome_empresa = forms.CharField(label='Nome da empresa', max_length=150)

    def __init__(self, *args, convite=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.convite = convite
        if convite:
            self.fields['email_usuario'].initial = convite.email
            self.fields['email_usuario'].disabled = True
            self.fields.pop('nome_empresa')

    def clean_nome_usuario(self):
        nome = self.cleaned_data['nome_usuario']
        if User.objects.filter(username__iexact=nome).exists():
            raise ValidationError('Este nome de usuário já está em uso.')
        return nome

    def clean_email_usuario(self):
        email = self.cleaned_data['email_usuario']
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError('Este e-mail já está associado a uma conta.')
        return email

    def clean(self):
        dados = super().clean()
        senha = dados.get('senha_usuario')
        confirmacao = dados.get('confirmar_senha')
        if senha and confirmacao and senha != confirmacao:
            self.add_error('confirmar_senha', 'As senhas não coincidem.')
        if senha:
            usuario = User(
                username=dados.get('nome_usuario', ''),
                email=dados.get('email_usuario', ''),
            )
            try:
                validate_password(senha, user=usuario)
            except ValidationError as erro:
                self.add_error('senha_usuario', erro)
        if not self.convite and not dados.get('nome_empresa'):
            self.add_error('nome_empresa', 'Informe o nome da empresa.')
        return dados


class ConviteEmpresaForm(forms.ModelForm):
    class Meta:
        model = ConviteEmpresa
        fields = ['email', 'papel']


class DispositivoForm(forms.ModelForm):
    class Meta:
        model = Dispositivo
        fields = [
            'nome',
            'tipo_sensor',
            'localizacao',
            'limite_kwh',
            'limite_temperatura_c',
            'limite_corrente_a',
            'limite_ruido_db',
            'custo_reparo',
        ]
        widgets = {
            'limite_kwh': forms.NumberInput(attrs={'step': '0.01', 'min': '0.01'}),
            'limite_temperatura_c': forms.NumberInput(attrs={'step': '0.01', 'min': '0.01'}),
            'limite_corrente_a': forms.NumberInput(attrs={'step': '0.01', 'min': '0.01'}),
            'limite_ruido_db': forms.NumberInput(attrs={'step': '0.01', 'min': '0.01'}),
            'custo_reparo': forms.NumberInput(attrs={'step': '0.01', 'min': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in ('limite_temperatura_c', 'limite_corrente_a', 'limite_ruido_db'):
            self.fields[campo].required = False

    def clean_limite_temperatura_c(self):
        return self.cleaned_data.get('limite_temperatura_c') or Dispositivo._meta.get_field('limite_temperatura_c').default

    def clean_limite_corrente_a(self):
        return self.cleaned_data.get('limite_corrente_a') or Dispositivo._meta.get_field('limite_corrente_a').default

    def clean_limite_ruido_db(self):
        return self.cleaned_data.get('limite_ruido_db') or Dispositivo._meta.get_field('limite_ruido_db').default


class MensagemContatoForm(forms.ModelForm):
    class Meta:
        model = MensagemContato
        fields = ['nome', 'email', 'mensagem']
        widgets = {
            'mensagem': forms.Textarea(attrs={'rows': 4}),
        }


class ParametroForm(forms.ModelForm):
    class Meta:
        model = Parametro
        fields = [
            'tarifa_kwh',
            'fator_emissao_co2',
            'taxa_base_bndes_aa',
            'spread_maximo_desconto_aa',
        ]
        widgets = {
            'tarifa_kwh': forms.NumberInput(attrs={'step': '0.0001', 'min': '0.0001'}),
            'fator_emissao_co2': forms.NumberInput(attrs={'step': '0.0001', 'min': '0.0001'}),
            'taxa_base_bndes_aa': forms.NumberInput(attrs={'step': '0.01', 'min': '0.01'}),
            'spread_maximo_desconto_aa': forms.NumberInput(attrs={'step': '0.01', 'min': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in ('fator_emissao_co2', 'taxa_base_bndes_aa', 'spread_maximo_desconto_aa'):
            self.fields[campo].required = False

    def clean_fator_emissao_co2(self):
        return self.cleaned_data.get('fator_emissao_co2') or Parametro._meta.get_field('fator_emissao_co2').default

    def clean_taxa_base_bndes_aa(self):
        return self.cleaned_data.get('taxa_base_bndes_aa') or Parametro._meta.get_field('taxa_base_bndes_aa').default

    def clean_spread_maximo_desconto_aa(self):
        return self.cleaned_data.get('spread_maximo_desconto_aa') or Parametro._meta.get_field('spread_maximo_desconto_aa').default


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
