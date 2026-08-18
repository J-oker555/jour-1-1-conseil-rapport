from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path


def append_run_header(report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with report_path.open("a", encoding="utf-8") as report:
        report.write(f"\n\n## Execution {timestamp}\n")

