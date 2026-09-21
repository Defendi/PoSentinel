"""Adaptador que converte arquivos .po (via polib) em TranslationEntry imutáveis.

`polib` é um detalhe de implementação estritamente confinado a este módulo, conforme
ADR 001 (Clean Core). Nenhuma regra de negócio deve importar `polib` diretamente.
"""

from dataclasses import dataclass
from pathlib import Path

import polib

from posentinel.models import Issue, OdooMetadata, Severity, TranslationEntry


@dataclass(frozen=True, slots=True)
class ParseResult:
    """Resultado de uma tentativa de parsing de um arquivo .po."""

    entries: list[TranslationEntry]
    issues: list[Issue]


class PoParser:
    """Encapsula `polib` e mapeia arquivos .po para `TranslationEntry` imutáveis."""

    def parse_file(self, path: Path) -> ParseResult:
        if not path.is_file():
            raise FileNotFoundError(f"Arquivo não encontrado: {path}")

        try:
            pofile = self._load(path)
        except OSError as error:
            issue = Issue(
                code="SYS001",
                message=f"Falha de sintaxe ao ler o arquivo .po: {error}",
                severity=Severity.ERROR,
                line=None,
                msgid=None,
            )
            return ParseResult(entries=[], issues=[issue])

        entries = [self._to_entry(item) for item in pofile]
        return ParseResult(entries=entries, issues=[])

    def _load(self, path: Path) -> polib.POFile:
        try:
            return polib.pofile(str(path), encoding="utf-8")
        except UnicodeDecodeError:
            return polib.pofile(str(path), encoding="latin-1")

    def _to_entry(self, item: polib.POEntry) -> TranslationEntry:
        return TranslationEntry(
            msgid=item.msgid,
            msgstr=item.msgstr,
            msgid_plural=item.msgid_plural or None,
            msgstr_plural=dict(item.msgstr_plural),
            msgctxt=item.msgctxt,
            comments=tuple(item.comment.splitlines()) if item.comment else (),
            references=tuple(occurrence for occurrence, _ in item.occurrences),
            flags=tuple(item.flags),
            line=item.linenum,
            is_fuzzy="fuzzy" in item.flags,
            odoo_metadata=self._extract_odoo_metadata(item),
        )

    def _extract_odoo_metadata(self, item: polib.POEntry) -> OdooMetadata:
        module = self._extract_module(item.comment)
        model, term_type, field_name, xml_id = self._extract_model_reference(item.occurrences)
        return OdooMetadata(
            module=module,
            model=model,
            field_name=field_name,
            xml_id=xml_id,
            term_type=term_type,
        )

    def _extract_module(self, comment: str) -> str | None:
        if not comment:
            return None
        for line in comment.splitlines():
            if line.startswith("module:"):
                return line.split(":", 1)[1].strip()
        return None

    def _extract_model_reference(
        self, occurrences: list[tuple[str, str]]
    ) -> tuple[str | None, str | None, str | None, str | None]:
        for occurrence, _ in occurrences:
            if not occurrence.startswith("model:"):
                continue

            remainder = occurrence.removeprefix("model:")
            model_part, _, rest = remainder.partition(",")
            term_type_part, _, tail = rest.partition(":")

            model = model_part or None
            term_type = term_type_part or None
            field_name = tail if term_type == "field_description" else None
            xml_id = tail if term_type != "field_description" else None
            return model, term_type, field_name or None, xml_id or None

        return None, None, None, None
