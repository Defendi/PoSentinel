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
    file_module: str | None = None
    is_odoo_file: bool = False
    module_is_file_pattern: bool = False
    odoo_python_is_file_pattern: bool = False
    odoo_js_is_file_pattern: bool = False
    odoo_refs_is_file_pattern: bool = False


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
    def has_odoo_python(self) -> bool:
        return any(c == "odoo-python" or c.endswith("odoo-python") for c in self.comments)

    @property
    def has_odoo_javascript(self) -> bool:
        return any(c == "odoo-javascript" or c.endswith("odoo-javascript") for c in self.comments)

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

    @property
    def translation_pairs(self) -> list[tuple[str, str]]:
        """Retorna pares (msgid_correspondente, msgstr) para singular e plurais."""
        if self.msgstr_plural:
            pairs = []
            for idx, trans in sorted(self.msgstr_plural.items()):
                if not trans:
                    continue
                # No gettext/po padrão: forma 0 compara com msgid singular,
                # e forma > 0 com msgid_plural (se existir).
                orig = self.msgid if idx == 0 or not self.msgid_plural else self.msgid_plural
                pairs.append((orig, trans))
            return pairs
        if self.msgstr:
            return [(self.msgid, self.msgstr)]
        return []
