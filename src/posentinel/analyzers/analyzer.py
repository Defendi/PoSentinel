"""Orquestrador de varredura: coordena PoParser e RulesEngine por arquivo/diretório."""

from pathlib import Path

from posentinel.models import ScanSummary
from posentinel.parser.po_parser import PoParser
from posentinel.rules.engine import RulesEngine


class TranslationAnalyzer:
    """Analisa um arquivo `.po` único ou varre recursivamente um diretório."""

    def __init__(self, parser: PoParser, engine: RulesEngine) -> None:
        self._parser = parser
        self._engine = engine

    def analyze_path(
        self,
        path: Path,
        target_lang: str | None = None,
        baseline_path: Path | None = None,
        git_ref: str | None = None,
    ) -> list[ScanSummary]:
        baseline_issues_by_msgid_and_code: set[tuple[str | None, str]] = set()

        if baseline_path is not None:
            baseline_summaries = self.analyze_path(baseline_path, target_lang=target_lang)
            for b_sum in baseline_summaries:
                for b_iss in b_sum.issues:
                    baseline_issues_by_msgid_and_code.add((b_iss.msgid, b_iss.code))

        if path.is_dir():
            summaries = [
                self._analyze_file(po_file)
                for po_file in self._discover_po_files(path, target_lang)
            ]
        else:
            summaries = [self._analyze_file(path)]

        # Se git_ref foi passado, extrai o conteúdo daquele ref para cada arquivo analisado
        if git_ref is not None:
            import subprocess

            for summary in summaries:
                file_p = Path(summary.file_path)
                # Tenta obter o caminho relativo ao repositório git
                try:
                    rel_path = file_p.relative_to(Path.cwd())
                except ValueError:
                    rel_path = file_p

                res = subprocess.run(
                    ["git", "show", f"{git_ref}:{rel_path}"],
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if res.returncode == 0:
                    base_parse = self._parser.parse_string(res.stdout)
                    for entry in base_parse.entries:
                        for iss in self._engine.analyze(entry):
                            baseline_issues_by_msgid_and_code.add((iss.msgid, iss.code))

        if baseline_path is not None or git_ref is not None:
            filtered_summaries = []
            for summary in summaries:
                new_issues = [
                    iss
                    for iss in summary.issues
                    if (iss.msgid, iss.code) not in baseline_issues_by_msgid_and_code
                ]
                filtered_summaries.append(
                    ScanSummary(
                        file_path=summary.file_path,
                        locale=summary.locale,
                        total_entries=summary.total_entries,
                        issues=new_issues,
                    )
                )
            return filtered_summaries

        return summaries

    def _discover_po_files(self, directory: Path, target_lang: str | None = None) -> list[Path]:
        if target_lang:
            return sorted(directory.rglob(f"{target_lang}.po"))
        return sorted(directory.rglob("*.po"))

    def _analyze_file(self, path: Path) -> ScanSummary:
        parse_result = self._parser.parse_file(path)

        issues = list(parse_result.issues)
        for entry in parse_result.entries:
            issues.extend(self._engine.analyze(entry))

        return ScanSummary(
            file_path=str(path),
            locale=path.stem,
            total_entries=len(parse_result.entries),
            issues=issues,
        )
