from __future__ import annotations

import streamlit as st

import numpy as np
import pandas as pd
from typing import Any

from engine_akxom import (
    build_empty_tensor,
    set_power_structured,
    PODERES_INFO,
)

# P5, P8, P9 en orden PODERES_INFO (0-based).
_GERMINAL_IDX_P5 = 4
_GERMINAL_IDX_P8 = 7
_GERMINAL_IDX_P9 = 8

# Umbrales etapa germinal (media aritmética de las 9 celdas del tensor por poder, escala 0–10).
GERMINAL_P8_P9_CELL_MEAN_MIN = 7.5  # P8 y P9 deben ser estrictamente mayores.
GERMINAL_P5_CELL_MEAN_MAX = 4.0  # P5 estrictamente por debajo (madurez institucional rezagada).
# Gap benchmark P5 (vs tabla benchmark) para mostrar nota de «potencial futuro» en panel Ignición.
GERMINAL_P5_BENCHMARK_GAP_NOTE_MIN = 12.0

# Prospecto / S-1: recalibración de integridad ejecutiva (no sustituye validación humana).
OFFERING_PROSPECTUS_INTEGRITY_SCALE = 0.775
OFFERING_PROSPECTUS_INTEGRITY_CAP = 60.5
OFFERING_PROSPECTUS_INTEGRITY_FLOOR = 50.0

# P5, P6, P8, P9 (índices 0-based en power_cell_mean / leakscore)
_INP5, _INP6, _INP8, _INP9 = 4, 5, 7, 8


def _apply_inertial_sovereignty_discount(report: dict, prof: dict, integrity: float) -> tuple[float, dict[str, Any]]:
    """
    Distingue dominio activo (innovación / plataforma) de inercia de legado:
    fortaleza P5/P6 en large cap sin señal equivalente de expansión estratégica dinámica.
    """
    pcm = np.asarray(report.get("power_cell_mean"), dtype=float).reshape(-1)
    if pcm.size < 10:
        return integrity, {"active": False, "reason": "no_pcm"}

    leak = np.asarray(report["leakscore"], dtype=float)
    p5 = float(pcm[_INP5])
    p6 = float(pcm[_INP6])
    p8 = float(pcm[_INP8])
    p9 = float(pcm[_INP9])
    l8 = float(leak[_INP8])
    l9 = float(leak[_INP9])
    avg_leak_89 = (l8 + l9) / 2.0

    large_cap = bool(prof.get("big_tech_scale_anchor")) or bool(prof.get("large_cap_revenue_anchor"))
    moat = bool(prof.get("p9_moat_hardening_narrative"))
    big_tech = bool(prof.get("big_tech_scale_anchor"))

    # Soberanía activa: mega-cap con narrativa de foso / plataforma AI o P9 muy alto con moat.
    active_sovereignty_exempt = moat and (p9 > 8.45 or big_tech)

    meta: dict[str, Any] = {
        "active": False,
        "exempt_active_sovereignty": bool(active_sovereignty_exempt),
        "p8_cell_mean": round(p8, 3),
        "p9_cell_mean": round(p9, 3),
        "avg_leak_p8_p9": round(avg_leak_89, 4),
    }

    if active_sovereignty_exempt:
        return integrity, meta

    if not large_cap:
        meta["reason"] = "not_large_cap"
        return integrity, meta
    if not (p5 > 8.0 and p6 > 8.0):
        meta["reason"] = "p5_p6_not_fortress"
        return integrity, meta

    # A) Sensor duro (especificación): P8 bajo pese a fortaleza institucional/económica.
    path_strategic_low = p8 < 7.0
    # B) Large cap «IBM»: P8 puede ser alto en papel, pero P8/P9 arrastran fuga fuerte sin ventaja estratégica clara vs P9.
    path_legacy_friction = (
        p8 >= 7.0
        and avg_leak_89 >= 0.68
        and p8 <= p9 + 0.4
        and p9 <= 8.62
    )

    if not (path_strategic_low or path_legacy_friction):
        meta["reason"] = "no_inertia_pattern"
        return integrity, meta

    if path_strategic_low:
        discount = 0.05 + 0.03 * float(max(0.0, min(1.0, (7.0 - p8) / 7.0)))
        meta["path"] = "strategic_sensor_low"
    else:
        discount = 0.085 + 0.025 * float(min(1.0, max(0.0, (avg_leak_89 - 0.68) / (1.02 - 0.68))))
        meta["path"] = "legacy_p8p9_friction"

    discount = float(min(0.11, max(0.05, discount)))
    meta["active"] = True
    meta["discount_rate"] = round(discount, 4)
    new_int = float(integrity) * (1.0 - discount)
    return new_int, meta


def germinal_startup_stage_active(report: dict) -> bool:
    """
    Etapa de vida «germinal» / startup de alto tiro: P8 y P9 muy altos (>7.5 en media de celdas)
    con P5 institucional bajo (<4.0). No implica colapso sistémico: madurez institucional rezagada
    frente a impulso estratégico y tecnológico.
    """
    pcm = report.get("power_cell_mean")
    if pcm is None:
        return False
    arr = np.asarray(pcm, dtype=float).reshape(-1)
    if arr.shape[0] < 10:
        return False
    p5 = float(arr[_GERMINAL_IDX_P5])
    p8 = float(arr[_GERMINAL_IDX_P8])
    p9 = float(arr[_GERMINAL_IDX_P9])
    return (
        p8 > GERMINAL_P8_P9_CELL_MEAN_MIN
        and p9 > GERMINAL_P8_P9_CELL_MEAN_MIN
        and p5 < GERMINAL_P5_CELL_MEAN_MAX
    )


def ignition_archetype_active(report: dict) -> bool:
    """
    Arquetipo Ignición: germinal clásico (P8/P9 altos, P5 bajo) o prospecto/S-1 con P8/P9 altos
    (P5 del tensor se lee como deuda institucional, no como junta cotizada madura).
    """
    prof = report.get("ingest_disclosure") or {}
    if bool(prof.get("established_sec_periodic_filing")):
        return False
    if germinal_startup_stage_active(report):
        return True
    if not bool(prof.get("offering_prospectus_context")):
        return False
    pcm = report.get("power_cell_mean")
    if pcm is None:
        return False
    arr = np.asarray(pcm, dtype=float).reshape(-1)
    if arr.shape[0] < 10:
        return False
    p8 = float(arr[_GERMINAL_IDX_P8])
    p9 = float(arr[_GERMINAL_IDX_P9])
    return p8 > GERMINAL_P8_P9_CELL_MEAN_MIN and p9 > GERMINAL_P8_P9_CELL_MEAN_MIN


def decadence_sovereign_active(report: dict) -> bool:
    """
    Large cap con base institucional instalada pero estrés financiero y fricción en el liderazgo
    tecnológico (p. ej. Intel): no es Ignición ni simple «barro».
    """
    prof = report.get("ingest_disclosure") or {}
    if not bool(prof.get("financial_decay_stress")):
        return False
    if not (bool(prof.get("large_cap_revenue_anchor")) or bool(prof.get("big_tech_scale_anchor"))):
        return False
    pcm = report.get("power_cell_mean")
    if pcm is None:
        return False
    arr = np.asarray(pcm, dtype=float).reshape(-1)
    if arr.shape[0] < 10:
        return False
    p5 = float(arr[4])
    leak = np.asarray(report["leakscore"], dtype=float)
    potency = np.asarray(report["potency100"], dtype=float)
    l9 = float(leak[8])
    p9_pot = float(potency[8])
    if p5 < 5.15:
        return False
    if p9_pot < 60.0:
        return False
    if l9 < 0.10:
        return False
    return True


def build_motor_debug_trace(core: dict | None) -> dict:
    """
    Instantánea JSON-serializable para depuración y export: medias por poder, germinal, ingest.
    No depende de Streamlit; usar al guardar JSON o en modo herramientas internas.
    """
    out: dict = {
        "trace_schema_version": 1,
        "thresholds": {
            "germinal_p8_p9_cell_mean_min": float(GERMINAL_P8_P9_CELL_MEAN_MIN),
            "germinal_p5_cell_mean_max": float(GERMINAL_P5_CELL_MEAN_MAX),
            "germinal_p5_benchmark_gap_note_min": float(GERMINAL_P5_BENCHMARK_GAP_NOTE_MIN),
        },
    }
    if not isinstance(core, dict):
        out["error"] = "core_missing"
        return out
    report = core.get("report")
    if not isinstance(report, dict):
        out["error"] = "report_missing"
        return out

    pcm = report.get("power_cell_mean")
    by_power: dict[str, float | None] = {}
    if pcm is not None:
        arr = np.asarray(pcm, dtype=float).reshape(-1)
        for i, (p_code, _, _, _) in enumerate(PODERES_INFO):
            by_power[p_code] = round(float(arr[i]), 3) if i < arr.shape[0] else None
    else:
        for p_code, _, _, _ in PODERES_INFO:
            by_power[p_code] = None
    out["power_cell_mean_by_power"] = by_power

    out["germinal_startup_stage_active"] = bool(germinal_startup_stage_active(report))

    prof = report.get("ingest_disclosure") or {}
    out["ingest_disclosure"] = {
        "financial_performance_anchor": bool(prof.get("financial_performance_anchor")),
        "big_tech_scale_anchor": bool(prof.get("big_tech_scale_anchor")),
        "large_cap_revenue_anchor": bool(prof.get("large_cap_revenue_anchor")),
        "established_sec_periodic_filing": bool(prof.get("established_sec_periodic_filing")),
        "financial_decay_stress": bool(prof.get("financial_decay_stress")),
        "p9_moat_hardening_narrative": bool(prof.get("p9_moat_hardening_narrative")),
        "healthy_disclosure_bias": bool(prof.get("healthy_disclosure_bias")),
        "strong_crisis_evidence": bool(prof.get("strong_crisis_evidence")),
        "critical_incident_evidence": bool(prof.get("critical_incident_evidence")),
        "offering_prospectus_context": bool(prof.get("offering_prospectus_context")),
        "prospectus_profitability_lift": bool(prof.get("prospectus_profitability_lift")),
        "tension_multiplier": prof.get("tension_multiplier"),
        "autofill_tension_drop_scale": prof.get("autofill_tension_drop_scale"),
    }
    out["ignition_archetype_active"] = bool(ignition_archetype_active(report))
    out["decadence_sovereign_active"] = bool(decadence_sovereign_active(report))
    out["inertial_sovereignty"] = report.get("inertial_sovereignty")
    out["decadence_sovereign"] = report.get("decadence_sovereignty")

    dp = core.get("decision_panel") if isinstance(core.get("decision_panel"), dict) else {}
    on = (dp.get("opportunity_note") or "").strip()
    out["panel_snapshot"] = {
        "archetype_name": str(core.get("archetype_name") or ""),
        "integrity": round(float(core.get("integrity", 0.0)), 3),
        "friction": round(float(core.get("friction", 0.0)), 3),
        "opportunity_note_set": bool(on),
    }
    return out


def compute_dependency_scores(report, flows):
    potency = np.asarray(report["potency100"], dtype=float)
    leak = np.asarray(report["leakscore"], dtype=float)
    avgm3 = np.asarray(report["avgm3"], dtype=float)
    avga = np.asarray(report["avga"], dtype=float)
    flow = np.asarray(flows, dtype=float)

    structural_base = (
        0.45 * potency +
        8.0 * flow +
        2.5 * avgm3 +
        2.5 * avga -
        6.0 * leak
    )

    min_v = float(np.min(structural_base))
    max_v = float(np.max(structural_base))

    if max_v - min_v < 1e-9:
        scores = np.full_like(structural_base, 50.0)
    else:
        scores = 100.0 * (structural_base - min_v) / (max_v - min_v)

    labels = []
    for s in scores:
        if s >= 75:
            labels.append("Poder tractor")
        elif s >= 55:
            labels.append("Poder de soporte")
        elif s >= 35:
            labels.append("Poder sensible")
        else:
            labels.append("Poder vulnerable")

    return scores, labels


def get_auto_profile(mode_name):
    if mode_name == "Estable":
        return {
            "P1": (7.0, 7.0, 7.0, 7.0, 7.0, 7.0),
            "P2": (7.0, 7.0, 7.0, 7.0, 7.0, 7.0),
            "P3": (7.2, 7.1, 7.1, 7.2, 7.0, 7.0),
            "P4": (6.8, 6.9, 6.9, 6.8, 6.9, 6.8),
            "P5": (7.3, 7.2, 7.4, 7.1, 7.2, 7.3),
            "P6": (7.1, 7.1, 7.0, 7.2, 7.1, 7.0),
            "P7": (6.9, 7.0, 7.1, 6.9, 7.0, 7.2),
            "P8": (7.0, 7.1, 7.0, 7.1, 7.0, 7.0),
            "P9": (7.1, 7.0, 7.0, 7.2, 7.0, 6.9),
            "P10": (6.9, 7.0, 7.1, 6.8, 7.0, 7.1),
        }

    if mode_name == "Tensión":
        return {
            "P1": (6.2, 7.4, 4.8, 6.1, 7.0, 5.0),
            "P2": (6.4, 7.8, 4.9, 6.2, 7.4, 5.1),
            "P3": (6.8, 8.0, 4.6, 6.9, 7.8, 4.8),
            "P4": (6.3, 7.5, 4.9, 6.0, 7.6, 5.0),
            "P5": (5.8, 6.4, 4.5, 5.7, 6.3, 4.7),
            "P6": (6.7, 7.2, 5.0, 6.8, 6.9, 5.1),
            "P7": (5.9, 6.5, 4.2, 5.8, 6.1, 4.6),
            "P8": (6.4, 7.1, 4.8, 6.5, 6.8, 4.9),
            "P9": (6.3, 6.9, 5.0, 6.6, 6.4, 5.0),
            "P10": (6.1, 6.8, 4.7, 6.0, 6.5, 4.9),
        }

    return {
        "P1": (5.0, 5.0, 5.0, 5.0, 5.0, 5.0),
        "P2": (5.0, 5.0, 5.0, 5.0, 5.0, 5.0),
        "P3": (5.0, 5.0, 5.0, 5.0, 5.0, 5.0),
        "P4": (5.0, 5.0, 5.0, 5.0, 5.0, 5.0),
        "P5": (5.0, 5.0, 5.0, 5.0, 5.0, 5.0),
        "P6": (5.0, 5.0, 5.0, 5.0, 5.0, 5.0),
        "P7": (5.0, 5.0, 5.0, 5.0, 5.0, 5.0),
        "P8": (5.0, 5.0, 5.0, 5.0, 5.0, 5.0),
        "P9": (5.0, 5.0, 5.0, 5.0, 5.0, 5.0),
        "P10": (5.0, 5.0, 5.0, 5.0, 5.0, 5.0),
    }


def generate_auto_base(org_type, tech_intensity, regulation_level, capital_intensity, competitive_pressure):
    base_map = {
        "P1": np.array([5.5, 5.5, 5.2, 5.4, 5.4, 5.2], dtype=float),
        "P2": np.array([5.2, 5.4, 5.0, 5.1, 5.2, 5.1], dtype=float),
        "P3": np.array([5.8, 6.0, 5.5, 5.8, 5.7, 5.8], dtype=float),
        "P4": np.array([5.6, 5.8, 5.5, 5.5, 5.8, 5.7], dtype=float),
        "P5": np.array([6.2, 6.0, 6.2, 6.1, 6.0, 6.2], dtype=float),
        "P6": np.array([6.0, 6.1, 5.9, 6.1, 6.0, 6.0], dtype=float),
        "P7": np.array([5.4, 5.3, 5.5, 5.3, 5.2, 5.6], dtype=float),
        "P8": np.array([5.8, 6.0, 5.6, 5.8, 5.7, 5.8], dtype=float),
        "P9": np.array([5.8, 5.9, 5.7, 5.9, 5.8, 5.8], dtype=float),
        "P10": np.array([5.7, 5.8, 5.7, 5.6, 5.8, 5.9], dtype=float),
    }

    if org_type == "Corporación tecnológica":
        base_map["P3"] += np.array([0.4, 0.6, 0.2, 0.3, 0.3, 0.4])
        base_map["P8"] += np.array([0.5, 0.6, 0.3, 0.4, 0.4, 0.4])
        base_map["P9"] += np.array([1.4, 1.2, 0.8, 1.2, 0.8, 0.6])
        base_map["P10"] += np.array([0.2, 0.4, 0.2, 0.1, 0.2, 0.3])

    elif org_type == "Corporación industrial":
        base_map["P1"] += np.array([0.5, 0.2, 0.1, 0.5, 0.2, 0.1])
        base_map["P5"] += np.array([0.8, 0.4, 0.8, 0.8, 0.3, 0.6])
        base_map["P6"] += np.array([1.0, 0.6, 0.6, 1.0, 0.4, 0.5])
        base_map["P9"] += np.array([0.5, 0.3, 0.3, 0.6, 0.2, 0.2])

    elif org_type == "Institución pública":
        base_map["P5"] += np.array([1.4, 1.0, 1.5, 1.2, 0.8, 1.2])
        base_map["P7"] += np.array([1.2, 1.0, 1.3, 1.0, 0.8, 1.4])
        base_map["P10"] += np.array([0.4, 0.6, 0.8, 0.2, 0.5, 0.9])

    elif org_type == "Startup":
        base_map["P2"] += np.array([0.4, 1.0, -0.3, 0.2, 0.5, 0.2])
        base_map["P3"] += np.array([0.7, 0.9, -0.2, 0.5, 0.4, 0.5])
        base_map["P8"] += np.array([0.8, 1.0, -0.4, 0.7, 0.5, 0.4])
        base_map["P9"] += np.array([1.0, 0.9, 0.1, 0.9, 0.5, 0.2])
        base_map["P5"] += np.array([-0.4, 0.0, -0.8, -0.3, -0.2, -0.4])

    elif org_type == "ONG / organización social":
        base_map["P2"] += np.array([0.4, 0.9, 0.3, 0.2, 0.6, 0.5])
        base_map["P4"] += np.array([0.8, 0.9, 0.4, 0.3, 0.9, 0.7])
        base_map["P10"] += np.array([0.5, 0.8, 0.6, 0.3, 0.7, 0.8])
        base_map["P6"] += np.array([-0.4, -0.2, -0.2, -0.3, -0.2, -0.2])

    tech_boost = (tech_intensity - 5.0) / 5.0
    reg_boost = (regulation_level - 5.0) / 5.0
    cap_boost = (capital_intensity - 5.0) / 5.0
    comp_boost = (competitive_pressure - 5.0) / 5.0

    base_map["P9"] += np.array([1.0, 0.8, 0.4, 0.9, 0.5, 0.3]) * tech_boost
    base_map["P8"] += np.array([0.6, 0.8, 0.3, 0.5, 0.4, 0.3]) * tech_boost

    base_map["P5"] += np.array([0.8, 0.5, 0.9, 0.7, 0.4, 0.8]) * reg_boost
    base_map["P7"] += np.array([0.5, 0.4, 0.6, 0.4, 0.3, 0.8]) * reg_boost

    base_map["P6"] += np.array([1.0, 0.7, 0.6, 0.9, 0.5, 0.5]) * cap_boost
    base_map["P5"] += np.array([0.2, 0.1, 0.3, 0.2, 0.1, 0.2]) * cap_boost

    base_map["P2"] += np.array([0.3, 0.7, -0.2, 0.1, 0.3, 0.1]) * comp_boost
    base_map["P3"] += np.array([0.5, 0.7, 0.0, 0.3, 0.3, 0.3]) * comp_boost
    base_map["P8"] += np.array([0.6, 0.7, 0.0, 0.4, 0.3, 0.2]) * comp_boost

    output = {}
    for p_code, vals in base_map.items():
        output[p_code] = tuple(np.clip(vals, 0.0, 10.0))

    return output


def apply_auto_base_to_session(auto_base):
    for p_code, vals in auto_base.items():
        m1, m2, m3, r, c, a = vals
        st.session_state[f"{p_code}_m1"] = float(m1)
        st.session_state[f"{p_code}_m2"] = float(m2)
        st.session_state[f"{p_code}_m3"] = float(m3)
        st.session_state[f"{p_code}_r"] = float(r)
        st.session_state[f"{p_code}_c"] = float(c)
        st.session_state[f"{p_code}_a"] = float(a)


def build_autobase_explanation(org_type, tech_intensity, regulation_level, capital_intensity, competitive_pressure):
    rows = []

    def level_label(v):
        if v >= 8:
            return "Muy alto"
        if v >= 6:
            return "Alto"
        if v >= 4:
            return "Medio"
        if v >= 2:
            return "Bajo"
        return "Muy bajo"

    rows.append({
        "Factor": "Tipo de organización",
        "Valor": org_type,
        "Impacto": "Define la arquitectura base del sistema."
    })

    rows.append({
        "Factor": "Intensidad tecnológica",
        "Valor": f"{tech_intensity:.1f} · {level_label(tech_intensity)}",
        "Impacto": "Ajusta principalmente P8 y P9."
    })

    rows.append({
        "Factor": "Nivel regulatorio",
        "Valor": f"{regulation_level:.1f} · {level_label(regulation_level)}",
        "Impacto": "Ajusta principalmente P5 y P7."
    })

    rows.append({
        "Factor": "Intensidad de capital",
        "Valor": f"{capital_intensity:.1f} · {level_label(capital_intensity)}",
        "Impacto": "Ajusta principalmente P6 y refuerza P5."
    })

    rows.append({
        "Factor": "Presión competitiva",
        "Valor": f"{competitive_pressure:.1f} · {level_label(competitive_pressure)}",
        "Impacto": "Ajusta principalmente P2, P3 y P8."
    })

    return pd.DataFrame(rows)


def load_demo_helios():
    helios_values = {
        "P1": (6.5, 6.2, 5.0, 6.0, 5.8, 5.2),
        "P2": (4.6, 7.1, 3.2, 4.3, 3.8, 4.1),
        "P3": (7.4, 8.0, 5.1, 7.1, 6.8, 7.4),
        "P4": (6.7, 6.3, 5.4, 6.0, 6.5, 6.2),
        "P5": (7.8, 5.6, 8.6, 7.5, 5.0, 7.9),
        "P6": (8.1, 7.0, 6.3, 8.2, 6.4, 6.8),
        "P7": (6.2, 5.8, 6.7, 6.0, 5.5, 7.2),
        "P8": (3.2, 4.1, 2.1, 3.0, 2.8, 2.4),
        "P9": (8.8, 7.9, 6.1, 8.5, 7.1, 5.8),
        "P10": (6.1, 6.8, 6.2, 5.9, 6.6, 7.1),
    }

    helios_flows = {
        "P1": -0.1,
        "P2": -1.4,
        "P3": 1.1,
        "P4": 0.4,
        "P5": -0.2,
        "P6": 0.6,
        "P7": 0.2,
        "P8": -1.9,
        "P9": 1.8,
        "P10": 0.3,
    }

    helios_notes = {
        "P2": "Desgaste emocional en equipos senior tras crecimiento acelerado y presión por entregas.",
        "P5": "La estructura formal crece más rápido que la capacidad real de coordinación horizontal.",
        "P8": "La empresa ejecuta mucho, pero prioriza mal y reacciona tarde en decisiones de tablero.",
        "P9": "Capacidad tecnológica muy alta, con excelencia ingenieril y fuerte escalabilidad técnica.",
    }

    for p_code, vals in helios_values.items():
        m1, m2, m3, r, c, a = vals
        st.session_state[f"{p_code}_m1"] = m1
        st.session_state[f"{p_code}_m2"] = m2
        st.session_state[f"{p_code}_m3"] = m3
        st.session_state[f"{p_code}_r"] = r
        st.session_state[f"{p_code}_c"] = c
        st.session_state[f"{p_code}_a"] = a

    for p_code, flow in helios_flows.items():
        st.session_state[f"{p_code}_flow"] = flow

    for p_code, _, _, _ in PODERES_INFO:
        st.session_state[f"{p_code}_note"] = helios_notes.get(p_code, "")
        st.session_state[f"{p_code}_source"] = "Mixto"
        st.session_state[f"{p_code}_confidence"] = 78

    st.session_state["loaded_target"] = "Helios Aerospace"
    st.session_state["loaded_client_name"] = "Demo"
    st.session_state["loaded_project_name"] = "Caso Helios"
    st.session_state["loaded_analyst_name"] = "Noumenon"


def build_tensor_from_session():
    T = build_empty_tensor()

    for i, (p_code, _, _, _) in enumerate(PODERES_INFO):
        m1 = float(st.session_state.get(f"{p_code}_m1", 5.0))
        m2 = float(st.session_state.get(f"{p_code}_m2", 5.0))
        m3 = float(st.session_state.get(f"{p_code}_m3", 5.0))
        r = float(st.session_state.get(f"{p_code}_r", 5.0))
        c = float(st.session_state.get(f"{p_code}_c", 5.0))
        a = float(st.session_state.get(f"{p_code}_a", 5.0))

        T = set_power_structured(T, i, m1, m2, m3, r, c, a)

    return T


def build_flows_from_session():
    flows = []

    for p_code, _, _, _ in PODERES_INFO:
        flows.append(float(st.session_state.get(f"{p_code}_flow", 0.0)))

    return flows


def compute_input_trace(auto_profile, T):
    rows = []

    for i, (p_code, p_title, _, _) in enumerate(PODERES_INFO):
        auto_m1, auto_m2, auto_m3, auto_r, auto_c, auto_a = auto_profile[p_code]

        auto_mean = float(np.mean([auto_m1, auto_m2, auto_m3, auto_r, auto_c, auto_a]))

        matrix = np.asarray(T[i], dtype=float)

        final_m1 = float(np.mean(matrix[0, :]))
        final_m2 = float(np.mean(matrix[1, :]))
        final_m3 = float(np.mean(matrix[2, :]))
        final_r = float(np.mean(matrix[:, 0]))
        final_c = float(np.mean(matrix[:, 1]))
        final_a = float(np.mean(matrix[:, 2]))

        final_mean = float(np.mean([final_m1, final_m2, final_m3, final_r, final_c, final_a]))
        delta = final_mean - auto_mean

        if abs(delta) < 0.25:
            lectura = "Alineado con modelo"
        elif delta > 0:
            lectura = "Corrección experta al alza"
        else:
            lectura = "Corrección experta a la baja"

        rows.append({
            "Poder": p_code,
            "Nombre": p_title,
            "Auto base": round(auto_mean, 2),
            "Valor final": round(final_mean, 2),
            "Delta": round(delta, 2),
            "Lectura": lectura
        })

    return pd.DataFrame(rows)


def build_evidence_table():
    rows = []

    for p_code, p_title, _, _ in PODERES_INFO:
        source = st.session_state.get(f"{p_code}_source", "Manual")
        confidence = st.session_state.get(f"{p_code}_confidence", 50)
        note = st.session_state.get(f"{p_code}_note", "").strip()

        evidence_status = "Sí" if note else "No"

        rows.append({
            "Poder": p_code,
            "Nombre": p_title,
            "Origen": source,
            "Confianza": int(confidence),
            "Evidencia": evidence_status,
            "Nota": note
        })

    return pd.DataFrame(rows)


def compute_executive_integrity(report: dict) -> float:
    """
    Integridad ejecutiva: no es 100 - media(leak); combina fuga media, dolor en M3/A
    (forma instituida y legitimidad) y señales de crisis de soberanía/institución.

    Objetivo: que textos de tragedia organizativa no muestren ~99 % de integridad por
    un tensor numéricamente «liso».
    """
    if "_executive_integrity_final" in report:
        return float(report["_executive_integrity_final"])

    leak = np.asarray(report["leakscore"], dtype=float)
    avgm3 = np.asarray(report["avgm3"], dtype=float)
    avga = np.asarray(report["avga"], dtype=float)
    mean_leak = float(np.mean(leak))
    prof = report.get("ingest_disclosure") or {}
    anchor_shield = bool(prof.get("financial_performance_anchor")) and not bool(
        prof.get("critical_incident_evidence")
    )
    healthy_doc = (
        bool(prof.get("healthy_disclosure_bias"))
        and not bool(prof.get("strong_crisis_evidence"))
        and not bool(prof.get("critical_incident_evidence"))
    )
    big_tech = bool(prof.get("big_tech_scale_anchor"))
    if healthy_doc:
        mean_leak = float(mean_leak * 0.72)
    if healthy_doc and big_tech:
        # Inercia de poder: mega-cap con disclosure sano no paga el mismo coste léxico en integridad.
        mean_leak = float(mean_leak * 0.93)
    # Dolor estructural y de legitimidad: desviación por debajo del punto medio sano (~5).
    m3_pain = float(np.mean(np.maximum(0.0, 5.0 - avgm3)) / 5.0)
    a_pain = float(np.mean(np.maximum(0.0, 5.0 - avga)) / 5.0)
    if healthy_doc:
        m3_pain = float(m3_pain * 0.88)
        a_pain = float(a_pain * 0.88)
    # Decaimiento exponencial (sensible a tragedia: fuga + debilidad de forma/legitimidad).
    k_l, k_m3, k_a = 0.98, 1.22, 1.22
    if healthy_doc:
        # mean_leak ya lleva ×0.72 (disclosure normativo); sin esto el término exp(-k_l·mean_leak)
        # seguiría anclando ~71 % en 10-K típicos. k_l más bajo solo aquí acerca 78–82 % sin tocar crisis.
        k_l = 0.705
    integrity = 100.0 * float(
        np.exp(-k_l * mean_leak - k_m3 * m3_pain - k_a * a_pain)
    )
    # Crisis de soberanía / institución / señal: choque típico P7 + P5 (+ P3 narrativo).
    idx_p7, idx_p5, idx_p3 = 6, 4, 2
    sovereignty_signal = float(leak[idx_p7]) + 0.62 * float(leak[idx_p5]) + 0.38 * float(leak[idx_p3])
    if not anchor_shield:
        if sovereignty_signal > 2.35 or (mean_leak > 0.58 and float(np.max(leak)) > 1.55):
            integrity = min(integrity, 76.0)
        # Tragedia distribuida: fuga generalizada + dispersión de fugas.
        if mean_leak > 0.68 and float(np.std(leak)) > 0.32:
            integrity = min(integrity, 68.0)
    # Crisis léxica: tope duro para no «soberanizar» informes de incidente grave o quiebra.
    if bool(prof.get("critical_incident_evidence")):
        integrity = min(integrity, 40.0)
    elif bool(prof.get("strong_crisis_evidence")):
        integrity = min(integrity, 52.0)
    if anchor_shield:
        integrity = max(float(integrity), 72.0)
        if healthy_doc and big_tech:
            integrity = max(float(integrity), 78.0)
        if healthy_doc:
            integrity = min(float(integrity), 82.0)
    # Escepticismo prospecto/S-1: el disclosure regulatorio no es soberanía ejecutiva cotizada.
    if bool(prof.get("offering_prospectus_context")) and not bool(prof.get("critical_incident_evidence")):
        integrity = float(integrity) * float(OFFERING_PROSPECTUS_INTEGRITY_SCALE)
        integrity = min(float(integrity), float(OFFERING_PROSPECTUS_INTEGRITY_CAP))
        integrity = max(float(integrity), float(OFFERING_PROSPECTUS_INTEGRITY_FLOOR))
    # Startup germinal: P5 bajo es esperable; suelo 50 % solo si el texto no grita crisis fuerte/incidente.
    if germinal_startup_stage_active(report) and not bool(prof.get("critical_incident_evidence")) and not bool(
        prof.get("strong_crisis_evidence")
    ):
        integrity = max(float(integrity), 50.0)

    if decadence_sovereign_active(report):
        x = float(integrity)
        integrity = min(x, 64.0)
        integrity = max(float(integrity), 60.0)
        report["decadence_sovereign"] = {"active": True, "pre_clip": round(x, 2)}
    else:
        report["decadence_sovereign"] = {"active": False}

    integrity, inertial_meta = _apply_inertial_sovereignty_discount(report, prof, float(integrity))
    report["inertial_sovereignty"] = inertial_meta

    # Chequeo de hardware basal: promedio M1 en P1, P6, P9 (cuerpo, caja, tecnología material).
    m1_core = report.get("m1_p1_p6_p9_mean")
    avgm1 = report.get("avgm1")
    if m1_core is None and avgm1 is not None:
        m1_arr = np.asarray(avgm1, dtype=float).ravel()
        if m1_arr.size >= 10:
            m1_core = float((m1_arr[0] + m1_arr[5] + m1_arr[8]) / 3.0)
    if m1_core is not None:
        m1_core_f = float(m1_core)
        if m1_core_f < 3.5:
            integrity = float(integrity) * 0.3
            report["hardware_basal_veto"] = {"active": True, "m1_p1_p6_p9_mean": round(m1_core_f, 3)}
            report["m1_vacuum_veto"] = {
                "active": True,
                "mean_m1": round(m1_core_f, 3),
                "scope": "P1_P6_P9_M1",
            }
        else:
            report["hardware_basal_veto"] = {"active": False, "m1_p1_p6_p9_mean": round(m1_core_f, 3)}
            report["m1_vacuum_veto"] = {
                "active": False,
                "mean_m1": round(m1_core_f, 3),
                "scope": "P1_P6_P9_M1",
            }
    else:
        report["hardware_basal_veto"] = {"active": False}
        report["m1_vacuum_veto"] = {"active": False, "reason": "no_avgm1"}

    out = float(np.clip(integrity, 12.0, 99.5))
    report["_executive_integrity_final"] = out
    return out


def executive_global_verdict(report_data: dict) -> str:
    """
    Veredicto global alineado con la integridad ejecutiva (valor absoluto).

    Si la integridad ejecutiva es < 60 %, no se permite etiqueta de «arquitectura soberana»:
    el motor interno puede leer tensor favorable; el juicio ejecutivo debe reflejar crisis persistente.

    Veto M1: si la materialidad operativa media colapsa, no se usa lenguaje de soberanía institucional
    (el dictamen ejecutivo desacopla el juicio del veredicto bruto del motor).
    """
    ei = compute_executive_integrity(report_data)
    m1vv = report_data.get("m1_vacuum_veto")
    if isinstance(m1vv, dict) and bool(m1vv.get("active")):
        mm = m1vv.get("mean_m1")
        try:
            mm_f = float(mm) if mm is not None else float("nan")
            mm_s = f"{mm_f:.2f}" if mm_f == mm_f else "—"
        except (TypeError, ValueError):
            mm_s = "—"
        if ei < 32.0:
            return (
                f"FALLO SISTÉMICO: vacío de materialidad operativa (M1 media {mm_s}/10). "
                "Sin cuerpo ejecutivo no hay lectura de soberanía estructural."
            )
        if ei < 60.0:
            return (
                f"COLAPSO DE BASE OPERATIVA: integridad ejecutiva degradada por M1 insuficiente (media {mm_s}/10); "
                "el dictamen no admite arquitectura soberana mientras falte masa material en el tensor."
            )
        return (
            f"TENSIÓN CON BASE M1 DÉBIL: integridad ejecutiva {ei:.1f} % con media M1 {mm_s}/10 — "
            "consolidación institucional no verificable en materialidad operativa."
        )

    engine_v = str(report_data.get("global_verdict", "") or "")
    u = engine_v.upper()

    if ei < 60.0:
        if ei < 32.0:
            return (
                "FALLO SISTÉMICO: integridad ejecutiva crítica; "
                "el sistema no puede calificarse como soberano mientras el gobierno real quede bajo umbral mínimo."
            )
        return (
            "GIGANTE DE BARRO: integridad ejecutiva inferior al 60 %; "
            "mejora relativa o simulada sin recuperación suficiente: no hay soberanía estructural."
        )

    dec_sov = report_data.get("decadence_sovereign") or {}
    if bool(dec_sov.get("active")) and ei >= 59.0:
        return (
            "DECADENCIA SOBERANA: escala e institución aún pesan, pero la erosión económica y la fricción "
            "tecnológica comprimen el margen de mando estructural frente al mercado."
        )

    inertial = report_data.get("inertial_sovereignty") or {}
    if bool(inertial.get("active")) and ei >= 60.0:
        return (
            "SOBERANÍA INERCIAL: solidez institucional y económica con inercia de legado; "
            "consolidación sin plena alineación estratégico-tecnológica frente al ritmo del mercado."
        )

    if ei < 72.0 and "SOBERANA" in u:
        return (
            "SOBERANÍA EXPUESTA: integridad ejecutiva aún en tensión; "
            "consolidación parcial sin mando institucional pleno."
        )

    return engine_v


def apply_executive_verdict_to_report(report_data: dict) -> None:
    """Sobrescribe global_verdict en el dict de reporte (mutación in-place)."""
    report_data["global_verdict"] = executive_global_verdict(report_data)


def _contradiction_message(p_code: str, kind: str, *, gap: float = 0.0) -> str:
    """Texto de contradicción por poder y tipo de desalineación (evita plantillas idénticas)."""
    g = max(0.0, min(4.0, gap))
    _ = g  # reservado para matices futuros
    copy = {
        "a_m3": {
            "P1": "El mandato simbólico o la exigencia de obediencia presionan más que la forma médica o biológica instituida: el cuerpo organizativo queda desprotegido frente al comando.",
            "P2": "Afecto y lealtad se viven como obligación moral por encima del reglamento: la legitimidad emocional desborda la estructura que debería contenerla.",
            "P3": "La versión oficial y el relato público mandan más que el procedimiento: la narrativa vence a la institución que debería sostenerla.",
            "P4": "La membresía o el estatus relacional pesan más que las reglas escritas: el grupo manda sobre la forma instituida.",
            "P5": "La autoridad reconocida y el deber de obediencia superan al reglamento y al cargo: la legitimidad práctica erosiona la forma jurídica.",
            "P6": "La promesa de retorno o la coacción del capital mandan más que el plan contable estable: el dinero exige obediencia antes que forma.",
            "P7": "La coerción o el mandato político pesan más que el ordenamiento estable: la soberanía efectiva se come al aparato normado.",
            "P8": "La lectura estratégica y el timing mandan más que el plan fijado: la inteligencia de maniobra desautoriza la estructura prevista.",
            "P9": "La promesa técnica o el control del stack mandan más que el estándar asentado: la herramienta impone su ley sobre la forma.",
            "P10": "El dogma o la verdad vivida mandan más que el método: la legitimidad cultural aplasta la forma epistémica.",
        },
        "m2_m3": {
            "P1": "La energía vital y el ritmo desbordan la clínica del sistema: el cuerpo sigue una lógica que la institución no alcanza a formalizar.",
            "P2": "Lealtad y emoción van delante del pacto escrito: el vínculo afectivo desborda la forma instituida y abre grieta de gobernanza.",
            "P3": "El mensaje y la urgencia comunicativa van delante del manual: la intención narrativa erosiona la portavocía estable.",
            "P4": "La tribu y el vínculo relacional mandan sobre el estatuto: la pertenencia viva desborda la membresía formal.",
            "P5": "La intención política interna y el mandato implícito van delante del expediente: la voluntad desautoriza la norma escrita.",
            "P6": "La apuesta y el apetito de mercado van delante del presupuesto: la intención financiera desborda la estructura de control.",
            "P7": "La movilización y el mandato de calle van delante del texto constitucional: la voluntad política rompe la forma del Estado.",
            "P8": "La maniobra y el impulso competitivo van delante del plan: la intención estratégica no está asentada en estructura.",
            "P9": "La ambición de producto y el sprint técnico van delante del estándar: la voluntad de ingeniería desborda la forma instituida.",
            "P10": "La creación de sentido y el relato fundacional van delante del canon: la intención cultural desborda la verdad asentada.",
        },
        "m1_m3": {
            "P1": "La capacidad operativa inmediata (turnos, carga, ejecución) supera la forma médica o administrativa: se ejecuta sin estructura que aguante.",
            "P2": "La acción emocional y el gesto colectivo van delante del acuerdo: la práctica supera el pacto instituido.",
            "P3": "El canal y el alcance activo superan al protocolo: la máquina comunicativa corre sin marco estable.",
            "P4": "La movilización y el contacto van delante del estatuto: la red opera más rápido que la forma.",
            "P5": "La práctica administrativa y el despacho van delante del reglamento: la ejecución supera la norma que debería ordenarla.",
            "P6": "La tesorería operativa y el flujo van delante del covenant: la ejecución financiera supera la estructura de gobierno.",
            "P7": "La fuerza desplegada y el hecho territorial van delante del ordenamiento: la capacidad fáctica supera la forma jurídica.",
            "P8": "La ejecución táctica y el movimiento de piezas van delante del plan maestro: la capacidad supera la arquitectura decidida.",
            "P9": "El despliegue y el stack activo van delante del estándar corporativo: la operación técnica supera la forma fijada.",
            "P10": "La producción simbólica y el artefacto van delante del canon: la práctica intelectual supera la verdad instituida.",
        },
        "power_leak": {
            "P1": "Potencia biológica alta con fuga fuerte: el sistema gasta cuerpo sin convertir capacidad en forma estable.",
            "P2": "Potencia emocional alta con fuga fuerte: hay vínculo e intensidad, pero la estructura no aguanta la presión afectiva.",
            "P3": "Potencia comunicativa alta con fuga fuerte: alcance y señal sin canal instituido que las contenga.",
            "P4": "Potencia relacional alta con fuga fuerte: masa y red sin institución que distribuya el poder.",
            "P5": "Potencia institucional alta con fuga fuerte: aparato pesado que pierde eficiencia por desalineación interna.",
            "P6": "Potencia económica alta con fuga fuerte: caja y mercado exigen, pero la arquitectura de control no sigue el ritmo.",
            "P7": "Potencia política alta con fuga fuerte: coerción y soberanía en tensión: el aparato pierde eficiencia normativa.",
            "P8": "Potencia estratégica alta con fuga fuerte: ventaja competitiva que se filtra por fricción estructural.",
            "P9": "Potencia tecnológica alta con fuga fuerte: capacidad técnica que no se traduce en forma estable (deuda y fricción).",
            "P10": "Potencia cultural alta con fuga fuerte: sentido y verdad en juego, pero la institución no amortigua el choque.",
        },
        "struct_no_legit": {
            "P1": "Forma biológica o administrativa rígida con legitimidad baja: el cuerpo organizativo queda expuesto a rechazo o desobediencia tácita.",
            "P2": "Rituales y normas visibles sin legitimidad emocional: la forma existe, pero el grupo no la cree.",
            "P3": "Protocolos y canales sin credibilidad: la estructura comunicativa es sólida en papel y débil en aceptación.",
            "P4": "Estatutos de red sin adhesión: la forma de pertenencia no obtiene reconocimiento vivido.",
            "P5": "Organigrama y reglamento sin mandato vivido: la institución es corpórea y hueca a la vez.",
            "P6": "Estructura financiera y covenant sin confianza de mercado: la forma contable no obtiene validación externa.",
            "P7": "Ordenamiento y frontera sin consentimiento político efectivo: la forma estatal se agrieta frente a la calle.",
            "P8": "Plan y prioridades sin mandato estratégico compartido: la forma del roadmap no obtiene legitimidad ejecutiva.",
            "P9": "Arquitectura técnica y estándares sin adopción: la forma del sistema no obtiene obediencia práctica.",
            "P10": "Canon y doctrina sin fe operativa: la forma intelectual no obtiene sumisión vivida.",
        },
        "r_c": {
            "P1": "Recursos vitales o de entorno abundantes, pero coordinación interna baja: el entorno alimenta sin tejer cohesión.",
            "P2": "Afecto y vínculo externos fuertes, coordinación interna baja: la energía relacional no se traduce en alineación.",
            "P3": "Alcance y audiencia amplios, pero coordinación interna baja: la señal llega sin disciplina de emisor único.",
            "P4": "Recursos de red y acceso abundantes, coordinación interna baja: el grafo conecta sin mando común.",
            "P5": "Mandos y recursos formales amplios, coordinación interna baja: el aparato existe sin sincronía.",
            "P6": "Liquidez o acceso a mercado fuertes, coordinación interna baja: el dinero circula sin gobierno único.",
            "P7": "Territorio o aparato coercitivo fuerte, coordinación política baja: el recurso soberano no alinea facciones.",
            "P8": "Inteligencia de mercado y posicionamiento fuertes, coordinación interna baja: la ventaja no se traduce en disciplina.",
            "P9": "Stack y capacidad técnica fuertes, coordinación interna baja: la tecnología escala sin gobierno común.",
            "P10": "Capital simbólico y verdad instituida fuertes, coordinación interna baja: el sentido no alinea prácticas.",
        },
    }
    block = copy.get(kind, {})
    return block.get(p_code, block.get("P5", "Desalineación estructural relevante entre materialidad y forma instituida."))


def detect_power_contradictions(T, report):
    contradictions = []

    potency = np.asarray(report["potency100"], dtype=float)
    leak = np.asarray(report["leakscore"], dtype=float)

    for i, (p_code, p_title, _, _) in enumerate(PODERES_INFO):
        matrix = np.asarray(T[i], dtype=float)

        avg_m1 = float(np.mean(matrix[0, :]))
        avg_m2 = float(np.mean(matrix[1, :]))
        avg_m3 = float(np.mean(matrix[2, :]))

        avg_r = float(np.mean(matrix[:, 0]))
        avg_c = float(np.mean(matrix[:, 1]))
        avg_a = float(np.mean(matrix[:, 2]))

        issues = []

        gap_plane = 2.05
        if avg_a > avg_m3 + gap_plane:
            issues.append(
                _contradiction_message(p_code, "a_m3", gap=avg_a - avg_m3)
            )

        if avg_m2 > avg_m3 + gap_plane:
            issues.append(
                _contradiction_message(p_code, "m2_m3", gap=avg_m2 - avg_m3)
            )

        if avg_m1 > avg_m3 + gap_plane:
            issues.append(
                _contradiction_message(p_code, "m1_m3", gap=avg_m1 - avg_m3)
            )

        if potency[i] > 62 and leak[i] > 2.25:
            issues.append(_contradiction_message(p_code, "power_leak"))

        if avg_m3 > 6.5 and avg_a < 4.0:
            issues.append(_contradiction_message(p_code, "struct_no_legit"))

        if avg_r > 6.5 and avg_c < 4.0:
            issues.append(_contradiction_message(p_code, "r_c"))

        if issues:
            contradictions.append({
                "poder": p_code,
                "nombre": p_title,
                "issues": issues
            })

    return contradictions


def build_future_scenario(report, flows, contradictions):
    potency = np.asarray(report["potency100"], dtype=float)
    leak = np.asarray(report["leakscore"], dtype=float)
    flow = np.asarray(flows, dtype=float)

    contradiction_count = {p[0]: 0 for p in PODERES_INFO}
    for item in contradictions:
        contradiction_count[item["poder"]] = len(item["issues"])

    future_potency = []
    future_friction = []
    future_labels = []

    for i, (p_code, p_title, _, _) in enumerate(PODERES_INFO):
        c_count = contradiction_count[p_code]

        flow_effect = flow[i] * 4.0
        leak_effect = leak[i] * 2.0
        contradiction_effect = c_count * 3.0

        projected_potency = potency[i] + flow_effect - leak_effect - contradiction_effect
        projected_potency = float(np.clip(projected_potency, 0.0, 100.0))

        projected_friction = leak[i] - (flow[i] * 0.15) + (c_count * 0.20)
        projected_friction = float(max(0.0, projected_friction))

        delta = projected_potency - potency[i]

        if delta >= 5:
            label = "Consolidación probable"
        elif delta >= 1:
            label = "Mejora moderada"
        elif delta <= -5:
            label = "Deterioro probable"
        elif delta <= -1:
            label = "Desgaste moderado"
        else:
            label = "Estabilidad probable"

        future_potency.append(projected_potency)
        future_friction.append(projected_friction)
        future_labels.append(label)

    return {
        "future_potency": np.array(future_potency, dtype=float),
        "future_friction": np.array(future_friction, dtype=float),
        "future_labels": future_labels
    }
