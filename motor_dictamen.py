"""
Núcleo del dictamen Trabajo (motor + simulación + texto ejecutivo) sin Streamlit.
Usado por la suite Fase 2.9 y por app.build_core_output (con evidencia de sesión).
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from engine_akxom import run_engine, compute_power_flow
from labels import INTERVENTION_LABELS, POWER_LABELS, format_power_label, parse_intervention_number
from simulation import build_final_recommendation, simulate_intervention_outcome

from analysis import (
    apply_executive_verdict_to_report,
    compute_dependency_scores,
    compute_executive_integrity,
    compute_input_trace,
    detect_power_contradictions,
    build_future_scenario,
)

from akxom_archetypes import identify_archetype

from akxom_intelligence import (
    detect_structural_archetype,
    build_intervention_recommendations,
    build_benchmark_table,
    build_board_summary,
    build_ceo_insights,
    build_intervention_strategies,
    build_executive_decision_panel,
)

from archetype_action_engine import build_action_plan
from decision_scenarios import build_decision_scenarios, merge_scenarios_executive_plain_text
from executive_surface import build_executive_decision_surface
from executive_view import build_executive_view


def _placeholder_evidence_df() -> pd.DataFrame:
    """Confianza neutra cuando no hay tabla de evidencia (suite / tests)."""
    return pd.DataFrame({"Confianza": [55.0] * 10})


def build_core_output_impl(
    T,
    flows,
    target,
    benchmark_name,
    auto_profile,
    evidence_df: pd.DataFrame | None = None,
    manual_sim=None,
    ingest_disclosure: dict | None = None,
):
    """
    Equivalente a build_core_output en app.py sin dependencia de st.session_state.
    Si evidence_df es None, usa placeholder para build_board_summary.
    """
    evidence_df = evidence_df if evidence_df is not None else _placeholder_evidence_df()

    result = run_engine(T, target if target else "Unknown")
    report = result["report_data"]
    if ingest_disclosure:
        report["ingest_disclosure"] = ingest_disclosure
    apply_executive_verdict_to_report(report)

    flow_labels = compute_power_flow(flows)
    dependency_scores, dependency_labels = compute_dependency_scores(report, flows)
    trace_df = compute_input_trace(auto_profile, T)
    contradictions = detect_power_contradictions(T, report)
    future_scenario = build_future_scenario(report, flows, contradictions)
    benchmark_df = build_benchmark_table(report, benchmark_name)

    integrity = compute_executive_integrity(report)
    friction = np.mean(report["leakscore"]) * 10

    archetype_name, archetype_desc = detect_structural_archetype(report)

    _ev_mean = None
    if evidence_df is not None and not evidence_df.empty and "Confianza" in evidence_df.columns:
        try:
            _ev_mean = float(np.mean(evidence_df["Confianza"]))
        except Exception:
            _ev_mean = None
    archetype_universal = identify_archetype(
        report,
        executive_integrity=float(integrity),
        friction=float(friction),
        flows=flows,
        evidence_confidence_mean=_ev_mean,
        contradictions=contradictions,
    )

    recommendations = build_intervention_recommendations(report)

    decision_panel = build_executive_decision_panel(
        report=report,
        benchmark_df=benchmark_df,
        future_scenario=future_scenario,
        recommendations=recommendations,
        contradictions=contradictions,
        executive_integrity=integrity,
        archetype_name=archetype_name,
    )

    ceo_insights = build_ceo_insights(
        report=report,
        benchmark_df=benchmark_df,
        future_scenario=future_scenario,
        contradictions=contradictions,
        executive_integrity=integrity,
        archetype_name=archetype_name,
    )

    intervention_strategies = build_intervention_strategies(
        report=report,
        benchmark_df=benchmark_df,
        future_scenario=future_scenario,
        contradictions=contradictions,
        executive_integrity=integrity,
        archetype_name=archetype_name,
    )

    intervention_outcome = simulate_intervention_outcome(
        T=T,
        report=report,
        intervention_strategies=intervention_strategies,
        target=target,
        prioritize_institutional_build=(str(archetype_name or "").strip() == "Ignición"),
    )

    sim_report = intervention_outcome["sim_report"]
    if ingest_disclosure:
        sim_report["ingest_disclosure"] = ingest_disclosure
    acted_power = intervention_outcome["acted_power"]
    action_label = intervention_outcome["action_label"]
    apply_executive_verdict_to_report(sim_report)

    simulated_integrity = compute_executive_integrity(sim_report)
    simulated_friction = np.mean(sim_report["leakscore"]) * 10

    current_top_risk = report["top3_risks_labels"][0] if report["top3_risks_labels"] else "Sin riesgo prioritario"

    board_summary_lines = build_board_summary(
        report=report,
        integrity=integrity,
        friction=friction,
        archetype_name=archetype_name,
        benchmark_df=benchmark_df,
        future_scenario=future_scenario,
        evidence_df=evidence_df,
        acted_power=acted_power,
        action_label=action_label,
        archetype_universal_name=str(archetype_universal.get("name") or "").strip() or None,
        archetype_universal_id=str(archetype_universal.get("id") or "").strip() or None,
    )
    simulated_top_risk = sim_report["top3_risks_labels"][0] if sim_report["top3_risks_labels"] else "Sin riesgo prioritario"

    final_reco = build_final_recommendation(
        report=report,
        decision_panel=decision_panel,
        intervention_outcome=intervention_outcome,
        current_integrity=integrity,
        current_friction=friction,
        simulated_integrity=simulated_integrity,
        simulated_friction=simulated_friction,
        current_top_risk=current_top_risk,
        simulated_top_risk=simulated_top_risk,
        manual_sim=manual_sim,
        archetype_name=archetype_name,
    )

    recommended_power = final_reco["acted_power"] if final_reco["acted_power"] else current_top_risk
    recommended_action_label = final_reco["action_label"] if final_reco["action_label"] else f"Intervención sobre {recommended_power}"

    if final_reco["delta_friction"] < 0:
        result_phrase = f"reducir la fricción estructural en {abs(final_reco['delta_friction']):.1f} puntos"
    elif final_reco["delta_integrity"] > 0:
        result_phrase = f"mejorar la integridad en {final_reco['delta_integrity']:+.1f} puntos"
    else:
        result_phrase = "generar una mejora estructural limitada"

    if recommended_action_label in ["Sin intervención recomendada", "Sin intervención necesaria"] or final_reco["title"] == "No intervenir":
        one_liner = "No intervengas este ciclo; vigila activamente y reacciona solo ante shock externo."
    else:
        iv_num = parse_intervention_number(recommended_action_label)
        iv_type = INTERVENTION_LABELS.get(iv_num, "Intervención estratégica")
        t = iv_type.lower()
        rp = format_power_label(str(recommended_power))
        cr = format_power_label(str(current_top_risk))
        if (
            recommended_power
            and current_top_risk
            and str(current_top_risk) != "Sin riesgo prioritario"
            and str(recommended_power) != str(current_top_risk)
        ):
            one_liner = (
                f"Riesgo crítico detectado en {cr}. "
                f"Palanca de impacto simulada en {rp}: ejecuta {t} ({result_phrase})."
            )
        else:
            one_liner = f"Ejecuta {t} en {rp}: {result_phrase}."

    executive_decision = generate_executive_decision(
        acted_power=recommended_power,
        action_label=recommended_action_label,
        delta_friction=final_reco["delta_friction"],
        core_problem=current_top_risk,
    )

    executive_surface = build_executive_decision_surface(
        {
            "integrity": integrity,
            "friction": friction,
            "final_reco": final_reco,
            "ceo_insights": ceo_insights,
            "decision_panel": decision_panel,
            "executive_decision": executive_decision,
            "acted_power": acted_power,
            "action_label": action_label,
            "current_top_risk": current_top_risk,
            "archetype_universal": archetype_universal,
            "report": report,
            "future_scenario": future_scenario,
            "evidence_df": evidence_df,
            "benchmark_df": benchmark_df,
        }
    )

    _lever_plan = decision_panel.get("lever_power") or acted_power
    action_plan = build_action_plan(
        str(archetype_universal.get("id") or ""),
        current_top_risk,
        _lever_plan,
    )

    _out = {
        "result": result,
        "report": report,
        "flow_labels": flow_labels,
        "dependency_scores": dependency_scores,
        "dependency_labels": dependency_labels,
        "trace_df": trace_df,
        "contradictions": contradictions,
        "evidence_df": evidence_df,
        "future_scenario": future_scenario,
        "benchmark_df": benchmark_df,
        "integrity": integrity,
        "friction": friction,
        "archetype_name": archetype_name,
        "archetype_desc": archetype_desc,
        "archetype_universal": archetype_universal,
        "recommendations": recommendations,
        "decision_panel": decision_panel,
        "ceo_insights": ceo_insights,
        "intervention_strategies": intervention_strategies,
        "board_summary_lines": board_summary_lines,
        "intervention_outcome": intervention_outcome,
        "sim_report": sim_report,
        "acted_power": acted_power,
        "action_label": action_label,
        "simulated_integrity": simulated_integrity,
        "simulated_friction": simulated_friction,
        "current_top_risk": current_top_risk,
        "simulated_top_risk": simulated_top_risk,
        "final_reco": final_reco,
        "one_liner": one_liner,
        "executive_decision": executive_decision,
        "executive_surface": executive_surface,
        "action_plan": action_plan,
    }
    _out["executive_view"] = build_executive_view(_out)
    _out["decision_scenarios"] = build_decision_scenarios(_out)
    _out["executive_view"] = merge_scenarios_executive_plain_text(
        _out["executive_view"],
        _out["decision_scenarios"],
    )
    return _out


def generate_executive_decision(acted_power, action_label, delta_friction, core_problem):
    if (
        not acted_power
        or acted_power == "Sin riesgo prioritario"
        or not action_label
        or action_label in ["Sin intervención necesaria", "Sin intervención recomendada"]
    ):
        return {
            "title": "Preservar arquitectura actual",
            "impact": "No se detecta mejora marginal relevante porque el sistema ya opera en equilibrio estructural.",
            "warning": "La prioridad no es intervenir, sino mantener vigilancia y evitar sobreintervención.",
        }

    power_label = POWER_LABELS.get(acted_power, acted_power)
    intervention_number = parse_intervention_number(action_label)
    intervention_label = INTERVENTION_LABELS.get(intervention_number, "Intervención estratégica")

    title = f"{intervention_label} en {power_label}"
    df = float(delta_friction)
    friction_pts = abs(df)

    core_ok = bool(
        core_problem
        and str(core_problem) != "Sin riesgo prioritario"
    )
    risk_mismatch = bool(
        core_ok and str(acted_power) != str(core_problem)
    )

    risk_fmt = format_power_label(str(core_problem)) if core_ok else None
    lever_fmt = format_power_label(str(acted_power))

    if risk_mismatch and risk_fmt:
        impact = (
            f"Aunque el núcleo del riesgo estructural reside en {risk_fmt}, "
            f"la máxima eficiencia de intervención se localiza en {lever_fmt}. "
            f"Se recomienda actuar sobre {lever_fmt} para estabilizar el sistema global."
        )
        # delta_friction = sim - actual: negativo implica menor fricción (mejora).
        if df < -0.05:
            impact += f" La simulación estima una reducción de fricción global de {abs(df):.1f} puntos."
        elif df > 0.05:
            impact += f" La simulación proyecta Δ fricción global {df:+.1f} puntos (validar supuestos del experimento)."
        warning = (
            f"Mantén vigilancia sobre el frente {risk_fmt}: puede seguir tensionado hasta una segunda "
            f"intervención focalizada sobre ese núcleo."
        )
    else:
        impact = (
            f"Reduce la fricción estructural en {friction_pts:.1f} puntos sin comprometer la estabilidad del sistema."
        )
        warning = "Actúa directamente sobre el núcleo estructural del sistema."

    return {
        "title": title,
        "impact": impact,
        "warning": warning,
    }
