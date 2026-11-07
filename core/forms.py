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
        fields = ['nome', 'localizacao', 'limite_kwh', 'custo_reparo']
        widgets = {
            'limite_kwh': forms.NumberInput(attrs={'step': '0.01', 'min': '0.01'}),
            'custo_reparo': forms.NumberInput(attrs={'step': '0.01', 'min': '0.01'}),
        }


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
