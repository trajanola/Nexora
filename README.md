# _NEXORA_

## 👥 &nbsp;Integrantes do Projeto

<div align="center">

| Membro | E-mail |
| :---: | :---: |
| Arthur Santana de Andrade | **asa4@cesar.school** |
| Lucas Silva Moreira do Nascimento | **lsmn@cesar.school** |
| Mariana de Melquiades Melo | **mmm4@cesar.school** |
| Matheus Trajano de Freitas | **mtf@cesar.school** |
| Paulo Ferreira Fonseca dos Santos | **pffs@cesar.school** |
| Ricardo Amorim Bayma | **rab5@cesar.school** |
| Lucas Berenguer Avelino de Souza | **lbas@cesar.school** |
| Matheus Guerra Britto | **mgb3@cesar.school** |

</div>

## 🎯 &nbsp;Contexto e Propósito

A maioria das empresas falha na adoção de IoT não por falta de sensores, mas por incapacidade de **transformar** dados brutos em inteligência aplicável. O objetivo central da _NEXORA_ é ir além de um simples dashboard passivo: a plataforma foi desenhada para educar as empresas, traduzindo sinais operacionais em percepção de **valor financeiro e orientação estratégica**.

## 📝 &nbsp;Descrição do Projeto

A _NEXORA_ é uma plataforma desenvolvida para modernizar, simplificar e otimizar a gestão de ecossistemas educacionais. O sistema conecta alunos, professores e administradores em um ambiente integrado, intuitivo e funcional, facilitando o acompanhamento acadêmico, a organização de conteúdos e a comunicação institucional.

## ⚙️ &nbsp;Funcionalidades da plataforma

Depois de criar uma conta e entrar, o usuário pode:

- Cadastrar dispositivos com localização, limite de consumo e custo estimado de reparo preventivo.
- Consultar o histórico recente de leituras de cada dispositivo.
- Configurar a tarifa de energia da empresa em R$/kWh.
- Acompanhar no painel o custo mensal do consumo excedente e, quando há custo de reparo cadastrado, o payback estimado em meses.
- Configurar uma linha de base mensal e um fator de emissão para acompanhar eficiência energética, economia de kWh e CO2e evitado.
- Simular crédito BNDES com valor financiado, desconto configurável, juros e prazo, sem substituir a análise da instituição financeira.
- Receber diagnósticos causais multivariáveis (energia, temperatura e vibração) com prescrição automática em linguagem simples e alertas de segurança normativa NR-12 e NR-15.
- Acompanhar o Índice Nexora de Maturidade Operacional (0 a 100 pontos, estágios Reativo, Preventivo, Preditivo e Prescritivo) e concluir missões operacionais gamificadas.
- Emitir e exportar o Dossiê Digital Auditável Criptografado em PDF e JSON com carimbo de tempo imutável e assinatura SHA-256 / HMAC-SHA256 para homologação B2B.
- Enviar mensagens pelo formulário Fale Conosco; a equipe consulta as mensagens no Django Admin.
- Convidar novos membros para a empresa como Financeiro ou Gerente de Manutenção. O Gerente de Manutenção não pode acessar os parâmetros financeiros.

O primeiro usuário de cada cadastro cria a empresa e recebe o perfil de Proprietário. Convites por e-mail podem ser aceitos por uma conta existente ou usados para criar uma conta; expiram após sete dias. Ao aceitar com uma conta existente, os dispositivos e a tarifa da empresa individual são associados à empresa convidante; dados de uma empresa com outros membros permanecem com essa empresa. Em desenvolvimento, os e-mails são exibidos no terminal; para envio real, configure `EMAIL_BACKEND` e `DEFAULT_FROM_EMAIL` no ambiente.

Cada dispositivo possui um token próprio. Na página de detalhes do dispositivo, copie o token e envie leituras para `POST /api/leituras/` como JSON:

```bash
curl -X POST http://127.0.0.1:8000/api/leituras/ \
  -H "Content-Type: application/json" \
  -H "X-Device-Token: <token-do-dispositivo>" \
  -d '{"valor_kwh": 42.7}'
```

O token autentica o dispositivo na API; mantenha-o privado. O custo exibido no painel considera somente a parcela de cada leitura acima do limite, multiplicada pela tarifa configurada.

Para sincronizar várias leituras, envie uma lista no mesmo endpoint. O campo `id_externo` torna o envio idempotente:

```bash
curl -X POST http://127.0.0.1:8000/api/leituras/ \
  -H "Content-Type: application/json" \
  -H "X-Device-Token: <token-do-dispositivo>" \
  -d '{"leituras":[{"id_externo":"sensor-001-0001","valor_kwh":42.7},{"id_externo":"sensor-001-0002","valor_kwh":43.1}]}'
```

Leituras válidas são persistidas mesmo quando outra entrada do lote é rejeitada; nesse caso a API responde `207`. Reenviar o mesmo `id_externo` não cria uma duplicata.

Na tela **Tarifa**, o proprietário ou usuário financeiro também pode informar o consumo base mensal e o fator de emissão. O painel compara as leituras do mês com essa linha de base. A tela **Crédito BNDES** calcula uma simulação configurável usando o sistema de amortização Price; os parâmetros não representam uma oferta oficial do BNDES.

## 🛠️ &nbsp;Tecnologias Utilizadas

<div align="center">

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white)
![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white)
![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=for-the-badge&logo=css3&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white)
![Selenium](https://img.shields.io/badge/Selenium-43B02A?style=for-the-badge&logo=selenium&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-2088FF?style=for-the-badge&logo=github-actions&logoColor=white)
![Render](https://img.shields.io/badge/Render-46E3B7?style=for-the-badge&logo=render&logoColor=white)
![AWS](https://img.shields.io/badge/Amazon_AWS-232F3E?style=for-the-badge&logo=amazon-aws&logoColor=white)
![Jira](https://img.shields.io/badge/Jira-0052CC?style=for-the-badge&logo=jira&logoColor=white)
![Figma](https://img.shields.io/badge/Figma-F24E1E?style=for-the-badge&logo=figma&logoColor=white)

</div>

<details>
<summary><b>📦 Bibliotecas Implementadas</b> (clique para expandir)</summary>

<br>

| Biblioteca | Versão | Finalidade no Projeto |
| :--- | :---: | :--- |
| **Django** | `6.1.1` | Núcleo da aplicação: ORM para dispositivos/telemetria, autenticação, controle de permissões e views |
| **selenium** | `>=4.25,<5` | Testes automatizados de sistema (E2E) no navegador Google Chrome via Selenium Manager |
| **whitenoise** | `6.9.0` | Servidor de arquivos estáticos otimizado para produção com compressão e manifesto com hash |
| **gunicorn** | `23.0.0` | Servidor HTTP WSGI para execução em ambiente de produção (Render / Linux) |
| **psycopg[binary]** | `3.2.10` | Driver de alta performance para comunicação com o banco PostgreSQL |
| **dj-database-url** | `3.0.1` | Configuração dinâmica da conexão com o banco a partir da variável `DATABASE_URL` |
| **python-dotenv** | `1.2.4` | Carregamento seguro de variáveis de ambiente a partir do arquivo `.env` |
| **asgiref** | `3.12.1` | Padrão e utilitários ASGI de suporte ao ecossistema assíncrono do Django |
| **sqlparse** | `0.6.0` | Motor de parsing e inspeção SQL utilizado internamente pelas migrações do Django |
| **tzdata** | `2026.3` | Base de dados de fusos horários do IANA para suporte a horários locais (`America/Sao_Paulo`) |

</details>

## 💻 &nbsp;Como Rodar o Projeto Localmente
<details>
<summary><b>Requisitos funcionais para rodar localmente</b> (clique para expandir)</summary>

### Pré-requisitos

- Git instalado (`git --version` para conferir)
- Python 3.12 ou superior (`python --version`)
- Um editor de código, como o VS Code

### 1. Clonar o repositório

```bash
git clone https://github.com/trajanola/Nexora.git
cd Nexora
```

Se você configurou chave SSH, pode usar a URL SSH:

```bash
git clone git@github.com:trajanola/Nexora.git
```

### 2. Criar e ativar o ambiente virtual

O ambiente virtual isola as dependências do projeto das do resto do seu computador.

**Windows (PowerShell):**

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

**Linux / macOS:**

```bash
python3 -m venv venv
source venv/bin/activate
```

Quando estiver ativo, o terminal mostra `(venv)` no começo da linha.

### 3. Instalar as dependências

Com o ambiente virtual ativo, dentro da pasta `Nexora`:

```bash
pip install -r requirements.txt
```

### 4. Configurar a variável de ambiente `SECRET_KEY`

O projeto lê a `SECRET_KEY` do Django a partir de uma variável de ambiente (`config/settings.py`). Sem ela, o servidor não inicia e mostra o erro `KeyError: 'SECRET_KEY'`.

Gere uma chave:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Depois defina a variável no terminal, **antes** de rodar o servidor (vale apenas para a sessão atual do terminal):

**Windows (PowerShell):**

```powershell
$env:SECRET_KEY = "cole-a-chave-gerada-aqui"
```

**Linux / macOS:**

```bash
export SECRET_KEY='cole-a-chave-gerada-aqui'
```

> Nunca coloque a `SECRET_KEY` real dentro do código nem envie arquivos com segredos ao GitHub.

### 5. Preparar o banco de dados

O projeto usa SQLite (`db.sqlite3`), então não é necessário instalar nem configurar um banco separado.

```bash
python manage.py migrate
```

Opcional, para acessar o painel administrativo:

```bash
python manage.py createsuperuser
```

### 6. Rodar o servidor

```bash
python manage.py runserver
```

Abra http://127.0.0.1:8000 no navegador. O painel administrativo fica em http://127.0.0.1:8000/admin.

### Deploy no Render

O arquivo `render.yaml` descreve o Web Service, o PostgreSQL, as migrations e a coleta de arquivos estáticos. O Render deve receber:

- `SECRET_KEY`: segredo gerado ou armazenado pelo Render;
- `DEBUG=False`;
- `ALLOWED_HOSTS`: o domínio `onrender.com` do serviço;
- `CSRF_TRUSTED_ORIGINS`: a URL HTTPS completa do serviço;
- `DATABASE_URL`: preenchida automaticamente quando o banco do blueprint for criado.

Localmente, a ausência de `DATABASE_URL` mantém o SQLite. No Render, a variável seleciona o PostgreSQL sem alteração de código.

Para parar o servidor, use `Ctrl+C` no terminal.

### Problemas comuns

| Problema | Solução |
|---|---|
| `python: command not found` | Use `python3`, ou instale o Python |
| `ModuleNotFoundError` | O ambiente virtual não está ativo ou faltou o `pip install -r requirements.txt` |
| `KeyError: 'SECRET_KEY'` | A variável de ambiente não foi definida neste terminal (veja o passo 4) |
| Página sem estilo e `404` para o CSS no terminal | Os templates devem começar com `{% load static %}` e usar `<link rel="stylesheet" href="{% static 'css/style.css' %}">` |
| Erro de permissão no PowerShell ao ativar o venv | Rode `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |

### Fluxo do dia a dia

Para pegar as novidades do repositório:

```bash
git pull
pip install -r requirements.txt
python manage.py migrate
```

Para contribuir, crie uma branch antes de mexer no código:

```bash
git checkout -b minha-feature
```

### Testes automatizados

Os testes Django são executados com:

```bash
python manage.py test
```

Os testes de navegador usam Selenium e Chrome. Instale as dependências de desenvolvimento e execute-os em modo headless:

```powershell
pip install -r requirements-dev.txt
$env:SECRET_KEY = "chave-local-de-teste"
$env:DEBUG = "False"
$env:SELENIUM_HEADLESS = "1"
python manage.py test core.tests_e2e --verbosity=2
```

Para abrir o navegador durante a execução, use `$env:SELENIUM_HEADLESS = "0"`. O Chrome precisa estar instalado localmente; o Selenium Manager providencia o driver compatível.
</details>

## 📅 &nbsp;Entregas do Projeto

<details>
<summary><b>📌 Entrega 1: Pesquisa, Benchmarking e Prototipagem</b> (clique para expandir)</summary>

<br>

Nesta primeira etapa, estruturamos a base conceitual, a análise de mercado e a prototipagem inicial do projeto **Nexora**, definindo nossos diferenciais competitivos e o escopo da Sprint 01.

---

### 🔍 Pesquisa e Documentação

* **[Desk Research](https://www.figma.com/board/jxNemj7jNW6uGalSK9BPTA/Projetos-2?t=3C9odntDyPqumqQf-0):** Levantamento inicial de requisitos, dores dos usuários e alinhamento estratégico no Figma.
* **[Documento de Análise de Competidores](https://github.com/trajanola/Nexora/blob/main/Documenta%C3%A7%C3%A3o_Interface.md):** Detalhamento técnico e estrutural dos concorrentes diretos e indiretos no GitHub.

---

### 📊 Benchmark da Análise de Competidores

Comparativo de funcionalidades, capacidade e segurança entre plataformas de mercado e o **Nexora**:

| Funcionalidade / Competidor | atDesigner-TP | Plataforma IoT Tecnolog | Node-RED | Blynk IoT | AWS IoT Core | 🚀 _NEXORA_ |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Interface simples e de fácil uso** | ❌ | ✅ | ❌ | ✅ | ❌ | **✅** |
| **Reúne informações de forma eficiente** | ❌ | ❌ | ❌ | ✅ | ❌ | **✅** |
| **Ferramentas personalizáveis** | ✅ | ❌ | ✅ | ❌ | ✅ | **✅** |
| **Qtd. de dispositivos simultâneos** | 32 | 20–30 | 15–25 | 10–20 | 30–40 | **50** |
| **Segurança e controle de acesso** | ❌ ❌ | ✅ ❌ | ❌ ❌ | ✅ ❌ | ✅ ✅ | **✅ ✅** |

---

### 💻 Prototipagem e Planejamento

#### Protótipo Não Funcional da Interface
![Interface não funcional](https://github.com/trajanola/Nexora/blob/main/docs/Interface%20Nexora.png)

#### Quadro de Acompanhamento - Sprint 01
![Print do Jira](https://github.com/trajanola/Nexora/blob/main/docs/Quadro%201.png)

</details>
  
<details>
<summary><b>📌 Entrega 2: Infraestrutura, Deploy e Código</b> (clique para expandir)</summary>

<br>

Apresentação dos screencasts demonstrativos da infraestrutura em produção e arquitetura do código Django, acompanhado do quadro da Sprint 02.

---

### 🎥 Demonstrações em Vídeo
- 🎬 **[Screencast Deployment da infraestrutura em produção](https://youtu.be/GkYC9-hXWlg)**
- 🎬 **[Screencast de explicação do código Django](https://youtu.be/Fvb92Io1STo)**

---

### 📋 Planejamento e Acompanhamento

#### Quadro da Sprint 02
![Print do Quadro](https://github.com/trajanola/Nexora/blob/main/docs/Quadro%202.png)

</details>

<details>
<summary><b>📌 Entrega 3: Histórias de Usuário e Implementação</b> (clique para expandir)</summary>

<br>

Mapeamento das Histórias de Usuário com cenários de testes operacionais em BDD (Gherkin), funcionalidades entregues e acompanhamento do backlog no Jira.

---

### 📖 Histórias de Usuário

Todas as histórias, escritas com cenários de validação em BDD (Gherkin): **[historias-de-usuario.md](./docs/historias-de-usuario.md)**

### ✅ Histórias Implementadas

---

- **US11 — Criar conta:** cadastro com nome de usuário, e-mail, empresa, confirmação e validação da senha; usuário único e senha armazenada com hash pelo Django.
- **US12 — Entrar e sair da plataforma:** autenticação, redirecionamento ao painel após login, proteção das áreas privadas e encerramento de sessão via logout.
- **US13 — Fale Conosco:** validação e persistência das mensagens, confirmação de envio e consulta pela equipe no Django Admin.
- **US15 — Perfis e isolamento por empresa:** dados compartilhados apenas entre membros da mesma empresa; Proprietário pode enviar convites para novos membros com perfil Financeiro ou Gerente de Manutenção, sem acesso financeiro para o gerente.
- **US03 — Traduzir anomalias em custo e payback:** custo mensal calculado sobre o consumo excedente e prazo estimado de retorno do reparo preventivo quando há custo cadastrado.
- **US21 — Cadastrar e listar dispositivos:** cadastro de dispositivos com localização e limite de consumo, com acesso restrito à empresa do usuário.
- **US22 — Registrar e consultar leituras:** recebimento de leituras pela API autenticada com token do dispositivo e consulta do histórico recente.
- **US23 — Acompanhar custos de anomalias:** configuração de tarifa compartilhada pela empresa e painel mensal que calcula o custo do consumo acima do limite dos dispositivos.
- **US18 — Gerenciar ordens de serviço:** criação de rascunhos por dispositivo, aprovação com registro do responsável e horário, acompanhamento da execução e conclusão com causa, ação realizada e tempo de parada.

### 🎥 Demonstrações em Vídeo

---

- 🎬 **[Screencast de explicação do código Django](https://youtu.be/MTF9BKQNVtI?si=Ci19lpYDu7i5IkUc)**

### 👾 Print Issue:

---

#### Quadro da Issue
![Print da Issue](https://github.com/trajanola/Nexora/blob/main/docs/Captura%20de%20Tela%202026-10-23%20a%CC%80s%2022.44.11.png)

### 📋 Backlog (Jira)

---

#### Quadro da Sprint 03
![Quadro da Sprint 03](./docs/entrega3_backlog_jira.png)

</details>

<details>
<summary><b>📌 Entrega 4: Implementação Completa do MVP, Testes E2E e CI/CD</b> (clique para expandir)</summary>

<br>

Consolidação dos 4 Épicos do MVP Nexora, testes automatizados de sistema (E2E) com Selenium, pipeline de integração e entrega contínua (CI/CD) no GitHub Actions e guia de contribuição.

---

### Histórias implementadas

Histórias implementadas na **Entrega 04** no formato **POST-IT** (além da evolução das entregas anteriores):

#### US02 — Endpoint REST para Ingestão de Leituras em Lote

| | |
|---|---|
| **Como** | Gerente de Manutenção (Carlos) |
| **Quero** | que o gateway da fábrica envie leituras de sensores em lote via API com autenticação por token e prevenção de duplicatas |
| **Para** | garantir que os dados de telemetria cheguem completos mesmo após oscilações de rede no chão de fábrica |
| **Critério de pronto** | Endpoint `POST /api/leituras/` aceita lote JSON com `id_externo` idempotente, persiste leituras válidas em rejeição parcial (`HTTP 207`) e suporta grandezas de energia (`kWh`), temperatura (`°C`) e vibração (`mm/s`) |

#### US03 — Tradutor de Anomalias em Custo Financeiro (R$)

| | |
|---|---|
| **Como** | Proprietário (Marcos) |
| **Quero** | visualizar no painel a conversão automática de leituras anômalas de energia em custo financeiro mensal em Reais (R$) e o payback do reparo preventivo |
| **Para** | entender imediatamente quanto dinheiro a fábrica está perdendo por ineficiência e priorizar investimentos |
| **Critério de pronto** | Painel calcula o consumo excedente mensal multiplicado pela tarifa da empresa, exibe alerta financeiro em R$/mês e calcula o payback estimado quando há custo de reparo preventivo cadastrado |

#### US04 — Calculadora de Eficiência Energética e Emissões de CO₂e

| | |
|---|---|
| **Como** | Diretora Financeira e de Compliance (Ana) |
| **Quero** | acompanhar a economia acumulada em kWh e a redução equivalente em emissões de CO₂e em relação à linha de base mensal |
| **Para** | comprovar metas de descarbonização e sustentabilidade perante auditorias e clientes corporativos |
| **Critério de pronto** | Painel compara o consumo mensal com a linha de base configurada, exibindo kWh economizados, percentual de redução e kg de CO₂e evitados |

#### US05 — Simulador de Elegibilidade e Estimativa de Crédito Verde BNDES

| | |
|---|---|
| **Como** | Diretora Financeira e de Compliance (Ana) |
| **Quero** | simular o financiamento de modernização com desconto na taxa de juros atrelado às metas de eficiência energética e ESG |
| **Para** | avaliar a viabilidade financeira de substituir ou reformar máquinas ineficientes com linhas de crédito verde |
| **Critério de pronto** | Tela `/credito-bndes/` calcula parcela mensal, total pago e economia estimada pela tabela Price com desconto configurável quando a empresa atinge redução positiva de consumo |

#### US06 — Motor de Diagnóstico Causal Multivariável (Regra de Negócio Prescritiva)

| | |
|---|---|
| **Como** | Gerente de Manutenção (Carlos) |
| **Quero** | que o sistema cruze dados de consumo elétrico, temperatura e vibração para apontar a causa provável da falha e uma recomendação prescritiva em linguagem simples |
| **Para** | orientar a equipe de manutenção direto na raiz do problema sem precisar interpretar gráficos complexos |
| **Critério de pronto** | Ingestão correlaciona picos simultâneos em até 10 minutos, registra `OcorrenciaDiagnostico` com causa provável, orientação prescritiva e perda financeira por hora, consolidando sinais repetidos em 5 minutos |

#### US07 — Alertas de Segurança Operacional e Conformidade (NR-12 e NR-15)

| | |
|---|---|
| **Como** | Gerente de Manutenção (Carlos) |
| **Quero** | receber alertas destacados de risco trabalhista e operacional quando os sensores ultrapassarem os limites de segurança da NR-12 e da NR-15 |
| **Para** | proteger os operadores de acidentes ou insalubridade térmica e evitar interdições e passivos trabalhistas |
| **Critério de pronto** | Violação de limite térmico (`NR-15`) ou vibração (`NR-12`) cria `AlertaSegurancaNormativa` crítico visível no painel e no detalhe do dispositivo, permitindo reconhecimento rastreável pelo responsável |

#### US08 — Algoritmo do Índice Nexora de Maturidade Operacional

| | |
|---|---|
| **Como** | Proprietário (Marcos) |
| **Quero** | visualizar uma pontuação automática de 0 a 100 e o estágio de maturidade operacional da minha fábrica (*Reativo, Preventivo, Preditivo, Prescritivo*) |
| **Para** | acompanhar a evolução da gestão industrial a partir da telemetria real sem responder questionários manuais |
| **Critério de pronto** | Algoritmo calcula o score automaticamente com base nos pilares operacionais da empresa e exibe no painel a pontuação atual, o estágio correspondente e os pontos/percentual restantes para o próximo nível |

#### US09 — Trilha Gamificada de Missões Operacionais

| | |
|---|---|
| **Como** | Proprietário (Marcos) |
| **Quero** | receber até 3 missões operacionais prioritárias com a pontuação estimada de ganho no índice de maturidade |
| **Para** | guiar minha equipe nas próximas ações práticas que trazem retorno rápido e aumentam a maturidade da planta |
| **Critério de pronto** | Painel lista até 3 missões prioritárias com recompensa em pontos de maturidade e atualiza automaticamente o status para *Concluída* quando a ação correspondente é detectada no sistema |

#### US10 — Dossiê Digital Auditável Criptografado para Homologação

| | |
|---|---|
| **Como** | Diretora Financeira e de Compliance (Ana) |
| **Quero** | emitir e exportar um Dossiê Digital Auditável em PDF e JSON contendo resumo executivo, histórico energético, indicadores NR-12/NR-15 e hash criptográfico de validação |
| **Para** | comprovar a conformidade técnica, energética e trabalhista da fábrica em processos de homologação B2B com grandes montadoras |
| **Critério de pronto** | Tela `/dossie-auditoria/` gera dossiê com timestamp imutável, hash `SHA-256` do payload canônico e assinatura `HMAC-SHA256`, permitindo download imediato em formato PDF e JSON |

---

### 🤝 Guia de Contribuição

Qualquer pessoa pode configurar o ambiente, rodar a suíte de testes e colaborar com o projeto seguindo nosso guia passo a passo:
- 📄 **[Guia de Contribuição (CONTRIBUTING.md)](./CONTRIBUTING.md)**

---

### 🧪 Testes de Sistema (E2E) e Pipeline CI/CD

- **Testes E2E com Selenium:** implementados em [`core/tests_e2e.py`](./core/tests_e2e.py), cobrindo cadastro/login, isolamento por empresa, alertas financeiros e reparo preventivo, eficiência energética + crédito BNDES, diagnóstico causal multivariável + NR-12/NR-15 e maturidade operacional + missões + emissão de dossiê auditável.
- **Pipeline GitHub Actions:** configurada em [`.github/workflows/ci.yml`](./.github/workflows/ci.yml) com os jobs `Django test suite` e `Selenium E2E suite`.

---

### 🎥 Demonstrações em Vídeo (Entrega 04)

- 🎬 **Screencast das novas histórias em produção (URL visível):** _Adicionar link do YouTube_
- 🎬 **Screencast da execução dos testes E2E (Selenium) com áudio:** _Adicionar link do YouTube_
- 🎬 **Screencast do pipeline de CI/CD (build, testes e deploy) com áudio:** _Adicionar link do YouTube_
- 🎬 **Screencast de explicação do código Django (URL -> View -> Template -> Model):** _Adicionar link do YouTube_

---

### 📋 Quadro da Sprint 04 (Jira)

![Quadro da Sprint 04](./docs/entrega3_backlog_jira.png)

</details>

## 🤝 &nbsp;Como Contribuir

Leia o nosso **[Guia de Contribuição (CONTRIBUTING.md)](./CONTRIBUTING.md)** para instruções detalhadas sobre criação de branches, execução dos testes unitários e E2E com Selenium e abertura de Pull Requests.

## 🔗 &nbsp;Links Importantes

-  📑 [&nbsp;Jira](https://nexora-cesar.atlassian.net/jira/software/projects/NEX/summary?atlOrigin=eyJpIjoiOTVmMjUwY2UzMzlkNDExOTgzMDMxZjRjNzMxNDI0OTUiLCJwIjoiaiJ9)
-  **O BackLog das entregas se encontra na aba de documentos do Jira.**
-  Deploy em Desenvolvimento: [Clique Aqui](http://3.95.179.201)

## 🐞 &nbsp;Encontrou um bug?
- Abra uma issue na aba **[Issues](https://github.com/trajanola/Nexora/issues)** do repositório e inclua os passos para reproduzir o problema.
