"""Contrato base para as regras de validação de traduções."""

from abc import ABC, abstractmethod

from posentinel.models import Issue, Severity, TranslationEntry


class BaseRule(ABC):
    """Regra determinística que avalia uma `TranslationEntry` isoladamente."""

    code: str
    description: str
    default_severity: Severity

    @abstractmethod
    def check(self, entry: TranslationEntry) -> list[Issue]:
        """Avalia a entrada fornecida e retorna problemas encontrados."""
        ...

    def _issue(
        self,
        entry: TranslationEntry,
        message: str,
        *,
        severity: Severity | None = None,
        suggestion: str | None = None,
        translation: str | None = None,
    ) -> Issue:
        """Constrói uma Issue a partir dos atributos da regra e da entrada avaliada."""
        return Issue(
            code=self.code,
            message=message,
            severity=severity if severity is not None else self.default_severity,
            line=entry.line,
            msgid=entry.msgid,
            msgstr=translation if translation is not None else entry.msgstr,
            odoo_context=entry.odoo_metadata.module,
            suggestion=suggestion,
            references=entry.references,
            comments=entry.comments,
        )
