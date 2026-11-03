# PoSentinel

[![PyPI version](https://img.shields.io/pypi/v/posentinel.svg)](https://pypi.org/project/posentinel/)
[![Python versions](https://img.shields.io/pypi/pyversions/posentinel.svg)](https://pypi.org/project/posentinel/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Analisador de Qualidade de Tradução para Odoo** — Proteja as traduções do seu ecossistema Odoo e evite falhas críticas em produção.

---

## O que é o PoSentinel?

O **PoSentinel** é um linter determinístico voltado para a validação de arquivos de localização `.po`, com foco especial em módulos do sistema Odoo e na língua portuguesa (`pt_BR`). 

No Odoo, um erro simples de digitação em um placeholder (por exemplo, traduzir `%(name)s` para `%(nome)s`) pode causar **erros de servidor irreversíveis (Internal Server Error / Tracebacks)** ao renderizar uma visualização ou relatório. O PoSentinel foi criado exatamente para detectar essas anomalias em tempo de desenvolvimento ou integração contínua (CI/CD).

### Principais Funcionalidades

- **Proteção de Placeholders:** Identifica se variáveis Python (como `%s`, `%d`, `%.2f`, `%(partner_id)s`, `{value}`) foram apagadas, alteradas ou inseridas indevidamente na tradução.
- **Validação de Marcação (Markup):** Detecta tags HTML/XML desbalanceadas ou corrompidas (ex: `<strong>` sem o devido fechamento `</strong>`), com suporte nativo a tags void (`<br>`, `<img>`).
- **Conformidade com Glossário Regulatório:** Assegura o uso de termos obrigatórios definidos no projeto (ex.: regras regulatórias MOVER / Inovar-Auto).
- **Consistência de Pontuação e Espaçamento:** Verifica correspondência de dois-pontos e pontos finais, e remove espaços indevidos antes de pontuação dupla no padrão pt_BR.
- **Detecção de Termos Duvidosos:** Avisa sobre traduções vazias ou marcadas como `fuzzy` (desatualizadas).
- **Edição Cirúrgica (`lookup` e `set`):** Consulta status e atualiza traduções diretamente no `.po` sem corromper quebras de linha (CRLF/LF), permissões de arquivo ou gerar diffs desnecessários.
- **Formatos de Saída Versáteis:** Resultados visuais detalhados no terminal ou exportação em JSON para automações estruturadas.
- **Assistente de Tradução (Opcional):** Integração opcional para sugerir traduções contextuais diretamente pelo terminal ou gerar subagente dedicado para Claude Code.

---

## Instalação

Recomendamos instalar o PoSentinel usando `pipx` ou `uv` para isolar suas dependências, ou diretamente via `pip` no seu ambiente:

```bash
# Usando pip tradicional
pip install posentinel

# Ou usando uv (recomendado)
uv tool install posentinel
```

---

## Como Usar (Guia Rápido)

### 1. Varredura Básica (`scan`)

Para escanear um único arquivo ou todos os arquivos de um diretório recursivamente:

```bash
# Inspecionar um arquivo específico
posentinel scan caminho/para/pt_BR.po

# Inspecionar uma pasta de um módulo Odoo
posentinel scan ./addons/meu_modulo/i18n

# Comparar apenas alterações novas em relação a uma baseline ou ref Git
posentinel scan pt_BR.po --baseline baseline/pt_BR.po
posentinel scan pt_BR.po --changed-only origin/main
```

### 2. Edição e Consulta Cirúrgica (`lookup` e `set`)

Ideal para pipelines, scripts ou assistentes automatizados (como subagentes de tradução) que precisam consultar e atualizar entradas pontuais com segurança total:

```bash
# Consulta status de um termo (missing, empty, fuzzy ou translated)
posentinel lookup pt_BR.po "Invoice %s" --format json

# Atualiza a tradução de forma atômica, preservando line endings (CRLF/LF) e chmod
posentinel set pt_BR.po "Invoice %s" "Fatura %s"

# Simula alteração e visualiza apenas o diff gerado sem gravar no disco
posentinel set pt_BR.po "Discount" "Desconto" --dry-run
```

### 3. Integração com Pipelines (CI/CD)

O PoSentinel é ideal para barrar Pull Requests que introduzam erros de tradução. 
Você pode ajustar o nível de rigor da análise com o parâmetro `--fail-on`:

```bash
# O comando só falha (exit code 1) se houver ERROS graves (placeholders corrompidos). Ignora avisos.
posentinel scan pt_BR.po --fail-on error

# O comando falha se houver ERROS ou AVISOS (traduções vazias, fuzzy, pontuação).
posentinel scan pt_BR.po --fail-on warning
```

Exemplo de uso no **GitHub Actions**:

```yaml
name: Validar Traduções
on: [pull_request]
jobs:
  posentinel:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Instalar PoSentinel
        run: pip install posentinel
      - name: Rodar Inspeção
        run: posentinel scan ./addons --fail-on error
```

### 4. Gerar Saída para Ferramentas Terceiras

Para exportar as falhas num formato processável, utilize `--format json`:

```bash
posentinel scan pt_BR.po --format json > report.json
```

---

## Regras de Validação Ativas

Consulte as regras ativas a qualquer momento com `posentinel rules`:

| Código | Severidade | Descrição |
|---|---|---|
| **PO001** | WARNING | Termo original com tradução vazia |
| **PO002** | ERROR | Placeholder do original ausente na tradução (`%s`, `%.2f`, `%(x)s`, `{var}`) |
| **PO003** | ERROR / WARNING | Variável nomeada traduzida por engano ou caractere `%` solto em template |
| **PO004** | ERROR | Tradução contém mais placeholders do que o original ou mistura `%s` com `%(x)s` |
| **PO005** | WARNING | Tags HTML/XML omitidas ou desequilibradas na tradução (void tags tratadas) |
| **PO006** | WARNING | Entrada marcada como fuzzy (`#, fuzzy`), pendente de revisão |
| **PO007** | WARNING | Termo obrigatório do glossário não utilizado na tradução |
| **PO010** | WARNING | Divergência de pontuação final (`:`, `.`) ou espaçamento antes de pontuação dupla |

---

## Arquivo de Configuração

O PoSentinel descobre automaticamente o arquivo `posentinel.toml` subindo a árvore de diretórios ancestrais (estilo Ruff/ESLint). Você também pode especificar o arquivo via `--config / -c`:

```toml
[project]
source_language = "en_US"
target_language = "pt_BR"

[project.glossary]
"vehicle recycling certificate" = ["Certificado de Reciclagem Veicular", "CRV"]
"dismantling" = ["desmontagem"]
"scrapped" = ["baixa", "baixado"]

[scan]
target = "./addons"
fail_on = "error"
format = "console"
ignore_rules = ["PO006"]

[ai]
enabled = false
auto_translate = false
```

---

## Assistente de Tradução por IA

O PoSentinel conta com um assistente capaz de sugerir traduções contextuais e corrigir inconsistências técnicas através da API do Claude (Anthropic).

**Configurando o Acesso:**

Você pode conectar o assistente à API da Anthropic de duas maneiras:

**Opção 1: Via Chave de API (Tradicional)**
Exporte a chave gerada no Console da Anthropic no seu terminal:
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

**Opção 2: Via SSO / OAuth (Recomendado para Empresas)**
Se você possui uma assinatura vinculada a um SSO ou prefere não manipular chaves puras, utilize a CLI oficial da Anthropic (`ant`).
Basta rodar o comando de autenticação no terminal:
```bash
ant auth login
```
Isso abrirá uma janela no seu navegador para o fluxo de Single Sign-On (SSO). Após o login com sucesso, o token ficará salvo no seu perfil local. 
O PoSentinel utiliza o SDK oficial da Anthropic, que é capaz de detectar e **utilizar essa sessão de SSO automaticamente**, sem a necessidade de nenhuma configuração adicional ou variáveis de ambiente!

**Utilizando o Assistente:**
Rode o scan com a flag `--translation`:

```bash
# Analisa os erros e sugere traduções perguntando (Y/n) antes de aplicar:
posentinel scan pt_BR.po --translation

# Analisa e aplica a correção da IA de forma 100% automática:
posentinel scan pt_BR.po --translation --auto-translate
```

---

## Licença

Este projeto é distribuído sob a licença [MIT](LICENSE).
