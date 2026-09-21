"""Testes de integração ponta a ponta sobre as fixtures compartilhadas em tests/fixtures/.

Exercita o pipeline real (PoParser + RulesEngine com as 6 regras do MVP) sobre
arquivos .po estáticos, complementando os testes unitários das camadas isoladas.
"""

from pathlib import Path

import pytest

from posentinel.models import Issue, TranslationEntry
from posentinel.parser.po_parser import PoParser
from posentinel.rules import (
    EmptyTranslationRule,
    ExtraPlaceholderRule,
    FuzzyTranslationRule,
    InvalidMarkupRule,
    InvalidPlaceholderRule,
    MissingPlaceholderRule,
    RulesEngine,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _all_rules_engine() -> RulesEngine:
    return RulesEngine(
        [
            EmptyTranslationRule(),
            MissingPlaceholderRule(),
            InvalidPlaceholderRule(),
            ExtraPlaceholderRule(),
            InvalidMarkupRule(),
            FuzzyTranslationRule(),
        ]
    )


def _analyze_file(path: Path) -> tuple[list[TranslationEntry], list[Issue]]:
    parser_result = PoParser().parse_file(path)
    engine = _all_rules_engine()
    issues: list[Issue] = list(parser_result.issues)
    for entry in parser_result.entries:
        issues.extend(engine.analyze(entry))
    return parser_result.entries, issues


class TestValidFixture:
    def test_has_no_issues(self) -> None:
        entries, issues = _analyze_file(FIXTURES_DIR / "valid.po")

        assert len(entries) == 4
        assert issues == []

    def test_includes_singular_and_plural_entries(self) -> None:
        entries, _issues = _analyze_file(FIXTURES_DIR / "valid.po")

        plural_entries = [entry for entry in entries if entry.msgid_plural is not None]
        singular_entries = [entry for entry in entries if entry.msgid_plural is None]

        assert len(plural_entries) == 1
        assert len(singular_entries) == 3

    def test_includes_odoo_metadata(self) -> None:
        entries, _issues = _analyze_file(FIXTURES_DIR / "valid.po")

        assert any(entry.odoo_metadata.module == "sale" for entry in entries)


class TestInvalidFixture:
    def test_flags_exactly_the_expected_codes(self) -> None:
        entries, issues = _analyze_file(FIXTURES_DIR / "invalid.po")

        assert len(entries) == 5
        codes = sorted(issue.code for issue in issues)
        assert codes == ["PO001", "PO002", "PO003", "PO005", "PO006"]

    def test_po003_suggests_the_original_placeholder(self) -> None:
        _entries, issues = _analyze_file(FIXTURES_DIR / "invalid.po")

        po003 = next(issue for issue in issues if issue.code == "PO003")
        assert po003.suggestion == "%(amount)s"


class TestOdooPtBrFixture:
    def test_has_no_issues(self) -> None:
        entries, issues = _analyze_file(FIXTURES_DIR / "odoo_pt_br.po")

        assert len(entries) == 3
        assert issues == []

    def test_extracts_field_description_metadata(self) -> None:
        entries, _issues = _analyze_file(FIXTURES_DIR / "odoo_pt_br.po")

        for entry in entries:
            assert entry.odoo_metadata.module == "account"
            assert entry.odoo_metadata.model == "ir.model.fields"
            assert entry.odoo_metadata.term_type == "field_description"

    def test_includes_pt_br_plural_form(self) -> None:
        entries, _issues = _analyze_file(FIXTURES_DIR / "odoo_pt_br.po")

        plural_entry = next(entry for entry in entries if entry.msgid_plural is not None)
        assert plural_entry.msgstr_plural == {
            0: "%(count)d linha de fatura",
            1: "%(count)d linhas de fatura",
        }


@pytest.mark.parametrize("filename", ["valid.po", "invalid.po", "odoo_pt_br.po"])
def test_fixture_file_exists(filename: str) -> None:
    assert (FIXTURES_DIR / filename).is_file()
