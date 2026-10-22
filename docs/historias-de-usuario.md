# Nexora: Histórias de Usuário (Entrega 03)

Plataforma de telemetria industrial para PMEs, desenvolvida em Python e Django.
Este documento reúne as histórias de usuário com cenários de validação em BDD (Gherkin) e parte do que o projeto já possui: site institucional publicado, banco SQLite e o sistema de usuários do Django instalado.

Nesta entrega, o foco é a **infraestrutura inicial da aplicação**: cadastro de conta, login e logout, e um canal de contato que grava no banco de dados. As funcionalidades de telemetria e de valor financeiro ficam para a Entrega 04.

## Personas

| Persona | Papel | Necessidade principal |
|---|---|---|
| **Marcos** | Proprietário de PME fabril | Ver o impacto das falhas e da operação em Reais (R$) |
| **Carlos** | Gerente de Manutenção | Diagnósticos de causa raiz, sem excesso de alarmes |
| **Ana** | Diretora Financeira e Compliance | Dados auditáveis, seguros e confiáveis |

## Índice

| ID | Título | Persona | Épico | Status |
|---|---|---|---|---|
| US11 | Criar conta de usuário | Marcos | 1 | Entrega 03 |
| US12 | Entrar e sair da plataforma (login e logout) | Ana | 1 | Entrega 03 |
| US13 | Enviar mensagem pelo Fale Conosco | Marcos | 1 | Entrega 03 |
| US14 | Conhecer a Nexora pelo site institucional | Marcos | 1 | Já existente (Entrega 02) |
| US15 | Perfis de acesso e isolamento de dados por empresa | Ana | 1 | Backlog |
| US16 | Cadastro de dispositivos e sensores pela web | Carlos | 1 | Backlog |
| US17 | Configuração de tarifa e parâmetros financeiros | Marcos | 2 | Backlog |
| US03 | Tradutor de anomalias em custo (R$) | Marcos | 2 | Backlog |
| US18 | Ciclo de vida da Ordem de Serviço corretiva | Carlos | 3 | Backlog |
| US19 | Notificações consolidadas e priorizadas | Carlos | 3 | Backlog |
| US20 | Painel executivo de resultados em Reais | Marcos | 4 | Backlog |

---

# Histórias da Entrega 03

## US11: Criar conta de usuário

**Persona:** Marcos | **Épico 1:** Fundamentação Técnica Django

**História:** Como Proprietário (Marcos), quero criar uma conta na plataforma com nome de usuário, e-mail e senha, para ter acesso próprio e seguro ao sistema.

```gherkin
Funcionalidade: Cadastro de conta de usuário

  Cenário: Criar conta com dados válidos
    Dado que o visitante acessa a página de cadastro
    Quando informa nome de usuário, e-mail, senha e confirmação de senha válidos
    E confirma o cadastro
    Então a conta é criada
    E a senha é armazenada de forma criptografada (hash) no banco de dados
    E o sistema o direciona para a tela de login com uma mensagem de sucesso

  Cenário: Senhas diferentes
    Dado que o visitante está na página de cadastro
    Quando informa uma senha e uma confirmação diferentes
    Então o sistema exibe uma mensagem de erro
    E nenhuma conta é criada

  Cenário: Senha fraca
    Dado que o visitante está na página de cadastro
    Quando informa uma senha muito curta, somente numérica ou muito comum
    Então o sistema exibe a regra de senha que não foi atendida
    E nenhuma conta é criada

  Cenário: Nome de usuário já existente
    Dado que já existe uma conta com o nome de usuário "marcos"
    Quando outro visitante tenta se cadastrar com o nome "marcos"
    Então o sistema exibe uma mensagem informando que o nome já está em uso
    E nenhuma conta é criada
```

---

## US12: Entrar e sair da plataforma (login e logout)

**Persona:** Ana | **Épico 1:** Fundamentação Técnica Django

**História:** Como Diretora Financeira (Ana), quero entrar na plataforma com meu usuário e senha e sair quando terminar, para que somente pessoas autorizadas vejam os dados da minha empresa.

```gherkin
Funcionalidade: Login e logout

  Contexto:
    Dado que existe um usuário cadastrado

  Cenário: Login com credenciais válidas
    Dado que o usuário está na tela de login
    Quando informa nome de usuário e senha corretos
    Então o sistema o autentica
    E o direciona para o painel inicial, que exibe o seu nome de usuário

  Cenário: Login com credenciais inválidas
    Dado que o usuário está na tela de login
    Quando informa uma senha incorreta
    Então o sistema exibe uma mensagem de erro
    E nenhuma sessão é criada

  Cenário: Acessar página restrita sem estar logado
    Dado que o visitante não está autenticado
    Quando tenta acessar o painel inicial pelo endereço direto
    Então o sistema o redireciona para a tela de login

  Cenário: Sair da plataforma
    Dado que o usuário está autenticado
    Quando clica em "Sair"
    Então a sessão é encerrada
    E o painel inicial volta a exigir login
```

---

## US13: Enviar mensagem pelo Fale Conosco

**Persona:** Marcos | **Épico 1:** Fundamentação Técnica Django

**História:** Como Proprietário (Marcos) interessado na plataforma, quero enviar uma mensagem pelo Fale Conosco, para entrar em contato com a equipe da Nexora e ter certeza de que ela foi recebida.

```gherkin
Funcionalidade: Fale Conosco

  Cenário: Enviar mensagem com dados válidos
    Dado que o visitante está na página "Fale Conosco"
    Quando preenche nome, e-mail e mensagem
    E clica em "Enviar Mensagem"
    Então a mensagem é salva no banco de dados
    E o sistema exibe uma confirmação de envio

  Cenário: Campo obrigatório em branco
    Dado que o visitante está na página "Fale Conosco"
    Quando tenta enviar sem preencher a mensagem
    Então o sistema exibe um aviso de campo obrigatório
    E nada é salvo

  Cenário: E-mail inválido
    Dado que o visitante está na página "Fale Conosco"
    Quando informa um e-mail em formato inválido
    Então o sistema exibe uma mensagem de erro
    E nada é salvo

  Cenário: Equipe consulta as mensagens recebidas
    Dado que existem mensagens salvas
    Quando um administrador acessa o Django Admin
    Então vê a lista de mensagens com nome, e-mail, texto e data de envio
```

---

# Histórias já existentes

## US14: Conhecer a Nexora pelo site institucional

**Persona:** Marcos | **Épico 1:** Fundamentação Técnica Django

**História:** Como Proprietário (Marcos), quero navegar pelo site da Nexora, para entender quem é a empresa e o que ela oferece antes de criar uma conta.

**Situação:** já implementada e publicada na Entrega 02 (páginas inicial, Quem Somos, O que Fazemos e Fale Conosco).

```gherkin
Funcionalidade: Site institucional

  Cenário: Ver o sumário na página inicial
    Dado que o visitante acessa a página inicial
    Então vê o sumário com links para "Quem Somos Nós", "O que Fazemos" e "Fale Conosco"

  Cenário: Conhecer a empresa
    Dado que o visitante está na página inicial
    Quando clica em "Quem Somos Nós"
    Então vê o propósito da Nexora

  Cenário: Conhecer os serviços
    Dado que o visitante está na página inicial
    Quando clica em "O que Fazemos"
    Então vê a descrição dos serviços da plataforma

  Cenário: Voltar ao sumário
    Dado que o visitante está em uma página interna
    Quando clica em "Voltar ao Sumário"
    Então retorna à página inicial
```

---

# Backlog (Entrega 04 em diante)

## US15: Perfis de acesso e isolamento de dados por empresa

**Persona:** Ana | **Épico 1:** Fundamentação Técnica Django

**Depende de:** US12

**História:** Como Diretora Financeira (Ana), quero que cada usuário acesse apenas os dados da sua própria empresa e conforme o seu perfil, para garantir a confidencialidade dos dados financeiros e de compliance.

```gherkin
Funcionalidade: Perfis e isolamento de dados

  Cenário: Isolamento de dados entre empresas
    Dado que o usuário pertence à Empresa A
    Quando tenta acessar dados da Empresa B por endereço direto
    Então o sistema retorna HTTP 403 ou 404
    E nenhum dado da Empresa B é exibido

  Cenário: Acesso restrito por perfil
    Dado que o usuário tem perfil "Gerente de Manutenção"
    Quando tenta acessar a tela de parâmetros financeiros
    Então o sistema retorna HTTP 403
```

---

## US16: Cadastro de dispositivos e sensores pela interface web

**Persona:** Carlos | **Épico 1:** Fundamentação Técnica Django

**Depende de:** US12

**História:** Como Gerente de Manutenção (Carlos), quero cadastrar e editar máquinas e sensores em uma tela simples, para conectar novos equipamentos sem depender de suporte técnico.

```gherkin
Funcionalidade: Cadastro de dispositivos e sensores

  Contexto:
    Dado que o Gerente de Manutenção está autenticado
    E existem tipos de sensor cadastrados

  Cenário: Cadastrar um novo dispositivo
    Quando acessa a tela de cadastro de dispositivos
    E preenche nome da máquina, localização, tipo de sensor e limite de consumo (kWh)
    E, opcionalmente, informa o custo estimado do reparo preventivo
    E confirma o cadastro
    Então o dispositivo aparece na lista de dispositivos da empresa

  Cenário: Validar campos obrigatórios
    Quando tenta salvar o formulário sem informar o nome da máquina
    Então o sistema exibe a mensagem "Este campo é obrigatório"
    E o dispositivo não é criado

  Cenário: Editar limite de consumo
    Dado que existe o dispositivo "Prensa 02"
    Quando altera o limite de consumo e salva
    Então o novo limite passa a ser usado no cálculo de anomalias
```

---

## US17: Configuração de tarifa de energia e parâmetros financeiros

**Persona:** Marcos | **Épico 2:** Tradução Financeira e Impacto ESG

**Depende de:** US12

**História:** Como Proprietário (Marcos), quero informar a tarifa de energia da minha concessionária e o custo de hora parada, para que os cálculos em Reais reflitam a realidade da minha fábrica.

```gherkin
Funcionalidade: Configuração de parâmetros financeiros

  Contexto:
    Dado que o Proprietário está autenticado

  Cenário: Salvar tarifa de energia
    Quando acessa a tela de parâmetros financeiros
    E informa tarifa de ponta, tarifa fora de ponta e custo por hora parada
    E confirma
    Então os valores são salvos para a empresa
    E o sistema exibe uma mensagem de sucesso

  Cenário: Rejeitar valores inválidos
    Quando informa uma tarifa negativa ou igual a zero
    Então o sistema exibe uma mensagem de erro de validação
    E os valores anteriores são mantidos

  Cenário: Usar valores padrão
    Dado que a empresa ainda não configurou os parâmetros
    Quando abre a tela pela primeira vez
    Então os campos aparecem pré-preenchidos com valores padrão de referência
    E podem ser editados

  Cenário: Refletir a nova tarifa nos cálculos
    Dado que a tarifa foi alterada
    Quando consulta o custo de uma anomalia
    Então o valor em Reais é recalculado com a nova tarifa
```

---

## US03: Tradutor de anomalias em custo financeiro (R$)

**Persona:** Marcos | **Épico 2:** Tradução Financeira e Impacto ESG

**Depende de:** US16 e US17

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

## US18: Ciclo de vida da Ordem de Serviço corretiva

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

## US19: Notificações consolidadas e priorizadas

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

## US20: Painel executivo de resultados em Reais

**Persona:** Marcos | **Épico 4:** Maturidade Operacional e Visão Executiva

**História:** Como Proprietário (Marcos), quero uma única tela inicial com os principais resultados do mês em Reais, para entender em segundos o retorno que a plataforma está gerando.

```gherkin
Funcionalidade: Painel executivo

  Cenário: Exibir resumo do mês
    Dado que o Proprietário está autenticado
    Quando acessa a tela inicial
    Então vê cartões com custo evitado (R$), economia de energia (R$), CO2e evitado (kg) e nota de maturidade

  Cenário: Comparar com o mês anterior
    Dado que existem dados de dois meses consecutivos
    Quando visualiza o painel
    Então cada cartão mostra a variação percentual em relação ao mês anterior

  Cenário: Painel sem dados
    Dado que a empresa não possui leituras no mês
    Quando acessa o painel
    Então o sistema exibe uma mensagem orientando a cadastrar sensores
```

---

# Entrega 03

## Histórias implementadas

Histórias selecionadas para implementação nesta entrega, no formato post-it.

### US11: Criar conta de usuário

| | |
|---|---|
| **Como** | Proprietário (Marcos) |
| **Quero** | criar uma conta com nome de usuário, e-mail e senha |
| **Para** | ter acesso próprio e seguro ao sistema |
| **Critério de pronto** | Cadastro valida os dados (senhas iguais, senha forte, usuário único), salva a conta no banco com a senha criptografada e leva o usuário ao login |

### US12: Entrar e sair da plataforma (login e logout)

| | |
|---|---|
| **Como** | Diretora Financeira (Ana) |
| **Quero** | entrar com meu usuário e senha e sair quando terminar |
| **Para** | que somente pessoas autorizadas vejam os dados da minha empresa |
| **Critério de pronto** | Login válido leva ao painel inicial, login inválido mostra erro, o painel redireciona quem não está logado e o logout encerra a sessão |

### US13: Enviar mensagem pelo Fale Conosco

| | |
|---|---|
| **Como** | Proprietário (Marcos) |
| **Quero** | enviar uma mensagem pelo Fale Conosco |
| **Para** | falar com a equipe da Nexora e ter certeza de que fui ouvido |
| **Critério de pronto** | A mensagem válida é salva no banco e confirmada na tela, dados inválidos são rejeitados e a equipe vê as mensagens no Django Admin |
