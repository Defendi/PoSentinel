"""Implementação dos comandos determinísticos `lookup` e `set`."""

import difflib
import os
import re
import tempfile
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

import polib

from posentinel.models import Issue, Severity, TranslationEntry
from posentinel.parser.po_parser import PoParser
from posentinel.rules.base import BaseRule
from posentinel.rules.placeholders import (
    ExtraPlaceholderRule,
    InvalidPlaceholderRule,
    MissingPlaceholderRule,
)
from posentinel.rules.syntax import InvalidMarkupRule


class ScopeError(Exception):
    """Arquivo fora do escopo (Language diferente de pt_BR ou arquivo en_US.po)."""


class OperationalError(Exception):
    """Erro operacional ao processar arquivo .po (arquivo inválido, corrompido ou erro de I/O)."""


class AmbiguousContextError(Exception):
    """msgid encontrado em múltiplos contextos sem especificação de --context."""

    def __init__(self, contexts: list[str]) -> None:
        self.contexts = contexts
        super().__init__(f"msgid ambíguo entre múltiplos contextos: {', '.join(contexts)}")


class ViewResolutionError(Exception):
    """Não foi possível determinar o id da view QWeb a partir do arquivo XML."""

    def __init__(self, clean_path: str) -> None:
        self.clean_path = clean_path
        msg = (
            f"Não foi possível identificar o id da view em '{clean_path}'. "
            f"Informe o ID da view (--ref '{clean_path}:<id_da_view>') "
            f"ou o número da linha (--ref '{clean_path}:<linha>')."
        )
        super().__init__(msg)


def normalize_msgid(text: str) -> str:
    """Normaliza apenas quebras de linha (CRLF -> LF), preservando espaços e caixa."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def check_scope(path: Path) -> None:
    """Valida se o arquivo está no escopo (recusa se en_US.po ou Language != pt_BR)."""
    if path.name == "en_US.po":
        raise ScopeError("Arquivo 'en_US.po' está fora do escopo do PoSentinel.")

    if not path.is_file():
        return

    # Lê o header para inspecionar 'Language:'
    try:
        po = polib.pofile(str(path), encoding="utf-8")
    except Exception:
        try:
            po = polib.pofile(str(path), encoding="latin-1")
        except Exception:
            return

    lang = po.metadata.get("Language", "")
    if lang and lang.strip().replace("-", "_") != "pt_BR":
        raise ScopeError(f"Language '{lang}' está fora do escopo (esperado 'pt_BR').")


def entry_context(entry: TranslationEntry) -> str:
    """Retorna o contexto de uma entrada (msgctxt ou módulo Odoo ou vazio)."""
    return entry.msgctxt or entry.odoo_metadata.module or ""


def _validation_rules() -> list[BaseRule]:
    return [
        MissingPlaceholderRule(),
        InvalidPlaceholderRule(),
        ExtraPlaceholderRule(),
        InvalidMarkupRule(),
    ]


@dataclass(frozen=True, slots=True)
class LookupResult:
    msgid: str
    status: str  # "missing" | "empty" | "fuzzy" | "translated"
    entries: list[dict[str, object]]
    similar: list[dict[str, object]]


def execute_lookup(
    po_path: Path,
    msgid: str,
    context: str | None = None,
    similar_n: int = 5,
) -> LookupResult:
    check_scope(po_path)

    parser = PoParser()
    parse_result = parser.parse_file(po_path)

    if parse_result.issues:
        error_msgs = "; ".join(iss.message for iss in parse_result.issues)
        raise OperationalError(f"Arquivo inválido ou erro de sintaxe: {error_msgs}")

    norm_target = normalize_msgid(msgid)
    matched_entries: list[TranslationEntry] = []

    for entry in parse_result.entries:
        if entry.is_header:
            continue
        if normalize_msgid(entry.msgid) == norm_target:
            if context is not None:
                ctx = entry_context(entry)
                if ctx == context:
                    matched_entries.append(entry)
            else:
                matched_entries.append(entry)

    if not matched_entries and context is None:
        # Procurar se existe o msgid para verificar se houve ambiguidade
        all_for_msgid = [
            e
            for e in parse_result.entries
            if not e.is_header and normalize_msgid(e.msgid) == norm_target
        ]
        if len(all_for_msgid) > 1:
            contexts = sorted({entry_context(e) for e in all_for_msgid})
            raise AmbiguousContextError(contexts)
        matched_entries = all_for_msgid
    elif len(matched_entries) > 1 and context is None:
        contexts = sorted({entry_context(e) for e in matched_entries})
        raise AmbiguousContextError(contexts)

    # Buscar similares se similar_n > 0
    similar_list: list[dict[str, object]] = []
    if similar_n > 0:
        candidates: list[tuple[float, TranslationEntry]] = []
        for entry in parse_result.entries:
            if entry.is_header or normalize_msgid(entry.msgid) == norm_target:
                continue
            ratio = SequenceMatcher(None, norm_target, normalize_msgid(entry.msgid)).ratio()
            if ratio > 0.4:
                candidates.append((ratio, entry))
        candidates.sort(key=lambda x: x[0], reverse=True)
        for _, sim_entry in candidates[:similar_n]:
            similar_list.append(
                {
                    "msgid": sim_entry.msgid,
                    "msgstr": sim_entry.msgstr,
                    "line": sim_entry.line,
                }
            )

    if not matched_entries:
        return LookupResult(
            msgid=msgid,
            status="missing",
            entries=[],
            similar=similar_list,
        )

    target_entry = matched_entries[0]
    if target_entry.is_fuzzy:
        status = "fuzzy"
    elif not target_entry.msgstr and not any(target_entry.msgstr_plural.values()):
        status = "empty"
    else:
        status = "translated"

    # Rodar regras PO001-PO006 sobre a entrada encontrada
    from posentinel.cli.commands import _default_rules
    from posentinel.rules.engine import RulesEngine

    engine = RulesEngine(_default_rules())
    entry_issues = engine.analyze(target_entry)

    issue_dicts = [
        {
            "code": iss.code,
            "severity": iss.severity.value,
            "message": iss.message,
        }
        for iss in entry_issues
    ]

    entries_payload: list[dict[str, object]] = [
        {
            "line": target_entry.line,
            "context": entry_context(target_entry),
            "references": list(target_entry.references),
            "flags": list(target_entry.flags),
            "msgstr": target_entry.msgstr,
            "issues": issue_dicts,
        }
    ]

    return LookupResult(
        msgid=msgid,
        status=status,
        entries=entries_payload,
        similar=similar_list,
    )


@dataclass(frozen=True, slots=True)
class SetResult:
    action: str  # "created" | "updated" | "unchanged" | "refused"
    changed: bool
    line: int | None
    previous_msgstr: str
    msgstr: str
    warnings: list[str]
    reason: str | None = None
    diff: str | None = None


def execute_set(
    po_path: Path,
    msgid: str,
    msgstr: str,
    context: str | None = None,
    refs: list[str] | None = None,
    force: bool = False,
    dry_run: bool = False,
) -> SetResult:
    check_scope(po_path)

    if not po_path.is_file():
        raise FileNotFoundError(f"Arquivo não encontrado: {po_path}")

    norm_target = normalize_msgid(msgid)
    norm_new_msgstr = normalize_msgid(msgstr)

    if not norm_new_msgstr.strip():
        return SetResult(
            action="refused",
            changed=False,
            line=None,
            previous_msgstr="",
            msgstr=msgstr,
            warnings=["Tradução 'msgstr' vazia ou contendo apenas espaços não é permitida."],
            reason="empty_msgstr",
        )

    # 1. Validação prévia de integridade (PO002, PO003, PO004, PO005)
    dummy_entry = TranslationEntry(
        msgid=norm_target,
        msgstr=norm_new_msgstr,
    )

    validation_issues: list[Issue] = []
    for rule in _validation_rules():
        validation_issues.extend(rule.check(dummy_entry))

    errors = [iss for iss in validation_issues if iss.severity == Severity.ERROR]
    warnings = [iss.message for iss in validation_issues if iss.severity == Severity.WARNING]

    if errors:
        reason = "placeholder"
        for err in errors:
            if err.code == "PO003":
                reason = "placeholder"
        return SetResult(
            action="refused",
            changed=False,
            line=None,
            previous_msgstr="",
            msgstr=msgstr,
            warnings=[e.message for e in errors] + warnings,
            reason=reason,
        )

    # 2. Localiza a entrada no arquivo original com polib para obter metadados e linha
    po = polib.pofile(str(po_path), encoding="utf-8")
    matched_items: list[polib.POEntry] = []

    for item in po:
        if item.msgid == "" or getattr(item, "obsolete", False):
            continue
        if normalize_msgid(item.msgid) == norm_target:
            ctx = item.msgctxt or ""
            if not ctx and item.comment:
                for line in item.comment.splitlines():
                    if line.startswith("module:"):
                        ctx = line.split(":", 1)[1].strip()
                        break
            if context is not None:
                if ctx == context:
                    matched_items.append(item)
            else:
                matched_items.append(item)

    if len(matched_items) > 1 and context is None:
        contexts = sorted(
            {
                (
                    item.msgctxt
                    or next(
                        (
                            line_text.split(":", 1)[1].strip()
                            for line_text in (item.comment or "").splitlines()
                            if line_text.startswith("module:")
                        ),
                        "",
                    )
                )
                for item in matched_items
            }
        )
        raise AmbiguousContextError(contexts)

    orig_content = po_path.read_text(encoding="utf-8", errors="replace")
    # Detecta CRLF antes de normalizar ou decodificar em modo texto padrão
    has_crlf = b"\r\n" in po_path.read_bytes()

    if matched_items:
        item = matched_items[0]
        prev_msgstr = item.msgstr

        # Se já é igual:
        if prev_msgstr == norm_new_msgstr and "fuzzy" not in item.flags:
            return SetResult(
                action="unchanged",
                changed=False,
                line=item.linenum,
                previous_msgstr=prev_msgstr,
                msgstr=norm_new_msgstr,
                warnings=warnings,
            )

        # Se já está preenchida, é diferente e não tem force:
        if (
            prev_msgstr
            and prev_msgstr != norm_new_msgstr
            and "fuzzy" not in item.flags
            and not force
        ):
            return SetResult(
                action="refused",
                changed=False,
                line=item.linenum,
                previous_msgstr=prev_msgstr,
                msgstr=norm_new_msgstr,
                warnings=warnings,
                reason="already_translated",
            )

        # Alteração pontual preservando todo o resto do arquivo
        new_content = _replace_entry_in_po_text(
            orig_content=orig_content,
            target_msgid=norm_target,
            target_context=context,
            new_msgstr=norm_new_msgstr,
            remove_fuzzy=True,
        )
        action = "updated"
        line = item.linenum

    else:
        # Criação de nova entrada
        has_python_format = bool(
            re.search(r"%[sdiouxXeEfFgGcrsa]|%\([^)]+\)[sdiouxXeEfFgGcrsa]", norm_target)
        )
        try:
            inferred_context, inferred_refs, inferred_comments, inferred_warnings = (
                _infer_entry_metadata(
                    po=po,
                    context=context,
                    refs=refs,
                    python_format=has_python_format,
                    msgid=norm_target,
                    po_path=po_path,
                )
            )
        except ViewResolutionError as exc:
            return SetResult(
                action="refused",
                changed=False,
                line=None,
                previous_msgstr="",
                msgstr=norm_new_msgstr,
                warnings=[str(exc)],
                reason="view_not_found",
            )
        warnings.extend(inferred_warnings)

        new_entry_block = _format_new_entry(
            msgid=norm_target,
            msgstr=norm_new_msgstr,
            context=inferred_context,
            refs=inferred_refs,
            python_format=has_python_format,
            extracted_comments=inferred_comments,
        )

        new_content, line = _insert_new_entry_in_po_text(
            orig_content=orig_content,
            new_entry_block=new_entry_block,
            context=inferred_context,
        )
        action = "created"
        prev_msgstr = ""

    if has_crlf:
        # Garante que novas linhas inseridas ou modificadas mantenham CRLF
        new_content = new_content.replace("\r\n", "\n").replace("\n", "\r\n")

    # Gera diff unificado
    diff_lines = list(
        difflib.unified_diff(
            orig_content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=str(po_path),
            tofile=str(po_path),
        )
    )
    diff_text = "".join(diff_lines)

    if dry_run:
        return SetResult(
            action=action,
            changed=True,
            line=line,
            previous_msgstr=prev_msgstr,
            msgstr=norm_new_msgstr,
            warnings=warnings,
            diff=diff_text,
        )

    # Escrita atômica usando arquivo temporário no mesmo diretório
    _atomic_write(po_path, new_content)

    return SetResult(
        action=action,
        changed=True,
        line=line,
        previous_msgstr=prev_msgstr,
        msgstr=norm_new_msgstr,
        warnings=warnings,
        diff=diff_text,
    )


def _atomic_write(target_path: Path, content: str) -> None:
    if target_path.exists() and not os.access(target_path, os.W_OK):
        raise PermissionError(f"Arquivo é somente leitura: {target_path}")

    target_stat = target_path.stat() if target_path.exists() else None
    temp_dir = target_path.parent
    fd, temp_file = tempfile.mkstemp(prefix=".posentinel_tmp_", dir=temp_dir, text=True)
    try:
        with open(fd, "w", encoding="utf-8", newline="") as f:
            f.write(content)

        if target_stat is not None:
            os.chmod(temp_file, target_stat.st_mode)

        os.replace(temp_file, target_path)
    except Exception:
        if os.path.exists(temp_file):
            os.remove(temp_file)
        raise


def _escape_po(text: str) -> str:
    """Escapa quebras de linha e aspas para formato PO."""
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _format_msgstr_lines(text: str) -> str:
    if "\n" in text:
        lines = text.split("\n")
        formatted = ['msgstr ""\n']
        for i, line_item in enumerate(lines):
            terminator = "\\n" if i < len(lines) - 1 else ""
            escaped = _escape_po(line_item) + terminator
            formatted.append(f'"{escaped}"\n')
        return "".join(formatted)
    return f'msgstr "{_escape_po(text)}"\n'


def _is_qweb_path(path_str: str) -> bool:
    clean = path_str.strip().lstrip("/")
    low = clean.lower()
    if not low.endswith(".xml"):
        return False
    if "static/" in low:
        return False
    parts = low.split("/")
    return any(p in ("views", "report", "reports") for p in parts[:-1])


def _get_module_roots(po_path: Path | None, module_name: str | None) -> list[Path]:
    roots: list[Path] = []
    seen: set[str] = set()

    def add_root(p: Path) -> None:
        try:
            resolved = p.resolve()
            s = str(resolved)
            if s not in seen and resolved.is_dir():
                seen.add(s)
                roots.append(resolved)
        except Exception:
            pass

    if po_path:
        if po_path.parent.name == "i18n":
            add_root(po_path.parent.parent)
        add_root(po_path.parent)

    if module_name:
        add_root(Path.cwd() / module_name)
        add_root(Path.cwd() / "addons" / module_name)
        if po_path:
            base = po_path.parent.parent if po_path.parent.name == "i18n" else po_path.parent
            add_root(base / module_name)
            add_root(base.parent / module_name)

    add_root(Path.cwd())
    return roots


def _find_xml_file(
    file_path_str: str,
    po_path: Path | None = None,
    module_name: str | None = None,
) -> Path | None:
    clean = file_path_str.lstrip("/")

    # 1. Caminho direto relativo ao CWD ou absoluto
    direct_p = Path(clean)
    if direct_p.is_file():
        return direct_p

    # Remove prefixos comuns addons/<modulo>/ ou <modulo>/
    sub_paths = [clean]
    if clean.startswith("addons/"):
        parts = clean.split("/", 2)
        if len(parts) >= 3:
            sub_paths.append(parts[2])
    if module_name and clean.startswith(f"{module_name}/"):
        sub_paths.append(clean.split("/", 1)[1])

    roots = _get_module_roots(po_path, module_name)
    for root in roots:
        for sp in sub_paths:
            cand = root / sp
            if cand.is_file():
                return cand

        # Procura por nome de arquivo em views/ ou report/ ou reports/ dentro do módulo
        file_name = Path(clean).name
        for sub_dir in ("views", "report", "reports"):
            cand = root / sub_dir / file_name
            if cand.is_file():
                return cand

    return None


def _find_all_module_qweb_files(po_path: Path | None, module_name: str | None) -> list[Path]:
    roots = _get_module_roots(po_path, module_name)
    xml_files: list[Path] = []
    seen_files: set[str] = set()

    for root in roots:
        for sub_name in ("views", "report", "reports"):
            sub_dir = root / sub_name
            if sub_dir.is_dir():
                for f in sub_dir.rglob("*.xml"):
                    if _is_qweb_path(str(f)):
                        try:
                            res_path = f.resolve()
                            s = str(res_path)
                            if s not in seen_files and res_path.is_file():
                                seen_files.add(s)
                                xml_files.append(res_path)
                        except Exception:
                            pass
    return xml_files


def _extract_views_from_xml(xml_text: str) -> list[tuple[str, str]]:
    """Retorna lista de (view_id, block_text) para <template> ou <record model='ir.ui.view'>."""
    views: list[tuple[str, str]] = []

    try:
        import xml.etree.ElementTree as ET

        root = ET.fromstring(xml_text)
        for elem in root.iter():
            vid: str | None = None
            if elem.tag == "template" or (
                elem.tag == "record" and elem.attrib.get("model") == "ir.ui.view"
            ):
                vid = elem.attrib.get("id")

            if vid:
                text_parts = list(elem.itertext())
                for sub in elem.iter():
                    text_parts.extend(sub.attrib.values())
                views.append((vid, " ".join(text_parts)))
        if views:
            return views
    except Exception:
        pass

    template_block_re = re.compile(
        r'<template\s+[^>]*?id=["\']([^"\']+)["\'][^>]*?>([\s\S]*?)</template>',
        re.IGNORECASE,
    )
    for m in template_block_re.finditer(xml_text):
        views.append((m.group(1), m.group(2)))

    record_block_re = re.compile(
        r'<record\s+[^>]*?(?:id=["\'](?P<id1>[^"\']+)["\'][^>]*?model=["\']ir\.ui\.view["\']|model=["\']ir\.ui\.view["\'][^>]*?id=["\'](?P<id2>[^"\']+)["\'])[^>]*?>([\s\S]*?)</record>',
        re.IGNORECASE,
    )
    for m in record_block_re.finditer(xml_text):
        vid = m.group("id1") or m.group("id2")
        if vid:
            views.append((vid, m.group(3)))

    return views


def _view_contains_msgid(block_text: str, msgid: str) -> bool:
    if not msgid:
        return False
    if msgid in block_text:
        return True
    norm_msgid = " ".join(msgid.split())
    norm_block = " ".join(block_text.split())
    return norm_msgid in norm_block


def _find_view_id_by_line(xml_text: str, line_no: int) -> str | None:
    lines = xml_text.splitlines()
    if not (1 <= line_no <= len(lines)):
        return None

    target_idx = line_no - 1
    template_id_re = re.compile(r'<template\s+[^>]*?id=["\']([^"\']+)["\']', re.IGNORECASE)
    view_id_re = re.compile(
        r'<record\s+[^>]*?(?:id=["\']([^"\']+)["\'][^>]*?model=["\']ir\.ui\.view["\']|model=["\']ir\.ui\.view["\'][^>]*?id=["\']([^"\']+)["\'])',
        re.IGNORECASE,
    )

    for i in range(target_idx, -1, -1):
        line_str = lines[i].strip()
        if i < target_idx and (line_str.endswith("</template>") or line_str.endswith("</record>")):
            break

        if "<template" in lines[i]:
            chunk = "\n".join(lines[i : min(len(lines), i + 10)])
            m = template_id_re.search(chunk)
            if m:
                return m.group(1)
        if "<record" in lines[i]:
            chunk = "\n".join(lines[i : min(len(lines), i + 10)])
            if 'model="ir.ui.view"' in chunk or "model='ir.ui.view'" in chunk:
                m = view_id_re.search(chunk)
                if m:
                    return m.group(1) or m.group(2)

    return None


def _find_all_matching_views_in_xml_content(
    xml_text: str,
    msgid: str,
) -> list[str]:
    views = _extract_views_from_xml(xml_text)
    matching: list[str] = []
    for vid, block in views:
        if _view_contains_msgid(block, msgid) and vid not in matching:
            matching.append(vid)

    if (
        not matching
        and len(views) == 1
        and msgid
        and (msgid in xml_text or " ".join(msgid.split()) in " ".join(xml_text.split()))
    ):
        matching.append(views[0][0])

    return matching


def _find_view_id_in_xml_content(
    xml_text: str,
    msgid: str,
    line_no: int | None = None,
) -> str | None:
    """Busca o id do template QWeb ou view (ir.ui.view) que contém o msgid ou a linha indicada."""
    if line_no is not None:
        vid = _find_view_id_by_line(xml_text, line_no)
        if vid:
            return vid

    matching = _find_all_matching_views_in_xml_content(xml_text, msgid)
    if matching:
        return matching[0]

    return None


def _infer_entry_metadata(
    po: polib.POFile,
    context: str | None,
    refs: list[str] | None,
    python_format: bool,
    msgid: str = "",
    po_path: Path | None = None,
) -> tuple[str | None, list[str], list[str], list[str]]:
    valid_items = [it for it in po if it.msgid and not getattr(it, "obsolete", False)]

    # 1. Inferir contexto/módulo se não fornecido
    inferred_context = context
    modules: list[str] = []
    for it in valid_items:
        if it.comment:
            for line in it.comment.splitlines():
                if line.startswith("module:"):
                    mod = line.split(":", 1)[1].strip()
                    if mod:
                        modules.append(mod)
    if inferred_context is None and modules:
        from collections import Counter

        inferred_context = Counter(modules).most_common(1)[0][0]

    # 2. Inspecionar padrões de ocorrência existentes no arquivo
    existing_occurrences = [occ for it in valid_items for occ, _ in it.occurrences]
    has_code_addons_pattern = any(occ.startswith("code:addons/") for occ in existing_occurrences)
    has_code_pattern = any(occ.startswith("code:") for occ in existing_occurrences)
    has_odoo_ref_pattern = any(
        any(occ.startswith(prefix) for prefix in ("code:", "model:", "model_terms:"))
        for occ in existing_occurrences
    )
    has_odoo_ref_style = has_code_addons_pattern or has_code_pattern or has_odoo_ref_pattern

    existing_code_lines = [
        line for it in valid_items for occ, line in it.occurrences if occ.startswith("code:")
    ]
    all_zeros_line = bool(existing_code_lines) and all(
        line_val in ("0", 0, "") for line_val in existing_code_lines
    )

    # 3. Normalizar referências se houver, ou buscar no módulo se não houver
    normalized_refs: list[str] = []
    inferred_warnings: list[str] = []
    has_python_ref = False
    has_js_ref = False

    raw_refs = [r.strip() for r in (refs or []) if r.strip()]

    if not raw_refs:
        # Defeito 2: sem --ref, procurar o msgid nos .xml de views/, report/ e reports/ do módulo
        if inferred_context and msgid:
            qweb_files = _find_all_module_qweb_files(po_path, inferred_context)
            discovered_views: list[str] = []
            norm_msg = " ".join(msgid.split())
            for q_file in qweb_files:
                try:
                    xml_content = q_file.read_text(encoding="utf-8", errors="replace")
                    if msgid in xml_content or norm_msg in " ".join(xml_content.split()):
                        vids = _find_all_matching_views_in_xml_content(xml_content, msgid)
                        for v in vids:
                            if v not in discovered_views:
                                discovered_views.append(v)
                except Exception:
                    continue

            if len(discovered_views) == 1:
                vid = discovered_views[0]
                full_vid = vid if "." in vid else f"{inferred_context}.{vid}"
                normalized_refs.append(f"model_terms:ir.ui.view,arch_db:{full_vid}")
            elif len(discovered_views) > 1:
                for vid in discovered_views:
                    full_vid = vid if "." in vid else f"{inferred_context}.{vid}"
                    normalized_refs.append(f"model_terms:ir.ui.view,arch_db:{full_vid}")
            else:
                msg = (
                    f"Texto não localizado em views ou relatórios QWeb "
                    f"do módulo '{inferred_context}'."
                )
                inferred_warnings.append(msg)
    else:
        for r in raw_refs:
            r_was_code = False
            # Defeito 1: --ref com prefixo code: para arquivo QWeb
            if r.startswith("code:"):
                raw_path_and_line = r[5:]
                path_part, sep, tail = raw_path_and_line.rpartition(":")
                is_line = sep and (tail.isdigit() or not tail)
                check_path = path_part if is_line else raw_path_and_line

                if _is_qweb_path(check_path):
                    r = raw_path_and_line
                    r_was_code = True
                else:
                    if all_zeros_line:
                        path_part, sep, line_part = r.rpartition(":")
                        if sep and line_part.isdigit() and line_part != "0":
                            normalized_refs.append(f"{path_part}:0")
                        else:
                            normalized_refs.append(r)
                    else:
                        normalized_refs.append(r)
                    if ".py" in r:
                        has_python_ref = True
                    if ".js" in r:
                        has_js_ref = True
                    continue

            if any(r.startswith(prefix) for prefix in ("model:", "model_terms:")):
                normalized_refs.append(r)
                continue

            # Caminho sem prefixo Odoo
            path_part, sep, tail = r.rpartition(":")
            line_part = "0"
            view_id_from_tail: str | None = None
            line_no: int | None = None

            if sep:
                if tail.isdigit():
                    line_part = "0" if all_zeros_line else tail
                    line_no = int(tail)
                else:
                    view_id_from_tail = tail
            else:
                path_part = r

            clean_path = path_part.lstrip("/")
            is_qweb = _is_qweb_path(clean_path)

            if is_qweb and (has_odoo_ref_style or r_was_code):
                view_id = view_id_from_tail
                if not view_id:
                    xml_file = _find_xml_file(
                        clean_path, po_path=po_path, module_name=inferred_context
                    )
                    if xml_file:
                        try:
                            content = xml_file.read_text(encoding="utf-8", errors="replace")
                            view_id = _find_view_id_in_xml_content(
                                content, msgid=msgid, line_no=line_no
                            )
                        except Exception:
                            view_id = None

                # Defeito 3: nunca usar o nome do arquivo como id de view
                if not view_id:
                    raise ViewResolutionError(clean_path)

                module = inferred_context or ""
                if "." in view_id:
                    full_view_id = view_id
                elif module:
                    full_view_id = f"{module}.{view_id}"
                else:
                    full_view_id = view_id

                normalized_refs.append(f"model_terms:ir.ui.view,arch_db:{full_view_id}")
                continue

            # Arquivos de código Python / JS
            if clean_path.endswith(".py"):
                has_python_ref = True
            if clean_path.endswith(".js"):
                has_js_ref = True

            if has_code_addons_pattern:
                if clean_path.startswith("addons/"):
                    normalized_refs.append(f"code:{clean_path}:{line_part}")
                elif inferred_context and clean_path.startswith(f"{inferred_context}/"):
                    normalized_refs.append(f"code:addons/{clean_path}:{line_part}")
                elif inferred_context and not clean_path.startswith(f"{inferred_context}/"):
                    normalized_refs.append(
                        f"code:addons/{inferred_context}/{clean_path}:{line_part}"
                    )
                else:
                    normalized_refs.append(f"code:addons/{clean_path}:{line_part}")
            elif has_code_pattern:
                normalized_refs.append(f"code:{clean_path}:{line_part}")
            else:
                normalized_refs.append(f"{clean_path}:{line_part}" if sep else r)

    # 4. Inferir comentários extraídos (#.)
    inferred_comments: list[str] = []

    file_has_odoo_python = any(
        "odoo-python" in (it.comment or "").splitlines() for it in valid_items
    )
    file_has_odoo_javascript = any(
        "odoo-javascript" in (it.comment or "").splitlines() for it in valid_items
    )

    is_python = has_python_ref or (python_format and not normalized_refs)
    if is_python and file_has_odoo_python:
        inferred_comments.append("odoo-python")
    if has_js_ref and file_has_odoo_javascript:
        inferred_comments.append("odoo-javascript")

    return inferred_context, normalized_refs, inferred_comments, inferred_warnings


def _format_new_entry(
    msgid: str,
    msgstr: str,
    context: str | None,
    refs: list[str],
    python_format: bool,
    extracted_comments: list[str] | None = None,
) -> str:
    parts = ["\n"]
    if context:
        parts.append(f"#. module: {context}\n")
    if extracted_comments:
        for c in extracted_comments:
            if not c.startswith("module:"):
                parts.append(f"#. {c}\n")
    for r in refs:
        parts.append(f"#: {r}\n")
    if python_format:
        parts.append("#, python-format\n")

    if "\n" in msgid:
        lines = msgid.split("\n")
        parts.append('msgid ""\n')
        for i, line_item in enumerate(lines):
            terminator = "\\n" if i < len(lines) - 1 else ""
            parts.append(f'"{_escape_po(line_item)}{terminator}"\n')
    else:
        parts.append(f'msgid "{_escape_po(msgid)}"\n')

    parts.append(_format_msgstr_lines(msgstr))
    return "".join(parts)


def _insert_new_entry_in_po_text(
    orig_content: str,
    new_entry_block: str,
    context: str | None,
) -> tuple[str, int]:
    lines = orig_content.splitlines(keepends=True)
    if not orig_content.endswith("\n"):
        orig_content += "\n"
        lines.append("\n")

    # Tenta achar a última entrada com o mesmo módulo Odoo se houver contexto
    target_idx = len(lines)
    if context:
        marker = f"module: {context}"
        for i in range(len(lines) - 1, -1, -1):
            if marker in lines[i]:
                # Encontra o fim deste bloco de entrada
                for j in range(i, len(lines)):
                    if lines[j].strip().startswith("msgstr"):
                        # avança até a linha em branco subsequente
                        k = j + 1
                        while k < len(lines) and lines[k].strip().startswith('"'):
                            k += 1
                        target_idx = k
                        break
                break

    lines.insert(target_idx, new_entry_block)
    new_content = "".join(lines)
    line_number = len("".join(lines[:target_idx]).splitlines()) + 1
    return new_content, line_number


def _replace_entry_in_po_text(
    orig_content: str,
    target_msgid: str,
    target_context: str | None,
    new_msgstr: str,
    remove_fuzzy: bool,
) -> str:
    """Substitui cirurgicamente apenas as linhas do msgstr da entrada correspondente."""
    # Encontra as entradas via polib para obter os números de linha exatos
    po = polib.pofile(orig_content, encoding="utf-8")
    matched_entry = None
    for entry in po:
        if entry.msgid == "" or getattr(entry, "obsolete", False):
            continue
        if normalize_msgid(entry.msgid) == target_msgid:
            ctx = entry.msgctxt or ""
            if not ctx and entry.comment:
                for line in entry.comment.splitlines():
                    if line.startswith("module:"):
                        ctx = line.split(":", 1)[1].strip()
                        break
            if target_context is not None:
                if ctx == target_context:
                    matched_entry = entry
                    break
            else:
                matched_entry = entry
                break

    if not matched_entry:
        return orig_content

    # Mapeia linhas do arquivo de texto original
    lines = orig_content.splitlines(keepends=True)

    # Acha o trecho correspondente no arquivo
    # Procuramos msgid a partir de linenum aproximado
    start_idx = max(0, (matched_entry.linenum or 1) - 1)

    # Procura msgid exato
    msgid_idx = None
    for i in range(start_idx, min(len(lines), start_idx + 25)):
        if lines[i].startswith("msgid "):
            msgid_idx = i
            break
    if msgid_idx is None:
        # Busca no arquivo todo se o linenum variou
        for i in range(len(lines)):
            if lines[i].startswith("msgid ") and _unescape_chunk(lines, i) == target_msgid:
                msgid_idx = i
                break

    if msgid_idx is None:
        # Fallback para substituição limpa pelo polib
        matched_entry.msgstr = new_msgstr
        if remove_fuzzy and "fuzzy" in matched_entry.flags:
            matched_entry.flags.remove("fuzzy")
        return str(po)

    # Trata remoção de fuzzy se aplicável antes do msgid
    if remove_fuzzy:
        for f_idx in range(max(0, msgid_idx - 5), msgid_idx):
            if lines[f_idx].startswith("#,") and "fuzzy" in lines[f_idx]:
                raw_flags = [
                    fl.strip() for fl in lines[f_idx].removeprefix("#,").split(",") if fl.strip()
                ]
                remaining = [fl for fl in raw_flags if fl != "fuzzy"]
                if remaining:
                    lines[f_idx] = "#, " + ", ".join(remaining) + "\n"
                else:
                    lines[f_idx] = ""

    # Acha msgstr a partir de msgid_idx
    msgstr_idx = None
    for i in range(msgid_idx + 1, min(len(lines), msgid_idx + 20)):
        cur_line = lines[i]
        if (
            cur_line.startswith("msgstr ")
            or cur_line.startswith('msgstr""')
            or cur_line == 'msgstr ""\n'
        ):
            msgstr_idx = i
            break

    if msgstr_idx is None:
        return orig_content

    # Acha onde termina o msgstr (linhas subsequentes entre aspas)
    end_msgstr_idx = msgstr_idx + 1
    while end_msgstr_idx < len(lines) and lines[end_msgstr_idx].strip().startswith('"'):
        end_msgstr_idx += 1

    # Substitui exatamente a fatia do msgstr
    formatted_replacement = _format_msgstr_lines(new_msgstr)
    lines[msgstr_idx:end_msgstr_idx] = [formatted_replacement]

    return "".join(lines)


def _unescape_chunk(lines: list[str], start_i: int) -> str:
    content = []
    first = lines[start_i].removeprefix("msgid ").strip()
    if first.startswith('"') and first.endswith('"') and len(first) > 1:
        content.append(first[1:-1])
    i = start_i + 1
    while i < len(lines) and lines[i].strip().startswith('"'):
        line_clean = lines[i].strip()
        if line_clean.startswith('"') and line_clean.endswith('"'):
            content.append(line_clean[1:-1])
        i += 1
    joined = "".join(content)
    return joined.replace('\\"', '"').replace("\\n", "\n").replace("\\\\", "\\")
