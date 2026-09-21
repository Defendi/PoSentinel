"""Testes do orquestrador TranslationAnalyzer (posentinel.analyzers.analyzer)."""

from pathlib import Path

import pytest

from posentinel.analyzers.analyzer import TranslationAnalyzer
from posentinel.parser.po_parser import PoParser
from posentinel.rules.engine import RulesEngine
from posentinel.rules.translations import EmptyTranslationRule


def _analyzer() -> TranslationAnalyzer:
    return TranslationAnalyzer(PoParser(), RulesEngine([EmptyTranslationRule()]))


class TestAnalyzeSingleFile:
    def test_returns_single_summary_for_a_file(self, tmp_path: Path) -> None:
        po_file = tmp_path / "pt_BR.po"
        po_file.write_text('msgid "Hello"\nmsgstr "Olá"\n', encoding="utf-8")

        summaries = _analyzer().analyze_path(po_file)

        assert len(summaries) == 1
        summary = summaries[0]
        assert summary.file_path == str(po_file)
        assert summary.total_entries == 1
        assert summary.issues == []

    def test_detects_locale_from_file_stem(self, tmp_path: Path) -> None:
        po_file = tmp_path / "pt_BR.po"
        po_file.write_text('msgid "Hello"\nmsgstr "Olá"\n', encoding="utf-8")

        summaries = _analyzer().analyze_path(po_file)

        assert summaries[0].locale == "pt_BR"

    def test_includes_issues_from_rules_engine(self, tmp_path: Path) -> None:
        po_file = tmp_path / "pt_BR.po"
        po_file.write_text('msgid "Hello"\nmsgstr ""\n', encoding="utf-8")

        summaries = _analyzer().analyze_path(po_file)

        assert len(summaries[0].issues) == 1
        assert summaries[0].issues[0].code == "PO001"

    def test_includes_syntax_issue_without_raising(self, tmp_path: Path) -> None:
        po_file = tmp_path / "broken.po"
        po_file.write_text("isso nao eh um arquivo po valido\n", encoding="utf-8")

        summaries = _analyzer().analyze_path(po_file)

        assert len(summaries) == 1
        assert summaries[0].total_entries == 0
        assert summaries[0].issues[0].code == "SYS001"

    def test_missing_file_propagates_file_not_found(self, tmp_path: Path) -> None:
        missing = tmp_path / "does_not_exist.po"

        with pytest.raises(FileNotFoundError):
            _analyzer().analyze_path(missing)


class TestAnalyzeDirectory:
    def test_returns_one_summary_per_po_file(self, tmp_path: Path) -> None:
        (tmp_path / "pt_BR.po").write_text('msgid "a"\nmsgstr "b"\n', encoding="utf-8")
        (tmp_path / "en.po").write_text('msgid "a"\nmsgstr "b"\n', encoding="utf-8")
        (tmp_path / "readme.txt").write_text("not a po file", encoding="utf-8")

        summaries = _analyzer().analyze_path(tmp_path)

        assert len(summaries) == 2
        file_paths = {Path(summary.file_path).name for summary in summaries}
        assert file_paths == {"pt_BR.po", "en.po"}

    def test_scans_subdirectories_recursively(self, tmp_path: Path) -> None:
        nested = tmp_path / "addons" / "sale" / "i18n"
        nested.mkdir(parents=True)
        (nested / "pt_BR.po").write_text('msgid "a"\nmsgstr "b"\n', encoding="utf-8")

        summaries = _analyzer().analyze_path(tmp_path)

        assert len(summaries) == 1
        assert summaries[0].file_path == str(nested / "pt_BR.po")

    def test_returns_empty_list_for_directory_without_po_files(self, tmp_path: Path) -> None:
        (tmp_path / "readme.txt").write_text("not a po file", encoding="utf-8")

        summaries = _analyzer().analyze_path(tmp_path)

        assert summaries == []

    def test_syntax_error_in_one_file_does_not_abort_the_scan(self, tmp_path: Path) -> None:
        (tmp_path / "broken.po").write_text("nao eh po valido\n", encoding="utf-8")
        (tmp_path / "ok.po").write_text('msgid "a"\nmsgstr "b"\n', encoding="utf-8")

        summaries = _analyzer().analyze_path(tmp_path)

        assert len(summaries) == 2
        by_name = {Path(summary.file_path).name: summary for summary in summaries}
        assert by_name["broken.po"].issues[0].code == "SYS001"
        assert by_name["ok.po"].issues == []

    def test_summaries_are_sorted_deterministically(self, tmp_path: Path) -> None:
        (tmp_path / "zz.po").write_text('msgid "a"\nmsgstr "b"\n', encoding="utf-8")
        (tmp_path / "aa.po").write_text('msgid "a"\nmsgstr "b"\n', encoding="utf-8")

        summaries = _analyzer().analyze_path(tmp_path)

        names = [Path(summary.file_path).name for summary in summaries]
        assert names == sorted(names)
