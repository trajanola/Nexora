"""Regras de negócio das US04 a US10 (PDF Nexora MVP).

US04 - Eficiência energética e CO2e evitado
US05 - Estimador de desconto em crédito BNDES
US06 - Diagnóstico causal multivariável
US07 - Alertas de conformidade NR-12 e NR-15
US08 - Índice Nexora de Maturidade Operacional
US09 - Trilha gamificada de missões
US10 - Dossiê digital auditável
"""
import hashlib
import hmac
import json
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.db import transaction
from django.db.models import F, Q, Sum
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
JANELA_CORRELACAO = timedelta(minutes=5)
LIMITE_VIBRACAO_MM_S = Decimal('7.10')  # ISO 10816, zona C para máquinas médias
VALORES_SIMULACAO = [
    Decimal('100000'),
    Decimal('250000'),
    Decimal('500000'),
    Decimal('1000000'),
]
PRAZO_SIMULACAO_MESES = 60
NOMES_MESES = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez']
ESTAGIOS = [
    (0, 'Reativo'),
    (25, 'Preventivo'),
    (50, 'Preditivo'),
    (75, 'Prescritivo'),
]


def parametro_da_empresa(empresa):
    parametro, _ = Parametro.objects.get_or_create(empresa=empresa)
    return parametro


def _inicio_mes(data):
    data = timezone.localtime(data)
    return data.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _mes_anterior(inicio):
    return _inicio_mes(inicio - timedelta(days=1))


def _proximo_mes(inicio):
    return _inicio_mes(inicio + timedelta(days=32))


# ---------------------------------------------------------------- US04


def eficiencia_energetica(empresa, meses=6, agora=None):
    """Compara o consumo mensal e converte kWh economizados em kg CO2e evitados."""
    fator = parametro_da_empresa(empresa).fator_emissao_co2
    inicio_atual = _inicio_mes(agora or timezone.now())
    inicios = [inicio_atual]
    for _ in range(meses):  # um mês extra serve de base para o mais antigo
        inicios.insert(0, _mes_anterior(inicios[0]))

    consumos = []
    for inicio in inicios:
        total = Leitura.objects.filter(
            dispositivo__empresa=empresa,
            registrado_em__gte=inicio,
            registrado_em__lt=_proximo_mes(inicio),
        ).aggregate(total=Sum('valor_kwh'))['total'] or Decimal('0')
        consumos.append(total)

    historico = []
    for indice in range(1, len(inicios)):
        consumo = consumos[indice]
        anterior = consumos[indice - 1]
        economia = max(anterior - consumo, Decimal('0')) if anterior else Decimal('0')
        historico.append({
            'mes': f'{NOMES_MESES[inicios[indice].month - 1]}/{inicios[indice].year}',
            'consumo_kwh': consumo.quantize(CENTAVOS),
            'economia_kwh': economia.quantize(CENTAVOS),
            'emissao_kg': (consumo * fator).quantize(CENTAVOS),
            'co2_evitado_kg': (economia * fator).quantize(CENTAVOS),
            'variacao_pct': (
                ((consumo - anterior) / anterior * 100).quantize(Decimal('0.1'))
                if anterior else None
            ),
        })

    maior = max([item['consumo_kwh'] for item in historico] + [Decimal('1')])
    for item in historico:
        item['barra_pct'] = int(item['consumo_kwh'] / maior * 100)

    mes_atual = historico[-1]
    return {
        'fator': fator,
        'historico': historico,
        'mes_atual': mes_atual,
        'co2_evitado_total_kg': sum(
            (item['co2_evitado_kg'] for item in historico),
            Decimal('0.00'),
        ),
        'tem_dados': any(item['consumo_kwh'] > 0 for item in historico),
    }


# ---------------------------------------------------------------- US08


def _estagio(nota):
    atual = ESTAGIOS[0]
    proximo = None
    for indice, (minimo, nome) in enumerate(ESTAGIOS):
        if nota >= minimo:
            atual = (minimo, nome)
            proximo = ESTAGIOS[indice + 1] if indice + 1 < len(ESTAGIOS) else None
    return atual, proximo


def indice_maturidade(empresa, agora=None):
    """Nota 0-100 calculada apenas com dados de telemetria e manutenção (sem questionário)."""
    agora = agora or timezone.now()
    janela = agora - timedelta(days=30)
    dispositivos = Dispositivo.objects.filter(empresa=empresa)
    total_dispositivos = dispositivos.count()
    leituras = Leitura.objects.filter(dispositivo__empresa=empresa, registrado_em__gte=janela)
    total_leituras = leituras.count()

    ativos = dispositivos.filter(leituras__registrado_em__gte=janela).distinct().count()
    cobertura = Decimal(ativos) / total_dispositivos * 30 if total_dispositivos else Decimal('0')

    if total_leituras:
        anomalas = leituras.filter(valor_kwh__gt=F('dispositivo__limite_kwh')).count()
        estabilidade = (1 - Decimal(anomalas) / total_leituras) * 30
        multivariaveis = leituras.filter(
            Q(temperatura_c__isnull=False)
            | Q(corrente_a__isnull=False)
            | Q(ruido_db__isnull=False)
            | Q(vibracao_mm_s__isnull=False)
        ).count()
        sensoriamento = Decimal(multivariaveis) / total_leituras * 20
    else:
        estabilidade = Decimal('0')
        sensoriamento = Decimal('0')

    ordens = OrdemServico.objects.filter(dispositivo__empresa=empresa)
    total_ordens = ordens.count()
    concluidas = ordens.filter(status=OrdemServico.Status.CONCLUIDA).count()
    abertas_nr = OcorrenciaCausal.objects.filter(
        dispositivo__empresa=empresa,
        resolvida=False,
    ).exclude(norma=OcorrenciaCausal.Norma.NENHUMA).count()
    manutencao = Decimal(concluidas) / total_ordens * 15 if total_ordens else Decimal('0')
    if total_leituras and not abertas_nr:
        manutencao += 5

    componentes = {
        'cobertura': cobertura,
        'estabilidade': estabilidade,
        'sensoriamento': sensoriamento,
        'manutencao': manutencao,
    }
    componentes = {
        chave: int(valor.quantize(Decimal('1'), rounding=ROUND_HALF_UP))
        for chave, valor in componentes.items()
    }
    nota = max(0, min(100, sum(componentes.values())))
    (minimo, estagio), proximo = _estagio(nota)
    if proximo:
        faltam = proximo[0] - nota
        progresso = int((nota - minimo) / (proximo[0] - minimo) * 100)
    else:
        faltam = 0
        progresso = 100
    return {
        'nota': nota,
        'estagio': estagio,
        'proximo_estagio': proximo[1] if proximo else None,
        'pontos_para_proximo': faltam,
        'progresso_pct': progresso,
        'percentual_para_proximo': 100 - progresso if proximo else 0,
        'componentes': componentes,
        'estagios': [nome for _, nome in ESTAGIOS],
    }


# ---------------------------------------------------------------- US05


def _juros_totais(principal, taxa_aa, meses):
    taxa_mensal = (1 + float(taxa_aa) / 100) ** (1 / 12) - 1
    if taxa_mensal <= 0:
        return Decimal('0')
    parcela = float(principal) * taxa_mensal / (1 - (1 + taxa_mensal) ** -meses)
    return Decimal(str(parcela * meses - float(principal)))


def simular_credito_bndes(empresa, nota=None):
    """Projeta redução de spread (até o máximo configurado) proporcional à nota de eficiência."""
    parametro = parametro_da_empresa(empresa)
    if nota is None:
        nota = indice_maturidade(empresa)['nota']
    reducao = (parametro.spread_maximo_desconto_aa * Decimal(nota) / 100).quantize(CENTAVOS)
    taxa_base = parametro.taxa_base_bndes_aa
    taxa_esg = max(taxa_base - reducao, Decimal('0.01'))
    simulacoes = []
    for valor in VALORES_SIMULACAO:
        juros_base = _juros_totais(valor, taxa_base, PRAZO_SIMULACAO_MESES)
        juros_esg = _juros_totais(valor, taxa_esg, PRAZO_SIMULACAO_MESES)
        simulacoes.append({
            'valor': valor,
            'juros_base': juros_base.quantize(CENTAVOS),
            'juros_esg': juros_esg.quantize(CENTAVOS),
            'economia': (juros_base - juros_esg).quantize(CENTAVOS),
        })
    return {
        'nota': nota,
        'taxa_base': taxa_base,
        'reducao_spread': reducao,
        'spread_maximo': parametro.spread_maximo_desconto_aa,
        'taxa_esg': taxa_esg,
        'prazo_meses': PRAZO_SIMULACAO_MESES,
        'simulacoes': simulacoes,
    }


# ---------------------------------------------------------------- US06 / US07

REGRAS_CAUSAIS = [
    (
        {'ruido', 'vibracao'},
        'Degradação de lubrificante mecânico provocando atrito e elevação de ruído',
        'Degradação de lubrificante mecânico provocando atrito e elevação de ruído. '
        'Programe relubrificação e inspeção dos rolamentos no próximo turno.',
    ),
    (
        {'ruido', 'temperatura'},
        'Degradação de lubrificante mecânico provocando atrito e elevação de ruído',
        'Degradação de lubrificante mecânico provocando atrito e elevação de ruído. '
        'Programe relubrificação e inspeção dos rolamentos no próximo turno.',
    ),
    (
        {'corrente', 'temperatura'},
        'Sobrecarga do motor elétrico com aquecimento dos enrolamentos',
        'Sobrecarga do motor elétrico com aquecimento dos enrolamentos. '
        'Verifique a carga mecânica, a ventilação e o isolamento do motor.',
    ),
    (
        {'vibracao', 'corrente'},
        'Desalinhamento ou desbalanceamento de eixo',
        'Desalinhamento ou desbalanceamento de eixo elevando vibração e corrente. '
        'Realize alinhamento a laser e balanceamento do conjunto rotativo.',
    ),
    (
        {'corrente', 'consumo'},
        'Esforço mecânico excessivo elevando corrente e consumo de energia',
        'Esforço mecânico excessivo elevando corrente e consumo de energia. '
        'Inspecione travamentos, correias e ferramentas desgastadas.',
    ),
]
NOMES_SINAIS = {
    'consumo': 'consumo de energia',
    'corrente': 'pico de corrente',
    'temperatura': 'elevação de temperatura',
    'ruido': 'elevação de ruído',
    'vibracao': 'vibração excessiva',
}
ORDEM_SEVERIDADE = ['baixa', 'media', 'alta', 'critica']


def sinais_da_leitura(leitura):
    dispositivo = leitura.dispositivo
    sinais = set()
    if leitura.valor_kwh is not None and leitura.valor_kwh > dispositivo.limite_kwh:
        sinais.add('consumo')
    if leitura.corrente_a is not None and leitura.corrente_a > dispositivo.limite_corrente_a:
        sinais.add('corrente')
    if leitura.temperatura_c is not None and leitura.temperatura_c > dispositivo.limite_temperatura_c:
        sinais.add('temperatura')
    if leitura.ruido_db is not None and leitura.ruido_db > dispositivo.limite_ruido_db:
        sinais.add('ruido')
    if leitura.vibracao_mm_s is not None and leitura.vibracao_mm_s > LIMITE_VIBRACAO_MM_S:
        sinais.add('vibracao')
    return sinais


def diagnosticar(sinais, nr12=False):
    if nr12:
        return (
            'Falha de dispositivo de segurança da máquina (NR-12)',
            'Interrompa a operação e inspecione proteções, intertravamentos e botões de '
            'emergência antes de religar a máquina (NR-12).',
        )
    for requeridos, causa, mensagem in REGRAS_CAUSAIS:
        if requeridos <= sinais:
            return causa, mensagem
    if sinais == {'ruido'}:
        return (
            'Exposição a ruído acima do limite de tolerância (NR-15)',
            'Ruído acima do limite de tolerância da NR-15. Enclausure a fonte, revise a '
            'manutenção e garanta o uso de protetor auricular.',
        )
    descricao = ', '.join(NOMES_SINAIS[sinal] for sinal in sorted(sinais))
    return (
        f'Anomalia combinada: {descricao}',
        f'Sinais simultâneos detectados ({descricao}). Inspecione o equipamento e confirme a causa.',
    )


def _norma(nr12, nr15):
    if nr12 and nr15:
        return OcorrenciaCausal.Norma.NR12_NR15
    if nr12:
        return OcorrenciaCausal.Norma.NR12
    if nr15:
        return OcorrenciaCausal.Norma.NR15
    return OcorrenciaCausal.Norma.NENHUMA


def _severidade(sinais, norma):
    if norma == OcorrenciaCausal.Norma.NR12_NR15 or norma == OcorrenciaCausal.Norma.NR12:
        return OcorrenciaCausal.Severidade.CRITICA
    if norma == OcorrenciaCausal.Norma.NR15 or len(sinais) >= 3:
        return OcorrenciaCausal.Severidade.ALTA
    return OcorrenciaCausal.Severidade.MEDIA


def _mesclar_norma(atual, nova):
    nr12 = 'nr12' in atual or 'nr12' in nova
    nr15 = 'nr15' in atual or 'nr15' in nova
    return _norma(nr12, nr15)


def _criar_os_corretiva(ocorrencia):
    ordem = OrdemServico.objects.create(
        dispositivo=ocorrencia.dispositivo,
        resumo=f'Corretiva {ocorrencia.get_norma_display().split(" (")[0]}: {ocorrencia.causa_raiz}'[:160],
        descricao=(
            'Rascunho gerado automaticamente pelo alerta regulatório da Nexora.\n'
            f'Sinais: {ocorrencia.sinais_correlacionados}\n'
            f'Orientação: {ocorrencia.mensagem_prescritiva}'
        ),
    )
    ocorrencia.ordem_servico = ordem
    ocorrencia.save(update_fields=['ordem_servico'])
    return ordem


@transaction.atomic
def processar_leitura(leitura):
    """Correlaciona sinais da leitura com a janela de 5 minutos e gera uma única ocorrência."""
    sinais_atuais = sinais_da_leitura(leitura)
    nr12 = leitura.falha_seguranca_nr12
    if not sinais_atuais and not nr12:
        return None

    vizinhas = Leitura.objects.filter(
        dispositivo=leitura.dispositivo,
        registrado_em__gte=leitura.registrado_em - JANELA_CORRELACAO,
        registrado_em__lte=leitura.registrado_em + JANELA_CORRELACAO,
    ).exclude(pk=leitura.pk).select_related('dispositivo')
    sinais = set(sinais_atuais)
    for vizinha in vizinhas:
        sinais |= sinais_da_leitura(vizinha)
        nr12 = nr12 or vizinha.falha_seguranca_nr12

    nr15 = 'ruido' in sinais
    if len(sinais) < 2 and not (nr12 or nr15):
        return None

    causa, mensagem = diagnosticar(sinais, nr12)
    norma = _norma(nr12, nr15)
    descricao_sinais = ', '.join(NOMES_SINAIS[sinal] for sinal in sorted(sinais))
    if nr12:
        descricao_sinais = ', '.join(filter(None, ['violação de segurança NR-12', descricao_sinais]))

    existente = OcorrenciaCausal.objects.select_for_update().filter(
        dispositivo=leitura.dispositivo,
        causa_raiz=causa,
        resolvida=False,
        detectada_em__gte=leitura.registrado_em - JANELA_CORRELACAO,
        detectada_em__lte=leitura.registrado_em + JANELA_CORRELACAO,
    ).first()
    if existente:
        existente.quantidade_eventos += 1
        existente.sinais_correlacionados = descricao_sinais[:255]
        existente.norma = _mesclar_norma(existente.norma, norma)
        nova_severidade = _severidade(sinais, existente.norma)
        if ORDEM_SEVERIDADE.index(nova_severidade) > ORDEM_SEVERIDADE.index(existente.severidade):
            existente.severidade = nova_severidade
        existente.save()
        if existente.norma != OcorrenciaCausal.Norma.NENHUMA and not existente.ordem_servico_id:
            _criar_os_corretiva(existente)
        return existente

    ocorrencia = OcorrenciaCausal.objects.create(
        dispositivo=leitura.dispositivo,
        causa_raiz=causa,
        mensagem_prescritiva=mensagem,
        sinais_correlacionados=descricao_sinais[:255],
        quantidade_eventos=1 + vizinhas.count(),
        severidade=_severidade(sinais, norma),
        norma=norma,
        detectada_em=leitura.registrado_em,
    )
    if norma != OcorrenciaCausal.Norma.NENHUMA:
        _criar_os_corretiva(ocorrencia)
    return ocorrencia


# ---------------------------------------------------------------- US09


def _catalogo_missoes(empresa):
    dispositivos = list(Dispositivo.objects.filter(empresa=empresa))
    semana = timezone.now() - timedelta(days=7)
    catalogo = [
        {
            'codigo': 'primeiro-dispositivo',
            'titulo': 'Cadastre a primeira máquina monitorada',
            'descricao': 'Acesse Dispositivos > Novo dispositivo e informe nome, local e limite de consumo.',
            'pontos': 15,
            'concluida': bool(dispositivos),
        },
        {
            'codigo': 'enviar-leituras',
            'titulo': 'Conecte um sensor e envie leituras',
            'descricao': 'Configure o equipamento com o token do dispositivo para enviar leituras à API.',
            'pontos': 20,
            'concluida': Leitura.objects.filter(
                dispositivo__empresa=empresa,
                registrado_em__gte=semana,
            ).exists(),
        },
    ]
    for dispositivo in dispositivos:
        catalogo.append({
            'codigo': f'sensor-multivariavel-{dispositivo.pk}',
            'titulo': f'Instale sensor de temperatura/ruído na {dispositivo.nome}',
            'descricao': (
                'Adicione sensores de temperatura, corrente, ruído ou vibração e envie os campos '
                'temperatura_c, corrente_a, ruido_db ou vibracao_mm_s junto com o consumo.'
            ),
            'pontos': 10,
            'concluida': dispositivo.leituras.filter(
                Q(temperatura_c__isnull=False)
                | Q(corrente_a__isnull=False)
                | Q(ruido_db__isnull=False)
                | Q(vibracao_mm_s__isnull=False)
            ).exists(),
        })
    catalogo.append({
        'codigo': 'concluir-os',
        'titulo': 'Conclua uma ordem de serviço com causa confirmada',
        'descricao': 'Aprove, execute e conclua uma OS registrando causa, ação e tempo de parada.',
        'pontos': 15,
        'concluida': OrdemServico.objects.filter(
            dispositivo__empresa=empresa,
            status=OrdemServico.Status.CONCLUIDA,
        ).exists(),
    })
    for dispositivo in dispositivos:
        catalogo.append({
            'codigo': f'custo-reparo-{dispositivo.pk}',
            'titulo': f'Informe o custo de reparo da {dispositivo.nome}',
            'descricao': 'O custo do reparo preventivo habilita o cálculo de payback da anomalia.',
            'pontos': 5,
            'concluida': dispositivo.custo_reparo is not None,
        })
    catalogo.append({
        'codigo': 'tres-maquinas',
        'titulo': 'Monitore ao menos três máquinas',
        'descricao': 'Amplie a cobertura cadastrando as máquinas críticas da linha de produção.',
        'pontos': 10,
        'concluida': len(dispositivos) >= 3,
    })
    return catalogo


@transaction.atomic
def sincronizar_missoes(empresa):
    """Cria missões aplicáveis e atualiza automaticamente o status quando a ação é detectada."""
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
        if item['concluida'] and missao.status == MissaoOperacional.Status.PENDENTE:
            missao.status = MissaoOperacional.Status.CONCLUIDA
            missao.concluida_em = agora
            missao.save(update_fields=['status', 'concluida_em'])
        elif missao.prioridade != prioridade:
            missao.prioridade = prioridade
            missao.save(update_fields=['prioridade'])
    pendentes = MissaoOperacional.objects.filter(
        empresa=empresa,
        status=MissaoOperacional.Status.PENDENTE,
    )
    concluidas = MissaoOperacional.objects.filter(
        empresa=empresa,
        status=MissaoOperacional.Status.CONCLUIDA,
    ).order_by('-concluida_em')
    return {
        'prioritarias': list(pendentes[:3]),
        'total_pendentes': pendentes.count(),
        'concluidas': list(concluidas[:5]),
    }


# ---------------------------------------------------------------- US10


def _decimal_json(valor):
    if isinstance(valor, Decimal):
        return str(valor)
    raise TypeError(f'Tipo não serializável: {type(valor)}')


def json_canonico(dados):
    return json.dumps(dados, sort_keys=True, ensure_ascii=False, separators=(',', ':'), default=_decimal_json)


def assinar(conteudo):
    return hmac.new(settings.SECRET_KEY.encode(), conteudo.encode(), hashlib.sha256).hexdigest()


def montar_evidencias(empresa, carimbo):
    maturidade = indice_maturidade(empresa)
    eficiencia = eficiencia_energetica(empresa)
    ocorrencias = OcorrenciaCausal.objects.filter(dispositivo__empresa=empresa)
    ordens = OrdemServico.objects.filter(dispositivo__empresa=empresa)
    return {
        'emissor': 'Nexora',
        'versao': 1,
        'empresa': {'id': empresa.pk, 'nome': empresa.nome},
        'carimbo_data_hora': carimbo.isoformat(),
        'resumo_executivo': {
            'nota_maturidade': maturidade['nota'],
            'estagio_maturidade': maturidade['estagio'],
            'componentes_maturidade': maturidade['componentes'],
            'co2_evitado_kg_6_meses': eficiencia['co2_evitado_total_kg'],
            'fator_emissao_kg_co2e_kwh': eficiencia['fator'],
        },
        'historico_eficiencia_energetica': [
            {
                'mes': item['mes'],
                'consumo_kwh': item['consumo_kwh'],
                'economia_kwh': item['economia_kwh'],
                'co2_evitado_kg': item['co2_evitado_kg'],
            }
            for item in eficiencia['historico']
        ],
        'indices_seguranca': {
            'ocorrencias_nr12': ocorrencias.filter(norma__in=['nr12', 'nr12_nr15']).count(),
            'ocorrencias_nr15': ocorrencias.filter(norma__in=['nr15', 'nr12_nr15']).count(),
            'ocorrencias_resolvidas': ocorrencias.filter(resolvida=True).count(),
            'ocorrencias_abertas': ocorrencias.filter(resolvida=False).count(),
            'ordens_servico_concluidas': ordens.filter(status=OrdemServico.Status.CONCLUIDA).count(),
            'ordens_servico_total': ordens.count(),
        },
        'telemetria': {
            'dispositivos': Dispositivo.objects.filter(empresa=empresa).count(),
            'leituras_registradas': Leitura.objects.filter(dispositivo__empresa=empresa).count(),
        },
    }


def gerar_dossie(empresa, usuario):
    carimbo = timezone.now().replace(microsecond=0)
    evidencias = montar_evidencias(empresa, carimbo)
    payload = json_canonico(evidencias)
    return DossieAuditoria.objects.create(
        empresa=empresa,
        gerado_por=usuario,
        carimbo_data_hora=carimbo,
        hash_sha256=hashlib.sha256(payload.encode()).hexdigest(),
        assinatura_hmac=assinar(payload),
        nota_maturidade=evidencias['resumo_executivo']['nota_maturidade'],
        estagio_maturidade=evidencias['resumo_executivo']['estagio_maturidade'],
        payload_json=payload,
    )


def verificar_dossie(dossie):
    hash_ok = hashlib.sha256(dossie.payload_json.encode()).hexdigest() == dossie.hash_sha256
    assinatura_ok = hmac.compare_digest(assinar(dossie.payload_json), dossie.assinatura_hmac)
    return hash_ok and assinatura_ok


def dossie_para_json(dossie):
    return json.dumps({
        'evidencias': json.loads(dossie.payload_json),
        'integridade': {
            'algoritmo_hash': 'SHA-256',
            'hash_sha256': dossie.hash_sha256,
            'assinatura_hmac_sha256': dossie.assinatura_hmac,
            'carimbo_data_hora': dossie.carimbo_data_hora.isoformat(),
            'observacao': 'O hash é calculado sobre o JSON canônico do campo "evidencias" '
                          '(chaves ordenadas, separadores "," e ":", UTF-8).',
        },
    }, ensure_ascii=False, indent=2)


def _pdf_texto(texto):
    texto = texto.encode('cp1252', errors='replace').decode('latin-1')
    return texto.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')


def dossie_para_pdf(dossie):
    """Gera um PDF simples (sem dependências externas) com resumo executivo e hash."""
    dados = json.loads(dossie.payload_json)
    resumo = dados['resumo_executivo']
    seguranca = dados['indices_seguranca']
    linhas = [
        ('F2', 16, 'Nexora - Dossie Digital Auditavel'),
        ('F1', 10, f'Empresa: {dados["empresa"]["nome"]}'),
        ('F1', 10, f'Carimbo de data/hora (UTC): {dados["carimbo_data_hora"]}'),
        ('F1', 10, ''),
        ('F2', 12, 'Resumo executivo'),
        ('F1', 10, f'Nota de maturidade: {resumo["nota_maturidade"]}/100 ({resumo["estagio_maturidade"]})'),
        ('F1', 10, f'CO2e evitado (6 meses): {resumo["co2_evitado_kg_6_meses"]} kg'),
        ('F1', 10, f'Fator de emissao: {resumo["fator_emissao_kg_co2e_kwh"]} kg CO2e/kWh'),
        ('F1', 10, ''),
        ('F2', 12, 'Historico de eficiencia energetica'),
    ]
    for item in dados['historico_eficiencia_energetica']:
        linhas.append((
            'F1', 10,
            f'{item["mes"]}: consumo {item["consumo_kwh"]} kWh | economia {item["economia_kwh"]} kWh | '
            f'CO2e evitado {item["co2_evitado_kg"]} kg',
        ))
    linhas += [
        ('F1', 10, ''),
        ('F2', 12, 'Indices de seguranca e conformidade'),
        ('F1', 10, f'Ocorrencias NR-12: {seguranca["ocorrencias_nr12"]} | NR-15: {seguranca["ocorrencias_nr15"]}'),
        ('F1', 10, f'Ocorrencias resolvidas: {seguranca["ocorrencias_resolvidas"]} | abertas: {seguranca["ocorrencias_abertas"]}'),
        ('F1', 10, f'Ordens de servico concluidas: {seguranca["ordens_servico_concluidas"]} de {seguranca["ordens_servico_total"]}'),
        ('F1', 10, f'Dispositivos: {dados["telemetria"]["dispositivos"]} | Leituras: {dados["telemetria"]["leituras_registradas"]}'),
        ('F1', 10, ''),
        ('F2', 12, 'Integridade'),
        ('F1', 9, f'SHA-256: {dossie.hash_sha256}'),
        ('F1', 9, f'HMAC-SHA256: {dossie.assinatura_hmac}'),
        ('F1', 9, 'Valide o hash recalculando o SHA-256 do JSON canonico exportado.'),
    ]
    comandos = ['BT', '50 790 Td']
    for fonte, tamanho, texto in linhas:
        comandos.append(f'/{fonte} {tamanho} Tf')
        comandos.append(f'({_pdf_texto(texto)}) Tj')
        comandos.append(f'0 -{tamanho + 8} Td')
    comandos.append('ET')
    conteudo = '\n'.join(comandos).encode('latin-1')

    objetos = [
        b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] '
        b'/Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> /Contents 6 0 R >>',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>',
        b'<< /Length ' + str(len(conteudo)).encode() + b' >>\nstream\n' + conteudo + b'\nendstream',
    ]
    saida = bytearray(b'%PDF-1.4\n')
    posicoes = []
    for numero, objeto in enumerate(objetos, start=1):
        posicoes.append(len(saida))
        saida += f'{numero} 0 obj\n'.encode() + objeto + b'\nendobj\n'
    inicio_xref = len(saida)
    saida += f'xref\n0 {len(objetos) + 1}\n0000000000 65535 f \n'.encode()
    for posicao in posicoes:
        saida += f'{posicao:010d} 00000 n \n'.encode()
    saida += (
        f'trailer\n<< /Size {len(objetos) + 1} /Root 1 0 R >>\nstartxref\n{inicio_xref}\n%%EOF\n'
    ).encode()
    return bytes(saida)
