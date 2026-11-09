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


class TestQWebReferencesAndValidation:
    """Testes específicos para referências QWeb (model_terms), Python (code:) e validação PO008."""

    def test_qweb_set_generates_model_terms_reference(self, tmp_path: Path) -> None:
        """Caso 1: QWeb deve gerar model_terms e não deve ter odoo-python."""
        po_file = tmp_path / "pt_BR.po"
        _create_sample_odoo_po(po_file, module="mut_mover_renovar")

        res = runner.invoke(
            app,
            [
                "set",
                str(po_file),
                "Delivery Slip Title",
                "Título do Comprovante",
                "--ref",
                "report/report_mover.xml:report_deliveryslip_document",
                "--format",
                "json",
            ],
        )
        assert res.exit_code == 0
        content = po_file.read_text(encoding="utf-8")

        # Deve gerar model_terms e não deve gerar code: nem odoo-python
        expected_ref = (
            "#: model_terms:ir.ui.view,arch_db:mut_mover_renovar.report_deliveryslip_document\n"
        )
        assert expected_ref in content
        assert "#: code:" not in content.split('msgid "Delivery Slip Title"')[1].split("msgstr")[0]
        # Não pode ter odoo-python antes de Delivery Slip Title
        prefix_part = content.split('msgid "Delivery Slip Title"')[0]
        entry_part = prefix_part.split("#. module: mut_mover_renovar")[-1]
        assert "odoo-python" not in entry_part

    def test_qweb_set_extracts_id_from_xml_file_on_disk(self, tmp_path: Path) -> None:
        """QWeb extrai o view_id diretamente do arquivo XML quando existe em disco."""
        module_dir = tmp_path / "my_module"
        i18n_dir = module_dir / "i18n"
        views_dir = module_dir / "views"
        i18n_dir.mkdir(parents=True)
        views_dir.mkdir(parents=True)

        xml_file = views_dir / "my_report.xml"
        xml_file.write_text(
            """<odoo>
    <template id="custom_report_template">
        <div><span>Hello QWeb Report</span></div>
    </template>
</odoo>""",
            encoding="utf-8",
        )

        po_file = i18n_dir / "pt_BR.po"
        _create_sample_odoo_po(po_file, module="my_module")

        res = runner.invoke(
            app,
            [
                "set",
                str(po_file),
                "Hello QWeb Report",
                "Olá Relatório QWeb",
                "--ref",
                "views/my_report.xml:3",
                "--format",
                "json",
            ],
        )
        assert res.exit_code == 0
        content = po_file.read_text(encoding="utf-8")
        assert "#: model_terms:ir.ui.view,arch_db:my_module.custom_report_template\n" in content

    def test_python_code_continues_generating_code_ref_and_odoo_python(
        self, tmp_path: Path
    ) -> None:
        """Caso 2: Código Python continua gerando code: e comentário extraído odoo-python."""
        po_file = tmp_path / "pt_BR.po"
        _create_sample_odoo_po(po_file, module="mut_mover_renovar")

        res = runner.invoke(
            app,
            [
                "set",
                str(po_file),
                "Python calculation error",
                "Erro de cálculo Python",
                "--ref",
                "models/stock_move.py:55",
                "--format",
                "json",
            ],
        )
        assert res.exit_code == 0
        content = po_file.read_text(encoding="utf-8")
        assert "#: code:addons/mut_mover_renovar/models/stock_move.py:0\n" in content
        # Deve ter odoo-python
        assert "#. odoo-python\n" in content

    def test_text_in_two_places_generates_both_references(self, tmp_path: Path) -> None:
        """Caso 3: Um mesmo texto em dois lugares leva uma linha de referência por lugar."""
        po_file = tmp_path / "pt_BR.po"
        _create_sample_odoo_po(po_file, module="mut_mover_renovar")

        res = runner.invoke(
            app,
            [
                "set",
                str(po_file),
                "Shared Label",
                "Rótulo Compartilhado",
                "--ref",
                "models/sale_order.py:10",
                "--ref",
                "report/report_mover.xml:report_deliveryslip_document",
                "--format",
                "json",
            ],
        )
        assert res.exit_code == 0
        content = po_file.read_text(encoding="utf-8")

        assert "#: code:addons/mut_mover_renovar/models/sale_order.py:0\n" in content
        assert (
            "#: model_terms:ir.ui.view,arch_db:mut_mover_renovar.report_deliveryslip_document\n"
            in content
        )
        # Como tem Python, inclui odoo-python
        assert "#. odoo-python\n" in content

    def test_scan_warns_on_qweb_entry_with_code_ref(self, tmp_path: Path) -> None:
        """Scan falha com --fail-on warning se encontrar entrada QWeb com #: code:."""
        po_file = tmp_path / "pt_BR.po"
        content = (
            'msgid ""\n'
            'msgstr ""\n'
            '"Project-Id-Version: Odoo Server 17.0\\n"\n'
            '"Content-Type: text/plain; charset=UTF-8\\n"\n'
            '"Language: pt_BR\\n"\n'
            "\n"
            "#. module: mut_mover_renovar\n"
            "#: code:addons/mut_mover_renovar/report/report_mover.xml:0\n"
            'msgid "Corrupted QWeb Entry"\n'
            'msgstr "Entrada QWeb Corrompida"\n'
        )
        po_file.write_text(content, encoding="utf-8")

        res = runner.invoke(
            app,
            [
                "scan",
                str(po_file),
                "--fail-on",
                "warning",
                "--format",
                "json",
            ],
        )
        assert res.exit_code == 1
        data = json.loads(res.stdout)
        issues = data["results"][0]["issues"]
        qweb_issues = [
            i
            for i in issues
            if i["code"] == "PO008" and "Entrada QWeb com referência 'code:'" in i["message"]
        ]
        assert len(qweb_issues) == 1
        assert qweb_issues[0]["severity"] == "warning"

    def test_lookup_displays_warning_on_qweb_entry_with_code_ref(self, tmp_path: Path) -> None:
        """Lookup reporta o aviso PO008 quando consultado para entrada QWeb com #: code:."""
        po_file = tmp_path / "pt_BR.po"
        content = (
            'msgid ""\n'
            'msgstr ""\n'
            '"Project-Id-Version: Odoo Server 17.0\\n"\n'
            '"Content-Type: text/plain; charset=UTF-8\\n"\n'
            '"Language: pt_BR\\n"\n'
            "\n"
            "#. module: mut_mover_renovar\n"
            "#: code:addons/mut_mover_renovar/views/report_view.xml:0\n"
            'msgid "Corrupted QWeb Entry"\n'
            'msgstr "Entrada QWeb Corrompida"\n'
        )
        po_file.write_text(content, encoding="utf-8")

        res = runner.invoke(
            app,
            [
                "lookup",
                str(po_file),
                "Corrupted QWeb Entry",
                "--format",
                "json",
            ],
        )
        assert res.exit_code == 0  # está traduzida
        data = json.loads(res.stdout)
        issues = data["entries"][0]["issues"]
        assert any(
            iss["code"] == "PO008" and "Entrada QWeb com referência 'code:'" in iss["message"]
            for iss in issues
        )
