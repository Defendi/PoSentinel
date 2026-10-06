from posentinel.ai.prompts import build_fix_prompt, build_generate_prompt
from posentinel.models import Issue, OdooMetadata, Severity, TranslationEntry


def test_build_generate_prompt() -> None:
    entry = TranslationEntry(
        msgid="Hello",
        msgstr="",
        odoo_metadata=OdooMetadata(module="sale", field_name="state"),
    )
    prompt = build_generate_prompt(entry, "en", "pt_BR")
    assert "Idioma original (en): Hello" in prompt
    assert "Módulo Odoo: sale" in prompt
    assert "Campo: state" in prompt
    assert "Traduza o texto de en para pt_BR" in prompt


def test_build_fix_prompt() -> None:
    entry = TranslationEntry(msgid="Hello", msgstr="Ola")
    issue = Issue(
        code="PO002", message="Missing placeholder", severity=Severity.ERROR, msgid="Hello", line=1
    )
    prompt = build_fix_prompt(entry, issue, "en", "pt_BR")
    assert "[PO002] Missing placeholder" in prompt
    assert "Original: Hello" in prompt
    assert "Tradução atual: Ola" in prompt
