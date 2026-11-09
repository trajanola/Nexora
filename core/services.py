from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, F, Q, Sum
from django.utils import timezone

from .models import (
    Dispositivo,
    EventoSinal,
    OcorrenciaAnomalia,
    OrdemServico,
    Parametro,
)

CENTAVOS = Decimal('0.01')


def obter_parametro(usuario):
    parametro, _ = Parametro.objects.get_or_create(empresa=usuario.perfil.empresa)
    return parametro


def inicio_do_mes(agora=None):
    agora = timezone.localtime(agora or timezone.now())
    return agora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def calcular_anomalias(usuario, agora=None):
    inicio = inicio_do_mes(agora)
    tarifa = obter_parametro(usuario).tarifa_kwh
    acima_do_limite = Q(
        leituras__registrado_em__gte=inicio,
        leituras__valor_kwh__gt=F('limite_kwh'),
    )
    dispositivos = Dispositivo.objects.filter(empresa=usuario.perfil.empresa).annotate(
        qtd_anomalias=Count('leituras', filter=acima_do_limite),
        soma_anomalias=Sum('leituras__valor_kwh', filter=acima_do_limite),
    )

    itens = []
    for dispositivo in dispositivos:
        quantidade = dispositivo.qtd_anomalias or 0
        soma = dispositivo.soma_anomalias or Decimal('0')
        excedente = soma - dispositivo.limite_kwh * quantidade
        custo = (excedente * tarifa).quantize(CENTAVOS)
        itens.append({
            'dispositivo': dispositivo,
            'qtd_anomalias': quantidade,
            'excedente_kwh': excedente,
            'custo': custo,
            'payback_meses': (
                (dispositivo.custo_reparo / custo).quantize(CENTAVOS)
                if dispositivo.custo_reparo is not None and custo > 0
                else None
            ),
        })

    com_anomalia = [item for item in itens if item['excedente_kwh'] > 0]
    return {
        'tarifa': tarifa,
        'itens': itens,
        'com_anomalia': com_anomalia,
        'custo_total': sum(
            (item['custo'] for item in com_anomalia),
            Decimal('0.00'),
        ),
    }


def calcular_eficiencia_energetica(usuario, agora=None):
    agora = timezone.localtime(agora or timezone.now())
    inicio_atual = inicio_do_mes(agora)
    inicio_anterior = inicio_atual - timedelta(days=1)
    inicio_anterior = inicio_anterior.replace(day=1)
    fim_anterior = min(inicio_anterior + (agora - inicio_atual), inicio_atual)
    empresa = usuario.perfil.empresa

    consumo_atual = (
        Dispositivo.objects.filter(empresa=empresa)
        .aggregate(total=Sum(
            'leituras__valor_kwh',
            filter=Q(
                leituras__registrado_em__gte=inicio_atual,
                leituras__registrado_em__lt=agora,
            ),
        ))['total']
        or Decimal('0.00')
    )
    consumo_anterior = (
        Dispositivo.objects.filter(empresa=empresa)
        .aggregate(total=Sum(
            'leituras__valor_kwh',
            filter=Q(
                leituras__registrado_em__gte=inicio_anterior,
                leituras__registrado_em__lt=fim_anterior,
            ),
        ))['total']
        or Decimal('0.00')
    )
    economia_kwh = max(consumo_anterior - consumo_atual, Decimal('0.00'))
    pontuacao = (
        (economia_kwh * Decimal('100') / consumo_anterior).quantize(CENTAVOS)
        if consumo_anterior > 0
        else Decimal('0.00')
    )
    fator_emissao = obter_parametro(usuario).fator_emissao_co2e
    maximo_grafico = max(consumo_atual, consumo_anterior, Decimal('1.00'))

    return {
        'consumo_atual_kwh': consumo_atual,
        'consumo_anterior_kwh': consumo_anterior,
        'maximo_grafico_kwh': maximo_grafico,
        'economia_kwh': economia_kwh,
        'co2e_evitado_kg': (economia_kwh * fator_emissao).quantize(CENTAVOS),
        'fator_emissao_co2e': fator_emissao,
        'pontuacao_eficiencia': pontuacao,
        'inicio_atual': inicio_atual,
        'inicio_anterior': inicio_anterior,
    }


def estimar_economia_bndes(valor_financiado, pontuacao_eficiencia):
    spread_percentual = Decimal('1.5') * pontuacao_eficiencia / Decimal('100')
    spread = spread_percentual / Decimal('100')
    return {
        'spread_estimado_pp': spread_percentual.quantize(CENTAVOS),
        'economia_anual': (valor_financiado * spread).quantize(CENTAVOS),
    }


def _causa_prescritiva(tipos):
    tipos = set(tipos)
    if {EventoSinal.Tipo.TEMPERATURA, EventoSinal.Tipo.RUIDO} <= tipos:
        return (
            'Degradação de lubrificante mecânico',
            'Degradação de lubrificante mecânico provocando atrito e elevação de ruído',
        )
    if {EventoSinal.Tipo.CORRENTE, EventoSinal.Tipo.RUIDO} <= tipos:
        return (
            'Desbalanceamento mecânico',
            'Verificar desbalanceamento mecânico: elevação simultânea de corrente e ruído',
        )
    if {EventoSinal.Tipo.CORRENTE, EventoSinal.Tipo.TEMPERATURA} <= tipos:
        return (
            'Sobrecarga elétrica',
            'Inspecionar sobrecarga elétrica associada ao aquecimento do equipamento',
        )
    return (
        'Anomalia multivariável',
        'Inspecionar o equipamento e verificar a causa dos sinais simultâneos detectados',
    )


def _atualizar_diagnostico(ocorrencia):
    eventos = list(ocorrencia.eventos.select_related('dispositivo'))
    tipos = {evento.tipo for evento in eventos}
    ocorrencia.causa, ocorrencia.mensagem_prescritiva = _causa_prescritiva(tipos)
    ocorrencia.save(update_fields=['causa', 'mensagem_prescritiva'])
    resumo = f'Investigar: {ocorrencia.causa}'[:160]
    descricao = (
        f'{ocorrencia.mensagem_prescritiva}\n'
        'Sinais correlacionados: '
        + ', '.join(
            f'{evento.get_tipo_display()} {evento.valor} {evento.unidade}'
            for evento in eventos
        )
    )
    if ocorrencia.ordem_servico_id is None:
        ocorrencia.ordem_servico = OrdemServico.objects.create(
            dispositivo=ocorrencia.dispositivo,
            resumo=resumo,
            descricao=descricao,
        )
        ocorrencia.save(update_fields=['ordem_servico'])
    else:
        ocorrencia.ordem_servico.resumo = resumo
        ocorrencia.ordem_servico.descricao = descricao
        ocorrencia.ordem_servico.save(update_fields=['resumo', 'descricao', 'atualizada_em'])
    return ocorrencia


@transaction.atomic
def registrar_evento_sinal(evento):
    dispositivo = Dispositivo.objects.select_for_update().get(pk=evento.dispositivo_id)
    if evento.id_externo:
        existente = EventoSinal.objects.filter(
            dispositivo=dispositivo,
            id_externo=evento.id_externo,
        ).first()
        if existente:
            ocorrencia = existente.ocorrencias.select_related('ordem_servico').first()
            return existente, ocorrencia, False

    evento.dispositivo = dispositivo
    evento.save(force_insert=True)

    janela = timedelta(minutes=5)
    inicio_janela = evento.registrado_em - janela
    fim_janela = evento.registrado_em + janela
    ocorrencia = (
        OcorrenciaAnomalia.objects.filter(
            dispositivo=dispositivo,
            eventos__registrado_em__gte=inicio_janela,
            eventos__registrado_em__lte=fim_janela,
        )
        .distinct()
        .order_by('criada_em')
        .first()
    )

    if ocorrencia:
        ocorrencia.eventos.add(evento)
    else:
        eventos_correlacionados = list(
            EventoSinal.objects.filter(
                dispositivo=dispositivo,
                registrado_em__gte=inicio_janela,
                registrado_em__lte=fim_janela,
            ).exclude(pk=evento.pk)
        )
        if len({evento.tipo, *(item.tipo for item in eventos_correlacionados)}) < 2:
            return evento, None, True

        causa, mensagem = _causa_prescritiva(
            {evento.tipo, *(item.tipo for item in eventos_correlacionados)}
        )
        ocorrencia = OcorrenciaAnomalia.objects.create(
            dispositivo=dispositivo,
            causa=causa,
            mensagem_prescritiva=mensagem,
            criada_em=evento.registrado_em,
        )
        ocorrencia.eventos.set([*eventos_correlacionados, evento])

    return evento, _atualizar_diagnostico(ocorrencia), True


@transaction.atomic
def aprovar_ordem_servico(ordem_servico, usuario):
    ordem = OrdemServico.objects.select_for_update().get(pk=ordem_servico.pk)
    if ordem.status != OrdemServico.Status.RASCUNHO:
        raise ValidationError('Somente ordens em rascunho podem ser aprovadas.')

    ordem.status = OrdemServico.Status.APROVADA
    ordem.aprovada_em = timezone.now()
    ordem.aprovada_por = usuario
    ordem.save(update_fields=['status', 'aprovada_em', 'aprovada_por', 'atualizada_em'])
    return ordem


@transaction.atomic
def iniciar_ordem_servico(ordem_servico):
    ordem = OrdemServico.objects.select_for_update().get(pk=ordem_servico.pk)
    if ordem.status != OrdemServico.Status.APROVADA:
        raise ValidationError('Somente ordens aprovadas podem entrar em execução.')

    ordem.status = OrdemServico.Status.EM_EXECUCAO
    ordem.save(update_fields=['status', 'atualizada_em'])
    return ordem


@transaction.atomic
def concluir_ordem_servico(
    ordem_servico,
    usuario,
    *,
    causa_confirmada,
    acao_realizada,
    tempo_parada_minutos,
):
    ordem = OrdemServico.objects.select_for_update().get(pk=ordem_servico.pk)
    if ordem.status != OrdemServico.Status.EM_EXECUCAO:
        raise ValidationError('Somente ordens em execução podem ser concluídas.')
    if not causa_confirmada.strip() or not acao_realizada.strip():
        raise ValidationError('Informe a causa confirmada e a ação realizada.')
    if tempo_parada_minutos < 0:
        raise ValidationError('O tempo de parada não pode ser negativo.')

    ordem.status = OrdemServico.Status.CONCLUIDA
    ordem.causa_confirmada = causa_confirmada.strip()
    ordem.acao_realizada = acao_realizada.strip()
    ordem.tempo_parada_minutos = tempo_parada_minutos
    ordem.concluida_em = timezone.now()
    ordem.concluida_por = usuario
    ordem.save(update_fields=[
        'status',
        'causa_confirmada',
        'acao_realizada',
        'tempo_parada_minutos',
        'concluida_em',
        'concluida_por',
        'atualizada_em',
    ])
    return ordem
