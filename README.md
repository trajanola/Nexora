# _NEXORA_

## 👥 &nbsp;Integrantes do Projeto

<div align="center">

| Membro | E-mail |
| :---: | :---: |
| Arthur Santanda de Andrade | **asa4@cesar.school** |
| Lucas Silva Moreira do Nascimento | **lsmn@cesar.school** |
| Mariana de Melquiades Melo | **mmm4@cesar.school** |
| Matheus Trajano de Freitas | **mtf@cesar.school** |
| Paulo Ferreira Fonseca dos Santos | **pffs@cesar.school** |
| Ricardo Amorim Amorim Bayma | **rab5@cesar.school** |
| Lucas Berenguer Avelino de Souza | **lbas@cesar.school** |
| Matheus Guerra Britto | **mgb3@cesar.school** |

</div>

---

## 🎯 &nbsp;Contexto e Propósito

A maioria das empresas falha na adoção de IoT não por falta de sensores, mas por incapacidade de **transformar** dados brutos em inteligência aplicável. O objetivo central da _NEXORA_ é ir além de um simples dashboard passivo: a plataforma foi desenhada para educar as empresas, traduzindo sinais operacionais em percepção de **valor financeiro e orientação estratégica**.

---

## 📝 &nbsp;Descrição do Projeto

A _NEXORA_ é uma plataforma desenvolvida para modernizar, simplificar e otimizar a gestão de ecossistemas educacionais. O sistema conecta alunos, professores e administradores em um ambiente integrado, intuitivo e funcional, facilitando o acompanhamento acadêmico, a organização de conteúdos e a comunicação institucional.

---

## 🛠️ &nbsp;Tecnologias Utilizadas

- Python
- Django
- HTML5
- JIRA

---
## 🔗 &nbsp;Links Importantes

-  📑 [&nbsp;Jira](https://nexora-cesar.atlassian.net/jira/software/projects/NEX/summary?atlOrigin=eyJpIjoiOTVmMjUwY2UzMzlkNDExOTgzMDMxZjRjNzMxNDI0OTUiLCJwIjoiaiJ9)
-  **O BackLog das entregas se encontra na aba de documentos do Jira.**
-  [Deploy em Desenvolvimento:](http://3.95.179.201)
---
## Como rodar o projeto localmente

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
export SECRET_KEY="cole-a-chave-gerada-aqui"
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

### 🐞 Encontrou um bug?

Abra uma issue na aba **Issues** do repositório e inclua os passos para reproduzir o problema.
---
## 📅 &nbsp;Entregas do Projeto

### 📌 &nbsp;Entrega 1
- **[Desk Research](https://www.figma.com/board/jxNemj7jNW6uGalSK9BPTA/Projetos-2?t=3C9odntDyPqumqQf-0)**

- **[Documento de Análise de Competidores](https://github.com/trajanola/Nexora/blob/main/Documenta%C3%A7%C3%A3o_Interface.md)**

- **BenchMark da Análise de Competidores:**

| Funcionalidade / Competidor | atDesigner-TP | Plataforma IoT Tecnolog | Node-RED | Blynk IoT | AWS IoT Core | 🚀 _NEXORA_ |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Interface simples e de fácil uso** | ❌ | ✅ | ❌ | ✅ | ❌ | ✅ |
| **Reúne informações de forma eficiente** | ❌ | ❌ | ❌ | ✅ | ❌ | ✅ |
| **Ferramentas personalizáveis** | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ |
| **Qtd. de dispositivos simultâneos** | 32 | 20-30 | 15-25 | 10-20 | 30-40 | **50** |
| **Segurança e controle de acesso** | ❌ ❌ | ✅ ❌ | ❌ ❌ | ✅ ❌ | ✅ ✅ | ✅ ✅ |

- **Interface - Protótipo Não Funcional:**

![Interface não funcional](https://github.com/trajanola/Nexora/blob/main/docs/Interface%20Nexora.png)

- **Quadro da Sprint 01:**

![Print do Jira](https://github.com/trajanola/Nexora/blob/main/docs/Quadro%201.png)
  
### 📌 &nbsp;Entrega 2
- **Screencast Deployment da infaestrutura em produção:**
[Vídeo - Screencast Deployment](https://youtu.be/GkYC9-hXWlg)
- **Screencast de explicação do código Django:**
[Vídeo - Screencast Código](https://youtu.be/Fvb92Io1STo)
- **Quadro da Sprint 02:**

![Print do Quadro](https://github.com/trajanola/Nexora/blob/main/docs/Quadro%202.png)

### 📌 &nbsp;Entrega 3
- *Conteúdo indisponível temporariamente.*

### 📌 &nbsp;Entrega 4
- *Conteúdo indisponível temporariamente.*

---
