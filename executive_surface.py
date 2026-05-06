"""
Capa de salida «decisión ejecutiva» (Palantir-style): contrato único qué / por qué / si no.

No toca motor tensorial ni métricas; solo compone texto y estructura desde `core`.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from archetype_actions import get_archetype_action
from labels import INTERVENTION_LABELS, format_power_label, parse_intervention_number


def _intervention_verb(action_label: str | None) -> str:
    n = parse_intervention_number(action_label or "")
    if n == 1:
        return "Intervenir"
    if n == 2:
        return "Reforzar"
    if n == 3:
        return "Reordenar"
    if n == 4:
        return "Ejecutar intervención intensiva sobre"
    if n == 5:
        return "Reforzar autoridad y cohesión en"
    return "Actuar sobre"


def _intervention_family(action_label: str | None, friction: float, integrity: float) -> str:
    """Contención / reconstrucción / ofensiva — heurística de producto."""
    n = parse_intervention_number(action_label or "")
    if n in (4, 5) or friction >= 35:
        return "reconstrucción"
    if n in (1, 3) or integrity < 48:
        return "contención"
    if n == 2:
        return "ofensiva"
    # Fallback: alinear con contención (evita un cuarto tipo fuera del contrato de producto)
    return "contención"


def _priority_level(integrity: float, friction: float, final_level: str | None) -> str:
    fl = (final_level or "").strip().lower()
    if "alta" in fl or friction >= 38 or integrity <= 45:
        return "ALTO"
    if "media" in fl or friction >= 22 or integrity <= 58:
        return "MEDIO"
    return "BAJO"


def _deterioration_class(report: dict[str, Any], future_scenario: dict[str, Any] | None) -> str:
    if future_scenario is None or "future_potency" not in future_scenario:
        return "progresivo"
    p = np.asarray(report.get("potency100"), dtype=float).ravel()
    f = np.asarray(future_scenario.get("future_potency"), dtype=float).ravel()
    if p.size < 10 or f.size < 10:
        return "progresivo"
    delta_mean = float(np.mean(f[:10]) - np.mean(p[:10]))
    if delta_mean <= -4:
        return "irreversible"
    if delta_mean <= -1.5:
        return "crítico"
    return "progresivo"


def _decision_confidence(
    archetype_universal: dict[str, Any] | None,
    evidence_df: Any,
    delta_integrity: float,
    delta_friction: float,
) -> str:
    hybrid = bool(archetype_universal and archetype_universal.get("hybrid"))
    ev_mean: float | None = None
    if evidence_df is not None and not getattr(evidence_df, "empty", True):
        if hasattr(evidence_df, "columns") and "Confianza" in evidence_df.columns:
            try:
                ev_mean = float(np.mean(evidence_df["Confianza"]))
            except (TypeError, ValueError):
                ev_mean = None
    sim_strength = max(abs(float(delta_integrity)), abs(float(delta_friction)))
    if hybrid or (ev_mean is not None and ev_mean < 52):
        return "LOW"
    if ev_mean is not None and ev_mean >= 68 and sim_strength >= 0.4 and not hybrid:
        return "HIGH"
    return "MEDIUM"


def build_executive_decision_surface(core: dict[str, Any]) -> dict[str, Any]:
    """
    Construye los tres bloques de producto + confianza, sin recalcular tensores.

    Claves esperadas en `core` (como devuelve `build_core_output_impl`):
    integrity, friction, final_reco, ceo_insights, decision_panel, executive_decision,
    acted_power, action_label, current_top_risk, archetype_universal, report,
    future_scenario, evidence_df, sim_report (opcional).
    """
    integrity = float(core.get("integrity") or 0.0)
    friction = float(core.get("friction") or 0.0)
    final_reco = core.get("final_reco") or {}
    ceo = core.get("ceo_insights") or {}
    panel = core.get("decision_panel") or {}
    ex_dec = core.get("executive_decision") or {}
    au = core.get("archetype_universal")
    if not isinstance(au, dict):
        au = {}
    report = core.get("report") or {}
    future_scenario = core.get("future_scenario")
    evidence_df = core.get("evidence_df")

    acted = core.get("acted_power") or final_reco.get("acted_power")
    action_label = core.get("action_label") or final_reco.get("action_label")
    top_risk = core.get("current_top_risk") or "Sin riesgo prioritario"

    di = float(final_reco.get("delta_integrity") or 0.0)
    df = float(final_reco.get("delta_friction") or 0.0)

    target = format_power_label(str(acted)) if acted else "—"
    verb = _intervention_verb(str(action_label) if action_label else None)
    _ivn = parse_intervention_number(str(action_label))
    iv_type = INTERVENTION_LABELS.get(_ivn, "Intervención") if _ivn else "Intervención"

    motivo = str(ceo.get("core_problem") or panel.get("risk_msg") or "").strip()
    bench = core.get("benchmark_df")
    if bench is not None and not getattr(bench, "empty", True):
        if hasattr(bench, "columns") and "Gap" in bench.columns:
            try:
                gap_bit = f"Brecha media vs benchmark: {float(np.mean(bench['Gap'])):+.1f}."
                motivo = (motivo + (" " if motivo else "") + gap_bit).strip()
            except (TypeError, ValueError):
                pass
    if not motivo:
        motivo = "Brecha y fricción según tensor y benchmark."
    if top_risk and str(top_risk) != "Sin riesgo prioritario":
        risk_tag = f"Riesgo dominante {format_power_label(str(top_risk))}. "
        if risk_tag not in motivo[: len(risk_tag) + 8]:
            motivo = (risk_tag + motivo).strip()
    if len(motivo) > 260:
        motivo = motivo[:257] + "…"

    riesgo_no_actuar = str(ceo.get("cost_of_inaction") or ex_dec.get("impact") or "").strip()
    if len(riesgo_no_actuar) > 200:
        riesgo_no_actuar = riesgo_no_actuar[:197] + "…"

    prio = _priority_level(integrity, friction, str(final_reco.get("level") or ""))

    au_id = str(au.get("id") or "").strip()
    actions = get_archetype_action(au_id) if au_id else {"doctrina": "", "error": "", "palanca": ""}
    family = _intervention_family(str(action_label), friction, integrity)
    det_word = _deterioration_class(report, future_scenario if isinstance(future_scenario, dict) else None)

    conf = _decision_confidence(au, evidence_df, di, df)

    # Materialidad: mensaje operativo concreto (sin abstracto)
    nodo_codigo = str(acted) if acted and str(acted).startswith("P") else str(panel.get("lever_power") or acted or "")
    material_line = (
        f"Modular M1–M3 en el nodo {format_power_label(nodo_codigo)} según palanca del tensor; "
        f"ejes R/C/A como moduladores globales del informe."
        if nodo_codigo and str(nodo_codigo).startswith("P")
        else "Alinear materialidades del nodo objetivo con la simulación prioritaria."
    )
    pal_doc = str(actions.get("palanca") or "").strip()
    if pal_doc:
        material_line = f"{material_line} Palanca: {pal_doc}"

    block_decision = {
        "accion": f"{verb} {target} — {iv_type}".strip(),
        "nodo_objetivo": str(acted or ""),
        "motivo_estructural": motivo,
        "delta_integridad": round(di, 2),
        "delta_friccion": round(df, 2),
        "riesgo_inaccion": riesgo_no_actuar or "Pérdida de margen de maniobra frente al deterioro estructural.",
        "prioridad": prio,
    }

    block_movimiento = {
        "estructura": material_line,
        "error_arquetipo": str(actions.get("error") or "Reforzar hábitos que el tensor ya penaliza."),
        "tipo_intervencion": family,
        "doctrina": str(actions.get("doctrina") or ""),
        "palanca_doc": str(actions.get("palanca") or ""),
    }

    consec_text = str(ceo.get("cost_of_inaction") or "").strip()
    block_consecuencia = {
        "si_no_ejecuta": consec_text or "El sistema continúa la trayectoria actual de fuga estructural.",
        "tipo_deterioro": det_word,
    }

    det_plain = {"progresivo": "Progresivo", "crítico": "Crítico", "irreversible": "Irreversible"}.get(
        det_word, det_word[:1].upper() + det_word[1:] if det_word else ""
    )
    fam_plain = family[:1].upper() + family[1:] if family else ""

    # Texto plano único (<10s lectura) para UI/PDF
    lines = [
        "=== DECISIÓN EJECUTIVA ===",
        f"• Acción: {block_decision['accion']}",
        f"• Nodo objetivo: {target}",
        f"• Motivo: {block_decision['motivo_estructural']}",
        f"• Impacto esperado: Δ integridad {block_decision['delta_integridad']:+g} · Δ fricción {block_decision['delta_friccion']:+g}",
        f"• Riesgo de no actuar: {block_decision['riesgo_inaccion']}",
        f"• Prioridad: {prio}",
        "",
        "=== MOVIMIENTO OPERATIVO ===",
        f"• Estructura: {block_movimiento['estructura']}",
        f"• Evitar (error del arquetipo): {block_movimiento['error_arquetipo']}",
        f"• Tipo: {fam_plain}",
        "",
        "=== CONSECUENCIA ===",
        f"• Si no se ejecuta: {block_consecuencia['si_no_ejecuta']}",
        f"• Deterioro: {det_plain}",
        "",
        f"decision_confidence: {conf}",
    ]
    plain = "\n".join(lines)

    return {
        "decision_ejecutiva": block_decision,
        "movimiento_operativo": block_movimiento,
        "consecuencia": block_consecuencia,
        "decision_confidence": conf,
        "plain_text": plain,
    }
