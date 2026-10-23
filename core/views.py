import json
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView

from .forms import DispositivoForm, ParametroForm
from .models import Dispositivo, Leitura
from .services import calcular_anomalias, obter_parametro


def home(request):
    return render(request, 'core/index.html')


def sobre(request):
    return render(request, 'core/sobre.html')


def servicos(request):
    return render(request, 'core/servicos.html')


def contato(request):
    return render(request, 'core/contato.html')


class Cadastro(View):
    def get(self, request):
        return render(request, 'core/Cadastro.html')

    def post(self, request):
        nome_usuario = request.POST.get('nome_usuario')
        if User.objects.filter(username=nome_usuario).exists():
            return render(
                request,
                'core/Cadastro.html',
                {'erro_cadastro': 'Este nome de usuário já está em uso.'},
                status=409,
            )

        User.objects.create_user(
            username=nome_usuario,
            email=request.POST.get('email_usuario'),
            password=request.POST.get('senha_usuario'),
        )
        messages.success(request, 'Conta criada. Entre com seus dados para acessar a plataforma.')
        return redirect('login')


class Logar(View):
    def get(self, request):
        if request.user.is_authenticated:
            return redirect('painel')
        return render(request, 'core/Login.html')

    def post(self, request):
        user = authenticate(
            request,
            username=request.POST.get('nome_usuario'),
            password=request.POST.get('senha_usuario'),
        )
        if user is None:
            return render(
                request,
                'core/Login.html',
                {'erro_login': 'Usuário ou senha inválidos.'},
                status=400,
            )

        auth_login(request, user)
        proxima = request.POST.get('next') or request.GET.get('next')
        if proxima and url_has_allowed_host_and_scheme(
            proxima,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return redirect(proxima)
        return redirect('painel')


class Logout(View):
    def get(self, request):
        return redirect('painel' if request.user.is_authenticated else 'login')

    def post(self, request):
        auth_logout(request)
        return redirect('login')


class ExcluirConta(LoginRequiredMixin, View):
    template_name = 'core/excluir_conta.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        if not request.user.check_password(request.POST.get('senha_atual', '')):
            return render(
                request,
                self.template_name,
                {'erro_senha': 'A senha informada está incorreta.'},
                status=400,
            )

        usuario = request.user
        usuario.delete()
        auth_logout(request)
        messages.success(request, 'A conta e os dados associados foram excluídos.')
        return redirect('login')


class DispositivoListView(LoginRequiredMixin, ListView):
    template_name = 'core/dispositivos_lista.html'
    context_object_name = 'dispositivos'

    def get_queryset(self):
        return Dispositivo.objects.filter(dono=self.request.user)


class DispositivoCreateView(LoginRequiredMixin, CreateView):
    form_class = DispositivoForm
    template_name = 'core/dispositivo_form.html'
    success_url = reverse_lazy('dispositivo_lista')

    def form_valid(self, form):
        form.instance.dono = self.request.user
        messages.success(self.request, 'Dispositivo cadastrado com sucesso.')
        return super().form_valid(form)


class DispositivoDetailView(LoginRequiredMixin, DetailView):
    template_name = 'core/dispositivo_detalhe.html'
    context_object_name = 'dispositivo'

    def get_queryset(self):
        return Dispositivo.objects.filter(dono=self.request.user)

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['leituras'] = self.object.leituras.all()[:20]
        return contexto


@csrf_exempt
@require_POST
def registrar_leitura(request):
    try:
        dados = json.loads(request.body or b'{}')
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({'erro': 'JSON inválido.'}, status=400)
    if not isinstance(dados, dict):
        return JsonResponse({'erro': 'O corpo deve ser um objeto JSON.'}, status=400)

    token = request.headers.get('X-Device-Token') or dados.get('token')
    if not token:
        return JsonResponse({'erro': 'Token do dispositivo não informado.'}, status=401)
    try:
        dispositivo = Dispositivo.objects.get(token=token)
    except (Dispositivo.DoesNotExist, ValueError, TypeError, ValidationError):
        return JsonResponse({'erro': 'Dispositivo não encontrado.'}, status=404)

    try:
        valor = Decimal(str(dados.get('valor_kwh')))
        if not valor.is_finite():
            raise InvalidOperation
        valor = valor.quantize(Decimal('0.01'))
    except (InvalidOperation, ValueError):
        return JsonResponse({'erro': 'valor_kwh deve ser um número válido.'}, status=400)

    leitura = Leitura(dispositivo=dispositivo, valor_kwh=valor)
    try:
        leitura.full_clean()
    except ValidationError as erro:
        return JsonResponse(
            {'erro': {campo: [str(item) for item in itens] for campo, itens in erro.message_dict.items()}},
            status=400,
        )
    leitura.save()
    return JsonResponse({
        'id': leitura.pk,
        'dispositivo': dispositivo.nome,
        'valor_kwh': str(leitura.valor_kwh),
        'registrado_em': leitura.registrado_em.isoformat(),
    }, status=201)


class Painel(LoginRequiredMixin, TemplateView):
    template_name = 'core/painel.html'

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['resumo'] = calcular_anomalias(self.request.user)
        return contexto


class ParametrosView(LoginRequiredMixin, UpdateView):
    form_class = ParametroForm
    template_name = 'core/parametros.html'
    success_url = reverse_lazy('painel')

    def get_object(self, queryset=None):
        return obter_parametro(self.request.user)

    def form_valid(self, form):
        messages.success(self.request, 'Tarifa salva com sucesso.')
        return super().form_valid(form)
