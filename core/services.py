import hashlib
import hmac
import json
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Count, F, Q, Sum
from django.db import transaction
from django.utils import timezone

from .models import (
    Dispositivo,
    DossieAuditoria,
    Leitura,
    MissaoOperacional,
    OcorrenciaCausal,
    OrdemServico,
    Parametro,
)

CENTAVOS = Decimal('0.01')
ESTAGIOS_MATURIDADE = [
    (0, 'Reativo'),
    (25, 'Preventivo'),
    (50, 'Preditivo'),
    (75, 'Prescritivo'),
]
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


def _estagio_por_nota(nota):
    atual = ESTAGIOS_MATURIDADE[0]
    proximo = None
    for indice, (minimo, nome) in enumerate(ESTAGIOS_MATURIDADE):
        if nota >= minimo:
            atual = (minimo, nome)
            proximo = (
                ESTAGIOS_MATURIDADE[indice + 1]
                if indice + 1 < len(ESTAGIOS_MATURIDADE)
                else None
            )
    return atual, proximo


def calcular_maturidade_operacional(usuario, agora=None):
    agora = agora or timezone.now()
    janela = agora - timedelta(days=30)
    empresa = usuario.perfil.empresa
    dispositivos = Dispositivo.objects.filter(empresa=empresa)
    total_dispositivos = dispositivos.count()
    leituras = Leitura.objects.filter(
        dispositivo__empresa=empresa,
        registrado_em__gte=janela,
    )
    total_leituras = leituras.count()

    ativos = dispositivos.filter(leituras__registrado_em__gte=janela).distinct().count()
    cobertura = (
        Decimal(ativos) / Decimal(total_dispositivos) * Decimal('30')
        if total_dispositivos
        else Decimal('0')
    )

    if total_leituras:
        anomalas = leituras.filter(valor_kwh__gt=F('dispositivo__limite_kwh')).count()
        estabilidade = (Decimal('1') - Decimal(anomalas) / Decimal(total_leituras)) * Decimal('30')
        multivariaveis = leituras.filter(
            Q(temperatura_c__isnull=False)
            | Q(corrente_a__isnull=False)
            | Q(ruido_db__isnull=False)
        ).count()
        sensoriamento = Decimal(multivariaveis) / Decimal(total_leituras) * Decimal('20')
    else:
        estabilidade = Decimal('0')
        sensoriamento = Decimal('0')

    ordens = OrdemServico.objects.filter(dispositivo__empresa=empresa)
    total_ordens = ordens.count()
    concluidas = ordens.filter(status=OrdemServico.Status.CONCLUIDA).count()
    manutencao = (
        Decimal(concluidas) / Decimal(total_ordens) * Decimal('15')
        if total_ordens
        else Decimal('0')
    )
    ocorrencias_nr = OcorrenciaCausal.objects.filter(
        dispositivo__empresa=empresa,
    ).exclude(norma=OcorrenciaCausal.Norma.NENHUMA).count()
    if total_leituras and ocorrencias_nr == 0:
        manutencao += Decimal('5')

    componentes = {
        chave: int(valor.quantize(Decimal('1'), rounding=ROUND_HALF_UP))
        for chave, valor in {
            'cobertura': cobertura,
            'estabilidade': estabilidade,
            'sensoriamento': sensoriamento,
            'manutencao': manutencao,
        }.items()
    }
    nota = max(0, min(100, sum(componentes.values())))
    (minimo, estagio), proximo = _estagio_por_nota(nota)
    if proximo:
        faixa = proximo[0] - minimo
        progresso_pct = int((nota - minimo) / faixa * 100)
        percentual_para_proximo = 100 - progresso_pct
        pontos_para_proximo = proximo[0] - nota
        proximo_estagio = proximo[1]
    else:
        progresso_pct = 100
        percentual_para_proximo = 0
        pontos_para_proximo = 0
        proximo_estagio = None

    return {
        'nota': nota,
        'estagio': estagio,
        'proximo_estagio': proximo_estagio,
        'pontos_para_proximo': pontos_para_proximo,
        'progresso_pct': progresso_pct,
        'percentual_para_proximo': percentual_para_proximo,
        'componentes': componentes,
    }


def _catalogo_missoes(empresa):
    dispositivos = list(Dispositivo.objects.filter(empresa=empresa))
    leituras_empresa = Leitura.objects.filter(dispositivo__empresa=empresa)
    catalogo = [
        {
            'codigo': 'primeiro-dispositivo',
            'titulo': 'Cadastrar o primeiro dispositivo monitorado',
            'descricao': 'Cadastre uma máquina com nome, localização e limite de consumo (kWh).',
            'pontos': 15,
            'concluida': bool(dispositivos),
        },
        {
            'codigo': 'primeira-leitura',
            'titulo': 'Sincronizar leituras de telemetria pela API',
            'descricao': 'Envie leituras de consumo da máquina usando o token do dispositivo.',
            'pontos': 20,
            'concluida': leituras_empresa.exists(),
        },
    ]
    for disp in dispositivos:
        catalogo.append({
            'codigo': f'sensor-multivariavel-{disp.pk}',
            'titulo': f'Instalar sensor multivariável na {disp.nome}',
            'descricao': (
                f'Envie leituras com temperatura_c, corrente_a ou ruido_db para {disp.nome} '
                'para ativar o diagnóstico causal e aumentar o ROI.'
            ),
            'pontos': 15,
            'concluida': disp.leituras.filter(
                Q(temperatura_c__isnull=False)
                | Q(corrente_a__isnull=False)
                | Q(ruido_db__isnull=False)
            ).exists(),
        })
        catalogo.append({
            'codigo': f'custo-reparo-{disp.pk}',
            'titulo': f'Informar custo de reparo preventivo na {disp.nome}',
            'descricao': f'Defina o custo de reparo da {disp.nome} para calcular o payback automático.',
            'pontos': 10,
            'concluida': disp.custo_reparo is not None,
        })
    catalogo.append({
        'codigo': 'concluir-os',
        'titulo': 'Concluir uma Ordem de Serviço com causa confirmada',
        'descricao': 'Aprove, inicie e conclua uma OS registrando causa, ação e tempo de parada.',
        'pontos': 15,
        'concluida': OrdemServico.objects.filter(
            dispositivo__empresa=empresa,
            status=OrdemServico.Status.CONCLUIDA,
        ).exists(),
    })
    return catalogo


@transaction.atomic
def sincronizar_missoes(usuario):
    empresa = usuario.perfil.empresa
    agora = timezone.now()
    for prioridade, item in enumerate(_catalogo_missoes(empresa), start=1):
        missao, _ = MissaoOperacional.objects.get_or_create(
            empresa=empresa,
            codigo=item['codigo'],
            defaults={
                'titulo': item['titulo'],
                'descricao': item['descricao'],
                'pontos_ganho': item['pontos'],
                'prioridade': prioridade,
            },
        )
        campos_atualizados = []
        if missao.titulo != item['titulo']:
            missao.titulo = item['titulo']
            campos_atualizados.append('titulo')
        if missao.prioridade != prioridade:
            missao.prioridade = prioridade
            campos_atualizados.append('prioridade')
        if item['concluida'] and missao.status != MissaoOperacional.Status.CONCLUIDA:
            missao.status = MissaoOperacional.Status.CONCLUIDA
            missao.concluida_em = agora
            campos_atualizados.extend(['status', 'concluida_em'])
        elif not item['concluida'] and missao.status == MissaoOperacional.Status.CONCLUIDA:
            missao.status = MissaoOperacional.Status.PENDENTE
            missao.concluida_em = None
            campos_atualizados.extend(['status', 'concluida_em'])
        if campos_atualizados:
            missao.save(update_fields=campos_atualizados)

    pendentes = MissaoOperacional.objects.filter(
        empresa=empresa,
        status=MissaoOperacional.Status.PENDENTE,
    ).order_by('prioridade', 'pk')
    concluidas = MissaoOperacional.objects.filter(
        empresa=empresa,
        status=MissaoOperacional.Status.CONCLUIDA,
    ).order_by('-concluida_em', 'prioridade')
    return {
        'prioritarias': list(pendentes[:3]),
        'concluidas': list(concluidas[:5]),
        'total_pendentes': pendentes.count(),
    }


def _serializar_decimal(valor):
    if isinstance(valor, Decimal):
        return str(valor)
    raise TypeError(f'Tipo não serializável: {type(valor)}')


def json_canonico(dados):
    return json.dumps(
        dados,
        sort_keys=True,
        ensure_ascii=False,
        separators=(',', ':'),
        default=_serializar_decimal,
    )


def assinar_payload(payload_json):
    return hmac.new(
        settings.SECRET_KEY.encode('utf-8'),
        payload_json.encode('utf-8'),
        hashlib.sha256,
    ).hexdigest()


@transaction.atomic
def emitir_dossie_auditoria(usuario, agora=None):
    empresa = usuario.perfil.empresa
    carimbo = (agora or timezone.now()).replace(microsecond=0)
    maturidade = calcular_maturidade_operacional(usuario, agora=carimbo)
    eficiencia = calcular_eficiencia_co2(usuario, agora=carimbo)
    anomalias = calcular_anomalias(usuario, agora=carimbo)
    ocorrencias = OcorrenciaCausal.objects.filter(dispositivo__empresa=empresa)
    ordens = OrdemServico.objects.filter(dispositivo__empresa=empresa)

    evidencias = {
        'emissor': 'Nexora Compliance B2B',
        'versao': 1,
        'empresa': {
            'id': empresa.pk,
            'nome': empresa.nome,
        },
        'carimbo_data_hora': carimbo.isoformat(),
        'resumo_executivo': {
            'nota_maturidade': maturidade['nota'],
            'estagio_maturidade': maturidade['estagio'],
            'proximo_estagio': maturidade['proximo_estagio'],
            'percentual_para_proximo_nivel': maturidade['percentual_para_proximo'],
            'componentes_maturidade': maturidade['componentes'],
        },
        'historico_eficiencia_energetica': {
            'consumo_real_kwh': eficiencia['consumo_real_kwh'],
            'consumo_base_kwh': eficiencia['consumo_base_kwh'],
            'economia_kwh': eficiencia['economia_kwh'],
            'eficiencia_percentual': eficiencia['eficiencia_percentual'],
            'co2_evitado_kg': eficiencia['co2_evitado_kg'],
            'custo_anomalias_mes_rs': anomalias['custo_total'],
        },
        'indices_seguranca': {
            'alertas_nr12': ocorrencias.filter(
                norma__in=[OcorrenciaCausal.Norma.NR12, OcorrenciaCausal.Norma.NR12_NR15]
            ).count(),
            'alertas_nr15': ocorrencias.filter(
                norma__in=[OcorrenciaCausal.Norma.NR15, OcorrenciaCausal.Norma.NR12_NR15]
            ).count(),
            'ocorrencias_causais_total': ocorrencias.count(),
            'ordens_servico_concluidas': ordens.filter(
                status=OrdemServico.Status.CONCLUIDA
            ).count(),
            'ordens_servico_total': ordens.count(),
        },
        'telemetria': {
            'dispositivos_monitorados': Dispositivo.objects.filter(empresa=empresa).count(),
            'leituras_auditadas': Leitura.objects.filter(dispositivo__empresa=empresa).count(),
        },
    }
    payload = json_canonico(evidencias)
    hash_sha256 = hashlib.sha256(payload.encode('utf-8')).hexdigest()
    assinatura = assinar_payload(payload)
    return DossieAuditoria.objects.create(
        empresa=empresa,
        gerado_por=usuario,
        carimbo_data_hora=carimbo,
        hash_sha256=hash_sha256,
        assinatura_hmac=assinatura,
        nota_maturidade=maturidade['nota'],
        estagio_maturidade=maturidade['estagio'],
        payload_json=payload,
    )


def exportar_dossie_json(dossie):
    return json.dumps(
        {
            'dossie_id': dossie.pk,
            'carimbo_data_hora': dossie.carimbo_data_hora.isoformat(),
            'hash_sha256': dossie.hash_sha256,
            'assinatura_hmac': dossie.assinatura_hmac,
            'evidencias': json.loads(dossie.payload_json),
        },
        ensure_ascii=False,
        indent=2,
    )


def _escapar_pdf(texto):
    texto_latin = texto.encode('cp1252', errors='replace').decode('latin-1')
    return texto_latin.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')


def exportar_dossie_pdf(dossie):
    dados = json.loads(dossie.payload_json)
    resumo = dados['resumo_executivo']
    eficiencia = dados['historico_eficiencia_energetica']
    seguranca = dados['indices_seguranca']
    telemetria = dados['telemetria']
    linhas = [
        ('F2', 15, 'Nexora - Dossie Digital Auditavel Criptografado'),
        ('F1', 10, f'Empresa: {dados["empresa"]["nome"]}'),
        ('F1', 10, f'Carimbo de data/hora imutavel: {dados["carimbo_data_hora"]}'),
        ('F1', 10, ''),
        ('F2', 12, '1. Resumo Executivo e Maturidade Operacional'),
        (
            'F1',
            10,
            f'Nota de Maturidade: {resumo["nota_maturidade"]}/100 '
            f'- Estagio: {resumo["estagio_maturidade"]}',
        ),
        (
            'F1',
            10,
            f'Proximo nivel: {resumo["proximo_estagio"] or "Nivel maximo atingido"} '
            f'({resumo["percentual_para_proximo_nivel"]}% restante)',
        ),
        ('F1', 10, ''),
        ('F2', 12, '2. Historico de Eficiencia Energetica e ESG'),
        (
            'F1',
            10,
            f'Consumo real: {eficiencia["consumo_real_kwh"]} kWh | '
            f'Linha de base: {eficiencia["consumo_base_kwh"]} kWh',
        ),
        (
            'F1',
            10,
            f'Economia energetica: {eficiencia["economia_kwh"]} kWh | '
            f'CO2e evitado: {eficiencia["co2_evitado_kg"]} kg',
        ),
        ('F1', 10, ''),
        ('F2', 12, '3. Indices de Seguranca Ocupacional (NR-12 e NR-15)'),
        (
            'F1',
            10,
            f'Alertas NR-12: {seguranca["alertas_nr12"]} | '
            f'Alertas NR-15: {seguranca["alertas_nr15"]} | '
            f'Ocorrencias causais: {seguranca["ocorrencias_causais_total"]}',
        ),
        (
            'F1',
            10,
            f'Ordens de servico concluidas: {seguranca["ordens_servico_concluidas"]} '
            f'de {seguranca["ordens_servico_total"]}',
        ),
        (
            'F1',
            10,
            f'Dispositivos monitorados: {telemetria["dispositivos_monitorados"]} | '
            f'Leituras auditadas: {telemetria["leituras_auditadas"]}',
        ),
        ('F1', 10, ''),
        ('F2', 12, '4. Validador Criptografico'),
        ('F1', 9, f'Hash SHA-256: {dossie.hash_sha256}'),
        ('F1', 9, f'Assinatura HMAC-SHA256: {dossie.assinatura_hmac}'),
    ]
    comandos = ['BT', '48 790 Td']
    for fonte, tamanho, texto in linhas:
        comandos.append(f'/{fonte} {tamanho} Tf')
        comandos.append(f'({_escapar_pdf(texto)}) Tj')
        comandos.append(f'0 -{tamanho + 8} Td')
    comandos.append('ET')
    stream = '\n'.join(comandos).encode('latin-1')

    objetos = [
        b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] '
        b'/Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> /Contents 6 0 R >>',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>',
        b'<< /Length ' + str(len(stream)).encode('ascii') + b' >>\nstream\n' + stream + b'\nendstream',
    ]
    pdf = bytearray(b'%PDF-1.4\n')
    offsets = []
    for indice, obj in enumerate(objetos, start=1):
        offsets.append(len(pdf))
        pdf += f'{indice} 0 obj\n'.encode('ascii') + obj + b'\nendobj\n'
    xref_pos = len(pdf)
    pdf += f'xref\n0 {len(objetos) + 1}\n0000000000 65535 f \n'.encode('ascii')
    for pos in offsets:
        pdf += f'{pos:010d} 00000 n \n'.encode('ascii')
    pdf += (
        f'trailer\n<< /Size {len(objetos) + 1} /Root 1 0 R >>\n'
        f'startxref\n{xref_pos}\n%%EOF\n'
    ).encode('ascii')
    return bytes(pdf)
