import sys
from enum import StrEnum
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from posentinel.analyzers.analyzer import TranslationAnalyzer
from posentinel.models.entry import Severity
from posentinel.reporters.console import ConsoleReporter
from posentinel.reporters.json import JsonReporter
from posentinel.rules import get_default_rules

app = typer.Typer(
    name="posentinel",
    help="Odoo Translation Quality Analyzer - Linter determinístico para arquivos .po",
    no_args_is_help=True,
)
console = Console()

__version__ = "0.1.0"


class OutputFormat(StrEnum):
    CONSOLE = "console"
    JSON = "json"


class FailOnLevel(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    NONE = "none"


@app.command()
def scan(
    target: Path = typer.Argument(
        ...,
        help="Caminho do arquivo .po ou diretório contendo arquivos .po para análise.",
        exists=True,
    ),
    format: OutputFormat = typer.Option(
        OutputFormat.CONSOLE,
        "--format",
        "-f",
        help="Formato de apresentação do relatório (console ou json).",
    ),
    fail_on: FailOnLevel = typer.Option(
        FailOnLevel.ERROR,
        "--fail-on",
        help="Nível de severidade mínimo para retornar código de saída de erro (1).",
    ),
) -> None:
    """Executa a varredura e validação das regras de qualidade sobre os arquivos .po."""
    analyzer = TranslationAnalyzer()

    try:
        summaries = analyzer.analyze_path(target)
    except Exception as exc:  # noqa: BLE001
        console.print(f"[bold red]Erro ao processar arquivos:[/bold red] {exc}", file=sys.stderr)
        raise typer.Exit(code=2) from exc

    if format == OutputFormat.JSON:
        json_reporter = JsonReporter()
        print(json_reporter.render(summaries))
    else:
        console_reporter = ConsoleReporter(console)
        console_reporter.report(summaries)

    # Avaliação de Exit Code
    has_blocking_issues = False
    for s in summaries:
        if fail_on == FailOnLevel.ERROR and s.has_errors or fail_on == FailOnLevel.WARNING and (s.has_errors or s.warnings_count > 0):
            has_blocking_issues = True
            break

    if has_blocking_issues:
        raise typer.Exit(code=1)

    raise typer.Exit(code=0)


@app.command()
def rules() -> None:
    """Lista todas as regras de qualidade registradas no PoSentinel."""
    all_rules = get_default_rules()
    table = Table(
        title="Regras Disponíveis - PoSentinel", show_header=True, header_style="bold cyan"
    )
    table.add_column("Código", width=10, style="bold")
    table.add_column("Severidade Padrão", width=16)
    table.add_column("Descrição")

    for r in all_rules:
        sev_color = "red" if r.default_severity == Severity.ERROR else "yellow"
        table.add_row(
            r.code, f"[{sev_color}]{r.default_severity.value.upper()}[/{sev_color}]", r.description
        )

    console.print(table)


@app.command()
def version() -> None:
    """Exibe a versão instalada do PoSentinel."""
    console.print(
        f"[bold cyan]PoSentinel[/bold cyan] versão [bold green]{__version__}[/bold green]"
    )


def main() -> None:
    app()


if __name__ == "__main__":
    main()
