"""Testes da regra PO006 (posentinel.rules.fuzzy)."""

from posentinel.models import OdooMetadata, Severity, TranslationEntry
from posentinel.rules.fuzzy import FuzzyTranslationRule


class TestFuzzyTranslationRule:
    def test_flags_fuzzy_entry(self) -> None:
        rule = FuzzyTranslationRule()
        entry = TranslationEntry(msgid="Total", msgstr="Totale", flags=("fuzzy",), is_fuzzy=True)

        issues = rule.check(entry)

        assert len(issues) == 1
        assert issues[0].code == "PO006"
        assert issues[0].severity == Severity.WARNING

    def test_does_not_flag_non_fuzzy_entry(self) -> None:
        rule = FuzzyTranslationRule()
        entry = TranslationEntry(msgid="Hello", msgstr="Olá", is_fuzzy=False)

        assert rule.check(entry) == []

    def test_ignores_header_entry_even_if_fuzzy(self) -> None:
        rule = FuzzyTranslationRule()
        entry = TranslationEntry(msgid="", msgstr="", is_fuzzy=True)

        assert rule.check(entry) == []

    def test_odoo_context_is_copied_from_entry(self) -> None:
        rule = FuzzyTranslationRule()
        entry = TranslationEntry(
            msgid="Total",
            msgstr="Totale",
            is_fuzzy=True,
            odoo_metadata=OdooMetadata(module="sale"),
        )

        issues = rule.check(entry)

        assert issues[0].odoo_context == "sale"

    def test_flags_fuzzy_entry_regardless_of_plural(self) -> None:
        rule = FuzzyTranslationRule()
        entry = TranslationEntry(
            msgid="%(count)d item",
            msgid_plural="%(count)d items",
            msgstr_plural={0: "%(count)d item", 1: "%(count)d itens"},
            is_fuzzy=True,
        )

        issues = rule.check(entry)

        assert len(issues) == 1
