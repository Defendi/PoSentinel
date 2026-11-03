"""Regra PO008: conformidade de metadados e referências em arquivos do ecossistema Odoo."""

from posentinel.models import Issue, Severity, TranslationEntry
from posentinel.rules.base import BaseRule

_VALID_ODOO_REF_PREFIXES = ("code:", "model:", "model_terms:")


class OdooFormatRule(BaseRule):
    """Valida comentários extraídos (#.) e referências (#:) em arquivos do ecossistema Odoo."""

    code = "PO008"
    description = "Metadados ou referências fora do padrão Odoo"
    default_severity = Severity.WARNING

    def check(self, entry: TranslationEntry) -> list[Issue]:
        if entry.is_header:
            return []

        meta = entry.odoo_metadata
        is_odoo_context = meta.is_odoo_file or bool(meta.module)
        if not is_odoo_context:
            return []

        issues: list[Issue] = []

        # 1. '#. module:' ausente quando o arquivo tem padrão dominante de módulo
        if meta.module_is_file_pattern and meta.file_module and not meta.module:
            issues.append(
                self._issue(
                    entry,
                    f"Entrada sem comentário extraído '#. module: {meta.file_module}' "
                    f"divergindo do padrão das demais entradas do arquivo.",
                )
            )

        # 2. Formato de referências (#:)
        # Se as referências do arquivo seguem o padrão Odoo (code:, model:, model_terms:)
        # ou se a entrada tem módulo Odoo:
        if (meta.odoo_refs_is_file_pattern or bool(meta.module)) and entry.references:
            for ref in entry.references:
                if not any(ref.startswith(prefix) for prefix in _VALID_ODOO_REF_PREFIXES):
                    issues.append(
                        self._issue(
                            entry,
                            f"Referência '{ref}' diverge do padrão Odoo "
                            f"(esperado 'code:', 'model:' ou 'model_terms:').",
                        )
                    )

        # 3. Comentários extraídos de código (#. odoo-python, #. odoo-javascript)
        is_python_code = any(".py" in ref for ref in entry.references) or (
            entry.is_python_format and any(ref.startswith("code:") for ref in entry.references)
        )
        is_js_code = any(".js" in ref for ref in entry.references)

        should_check_python = meta.odoo_python_is_file_pattern or (
            (meta.is_odoo_file or bool(meta.module))
            and any(ref.startswith("code:") and ".py" in ref for ref in entry.references)
        )
        if is_python_code and should_check_python and not entry.has_odoo_python:
            issues.append(
                self._issue(
                    entry,
                    "Entrada de código Python sem comentário extraído '#. odoo-python' "
                    "(a tradução não será aplicada pelo Odoo).",
                )
            )

        should_check_js = meta.odoo_js_is_file_pattern or (
            (meta.is_odoo_file or bool(meta.module))
            and any(ref.startswith("code:") and ".js" in ref for ref in entry.references)
        )
        if is_js_code and should_check_js and not entry.has_odoo_javascript:
            issues.append(
                self._issue(
                    entry,
                    "Entrada de código JavaScript sem comentário extraído '#. odoo-javascript' "
                    "(a tradução não será aplicada pelo Odoo).",
                )
            )

        return issues
