from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, UTC
from typing import Any
import copy

from engine_akxom import PODERES_INFO

CASE_SCHEMA_VERSION = 2
DEFAULT_BENCHMARK = "Estable"
DEFAULT_CASE_STATUS = "Borrador"


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


@dataclass
class EvidenceItem:
    summary: str = ""
    excerpts: str = ""
    source: str = "Manual"
    confidence: int = 50
    analyst_note: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "EvidenceItem":
        data = data or {}
        return cls(
            summary=str(data.get("summary") or ""),
            excerpts=str(data.get("excerpts") or ""),
            source=str(data.get("source") or "Manual"),
            confidence=int(data.get("confidence") or 50),
            analyst_note=str(data.get("analyst_note") or ""),
        )


@dataclass
class PowerAssessment:
    power_code: str
    power_title: str
    m1: float = 5.0
    m2: float = 5.0
    m3: float = 5.0
    r: float = 5.0
    c: float = 5.0
    a: float = 5.0
    flow: float = 0.0
    evidence: EvidenceItem = field(default_factory=EvidenceItem)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "PowerAssessment":
        data = data or {}
        return cls(
            power_code=str(data.get("power_code") or ""),
            power_title=str(data.get("power_title") or ""),
            m1=float(data.get("m1", 5.0)),
            m2=float(data.get("m2", 5.0)),
            m3=float(data.get("m3", 5.0)),
            r=float(data.get("r", 5.0)),
            c=float(data.get("c", 5.0)),
            a=float(data.get("a", 5.0)),
            flow=float(data.get("flow", 0.0)),
            evidence=EvidenceItem.from_dict(data.get("evidence")),
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["evidence"]["confidence"] = int(max(0, min(100, self.evidence.confidence)))
        return data


@dataclass
class CaseSnapshotRecord:
    created_at: str
    label: str
    integrity: float
    friction: float
    archetype_name: str
    top_risk: str
    dominant_power: str
    summary: str
    structural_state_name: str = ""

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "CaseSnapshotRecord":
        data = data or {}
        return cls(
            created_at=str(data.get("created_at") or _utc_now_iso()),
            label=str(data.get("label") or "Iteración guardada"),
            integrity=float(data.get("integrity") or 0.0),
            friction=float(data.get("friction") or 0.0),
            archetype_name=str(data.get("archetype_name") or ""),
            structural_state_name=str(data.get("structural_state_name") or ""),
            top_risk=str(data.get("top_risk") or ""),
            dominant_power=str(data.get("dominant_power") or ""),
            summary=str(data.get("summary") or ""),
        )


def default_assessments() -> dict[str, PowerAssessment]:
    assessments: dict[str, PowerAssessment] = {}
    for power_code, power_title, _, _ in PODERES_INFO:
        assessments[power_code] = PowerAssessment(
            power_code=power_code,
            power_title=power_title,
        )
    return assessments


@dataclass
class CaseRecord:
    schema_version: int
    case_id: str
    created_at: str
    updated_at: str
    client_name: str
    project_name: str
    analyst_name: str
    objective: str
    context: str
    benchmark_name: str
    case_status: str
    analyst_notes: str
    tags: list[str]
    assessments: dict[str, PowerAssessment] = field(default_factory=default_assessments)
    snapshots: list[CaseSnapshotRecord] = field(default_factory=list)

    @classmethod
    def create_blank(cls) -> "CaseRecord":
        now = _utc_now_iso()
        return cls(
            schema_version=CASE_SCHEMA_VERSION,
            case_id=f"case_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}",
            created_at=now,
            updated_at=now,
            client_name="",
            project_name="",
            analyst_name="",
            objective="",
            context="",
            benchmark_name=DEFAULT_BENCHMARK,
            case_status=DEFAULT_CASE_STATUS,
            analyst_notes="",
            tags=[],
            assessments=default_assessments(),
            snapshots=[],
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CaseRecord":
        assessments_raw = data.get("assessments") or {}
        assessments = default_assessments()
        for power_code, raw in assessments_raw.items():
            loaded = PowerAssessment.from_dict(raw)
            if loaded.power_code:
                assessments[power_code] = loaded
        snapshots = [CaseSnapshotRecord.from_dict(item) for item in (data.get("snapshots") or [])]
        return cls(
            schema_version=int(data.get("schema_version") or CASE_SCHEMA_VERSION),
            case_id=str(data.get("case_id") or cls.create_blank().case_id),
            created_at=str(data.get("created_at") or _utc_now_iso()),
            updated_at=str(data.get("updated_at") or _utc_now_iso()),
            client_name=str(data.get("client_name") or ""),
            project_name=str(data.get("project_name") or ""),
            analyst_name=str(data.get("analyst_name") or ""),
            objective=str(data.get("objective") or ""),
            context=str(data.get("context") or ""),
            benchmark_name=str(data.get("benchmark_name") or DEFAULT_BENCHMARK),
            case_status=str(data.get("case_status") or DEFAULT_CASE_STATUS),
            analyst_notes=str(data.get("analyst_notes") or ""),
            tags=[str(tag) for tag in (data.get("tags") or [])],
            assessments=assessments,
            snapshots=snapshots,
        )

    def touch(self) -> None:
        self.updated_at = _utc_now_iso()

    def clone(self) -> "CaseRecord":
        return copy.deepcopy(self)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "case_id": self.case_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "client_name": self.client_name,
            "project_name": self.project_name,
            "analyst_name": self.analyst_name,
            "objective": self.objective,
            "context": self.context,
            "benchmark_name": self.benchmark_name,
            "case_status": self.case_status,
            "analyst_notes": self.analyst_notes,
            "tags": self.tags,
            "assessments": {
                power_code: assessment.to_dict()
                for power_code, assessment in self.assessments.items()
            },
            "snapshots": [asdict(snapshot) for snapshot in self.snapshots],
        }
