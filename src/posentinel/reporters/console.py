"""Apresentação formatada dos resultados de scan via Rich."""

from rich.console import Console
from rich.table import Table

from posentinel.models import ScanSummary, Severity, TranslationChange

_SEVERITY_STYLES = {
    Severity.ERROR: "bold red",
    Severity.WARNING: "yellow",
    Severity.INFO: "cyan",
}

_STATUS_STYLES = {
    "FAILED": "bold red",
    "WARNINGS": "yellow",
    "PASSED": "bold green",
}


class ConsoleReporter:
    """Imprime os resultados do scan no terminal, com tabelas e cores por severidade."""

    def __init__(self, console: Console | None = None) -> None:
        self._console = console or Console()

    def report(
        self,
        summaries: list[ScanSummary],
        changes: dict[str, list[TranslationChange]] | None = None,
    ) -> None:
        for summary in summaries:
            file_changes = changes.get(summary.file_path) if changes else None
            self._report_summary(summary, file_changes)

    def _report_summary(
        self, summary: ScanSummary, changes: list[TranslationChange] | None = None
    ) -> None:
        locale_text = summary.locale or "—"
        self._console.print(
            f"[bold]{summary.file_path}[/bold] "
            f"(locale: {locale_text}, {summary.total_entries} entrada(s))"
        )

        if summary.issues:
            self._console.print(self._build_table(summary))

        if changes:
            self._console.print(self._build_changes_table(changes))

        self._console.print(self._summary_line(summary))
        self._console.print()

    def _build_table(self, summary: ScanSummary) -> Table:
        table = Table(show_header=True, header_style="bold")
        table.add_column("Severidade")
        table.add_column("Código")
        table.add_column("Linha")
        table.add_column("Módulo Odoo")
        table.add_column("Mensagem")

        for issue in summary.issues:
            style = _SEVERITY_STYLES[issue.severity]
            table.add_row(
                f"[{style}]{issue.severity.value.upper()}[/{style}]",
                issue.code,
                str(issue.line) if issue.line is not None else "—",
                issue.odoo_context or "—",
                issue.message,
            )
        return table

    def _build_changes_table(self, changes: list[TranslationChange]) -> Table:
        table = Table(show_header=True, header_style="bold", title="Traduções (IA)")
        table.add_column("Código")
        table.add_column("Original")
        table.add_column("Antes")
        table.add_column("Depois")
        table.add_column("Aplicada")

        for change in changes:
            applied = "[bold green]✓[/bold green]" if change.applied else "[bold red]✗[/bold red]"
            table.add_row(
                change.issue_code,
                change.msgid,
                change.old_msgstr,
                change.new_msgstr,
                applied,
            )
        return table

    def _summary_line(self, summary: ScanSummary) -> str:
        if summary.has_errors:
            status = "FAILED"
        elif summary.warnings_count:
            status = "WARNINGS"
        else:
            status = "PASSED"

        style = _STATUS_STYLES[status]
        return (
            f"[{style}]{status}[/{style}] — "
            f"{summary.errors_count} erro(s), {summary.warnings_count} aviso(s)"
        )
