"""Testes da regra PO005 (posentinel.rules.syntax)."""

from posentinel.models import OdooMetadata, Severity, TranslationEntry
from posentinel.rules.syntax import InvalidMarkupRule


class TestInvalidMarkupRule:
    def test_does_not_flag_when_tags_preserved_and_balanced(self) -> None:
        rule = InvalidMarkupRule()
        entry = TranslationEntry(
            msgid="Click <a>here</a> to continue", msgstr="Clique <a>aqui</a> para continuar"
        )

        assert rule.check(entry) == []

    def test_flags_missing_tag(self) -> None:
        rule = InvalidMarkupRule()
        entry = TranslationEntry(
            msgid="Click <a>here</a> to continue", msgstr="Clique aqui para continuar"
        )

        issues = rule.check(entry)

        assert len(issues) == 1
        assert issues[0].code == "PO005"
        assert issues[0].severity == Severity.WARNING
        assert "<a>" in issues[0].message

    def test_flags_unbalanced_tags(self) -> None:
        rule = InvalidMarkupRule()
        entry = TranslationEntry(
            msgid="Click <a>here</a> to continue", msgstr="Clique <a>aqui para continuar"
        )

        issues = rule.check(entry)

        assert len(issues) == 1
        assert "desequilibrada" in issues[0].message

    def test_flags_both_missing_and_unbalanced_as_separate_issues(self) -> None:
        rule = InvalidMarkupRule()
        entry = TranslationEntry(
            msgid="<b>Bold</b> and <i>italic</i>", msgstr="<b>Negrito e itálico"
        )

        issues = rule.check(entry)

        assert len(issues) == 2
        messages = " ".join(issue.message for issue in issues)
        assert "<i>" in messages
        assert "desequilibrada" in messages

    def test_flags_closing_tag_without_matching_opening(self) -> None:
        rule = InvalidMarkupRule()
        entry = TranslationEntry(msgid="<a>here</a>", msgstr="aqui</a>")

        issues = rule.check(entry)

        assert len(issues) == 1
        assert "desequilibrada" in issues[0].message

    def test_self_closing_tag_is_not_flagged_as_unbalanced(self) -> None:
        rule = InvalidMarkupRule()
        entry = TranslationEntry(msgid="Line<br/>break", msgstr="Linha<br/>quebrada")

        assert rule.check(entry) == []

    def test_does_not_flag_entries_without_tags(self) -> None:
        rule = InvalidMarkupRule()
        entry = TranslationEntry(msgid="Hello", msgstr="Olá")

        assert rule.check(entry) == []

    def test_ignores_header_entry(self) -> None:
        rule = InvalidMarkupRule()
        entry = TranslationEntry(msgid="", msgstr="")

        assert rule.check(entry) == []

    def test_checks_each_plural_form_independently(self) -> None:
        rule = InvalidMarkupRule()
        entry = TranslationEntry(
            msgid="<b>%(count)d item</b>",
            msgid_plural="<b>%(count)d items</b>",
            msgstr_plural={0: "<b>%(count)d item</b>", 1: "%(count)d itens"},
        )

        issues = rule.check(entry)

        assert len(issues) == 1
        assert "<b>" in issues[0].message

    def test_odoo_context_is_copied_from_entry(self) -> None:
        rule = InvalidMarkupRule()
        entry = TranslationEntry(
            msgid="<a>Link</a>",
            msgstr="Link",
            odoo_metadata=OdooMetadata(module="sale"),
        )

        issues = rule.check(entry)

        assert issues[0].odoo_context == "sale"

    def test_does_not_flag_empty_translation(self) -> None:
        rule = InvalidMarkupRule()
        entry = TranslationEntry(msgid="<a>Link</a>", msgstr="")

        assert rule.check(entry) == []
