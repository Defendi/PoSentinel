from posentinel.models.entry import Severity, TranslationEntry
from posentinel.models.issue import Issue
from posentinel.rules.base import BaseRule


class EmptyTranslationRule(BaseRule):
    """PO001: Identifica traduções vazias quando o termo original existe."""

    code = "PO001"
    description = "Tradução vazia para termo original preenchido"
    default_severity = Severity.WARNING

    def check(self, entry: TranslationEntry) -> list[Issue]:
        if entry.is_header:
            return []

        # Se msgid tem conteúdo mas msgstr está vazio ou apenas espaços
        if entry.msgid.strip() and not entry.msgstr.strip():
            return [
                Issue(
                    code=self.code,
                    message="Tradução está vazia",
                    severity=self.default_severity,
                    line=entry.line,
                    msgid=entry.msgid,
                    entry=entry,
                    odoo_context=entry.odoo_metadata.module,
                )
            ]
        return []
