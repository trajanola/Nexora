from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import Count, F, Q, Sum
from django.db import transaction
from django.utils import timezone

from .models import Dispositivo, OrdemServico, Parametro

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


def calcular_eficiencia_co2(usuario, agora=None):
    inicio = inicio_do_mes(agora)
    fim = (inicio + timedelta(days=32)).replace(day=1)
    empresa = usuario.perfil.empresa
    parametro = obter_parametro(usuario)
    consumo_real = (
        Dispositivo.objects.filter(empresa=empresa)
        .aggregate(
            total=Sum(
                'leituras__valor_kwh',
                filter=Q(
                    leituras__registrado_em__gte=inicio,
                    leituras__registrado_em__lt=fim,
                ),
            ),
        )['total']
        or Decimal('0.00')
    )
    base = parametro.consumo_base_mensal_kwh
    economia_kwh = max(base - consumo_real, Decimal('0.00'))
    percentual = (
        (economia_kwh / base * Decimal('100')).quantize(Decimal('0.01'))
        if base > 0
        else None
    )
    co2_evitado = (economia_kwh * parametro.fator_emissao_co2).quantize(Decimal('0.01'))
    return {
        'consumo_real_kwh': consumo_real,
        'consumo_base_kwh': base,
        'economia_kwh': economia_kwh,
        'eficiencia_percentual': percentual,
        'co2_evitado_kg': co2_evitado,
    }


def estimar_credito_bndes(
    *,
    valor_investimento,
    percentual_financiado,
    taxa_juros_anual,
    prazo_meses,
    percentual_desconto,
):
    valor_investimento = Decimal(valor_investimento)
    percentual_financiado = Decimal(percentual_financiado)
    taxa_juros_anual = Decimal(taxa_juros_anual)
    prazo_meses = int(prazo_meses)
    percentual_desconto = Decimal(percentual_desconto)
    valor_financiado = (
        valor_investimento * percentual_financiado / Decimal('100')
    ).quantize(CENTAVOS)
    desconto = (
        valor_financiado * percentual_desconto / Decimal('100')
    ).quantize(CENTAVOS)
    principal = valor_financiado - desconto
    taxa_mensal = (taxa_juros_anual / Decimal('100') / Decimal('12'))
    if taxa_mensal == 0:
        parcela = (principal / prazo_meses).quantize(CENTAVOS)
    else:
        fator = (Decimal('1') + taxa_mensal) ** prazo_meses
        parcela = (principal * taxa_mensal * fator / (fator - Decimal('1'))).quantize(CENTAVOS)
    total_pago = (parcela * prazo_meses).quantize(CENTAVOS)
    return {
        'valor_financiado': valor_financiado,
        'valor_desconto': desconto,
        'valor_financiado_liquido': principal.quantize(CENTAVOS),
        'parcela_mensal': parcela,
        'total_pago': total_pago,
    }


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
