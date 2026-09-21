from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from posentinel.models.entry import Severity
from posentinel.models.result import ScanSummary


class ConsoleReporter:
    """Apresentador de resultados no terminal formatado com Rich."""

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()

    def report(self, summaries: list[ScanSummary]) -> None:
        for summary in summaries:
            self._report_single(summary)

    def _report_single(self, summary: ScanSummary) -> None:
        status_color = (
            "red" if summary.has_errors else ("yellow" if summary.warnings_count > 0 else "green")
        )
        status_text = (
            "FAILED"
            if summary.has_errors
            else ("WARNINGS" if summary.warnings_count > 0 else "PASSED")
        )

        self.console.print()
        self.console.print(
            Panel.fit(
                f"[bold cyan]PoSentinel[/bold cyan] - Arquivo: [bold]{summary.file_path}[/bold] | "
                f"Locale: [green]{summary.locale or 'N/A'}[/green] | "
                f"Entradas: [bold]{summary.total_entries}[/bold]",
                border_style="blue",
            )
        )

        if not summary.issues:
            self.console.print(
                f"[{status_color}]✓ Nenhuma issue encontrada. Arquivo de tradução íntegro![/{status_color}]\n"
            )
            return

        table = Table(show_header=True, header_style="bold magenta", expand=True)
        table.add_column("Severidade", width=12)
        table.add_column("Código", width=8)
        table.add_column("Linha", width=7, justify="right")
        table.add_column("Módulo Odoo", width=14)
        table.add_column("Mensagem", ratio=1)

        for issue in summary.issues:
            if issue.severity == Severity.ERROR:
                sev_styled = "[bold red]✗ ERROR[/bold red]"
            elif issue.severity == Severity.WARNING:
                sev_styled = "[bold yellow]⚠ WARN[/bold yellow]"
            else:
                sev_styled = "[bold blue]ℹ INFO[/bold blue]"

            line_str = str(issue.line) if issue.line is not None else "-"
            odoo_ctx = issue.odoo_context or "-"
            table.add_row(sev_styled, issue.code, line_str, odoo_ctx, issue.message)

        self.console.print(table)
        self.console.print(
            f"Resultado: [{status_color}][bold]{status_text}[/bold][/{status_color}] "
            f"([red]{summary.errors_count} erro(s)[/red], [yellow]{summary.warnings_count} aviso(s)[/yellow], [blue]{summary.infos_count} info(s)[/blue])\n"
        )
