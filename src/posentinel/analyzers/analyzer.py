from pathlib import Path

from posentinel.models.result import ScanSummary
from posentinel.parser.po_parser import PoParser
from posentinel.rules import get_default_rules
from posentinel.rules.engine import RulesEngine


class TranslationAnalyzer:
    """Orquestrador responsável por analisar arquivos ou diretórios de arquivos .po."""

    def __init__(
        self,
        parser: PoParser | None = None,
        engine: RulesEngine | None = None,
    ) -> None:
        self.parser = parser or PoParser()
        self.engine = engine or RulesEngine(get_default_rules())

    def analyze_file(self, file_path: str | Path) -> ScanSummary:
        path = Path(file_path)
        entries = self.parser.parse_file(path)
        issues = self.engine.execute_all(entries)

        # Determina o locale pelo nome do arquivo ou cabeçalho se possível
        locale = path.stem

        return ScanSummary(
            file_path=str(path),
            locale=locale,
            total_entries=len(entries),
            issues=issues,
        )

    def analyze_path(self, target_path: str | Path) -> list[ScanSummary]:
        path = Path(target_path)
        if path.is_file():
            return [self.analyze_file(path)]

        if not path.is_dir():
            raise FileNotFoundError(f"Caminho não encontrado: {target_path}")

        # Busca recursiva por arquivos .po
        po_files = sorted(path.rglob("*.po"))
        results: list[ScanSummary] = []
        for po_file in po_files:
            results.append(self.analyze_file(po_file))

        return results
