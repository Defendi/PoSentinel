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


class TestQWebSetEnhancements:
    """Testes cobrindo os 3 defeitos resolvidos no posentinel set para referências QWeb."""

    def _setup_mut_module(self, tmp_path: Path) -> tuple[Path, Path]:
        module_dir = tmp_path / "mut_mover_renovar"
        i18n_dir = module_dir / "i18n"
        views_dir = module_dir / "views"
        i18n_dir.mkdir(parents=True)
        views_dir.mkdir(parents=True)

        po_file = i18n_dir / "pt_BR.po"
        _create_sample_odoo_po(po_file, module="mut_mover_renovar")

        xml_lines = ['<?xml version="1.0" encoding="utf-8"?>', "<odoo>"]
        while len(xml_lines) < 230:
            xml_lines.append("    <!-- padding line -->")
        xml_lines.extend(
            [
                '    <template id="qr_part_template">',
                "        <div>",
                "            <span>",
                "                Mover Program traceability record on Certificadora Mutualizo.",
                "            </span>",
                "        </div>",
                "    </template>",
                "</odoo>",
            ]
        )
        xml_file = views_dir / "mer_qr_part_template.xml"
        xml_file.write_text("\n".join(xml_lines), encoding="utf-8")

        return po_file, xml_file

    def test_cmd1_code_prefix_for_qweb_converts_to_model_terms(self, tmp_path: Path) -> None:
        """Defeito 1: --ref com code: para QWeb deve converter para model_terms e passar no scan."""
        po_file, _ = self._setup_mut_module(tmp_path)
        msgid = "Mover Program traceability record on Certificadora Mutualizo."

        res = runner.invoke(
            app,
            [
                "set",
                str(po_file),
                msgid,
                "Registro de rastreabilidade do Programa Mover na Certificadora Mutualizo.",
                "--ref",
                "code:addons/mut_mover_renovar/views/mer_qr_part_template.xml:238",
            ],
        )
        assert res.exit_code == 0
        content = po_file.read_text(encoding="utf-8")
        assert "#: model_terms:ir.ui.view,arch_db:mut_mover_renovar.qr_part_template\n" in content
        assert "#: code:" not in content.split(f'msgid "{msgid}"')[1].split("msgstr")[0]
        assert "odoo-python" not in content.split(f'msgid "{msgid}"')[0].split("#. module:")[-1]

        # Scan com --fail-on warning não pode ter PO008
        scan_res = runner.invoke(app, ["scan", str(po_file), "--fail-on", "warning"])
        assert scan_res.exit_code == 0
        assert "PASSED" in scan_res.stdout

    def test_cmd2_no_ref_discovers_single_qweb_view(self, tmp_path: Path) -> None:
        """Defeito 2: sem --ref, descobre a view QWeb no módulo e grava model_terms."""
        po_file, _ = self._setup_mut_module(tmp_path)
        msgid = "Mover Program traceability record on Certificadora Mutualizo."

        res = runner.invoke(
            app,
            [
                "set",
                str(po_file),
                msgid,
                "Registro de rastreabilidade do Programa Mover na Certificadora Mutualizo.",
                "--context",
                "mut_mover_renovar",
            ],
        )
        assert res.exit_code == 0
        content = po_file.read_text(encoding="utf-8")
        assert "#: model_terms:ir.ui.view,arch_db:mut_mover_renovar.qr_part_template\n" in content

        # Scan com --fail-on warning não pode ter PO008
        scan_res = runner.invoke(app, ["scan", str(po_file), "--fail-on", "warning"])
        assert scan_res.exit_code == 0
        assert "PASSED" in scan_res.stdout

    def test_cmd3_xml_path_without_line_resolves_via_msgid(self, tmp_path: Path) -> None:
        """Defeito 3: --ref sem linha acha o template pelo msgid e nunca usa nome do arquivo."""
        po_file, _ = self._setup_mut_module(tmp_path)
        msgid = "Mover Program traceability record on Certificadora Mutualizo."

        res = runner.invoke(
            app,
            [
                "set",
                str(po_file),
                msgid,
                "Registro de rastreabilidade do Programa Mover na Certificadora Mutualizo.",
                "--ref",
                "views/mer_qr_part_template.xml",
            ],
        )
        assert res.exit_code == 0
        content = po_file.read_text(encoding="utf-8")
        # Deve ter o id real qr_part_template e NUNCA mer_qr_part_template
        assert "#: model_terms:ir.ui.view,arch_db:mut_mover_renovar.qr_part_template\n" in content
        assert "mer_qr_part_template" not in content

        # Scan com --fail-on warning não pode ter PO008
        scan_res = runner.invoke(app, ["scan", str(po_file), "--fail-on", "warning"])
        assert scan_res.exit_code == 0
        assert "PASSED" in scan_res.stdout

    def test_qweb_view_resolution_fails_with_clear_error_when_not_found(
        self, tmp_path: Path
    ) -> None:
        """Defeito 3: quando a busca pelo msgid não acha a view, falha com exit code != 0."""
        po_file, _ = self._setup_mut_module(tmp_path)
        orig_content = po_file.read_text(encoding="utf-8")

        res = runner.invoke(
            app,
            [
                "set",
                str(po_file),
                "Texto Inexistente No XML",
                "Texto Traduzido",
                "--ref",
                "views/mer_qr_part_template.xml",
            ],
        )
        assert res.exit_code != 0
        assert po_file.read_text(encoding="utf-8") == orig_content
        assert (
            "Não foi possível identificar o id da view em 'views/mer_qr_part_template.xml'"
            in res.stdout
            or "view_not_found" in res.stdout
        )

    def test_text_in_two_qweb_views_generates_two_model_terms_lines(self, tmp_path: Path) -> None:
        """Caso 2 views: quando o texto está em duas views, gera uma linha #: por view."""
        module_dir = tmp_path / "mut_mover_renovar"
        i18n_dir = module_dir / "i18n"
        views_dir = module_dir / "views"
        i18n_dir.mkdir(parents=True)
        views_dir.mkdir(parents=True)

        po_file = i18n_dir / "pt_BR.po"
        _create_sample_odoo_po(po_file, module="mut_mover_renovar")

        xml_content = """<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <template id="first_view_template">
        <p>Texto presente em dois templates QWeb.</p>
    </template>
    <record id="second_view_record" model="ir.ui.view">
        <field name="name">Second View</field>
        <field name="arch" type="xml">
            <p>Texto presente em dois templates QWeb.</p>
        </field>
    </record>
</odoo>"""
        (views_dir / "multi_views.xml").write_text(xml_content, encoding="utf-8")

        res = runner.invoke(
            app,
            [
                "set",
                str(po_file),
                "Texto presente em dois templates QWeb.",
                "Texto traduzido em dois templates.",
                "--context",
                "mut_mover_renovar",
            ],
        )
        assert res.exit_code == 0
        content = po_file.read_text(encoding="utf-8")
        assert (
            "#: model_terms:ir.ui.view,arch_db:mut_mover_renovar.first_view_template\n" in content
        )
        assert "#: model_terms:ir.ui.view,arch_db:mut_mover_renovar.second_view_record\n" in content

    def test_static_owl_xml_remains_code_ref(self, tmp_path: Path) -> None:
        """Caso OWL: .xml em static/src/xml/ continua code: e não é convertido."""
        po_file = tmp_path / "pt_BR.po"
        _create_sample_odoo_po(po_file, module="mut_mover_renovar")

        res = runner.invoke(
            app,
            [
                "set",
                str(po_file),
                "OWL Template Button",
                "Botão do Template OWL",
                "--ref",
                "code:addons/mut_mover_renovar/static/src/xml/widget_view.xml:15",
            ],
        )
        assert res.exit_code == 0
        content = po_file.read_text(encoding="utf-8")
        assert "#: code:addons/mut_mover_renovar/static/src/xml/widget_view.xml:0\n" in content
        assert "model_terms:" not in content

    def test_python_code_ref_remains_code_and_odoo_python(self, tmp_path: Path) -> None:
        """Caso Python: código Python (code:...py) continua com code: e #. odoo-python."""
        po_file = tmp_path / "pt_BR.po"
        _create_sample_odoo_po(po_file, module="mut_mover_renovar")

        res = runner.invoke(
            app,
            [
                "set",
                str(po_file),
                "Validation Error from Python",
                "Erro de validação do Python",
                "--ref",
                "code:addons/mut_mover_renovar/models/sale_order.py:42",
            ],
        )
        assert res.exit_code == 0
        content = po_file.read_text(encoding="utf-8")
        assert "#: code:addons/mut_mover_renovar/models/sale_order.py:0\n" in content
        assert "#. odoo-python\n" in content
        assert "model_terms:" not in content

    def test_no_ref_text_not_found_in_qweb_emits_warning_and_keeps_no_ref(
        self, tmp_path: Path
    ) -> None:
        """Caso texto não achado: sem --ref, não inventa ref e emite aviso."""
        po_file, _ = self._setup_mut_module(tmp_path)
        msgid = "Texto Desconhecido Que Nao Existe No Modulo"

        res = runner.invoke(
            app,
            [
                "set",
                str(po_file),
                msgid,
                "Texto Desconhecido Traduzido",
                "--context",
                "mut_mover_renovar",
            ],
        )
        assert res.exit_code == 0
        content = po_file.read_text(encoding="utf-8")
        assert f'msgid "{msgid}"' in content
        assert 'msgstr "Texto Desconhecido Traduzido"' in content
        entry_block = content.split(f'msgid "{msgid}"')[0].split("#. module: mut_mover_renovar")[-1]
        assert "#:" not in entry_block
        assert "Aviso:           Texto não localizado em views ou relatórios QWeb" in res.stdout
