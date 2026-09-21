"""Motor de execução das regras de validação."""

from posentinel.models import Issue, Severity, TranslationEntry
from posentinel.rules.base import BaseRule


class RulesEngine:
    """Executa uma coleção de regras sobre uma entrada, isolando falhas individuais."""

    def __init__(self, rules: list[BaseRule]) -> None:
        self._rules = rules

    def analyze(self, entry: TranslationEntry) -> list[Issue]:
        issues: list[Issue] = []
        for rule in self._rules:
            try:
                issues.extend(rule.check(entry))
            except Exception as error:
                issues.append(
                    Issue(
                        code="SYS001",
                        message=f"Falha ao executar a regra {rule.code}: {error}",
                        severity=Severity.ERROR,
                        line=entry.line,
                        msgid=entry.msgid,
                    )
                )
        return issues
