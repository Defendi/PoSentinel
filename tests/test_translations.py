from posentinel.models.entry import Severity, TranslationEntry
from posentinel.rules.syntax import InvalidMarkupRule
from posentinel.rules.translations import EmptyTranslationRule


def test_empty_translation_rule() -> None:
    rule = EmptyTranslationRule()
    entry_empty = TranslationEntry(msgid="Save", msgstr="")
    issues = rule.check(entry_empty)
    assert len(issues) == 1
    assert issues[0].code == "PO001"
    assert issues[0].severity == Severity.WARNING

    entry_header = TranslationEntry(msgid="", msgstr="Project-Id-Version: 1.0")
    assert rule.check(entry_header) == []


def test_invalid_markup_rule() -> None:
    rule = InvalidMarkupRule()
    entry = TranslationEntry(
        msgid='Click <a href="#">here</a> to learn more.',
        msgstr="Clique aqui para saber mais.",
    )
    issues = rule.check(entry)
    assert len(issues) == 1
    assert issues[0].code == "PO005"
    assert issues[0].severity == Severity.WARNING
    assert "<a>" in issues[0].message
