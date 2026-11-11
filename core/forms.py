from decimal import Decimal

from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import ConviteEmpresa, Dispositivo, MensagemContato, OrdemServico, Parametro


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
        return (
            self.cleaned_data.get('limite_temperatura_c')
            or Dispositivo._meta.get_field('limite_temperatura_c').default
        )

    def clean_limite_corrente_a(self):
        return (
            self.cleaned_data.get('limite_corrente_a')
            or Dispositivo._meta.get_field('limite_corrente_a').default
        )

    def clean_limite_ruido_db(self):
        return (
            self.cleaned_data.get('limite_ruido_db')
            or Dispositivo._meta.get_field('limite_ruido_db').default
        )


class MensagemContatoForm(forms.ModelForm):
    class Meta:
        model = MensagemContato
        fields = ['nome', 'email', 'mensagem']
        widgets = {
            'mensagem': forms.Textarea(attrs={'rows': 4}),
        }


class ParametroForm(forms.ModelForm):
    consumo_base_mensal_kwh = forms.DecimalField(
        required=False,
        min_value=Decimal('0'),
        label='Consumo base mensal (kWh)',
        widget=forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
    )
    fator_emissao_co2 = forms.DecimalField(
        required=False,
        min_value=Decimal('0'),
        label='Fator de emissão (kgCO2e/kWh)',
        widget=forms.NumberInput(attrs={'step': '0.0001', 'min': '0'}),
    )

    class Meta:
        model = Parametro
        fields = ['tarifa_kwh', 'consumo_base_mensal_kwh', 'fator_emissao_co2']
        widgets = {
            'tarifa_kwh': forms.NumberInput(attrs={'step': '0.0001', 'min': '0.0001'}),
            'consumo_base_mensal_kwh': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'fator_emissao_co2': forms.NumberInput(attrs={'step': '0.0001', 'min': '0'}),
        }


class CreditoBNDESForm(forms.Form):
    valor_investimento = forms.DecimalField(
        label='Valor do investimento (R$)',
        min_value=Decimal('0.01'),
        max_digits=12,
        decimal_places=2,
        widget=forms.NumberInput(attrs={'step': '0.01', 'min': '0.01'}),
    )
    percentual_financiado = forms.DecimalField(
        label='Percentual financiado (%)',
        min_value=Decimal('0'),
        max_value=Decimal('100'),
        max_digits=5,
        decimal_places=2,
        initial=Decimal('80.00'),
        widget=forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'max': '100'}),
    )
    taxa_juros_anual = forms.DecimalField(
        label='Taxa de juros anual (%)',
        min_value=Decimal('0'),
        max_value=Decimal('100'),
        max_digits=6,
        decimal_places=3,
        initial=Decimal('12.000'),
        widget=forms.NumberInput(attrs={'step': '0.001', 'min': '0', 'max': '100'}),
    )
    prazo_meses = forms.IntegerField(
        label='Prazo (meses)',
        min_value=1,
        max_value=600,
        initial=60,
        widget=forms.NumberInput(attrs={'min': '1', 'max': '600'}),
    )
    percentual_desconto = forms.DecimalField(
        label='Desconto/subsídio (%)',
        min_value=Decimal('0'),
        max_value=Decimal('100'),
        max_digits=5,
        decimal_places=2,
        initial=Decimal('0.00'),
        widget=forms.NumberInput(attrs={'step': '0.01', 'min': '0', 'max': '100'}),
    )


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
