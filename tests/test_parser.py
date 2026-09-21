"""Testes do adaptador PoParser (posentinel.parser.po_parser)."""

from pathlib import Path

import pytest

from posentinel.models import Severity
from posentinel.parser.po_parser import PoParser


class TestPoParserValidFile:
    def test_parses_simple_entry(self, tmp_path: Path) -> None:
        po_file = tmp_path / "valid.po"
        po_file.write_text(
            'msgid ""\n'
            'msgstr ""\n'
            '"Content-Type: text/plain; charset=UTF-8\\n"\n'
            "\n"
            'msgid "Hello"\n'
            'msgstr "Olá"\n',
            encoding="utf-8",
        )

        result = PoParser().parse_file(po_file)

        assert result.issues == []
        assert len(result.entries) == 1
        entry = result.entries[0]
        assert entry.msgid == "Hello"
        assert entry.msgstr == "Olá"

    def test_empty_file_returns_no_entries_and_no_issues(self, tmp_path: Path) -> None:
        po_file = tmp_path / "empty.po"
        po_file.write_text("", encoding="utf-8")

        result = PoParser().parse_file(po_file)

        assert result.entries == []
        assert result.issues == []

    def test_parses_plural_forms(self, tmp_path: Path) -> None:
        po_file = tmp_path / "plural.po"
        po_file.write_text(
            'msgid "%(count)d item"\n'
            'msgid_plural "%(count)d items"\n'
            'msgstr[0] "%(count)d item"\n'
            'msgstr[1] "%(count)d itens"\n',
            encoding="utf-8",
        )

        result = PoParser().parse_file(po_file)

        entry = result.entries[0]
        assert entry.msgid_plural == "%(count)d items"
        assert entry.msgstr_plural == {0: "%(count)d item", 1: "%(count)d itens"}
        assert entry.all_translations == ["%(count)d item", "%(count)d itens"]

    def test_flags_include_fuzzy(self, tmp_path: Path) -> None:
        po_file = tmp_path / "fuzzy.po"
        po_file.write_text(
            '#, fuzzy\nmsgid "Total"\nmsgstr "Totale"\n',
            encoding="utf-8",
        )

        result = PoParser().parse_file(po_file)

        entry = result.entries[0]
        assert entry.is_fuzzy is True
        assert "fuzzy" in entry.flags


class TestPoParserOdooMetadata:
    def test_extracts_module_from_comment(self, tmp_path: Path) -> None:
        po_file = tmp_path / "odoo.po"
        po_file.write_text(
            "#. module: sale\n"
            "#: model:ir.model.fields,field_description:sale.field_sale_order__partner_id\n"
            'msgid "Customer"\n'
            'msgstr "Cliente"\n',
            encoding="utf-8",
        )

        result = PoParser().parse_file(po_file)

        metadata = result.entries[0].odoo_metadata
        assert metadata.module == "sale"
        assert metadata.model == "ir.model.fields"
        assert metadata.term_type == "field_description"
        assert metadata.field_name == "sale.field_sale_order__partner_id"
        assert metadata.xml_id is None

    def test_extracts_xml_id_for_non_field_description_term_type(self, tmp_path: Path) -> None:
        po_file = tmp_path / "odoo_view.po"
        po_file.write_text(
            "#. module: sale\n"
            "#: model:ir.ui.view,arch_db:sale.view_order_form\n"
            'msgid "Confirm"\n'
            'msgstr "Confirmar"\n',
            encoding="utf-8",
        )

        result = PoParser().parse_file(po_file)

        metadata = result.entries[0].odoo_metadata
        assert metadata.term_type == "arch_db"
        assert metadata.xml_id == "sale.view_order_form"
        assert metadata.field_name is None

    def test_ignores_model_terms_occurrence_when_no_model_occurrence_present(
        self, tmp_path: Path
    ) -> None:
        po_file = tmp_path / "model_terms_only.po"
        po_file.write_text(
            "#. module: sale\n"
            "#: model_terms:ir.ui.view,arch_db:sale.view_order_form\n"
            'msgid "Confirm"\n'
            'msgstr "Confirmar"\n',
            encoding="utf-8",
        )

        result = PoParser().parse_file(po_file)

        metadata = result.entries[0].odoo_metadata
        assert metadata.model is None
        assert metadata.field_name is None
        assert metadata.xml_id is None

    def test_entry_without_odoo_comments_has_empty_metadata(self, tmp_path: Path) -> None:
        po_file = tmp_path / "no_odoo.po"
        po_file.write_text('msgid "Hello"\nmsgstr "Olá"\n', encoding="utf-8")

        result = PoParser().parse_file(po_file)

        metadata = result.entries[0].odoo_metadata
        assert metadata.module is None
        assert metadata.model is None

    def test_comment_without_module_line_leaves_module_none(self, tmp_path: Path) -> None:
        po_file = tmp_path / "comment_no_module.po"
        po_file.write_text(
            '#. Nota qualquer sem prefixo module:\nmsgid "Hello"\nmsgstr "Olá"\n',
            encoding="utf-8",
        )

        result = PoParser().parse_file(po_file)

        assert result.entries[0].odoo_metadata.module is None


class TestPoParserEncodingFallback:
    def test_falls_back_to_latin1_when_utf8_decoding_fails(self, tmp_path: Path) -> None:
        po_file = tmp_path / "latin1.po"
        content = 'msgid "Ol\xe1"\nmsgstr "Mundo\xe1"\n'
        po_file.write_bytes(content.encode("latin-1"))

        result = PoParser().parse_file(po_file)

        assert result.issues == []
        assert result.entries[0].msgid == "Olá"
        assert result.entries[0].msgstr == "Mundoá"


class TestPoParserResilience:
    def test_missing_file_raises_file_not_found(self, tmp_path: Path) -> None:
        missing = tmp_path / "does_not_exist.po"

        with pytest.raises(FileNotFoundError):
            PoParser().parse_file(missing)

    def test_syntax_error_becomes_sys001_issue_without_raising(self, tmp_path: Path) -> None:
        po_file = tmp_path / "broken.po"
        po_file.write_text("isso nao eh um arquivo po valido\nblah blah\n", encoding="utf-8")

        result = PoParser().parse_file(po_file)

        assert result.entries == []
        assert len(result.issues) == 1
        issue = result.issues[0]
        assert issue.code == "SYS001"
        assert issue.severity == Severity.ERROR
