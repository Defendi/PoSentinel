"""Testes do motor de regras (posentinel.rules.base e posentinel.rules.engine)."""

import pytest

from posentinel.models import Issue, Severity, TranslationEntry
from posentinel.rules.base import BaseRule
from posentinel.rules.engine import RulesEngine


class _AlwaysFlagsRule(BaseRule):
    code = "T001"
    description = "Sempre gera uma issue de teste"
    default_severity = Severity.INFO

    def check(self, entry: TranslationEntry) -> list[Issue]:
        return [
            Issue(
                code=self.code,
                message="issue de teste",
                severity=self.default_severity,
                line=entry.line,
                msgid=entry.msgid,
            )
        ]


class _NeverFlagsRule(BaseRule):
    code = "T002"
    description = "Nunca gera issues"
    default_severity = Severity.INFO

    def check(self, _entry: TranslationEntry) -> list[Issue]:
        return []


class _BrokenRule(BaseRule):
    code = "T003"
    description = "Sempre levanta exceção"
    default_severity = Severity.ERROR

    def check(self, _entry: TranslationEntry) -> list[Issue]:
        raise RuntimeError("falha proposital da regra")


class TestBaseRule:
    def test_cannot_instantiate_directly(self) -> None:
        with pytest.raises(TypeError):
            BaseRule()  # type: ignore[abstract]


class TestRulesEngine:
    def test_aggregates_issues_from_multiple_rules(self) -> None:
        engine = RulesEngine([_AlwaysFlagsRule(), _NeverFlagsRule()])
        entry = TranslationEntry(msgid="Hello", msgstr="Olá")

        issues = engine.analyze(entry)

        assert len(issues) == 1
        assert issues[0].code == "T001"

    def test_isolates_exception_from_single_rule_as_sys001(self) -> None:
        engine = RulesEngine([_BrokenRule(), _AlwaysFlagsRule()])
        entry = TranslationEntry(msgid="Hello", msgstr="Olá")

        issues = engine.analyze(entry)

        codes = [issue.code for issue in issues]
        assert "SYS001" in codes
        assert "T001" in codes
        sys_issue = next(issue for issue in issues if issue.code == "SYS001")
        assert sys_issue.severity == Severity.ERROR
        assert "T003" in sys_issue.message

    def test_empty_rules_list_returns_no_issues(self) -> None:
        engine = RulesEngine([])
        entry = TranslationEntry(msgid="Hello", msgstr="Olá")

        assert engine.analyze(entry) == []
