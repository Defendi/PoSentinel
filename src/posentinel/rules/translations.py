"""Regra PO001: detecta traduções vazias para termos originais não vazios."""

from posentinel.models import Issue, Severity, TranslationEntry
from posentinel.rules.base import BaseRule


class EmptyTranslationRule(BaseRule):
    code = "PO001"
    description = "Termo original com tradução vazia"
    default_severity = Severity.WARNING

    def check(self, entry: TranslationEntry) -> list[Issue]:
        if entry.is_header:
            return []

        if entry.msgid_plural is not None:
            return self._check_plural(entry)

        if entry.msgstr:
            return []
        return [self._issue(entry, "Tradução vazia para o termo original")]

    def _check_plural(self, entry: TranslationEntry) -> list[Issue]:
        empty_indexes = sorted(index for index, value in entry.msgstr_plural.items() if not value)
        if not empty_indexes:
            return []

        indexes_text = ", ".join(str(index) for index in empty_indexes)
        return [self._issue(entry, f"Tradução vazia para forma(s) plural(is): {indexes_text}")]
