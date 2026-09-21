---
prd_number: "001"
status: pronto
priority: alta
created: 2026-09-21
issue: "PST-1"
depends_on: []
references:
  - "https://mygotryx.atlassian.net/browse/PST-1"
  - "docs/trd.md"
  - "docs/adrs/001-clean-core-odoo-metadata.md"
  - "docs/superpowers/specs/2026-09-21-posentinel-core-design.md"
---

# PRD 001: Linter Determinístico Core e Validação de Placeholders

## 1. Contexto

- **Produto/área**: Qualidade de Internacionalização (i18n) no ecossistema Odoo.
- **Estado atual**: Desenvolvedores e times de localização traduzem arquivos `.po` manualmente ou via ferramentas externas. Erros sutis em placeholders (`%s`, `%(name)s`), tags HTML quebradas ou termos vazios passam despercebidos até causarem falhas em tempo de execução (`TypeError: not all arguments converted during string formatting`) ou quebras de tela no ambiente produtivo do cliente.
- **Problema**: A ausência de um linter automatizado, determinístico e contextualizado para o Odoo em pipelines de CI/CD gera retrabalho, bugs em produção e degradação da experiência do usuário em português (`pt_BR`).

> **Contexto técnico**: Stack, arquitetura e convenções técnicas estão formalizados no [TRD](file:///mnt/home/alexandre/Projetos/PoSentinel/docs/trd.md) e no [ADR 001](file:///mnt/home/alexandre/Projetos/PoSentinel/docs/adrs/001-clean-core-odoo-metadata.md).

---

## 2. Solução Proposta

### Visão de produto
- Entregar uma ferramenta CLI leve, determinística e veloz (`posentinel scan`) que inspeciona arquivos `.po` de módulos Odoo antes do commit e em pipelines de CI/CD.
- Identificar imediatamente falhas estruturais críticas de formatação (`PO002`, `PO003`, `PO004`), strings vazias (`PO001`), markup rompido (`PO005`) e traduções pendentes de revisão (`PO006` fuzzy).
- Exibir relatórios claros no terminal apontando a linha, o módulo Odoo (`sale`, `account`, etc.) e o modelo/campo afetado.
- Disponibilizar saída estruturada em JSON e códigos de saída semânticos (`0`, `1`, `2`) para automação contínua.

### Decisões de produto
1. **Determinismo absoluto no MVP**: Sem dependência de modelos de linguagem (IA) no Core v0.1.0 para garantir previsibilidade, velocidade instantânea e zero custo de API em CI/CD.
2. **Contexto Odoo visível no diagnóstico**: O usuário não vê apenas a string isolada, mas sim o módulo e modelo ao qual ela pertence, agilizando a correção direta no código-fonte.
3. **Suporte nativo a plurais**: Strings com formas singulares e plurais (`msgid_plural`) devem ter suas variações validadas com o mesmo rigor.

### Fora do escopo
- Alteração ou correção automática de arquivos em disco (`posentinel fix` - previsto para o PRD 004).
- Análise semântica por inteligência artificial (`posentinel[ai]` - previsto para o PRD 003).
- Suporte a outros formatos de internacionalização além de `.po` (como XLIFF, JSON, YAML - previstos para versões posteriores).

---

## 3. Funcionalidades

### US01: Inspeção de Arquivo e Diretório via CLI
Como desenvolvedor de módulos Odoo,  
quero rodar `posentinel scan <caminho>` apontando para um arquivo `.po` ou diretório de módulos,  
para identificar se existem inconformidades nas minhas traduções.

**Rules:**
- O comando deve aceitar tanto um arquivo `.po` individual quanto um diretório (varredura recursiva de todos os `*.po`).
- Retorna exit code `0` se não houver problemas impeditivos.
- Retorna exit code `1` se houver violações no nível configurado (`--fail-on`).
- Retorna exit code `2` em caso de erro operacional (arquivo inexistente ou sintaxe corrompida).

**Edge cases:**
- Arquivo sem nenhuma entrada ou vazio → Exibe aviso de arquivo vazio e retorna exit code `0`.
- Arquivo em encoding não-UTF8 (ex: Latin-1) → Realiza fallback transparente de leitura sem quebrar a execução.

### US02: Validação Rigorosa de Placeholders (PO002, PO003, PO004)
Como desenvolvedor Odoo,  
quero que a ferramenta aponte placeholders ausentes, alterados ou extras entre o texto original e a tradução,  
para evitar exceções fatais de formatação (`TypeError`) no servidor Odoo.

**Rules:**
- Detectar especificadores printf (`%s`, `%d`, `%f`, etc.), printf nomeados (`%(partner_name)s`) e chaves Python (`{name}`, `{0}`).
- `PO002` (ERROR): Disparado se qualquer placeholder do original estiver ausente em `msgstr` ou em qualquer uma das formas plurais.
- `PO003` (ERROR): Disparado se uma variável nomeada foi inadvertidamente traduzida (ex: `%(data)s` em vez de `%(date)s`).
- `PO004` (ERROR): Disparado se a tradução contiver mais placeholders do que o texto original.

**Edge cases:**
- Strings com caracteres de porcentagem escapados (`%%`) → Não devem ser computadas como placeholders reais.
- Entradas plurais (`msgid_plural`) com variáveis numéricas (`%d`) → Todas as formas plurais (`msgstr[0]`, `msgstr[1]`) são avaliadas.

### US03: Detecção de Entradas Vazias, Markup Inválido e Fuzzy (PO001, PO005, PO006)
Como revisor de traduções,  
quero ser alertado sobre termos não traduzidos, tags HTML corrompidas e strings fuzzy,  
para garantir que a interface do usuário final permaneça consistente e íntegra.

**Rules:**
- `PO001` (WARNING): Termo original existente com tradução em branco (excluindo cabeçalho de metadados do PO).
- `PO005` (WARNING): Tags HTML/XML (ex: `<a>`, `<b>`, `<br/>`) presentes no original que foram omitidas ou fechadas incorretamente.
- `PO006` (WARNING): Termos marcados com flag `#, fuzzy`, indicando tradução desatualizada.

**Edge cases:**
- Cabeçalho do arquivo PO (`msgid ""`) → Ignorado por PO001.

### US04: Exportação em JSON e Relatório Visual
Como engenheiro de DevOps,  
quero exportar os resultados com `--format json` ou visualizar no terminal com cores e tabelas,  
para integrar as validações facilmente no GitHub Actions, GitLab CI ou no terminal local.

**Rules:**
- No modo console, utilizar `rich` com tabelas, cores por severidade (`ERROR`, `WARN`, `INFO`) e sumário de contadores.
- No modo JSON, emitir payload válido contendo caminho, locale, contadores e lista de issues com códigos, linha e módulo Odoo.

---

## 4. Critérios de Aceite

### 4a. Critérios de aceite da feature

| Critério | Razão de negócio | Como verificar (observável) |
|---|---|---|
| Varredura completa de arquivo com 10.000 entradas em < 1.5s | Não atrasar commits e pipelines de CI | Executar `posentinel scan` com medição de tempo |
| Exit code `1` imediato quando houver erros | Bloquear merge de Pull Requests com erro de placeholder | Verificar retorno `$?` após scan em arquivo inválido |
| Identificação do módulo Odoo nas issues | Desenvolvedor saber exatamente qual addon precisa de correção | Validar presença do campo `odoo_context` na saída console e JSON |

### 4b. Métricas de sucesso

| Métrica | Baseline | Meta | Prazo | Mín. aceitável | Responsável |
|---|---|---|---|---|---|
| Cobertura de testes unitários | 0% | ≥ 90% | v0.1.0 | 85% | Tech Lead |
| Detecção de falhas de placeholders em testes | 0% | 100% | v0.1.0 | 100% | Core Team |

---

## 5. Milestones

### Milestone 1: Core Engine e Validação de Placeholders (v0.1.0)
**Por que é um marco:** Entrega a primeira versão funcional e distribuível do PoSentinel capaz de proteger pipelines reais de Odoo contra as falhas mais frequentes e perigosas de internacionalização.
**Funcionalidades:** US01, US02, US03, US04.
**Checklist de aceite:**
- [ ] Empacotamento PyPI instalado e executando via terminal (`posentinel`).
- [ ] Parser extraindo metadados Odoo e lidando com singulares e plurais.
- [ ] Regras PO001 a PO006 ativas e testadas.
- [ ] Relatórios Console e JSON validados.
- [ ] Testes automatizados passando com cobertura ≥ 90%.
**Aprovador:** Alexandre (Tech Lead)
