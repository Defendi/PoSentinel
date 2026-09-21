from posentinel.models.entry import TranslationEntry
from posentinel.models.issue import Issue
from posentinel.rules.base import BaseRule


class RulesEngine:
    """Orquestrador e executor do conjunto de regras ativas."""

    def __init__(self, rules: list[BaseRule] | None = None) -> None:
        self.rules: list[BaseRule] = rules if rules is not None else []

    def register(self, rule: BaseRule) -> None:
        self.rules.append(rule)

    def execute_all(self, entries: list[TranslationEntry]) -> list[Issue]:
        issues: list[Issue] = []
        for entry in entries:
            for rule in self.rules:
                try:
                    rule_issues = rule.check(entry)
                    if rule_issues:
                        issues.extend(rule_issues)
                except Exception as exc:  # noqa: BLE001
                    # Falhas em regras individuais não interrompem o linter
                    from posentinel.models.entry import Severity

                    issues.append(
                        Issue(
                            code="SYS001",
                            message=f"Erro interno na execução da regra {rule.code}: {exc}",
                            severity=Severity.ERROR,
                            line=entry.line,
                            msgid=entry.msgid,
                            entry=entry,
                        )
                    )
        return issues
