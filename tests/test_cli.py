"""Testes da CLI (posentinel.cli.commands) via typer.testing.CliRunner."""

import json
import runpy
import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from posentinel import __version__
from posentinel.cli.commands import app

runner = CliRunner()
FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestScanExitCodes:
    def test_valid_file_returns_exit_0(self) -> None:
        result = runner.invoke(app, ["scan", str(FIXTURES_DIR / "valid.po")])

        assert result.exit_code == 0
        assert "PASSED" in result.stdout

    def test_invalid_file_returns_exit_1(self) -> None:
        result = runner.invoke(app, ["scan", str(FIXTURES_DIR / "invalid.po")])

        assert result.exit_code == 1
        assert "FAILED" in result.stdout

    def test_missing_file_returns_exit_2(self) -> None:
        result = runner.invoke(app, ["scan", "does_not_exist.po"])

        assert result.exit_code == 2

    def test_syntax_error_returns_exit_2_even_with_fail_on_none(self, tmp_path: Path) -> None:
        broken = tmp_path / "broken.po"
        broken.write_text("isso nao eh um arquivo po valido\n", encoding="utf-8")

        result = runner.invoke(app, ["scan", str(broken), "--fail-on", "none"])

        assert result.exit_code == 2

    def test_fail_on_none_always_returns_exit_0(self) -> None:
        result = runner.invoke(app, ["scan", str(FIXTURES_DIR / "invalid.po"), "--fail-on", "none"])

        assert result.exit_code == 0

    def test_fail_on_warning_blocks_on_warning_only_entry(self, tmp_path: Path) -> None:
        po_file = tmp_path / "fuzzy_only.po"
        po_file.write_text('#, fuzzy\nmsgid "Draft"\nmsgstr "Rascunho"\n', encoding="utf-8")

        default_result = runner.invoke(app, ["scan", str(po_file)])
        warning_result = runner.invoke(app, ["scan", str(po_file), "--fail-on", "warning"])

        assert default_result.exit_code == 0
        assert warning_result.exit_code == 1

    def test_empty_file_shows_warning_and_returns_exit_0(self, tmp_path: Path) -> None:
        empty_file = tmp_path / "empty.po"
        empty_file.write_text("", encoding="utf-8")

        result = runner.invoke(app, ["scan", str(empty_file)])

        assert result.exit_code == 0
        assert "vazio" in result.stdout.lower()

    def test_scans_directory_reporting_all_files(self, tmp_path: Path) -> None:
        (tmp_path / "a.po").write_text('msgid "x"\nmsgstr "y"\n', encoding="utf-8")
        (tmp_path / "b.po").write_text('msgid "x"\nmsgstr "y"\n', encoding="utf-8")

        result = runner.invoke(app, ["scan", str(tmp_path)])

        assert result.exit_code == 0
        assert "a.po" in result.stdout
        assert "b.po" in result.stdout


class TestScanJsonFormat:
    def test_produces_valid_json_payload(self) -> None:
        result = runner.invoke(app, ["scan", str(FIXTURES_DIR / "invalid.po"), "--format", "json"])

        payload = json.loads(result.stdout)
        assert len(payload["results"]) == 1
        assert payload["results"][0]["file_path"] == str(FIXTURES_DIR / "invalid.po")
        assert result.exit_code == 1


class TestRulesCommand:
    def test_lists_all_six_rule_codes(self) -> None:
        result = runner.invoke(app, ["rules"])

        assert result.exit_code == 0
        for code in ["PO001", "PO002", "PO003", "PO004", "PO005", "PO006"]:
            assert code in result.stdout


class TestVersionCommand:
    def test_prints_installed_version(self) -> None:
        result = runner.invoke(app, ["version"])

        assert result.exit_code == 0
        assert __version__ in result.stdout


class TestMainEntryPoint:
    def test_python_dash_m_posentinel_runs_the_cli(self) -> None:
        result = subprocess.run(
            [sys.executable, "-m", "posentinel", "version"],
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0
        assert __version__ in result.stdout

    def test_running_main_module_directly_invokes_the_app(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(sys, "argv", ["posentinel", "version"])

        with pytest.raises(SystemExit) as exc_info:
            runpy.run_module("posentinel", run_name="__main__")

        assert exc_info.value.code == 0
