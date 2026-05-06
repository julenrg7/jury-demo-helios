from __future__ import annotations

import json
from pathlib import Path

from noumenon_v2.domain.models import CaseRecord

DEFAULT_CASES_DIR = Path("noumenon_data_v2")


class JsonCaseRepository:
    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or DEFAULT_CASES_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _filepath(self, case_id: str) -> Path:
        return self.base_dir / f"{case_id}.json"

    def save(self, case: CaseRecord) -> Path:
        case.touch()
        path = self._filepath(case.case_id)
        path.write_text(
            json.dumps(case.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return path

    def load(self, case_id: str) -> CaseRecord:
        path = self._filepath(case_id)
        payload = json.loads(path.read_text(encoding="utf-8"))
        return CaseRecord.from_dict(payload)

    def list_case_ids(self) -> list[str]:
        return sorted(
            [path.stem for path in self.base_dir.glob("*.json")],
            reverse=True,
        )

    def delete(self, case_id: str) -> bool:
        path = self._filepath(case_id)
        if not path.exists():
            return False
        path.unlink()
        return True
