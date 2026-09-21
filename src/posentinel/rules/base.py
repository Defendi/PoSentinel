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
