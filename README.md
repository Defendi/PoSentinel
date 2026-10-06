# PoSentinel

[![PyPI version](https://img.shields.io/pypi/v/posentinel.svg)](https://pypi.org/project/posentinel/)
[![Python versions](https://img.shields.io/pypi/pyversions/posentinel.svg)](https://pypi.org/project/posentinel/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Analisador de Qualidade de Tradução para Odoo** — Proteja as traduções do seu Odoo antes que cheguem à produção.

---

## Visão Geral

O PoSentinel é um linter determinístico e motor de qualidade projetado para inspecionar arquivos de localização `.po`, com suporte de primeira classe para módulos e termos do Odoo (especialmente `pt_BR` e configurações multilíngues).

Ele captura problemas críticos de tradução em tempo de execução, como formatadores e variáveis Python (`%s`, `%(name)s`) ausentes ou alterados, tags HTML/XML quebradas, traduções vazias e entradas `fuzzy` não revisadas. Além disso, conta com um Assistente de Inteligência Artificial para sugerir correções automaticamente.

## Começo Rápido

### Instalação

```bash
pip install posentinel
```

### Uso Básico

Analisar um único arquivo `.po`:

```bash
posentinel scan caminho/para/pt_BR.po
```

Analisar um diretório inteiro ou estrutura de módulos Odoo:

```bash
posentinel scan ./addons/meu_modulo/i18n
```

Exportar problemas em formato JSON (ideal para integrações de CI/CD):

```bash
posentinel scan pt_BR.po --format json
```

## Códigos de Saída (Exit Codes) para CI/CD

- `0`: Validação concluída com sucesso sem problemas impeditivos.
- `1`: Problemas de validação detectados (erros encontrados).
- `2`: Erro de tempo de execução, argumentos inválidos ou falha de configuração.

## Autenticação e Assistente de Tradução por IA (v0.6)

O PoSentinel suporta opcionalmente um assistente de tradução e correção usando a API do Claude (Anthropic).

**Para configurar a autenticação:**
A maneira recomendada é exportar a variável de ambiente `ANTHROPIC_API_KEY`:
```bash
export ANTHROPIC_API_KEY="sk-..."
```
Alternativamente, se você usar a CLI da Anthropic, faça o login via terminal com `ant auth login`.

**Uso:**
- Com a chave de API presente, o assistente sugerirá correções para os problemas detectados e pedirá confirmação interativa.
- Para aceitar tudo automaticamente: `--auto-translate`
- Para desativar a IA e rodar estritamente como um linter local: `--no-translation`

Exemplo de configuração via arquivo `posentinel.toml`:
```toml
[ai]
enabled = true
auto_translate = false
model = "claude-3-5-sonnet-20240620"
```

## Licença

Licença MIT. Consulte o arquivo [LICENSE](LICENSE) para obter detalhes.
