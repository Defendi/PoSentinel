import typer
from rich.console import Console

from posentinel.ai.models import TranslationSuggestion
from posentinel.models import Issue, TranslationEntry


def confirm_translation(
    entry: TranslationEntry, issue: Issue, suggestion: TranslationSuggestion, console: Console
) -> bool:
    console.print(f"[bold]{issue.code}[/bold] {issue.message}")
    console.print(f"  Original: {entry.msgid}")
    console.print(f"  Atual:    {repr(entry.msgstr)}")
    console.print(f"  Sugestão: {repr(suggestion.msgstr)}")
    return typer.confirm("Aplicar esta tradução?", default=False)
