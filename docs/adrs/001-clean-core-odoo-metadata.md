# ADR 001: Adoção de Clean Core com Modelos Desacoplados e Metadados Odoo

- **Status**: aceito
- **Data**: 2026-09-21
- **Decisores**: Tech Lead, Core Team
- **Contexto Técnico**: [docs/trd.md](../trd.md)

---

## 1. Contexto

O PoSentinel tem como missão ser o analisador de qualidade de traduções definitivo para o ecossistema Odoo. Arquivos `.po` no Odoo contêm comentários estruturados cruciais (`#. module:`, `#: model:...`), flags (`python-format`) e convenções próprias.

No mercado existem bibliotecas como `polib` para ler arquivos PO, mas atrelar as regras de qualidade diretamente aos objetos do `polib`:
1. Vaza detalhes de implementação de bibliotecas de terceiros para dentro do motor de regras.
2. Dificulta a evolução futura para outros formatos de tradução (como XLIFF, JSON, YAML).
3. Complica a criação de fixtures e testes unitários puros.

## 2. Decisão

Adotar uma arquitetura de **Clean Core (Domain-Isolated)**:
1. Definir entidades de domínio imutáveis em `posentinel.models` (`TranslationEntry`, `OdooMetadata`, `Issue`, `ScanSummary`).
2. O `polib` atuará exclusivamente como detalhe de implementação dentro do adaptador `PoParser`.
3. O modelo `TranslationEntry` incluirá nativamente suporte a metadados do Odoo desde o primeiro milestone, mesmo que as regras iniciais foquem em sintaxe e placeholders.
4. As regras de validação herdam de `BaseRule` e interagem unicamente com instâncias de `TranslationEntry`, devolvendo objetos `Issue`.

## 3. Consequências

### Positivas
- **Isolamento e Testabilidade**: Qualquer regra pode ser testada passando instâncias puras de `TranslationEntry`, sem necessidade de arquivos `.po` em disco para cada caso de teste.
- **Pronto para o Futuro**: Suporte a outros parsers (ex: XLIFF) no futuro sem alterar nenhuma regra de negócio.
- **Riqueza de Contexto**: As falhas reportadas já contam com o módulo e modelo Odoo identificados, elevando drasticamente a utilidade para desenvolvedores Odoo.

### Negativas / Trade-offs
- Existe uma etapa intermediária de conversão em memória dos objetos `polib` para `TranslationEntry` (impacto de memória e CPU negligenciável em Python 3.12 com `slots=True`).
