from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd
import numpy as np

from analysis import get_auto_profile
from engine_akxom import PODERES_INFO, build_empty_tensor, set_power_structured
from motor_dictamen import build_core_output_impl
from noumenon_v2.domain.models import CaseRecord, CaseSnapshotRecord, PowerAssessment


@dataclass
class DiagnosisSnapshot:
    integrity: float
    friction: float
    archetype_name: str
    structural_state_name: str
    archetype_hybrid: bool
    runner_up_name: str
    runner_up_id: str
    priority_rule_applied: bool
    top_risk: str
    one_liner: str
    executive_view: dict[str, Any]
    decision_panel: dict[str, Any]
    core: dict[str, Any]


def format_power_focus(power_code: str | None) -> str:
    code = str(power_code or "").strip()
    if not code:
        return "Sin palanca definida"
    for current_code, title, _, _ in PODERES_INFO:
        if current_code == code:
            return f"{title} ({current_code})"
    return code


def _clean_editorial_copy(text: str) -> str:
    cleaned = " ".join(str(text or "").split())
    replacements = {
        "benchmark": "base de referencia",
        "Benchmark": "Base de referencia",
        "Arquetipo Ignición:": "Estado de ignición:",
        "Ignición:": "Estado de ignición:",
        "frente al base de referencia": "frente a la base de referencia",
        "frente al Base de referencia": "frente a la Base de referencia",
    }
    for source, target in replacements.items():
        cleaned = cleaned.replace(source, target)
    return cleaned


def build_editorial_frame(diagnosis: DiagnosisSnapshot) -> dict[str, str]:
    panel = diagnosis.decision_panel or {}
    lever_label = format_power_focus(panel.get("lever_power") or diagnosis.top_risk)
    lever_note = _clean_editorial_copy(
        str(
        panel.get("lever_msg")
        or panel.get("intervention_title")
        or "La lectura prioriza reforzar el nodo donde la capacidad ya no se convierte con suficiente estabilidad."
        ).strip()
    )
    classification = "Con frontera activa" if diagnosis.archetype_hybrid else "Lectura principal"
    return {
        "archetype": diagnosis.archetype_name,
        "structural_state": diagnosis.structural_state_name,
        "top_risk": format_power_focus(diagnosis.top_risk),
        "lever_label": lever_label,
        "lever_note": lever_note,
        "classification": classification,
    }


_ARCHETYPE_COMPARISON_RULES: dict[tuple[str, str], dict[str, str]] = {
    ("arquitectura_soberana", "feudo_carismatico"): {
        "activation": "La lectura favorece continuidad estructural, mando estable y maniobra sostenida por encima de dependencia biográfica.",
        "exclusion": "No cae en Feudo Carismático porque la estabilidad no depende principalmente de una figura visible ni de un núcleo biográfico insustituible.",
        "decisive": "La pregunta decisiva es si la arquitectura seguiría gobernando con coherencia tras retirar a la figura dominante.",
    },
    ("feudo_carismatico", "arquitectura_soberana"): {
        "activation": "La lectura favorece dependencia angular y peso biográfico del liderazgo por encima de la norma instituida.",
        "exclusion": "No cae en Arquitectura Soberana porque la continuidad todavía descansa demasiado en una figura o núcleo personal.",
        "decisive": "La frontera real está en la transferibilidad del mando: persona o estructura.",
    },
    ("vanguardia_disruptiva", "organismo_de_asalto"): {
        "activation": "La lectura favorece potencia estratégica y tecnológica con deuda de institución, no mera captura rápida de valor.",
        "exclusion": "No cae en Organismo de Asalto porque la debilidad principal es de forma y gobierno, no de espesor simbólico o legitimidad social reducida.",
        "decisive": "La diferencia crítica es si el sistema está construyendo orden nuevo o explotando velocidad con sesgo extractivo.",
    },
    ("vanguardia_disruptiva", "feudo_carismatico"): {
        "activation": "La lectura favorece crecimiento acelerado apoyado en potencia tecnológica y estratégica, con una institución todavía demasiado inmadura para sostenerlo con orden.",
        "exclusion": "No cae en Feudo Carismático porque el problema principal no es la dependencia del líder, sino que la estructura todavía no acompaña la velocidad real del sistema.",
        "decisive": "La pregunta decisiva es si la fragilidad dominante aparecería por retirada del líder o por expansión sin arquitectura suficiente. Aquí domina la segunda.",
    },
    ("organismo_de_asalto", "vanguardia_disruptiva"): {
        "activation": "La lectura favorece captura de valor, maniobra agresiva y bajo espesor cultural como centro del patrón.",
        "exclusion": "No cae en Vanguardia Disruptiva porque aquí no domina una deuda institucional de crecimiento sino una lógica de extracción altamente eficiente.",
        "decisive": "La pregunta clave es si la organización busca instituir futuro o capturar valor con máxima velocidad.",
    },
    ("feudo_carismatico", "vanguardia_disruptiva"): {
        "activation": "La lectura favorece dependencia biográfica y concentración del mando en la figura central por encima de una lógica de escala institucional todavía en construcción.",
        "exclusion": "No cae en Vanguardia Disruptiva porque la vulnerabilidad principal no está en crecer sin forma, sino en depender demasiado del núcleo personal de liderazgo.",
        "decisive": "La pregunta decisiva es si la lesión principal sería una expansión sin arquitectura o una transición de liderazgo mal absorbida. Aquí domina la segunda.",
    },
    ("leviatan_ciego", "estructura_fosilizada"): {
        "activation": "La lectura favorece exceso de institución y proceso frente a maniobra estratégica viva.",
        "exclusion": "No cae en Estructura Fosilizada porque el bloqueo dominante no nace del canon cultural heredado sino de la densidad institucional.",
        "decisive": "La frontera está en si la rigidez nace de la burocracia o del canon.",
    },
    ("estructura_fosilizada", "leviatan_ciego"): {
        "activation": "La lectura favorece canon, prestigio y hábito consolidados que frenan adaptación tecnológica u operativa.",
        "exclusion": "No cae en Leviatán Ciego porque el freno principal no es la institución procesual sino la fuerza cultural del legado.",
        "decisive": "La pregunta decisiva es qué bloquea más: la norma o el canon.",
    },
    ("zombi_estrategico", "fortaleza_sitiada"): {
        "activation": "La lectura favorece deterioro del cerebro estratégico y tecnológico más que un simple bloqueo de acceso al entorno.",
        "exclusion": "No cae en Fortaleza Sitiada porque el problema central no es el cerco externo sino la pérdida de lectura de futuro.",
        "decisive": "La frontera está en si el sistema aún ve el futuro pero no puede entrar, o si ya ha dejado de leerlo.",
    },
    ("fortaleza_sitiada", "zombi_estrategico"): {
        "activation": "La lectura favorece potencia real dentro del sistema con acceso narrativo y relacional deteriorado hacia fuera.",
        "exclusion": "No cae en Zombi Estratégico porque la capacidad interna sigue viva y el daño principal se concentra en el perímetro.",
        "decisive": "La pregunta decisiva es si el problema está en el cerebro interno o en el circuito de acceso externo.",
    },
    ("resonancia_fantasma", "estructura_fosilizada"): {
        "activation": "La lectura favorece un residuo simbólico que sobrevive a un cuerpo operativo ya degradado.",
        "exclusion": "No cae en Estructura Fosilizada porque aquí el imaginario pesa más que la estructura realmente viva.",
        "decisive": "La frontera está en si todavía queda cuerpo operativo o casi solo eco.",
    },
    ("estructura_fosilizada", "resonancia_fantasma"): {
        "activation": "La lectura favorece estructura todavía operativa, aunque rígida, y no mera supervivencia simbólica.",
        "exclusion": "No cae en Resonancia Fantasma porque aún existe cuerpo institucional y operativo suficiente para sostener el sistema.",
        "decisive": "La pregunta clave es si la organización sigue siendo fortaleza rígida o ya solo vive de aura.",
    },
    ("gigante_de_barro", "leviatan_ciego"): {
        "activation": "La lectura favorece peso real con cohesión deficiente, fricción extendida y forma insuficiente para sostener la masa.",
        "exclusion": "No cae en Leviatán Ciego porque aquí no domina una institución fuerte sino una masa que no termina de convertirse en arquitectura.",
        "decisive": "La frontera está en distinguir exceso de forma sin estrategia frente a exceso de peso sin forma.",
    },
    ("leviatan_ciego", "gigante_de_barro"): {
        "activation": "La lectura favorece densidad institucional y mando procesual por encima de una mera torre pesada y desordenada.",
        "exclusion": "No cae en Gigante de Barro porque la institución sí existe, aunque haya perdido maniobra.",
        "decisive": "La pregunta crítica es si el sistema falla por exceso de aparato o por falta de esqueleto.",
    },
}


def build_archetype_comparison(diagnosis: DiagnosisSnapshot) -> dict[str, str]:
    core_archetype = str((diagnosis.core.get("archetype_universal") or {}).get("id") or "").strip()
    runner_up_id = diagnosis.runner_up_id
    rule = _ARCHETYPE_COMPARISON_RULES.get((core_archetype, runner_up_id))
    if rule is None:
        activation = (
            f"La lectura favorece {diagnosis.archetype_name} porque su firma encaja mejor con el frente dominante "
            f"en {format_power_focus(diagnosis.top_risk)} y con el estado estructural {diagnosis.structural_state_name}."
        )
        exclusion = (
            f"No cae en {diagnosis.runner_up_name or 'otra lectura cercana'} porque la combinación actual de riesgo, forma y tracción "
            "se alinea mejor con el patrón dominante que mejor explica el caso."
        )
        decisive = (
            "La diferencia decisiva no está en una sola cifra, sino en la combinación entre potencia, fricción, estructura y dirección del sistema."
        )
    else:
        activation = rule["activation"]
        exclusion = rule["exclusion"].replace("Feudo Carismático", diagnosis.runner_up_name).replace("Organismo de Asalto", diagnosis.runner_up_name).replace("Estructura Fosilizada", diagnosis.runner_up_name).replace("Fortaleza Sitiada", diagnosis.runner_up_name).replace("Zombi Estratégico", diagnosis.runner_up_name).replace("Resonancia Fantasma", diagnosis.runner_up_name).replace("Gigante de Barro", diagnosis.runner_up_name).replace("Leviatán Ciego", diagnosis.runner_up_name).replace("Arquitectura Soberana", diagnosis.runner_up_name)
        decisive = rule["decisive"]

    framing = "La lectura queda en zona de frontera y exige mirar con cuidado la separación entre alternativas." if diagnosis.archetype_hybrid else "La lectura queda suficientemente separada de su alternativa más cercana."
    priority = "La lectura se ha cerrado con un criterio decisivo del sistema." if diagnosis.priority_rule_applied else "La lectura se ha cerrado por predominio claro de la señal estructural."
    return {
        "runner_up_name": diagnosis.runner_up_name or "Lectura cercana",
        "activation": activation,
        "exclusion": exclusion,
        "decisive": decisive,
        "framing": framing,
        "priority": priority,
    }


def build_tensor_and_flows(case: CaseRecord) -> tuple[Any, list[float]]:
    tensor = build_empty_tensor()
    flows: list[float] = []
    for idx, (power_code, _, _, _) in enumerate(PODERES_INFO):
        assessment = case.assessments[power_code]
        tensor = set_power_structured(
            tensor,
            idx,
            assessment.m1,
            assessment.m2,
            assessment.m3,
            assessment.r,
            assessment.c,
            assessment.a,
        )
        flows.append(float(assessment.flow))
    return tensor, flows


def build_evidence_dataframe(case: CaseRecord) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for power_code, power_title, _, _ in PODERES_INFO:
        assessment: PowerAssessment = case.assessments[power_code]
        rows.append(
            {
                "Poder": power_code,
                "Título": power_title,
                "Nota": assessment.evidence.summary,
                "Extractos": assessment.evidence.excerpts,
                "Origen": assessment.evidence.source,
                "Confianza": int(assessment.evidence.confidence),
                "Comentario analista": assessment.evidence.analyst_note,
            }
        )
    return pd.DataFrame(rows)


def run_case_diagnosis(case: CaseRecord) -> DiagnosisSnapshot:
    tensor, flows = build_tensor_and_flows(case)
    evidence_df = build_evidence_dataframe(case)
    benchmark_name = case.benchmark_name or "Estable"
    auto_profile = get_auto_profile(benchmark_name)
    target = case.objective.strip() or "Lectura estructural"

    core = build_core_output_impl(
        tensor,
        flows,
        target,
        benchmark_name,
        auto_profile,
        evidence_df=evidence_df,
    )
    archetype_universal = dict(core.get("archetype_universal") or {})
    public_archetype_name = str(archetype_universal.get("name") or core["archetype_name"])
    structural_state_name = str(core.get("archetype_name") or "")
    archetype_hybrid = bool(archetype_universal.get("hybrid"))
    runner_up_name = str(archetype_universal.get("runner_up_name") or "")
    runner_up_id = str(archetype_universal.get("runner_up_id") or "")
    priority_rule_applied = bool(archetype_universal.get("priority_rule_applied"))
    return DiagnosisSnapshot(
        integrity=float(core["integrity"]),
        friction=float(core["friction"]),
        archetype_name=public_archetype_name,
        structural_state_name=structural_state_name,
        archetype_hybrid=archetype_hybrid,
        runner_up_name=runner_up_name,
        runner_up_id=runner_up_id,
        priority_rule_applied=priority_rule_applied,
        top_risk=str(core["current_top_risk"]),
        one_liner=str(core["one_liner"]),
        executive_view=dict(core.get("executive_view") or {}),
        decision_panel=dict(core.get("decision_panel") or {}),
        core=core,
    )


def build_power_summary_rows(core: dict[str, Any]) -> list[dict[str, Any]]:
    report = core["report"]
    potency = np.asarray(report["potency100"], dtype=float)
    leak = np.asarray(report["leakscore"], dtype=float)
    avgm3 = np.asarray(report["avgm3"], dtype=float)
    avga = np.asarray(report["avga"], dtype=float)

    rows: list[dict[str, Any]] = []
    for idx, (power_code, power_title, _, _) in enumerate(PODERES_INFO):
        rows.append(
            {
                "Poder": power_code,
                "Título": power_title,
                "Potencia": round(float(potency[idx]), 1),
                "Fricción": round(float(leak[idx]) * 10.0, 1),
                "Estructura": round(float(avgm3[idx]), 1),
                "Autoridad": round(float(avga[idx]), 1),
            }
        )
    rows.sort(key=lambda row: (-row["Fricción"], -row["Potencia"], row["Poder"]))
    return rows


def build_case_snapshot(case: CaseRecord) -> dict[str, Any]:
    evidence_count = 0
    calibrated_count = 0
    high_confidence_count = 0

    for assessment in case.assessments.values():
        if assessment.evidence.summary.strip() or assessment.evidence.excerpts.strip():
            evidence_count += 1
        if any(abs(value - 5.0) > 1e-6 for value in (assessment.m1, assessment.m2, assessment.m3, assessment.r, assessment.c, assessment.a)):
            calibrated_count += 1
        if int(assessment.evidence.confidence) >= 70:
            high_confidence_count += 1

    return {
        "evidence_count": evidence_count,
        "calibrated_count": calibrated_count,
        "high_confidence_count": high_confidence_count,
        "objective_set": bool(case.objective.strip()),
        "context_set": bool(case.context.strip()),
        "snapshot_count": len(case.snapshots),
        "case_status": case.case_status,
    }


def build_structural_reading(case: CaseRecord, diagnosis: DiagnosisSnapshot) -> dict[str, str]:
    rows = build_power_summary_rows(diagnosis.core)
    top_row = rows[0] if rows else {"Poder": "P?", "Título": "Nodo crítico", "Fricción": 0.0, "Potencia": 0.0}
    top_assessment = case.assessments.get(top_row["Poder"])
    evidence_summary = (
        top_assessment.evidence.summary.strip()
        if top_assessment and top_assessment.evidence.summary.strip()
        else "Sin síntesis analítica cargada en este nodo."
    )
    analyst_note = (
        top_assessment.evidence.analyst_note.strip()
        if top_assessment and top_assessment.evidence.analyst_note.strip()
        else "Aún no hay nota específica del analista para este frente."
    )
    causal_reading = (
        f"La fricción dominante se concentra en {top_row['Título']} ({top_row['Poder']}) con "
        f"{top_row['Fricción']:.1f} puntos de tensión frente a {top_row['Potencia']:.1f} de potencia. "
        f"El sistema ya produce capacidad, pero no la convierte con suficiente estabilidad en ese nodo."
    )
    principal_leak = (
        f"La fuga principal aparece cuando la potencia acumulada en {top_row['Poder']} supera la "
        "estructura y la autoridad disponibles, generando un desajuste operativo que amenaza la coherencia del conjunto."
    )
    minimum_intervention = (
        diagnosis.executive_view.get("critical_action")
        or diagnosis.decision_panel.get("executive_decision")
        or diagnosis.one_liner
    )
    return {
        "causal_reading": causal_reading,
        "dominant_evidence": evidence_summary,
        "dominant_note": analyst_note,
        "principal_leak": principal_leak,
        "minimum_intervention": str(minimum_intervention),
        "dominant_power": f"{top_row['Título']} ({top_row['Poder']})",
    }


def append_case_snapshot(case: CaseRecord, diagnosis: DiagnosisSnapshot) -> CaseSnapshotRecord:
    reading = build_structural_reading(case, diagnosis)
    snapshot = CaseSnapshotRecord(
        created_at=case.updated_at,
        label=f"Iteración {len(case.snapshots) + 1}",
        integrity=round(diagnosis.integrity, 1),
        friction=round(diagnosis.friction, 1),
        archetype_name=diagnosis.archetype_name,
        structural_state_name=diagnosis.structural_state_name,
        top_risk=diagnosis.top_risk,
        dominant_power=reading["dominant_power"],
        summary=reading["principal_leak"],
    )
    case.snapshots.append(snapshot)
    case.snapshots = case.snapshots[-6:]
    return snapshot


def build_snapshot_comparison(case: CaseRecord, diagnosis: DiagnosisSnapshot) -> dict[str, str] | None:
    if not case.snapshots:
        return None
    previous = case.snapshots[-1]
    integrity_delta = round(diagnosis.integrity - previous.integrity, 1)
    friction_delta = round(diagnosis.friction - previous.friction, 1)
    if (
        integrity_delta == 0
        and friction_delta == 0
        and previous.archetype_name == diagnosis.archetype_name
        and previous.structural_state_name == diagnosis.structural_state_name
    ):
        direction = "La lectura actual replica la última iteración sin cambios sustantivos."
    else:
        direction = (
            f"Integridad {integrity_delta:+.1f} y fricción {friction_delta:+.1f} frente a la iteración anterior."
        )
    return {
        "previous_label": previous.label,
        "previous_archetype": previous.archetype_name,
        "previous_state": previous.structural_state_name,
        "previous_risk": previous.top_risk,
        "previous_power": previous.dominant_power,
        "direction": direction,
        "previous_summary": previous.summary,
    }


def build_flow_progress(case: CaseRecord, has_diagnosis: bool) -> list[dict[str, Any]]:
    snapshot = build_case_snapshot(case)
    evidence_ready = snapshot["evidence_count"] >= 3
    structure_ready = snapshot["calibrated_count"] >= 3
    report_ready = has_diagnosis

    return [
        {
            "label": "01 · Caso",
            "status": "done" if snapshot["objective_set"] and snapshot["context_set"] else "current",
            "hint": "Define la decisión a iluminar y el contexto que la vuelve crítica.",
        },
        {
            "label": "02 · Evidencia",
            "status": "done" if evidence_ready else "current",
            "hint": "Carga hechos defendibles en los poderes que más pesan en la lectura.",
        },
        {
            "label": "03 · Estructura",
            "status": "done" if structure_ready else "current",
            "hint": "Ajusta dónde hay capacidad, dónde falta forma y cómo se mueve el sistema.",
        },
        {
            "label": "04 · Diagnóstico",
            "status": "done" if has_diagnosis else "current",
            "hint": "Convierte la lectura en una hipótesis ejecutiva visible y priorizada.",
        },
        {
            "label": "05 · Informe",
            "status": "done" if report_ready else "pending",
            "hint": "Cierra la conversación con una salida exportable y defendible.",
        },
    ]


def recommend_next_step(case: CaseRecord, has_diagnosis: bool) -> tuple[str, str]:
    snapshot = build_case_snapshot(case)
    if not snapshot["objective_set"] or not snapshot["context_set"]:
        return (
            "01 · Caso",
            "Define con precisión qué decisión quieres iluminar y por qué ese contexto importa ahora.",
        )
    if snapshot["evidence_count"] < 3:
        return (
            "02 · Evidencia",
            "Introduce evidencia sólida en al menos tres poderes para que la lectura tenga densidad suficiente.",
        )
    if snapshot["calibrated_count"] < 3:
        return (
            "03 · Estructura",
            "Ajusta al menos tres frentes para que la estructura exprese la tensión dominante del caso.",
        )
    if not has_diagnosis:
        return (
            "04 · Diagnóstico",
            "Genera la lectura ejecutiva para hacer visible la tensión principal y la decisión recomendada.",
        )
    return (
        "05 · Informe",
        "La lectura ya está lista: ciérrala con una salida HTML o PDF lista para comité, cliente o jurado.",
    )
