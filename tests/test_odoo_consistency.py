"""Testes de consistência de metadados e referências Odoo no `set` e `scan` (PST-19)."""

import json
from pathlib import Path

from typer.testing import CliRunner

from posentinel.cli.commands import app
from posentinel.models import OdooMetadata, Severity, TranslationEntry
from posentinel.rules.odoo import OdooFormatRule

runner = CliRunner()


def _create_sample_odoo_po(path: Path, module: str = "my_module") -> None:
    content = (
        'msgid ""\n'
        'msgstr ""\n'
        '"Project-Id-Version: Odoo Server 19.0\\n"\n'
        '"Content-Type: text/plain; charset=UTF-8\\n"\n'
        '"Language: pt_BR\\n"\n'
        "\n"
        f"#. module: {module}\n"
        "#. odoo-python\n"
        f"#: code:addons/{module}/controllers/main.py:0\n"
        "#, python-format\n"
        'msgid "Existing message %(name)s."\n'
        'msgstr "Mensagem existente %(name)s."\n'
        "\n"
        f"#. module: {module}\n"
        f"#: model:ir.model.fields,field_description:{module}.field_res_partner__title\n"
        'msgid "Title"\n'
        'msgstr "Título"\n'
    )
    path.write_text(content, encoding="utf-8")


def _create_sample_plain_po(path: Path) -> None:
    content = (
        'msgid ""\n'
        'msgstr ""\n'
        '"Project-Id-Version: Generic 1.0\\n"\n'
        '"Content-Type: text/plain; charset=UTF-8\\n"\n'
        '"Language: pt_BR\\n"\n'
        "\n"
        "#: src/main.py:10\n"
        'msgid "Hello %(name)s"\n'
        'msgstr "Olá %(name)s"\n'
    )
    path.write_text(content, encoding="utf-8")


class TestSetOdooInference:
    """Valida inferência de padrão das entradas vizinhas ao criar entrada via `set`."""

    def test_set_new_entry_infers_module_odoo_python_and_code_ref(self, tmp_path: Path) -> None:
        po_file = tmp_path / "pt_BR.po"
        _create_sample_odoo_po(po_file, module="my_module")

        res = runner.invoke(
            app,
            [
                "set",
                str(po_file),
                "Unknown slot '%(slot)s'.",
                "Slot '%(slot)s' desconhecido.",
                "--ref",
                "my_module/controllers/api.py:42",
                "--format",
                "json",
            ],
        )
        assert res.exit_code == 0
        content = po_file.read_text(encoding="utf-8")

        # Deve gravar #. module: my_module, #. odoo-python e #: code:addons/...:0
        assert "#. module: my_module\n" in content
        assert "#. odoo-python\n" in content
        assert "#: code:addons/my_module/controllers/api.py:0\n" in content
        assert "#, python-format\n" in content
        assert "msgid \"Unknown slot '%(slot)s'.\"\n" in content
        assert "msgstr \"Slot '%(slot)s' desconhecido.\"\n" in content

    def test_set_with_explicit_context_adds_odoo_python_for_code_ref(self, tmp_path: Path) -> None:
        po_file = tmp_path / "pt_BR.po"
        _create_sample_odoo_po(po_file, module="my_module")

        res = runner.invoke(
            app,
            [
                "set",
                str(po_file),
                "Unknown slot '%(slot)s'.",
                "Slot '%(slot)s' desconhecido.",
                "--context",
                "my_module",
                "--ref",
                "code:addons/my_module/controllers/api.py:0",
                "--format",
                "json",
            ],
        )
        assert res.exit_code == 0
        content = po_file.read_text(encoding="utf-8")

        assert "#. module: my_module\n" in content
        assert "#. odoo-python\n" in content
        assert "#: code:addons/my_module/controllers/api.py:0\n" in content

    def test_set_plain_po_without_comments_preserves_behavior(self, tmp_path: Path) -> None:
        po_file = tmp_path / "pt_BR.po"
        _create_sample_plain_po(po_file)

        res = runner.invoke(
            app,
            [
                "set",
                str(po_file),
                "New message %(count)d",
                "Nova mensagem %(count)d",
                "--ref",
                "src/utils.py:42",
                "--format",
                "json",
            ],
        )
        assert res.exit_code == 0
        content = po_file.read_text(encoding="utf-8")

        # Num arquivo genérico sem #., não deve injetar #. module nem #. odoo-python
        assert "#. module:" not in content
        assert "#. odoo-python" not in content
        assert "#: src/utils.py:42\n" in content


class TestOdooFormatRuleUnit:
    """Valida a regra PO008 isoladamente."""

    def test_flags_missing_module_in_odoo_file_pattern(self) -> None:
        rule = OdooFormatRule()
        entry = TranslationEntry(
            msgid="Hello",
            msgstr="Olá",
            line=10,
            odoo_metadata=OdooMetadata(
                module=None,
                file_module="my_module",
                is_odoo_file=True,
                module_is_file_pattern=True,
            ),
        )
        issues = rule.check(entry)
        assert len(issues) == 1
        assert issues[0].code == "PO008"
        assert issues[0].severity == Severity.WARNING
        assert "module: my_module" in issues[0].message

    def test_flags_invalid_reference_format_in_odoo_context(self) -> None:
        rule = OdooFormatRule()
        entry = TranslationEntry(
            msgid="Hello",
            msgstr="Olá",
            references=("my_module/controllers/api.py:42",),
            line=15,
            odoo_metadata=OdooMetadata(
                module="my_module",
                file_module="my_module",
                is_odoo_file=True,
                odoo_refs_is_file_pattern=True,
            ),
        )
        issues = rule.check(entry)
        codes = [i.code for i in issues]
        assert "PO008" in codes
        msg_ref = next(
            i.message
            for i in issues
            if "fora do formato Odoo" in i.message or "diverge do padrão" in i.message
        )
        assert "my_module/controllers/api.py:42" in msg_ref

    def test_flags_missing_odoo_python_comment_for_python_code(self) -> None:
        rule = OdooFormatRule()
        entry = TranslationEntry(
            msgid="Hello %(name)s",
            msgstr="Olá %(name)s",
            flags=("python-format",),
            references=("code:addons/my_module/controllers/api.py:0",),
            comments=("module: my_module",),
            line=20,
            odoo_metadata=OdooMetadata(
                module="my_module",
                file_module="my_module",
                is_odoo_file=True,
                odoo_python_is_file_pattern=True,
            ),
        )
        issues = rule.check(entry)
        assert any("odoo-python" in i.message for i in issues)

    def test_passes_valid_odoo_python_entry(self) -> None:
        rule = OdooFormatRule()
        entry = TranslationEntry(
            msgid="Hello %(name)s",
            msgstr="Olá %(name)s",
            flags=("python-format",),
            references=("code:addons/my_module/controllers/api.py:0",),
            comments=("module: my_module", "odoo-python"),
            line=20,
            odoo_metadata=OdooMetadata(
                module="my_module",
                file_module="my_module",
                is_odoo_file=True,
                module_is_file_pattern=True,
                odoo_python_is_file_pattern=True,
                odoo_refs_is_file_pattern=True,
            ),
        )
        issues = rule.check(entry)
        assert len(issues) == 0


class TestScanBaselineOdooConsistency:
    """Valida o comportamento de `scan --baseline --fail-on warning` nos critérios de aceite."""

    def test_scan_baseline_fails_on_warning_for_0_7_4_entries(self, tmp_path: Path) -> None:
        baseline_file = tmp_path / "baseline.po"
        _create_sample_odoo_po(baseline_file, module="my_module")

        # Arquivo com as duas entradas geradas pela versão 0.7.4:
        # 1) caminho simples sem #. module e sem #. odoo-python
        # 2) --context com #. module mas sem #. odoo-python
        target_file = tmp_path / "target.po"
        content = baseline_file.read_text(encoding="utf-8")
        content += (
            "\n"
            "#: my_module/controllers/api.py:42\n"
            "#, python-format\n"
            'msgid "Slot one %(slot)s."\n'
            'msgstr "Slot um %(slot)s."\n'
            "\n"
            "#. module: my_module\n"
            "#: code:addons/my_module/controllers/api.py:0\n"
            "#, python-format\n"
            'msgid "Slot two %(slot)s."\n'
            'msgstr "Slot dois %(slot)s."\n'
        )
        target_file.write_text(content, encoding="utf-8")

        res = runner.invoke(
            app,
            [
                "scan",
                str(target_file),
                "--baseline",
                str(baseline_file),
                "--fail-on",
                "warning",
                "--format",
                "json",
            ],
        )
        # O scan com --fail-on warning deve sair com código diferente de 0
        assert res.exit_code != 0
        data = json.loads(res.stdout)
        file_issues = data["results"][0]["issues"]
        # Ambas as entradas devem ser acusadas
        slot1_issues = [i for i in file_issues if i["msgid"] == "Slot one %(slot)s."]
        slot2_issues = [i for i in file_issues if i["msgid"] == "Slot two %(slot)s."]
        assert len(slot1_issues) > 0
        assert len(slot2_issues) > 0

    def test_scan_clean_odoo_exported_po_has_zero_warnings(self, tmp_path: Path) -> None:
        po_file = tmp_path / "odoo_exported.po"
        _create_sample_odoo_po(po_file, module="my_module")

        res = runner.invoke(
            app,
            [
                "scan",
                str(po_file),
                "--fail-on",
                "warning",
            ],
        )
        assert res.exit_code == 0
        assert "PASSED — 0 erro(s), 0 aviso(s)" in res.stdout
