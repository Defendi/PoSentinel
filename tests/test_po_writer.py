import shutil
from pathlib import Path

from posentinel.models import TranslationChange
from posentinel.parser.po_writer import PoWriter


def test_po_writer_apply_changes(tmp_path: Path) -> None:
    po_file = tmp_path / "test.po"
    po_file.write_text(
        'msgid "Hello"\n'
        'msgstr ""\n',
        encoding="utf-8"
    )

    changes = [
        TranslationChange(
            msgid="Hello", old_msgstr="", new_msgstr="Olá", issue_code="PO001", applied=True
        )
    ]

    writer = PoWriter()
    backup_path = writer.apply_changes(po_file, changes)

    assert backup_path is not None
    assert backup_path.exists()
    assert po_file.read_text(encoding="utf-8").find('msgstr "Olá"') != -1
