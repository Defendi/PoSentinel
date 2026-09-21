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
        self, entry: TranslationEntry, message: str, *, suggestion: str | None = None
    ) -> Issue:
        """Constrói uma Issue a partir dos atributos da regra e da entrada avaliada."""
        return Issue(
            code=self.code,
            message=message,
            severity=self.default_severity,
            line=entry.line,
            msgid=entry.msgid,
            odoo_context=entry.odoo_metadata.module,
            suggestion=suggestion,
        )
