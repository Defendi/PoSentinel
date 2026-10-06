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

- **Proteção de Placeholders:** Identifica se variáveis Python (como `%s`, `%d`, `%(partner_id)s`, `{value}`) foram apagadas, alteradas ou inseridas indevidamente na tradução.
- **Validação de Marcação (Markup):** Detecta tags HTML/XML desbalanceadas ou corrompidas (ex: `<strong>` sem o devido fechamento `</strong>`).
- **Detecção de Termos Duvidosos:** Avisa sobre traduções vazias ou marcadas como `fuzzy` (desatualizadas).
- **Formatos de Saída Versáteis:** Resultados visuais detalhados no terminal ou exportação em JSON para automações estruturadas.
- **Assistente de Tradução (Opcional):** Integração opcional para corrigir automaticamente as traduções diretamente pelo terminal.

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

O comando principal é o `posentinel scan`, que pode receber o caminho de um arquivo específico ou de um diretório inteiro.

### 1. Varredura Básica

Para escanear um único arquivo ou todos os arquivos de um diretório recursivamente:

```bash
# Inspecionar um arquivo específico
posentinel scan caminho/para/pt_BR.po

# Inspecionar uma pasta de um módulo Odoo
posentinel scan ./addons/meu_modulo/i18n
```

### 2. Integração com Pipelines (CI/CD)

O PoSentinel é ideal para barrar Pull Requests que introduzam erros de tradução. 
Você pode ajustar o nível de rigor da análise com o parâmetro `--fail-on`:

```bash
# O comando só falha (exit code 1) se houver ERROS graves (placeholders corrompidos). Ignora avisos.
posentinel scan pt_BR.po --fail-on error

# O comando falha se houver ERROS ou AVISOS (traduções vazias, fuzzy).
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

### 3. Gerar Saída para Ferramentas Terceiras

Para exportar as falhas num formato processável, utilize `--format json`:

```bash
posentinel scan pt_BR.po --format json > report.json
```

---

## Arquivo de Configuração

Para não precisar digitar as opções no terminal toda vez, você pode criar um arquivo `posentinel.toml` na raiz do seu projeto. O PoSentinel fará a leitura automática deste arquivo:

```toml
[project]
source_language = "en_US"
target_language = "pt_BR"

[scan]
target = "./addons"
fail_on = "error"
format = "console"

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
