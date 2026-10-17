# Nexora: Histórias de Usuário (Entrega 03)

Reúne as histórias de usuário com cenários de validação em BDD (Gherkin).

## Personas

| Persona | Papel | Necessidade principal |
|---|---|---|
| **Marcos** | Proprietário de PME fabril | Ver o impacto das falhas e da operação em Reais (R$) |
| **Carlos** | Gerente de Manutenção | Diagnósticos de causa raiz, sem excesso de alarmes |
| **Ana** | Diretora Financeira e Compliance | Dados auditáveis, seguros e confiáveis |

## Índice

| ID | Título | Persona | Épico | Status |
|---|---|---|---|---|
| US03 | Tradutor de anomalias em custo (R$) | Marcos | 2 | Implementada |
| US11 | Autenticação e controle de acesso | Ana | 1 | Backlog |
| US12 | Cadastro de dispositivos e sensores pela web | Carlos | 1 | Implementada |
| US13 | Configuração de tarifa e parâmetros financeiros | Marcos | 2 | Implementada |
| US14 | Ciclo de vida da Ordem de Serviço corretiva | Carlos | 3 | Backlog |
| US15 | Notificações consolidadas e priorizadas | Carlos | 3 | Backlog |
| US16 | Painel executivo de resultados em Reais | Marcos | 4 | Backlog |

---

## US03: Tradutor de anomalias em custo financeiro (R$)

**Persona:** Marcos | **Épico 2:** Tradução Financeira e Impacto ESG

**História:** Como Proprietário (Marcos), quero visualizar no dashboard a conversão de leituras anômalas em custo mensal em Reais, para entender o impacto das falhas na lucratividade da fábrica.

```gherkin
Funcionalidade: Tradução de anomalias em custo financeiro

  Contexto:
    Dado que a empresa possui a tarifa de energia configurada
    E existe um dispositivo com leituras de consumo registradas

  Cenário: Exibir custo estimado de uma anomalia
    Dado que o dispositivo "Prensa 02" apresenta consumo acima do limite de consumo cadastrado
    Quando o Proprietário acessa o dashboard
    Então o sistema exibe "Atenção: Esta anomalia gera um custo adicional estimado de R$ X.XXX/mês"
    E o valor é calculado pelo consumo excedente (kWh) multiplicado pela tarifa

  Cenário: Exibir prazo de retorno do reparo preventivo
    Dado que existe uma anomalia com custo mensal estimado
    E o dispositivo possui custo de reparo cadastrado
    Quando o Proprietário acessa o dashboard
    Então o sistema exibe o prazo estimado de retorno financeiro (payback) do reparo

  Cenário: Nenhuma anomalia detectada
    Dado que todos os dispositivos operam dentro dos limites
    Quando o Proprietário acessa o dashboard
    Então o sistema informa que não há custos adicionais por anomalias
```

---

## US11: Autenticação e controle de acesso por perfil e empresa

**Persona:** Ana | **Épico 1:** Fundamentação Técnica Django

**História:** Como Diretora Financeira (Ana), quero que cada usuário acesse apenas os dados da sua própria empresa e conforme o seu perfil, para garantir a confidencialidade dos dados financeiros e de compliance.

```gherkin
Funcionalidade: Autenticação e controle de acesso

  Cenário: Login com credenciais válidas
    Dado que existe um usuário cadastrado com perfil "Financeiro"
    Quando ele informa e-mail e senha corretos na tela de login
    Então o sistema o autentica e o direciona ao seu painel

  Cenário: Login com credenciais inválidas
    Dado que o usuário informa uma senha incorreta
    Quando ele tenta entrar
    Então o sistema exibe uma mensagem de erro
    E não cria sessão autenticada

  Cenário: Isolamento de dados entre empresas
    Dado que o usuário pertence à Empresa A
    Quando ele tenta acessar dados da Empresa B por URL direta
    Então o sistema retorna HTTP 403 ou 404
    E nenhum dado da Empresa B é exibido

  Cenário: Acesso restrito por perfil
    Dado que o usuário tem perfil "Gerente de Manutenção"
    Quando ele tenta acessar a tela de parâmetros financeiros
    Então o sistema retorna HTTP 403
```

---

## US12: Cadastro de dispositivos e sensores pela interface web

**Persona:** Carlos | **Épico 1:** Fundamentação Técnica Django

**História:** Como Gerente de Manutenção (Carlos), quero cadastrar e editar máquinas e sensores em uma tela simples, para conectar novos equipamentos sem depender de suporte técnico.

```gherkin
Funcionalidade: Cadastro de dispositivos e sensores

  Contexto:
    Dado que o sistema possui uma empresa cadastrada
    E existem tipos de sensor cadastrados

  Cenário: Cadastrar um novo dispositivo
    Quando o Gerente de Manutenção acessa a tela de cadastro de dispositivos
    E preenche nome da máquina, localização, tipo de sensor e limite de consumo (kWh)
    E, opcionalmente, informa o custo estimado do reparo preventivo
    E confirma o cadastro
    Então o dispositivo aparece na lista de dispositivos da empresa

  Cenário: Validar campos obrigatórios
    Quando o Gerente de Manutenção tenta salvar o formulário sem informar o nome da máquina
    Então o sistema exibe a mensagem "Este campo é obrigatório"
    E o dispositivo não é criado

  Cenário: Editar limite de consumo
    Dado que existe o dispositivo "Prensa 02"
    Quando o Gerente de Manutenção altera o limite de consumo e salva
    Então o novo limite passa a ser usado no cálculo de anomalias
```

---

## US13: Configuração de tarifa de energia e parâmetros financeiros

**Persona:** Marcos | **Épico 2:** Tradução Financeira e Impacto ESG

**História:** Como Proprietário (Marcos), quero informar a tarifa de energia da minha concessionária e o custo de hora parada, para que os cálculos em Reais reflitam a realidade da minha fábrica.

```gherkin
Funcionalidade: Configuração de parâmetros financeiros

  Contexto:
    Dado que o sistema possui uma empresa cadastrada

  Cenário: Salvar tarifa de energia
    Quando o Proprietário acessa a tela de parâmetros financeiros
    E informa tarifa de ponta, tarifa fora de ponta e custo por hora parada
    E confirma
    Então os valores são salvos para a empresa
    E o sistema exibe uma mensagem de sucesso

  Cenário: Rejeitar valores inválidos
    Quando o Proprietário informa uma tarifa negativa ou igual a zero
    Então o sistema exibe uma mensagem de erro de validação
    E os valores anteriores são mantidos

  Cenário: Usar valores padrão
    Dado que a empresa ainda não configurou os parâmetros
    Quando o Proprietário abre a tela pela primeira vez
    Então os campos aparecem pré-preenchidos com valores padrão de referência
    E podem ser editados

  Cenário: Refletir a nova tarifa nos cálculos
    Dado que a tarifa foi alterada
    Quando o Proprietário consulta o custo de uma anomalia
    Então o valor em Reais é recalculado com a nova tarifa
```

---

## US14: Ciclo de vida da Ordem de Serviço corretiva

**Persona:** Carlos | **Épico 3:** Diagnóstico Causal e Alertas

**História:** Como Gerente de Manutenção (Carlos), quero acompanhar cada Ordem de Serviço do rascunho até o fechamento, para ter rastreabilidade das intervenções realizadas.

```gherkin
Funcionalidade: Ciclo de vida da Ordem de Serviço

  Cenário: Aprovar um rascunho de OS
    Dado que existe uma OS com status "Rascunho"
    Quando o Gerente de Manutenção a aprova
    Então o status muda para "Aprovada"
    E o sistema registra data, hora e responsável pela mudança

  Cenário: Concluir uma OS
    Dado que a OS está com status "Em execução"
    Quando o Gerente de Manutenção informa causa confirmada, ação realizada e tempo de parada
    E conclui a OS
    Então o status muda para "Concluída"

  Cenário: Impedir conclusão sem dados obrigatórios
    Dado que a OS está com status "Em execução"
    Quando o Gerente de Manutenção tenta concluí-la sem informar a ação realizada
    Então o sistema exibe erro de validação
    E o status permanece "Em execução"

  Cenário: Consultar histórico por máquina
    Dado que a máquina "Prensa 02" possui três OS registradas
    Quando o Gerente de Manutenção consulta o histórico da máquina
    Então as três OS são listadas em ordem cronológica
```

---

## US15: Notificações consolidadas e priorizadas

**Persona:** Carlos | **Épico 3:** Diagnóstico Causal e Alertas

**História:** Como Gerente de Manutenção (Carlos), quero receber apenas notificações de alertas críticos, já consolidados por causa raiz, para agir rápido sem ser interrompido por alarmes irrelevantes.

```gherkin
Funcionalidade: Notificações consolidadas

  Cenário: Notificar alerta crítico
    Dado que o diagnóstico gerou uma ocorrência de severidade alta
    Quando a ocorrência é registrada
    Então o Gerente de Manutenção recebe uma notificação
    E ela contém a mensagem prescritiva e um link para a ocorrência

  Cenário: Não notificar alerta de baixa severidade
    Dado que o diagnóstico gerou uma ocorrência de severidade baixa
    Quando a ocorrência é registrada
    Então nenhuma notificação é enviada

  Cenário: Agrupar sinais da mesma causa
    Dado que três sinais da mesma máquina disparam em 5 minutos
    Quando o sistema consolida a ocorrência
    Então apenas uma notificação é enviada
```

---

## US16: Painel executivo de resultados em Reais

**Persona:** Marcos | **Épico 4:** Maturidade Operacional e Visão Executiva

**História:** Como Proprietário (Marcos), quero uma única tela inicial com os principais resultados do mês em Reais, para entender em segundos o retorno que a plataforma está gerando.

```gherkin
Funcionalidade: Painel executivo

  Cenário: Exibir resumo do mês
    Dado que o Proprietário está autenticado
    Quando ele acessa a tela inicial
    Então vê cartões com custo evitado (R$), economia de energia (R$), CO2e evitado (kg) e nota de maturidade

  Cenário: Comparar com o mês anterior
    Dado que existem dados de dois meses consecutivos
    Quando o Proprietário visualiza o painel
    Então cada cartão mostra a variação percentual em relação ao mês anterior

  Cenário: Painel sem dados
    Dado que a empresa não possui leituras no mês
    Quando o Proprietário acessa o painel
    Então o sistema exibe uma mensagem orientando a cadastrar sensores
```

---

# Entrega 03

## Histórias implementadas

Histórias selecionadas para implementação nesta entrega, no formato post-it.

### US12: Cadastro de dispositivos e sensores pela web

| | |
|---|---|
| **Como** | Gerente de Manutenção (Carlos) |
| **Quero** | cadastrar e editar máquinas e sensores em uma tela simples |
| **Para** | conectar novos equipamentos sem depender de suporte técnico |
| **Critério de pronto** | Formulário valida os campos, o dispositivo salvo aparece na lista e pode ser editado |

### US13: Configuração de tarifa de energia e parâmetros financeiros

| | |
|---|---|
| **Como** | Proprietário (Marcos) |
| **Quero** | informar a tarifa de energia e o custo de hora parada |
| **Para** | que os cálculos em Reais reflitam a realidade da minha fábrica |
| **Critério de pronto** | Valores são validados e salvos por empresa, vêm pré-preenchidos com valores padrão de referência e a tarifa alimenta o cálculo de custo |

### US03: Tradutor de anomalias em custo financeiro (R$)

| | |
|---|---|
| **Como** | Proprietário (Marcos) |
| **Quero** | ver no dashboard o custo mensal em Reais de uma anomalia |
| **Para** | entender o impacto direto das falhas na lucratividade |
| **Critério de pronto** | Dashboard mostra "custo adicional estimado de R$ X.XXX/mês" calculado com a tarifa configurada e, quando há custo de reparo cadastrado, o prazo de payback do reparo |
