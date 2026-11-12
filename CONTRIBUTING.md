# Guia de Contribuição — Nexora

Obrigado pelo interesse em contribuir com o **Nexora**! Este guia descreve o fluxo de trabalho, padrões de código, configuração do ambiente local e execução dos testes automatizados (unitários e End-to-End com Selenium) exigidos pela pipeline de CI/CD.

---

## 1. Pré-requisitos

- **Git** instalado (`git --version`)
- **Python 3.12+** (`python3 --version`)
- **Google Chrome** instalado (necessário para os testes E2E com Selenium)

---

## 2. Configuração do Ambiente Local

1. **Clone o repositório e acesse a pasta do projeto:**

   ```bash
   git clone https://github.com/trajanola/Nexora.git
   cd Nexora
   ```

2. **Crie e ative o ambiente virtual (`venv`):**

   - **Linux / macOS:**
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```
   - **Windows (PowerShell):**
     ```powershell
     python -m venv venv
     venv\Scripts\Activate.ps1
     ```

3. **Instale as dependências de produção e desenvolvimento:**

   ```bash
   pip install -r requirements-dev.txt
   ```

4. **Configure a variável de ambiente `SECRET_KEY` e aplique as migrações:**

   - **Linux / macOS:**
     ```bash
     export SECRET_KEY="chave-local-de-desenvolvimento-com-mais-de-50-caracteres-seguros"
     python manage.py migrate
     ```
   - **Windows (PowerShell):**
     ```powershell
     $env:SECRET_KEY = "chave-local-de-desenvolvimento-com-mais-de-50-caracteres-seguros"
     python manage.py migrate
     ```

---

## 3. Fluxo de Branches e Pull Requests

1. **Mantenha sua branch `develop` atualizada:**
   ```bash
   git checkout develop
   git pull origin develop
   ```
2. **Crie uma branch descritiva para sua funcionalidade ou correção:**
   ```bash
   git checkout -b feat/us08-maturidade-operacional
   ```
3. **Padrão de commits:**
   - Faça commits frequentes, coesos e com mensagens claras em português (ex.: `Implementa US08, US09 e US10 do Épico 4`).
   - Sempre gere migrações caso altere `core/models.py` (`python manage.py makemigrations`).
   - Nunca versione arquivos `.env`, segredos (`SECRET_KEY`) ou o arquivo `db.sqlite3`.

4. **Abra um Pull Request (PR):**
   - Envie sua branch para o repositório remoto (`git push -u origin <sua-branch>`).
   - Abra o PR direcionado para `develop` (ou `main` no fechamento da entrega), descrevendo as Histórias de Usuário atendidas e aguardando a validação verde da pipeline do **GitHub Actions**.

---

## 4. Executando os Testes Automatizados (CI Local)

Antes de abrir qualquer Pull Request, valide ambos os jobs executados pelo GitHub Actions (`.github/workflows/ci.yml`):

### 4.1. Verificação do Django e Testes Unitários / Integração

```bash
export SECRET_KEY="ci-only-secret-key-with-more-than-fifty-characters-for-checks"
export DEBUG="False"
export SECURE_SSL_REDIRECT="False"
export ALLOWED_HOSTS="localhost,127.0.0.1"

python manage.py makemigrations --check --dry-run
python manage.py check
python manage.py test
```

### 4.2. Testes de Sistema (E2E) com Selenium

Como os testes E2E rodam com `DEBUG="False"`, é obrigatório executar `collectstatic` antes de iniciar o `LiveServerTestCase`:

```bash
export SECRET_KEY="ci-only-secret-key-with-more-than-fifty-characters-for-checks"
export DEBUG="False"
export SECURE_SSL_REDIRECT="False"
export ALLOWED_HOSTS="localhost,127.0.0.1"
export SELENIUM_HEADLESS="1"

python manage.py collectstatic --no-input
python manage.py test core.tests_e2e --verbosity=2
```

---

## 5. Estrutura Principal do Projeto

- `config/`: configurações do projeto Django (`settings.py`, `urls.py`).
- `core/models.py`: modelos ORM de empresas, dispositivos, leituras, ocorrências, alertas NR-12/NR-15, ordens de serviço, missões operacionais e dossiês de auditoria.
- `core/services.py`: regras de negócio de tradução financeira, ESG/CO₂e, crédito BNDES, diagnóstico causal multivariável, maturidade operacional, missões gamificadas e emissão de dossiê auditável (PDF/JSON).
- `core/views.py` e `core/urls.py`: endpoints REST e views da aplicação web.
- `core/tests.py` e `core/tests_e2e.py`: suíte de testes unitários/integração e testes de sistema E2E com Selenium.
- `docs/historias-de-usuario.md`: especificação BDD (Gherkin) e post-its das Histórias de Usuário.
