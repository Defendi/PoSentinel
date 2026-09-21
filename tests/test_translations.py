"""Testes da regra PO001 (posentinel.rules.translations)."""

from posentinel.models import OdooMetadata, Severity, TranslationEntry
from posentinel.rules.translations import EmptyTranslationRule


class TestEmptyTranslationRule:
    def test_flags_empty_singular_translation(self) -> None:
        rule = EmptyTranslationRule()
        entry = TranslationEntry(msgid="Hello", msgstr="")

        issues = rule.check(entry)

        assert len(issues) == 1
        assert issues[0].code == "PO001"
        assert issues[0].severity == Severity.WARNING

    def test_does_not_flag_filled_singular_translation(self) -> None:
        rule = EmptyTranslationRule()
        entry = TranslationEntry(msgid="Hello", msgstr="Olá")

        assert rule.check(entry) == []

    def test_ignores_header_entry(self) -> None:
        rule = EmptyTranslationRule()
        entry = TranslationEntry(msgid="", msgstr="")

        assert rule.check(entry) == []

    def test_flags_empty_plural_forms_with_indexes_in_message(self) -> None:
        rule = EmptyTranslationRule()
        entry = TranslationEntry(
            msgid="%(count)d item",
            msgid_plural="%(count)d items",
            msgstr_plural={0: "", 1: "%(count)d itens"},
        )

        issues = rule.check(entry)

        assert len(issues) == 1
        assert "0" in issues[0].message

    def test_does_not_flag_fully_filled_plural_forms(self) -> None:
        rule = EmptyTranslationRule()
        entry = TranslationEntry(
            msgid="%(count)d item",
            msgid_plural="%(count)d items",
            msgstr_plural={0: "%(count)d item", 1: "%(count)d itens"},
        )

        assert rule.check(entry) == []

    def test_flags_all_empty_plural_forms(self) -> None:
        rule = EmptyTranslationRule()
        entry = TranslationEntry(
            msgid="%(count)d item",
            msgid_plural="%(count)d items",
            msgstr_plural={0: "", 1: ""},
        )

        issues = rule.check(entry)

        assert len(issues) == 1
        assert "0" in issues[0].message
        assert "1" in issues[0].message

    def test_odoo_context_is_copied_from_entry(self) -> None:
        rule = EmptyTranslationRule()
        entry = TranslationEntry(
            msgid="Hello", msgstr="", odoo_metadata=OdooMetadata(module="sale")
        )

        issues = rule.check(entry)

        assert issues[0].odoo_context == "sale"
