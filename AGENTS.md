# Instruções para Agentes de IA (PoSentinel)

## Contexto do Projeto
O **PoSentinel** é um projeto independente de linter e ferramenta de qualidade para arquivos de internacionalização `.po` (com foco especial em ecossistemas Odoo e localizações `pt_BR`).

## Regras Específicas
- **Independência de Ecossistema**: Este projeto **NÃO** pertence ao ecossistema da Gotryx. Não carregue, não aplique e não faça referência a regras, convenções, skills ou MCPs específicos da Gotryx (`gotryx-project`, RabbitMQ Gotryx, Grafana Gotryx, módulos `gt_*`, etc.).
- **Comunicação**: Sempre responda e entregue as respostas em português do Brasil (`pt-BR`).
- **Arquitetura**: Siga os padrões estabelecidos na documentação interna em `docs/` e na especificação técnica do Core.
- **Skill obrigatória**: Antes de iniciar qualquer tarefa de desenvolvimento, implementação, revisão de código ou análise técnica neste repositório, carregue e leia a skill `posentinel-spec` localizada em `.agents/skills/posentinel-spec/SKILL.md`. Ela é a fonte de verdade do contexto técnico do projeto.
- **Gestão de tarefas no Jira**: As tarefas do projeto são gerenciadas no Jira, projeto **"PoSentinel Tarefas"** (key `PST`), no site `mygotryx.atlassian.net`. Use o MCP `atlassian-gotryx` para consultar, criar ou atualizar issues desse projeto (épicos, histórias, bugs, tarefas e subtarefas) — não use o MCP `atlassian` genérico nem assuma outro projeto Jira para o PoSentinel.

