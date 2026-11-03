"""Motor de execução das regras de validação."""

import re

from posentinel.models import Issue, Severity, TranslationEntry
from posentinel.rules.base import BaseRule

_IGNORE_PATTERN = re.compile(r"posentinel:\s*ignore\s+([a-zA-Z0-9_,\s]+)", re.IGNORECASE)


class RulesEngine:
    """Executa uma coleção de regras sobre uma entrada, isolando falhas individuais."""

    def __init__(
        self, rules: list[BaseRule], ignore_rules: set[str] | list[str] | None = None
    ) -> None:
        self._rules = rules
        self._ignore_rules = {code.upper() for code in (ignore_rules or [])}

    def _get_ignored_codes_from_entry(self, entry: TranslationEntry) -> set[str]:
        ignored = set(self._ignore_rules)
        for comment in entry.comments:
            match = _IGNORE_PATTERN.search(comment)
            if match:
                codes = [c.strip().upper() for c in match.group(1).split(",") if c.strip()]
                ignored.update(codes)
        return ignored

    def analyze(self, entry: TranslationEntry) -> list[Issue]:
        ignored_codes = self._get_ignored_codes_from_entry(entry)
        issues: list[Issue] = []
        for rule in self._rules:
            if rule.code.upper() in ignored_codes:
                continue
            try:
                found_issues = rule.check(entry)
                for issue in found_issues:
                    if issue.code.upper() not in ignored_codes:
                        issues.append(issue)
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
