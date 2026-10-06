"""Serialização estruturada dos resultados de scan em JSON para pipelines de CI/CD."""

import json

from posentinel.models import Issue, ScanSummary, TranslationChange


class JsonReporter:
    """Serializa os resultados do scan em um payload JSON estruturado."""

    def report(
        self,
        summaries: list[ScanSummary],
        changes: dict[str, list[TranslationChange]] | None = None,
    ) -> str:
        payload = {
            "results": [
                self._summary_to_dict(summary, changes.get(summary.file_path) if changes else None)
                for summary in summaries
            ]
        }
        return json.dumps(payload, ensure_ascii=False, indent=2)

    def _summary_to_dict(
        self, summary: ScanSummary, file_changes: list[TranslationChange] | None = None
    ) -> dict[str, object]:
        data: dict[str, object] = {
            "file_path": summary.file_path,
            "locale": summary.locale,
            "total_entries": summary.total_entries,
            "errors_count": summary.errors_count,
            "warnings_count": summary.warnings_count,
            "infos_count": summary.infos_count,
            "issues": [self._issue_to_dict(issue) for issue in summary.issues],
        }
        if file_changes:
            data["ai_changes"] = [
                {
                    "code": c.issue_code,
                    "msgid": c.msgid,
                    "old_msgstr": c.old_msgstr,
                    "new_msgstr": c.new_msgstr,
                    "applied": c.applied,
                }
                for c in file_changes
            ]
        return data

    def _issue_to_dict(self, issue: Issue) -> dict[str, object]:
        return {
            "code": issue.code,
            "message": issue.message,
            "severity": issue.severity.value,
            "line": issue.line,
            "msgid": issue.msgid,
            "odoo_context": issue.odoo_context,
            "suggestion": issue.suggestion,
        }
