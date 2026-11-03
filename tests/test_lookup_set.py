"""Testes completos cobrindo os 22 casos de teste especificados para `lookup` e `set`."""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from posentinel.cli.commands import app

runner = CliRunner()


def _create_sample_po(path: Path, lang: str = "pt_BR") -> None:
    content = (
        'msgid ""\n'
        'msgstr ""\n'
        f'"Language: {lang}\\n"\n'
        '"Content-Type: text/plain; charset=UTF-8\\n"\n'
        "\n"
        "#. module: account\n"
        "#: models/account.py:10\n"
        'msgid "Invoice %s"\n'
        'msgstr "Fatura %s"\n'
        "\n"
        "#. module: stock\n"
        "#: models/stock.py:20\n"
        'msgid "Empty entry"\n'
        'msgstr ""\n'
        "\n"
        "#. module: sale\n"
        "#, fuzzy\n"
        'msgid "Fuzzy entry"\n'
        'msgstr "Entrada aproximada"\n'
        "\n"
        "#. module: crm\n"
        "#: models/crm.py:30\n"
        'msgid "Ambiguous msgid"\n'
        'msgstr "Ambíguo CRM"\n'
        "\n"
        "#. module: helpdesk\n"
        "#: models/helpdesk.py:40\n"
        'msgid "Ambiguous msgid"\n'
        'msgstr "Ambíguo Helpdesk"\n'
        "\n"
        'msgid "Multi\\nline\\ntext"\n'
        'msgstr "Multi\\nlinha\\ntexto"\n'
    )
    path.write_text(content, encoding="utf-8")


class TestLookupAndSetCases:
    # 1. lookup de msgid inexistente -> missing, exit 1
    def test_case_01_lookup_missing_msgid(self, tmp_path: Path) -> None:
        po_file = tmp_path / "pt_BR.po"
        _create_sample_po(po_file)

        res = runner.invoke(app, ["lookup", str(po_file), "Non existent", "--format", "json"])
        assert res.exit_code == 1
        data = json.loads(res.stdout)
        assert data["status"] == "missing"
        assert data["entries"] == []

    # 2. lookup de entrada com msgstr vazio -> empty, exit 1
    def test_case_02_lookup_empty_entry(self, tmp_path: Path) -> None:
        po_file = tmp_path / "pt_BR.po"
        _create_sample_po(po_file)

        res = runner.invoke(app, ["lookup", str(po_file), "Empty entry", "--format", "json"])
        assert res.exit_code == 1
        data = json.loads(res.stdout)
        assert data["status"] == "empty"
        assert len(data["entries"]) == 1

    # 3. lookup de entrada fuzzy -> fuzzy, exit 1
    def test_case_03_lookup_fuzzy_entry(self, tmp_path: Path) -> None:
        po_file = tmp_path / "pt_BR.po"
        _create_sample_po(po_file)

        res = runner.invoke(app, ["lookup", str(po_file), "Fuzzy entry", "--format", "json"])
        assert res.exit_code == 1
        data = json.loads(res.stdout)
        assert data["status"] == "fuzzy"

    # 4. lookup de entrada preenchida -> translated, exit 0, traz msgstr e line
    def test_case_04_lookup_translated_entry(self, tmp_path: Path) -> None:
        po_file = tmp_path / "pt_BR.po"
        _create_sample_po(po_file)

        res = runner.invoke(app, ["lookup", str(po_file), "Invoice %s", "--format", "json"])
        assert res.exit_code == 0
        data = json.loads(res.stdout)
        assert data["status"] == "translated"
        assert data["entries"][0]["msgstr"] == "Fatura %s"
        assert isinstance(data["entries"][0]["line"], int)

    # 5. lookup com msgid em dois contextos, sem --context -> exit 3
    def test_case_05_lookup_ambiguous_contexts(self, tmp_path: Path) -> None:
        po_file = tmp_path / "pt_BR.po"
        _create_sample_po(po_file)

        res = runner.invoke(app, ["lookup", str(po_file), "Ambiguous msgid"])
        assert res.exit_code == 3
        assert "ambíguo" in res.stderr

    # 6. lookup --similar -> devolve parecidas com msgstr
    def test_case_06_lookup_similar(self, tmp_path: Path) -> None:
        po_file = tmp_path / "pt_BR.po"
        _create_sample_po(po_file)

        res = runner.invoke(
            app, ["lookup", str(po_file), "Invoice %d", "--similar", "3", "--format", "json"]
        )
        data = json.loads(res.stdout)
        assert len(data["similar"]) > 0
        assert data["similar"][0]["msgid"] == "Invoice %s"

    # 7. set em entrada vazia -> grava, updated, diff só da entrada
    def test_case_07_set_in_empty_entry(self, tmp_path: Path) -> None:
        po_file = tmp_path / "pt_BR.po"
        _create_sample_po(po_file)

        res = runner.invoke(
            app, ["set", str(po_file), "Empty entry", "Entrada preenchida", "--format", "json"]
        )
        assert res.exit_code == 0
        data = json.loads(res.stdout)
        assert data["action"] == "updated"
        assert data["changed"] is True
        assert 'msgstr "Entrada preenchida"' in po_file.read_text(encoding="utf-8")

    # 8. set em entrada fuzzy -> grava e remove fuzzy, mantém python-format se houver
    def test_case_08_set_fuzzy_removes_fuzzy_flag(self, tmp_path: Path) -> None:
        po_file = tmp_path / "pt_BR.po"
        _create_sample_po(po_file)

        res = runner.invoke(
            app, ["set", str(po_file), "Fuzzy entry", "Entrada revisada", "--format", "json"]
        )
        assert res.exit_code == 0
        data = json.loads(res.stdout)
        assert data["action"] == "updated"
        content = po_file.read_text(encoding="utf-8")
        assert "Entrada revisada" in content
        assert "fuzzy" not in content

    # 9. set em entrada preenchida e diferente, sem --force -> refused, arquivo intacto
    def test_case_09_set_already_translated_without_force(self, tmp_path: Path) -> None:
        po_file = tmp_path / "pt_BR.po"
        _create_sample_po(po_file)
        orig_content = po_file.read_text(encoding="utf-8")

        res = runner.invoke(app, ["set", str(po_file), "Invoice %s", "Novo %s", "--format", "json"])
        assert res.exit_code == 1
        data = json.loads(res.stdout)
        assert data["action"] == "refused"
        assert data["reason"] == "already_translated"
        assert po_file.read_text(encoding="utf-8") == orig_content

    # 10. mesmo com --force -> grava
    def test_case_10_set_already_translated_with_force(self, tmp_path: Path) -> None:
        po_file = tmp_path / "pt_BR.po"
        _create_sample_po(po_file)

        res = runner.invoke(
            app, ["set", str(po_file), "Invoice %s", "Novo %s", "--force", "--format", "json"]
        )
        assert res.exit_code == 0
        data = json.loads(res.stdout)
        assert data["action"] == "updated"
        assert 'msgstr "Novo %s"' in po_file.read_text(encoding="utf-8")

    # 11. set com o mesmo msgstr -> unchanged, exit 0, arquivo intacto
    def test_case_11_set_same_msgstr_unchanged(self, tmp_path: Path) -> None:
        po_file = tmp_path / "pt_BR.po"
        _create_sample_po(po_file)
        orig_content = po_file.read_text(encoding="utf-8")

        res = runner.invoke(
            app, ["set", str(po_file), "Invoice %s", "Fatura %s", "--format", "json"]
        )
        assert res.exit_code == 0
        data = json.loads(res.stdout)
        assert data["action"] == "unchanged"
        assert data["changed"] is False
        assert po_file.read_text(encoding="utf-8") == orig_content

    # 12. set de msgid novo com %s -> created, com #, python-format
    def test_case_12_set_new_msgid_creates_with_python_format(self, tmp_path: Path) -> None:
        po_file = tmp_path / "pt_BR.po"
        _create_sample_po(po_file)

        res = runner.invoke(
            app, ["set", str(po_file), "New item %s", "Novo item %s", "--format", "json"]
        )
        assert res.exit_code == 0
        data = json.loads(res.stdout)
        assert data["action"] == "created"
        content = po_file.read_text(encoding="utf-8")
        assert "#, python-format" in content
        assert 'msgid "New item %s"' in content

    # 13. set de msgid novo com --ref -> linha #: presente
    def test_case_13_set_new_msgid_with_references(self, tmp_path: Path) -> None:
        po_file = tmp_path / "pt_BR.po"
        _create_sample_po(po_file)

        res = runner.invoke(
            app,
            [
                "set",
                str(po_file),
                "Brand new string",
                "Texto novinho",
                "--ref",
                "models/foo.py:12",
                "--ref",
                "views/foo.xml:45",
                "--format",
                "json",
            ],
        )
        assert res.exit_code == 0
        content = po_file.read_text(encoding="utf-8")
        assert "#: models/foo.py:12" in content
        assert "#: views/foo.xml:45" in content

    # 14. set com %s removido -> refused, placeholder, arquivo intacto
    def test_case_14_set_missing_placeholder_refused(self, tmp_path: Path) -> None:
        po_file = tmp_path / "pt_BR.po"
        _create_sample_po(po_file)
        orig_content = po_file.read_text(encoding="utf-8")

        res = runner.invoke(app, ["set", str(po_file), "Invoice %s", "Fatura", "--format", "json"])
        assert res.exit_code == 1
        data = json.loads(res.stdout)
        assert data["action"] == "refused"
        assert data["reason"] == "placeholder"
        assert po_file.read_text(encoding="utf-8") == orig_content

    # 15. set com %(batch)s virado %(lote)s -> refused
    def test_case_15_set_translated_named_placeholder_refused(self, tmp_path: Path) -> None:
        po_file = tmp_path / "pt_BR.po"
        _create_sample_po(po_file)

        res = runner.invoke(
            app, ["set", str(po_file), "Batch %(batch)s", "Lote %(lote)s", "--format", "json"]
        )
        assert res.exit_code == 1
        data = json.loads(res.stdout)
        assert data["action"] == "refused"
        assert data["reason"] == "placeholder"

    # 16. set com %s a mais -> refused
    def test_case_16_set_extra_placeholder_refused(self, tmp_path: Path) -> None:
        po_file = tmp_path / "pt_BR.po"
        _create_sample_po(po_file)

        res = runner.invoke(app, ["set", str(po_file), "Invoice", "Fatura %s", "--format", "json"])
        assert res.exit_code == 1
        data = json.loads(res.stdout)
        assert data["action"] == "refused"

    # 17. set com tag desbalanceada -> grava, com aviso PO005
    def test_case_17_set_unbalanced_tag_saves_with_warning(self, tmp_path: Path) -> None:
        po_file = tmp_path / "pt_BR.po"
        _create_sample_po(po_file)

        res = runner.invoke(
            app,
            [
                "set",
                str(po_file),
                "Tag <b>test</b>",
                "Tag <b>teste",
                "--format",
                "json",
            ],
        )
        assert res.exit_code == 0
        data = json.loads(res.stdout)
        assert data["action"] == "created"
        assert len(data["warnings"]) > 0

    # 18. set --dry-run -> mostra diff, arquivo intacto
    def test_case_18_set_dry_run_shows_diff_intact(self, tmp_path: Path) -> None:
        po_file = tmp_path / "pt_BR.po"
        _create_sample_po(po_file)
        orig_content = po_file.read_text(encoding="utf-8")

        res = runner.invoke(
            app,
            [
                "set",
                str(po_file),
                "Empty entry",
                "Entrada preenchida",
                "--dry-run",
                "--format",
                "json",
            ],
        )
        assert res.exit_code == 0
        data = json.loads(res.stdout)
        assert "diff" in data
        assert po_file.read_text(encoding="utf-8") == orig_content

    # 19. set em en_US.po -> exit 4, arquivo intacto
    def test_case_19_set_refuses_en_us_file(self, tmp_path: Path) -> None:
        po_file = tmp_path / "en_US.po"
        _create_sample_po(po_file, lang="en_US")
        orig_content = po_file.read_text(encoding="utf-8")

        res = runner.invoke(app, ["set", str(po_file), "Hello", "Olá"])
        assert res.exit_code == 4
        assert po_file.read_text(encoding="utf-8") == orig_content

    # 20. diff completo antes/depois de um set -> só as linhas da entrada alterada
    def test_case_20_set_minimal_diff_only_affected_entry(self, tmp_path: Path) -> None:
        po_file = tmp_path / "pt_BR.po"
        _create_sample_po(po_file)

        res = runner.invoke(
            app,
            [
                "set",
                str(po_file),
                "Empty entry",
                "Entrada isolada",
                "--dry-run",
                "--format",
                "json",
            ],
        )
        data = json.loads(res.stdout)
        diff = data["diff"]
        # Garante que nenhuma outra entrada (como "Invoice %s") foi tocada no diff
        assert "Invoice" not in diff
        assert "Entrada isolada" in diff

    # 21. set com falha simulada na escrita -> arquivo original preservado
    def test_case_21_atomic_write_preserves_on_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        po_file = tmp_path / "pt_BR.po"
        _create_sample_po(po_file)
        orig_content = po_file.read_text(encoding="utf-8")

        import posentinel.cli.lookup_set as ls_mod

        def _broken_replace(_src: Path, _dst: Path) -> None:
            raise OSError("Falha proposital de I/O na gravação atômica")

        monkeypatch.setattr(ls_mod.os, "replace", _broken_replace)

        res = runner.invoke(app, ["set", str(po_file), "Empty entry", "Falha teste"])
        assert res.exit_code == 2
        assert po_file.read_text(encoding="utf-8") == orig_content

    # 22. msgid multilinha -> encontrado e gravado sem mudar o escape das demais
    def test_case_22_multiline_msgid(self, tmp_path: Path) -> None:
        po_file = tmp_path / "pt_BR.po"
        _create_sample_po(po_file)

        # Lookup em multilinha
        multiline_msgid = "Multi\nline\ntext"
        lookup_res = runner.invoke(
            app, ["lookup", str(po_file), multiline_msgid, "--format", "json"]
        )
        assert lookup_res.exit_code == 0
        data = json.loads(lookup_res.stdout)
        assert data["status"] == "translated"

        # Set com force em multilinha
        set_res = runner.invoke(
            app,
            [
                "set",
                str(po_file),
                multiline_msgid,
                "Multi\nlinha\nnova",
                "--force",
                "--format",
                "json",
            ],
        )
        assert set_res.exit_code == 0
        content = po_file.read_text(encoding="utf-8")
        assert 'msgstr ""\n"Multi\\n"\n"linha\\n"\n"nova"\n' in content

    # 23. Bug 1: CRLF original é preservado após set
    def test_case_23_crlf_line_endings_preserved(self, tmp_path: Path) -> None:
        po_file = tmp_path / "pt_BR.po"
        crlf_content = (
            'msgid ""\r\n'
            'msgstr ""\r\n'
            '"Language: pt_BR\\r\\n"\r\n'
            "\r\n"
            'msgid "Hello"\r\n'
            'msgstr ""\r\n'
        )
        po_file.write_bytes(crlf_content.encode("utf-8"))

        res = runner.invoke(app, ["set", str(po_file), "Hello", "Olá"])
        assert res.exit_code == 0
        new_bytes = po_file.read_bytes()
        assert b"\r\n" in new_bytes
        assert new_bytes[-2:] == b"\r\n" or b"\r\n" in new_bytes
        raw_text = new_bytes.decode("utf-8")
        lines = raw_text.splitlines(keepends=True)
        for line in lines:
            assert line.endswith("\r\n")

    # 24. Bug 2: Permissões de arquivo preservadas e recusa arquivo somente leitura
    def test_case_24_file_permissions_preserved_and_readonly_refused(self, tmp_path: Path) -> None:
        import os

        po_file = tmp_path / "pt_BR.po"
        _create_sample_po(po_file)
        os.chmod(po_file, 0o640)

        res = runner.invoke(app, ["set", str(po_file), "Empty entry", "Permissão mantida"])
        assert res.exit_code == 0
        assert (os.stat(po_file).st_mode & 0o777) == 0o640

        # Teste com somente leitura (0444)
        os.chmod(po_file, 0o444)
        res_ro = runner.invoke(
            app,
            ["set", str(po_file), "Empty entry", "Não deve gravar", "--force"],
        )
        assert res_ro.exit_code == 2

    # 25. Bug 3: Plurais validados contra msgid_plural, sem falso PO004
    def test_case_25_plural_translation_pairs_validation(self) -> None:
        from posentinel.models import TranslationEntry
        from posentinel.rules.placeholders import (
            ExtraPlaceholderRule,
            MissingPlaceholderRule,
        )

        plural_entry = TranslationEntry(
            msgid="Item",
            msgid_plural="%d items",
            msgstr_plural={
                0: "Item",
                1: "%d itens",
            },
        )

        missing_issues = MissingPlaceholderRule().check(plural_entry)
        extra_issues = ExtraPlaceholderRule().check(plural_entry)
        assert missing_issues == []
        assert extra_issues == []

    # 26. Bug 4: Tags void como <br> e <img> sem barra de fechamento não geram PO005
    def test_case_26_void_tags_do_not_trigger_po005(self) -> None:
        from posentinel.models import TranslationEntry
        from posentinel.rules.syntax import InvalidMarkupRule

        entry = TranslationEntry(
            msgid="Line 1<br>Line 2<img src='x'>",
            msgstr="Linha 1<br>Linha 2<img src='x'>",
        )
        issues = InvalidMarkupRule().check(entry)
        assert issues == []

    # 27. Bug 5: Entradas obsoletas (#~) ignoradas por lookup e set
    def test_case_27_obsolete_entries_ignored(self, tmp_path: Path) -> None:
        po_file = tmp_path / "pt_BR.po"
        content = (
            'msgid ""\n'
            'msgstr ""\n'
            '"Language: pt_BR\\n"\n'
            "\n"
            '#~ msgid "Obsolete text"\n'
            '#~ msgstr "Texto obsoleto"\n'
        )
        po_file.write_text(content, encoding="utf-8")

        # Lookup em entrada obsoleta deve retornar missing (não viva)
        lookup_res = runner.invoke(
            app,
            ["lookup", str(po_file), "Obsolete text", "--format", "json"],
        )
        assert lookup_res.exit_code == 1
        data = json.loads(lookup_res.stdout)
        assert data["status"] == "missing"

        # Set deve criar uma nova entrada viva, não sobrescrever a linha #~
        set_res = runner.invoke(app, ["set", str(po_file), "Obsolete text", "Nova viva"])
        assert set_res.exit_code == 0
        new_content = po_file.read_text(encoding="utf-8")
        assert '#~ msgid "Obsolete text"' in new_content
        assert 'msgid "Obsolete text"\nmsgstr "Nova viva"' in new_content

    # 28. Bug 6: set com msgstr vazio é recusado (exit 1)
    def test_case_28_set_empty_msgstr_refused(self, tmp_path: Path) -> None:
        po_file = tmp_path / "pt_BR.po"
        _create_sample_po(po_file)

        res = runner.invoke(app, ["set", str(po_file), "Empty entry", "  ", "--format", "json"])
        assert res.exit_code == 1
        data = json.loads(res.stdout)
        assert data["action"] == "refused"
        assert data["reason"] == "empty_msgstr"

    # 29. Bug 7: arquivo corrompido/inválido no lookup gera exit 2
    def test_case_29_lookup_corrupted_file_exits_2(self, tmp_path: Path) -> None:
        po_file = tmp_path / "pt_BR.po"
        po_file.write_text("ESTE ARQUIVO NAO E UM PO VALIDO: msgstr sem msgid\n", encoding="utf-8")

        res = runner.invoke(app, ["lookup", str(po_file), "Anything"])
        assert res.exit_code == 2

    # 30. Bug 8: --ignore com regra desconhecida emite aviso
    def test_case_30_ignore_unknown_rule_emits_warning(self, tmp_path: Path) -> None:
        po_file = tmp_path / "pt_BR.po"
        _create_sample_po(po_file)

        res = runner.invoke(app, ["scan", str(po_file), "--ignore", "PO999,PO005"])
        assert "Aviso: regra 'PO999' informada em --ignore não é reconhecida" in res.stderr

    # 31. Bug 9: % solto e printf com precisão/largura (PO002 e PO003)
    def test_case_31_printf_specifiers_and_loose_percent(self) -> None:
        from posentinel.models import TranslationEntry
        from posentinel.rules.placeholders import (
            InvalidPlaceholderRule,
            MissingPlaceholderRule,
        )

        # a) Casos literais sem interpolação
        assert InvalidPlaceholderRule().check(
            TranslationEntry(msgid="Discount (%)", msgstr="Desconto (%)")
        ) == []
        assert InvalidPlaceholderRule().check(
            TranslationEntry(msgid="<span>%</span>", msgstr="<span>%</span>")
        ) == []

        # b) Placeholders com precisão (ex: %.2f) reconhecidos no PO002
        missing_issues = MissingPlaceholderRule().check(
            TranslationEntry(
                msgid="Quantity (%.2f) exceeds the limit",
                msgstr="Quantidade excede o limite",
            )
        )
        assert len(missing_issues) == 1
        assert missing_issues[0].code == "PO002"
        assert "%.2f" in missing_issues[0].message

        # c) Named printf com precisão e escape duplo (%(rate).2f%%)
        assert InvalidPlaceholderRule().check(
            TranslationEntry(
                msgid="Rate %(rate).2f%%",
                msgstr="Taxa %(rate).2f%%",
                flags=("python-format",),
            )
        ) == []

        # d) Template python-format com % solto extra dispara PO003 (WARNING)
        loose_issues = InvalidPlaceholderRule().check(
            TranslationEntry(
                msgid="Total %s",
                msgstr="Total %s%",
                flags=("python-format",),
            )
        )
        assert len(loose_issues) == 1
        assert loose_issues[0].code == "PO003"
        assert loose_issues[0].severity.value == "warning"
