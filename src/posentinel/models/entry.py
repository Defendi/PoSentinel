"""Entidade de domínio que representa uma entrada de tradução normalizada."""

from dataclasses import dataclass, field
from enum import StrEnum


class Severity(StrEnum):
    """Severidade de um diagnóstico emitido por uma regra."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class OdooMetadata:
    """Contexto Odoo extraído dos comentários e referências de um arquivo .po."""

    module: str | None = None
    model: str | None = None
    field_name: str | None = None
    xml_id: str | None = None
    term_type: str | None = None


@dataclass(frozen=True, slots=True)
class TranslationEntry:
    """Entrada de tradução imutável, desacoplada de bibliotecas de parsing externas."""

    msgid: str
    msgstr: str = ""
    msgid_plural: str | None = None
    msgstr_plural: dict[int, str] = field(default_factory=dict)
    msgctxt: str | None = None
    comments: tuple[str, ...] = ()
    references: tuple[str, ...] = ()
    flags: tuple[str, ...] = ()
    line: int | None = None
    is_fuzzy: bool = False
    odoo_metadata: OdooMetadata = field(default_factory=OdooMetadata)

    @property
    def is_python_format(self) -> bool:
        return "python-format" in self.flags

    @property
    def is_header(self) -> bool:
        return self.msgid == ""

    @property
    def all_translations(self) -> list[str]:
        """Retorna todas as traduções associadas (singular ou plurais preenchidos)."""
        if self.msgstr_plural:
            return list(self.msgstr_plural.values())
        return [self.msgstr] if self.msgstr else []
