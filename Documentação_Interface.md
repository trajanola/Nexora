# Documentação de Interface: Plataforma Nexora

## 1. Visão Geral da Plataforma
A plataforma foi criada para armazenar e facilitar o gerenciamento de dados captados por sensores. A interface foi projetada para oferecer acompanhamento em tempo real, levantamento histórico e controle de parâmetros operacionais dos dispositivos.

---

### 1.1. Visão Geral do Problema
As Pequenas e Médias Empresas (PMEs) movimentam a economia real, mas a forma tradicional como o mercado vende "ESG" afasta o pequeno empresário.

| Indicador/Fator | O que os dados mostram? | O que isso significa na prática? |
| :---: | :---: | :---: |
| **Importância Econômica** | 26,5% do PIB e 80% das vagas de trabalho formais. | As PMEs sustentam o país, mas operam com margens de lucro apertadas. |
| **O Paradoxo do ESG** | 67% dos gestores não sabem o que a sigla ESG significa. | A maioria já faz boas ações no dia a dia, mas não sabe comprovar isso. |
| **Foco da Gestão** | O dono centraliza tudo e passa o dia "apagando incêndios". | Ninguém tem tempo para preencher relatórios longos e burocráticos. |
| **O Risco de Ficar Parado** | Grandes empresas e bancos já cobram critérios sustentáveis. | A empresa perde contratos de fornecimento e paga juros mais altos em empréstimos. |

### 1.2. Benchmarking: O Que o Mercado Oferece vs. Onde Ele Falha
Para entender por que as PMEs não usam as ferramentas atuais, analisamos os três tipos de soluções existentes:

| Categoria de Solução | Exemplos | O que faz bem? | Por que não serve para o Marcos? |
| :---: | :---: | :---: | :---: |
| Sistemas Corporativos Globais | Workiva, Sphera | Relatórios completos para multinacionais da Bolsa de Valores | Custo altíssimo em dólar, exige equipe técnica dedicada e consultorias caras. |
| SaaS ESG Simples (Questionários) | Paresi, Improvefy | Questionários guiados e planos de ação em português. | Depende de preenchimento manual no teclado; Marcos não tem tempo para responder formulários. |
| Supervisórios de IoT Tradicionais | atDesigner-TP, Plataforma Tecnolog | Monitora temperatura e consumo de energia por sensores. | Mostra apenas gráficos técnicos (, ), sem explicar como aquilo vira dinheiro ou conformidade. |

# Comparativo Direto de Recursos

| Funcionalidade / Recurso | atDesigner-TP | Plataforma Tecnolog | SaaS ESG Comum | Plataforma NEXORA |
| :---: | :---: | :---: | :---: | :---: |
| **Facilidade de Uso** | Complexa e técnica³ | Simples³ | Moderada (formulários)⁴ | Direta, visual e executiva³ |
| **Como Coleta os Dados?** | Sensores (via nuvem)³ | Sensores (via nuvem)³ | Digitação manual⁴ | Sensores automáticos na fábrica³ |
| **Limite de Aparelhos** | Até 32 dispositivos³ | 20 a 30 dispositivos³ | Não se aplica⁴ | Mais de 50 dispositivos³ |
| **Converte em Dinheiro (R$)?** | Não³ | Não³ | Estimativas teóricas⁴ | Sim, mostra o ganho em R$³ |
| **Explica a Causa do Problema?** | Apenas apita o alarme³ | Não³ | Não⁵ | Sim, cruza dados e aponta a raiz³ |
| **Funciona se a Internet Cair?** | Não (trava)³ | Guarda pouco cache³ | Não (precisa de web)⁴ | Sim (*Offline-First*)³ |
| **Ajuda a Vender para Grandes Clientes?** | Não³ | Não³ | Gera relatórios em PDF⁴ | Gera comprovação pronta para compras¹ |

---

## 2. Navegação Principal
A barra superior organiza o sistema em quatro abas principais:

* **Dispositivos:** Gestão individualizada, métricas e estado operacional de cada unidade conectada.
* **Dados:** Levantamento geral, relatórios consolidados e histórico analítico dos sensores.
* **Configuração:** Ajustes de parâmetros, preferências da plataforma e calibração dos aparelhos.
* **Alertas:** Painel centralizador de notificações críticas e avisos de manutenção urgente.

---

## 3. Painel do Dispositivo (Aba "Dispositivos")
Ao selecionar uma unidade específica, a tela apresenta **três seções principais**:

### 3.1. Gráficos de Desempenho
* **Formato:** Medidores radiais / mostradores analógicos (*gauges*).
* **Finalidade:** Monitorar grandezas instantâneas do equipamento em relação a escalas limites e faixas de tolerância.
* **Recursos Visuais:**
  * Indicadores de faixas seguras e limites operacionais.
  * Marcadores e avisos dinâmicos para limites ultrapassados.

### 3.2. Gráficos de Acompanhamento de Desempenho na Função
* **Formato:** Gráficos de linha contínuos (séries temporais).
* **Finalidade:** Avaliar a estabilidade, oscilações e tendências de comportamento do equipamento durante a execução de suas atividades.
* **Registro de Eventos:** Marcadores pontuais sobre a linha temporal destacando ocorrências e justificativas operacionais.

### 3.3. Dados Importantes
Painel de cartões com indicadores essenciais, pré-definidos conforme a função do aparelho e customizáveis pelo usuário:

* **Nível de Bateria / Carga:** Indicador percentual com avisos de recarga.
* **Temperatura / Nível Térmico:** Medidor com leitura de valor e estado de equilíbrio térmico.
* **Status Operacional:** Indicador de atividade e controle de funcionamento da unidade.

## 📌 Benchmarking

| Critério de Avaliação | atDesigner-TP | Dashboards IoT Tecnolog | Node-RED | Blynk IoT | AWS IoT Core | NEXORA |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Interface simples e de fácil uso** | ❌ | ✅ | ❌ | ✅ |❌| ✅ |
| **Reúne informações de forma eficiente** | ❌ | ❌ | ❌ | ✅ |❌| ✅ |
| **Variedade de ferramentas personalizáveis** | ✅ | ❌ | ✅ | ❌ |✅| ✅ |
| **Dispositivos simultâneos** | `32` | `20-30` | `15-25` | `10-20` |`30-40`| **`50`** |
| **Segurança e controle de acesso** | ❌ ❌ | ✅ ❌ | ❌ ❌ | ✅ ❌ |✅ ✅| ✅ ✅ |

<br>

<br>

> **Legenda:**
> * ✅ = Atendido / Suporte total
> * ✅ ❌ = Atendido parcialmente
> * ❌ = Não atendido
> * ❌ ❌ = Sem suporte / Crítico

<p align="center">
  <img src="image_2026-08-29_160049600.png" alt="Texto Alt" width="700">
</p>
