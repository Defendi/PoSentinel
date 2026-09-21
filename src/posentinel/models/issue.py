from dataclasses import dataclass

from posentinel.models.entry import Severity, TranslationEntry


@dataclass(frozen=True, slots=True)
class Issue:
    code: str
    message: str
    severity: Severity
    line: int | None
    msgid: str | None
    entry: TranslationEntry | None = None
    suggestion: str | None = None
    odoo_context: str | None = None
