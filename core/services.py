from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import Count, F, Q, Sum
from django.db import transaction
from django.utils import timezone

from .models import Dispositivo, Leitura, OcorrenciaCausal, OrdemServico, Parametro

CENTAVOS = Decimal('0.01')
JANELA_CORRELACAO = timedelta(minutes=5)
NOMES_SINAIS = {
    'consumo': 'consumo de energia acima do limite',
    'corrente': 'pico de corrente',
    'temperatura': 'elevação de temperatura',
    'ruido': 'elevação de ruído',
    'nr12': 'violação de segurança NR-12',
}
ORDEM_SEVERIDADE = [
    OcorrenciaCausal.Severidade.MEDIA,
    OcorrenciaCausal.Severidade.ALTA,
    OcorrenciaCausal.Severidade.CRITICA,
]


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


def sinais_da_leitura(leitura):
    dispositivo = leitura.dispositivo
    sinais = set()
    if leitura.valor_kwh is not None and leitura.valor_kwh > dispositivo.limite_kwh:
        sinais.add('consumo')
    if leitura.corrente_a is not None and leitura.corrente_a > dispositivo.limite_corrente_a:
        sinais.add('corrente')
    if (
        leitura.temperatura_c is not None
        and leitura.temperatura_c > dispositivo.limite_temperatura_c
    ):
        sinais.add('temperatura')
    if leitura.ruido_db is not None and leitura.ruido_db > dispositivo.limite_ruido_db:
        sinais.add('ruido')
    if leitura.alerta_seguranca_nr12:
        sinais.add('nr12')
    return sinais


def diagnosticar_causa_raiz(sinais):
    if 'nr12' in sinais:
        return (
            'Violação de dispositivo de segurança em máquina (NR-12)',
            'Violação de proteção ou intertravamento de segurança detectada. '
            'Interrompa a operação e inspecione os dispositivos de segurança (NR-12).',
        )
    if 'ruido' in sinais and ('temperatura' in sinais or 'corrente' in sinais):
        return (
            'Degradação de lubrificante mecânico',
            'Degradação de lubrificante mecânico provocando atrito e elevação de ruído.',
        )
    if 'corrente' in sinais and 'temperatura' in sinais:
        return (
            'Sobrecarga eletromecânica do motor',
            'Pico de corrente com elevação de temperatura nos enrolamentos; '
            'inspecione carga mecânica, ventilação e isolamento do motor.',
        )
    if 'corrente' in sinais and 'consumo' in sinais:
        return (
            'Esforço mecânico excessivo em operação',
            'Elevação simultânea de corrente e consumo de energia; '
            'verifique alinhamento, correias e desgaste de ferramentas.',
        )
    if 'temperatura' in sinais and 'consumo' in sinais:
        return (
            'Dissipação térmica anormal com desperdício energético',
            'Superaquecimento associado a consumo excedente; '
            'verifique sistema de arrefecimento e atrito nos mancais.',
        )
    if 'ruido' in sinais:
        return (
            'Exposição ocupacional a ruído acima do limite (NR-15)',
            'Nível de ruído acima do limite regulatório da NR-15; '
            'avalie enclausuramento acústico, manutenção preventiva e EPIs.',
        )
    descricao = ', '.join(NOMES_SINAIS[s] for s in sorted(sinais))
    return (
        'Anomalia multivariável correlacionada',
        f'Sinais simultâneos detectados ({descricao}); realize inspeção técnica na máquina.',
    )


def _classificar_norma(sinais):
    tem_nr12 = 'nr12' in sinais
    tem_nr15 = 'ruido' in sinais
    if tem_nr12 and tem_nr15:
        return OcorrenciaCausal.Norma.NR12_NR15
    if tem_nr12:
        return OcorrenciaCausal.Norma.NR12
    if tem_nr15:
        return OcorrenciaCausal.Norma.NR15
    return OcorrenciaCausal.Norma.NENHUMA


def _classificar_severidade(sinais, norma):
    if norma in (OcorrenciaCausal.Norma.NR12, OcorrenciaCausal.Norma.NR12_NR15):
        return OcorrenciaCausal.Severidade.CRITICA
    if norma == OcorrenciaCausal.Norma.NR15 or len(sinais) >= 3:
        return OcorrenciaCausal.Severidade.ALTA
    return OcorrenciaCausal.Severidade.MEDIA


def _garantir_os_corretiva_automatica(ocorrencia):
    if ocorrencia.norma == OcorrenciaCausal.Norma.NENHUMA or ocorrencia.ordem_servico_id:
        return ocorrencia.ordem_servico
    sigla = ocorrencia.get_norma_display().split(' (')[0]
    ordem = OrdemServico.objects.create(
        dispositivo=ocorrencia.dispositivo,
        resumo=f'[Alerta {sigla}] {ocorrencia.causa_raiz}'[:160],
        descricao=(
            f'Ordem de Serviço Corretiva gerada automaticamente por desvio regulatório '
            f'({ocorrencia.get_norma_display()}).\n'
            f'Diagnóstico prescritivo: {ocorrencia.mensagem_prescritiva}\n'
            f'Sinais correlacionados: {ocorrencia.sinais_correlacionados}'
        ),
        status=OrdemServico.Status.RASCUNHO,
    )
    ocorrencia.ordem_servico = ordem
    ocorrencia.save(update_fields=['ordem_servico'])
    return ordem


@transaction.atomic
def analisar_telemetria(leitura):
    sinais_leitura = sinais_da_leitura(leitura)
    if not sinais_leitura:
        return None

    inicio_janela = leitura.registrado_em - JANELA_CORRELACAO
    fim_janela = leitura.registrado_em + JANELA_CORRELACAO
    leituras_proximas = list(
        Leitura.objects.filter(
            dispositivo=leitura.dispositivo,
            registrado_em__gte=inicio_janela,
            registrado_em__lte=fim_janela,
        ).select_related('dispositivo')
    )

    sinais_acumulados = set(sinais_leitura)
    eventos_com_sinal = 0
    for item in leituras_proximas:
        sinais_item = sinais_da_leitura(item)
        if sinais_item:
            eventos_com_sinal += 1
            sinais_acumulados |= sinais_item

    norma = _classificar_norma(sinais_acumulados)
    if len(sinais_acumulados) < 2 and norma == OcorrenciaCausal.Norma.NENHUMA:
        return None

    causa_raiz, mensagem_prescritiva = diagnosticar_causa_raiz(sinais_acumulados)
    severidade = _classificar_severidade(sinais_acumulados, norma)
    sinais_texto = ', '.join(NOMES_SINAIS[s] for s in sorted(sinais_acumulados))[:255]

    existente = (
        OcorrenciaCausal.objects.select_for_update()
        .filter(
            dispositivo=leitura.dispositivo,
            detectada_em__gte=inicio_janela,
            detectada_em__lte=fim_janela,
        )
        .first()
    )
    if existente:
        existente.causa_raiz = causa_raiz
        existente.mensagem_prescritiva = mensagem_prescritiva
        existente.sinais_correlacionados = sinais_texto
        existente.quantidade_eventos = max(existente.quantidade_eventos + 1, eventos_com_sinal)
        existente.norma = norma
        if ORDEM_SEVERIDADE.index(severidade) > ORDEM_SEVERIDADE.index(existente.severidade):
            existente.severidade = severidade
        existente.save()
        _garantir_os_corretiva_automatica(existente)
        return existente

    ocorrencia = OcorrenciaCausal.objects.create(
        dispositivo=leitura.dispositivo,
        causa_raiz=causa_raiz,
        mensagem_prescritiva=mensagem_prescritiva,
        sinais_correlacionados=sinais_texto,
        quantidade_eventos=max(1, eventos_com_sinal),
        severidade=severidade,
        norma=norma,
        detectada_em=leitura.registrado_em,
    )
    _garantir_os_corretiva_automatica(ocorrencia)
    return ocorrencia
