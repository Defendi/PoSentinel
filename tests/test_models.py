"""Testes dos modelos de domínio imutáveis (posentinel.models)."""

import dataclasses

import pytest

from posentinel.models import Issue, OdooMetadata, ScanSummary, Severity, TranslationEntry


class TestSeverity:
    def test_values(self) -> None:
        assert Severity.INFO == "info"
        assert Severity.WARNING == "warning"
        assert Severity.ERROR == "error"


class TestOdooMetadata:
    def test_defaults_are_none(self) -> None:
        metadata = OdooMetadata()

        assert metadata.module is None
        assert metadata.model is None
        assert metadata.field_name is None
        assert metadata.xml_id is None
        assert metadata.term_type is None

    def test_is_frozen(self) -> None:
        metadata = OdooMetadata(module="sale")

        with pytest.raises(dataclasses.FrozenInstanceError):
            metadata.module = "account"  # type: ignore[misc]


class TestTranslationEntry:
    def test_is_header_true_for_empty_msgid(self) -> None:
        entry = TranslationEntry(msgid="")

        assert entry.is_header is True

    def test_is_header_false_for_regular_entry(self) -> None:
        entry = TranslationEntry(msgid="Hello", msgstr="Olá")

        assert entry.is_header is False

    def test_is_python_format_true_when_flag_present(self) -> None:
        entry = TranslationEntry(msgid="Hello %s", flags=("python-format",))

        assert entry.is_python_format is True

    def test_is_python_format_false_when_flag_absent(self) -> None:
        entry = TranslationEntry(msgid="Hello", flags=("fuzzy",))

        assert entry.is_python_format is False

    def test_all_translations_returns_singular_when_filled(self) -> None:
        entry = TranslationEntry(msgid="Hello", msgstr="Olá")

        assert entry.all_translations == ["Olá"]

    def test_all_translations_returns_empty_list_when_msgstr_blank(self) -> None:
        entry = TranslationEntry(msgid="Hello", msgstr="")

        assert entry.all_translations == []

    def test_all_translations_returns_plural_forms_when_present(self) -> None:
        entry = TranslationEntry(
            msgid="1 item",
            msgid_plural="%d items",
            msgstr_plural={0: "1 item", 1: "%d itens"},
        )

        assert entry.all_translations == ["1 item", "%d itens"]

    def test_is_frozen(self) -> None:
        entry = TranslationEntry(msgid="Hello")

        with pytest.raises(dataclasses.FrozenInstanceError):
            entry.msgstr = "Olá"  # type: ignore[misc]

    def test_odoo_metadata_default_factory_is_independent_per_instance(self) -> None:
        first = TranslationEntry(msgid="a")
        second = TranslationEntry(msgid="b", odoo_metadata=OdooMetadata(module="sale"))

        assert first.odoo_metadata.module is None
        assert second.odoo_metadata.module == "sale"


class TestIssue:
    def test_defaults(self) -> None:
        issue = Issue(
            code="PO001",
            message="Tradução vazia",
            severity=Severity.WARNING,
            line=10,
            msgid="Hello",
        )

        assert issue.odoo_context is None
        assert issue.suggestion is None

    def test_is_frozen(self) -> None:
        issue = Issue(
            code="PO001",
            message="Tradução vazia",
            severity=Severity.WARNING,
            line=10,
            msgid="Hello",
        )

        with pytest.raises(dataclasses.FrozenInstanceError):
            issue.message = "outra mensagem"  # type: ignore[misc]


class TestScanSummary:
    def test_defaults(self) -> None:
        summary = ScanSummary(file_path="pt_BR.po")

        assert summary.locale is None
        assert summary.total_entries == 0
        assert summary.issues == []
        assert summary.has_errors is False

    def test_counters_by_severity(self) -> None:
        summary = ScanSummary(
            file_path="pt_BR.po",
            issues=[
                Issue(code="PO002", message="m1", severity=Severity.ERROR, line=1, msgid="a"),
                Issue(code="PO002", message="m2", severity=Severity.ERROR, line=2, msgid="b"),
                Issue(code="PO001", message="m3", severity=Severity.WARNING, line=3, msgid="c"),
                Issue(code="SYS001", message="m4", severity=Severity.INFO, line=4, msgid="d"),
            ],
        )

        assert summary.errors_count == 2
        assert summary.warnings_count == 1
        assert summary.infos_count == 1
        assert summary.has_errors is True

    def test_has_errors_false_when_only_warnings(self) -> None:
        summary = ScanSummary(
            file_path="pt_BR.po",
            issues=[
                Issue(code="PO001", message="m1", severity=Severity.WARNING, line=1, msgid="a"),
            ],
        )

        assert summary.has_errors is False
