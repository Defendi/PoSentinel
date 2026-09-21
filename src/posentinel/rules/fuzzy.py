"""Regra PO006: detecta entradas marcadas com a flag fuzzy."""

from posentinel.models import Issue, Severity, TranslationEntry
from posentinel.rules.base import BaseRule


class FuzzyTranslationRule(BaseRule):
    code = "PO006"
    description = "Entrada marcada como fuzzy, pendente de revisão"
    default_severity = Severity.WARNING

    def check(self, entry: TranslationEntry) -> list[Issue]:
        if entry.is_header or not entry.is_fuzzy:
            return []

        return [self._issue(entry, "Entrada marcada como fuzzy — tradução pendente de revisão")]
