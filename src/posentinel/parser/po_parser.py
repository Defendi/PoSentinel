import re
from pathlib import Path
from typing import Any

import polib

from posentinel.models.entry import OdooMetadata, TranslationEntry


class PoParser:
    """Parser para arquivos .po com extração de metadados específicos do ecossistema Odoo."""

    _MODULE_RE = re.compile(r"module:\s*([\w_]+)", re.IGNORECASE)
    _MODEL_FIELD_RE = re.compile(r"model:([\w\.]+)(?:,\s*(\w+):([\w\.]+))?", re.IGNORECASE)

    def parse_file(self, file_path: str | Path) -> list[TranslationEntry]:
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

        po = polib.pofile(str(path), encoding="utf-8")
        entries: list[TranslationEntry] = []

        for item in po:
            odoo_meta = self._extract_odoo_metadata(item)
            entry = TranslationEntry(
                msgid=item.msgid,
                msgstr=item.msgstr,
                msgctxt=item.msgctxt or None,
                comments=tuple(item.comment.splitlines()) if item.comment else (),
                references=tuple(
                    f"{ref[0]}:{ref[1]}" if isinstance(ref, (list, tuple)) else str(ref)
                    for ref in item.occurrences
                ),
                flags=tuple(item.flags),
                line=getattr(item, "linenum", None),
                is_fuzzy=item.fuzzy,
                odoo_metadata=odoo_meta,
            )
            entries.append(entry)

        return entries

    def _extract_odoo_metadata(self, item: Any) -> OdooMetadata:
        module: str | None = None
        model: str | None = None
        field_name: str | None = None
        term_type: str | None = None
        xml_id: str | None = None

        # 1. Extrair module de comentários automáticos (tcomment: #. ...) ou comentários comuns (comment: # ...)
        all_comments = []
        if getattr(item, "tcomment", None):
            all_comments.extend(item.tcomment.splitlines())
        if getattr(item, "comment", None):
            all_comments.extend(item.comment.splitlines())

        for line in all_comments:
            line = line.strip()
            match = self._MODULE_RE.search(line)
            if match:
                module = match.group(1)
                break

        # 2. Extrair referências Odoo de occurrences ou flags
        # Exemplo Odoo: #: model:ir.model.fields,field_description:sale.field_res_partner__name
        for ref in getattr(item, "occurrences", []):
            ref_str = ref[0] if isinstance(ref, (list, tuple)) else str(ref)
            match = self._MODEL_FIELD_RE.search(ref_str)
            if match:
                model = match.group(1)
                term_type = match.group(2)
                field_name = match.group(3)
                break
            elif "." in ref_str and not ref_str.endswith(".py") and not ref_str.endswith(".xml"):
                xml_id = ref_str

        return OdooMetadata(
            module=module,
            model=model,
            field_name=field_name,
            xml_id=xml_id,
            term_type=term_type,
        )
