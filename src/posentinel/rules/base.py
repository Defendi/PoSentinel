from abc import ABC, abstractmethod

from posentinel.models.entry import Severity, TranslationEntry
from posentinel.models.issue import Issue


class BaseRule(ABC):
    """Contrato base para todas as regras de qualidade do PoSentinel."""

    code: str
    description: str
    default_severity: Severity

    @abstractmethod
    def check(self, entry: TranslationEntry) -> list[Issue]:
        """Verifica a entrada de tradução e retorna as ocorrências identificadas."""
        ...
