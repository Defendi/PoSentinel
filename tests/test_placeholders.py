"""Testes das regras de placeholders (posentinel.rules.placeholders)."""

from posentinel.models import TranslationEntry
from posentinel.rules.placeholders import (
    ExtraPlaceholderRule,
    InvalidPlaceholderRule,
    MissingPlaceholderRule,
)


class TestMissingPlaceholderRule:
    def test_flags_missing_positional_printf(self) -> None:
        rule = MissingPlaceholderRule()
        entry = TranslationEntry(msgid="Hello %s", msgstr="Olá")

        issues = rule.check(entry)

        assert len(issues) == 1
        assert issues[0].code == "PO002"
        assert "%s" in issues[0].message

    def test_flags_missing_named_printf(self) -> None:
        rule = MissingPlaceholderRule()
        entry = TranslationEntry(msgid="Hello %(name)s", msgstr="Olá")

        issues = rule.check(entry)

        assert len(issues) == 1
        assert "%(name)s" in issues[0].message

    def test_flags_missing_format_style_field(self) -> None:
        rule = MissingPlaceholderRule()
        entry = TranslationEntry(msgid="Hello {name}", msgstr="Olá")

        issues = rule.check(entry)

        assert len(issues) == 1
        assert "{name}" in issues[0].message

    def test_does_not_flag_when_all_placeholders_present(self) -> None:
        rule = MissingPlaceholderRule()
        entry = TranslationEntry(msgid="Hello %(name)s", msgstr="Olá %(name)s")

        assert rule.check(entry) == []

    def test_does_not_flag_when_original_has_no_placeholders(self) -> None:
        rule = MissingPlaceholderRule()
        entry = TranslationEntry(msgid="Hello", msgstr="Olá")

        assert rule.check(entry) == []

    def test_escaped_percent_is_not_a_placeholder(self) -> None:
        rule = MissingPlaceholderRule()
        entry = TranslationEntry(msgid="100%% concluído", msgstr="100%% concluído")

        assert rule.check(entry) == []

    def test_checks_each_plural_form_independently(self) -> None:
        rule = MissingPlaceholderRule()
        entry = TranslationEntry(
            msgid="%(count)d item",
            msgid_plural="%(count)d items",
            msgstr_plural={0: "item", 1: "%(count)d itens"},
        )

        issues = rule.check(entry)

        assert len(issues) == 1
        assert "%(count)d" in issues[0].message

    def test_ignores_header_entry(self) -> None:
        rule = MissingPlaceholderRule()
        entry = TranslationEntry(msgid="", msgstr="")

        assert rule.check(entry) == []

    def test_flags_missing_positional_format_field(self) -> None:
        rule = MissingPlaceholderRule()
        entry = TranslationEntry(msgid="Item {0}: {1}", msgstr="Item {0}")

        issues = rule.check(entry)

        assert len(issues) == 1
        assert "{1}" in issues[0].message

    def test_flags_missing_auto_numbered_format_field(self) -> None:
        rule = MissingPlaceholderRule()
        entry = TranslationEntry(msgid="Total: {}", msgstr="Total")

        issues = rule.check(entry)

        assert len(issues) == 1
        assert "{}" in issues[0].message


class TestInvalidPlaceholderRule:
    def test_does_not_flag_when_original_has_no_placeholders(self) -> None:
        rule = InvalidPlaceholderRule()
        entry = TranslationEntry(msgid="Hello", msgstr="Olá")

        assert rule.check(entry) == []

    def test_flags_translated_named_printf_variable(self) -> None:
        rule = InvalidPlaceholderRule()
        entry = TranslationEntry(msgid="Hello %(partner_name)s", msgstr="Olá %(nome_parceiro)s")

        issues = rule.check(entry)

        assert len(issues) == 1
        assert issues[0].code == "PO003"
        assert issues[0].suggestion == "%(partner_name)s"

    def test_flags_translated_format_style_field(self) -> None:
        rule = InvalidPlaceholderRule()
        entry = TranslationEntry(msgid="Hello {name}", msgstr="Olá {nome}")

        issues = rule.check(entry)

        assert len(issues) == 1
        assert issues[0].suggestion == "{name}"

    def test_does_not_flag_positional_printf_mismatch(self) -> None:
        rule = InvalidPlaceholderRule()
        entry = TranslationEntry(msgid="Hello %s", msgstr="Olá %d")

        assert rule.check(entry) == []

    def test_does_not_flag_when_names_match(self) -> None:
        rule = InvalidPlaceholderRule()
        entry = TranslationEntry(msgid="Hello %(name)s", msgstr="Olá %(name)s")

        assert rule.check(entry) == []

    def test_pairs_multiple_named_substitutions_deterministically(self) -> None:
        rule = InvalidPlaceholderRule()
        entry = TranslationEntry(
            msgid="Hello %(first_name)s and %(last_name)s",
            msgstr="Olá %(nome)s e %(sobrenome)s",
        )

        issues = rule.check(entry)

        assert len(issues) == 2
        suggestions = {issue.suggestion for issue in issues}
        assert suggestions == {"%(first_name)s", "%(last_name)s"}

    def test_ignores_header_entry(self) -> None:
        rule = InvalidPlaceholderRule()
        entry = TranslationEntry(msgid="", msgstr="")

        assert rule.check(entry) == []


class TestExtraPlaceholderRule:
    def test_flags_extra_placeholder_not_in_original(self) -> None:
        rule = ExtraPlaceholderRule()
        entry = TranslationEntry(msgid="Hello", msgstr="Olá %(name)s")

        issues = rule.check(entry)

        assert len(issues) == 1
        assert issues[0].code == "PO004"
        assert "%(name)s" in issues[0].message

    def test_does_not_flag_when_no_extra_placeholders(self) -> None:
        rule = ExtraPlaceholderRule()
        entry = TranslationEntry(msgid="Hello %s", msgstr="Olá %s")

        assert rule.check(entry) == []

    def test_does_not_flag_empty_translation(self) -> None:
        rule = ExtraPlaceholderRule()
        entry = TranslationEntry(msgid="Hello %s", msgstr="")

        assert rule.check(entry) == []

    def test_ignores_header_entry(self) -> None:
        rule = ExtraPlaceholderRule()
        entry = TranslationEntry(msgid="", msgstr="")

        assert rule.check(entry) == []

    def test_skips_empty_plural_form_without_flagging(self) -> None:
        rule = ExtraPlaceholderRule()
        entry = TranslationEntry(
            msgid="%(count)d item",
            msgid_plural="%(count)d items",
            msgstr_plural={0: "", 1: "%(count)d itens extra %(bonus)d"},
        )

        issues = rule.check(entry)

        assert len(issues) == 1
        assert "%(bonus)d" in issues[0].message
