import json
from typing import Any

from posentinel.models.result import ScanSummary


class JsonReporter:
    """Serializador estruturado em JSON dos resultados de análise."""

    def render(self, summaries: list[ScanSummary]) -> str:
        data: list[dict[str, Any]] = []
        for summary in summaries:
            item = {
                "file": summary.file_path,
                "locale": summary.locale,
                "entries": summary.total_entries,
                "errors_count": summary.errors_count,
                "warnings_count": summary.warnings_count,
                "infos_count": summary.infos_count,
                "status": "failed"
                if summary.has_errors
                else ("warning" if summary.warnings_count > 0 else "passed"),
                "issues": [
                    {
                        "code": issue.code,
                        "severity": issue.severity.value,
                        "line": issue.line,
                        "message": issue.message,
                        "msgid": issue.msgid,
                        "odoo_context": issue.odoo_context,
                    }
                    for issue in summary.issues
                ],
            }
            data.append(item)

        # Se for apenas 1 arquivo analisado, entrega o objeto direto para ergonomia
        output: Any = data[0] if len(data) == 1 else data
        return json.dumps(output, indent=2, ensure_ascii=False)
