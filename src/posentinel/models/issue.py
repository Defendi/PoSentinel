"""Value object que representa um diagnóstico emitido por uma regra."""

from dataclasses import dataclass

from posentinel.models.entry import Severity


@dataclass(frozen=True, slots=True)
class Issue:
    """Diagnóstico leve e serializável.

    Não referencia a `TranslationEntry` de origem por decisão de design: o contexto
    necessário para o reporter é copiado para campos escalares na criação.
    """

    code: str
    message: str
    severity: Severity
    line: int | None
    msgid: str | None
    odoo_context: str | None = None
    suggestion: str | None = None
