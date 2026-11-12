import json
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView

from .forms import (
    CadastroForm,
    ConclusaoOrdemServicoForm,
    CreditoBNDESForm,
    ConviteEmpresaForm,
    DispositivoForm,
    MensagemContatoForm,
    OrdemServicoForm,
    ParametroForm,
)
from .models import (
    ConviteEmpresa,
    Dispositivo,
    DossieAuditoria,
    Leitura,
    OcorrenciaCausal,
    OrdemServico,
    Parametro,
    PerfilEmpresa,
)
from .services import (
    analisar_telemetria,
    aprovar_ordem_servico,
    calcular_anomalias,
    calcular_eficiencia_co2,
    calcular_maturidade_operacional,
    concluir_ordem_servico,
    emitir_dossie_auditoria,
    estimar_credito_bndes,
    exportar_dossie_json,
    exportar_dossie_pdf,
    iniciar_ordem_servico,
    obter_parametro,
    sincronizar_missoes,
)


def home(request):
    return render(request, 'core/index.html')


def health(request):
    return JsonResponse({'status': 'ok'})


def sobre(request):
    return render(request, 'core/sobre.html')


def servicos(request):
    return render(request, 'core/servicos.html')


def contato(request):
    form = MensagemContatoForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Mensagem enviada com sucesso. A equipe Nexora recebeu seu contato.')
        return redirect('contato')
    return render(request, 'core/contato.html', {'form': form})


class Cadastro(View):
    def get(self, request):
        return render(request, 'core/Cadastro.html', {'form': CadastroForm()})

    @transaction.atomic
    def post(self, request):
        form = CadastroForm(request.POST)
        if not form.is_valid():
            return render(request, 'core/Cadastro.html', {'form': form}, status=400)

        usuario = User.objects.create_user(
            username=form.cleaned_data['nome_usuario'],
            email=form.cleaned_data['email_usuario'],
            password=form.cleaned_data['senha_usuario'],
        )
        usuario.perfil.empresa.nome = form.cleaned_data['nome_empresa']
        usuario.perfil.empresa.save(update_fields=['nome'])
        messages.success(request, 'Conta criada. Entre com seus dados para acessar a plataforma.')
        return redirect('login')


class ConvitesEmpresaView(LoginRequiredMixin, View):
    template_name = 'core/convites_empresa.html'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.perfil.papel != PerfilEmpresa.Papel.PROPRIETARIO:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        return render(request, self.template_name, {
            'form': ConviteEmpresaForm(),
            'convites': ConviteEmpresa.objects.filter(empresa=request.user.perfil.empresa),
        })

    @transaction.atomic
    def post(self, request):
        form = ConviteEmpresaForm(request.POST)
        empresa = request.user.perfil.empresa
        email = request.POST.get('email', '').strip()
        usuario_existente = User.objects.filter(email__iexact=email).select_related(
            'perfil',
            'perfil__empresa',
        ).first()
        if (
            form.is_valid()
            and usuario_existente
            and usuario_existente.perfil.empresa_id == empresa.pk
        ):
            form.add_error('email', 'Este usuário já faz parte da empresa.')
        if (
            form.is_valid()
            and ConviteEmpresa.objects.filter(
                empresa=empresa,
                email__iexact=form.cleaned_data['email'],
                aceita_em__isnull=True,
                criada_em__gte=timezone.now() - timedelta(days=7),
            ).exists()
        ):
            form.add_error('email', 'Já existe um convite pendente para este e-mail.')
        if not form.is_valid():
            return render(request, self.template_name, {
                'form': form,
                'convites': ConviteEmpresa.objects.filter(empresa=empresa),
            }, status=400)

        convite = form.save(commit=False)
        convite.empresa = empresa
        convite.convidado_por = request.user
        convite.save()
        link = request.build_absolute_uri(reverse('convite_aceitar', args=[convite.token]))
        enviado = send_mail(
            f'Convite para participar da {convite.empresa.nome} no Nexora',
            f'Você foi convidado para participar da {convite.empresa.nome} no Nexora. '
            f'Acesse o link em até sete dias para criar sua conta: {link}',
            None,
            [convite.email],
        )
        if not enviado:
            raise RuntimeError(f'Não foi possível enviar o convite para {convite.email}.')
        messages.success(request, f'Convite enviado para {convite.email}.')
        return redirect('convites_empresa')


class ConviteAceitarView(View):
    template_name = 'core/convite_aceitar.html'

    def get_convite(self, token):
        convite = get_object_or_404(
            ConviteEmpresa.objects.select_related('empresa'),
            token=token,
            aceita_em__isnull=True,
        )
        if convite.expirado:
            raise PermissionDenied('Este convite expirou.')
        return convite

    def contexto_convite(self, convite, form=None, usuario_existente=False):
        return {
            'convite': convite,
            'form': form,
            'usuario_existente': usuario_existente,
            'login_url': (
                f'{reverse("login")}?{urlencode({"next": reverse("convite_aceitar", args=[convite.token])})}'
            ),
        }

    def get(self, request, **kwargs):
        convite = self.get_convite(kwargs['token'])
        usuario_existente = User.objects.filter(email__iexact=convite.email).first()
        if request.user.is_authenticated:
            if request.user.email.casefold() != convite.email.casefold():
                raise PermissionDenied('Este convite foi enviado para outro endereço de e-mail.')
            if request.user.perfil.empresa_id == convite.empresa_id:
                raise PermissionDenied('Você já faz parte desta empresa.')
            return render(
                request,
                self.template_name,
                self.contexto_convite(convite, usuario_existente=True),
            )
        if usuario_existente:
            return render(
                request,
                self.template_name,
                self.contexto_convite(convite, usuario_existente=True),
            )
        return render(
            request,
            self.template_name,
            self.contexto_convite(convite, CadastroForm(convite=convite)),
        )

    @transaction.atomic
    def post(self, request, **kwargs):
        convite = self.get_convite(kwargs['token'])
        if request.user.is_authenticated:
            usuario = request.user
            if usuario.email.casefold() != convite.email.casefold():
                raise PermissionDenied('Este convite foi enviado para outro endereço de e-mail.')
        else:
            usuario_existente = User.objects.filter(email__iexact=convite.email).first()
            if usuario_existente:
                return redirect(self.contexto_convite(convite)['login_url'])
            form = CadastroForm(request.POST, convite=convite)
            if not form.is_valid():
                return render(
                    request,
                    self.template_name,
                    self.contexto_convite(convite, form),
                    status=400,
                )
            usuario = User.objects.create_user(
                username=form.cleaned_data['nome_usuario'],
                email=convite.email,
                password=form.cleaned_data['senha_usuario'],
            )

        perfil = usuario.perfil
        empresa_individual = perfil.empresa
        if empresa_individual.pk == convite.empresa_id:
            raise PermissionDenied('Você já faz parte desta empresa.')
        if not empresa_individual.perfis.exclude(usuario=usuario).exists():
            Dispositivo.objects.filter(empresa=empresa_individual).update(empresa=convite.empresa)
            if not Parametro.objects.filter(empresa=convite.empresa).exists():
                Parametro.objects.filter(empresa=empresa_individual).update(empresa=convite.empresa)
        perfil.empresa = convite.empresa
        perfil.papel = convite.papel
        perfil.save(update_fields=['empresa', 'papel'])
        if not empresa_individual.perfis.exists():
            empresa_individual.delete()
        convite.aceita_em = timezone.now()
        convite.save(update_fields=['aceita_em'])
        if request.user.is_authenticated:
            messages.success(request, f'Você agora faz parte da empresa {convite.empresa.nome}.')
            return redirect('painel')
        messages.success(request, f'Conta criada e vinculada à empresa {convite.empresa.nome}.')
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
        perfil = usuario.perfil
        empresa = perfil.empresa
        outros_membros = empresa.perfis.exclude(usuario=usuario)
        novo_proprietario = None
        if perfil.papel == PerfilEmpresa.Papel.PROPRIETARIO and outros_membros.exists():
            novo_proprietario = outros_membros.select_related('usuario').order_by('pk').first()
            novo_proprietario.papel = PerfilEmpresa.Papel.PROPRIETARIO
            novo_proprietario.save(update_fields=['papel'])
        elif not outros_membros.exists():
            empresa.delete()
        usuario.delete()
        auth_logout(request)
        if novo_proprietario:
            messages.success(
                request,
                f'A conta foi excluída e a propriedade da empresa passou para '
                f'{novo_proprietario.usuario.username}.',
            )
        elif outros_membros.exists():
            messages.success(
                request,
                'A conta foi excluída; os dados da empresa foram mantidos para os demais membros.',
            )
        else:
            messages.success(request, 'A conta e os dados associados foram excluídos.')
        return redirect('login')


class DispositivoListView(LoginRequiredMixin, ListView):
    template_name = 'core/dispositivos_lista.html'
    context_object_name = 'dispositivos'

    def get_queryset(self):
        return Dispositivo.objects.filter(empresa=self.request.user.perfil.empresa)


class DispositivoCreateView(LoginRequiredMixin, CreateView):
    form_class = DispositivoForm
    template_name = 'core/dispositivo_form.html'
    success_url = reverse_lazy('dispositivo_lista')

    def form_valid(self, form):
        form.instance.dono = self.request.user
        form.instance.empresa = self.request.user.perfil.empresa
        messages.success(self.request, 'Dispositivo cadastrado com sucesso.')
        return super().form_valid(form)


class DispositivoDetailView(LoginRequiredMixin, DetailView):
    template_name = 'core/dispositivo_detalhe.html'
    context_object_name = 'dispositivo'

    def get_queryset(self):
        return Dispositivo.objects.filter(empresa=self.request.user.perfil.empresa)

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['leituras'] = self.object.leituras.all()[:20]
        contexto['ordens_servico'] = self.object.ordens_servico.order_by('criada_em', 'pk')
        contexto['ocorrencias'] = self.object.ocorrencias_causais.select_related(
            'ordem_servico',
        )[:10]
        return contexto


class OrdemServicoCreateView(LoginRequiredMixin, CreateView):
    form_class = OrdemServicoForm
    template_name = 'core/ordem_servico_form.html'

    def get_dispositivo(self):
        return get_object_or_404(
            Dispositivo,
            pk=self.kwargs['dispositivo_pk'],
            empresa=self.request.user.perfil.empresa,
        )

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto['dispositivo'] = self.get_dispositivo()
        return contexto

    def form_valid(self, form):
        form.instance.dispositivo = self.get_dispositivo()
        messages.success(self.request, 'Ordem de serviço criada como rascunho.')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('ordem_servico_detalhe', kwargs={'pk': self.object.pk})


class OrdemServicoDetailView(LoginRequiredMixin, DetailView):
    model = OrdemServico
    template_name = 'core/ordem_servico_detalhe.html'
    context_object_name = 'ordem_servico'

    def get_queryset(self):
        return OrdemServico.objects.filter(
            dispositivo__empresa=self.request.user.perfil.empresa,
        ).select_related(
            'dispositivo',
            'aprovada_por',
            'concluida_por',
        )

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto.setdefault('form_conclusao', ConclusaoOrdemServicoForm())
        return contexto


class OrdemServicoAcaoView(LoginRequiredMixin, View):
    def post(self, request, pk):
        ordem = get_object_or_404(
            OrdemServico.objects.filter(dispositivo__empresa=request.user.perfil.empresa),
            pk=pk,
        )
        acao = request.POST.get('acao')

        try:
            if acao == 'aprovar':
                aprovar_ordem_servico(ordem, request.user)
                messages.success(request, 'Ordem de serviço aprovada.')
            elif acao == 'iniciar':
                iniciar_ordem_servico(ordem)
                messages.success(request, 'Ordem de serviço iniciada.')
            elif acao == 'concluir':
                form = ConclusaoOrdemServicoForm(request.POST)
                if not form.is_valid():
                    return render(
                        request,
                        'core/ordem_servico_detalhe.html',
                        {
                            'ordem_servico': ordem,
                            'form_conclusao': form,
                        },
                        status=400,
                    )
                concluir_ordem_servico(
                    ordem,
                    request.user,
                    **form.cleaned_data,
                )
                messages.success(request, 'Ordem de serviço concluída.')
            else:
                messages.error(request, 'Ação de ordem de serviço inválida.')
        except ValidationError as erro:
            messages.error(request, ' '.join(erro.messages))

        return redirect('ordem_servico_detalhe', pk=ordem.pk)


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

    if 'leituras' in dados:
        return _registrar_leituras_em_lote(dispositivo, dados['leituras'])

    existente = _leitura_existente(dados, dispositivo)
    if existente:
        return JsonResponse(_serializar_leitura(existente, duplicada=True), status=200)

    leitura, erro = _validar_leitura(dados, dispositivo)
    if erro:
        return JsonResponse({'erro': erro}, status=400)
    leitura, criada = _salvar_leitura(leitura)
    return JsonResponse(
        _serializar_leitura(leitura, duplicada=not criada),
        status=201 if criada else 200,
    )


def _validar_decimal_opcional(dados, campo):
    bruto = dados.get(campo)
    if bruto is None or bruto == '':
        return None, None
    try:
        valor = Decimal(str(bruto))
        if not valor.is_finite() or valor < 0:
            raise InvalidOperation
        return valor.quantize(Decimal('0.01')), None
    except (InvalidOperation, ValueError, TypeError):
        return None, f'{campo} deve ser um número válido não negativo.'


def _validar_leitura(dados, dispositivo):
    try:
        valor = Decimal(str(dados.get('valor_kwh')))
        if not valor.is_finite():
            raise InvalidOperation
        valor = valor.quantize(Decimal('0.01'))
    except (InvalidOperation, ValueError, TypeError):
        return None, 'valor_kwh deve ser um número válido.'

    campos_extras = {}
    for campo_decimal in ('temperatura_c', 'corrente_a', 'ruido_db'):
        valor_extra, erro_extra = _validar_decimal_opcional(dados, campo_decimal)
        if erro_extra:
            return None, erro_extra
        if valor_extra is not None:
            campos_extras[campo_decimal] = valor_extra

    if 'alerta_seguranca_nr12' in dados:
        alerta_nr12 = dados.get('alerta_seguranca_nr12')
        if not isinstance(alerta_nr12, bool):
            return None, 'alerta_seguranca_nr12 deve ser booleano.'
        campos_extras['alerta_seguranca_nr12'] = alerta_nr12

    id_externo = dados.get('id_externo')
    if id_externo is not None:
        if not isinstance(id_externo, str) or not id_externo.strip():
            return None, 'id_externo deve ser um texto não vazio.'
        id_externo = id_externo.strip()

    registrado_em = dados.get('registrado_em')
    if registrado_em is not None:
        if not isinstance(registrado_em, str):
            return None, 'registrado_em deve ser uma data ISO válida.'
        registrado_em = parse_datetime(registrado_em)
        if registrado_em is None:
            return None, 'registrado_em deve ser uma data ISO válida.'
        if timezone.is_naive(registrado_em):
            registrado_em = timezone.make_aware(registrado_em)

    campos = {'dispositivo': dispositivo, 'valor_kwh': valor, **campos_extras}
    if id_externo is not None:
        campos['id_externo'] = id_externo
    if registrado_em is not None:
        campos['registrado_em'] = registrado_em
    leitura = Leitura(**campos)
    try:
        leitura.full_clean()
    except ValidationError as erro:
        return None, {
            campo: [str(item) for item in itens]
            for campo, itens in erro.message_dict.items()
        }
    return leitura, None


def _salvar_leitura(leitura):
    leitura.save()
    analisar_telemetria(leitura)
    return leitura, True


def _leitura_existente(dados, dispositivo):
    id_externo = dados.get('id_externo')
    if not isinstance(id_externo, str) or not id_externo.strip():
        return None
    return Leitura.objects.filter(
        dispositivo=dispositivo,
        id_externo=id_externo.strip(),
    ).first()


def _serializar_leitura(leitura, *, duplicada=False):
    resposta = {
        'id': leitura.pk,
        'id_externo': leitura.id_externo,
        'dispositivo': leitura.dispositivo.nome,
        'valor_kwh': str(leitura.valor_kwh),
        'temperatura_c': str(leitura.temperatura_c) if leitura.temperatura_c is not None else None,
        'corrente_a': str(leitura.corrente_a) if leitura.corrente_a is not None else None,
        'ruido_db': str(leitura.ruido_db) if leitura.ruido_db is not None else None,
        'alerta_seguranca_nr12': leitura.alerta_seguranca_nr12,
        'registrado_em': leitura.registrado_em.isoformat(),
    }
    if duplicada:
        resposta['duplicada'] = True
    return resposta


def _registrar_leituras_em_lote(dispositivo, dados):
    if not isinstance(dados, list) or not dados:
        return JsonResponse(
            {'erro': 'leituras deve ser uma lista não vazia.'},
            status=400,
        )

    resultados = []
    erros = []
    leituras_para_salvar = []
    for indice, item in enumerate(dados):
        if not isinstance(item, dict):
            erros.append({'indice': indice, 'erro': 'Cada leitura deve ser um objeto JSON.'})
            continue
        existente = _leitura_existente(item, dispositivo)
        if existente:
            resultados.append(_serializar_leitura(existente, duplicada=True))
            continue
        leitura, erro = _validar_leitura(item, dispositivo)
        if erro:
            erros.append({'indice': indice, 'erro': erro})
            continue
        leituras_para_salvar.append((indice, leitura))

    for indice, leitura in leituras_para_salvar:
        try:
            with transaction.atomic():
                leitura.save()
                analisar_telemetria(leitura)
        except IntegrityError:
            existente = _leitura_existente(
                {'id_externo': leitura.id_externo},
                dispositivo,
            )
            if existente:
                resultados.append(_serializar_leitura(existente, duplicada=True))
            else:
                erros.append({'indice': indice, 'erro': 'Leitura duplicada ou inválida.'})
        else:
            resultados.append(_serializar_leitura(leitura))

    return JsonResponse(
        {
            'criadas': sum('duplicada' not in item for item in resultados),
            'duplicadas': sum('duplicada' in item for item in resultados),
            'erros': erros,
            'leituras': resultados,
        },
        status=201 if not erros else 207,
    )


class Painel(LoginRequiredMixin, TemplateView):
    template_name = 'core/painel.html'

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        empresa = self.request.user.perfil.empresa
        contexto['resumo'] = calcular_anomalias(self.request.user)
        contexto['eficiencia'] = calcular_eficiencia_co2(self.request.user)
        contexto['maturidade'] = calcular_maturidade_operacional(self.request.user)
        contexto['missoes'] = sincronizar_missoes(self.request.user)
        contexto['ocorrencias'] = (
            OcorrenciaCausal.objects.filter(dispositivo__empresa=empresa)
            .select_related('dispositivo', 'ordem_servico')[:10]
        )
        return contexto


class DossieAuditoriaView(LoginRequiredMixin, View):
    template_name = 'core/dossie_auditoria.html'

    def dispatch(self, request, *args, **kwargs):
        if (
            request.user.is_authenticated
            and request.user.perfil.papel == PerfilEmpresa.Papel.MANUTENCAO
        ):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        empresa = request.user.perfil.empresa
        dossies = DossieAuditoria.objects.filter(empresa=empresa)[:10]
        return render(
            request,
            self.template_name,
            {
                'dossies': dossies,
                'maturidade': calcular_maturidade_operacional(request.user),
                'eficiencia': calcular_eficiencia_co2(request.user),
            },
        )

    def post(self, request):
        dossie = emitir_dossie_auditoria(request.user)
        messages.success(
            request,
            f'Dossiê digital auditável #{dossie.pk} emitido com hash {dossie.hash_sha256[:16]}…',
        )
        return redirect('dossie_auditoria')


class DossieExportarView(LoginRequiredMixin, View):
    def dispatch(self, request, *args, **kwargs):
        if (
            request.user.is_authenticated
            and request.user.perfil.papel == PerfilEmpresa.Papel.MANUTENCAO
        ):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, pk, formato):
        dossie = get_object_or_404(
            DossieAuditoria,
            pk=pk,
            empresa=request.user.perfil.empresa,
        )
        if formato == 'json':
            conteudo = exportar_dossie_json(dossie)
            resposta = HttpResponse(
                conteudo,
                content_type='application/json; charset=utf-8',
            )
            resposta['Content-Disposition'] = f'attachment; filename="dossie-nexora-{dossie.pk}.json"'
            return resposta
        if formato == 'pdf':
            conteudo_pdf = exportar_dossie_pdf(dossie)
            resposta = HttpResponse(conteudo_pdf, content_type='application/pdf')
            resposta['Content-Disposition'] = f'attachment; filename="dossie-nexora-{dossie.pk}.pdf"'
            return resposta
        return JsonResponse({'erro': 'Formato de exportação inválido.'}, status=400)


class CreditoBNDESView(LoginRequiredMixin, View):
    template_name = 'core/credito_bndes.html'

    def get(self, request):
        return render(request, self.template_name, {'form': CreditoBNDESForm()})

    def post(self, request):
        form = CreditoBNDESForm(request.POST)
        resultado = None
        if form.is_valid():
            resultado = estimar_credito_bndes(**form.cleaned_data)
        return render(
            request,
            self.template_name,
            {'form': form, 'resultado': resultado},
        )


class ParametrosView(LoginRequiredMixin, UpdateView):
    form_class = ParametroForm
    template_name = 'core/parametros.html'
    success_url = reverse_lazy('painel')

    def dispatch(self, request, *args, **kwargs):
        if (
            request.user.is_authenticated
            and request.user.perfil.papel == PerfilEmpresa.Papel.MANUTENCAO
        ):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        return obter_parametro(self.request.user)

    def form_valid(self, form):
        messages.success(self.request, 'Tarifa salva com sucesso.')
        return super().form_valid(form)
