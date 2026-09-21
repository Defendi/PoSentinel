# PoSentinel

**Odoo Translation Quality Analyzer**

PoSentinel é uma ferramenta Python para análise de qualidade de arquivos
de internacionalização `.po`, inicialmente com foco em traduções do Odoo
para `pt_BR`.

A proposta é começar como um **linter determinístico**, confiável e
simples de integrar a CI/CD, evoluindo posteriormente para análise
semântica assistida por IA.

------------------------------------------------------------------------

## 1. Objetivos

### Objetivo principal

Detectar problemas em arquivos `.po` antes que cheguem ao ambiente de
produção.

### Problemas que o PoSentinel deverá identificar

-   Sintaxe inválida de arquivos PO
-   Traduções vazias
-   Placeholders ausentes
-   Placeholders alterados
-   Placeholders extras
-   Problemas em HTML/XML embutido
-   Traduções inconsistentes
-   Entradas `fuzzy`
-   Referências Odoo inválidas ou suspeitas
-   Problemas relacionados ao contexto de tradução
-   Termos técnicos inconsistentes
-   Problemas de encoding
-   Strings duplicadas ou potencialmente conflitantes

### Evolução futura

O projeto poderá evoluir para um **Translation Quality Engine**,
suportando futuramente outros formatos de internacionalização, como:

-   `.po`
-   `.json`
-   `.yaml`
-   `.xlf`
-   `.xliff`

O primeiro e principal adapter será o parser de `.po` para Odoo.

------------------------------------------------------------------------

# 2. Princípios do projeto

## 2.1 CLI-first

A interface principal será uma CLI:

``` bash
posentinel scan pt_BR.po
```

## 2.2 Core independente

As regras não deverão depender diretamente da biblioteca usada para ler
`.po`.

O parser transforma o arquivo em modelos internos do PoSentinel.

``` text
.po
 |
 v
PoParser
 |
 v
TranslationEntry
 |
 v
Rules Engine
 |
 v
Issues
 |
 v
Reporter
```

## 2.3 Regras determinísticas primeiro

O MVP não dependerá de IA.

Regras sintáticas e estruturais deverão ser determinísticas,
reproduzíveis e adequadas para execução em CI/CD.

A análise semântica por IA será adicionada posteriormente como recurso
opcional.

## 2.4 Extensibilidade

O sistema de regras deverá ser baseado em plugins/classes, evitando um
grande bloco de `if/elif`.

## 2.5 CI/CD ready

O resultado da análise deverá poder ser consumido por:

-   GitHub Actions
-   GitLab CI
-   Azure DevOps
-   Jenkins
-   pre-commit
-   outras ferramentas de automação

------------------------------------------------------------------------

# 3. Stack

## Runtime

-   Python 3.12+
-   Compatibilidade futura com versões suportadas do Python

## Dependências principais

### Parser PO

``` text
polib
```

### CLI

``` text
typer
rich
```

### Testes

``` text
pytest
pytest-cov
```

### Qualidade de código

``` text
ruff
mypy
pre-commit
```

### Build e publicação

``` text
build
twine
```

------------------------------------------------------------------------

# 4. Estrutura do projeto

``` text
posentinel/
├── pyproject.toml
├── README.md
├── LICENSE
├── CHANGELOG.md
├── CONTRIBUTING.md
├── .gitignore
├── .pre-commit-config.yaml
│
├── src/
│   └── posentinel/
│       ├── __init__.py
│       ├── __main__.py
│       │
│       ├── cli/
│       │   ├── __init__.py
│       │   └── commands.py
│       │
│       ├── parser/
│       │   ├── __init__.py
│       │   └── po_parser.py
│       │
│       ├── models/
│       │   ├── __init__.py
│       │   ├── entry.py
│       │   ├── issue.py
│       │   └── result.py
│       │
│       ├── rules/
│       │   ├── __init__.py
│       │   ├── base.py
│       │   ├── syntax.py
│       │   ├── placeholders.py
│       │   ├── translations.py
│       │   ├── odoo.py
│       │   └── consistency.py
│       │
│       ├── analyzers/
│       │   ├── __init__.py
│       │   ├── analyzer.py
│       │   └── similarity.py
│       │
│       ├── reporters/
│       │   ├── __init__.py
│       │   ├── console.py
│       │   ├── json.py
│       │   └── github.py
│       │
│       └── config/
│           ├── __init__.py
│           └── loader.py
│
├── tests/
│   ├── fixtures/
│   │   ├── valid.po
│   │   ├── invalid.po
│   │   └── odoo_pt_br.po
│   │
│   ├── test_parser.py
│   ├── test_placeholders.py
│   ├── test_translations.py
│   ├── test_odoo.py
│   └── test_cli.py
│
└── docs/
    ├── rules.md
    ├── configuration.md
    └── ci.md
```

------------------------------------------------------------------------

# 5. Modelo de dados

As regras não devem manipular diretamente objetos `polib`.

O parser deverá converter os dados para modelos próprios.

Exemplo:

``` python
from dataclasses import dataclass


@dataclass
class TranslationEntry:
    msgid: str
    msgstr: str
    msgctxt: str | None
    comments: list[str]
    references: list[str]
    flags: list[str]
    line: int | None
```

O modelo deverá ser expandido conforme surgirem necessidades específicas
do Odoo.

------------------------------------------------------------------------

# 6. Issue

Toda ocorrência encontrada pelo analisador deverá ser representada por
uma estrutura comum.

Exemplo conceitual:

``` python
@dataclass
class Issue:
    code: str
    severity: str
    message: str
    line: int | None
    msgid: str | None
    rule: str | None
```

Severidades iniciais:

``` text
INFO
WARNING
ERROR
```

------------------------------------------------------------------------

# 7. Rules Engine

O Rules Engine será o núcleo do PoSentinel.

Interface conceitual:

``` python
class Rule(ABC):

    code: str
    description: str
    severity: Severity

    @abstractmethod
    def check(self, entry, context) -> list[Issue]:
        ...
```

Cada regra deverá ser independente.

Exemplo:

``` text
PO001  Empty translation
PO002  Missing placeholder
PO003  Invalid placeholder
PO004  Extra placeholder
PO005  Invalid markup
PO006  Translation inconsistency
```

Regras específicas de Odoo deverão utilizar o prefixo:

``` text
ODOO001
ODOO002
ODOO003
```

------------------------------------------------------------------------

# 8. Regras do MVP

## PO001 --- Empty Translation

Detectar:

``` po
msgid "Customer"
msgstr ""
```

Resultado:

``` text
PO001 WARNING
Translation is empty
line: 1234
msgid: "Customer"
```

------------------------------------------------------------------------

## PO002 --- Missing Placeholder

Original:

``` text
Hello %s
```

Tradução:

``` text
Olá
```

Resultado:

``` text
PO002 ERROR
Placeholder '%s' is missing from translation
```

------------------------------------------------------------------------

## PO003 --- Invalid Placeholder

Original:

``` text
%(name)s
```

Tradução inválida:

``` text
%(nome)s
```

O placeholder deverá ser considerado incompatível com o original.

------------------------------------------------------------------------

## PO004 --- Extra Placeholder

Original:

``` text
Invoice %s
```

Tradução:

``` text
Fatura %s %s
```

Resultado:

``` text
PO004 ERROR
Translation contains an extra placeholder
```

------------------------------------------------------------------------

## PO005 --- Invalid Markup

Exemplo:

``` html
Click <a href="%s">here</a>
```

A tradução deverá preservar a estrutura necessária do markup.

------------------------------------------------------------------------

## PO006 --- Translation Inconsistency

Exemplo:

``` text
Customer -> Cliente
Customer -> Consumidor
Customer -> Cliente
```

Resultado:

``` text
PO006 WARNING

The term "Customer" has multiple translations:

Cliente
Consumidor
```

------------------------------------------------------------------------

# 9. Regras específicas do Odoo

O PoSentinel deverá entender informações presentes nas referências dos
arquivos de tradução do Odoo.

Exemplo:

``` po
#. module: sale
#: model:ir.model.fields,field_description:sale.field_x
msgid "..."
msgstr "..."
```

Possíveis informações analisadas:

-   módulo
-   modelo
-   campo
-   view
-   referência
-   contexto
-   comentários
-   placeholders
-   termos técnicos
-   entradas fuzzy
-   strings duplicadas
-   strings não traduzíveis

As regras específicas do Odoo deverão ser separadas das regras genéricas
de PO.

------------------------------------------------------------------------

# 10. CLI

A CLI deverá ser implementada com Typer.

## Comando principal

``` bash
posentinel scan pt_BR.po
```

Exemplo de saída:

``` text
PoSentinel 0.1.0

Scanning: pt_BR.po
Locale:   pt_BR
Entries:  12,483

✓ Syntax ..................... OK
✓ Encoding ................... OK
✓ Placeholders ............... OK
✓ Odoo references ............ OK

⚠ Missing translations ....... 23
⚠ Inconsistent translations . 17
✗ Invalid placeholders ...... 2

Result: FAILED

2 errors
40 warnings
```

------------------------------------------------------------------------

# 11. Comandos

A CLI deverá disponibilizar inicialmente:

``` bash
posentinel --help
```

``` text
Commands:

  scan       Analyze PO files
  check      Validate PO files
  report     Generate analysis report
  rules      List available rules
  version    Show version
```

## Scan

``` bash
posentinel scan pt_BR.po
```

## Scan de diretório

``` bash
posentinel scan .
```

## Listar regras

``` bash
posentinel rules
```

------------------------------------------------------------------------

# 12. Configuração

A configuração deverá utilizar TOML.

Arquivo:

``` text
posentinel.toml
```

Exemplo:

``` toml
[project]
locale = "pt_BR"

[scan]
fail_on = "error"

[rules]
PO001 = "warning"
PO002 = "error"
PO003 = "error"
PO004 = "error"
PO005 = "warning"

[odoo]
enabled = true

[report]
format = "console"
```

Isso permitirá:

``` bash
posentinel scan .
```

sem precisar informar todas as opções pela linha de comando.

------------------------------------------------------------------------

# 13. Exit Codes

A CLI deverá retornar códigos de saída adequados para CI/CD.

Sugestão:

``` text
0 = Nenhum problema bloqueante
1 = Foram encontrados erros
2 = Erro de execução/configuração
```

Exemplo:

``` bash
posentinel scan pt_BR.po

echo $?
```

O comportamento deverá ser documentado e mantido estável a partir da
versão 1.0.

------------------------------------------------------------------------

# 14. JSON Reporter

O resultado também deverá poder ser exportado em JSON:

``` bash
posentinel scan pt_BR.po --format json
```

Exemplo:

``` json
{
  "file": "pt_BR.po",
  "locale": "pt_BR",
  "entries": 12483,
  "issues": [
    {
      "code": "PO002",
      "severity": "error",
      "line": 1234,
      "message": "Missing placeholder '%s'"
    }
  ]
}
```

Esse formato deverá ser estável e adequado para integração com outras
ferramentas.

------------------------------------------------------------------------

# 15. GitHub Actions

O projeto deverá fornecer exemplos de CI/CD.

Exemplo:

``` yaml
name: PoSentinel

on:
  pull_request:

jobs:
  translation:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Install PoSentinel
        run: pip install posentinel

      - name: Validate translations
        run: posentinel scan ./i18n/pt_BR.po
```

------------------------------------------------------------------------

# 16. GitLab CI

Também deverá existir documentação para:

``` yaml
translation-quality:
  image: python:3.12

  script:
    - pip install posentinel
    - posentinel scan ./i18n/pt_BR.po
```

------------------------------------------------------------------------

# 17. Azure DevOps

Exemplo conceitual:

``` yaml
- script: |
    pip install posentinel
    posentinel scan ./i18n/pt_BR.po
  displayName: Validate translations
```

------------------------------------------------------------------------

# 18. Pre-commit

O projeto deverá fornecer uma configuração para execução local antes do
commit.

Exemplo:

``` yaml
repos:
  - repo: local
    hooks:
      - id: posentinel
        name: PoSentinel
        entry: posentinel scan
        language: system
        files: \.po$
```

Assim:

``` bash
git commit
```

poderá validar automaticamente os arquivos `.po`.

------------------------------------------------------------------------

# 19. Arquitetura

Arquitetura inicial:

``` text
                  ┌──────────────┐
                  │     CLI      │
                  └──────┬───────┘
                         │
                         ▼
                  ┌──────────────┐
                  │   Analyzer   │
                  └──────┬───────┘
                         │
                         ▼
                  ┌──────────────┐
                  │    Parser    │
                  └──────┬───────┘
                         │
                         ▼
                TranslationEntry
                         │
                         ▼
                  ┌──────────────┐
                  │ Rules Engine │
                  └──────┬───────┘
                         │
                         ▼
                      Issues
                         │
              ┌──────────┼──────────┐
              ▼          ▼          ▼
           Console      JSON      GitHub
```

------------------------------------------------------------------------

# 20. Arquitetura futura para múltiplos formatos

O `.po` será o primeiro formato suportado.

Arquitetura planejada:

``` text
                  Analyzer
                     │
          ┌──────────┼──────────┐
          ▼          ▼          ▼
       PoParser   XliffParser  JsonParser
          │          │          │
          └──────────┼──────────┘
                     ▼
             TranslationEntry
                     │
                     ▼
               Rules Engine
```

Dessa forma, as regras de qualidade não precisam conhecer detalhes de
cada formato.

------------------------------------------------------------------------

# 21. Análise semântica

A análise semântica deverá ser adicionada somente após o núcleo
determinístico estar consolidado.

Exemplo:

Original:

``` text
Create Customer
```

Tradução:

``` text
Excluir Cliente
```

Sintaticamente a entrada pode estar correta, mas semanticamente está
incorreta.

Esse tipo de análise poderá utilizar IA.

Arquitetura:

``` text
             ┌──────────────┐
.po ────────►│ Deterministic│
             │ Rules Engine │
             └──────┬───────┘
                    │
                    ▼
             ┌──────────────┐
             │  Semantic    │
             │  Analyzer    │
             └──────┬───────┘
                    │
                    ▼
                  Report
```

A IA deverá inicialmente apenas:

1.  detectar
2.  explicar
3.  sugerir

A alteração automática do arquivo deverá ser uma etapa posterior.

------------------------------------------------------------------------

# 22. Pacote opcional de IA

A análise por IA poderá ser disponibilizada separadamente.

Possibilidades:

``` bash
pip install posentinel[ai]
```

ou:

``` bash
pip install posentinel-ai
```

Uso:

``` bash
posentinel scan pt_BR.po --semantic
```

Possíveis análises:

-   tradução semanticamente incorreta
-   tradução literal inadequada
-   inconsistência terminológica
-   contexto Odoo
-   singular/plural
-   gênero
-   falsos cognatos
-   tradução de termos técnicos

------------------------------------------------------------------------

# 23. Auto Fix

O recurso de correção automática não deverá fazer parte do MVP.

Evolução planejada:

``` bash
posentinel scan pt_BR.po
```

Depois:

``` bash
posentinel fix pt_BR.po
```

E futuramente:

``` bash
posentinel fix pt_BR.po --interactive
```

Toda alteração automática deverá ser:

-   explícita
-   auditável
-   reversível
-   opcional

------------------------------------------------------------------------

# 24. Testes

O projeto deverá ter cobertura automatizada desde o início.

Estrutura:

``` text
tests/
├── fixtures/
│   ├── valid.po
│   ├── invalid.po
│   └── odoo_pt_br.po
│
├── test_parser.py
├── test_placeholders.py
├── test_translations.py
├── test_odoo.py
└── test_cli.py
```

Comando:

``` bash
pytest
```

Com cobertura:

``` bash
pytest --cov=posentinel
```

------------------------------------------------------------------------

# 25. Qualidade de código

O projeto deverá utilizar:

``` bash
ruff check .
ruff format .
mypy src/
```

E recomenda-se `pre-commit` para executar validações automaticamente.

------------------------------------------------------------------------

# 26. Packaging

O projeto deverá usar `pyproject.toml`.

Nome do pacote:

``` text
posentinel
```

Nome da CLI:

``` text
posentinel
```

Namespace Python:

``` python
import posentinel
```

Nome do repositório:

``` text
posentinel
```

Nome comercial:

``` text
PoSentinel
```

Essa padronização deverá ser mantida em todo o ecossistema.

------------------------------------------------------------------------

# 27. Publicação no PyPI

Build:

``` bash
python -m build
```

Resultado esperado:

``` text
dist/
├── posentinel-x.y.z-py3-none-any.whl
└── posentinel-x.y.z.tar.gz
```

Teste do pacote:

``` bash
python -m twine check dist/*
```

Publicação:

``` bash
python -m twine upload dist/*
```

------------------------------------------------------------------------

# 28. Versionamento

Utilizar Semantic Versioning:

``` text
MAJOR.MINOR.PATCH
```

Exemplos:

``` text
0.1.0
0.2.0
0.3.0
1.0.0
```

Durante o desenvolvimento:

``` text
0.x
```

A API pública deverá ser considerada estável a partir de:

``` text
1.0.0
```

------------------------------------------------------------------------

# 29. Roadmap

## v0.1 --- Core

-   [ ] Estrutura inicial Python 3.12+
-   [ ] `pyproject.toml`
-   [ ] Parser `.po`
-   [ ] Modelos internos
-   [ ] CLI
-   [ ] PO001
-   [ ] PO002
-   [ ] PO003
-   [ ] PO004
-   [ ] PO005
-   [ ] Console reporter
-   [ ] Testes automatizados

## v0.2 --- Rules Engine

-   [ ] Sistema de regras extensível
-   [ ] Severidades
-   [ ] Configuração TOML
-   [ ] PO006
-   [ ] Regras de encoding
-   [ ] Regras de fuzzy
-   [ ] JSON reporter
-   [ ] Exit codes

## v0.3 --- Odoo

-   [ ] Parser/contexto Odoo
-   [ ] Regras Odoo
-   [ ] Validação de referências
-   [ ] Análise de módulos
-   [ ] Análise de modelos/campos
-   [ ] Regras específicas para `pt_BR`

## v0.4 --- CI/CD

-   [ ] GitHub Actions
-   [ ] GitLab CI
-   [ ] Azure DevOps
-   [ ] Jenkins
-   [ ] pre-commit
-   [ ] Documentação de integração

## v0.5 --- Consistência

-   [ ] Glossário
-   [ ] Análise de termos
-   [ ] Detecção de traduções inconsistentes
-   [ ] Similaridade textual
-   [ ] Relatórios avançados

## v0.6 --- IA

-   [ ] Interface para provedores de IA
-   [ ] Análise semântica
-   [ ] Sugestões de tradução
-   [ ] Explicação dos problemas
-   [ ] IA opcional

## v0.7 --- Auto Fix

-   [ ] Correções automáticas simples
-   [ ] Modo interativo
-   [ ] Preview das alterações
-   [ ] Backup/reversão
-   [ ] Auditoria das alterações

## v1.0 --- Stable

-   [ ] API estável
-   [ ] CLI estável
-   [ ] Documentação completa
-   [ ] PyPI
-   [ ] CI/CD
-   [ ] Plugin architecture
-   [ ] Compatibilidade documentada
-   [ ] Política de versionamento

------------------------------------------------------------------------

# 30. Identidade do projeto

## Nome

**PoSentinel**

## Nome técnico

``` text
posentinel
```

## Tagline

**Odoo Translation Quality Analyzer**

Alternativa:

**Protect your Odoo translations.**

## Conceito visual

A identidade visual deverá combinar:

-   escudo
-   tradução
-   código
-   qualidade
-   precisão

Um conceito possível:

``` text
       ┌─────────┐
       │   PO    │
       │    ✓    │
       └─────────┘
          SENTINEL
```

O símbolo deverá funcionar independentemente do nome, permitindo
utilização como:

-   favicon
-   ícone de CLI
-   GitHub
-   PyPI
-   documentação
-   Docker
-   aplicação web futura

------------------------------------------------------------------------

# 31. MVP recomendado

A primeira versão deve ser deliberadamente pequena.

### Entrega do MVP

``` text
Python 3.12+
       │
       ▼
   posentinel
       │
       ├── CLI
       ├── PO parser
       ├── Models
       ├── Rules Engine
       ├── 5 regras básicas
       ├── Console Reporter
       ├── JSON Reporter
       └── pytest
```

Comando mínimo:

``` bash
posentinel scan pt_BR.po
```

Resultado:

``` text
PoSentinel 0.1.0

File: pt_BR.po
Locale: pt_BR
Entries: 12,483

Errors:   2
Warnings: 40

Result: FAILED
```

------------------------------------------------------------------------

# 32. Critérios de sucesso do MVP

O MVP será considerado pronto quando:

-   Um arquivo `.po` válido puder ser analisado pela CLI.
-   Erros de placeholders forem identificados de forma confiável.
-   Traduções vazias forem identificadas.
-   Problemas básicos de markup forem identificados.
-   O resultado tiver linha e mensagem claras.
-   O processo puder falhar corretamente em CI/CD.
-   O resultado puder ser exportado para JSON.
-   As regras puderem ser adicionadas sem alterar o núcleo do
    analisador.
-   O pacote puder ser instalado via `pip`.
-   Os testes automatizados cobrirem o comportamento principal.

------------------------------------------------------------------------

# 33. Visão de longo prazo

A visão do PoSentinel é evoluir de um simples validador `.po` para uma
plataforma de qualidade de internacionalização:

``` text
                 PoSentinel
                     │
       ┌─────────────┼─────────────┐
       ▼             ▼             ▼
   Validation    Consistency   Semantics
       │             │             │
       └─────────────┼─────────────┘
                     ▼
               Quality Engine
                     │
       ┌─────────────┼─────────────┐
       ▼             ▼             ▼
      CLI           CI/CD          API
```

O foco inicial permanece em **Odoo + `pt_BR` + `.po`**, mas a
arquitetura deve permitir que o projeto cresça sem precisar ser
reescrito.

------------------------------------------------------------------------

# 34. Primeiro milestone

O primeiro milestone de desenvolvimento deverá ser:

``` text
PoSentinel 0.1.0
```

Entrega:

``` text
[ ] Git repository
[ ] Python 3.12+
[ ] pyproject.toml
[ ] src layout
[ ] PO parser
[ ] TranslationEntry
[ ] Issue
[ ] Rule base
[ ] PO001
[ ] PO002
[ ] PO003
[ ] PO004
[ ] PO005
[ ] CLI scan
[ ] Console reporter
[ ] JSON reporter
[ ] Exit codes
[ ] Unit tests
[ ] README
[ ] LICENSE
[ ] CHANGELOG
```

Com isso concluído, o projeto já terá uma base sólida para começar a
analisar arquivos reais de tradução do Odoo e evoluir incrementalmente.
