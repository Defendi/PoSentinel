"""Regra PO007: conformidade de tradução com glossário de termos do projeto."""

import re

from posentinel.models import Issue, Severity, TranslationEntry
from posentinel.rules.base import BaseRule


class GlossaryRule(BaseRule):
    """Verifica se termos regulatórios/obrigatórios do msgid foram traduzidos conforme glossário."""

    code = "PO007"
    description = "Termo obrigatório do glossário não utilizado na tradução"
    default_severity = Severity.WARNING

    def __init__(self, glossary: dict[str, tuple[str, ...]] | None = None) -> None:
        self._glossary = glossary or {}
        # Pré-compila regex de busca para cada termo (com word boundaries quando aplicável)
        self._compiled_terms: list[tuple[str, re.Pattern[str], tuple[str, ...]]] = []
        for src_term, target_terms in self._glossary.items():
            pattern = re.compile(rf"\b{re.escape(src_term)}\b", re.IGNORECASE)
            self._compiled_terms.append((src_term, pattern, target_terms))

    def check(self, entry: TranslationEntry) -> list[Issue]:
        if entry.is_header or not self._compiled_terms:
            return []

        issues: list[Issue] = []
        for translation in entry.all_translations:
            if not translation:
                continue

            for src_term, pattern, approved_translations in self._compiled_terms:
                if pattern.search(entry.msgid):
                    # Verifica se ao menos uma das traduções aprovadas consta no msgstr
                    matched = any(
                        re.search(rf"\b{re.escape(appr)}\b", translation, re.IGNORECASE)
                        for appr in approved_translations
                    )
                    if not matched:
                        expected = " / ".join(f"'{a}'" for a in approved_translations)
                        message = (
                            f"Termo '{src_term}' requer a tradução oficial {expected} "
                            "conforme glossário do projeto."
                        )
                        suggestion = approved_translations[0] if approved_translations else None
                        issues.append(
                            self._issue(
                                entry,
                                message,
                                suggestion=suggestion,
                                translation=translation,
                            )
                        )
        return issues
