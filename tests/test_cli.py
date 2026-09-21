from pathlib import Path

from typer.testing import CliRunner

from posentinel.cli.commands import app

runner = CliRunner()


def test_cli_rules_command() -> None:
    result = runner.invoke(app, ["rules"])
    assert result.exit_code == 0
    assert "PO001" in result.stdout
    assert "PO002" in result.stdout


def test_cli_version_command() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "PoSentinel" in result.stdout


def test_cli_scan_valid_file() -> None:
    valid_file = Path(__file__).parent / "fixtures" / "valid.po"
    result = runner.invoke(app, ["scan", str(valid_file)])
    assert result.exit_code == 0
    assert "Nenhuma issue encontrada" in result.stdout


def test_cli_scan_invalid_file() -> None:
    invalid_file = Path(__file__).parent / "fixtures" / "invalid.po"
    result = runner.invoke(app, ["scan", str(invalid_file)])
    assert result.exit_code == 1
    assert "PO001" in result.stdout
    assert "PO002" in result.stdout
    assert "PO003" in result.stdout
    assert "PO004" in result.stdout
    assert "PO005" in result.stdout


def test_cli_scan_json_output() -> None:
    invalid_file = Path(__file__).parent / "fixtures" / "invalid.po"
    result = runner.invoke(app, ["scan", str(invalid_file), "--format", "json"])
    assert result.exit_code == 1
    assert '"code": "PO001"' in result.stdout
    assert '"code": "PO002"' in result.stdout
    assert '"status": "failed"' in result.stdout
