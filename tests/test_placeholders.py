from posentinel.models.entry import Severity, TranslationEntry
from posentinel.rules.placeholders import (
    ExtraPlaceholderRule,
    InvalidPlaceholderRule,
    MissingPlaceholderRule,
)


def test_missing_placeholder_rule() -> None:
    rule = MissingPlaceholderRule()
    entry = TranslationEntry(
        msgid="Hello %s, total is %d",
        msgstr="Olá %s, total é",
    )
    issues = rule.check(entry)
    assert len(issues) == 1
    assert issues[0].code == "PO002"
    assert issues[0].severity == Severity.ERROR
    assert "%d" in issues[0].message


def test_invalid_placeholder_rule() -> None:
    rule = InvalidPlaceholderRule()
    entry = TranslationEntry(
        msgid="Hello %(username)s!",
        msgstr="Olá %(nome_usuario)s!",
    )
    issues = rule.check(entry)
    assert len(issues) == 1
    assert issues[0].code == "PO003"
    assert issues[0].severity == Severity.ERROR
    assert "%(nome_usuario)s" in issues[0].message


def test_extra_placeholder_rule() -> None:
    rule = ExtraPlaceholderRule()
    entry = TranslationEntry(
        msgid="Simple text with %s",
        msgstr="Texto simples com %s e mais %s",
    )
    issues = rule.check(entry)
    assert len(issues) == 1
    assert issues[0].code == "PO004"
    assert issues[0].severity == Severity.ERROR
