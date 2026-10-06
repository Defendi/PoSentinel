from posentinel.models import Issue, TranslationEntry


def build_generate_prompt(
    entry: TranslationEntry, source_language: str, target_language: str
) -> str:
    """Prompt para gerar uma tradução do zero — usado quando a Issue é PO001 (msgstr vazio)."""
    context_lines = [f"Idioma original ({source_language}): {entry.msgid}"]
    if entry.odoo_metadata.module:
        context_lines.append(f"Módulo Odoo: {entry.odoo_metadata.module}")
    if entry.odoo_metadata.field_name:
        context_lines.append(f"Campo: {entry.odoo_metadata.field_name}")
    return (
        f"Traduza o texto de {source_language} para {target_language}, mantendo qualquer "
        f"placeholder (%s, %(name)s, {{var}}) e tag HTML/XML exatamente como no original.\n\n"
        + "\n".join(context_lines)
    )


def build_fix_prompt(
    entry: TranslationEntry, issue: Issue, source_language: str, target_language: str
) -> str:
    """Prompt para corrigir uma tradução existente com problema — usado para PO002-PO006."""
    return (
        f"A tradução abaixo de {source_language} para {target_language} tem um problema "
        f"detectado deterministicamente: [{issue.code}] {issue.message}\n\n"
        f"Original: {entry.msgid}\n"
        f"Tradução atual: {entry.msgstr}\n\n"
        "Corrija a tradução preservando o sentido, os placeholders e as tags do original."
    )
