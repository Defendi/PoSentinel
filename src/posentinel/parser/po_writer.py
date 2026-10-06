import shutil
from pathlib import Path

import polib

from posentinel.models import TranslationChange


class PoWriter:
    """Aplica TranslationChange (applied=True) de volta no arquivo .po, com backup automático."""

    def apply_changes(self, path: Path, changes: list[TranslationChange]) -> Path | None:
        applied_changes = [change for change in changes if change.applied]
        if not applied_changes:
            return None

        backup_path = path.with_suffix(path.suffix + ".bak")
        shutil.copy2(path, backup_path)

        pofile = polib.pofile(str(path))
        changes_by_msgid = {change.msgid: change for change in applied_changes}
        for entry in pofile:
            change = changes_by_msgid.get(entry.msgid)
            if change is not None:
                entry.msgstr = change.new_msgstr
        pofile.save(str(path))
        return backup_path
