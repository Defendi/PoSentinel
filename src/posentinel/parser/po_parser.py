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

    def parse_string(self, content: str) -> ParseResult:
        try:
            pofile = polib.pofile(content, encoding="utf-8")
        except Exception as error:
            issue = Issue(
                code="SYS001",
                message=f"Falha de sintaxe ao ler o conteúdo .po: {error}",
                severity=Severity.ERROR,
                line=None,
                msgid=None,
            )
            return ParseResult(entries=[], issues=[issue])

        (
            is_odoo_file,
            file_module,
            module_is_pattern,
            odoo_python_is_pattern,
            odoo_js_is_pattern,
            odoo_refs_is_pattern,
        ) = self._inspect_file_odoo_profile(pofile)
        entries = [
            self._to_entry(
                item,
                file_module=file_module,
                is_odoo_file=is_odoo_file,
                module_is_pattern=module_is_pattern,
                odoo_python_is_pattern=odoo_python_is_pattern,
                odoo_js_is_pattern=odoo_js_is_pattern,
                odoo_refs_is_pattern=odoo_refs_is_pattern,
            )
            for item in pofile
            if not getattr(item, "obsolete", False)
        ]
        return ParseResult(entries=entries, issues=[])

    def parse_file(self, path: Path) -> ParseResult:
        if not path.is_file():
            raise FileNotFoundError(f"Arquivo não encontrado: {path}")

        try:
            pofile = self._load(path)
        except Exception as error:
            issue = Issue(
                code="SYS001",
                message=f"Falha de sintaxe ao ler o arquivo .po: {error}",
                severity=Severity.ERROR,
                line=None,
                msgid=None,
            )
            return ParseResult(entries=[], issues=[issue])

        (
            is_odoo_file,
            file_module,
            module_is_pattern,
            odoo_python_is_pattern,
            odoo_js_is_pattern,
            odoo_refs_is_pattern,
        ) = self._inspect_file_odoo_profile(pofile)
        entries = [
            self._to_entry(
                item,
                file_module=file_module,
                is_odoo_file=is_odoo_file,
                module_is_pattern=module_is_pattern,
                odoo_python_is_pattern=odoo_python_is_pattern,
                odoo_js_is_pattern=odoo_js_is_pattern,
                odoo_refs_is_pattern=odoo_refs_is_pattern,
            )
            for item in pofile
            if not getattr(item, "obsolete", False)
        ]
        return ParseResult(entries=entries, issues=[])

    def _inspect_file_odoo_profile(
        self, pofile: polib.POFile
    ) -> tuple[bool, str | None, bool, bool, bool, bool]:
        module_counts: dict[str, int] = {}
        total_entries = 0
        python_entries_count = 0
        python_entries_with_odoo_python = 0
        js_entries_count = 0
        js_entries_with_odoo_js = 0
        total_refs = 0
        odoo_format_refs = 0

        for item in pofile:
            if item.msgid == "" or getattr(item, "obsolete", False):
                continue
            total_entries += 1

            has_py_comment = False
            has_js_comment = False
            if item.comment:
                for line in item.comment.splitlines():
                    line_clean = line.strip()
                    if line_clean.startswith("module:"):
                        mod = line_clean.split(":", 1)[1].strip()
                        if mod:
                            module_counts[mod] = module_counts.get(mod, 0) + 1
                    elif line_clean == "odoo-python":
                        has_py_comment = True
                    elif line_clean == "odoo-javascript":
                        has_js_comment = True

            is_py = (
                any(".py" in occ for occ, _ in item.occurrences) or "python-format" in item.flags
            )
            is_js = any(".js" in occ for occ, _ in item.occurrences)

            if is_py:
                python_entries_count += 1
                if has_py_comment:
                    python_entries_with_odoo_python += 1

            if is_js:
                js_entries_count += 1
                if has_js_comment:
                    js_entries_with_odoo_js += 1

            for occ, _ in item.occurrences:
                total_refs += 1
                if any(occ.startswith(prefix) for prefix in ("code:", "model:", "model_terms:")):
                    odoo_format_refs += 1

        project_id = pofile.metadata.get("Project-Id-Version", "")

        dominant_module = None
        module_is_pattern = False
        if module_counts and total_entries > 0:
            dominant_module, count = max(module_counts.items(), key=lambda x: x[1])
            if (count / total_entries >= 0.75) or ("Odoo" in project_id and count >= 1):
                module_is_pattern = True

        odoo_python_is_pattern = False
        if python_entries_count >= 1 and (
            python_entries_with_odoo_python / python_entries_count >= 0.75
        ):
            odoo_python_is_pattern = True

        odoo_js_is_pattern = False
        if js_entries_count >= 1 and (js_entries_with_odoo_js / js_entries_count >= 0.75):
            odoo_js_is_pattern = True

        odoo_refs_is_pattern = False
        if total_refs >= 1 and (odoo_format_refs / total_refs >= 0.75):
            odoo_refs_is_pattern = True

        is_odoo_file = (
            module_is_pattern
            or odoo_python_is_pattern
            or odoo_refs_is_pattern
            or ("Odoo" in project_id)
        )

        return (
            is_odoo_file,
            dominant_module,
            module_is_pattern,
            odoo_python_is_pattern,
            odoo_js_is_pattern,
            odoo_refs_is_pattern,
        )

    def _load(self, path: Path) -> polib.POFile:
        try:
            return polib.pofile(str(path), encoding="utf-8")
        except UnicodeDecodeError:
            return polib.pofile(str(path), encoding="latin-1")

    def _to_entry(
        self,
        item: polib.POEntry,
        file_module: str | None = None,
        is_odoo_file: bool = False,
        module_is_pattern: bool = False,
        odoo_python_is_pattern: bool = False,
        odoo_js_is_pattern: bool = False,
        odoo_refs_is_pattern: bool = False,
    ) -> TranslationEntry:
        return TranslationEntry(
            msgid=item.msgid,
            msgstr=item.msgstr,
            msgid_plural=item.msgid_plural or None,
            msgstr_plural=dict(item.msgstr_plural),
            msgctxt=item.msgctxt,
            comments=(
                *(item.comment.splitlines() if item.comment else ()),
                *(item.tcomment.splitlines() if getattr(item, "tcomment", None) else ()),
            ),
            references=tuple(occurrence for occurrence, _ in item.occurrences),
            flags=tuple(item.flags),
            line=item.linenum,
            is_fuzzy="fuzzy" in item.flags,
            odoo_metadata=self._extract_odoo_metadata(
                item,
                file_module=file_module,
                is_odoo_file=is_odoo_file,
                module_is_pattern=module_is_pattern,
                odoo_python_is_pattern=odoo_python_is_pattern,
                odoo_js_is_pattern=odoo_js_is_pattern,
                odoo_refs_is_pattern=odoo_refs_is_pattern,
            ),
        )

    def _extract_odoo_metadata(
        self,
        item: polib.POEntry,
        file_module: str | None = None,
        is_odoo_file: bool = False,
        module_is_pattern: bool = False,
        odoo_python_is_pattern: bool = False,
        odoo_js_is_pattern: bool = False,
        odoo_refs_is_pattern: bool = False,
    ) -> OdooMetadata:
        module = self._extract_module(item.comment)
        model, term_type, field_name, xml_id = self._extract_model_reference(item.occurrences)
        return OdooMetadata(
            module=module,
            model=model,
            field_name=field_name,
            xml_id=xml_id,
            term_type=term_type,
            file_module=file_module,
            is_odoo_file=is_odoo_file,
            module_is_file_pattern=module_is_pattern,
            odoo_python_is_file_pattern=odoo_python_is_pattern,
            odoo_js_is_file_pattern=odoo_js_is_pattern,
            odoo_refs_is_file_pattern=odoo_refs_is_pattern,
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
