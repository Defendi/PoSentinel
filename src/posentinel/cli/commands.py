"""Interface de linha de comando do PoSentinel, construída com Typer."""

from enum import StrEnum
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from posentinel import __version__
from posentinel.analyzers.analyzer import TranslationAnalyzer
from posentinel.models import ScanSummary
from posentinel.parser.po_parser import PoParser
from posentinel.reporters.console import ConsoleReporter
from posentinel.reporters.json import JsonReporter
from posentinel.rules.base import BaseRule
from posentinel.rules.engine import RulesEngine
from posentinel.rules.fuzzy import FuzzyTranslationRule
from posentinel.rules.placeholders import (
    ExtraPlaceholderRule,
    InvalidPlaceholderRule,
    MissingPlaceholderRule,
)
from posentinel.rules.syntax import InvalidMarkupRule
from posentinel.rules.translations import EmptyTranslationRule

app = typer.Typer(
    name="posentinel",
    help="Linter determinístico para arquivos .po de internacionalização (foco Odoo/pt_BR).",
)


class OutputFormat(StrEnum):
    CONSOLE = "console"
    JSON = "json"


class FailOnLevel(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    NONE = "none"


def _default_rules() -> list[BaseRule]:
    return [
        EmptyTranslationRule(),
        MissingPlaceholderRule(),
        InvalidPlaceholderRule(),
        ExtraPlaceholderRule(),
        InvalidMarkupRule(),
        FuzzyTranslationRule(),
    ]


def _determine_exit_code(summaries: list[ScanSummary], fail_on: FailOnLevel) -> int:
    has_operational_error = any(
        issue.code == "SYS001" for summary in summaries for issue in summary.issues
    )
    if has_operational_error:
        return 2

    if fail_on == FailOnLevel.NONE:
        return 0

    if any(summary.has_errors for summary in summaries):
        return 1

    if fail_on == FailOnLevel.WARNING and any(summary.warnings_count > 0 for summary in summaries):
        return 1

    return 0


@app.command()
def scan(
    target: Annotated[Path, typer.Argument(help="Arquivo .po ou diretório a analisar")],
    output_format: Annotated[
        OutputFormat, typer.Option("--format", help="Formato de saída")
    ] = OutputFormat.CONSOLE,
    fail_on: Annotated[
        FailOnLevel, typer.Option("--fail-on", help="Nível mínimo que bloqueia o scan")
    ] = FailOnLevel.ERROR,
) -> None:
    """Analisa um arquivo .po ou diretório em busca de problemas de tradução."""
    analyzer = TranslationAnalyzer(PoParser(), RulesEngine(_default_rules()))

    try:
        summaries = analyzer.analyze_path(target)
    except FileNotFoundError:
        typer.echo(f"Erro: arquivo ou diretório não encontrado: {target}", err=True)
        raise typer.Exit(code=2) from None

    if output_format == OutputFormat.JSON:
        typer.echo(JsonReporter().report(summaries))
    else:
        for summary in summaries:
            if summary.total_entries == 0 and not summary.issues:
                typer.echo(f"Aviso: {summary.file_path} está vazio (nenhuma entrada).")
        ConsoleReporter().report(summaries)

    raise typer.Exit(code=_determine_exit_code(summaries, fail_on))


@app.command()
def rules() -> None:
    """Lista as regras de validação ativas."""
    console = Console()
    table = Table(show_header=True, header_style="bold")
    table.add_column("Código")
    table.add_column("Severidade")
    table.add_column("Descrição")

    for rule in _default_rules():
        table.add_row(rule.code, rule.default_severity.value.upper(), rule.description)

    console.print(table)


@app.command()
def version() -> None:
    """Exibe a versão instalada do PoSentinel."""
    typer.echo(f"posentinel {__version__}")
