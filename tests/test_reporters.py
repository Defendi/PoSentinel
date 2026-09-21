"""Testes dos reporters (posentinel.reporters.console e posentinel.reporters.json)."""

import json
from io import StringIO

from rich.console import Console

from posentinel.models import Issue, ScanSummary, Severity
from posentinel.reporters.console import ConsoleReporter
from posentinel.reporters.json import JsonReporter


def _make_console_reporter() -> tuple[ConsoleReporter, Console]:
    buffer = StringIO()
    console = Console(file=buffer, record=True, width=120)
    return ConsoleReporter(console=console), console


def _issue(code: str, severity: Severity, **overrides: object) -> Issue:
    defaults: dict[str, object] = {
        "code": code,
        "message": f"mensagem de {code}",
        "severity": severity,
        "line": 10,
        "msgid": "Hello",
        "odoo_context": "sale",
        "suggestion": None,
    }
    defaults.update(overrides)
    return Issue(**defaults)  # type: ignore[arg-type]


class TestConsoleReporter:
    def test_reports_passed_when_no_issues(self) -> None:
        reporter, console = _make_console_reporter()
        summary = ScanSummary(file_path="pt_BR.po", locale="pt_BR", total_entries=3, issues=[])

        reporter.report([summary])

        output = console.export_text()
        assert "pt_BR.po" in output
        assert "PASSED" in output

    def test_reports_warnings_status_when_only_warnings(self) -> None:
        reporter, console = _make_console_reporter()
        summary = ScanSummary(
            file_path="pt_BR.po",
            locale="pt_BR",
            total_entries=1,
            issues=[_issue("PO001", Severity.WARNING)],
        )

        reporter.report([summary])

        output = console.export_text()
        assert "WARNINGS" in output
        assert "PO001" in output

    def test_reports_failed_status_when_errors_present(self) -> None:
        reporter, console = _make_console_reporter()
        summary = ScanSummary(
            file_path="pt_BR.po",
            locale="pt_BR",
            total_entries=1,
            issues=[_issue("PO002", Severity.ERROR)],
        )

        reporter.report([summary])

        output = console.export_text()
        assert "FAILED" in output
        assert "PO002" in output

    def test_includes_issue_details_in_table(self) -> None:
        reporter, console = _make_console_reporter()
        summary = ScanSummary(
            file_path="pt_BR.po",
            locale="pt_BR",
            total_entries=1,
            issues=[_issue("PO002", Severity.ERROR, odoo_context="sale", line=42)],
        )

        reporter.report([summary])

        output = console.export_text()
        assert "sale" in output
        assert "42" in output
        assert "mensagem de PO002" in output

    def test_reports_multiple_files(self) -> None:
        reporter, console = _make_console_reporter()
        summaries = [
            ScanSummary(file_path="pt_BR.po", locale="pt_BR", total_entries=1, issues=[]),
            ScanSummary(file_path="en.po", locale="en", total_entries=1, issues=[]),
        ]

        reporter.report(summaries)

        output = console.export_text()
        assert "pt_BR.po" in output
        assert "en.po" in output

    def test_creates_default_console_when_none_provided(self) -> None:
        reporter = ConsoleReporter()

        assert reporter is not None


class TestJsonReporter:
    def test_produces_valid_json(self) -> None:
        reporter = JsonReporter()
        summary = ScanSummary(file_path="pt_BR.po", locale="pt_BR", total_entries=2, issues=[])

        payload = json.loads(reporter.report([summary]))

        assert "results" in payload
        assert len(payload["results"]) == 1

    def test_includes_summary_fields(self) -> None:
        reporter = JsonReporter()
        summary = ScanSummary(
            file_path="pt_BR.po",
            locale="pt_BR",
            total_entries=5,
            issues=[_issue("PO001", Severity.WARNING), _issue("PO002", Severity.ERROR)],
        )

        payload = json.loads(reporter.report([summary]))
        result = payload["results"][0]

        assert result["file_path"] == "pt_BR.po"
        assert result["locale"] == "pt_BR"
        assert result["total_entries"] == 5
        assert result["errors_count"] == 1
        assert result["warnings_count"] == 1
        assert result["infos_count"] == 0

    def test_includes_issue_details(self) -> None:
        reporter = JsonReporter()
        summary = ScanSummary(
            file_path="pt_BR.po",
            issues=[
                _issue(
                    "PO003",
                    Severity.ERROR,
                    line=7,
                    msgid="Hello %(name)s",
                    odoo_context="sale",
                    suggestion="%(name)s",
                )
            ],
        )

        payload = json.loads(reporter.report([summary]))
        issue = payload["results"][0]["issues"][0]

        assert issue["code"] == "PO003"
        assert issue["severity"] == "error"
        assert issue["line"] == 7
        assert issue["msgid"] == "Hello %(name)s"
        assert issue["odoo_context"] == "sale"
        assert issue["suggestion"] == "%(name)s"

    def test_empty_summaries_list_produces_empty_results(self) -> None:
        reporter = JsonReporter()

        payload = json.loads(reporter.report([]))

        assert payload == {"results": []}

    def test_multiple_summaries(self) -> None:
        reporter = JsonReporter()
        summaries = [
            ScanSummary(file_path="pt_BR.po", issues=[]),
            ScanSummary(file_path="en.po", issues=[]),
        ]

        payload = json.loads(reporter.report(summaries))

        assert len(payload["results"]) == 2
