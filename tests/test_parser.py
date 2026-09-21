from pathlib import Path

from posentinel.parser.po_parser import PoParser


def test_po_parser_valid_file() -> None:
    fixture_path = Path(__file__).parent / "fixtures" / "valid.po"
    parser = PoParser()
    entries = parser.parse_file(fixture_path)

    assert len(entries) == 3

    first = entries[0]
    assert first.msgid == "Customer Rank"
    assert first.msgstr == "Classificação do Cliente"
    assert first.odoo_metadata.module == "sale"
    assert first.odoo_metadata.model == "ir.model.fields"
    assert first.odoo_metadata.term_type == "field_description"
    assert first.odoo_metadata.field_name == "sale.field_res_partner__customer_rank"

    second = entries[1]
    assert second.is_python_format is True
    assert second.odoo_metadata.module == "sale"
