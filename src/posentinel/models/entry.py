from dataclasses import dataclass, field
from enum import StrEnum


class Severity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class OdooMetadata:
    module: str | None = None
    model: str | None = None
    field_name: str | None = None
    xml_id: str | None = None
    term_type: str | None = None


@dataclass(frozen=True, slots=True)
class TranslationEntry:
    msgid: str
    msgstr: str
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
