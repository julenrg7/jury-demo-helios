"""
Consola Noumenon — Executive View primero (decisión en una pantalla);
el resto del dictamen va en paneles desplegables.
"""

from __future__ import annotations

import html
import json
from collections.abc import Callable
from typing import Any

import numpy as np
import streamlit as st

from akxom_oracular_report import build_oracular_report_html, professional_audit_pdf_filename
from archetype_action_engine import build_action_plan
from causal_chain import build_causal_chain
from decision_scenarios import (
    build_decision_scenarios,
    merge_scenarios_executive_plain_text,
    scenarios_streamlit_inner_html,
)
from executive_surface import build_executive_decision_surface
from executive_view import build_executive_view
from trabajo_detail_collapsed import render_trabajo_detail_collapsed
from analysis import build_motor_debug_trace
from labels import format_power_label, replace_power_codes_in_text
from report_visuals import build_potency_radar_svg
from storage import build_analysis_payload, save_analysis_json
from engine_akxom import PODERES_INFO

from ui_tokens import (
    SIGNAL_CYAN,
    SIGNAL_SKY,
    DECISION_GOLD,
    SIGNAL_GOOD,
    SIGNAL_BAD,
    SIGNAL_NEUTRAL,
    STRUCT_MID_BLUE,
    INTERVENTION_BLUE,
    INTERVENTION_LIGHT_BLUE,
)


def render_trabajo_hero() -> None:
    st.markdown(
        f"""
        <div style="margin:0 0 0 0;text-align:left;max-width:100%;">
            <p style="font-family:ui-monospace,'Courier New',monospace;font-size:11px;letter-spacing:0.14em;
            color:#737373;text-transform:uppercase;margin:0 0 12px 0;">
                Noumenon · Akxom OS™
            </p>
            <p style="font-size:22px;font-weight:800;color:#E5E7EB;margin:0 0 14px 0;line-height:1.2;">
                Executive View
            </p>
            <p style="font-size:15px;color:{DECISION_GOLD};font-weight:600;margin:0 0 30px 0;line-height:1.55;">
                Primero la decisión: situación, mandato, acción ejecutable, impacto y riesgo. Todo lo demás —diagnóstico, evidencia, mapa— queda un clic abajo.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <div style="display:flex;flex-wrap:wrap;gap:10px;margin:0 0 40px 0;">
            <span style="font-family:ui-monospace,'Courier New',monospace;font-size:11px;padding:6px 12px;
            border-radius:999px;border:1px solid #333;color:#a3a3a3;">01 · Contexto</span>
            <span style="font-family:ui-monospace,'Courier New',monospace;font-size:11px;padding:6px 12px;
            border-radius:999px;border:1px solid #333;color:#a3a3a3;">02 · Arquitectura</span>
            <span style="font-family:ui-monospace,'Courier New',monospace;font-size:11px;padding:6px 12px;
            border-radius:999px;border:1px solid #333;color:#a3a3a3;">03 · Tendencia</span>
            <span style="font-family:ui-monospace,'Courier New',monospace;font-size:11px;padding:6px 12px;
            border-radius:999px;border:1px solid {DECISION_GOLD};color:{DECISION_GOLD};background:#141208;">04 · Decisión</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _md_insight(s: str) -> str:
    return replace_power_codes_in_text(s or "")


def _safe_html(s: str) -> str:
    return html.escape(_md_insight(s))


def _perceptualize_text(text: str | None) -> str:
    """
    Noumenon (Ax layer): ajustes mínimos de lectura sin muletillas tipo «tiende a».
    El bloque Dictamen (05) no usa esta función: va alineado con el PDF.
    """
    if not text:
        return ""

    t = str(text)

    t = t.replace("se concentra en", "concentra el foco en")
    t = t.replace("debería centrarse en", "debe centrarse en")
    t = t.replace("prioritaria debería", "prioritaria: debe")
    t = t.replace("presenta la mayor brecha", "expone la mayor brecha")
    t = t.replace(
        "actúa como principal base de estabilidad relativa",
        "ancla la estabilidad relativa",
    )
    t = t.replace("La estructura proyecta", "El tensor proyecta")

    return t


def render_trabajo_results(
    core: dict[str, Any],
    *,
    client_name: str,
    project_name: str,
    analyst_name: str,
    target: str,
    T: Any,
    flows: list[float],
    benchmark_name: str,
    app_version: str,
    generate_pdf_from_html: Callable[[str], str],
    run_at: str | None = None,
    input_fingerprint: str | None = None,
) -> None:
    report = core["report"]
    result = core["result"]
    benchmark_df = core["benchmark_df"]
    integrity = core["integrity"]
    friction = core["friction"]
    decision_panel = core["decision_panel"]
    ceo_insights = core["ceo_insights"]
    sim_report = core["sim_report"]
    acted_power = core["acted_power"]
    action_label = core["action_label"]
    simulated_integrity = core["simulated_integrity"]
    simulated_friction = core["simulated_friction"]
    current_top_risk = core["current_top_risk"]
    simulated_top_risk = core["simulated_top_risk"]
    final_reco = core["final_reco"]
    one_liner = core["one_liner"]
    evidence_df = core["evidence_df"]
    trace_df = core.get("trace_df")
    flow_labels = core.get("flow_labels") or []
    contradictions = core.get("contradictions") or []
    board_summary_lines = core["board_summary_lines"]
    archetype_name = core["archetype_name"]
    archetype_universal = core.get("archetype_universal") or {}
    intervention_strategies = core["intervention_strategies"]
    future_scenario = core["future_scenario"]

    executive_surface = core.get("executive_surface")
    if executive_surface is None:
        executive_surface = build_executive_decision_surface(core)

    action_plan = core.get("action_plan")
    if action_plan is None:
        action_plan = build_action_plan(
            str((archetype_universal or {}).get("id") or ""),
            current_top_risk,
            decision_panel.get("lever_power") or acted_power,
        )

    # Ax (Noumenon): señal funcional de cambio vs estabilidad.
    delta_integrity = simulated_integrity - integrity
    delta_friction = simulated_friction - friction
    NOU_GOOD = SIGNAL_GOOD
    NOU_BAD = SIGNAL_BAD
    NOU_NEUTRAL = SIGNAL_NEUTRAL
    integrity_eps = 0.05
    friction_eps = 0.05

    if abs(delta_integrity) <= integrity_eps and abs(delta_friction) <= friction_eps:
        signal_color = NOU_NEUTRAL
        signal_text = "SEÑAL ESTABLE"
    else:
        # Mejora: aumenta integridad y/o disminuye fricción.
        # Deterioro: baja integridad y/o sube fricción.
        is_good = (delta_integrity > integrity_eps and abs(delta_friction) <= friction_eps) or (
            delta_friction < -friction_eps and abs(delta_integrity) <= integrity_eps
        ) or (delta_integrity > integrity_eps and delta_friction < -friction_eps)
        if is_good:
            signal_color = NOU_GOOD
            signal_text = "SEÑAL MEJORA"
        else:
            signal_color = NOU_BAD
            signal_text = "SEÑAL DETERIORO"

    st.divider()
    st.markdown("## Executive View")
    st.caption(
        "Lectura asistida; validar con hechos. Dato externo contradictorio prevalece. No sustituye mandato humano."
    )
    executive_view = core.get("executive_view")
    decision_scenarios = core.get("decision_scenarios")
    if not isinstance(decision_scenarios, dict):
        decision_scenarios = build_decision_scenarios(core)
    if executive_view is None or not str((executive_view or {}).get("decision") or "").strip():
        executive_view = build_executive_view(core)
        executive_view = merge_scenarios_executive_plain_text(executive_view, decision_scenarios)
    scen_card_html = scenarios_streamlit_inner_html(
        decision_scenarios,
        gold_hex=DECISION_GOLD,
        label_muted_hex="#9ca3af",
        line_mono_hex="#bbf7d0",
        safe_html=_safe_html,
    )

    ev = executive_view
    _low_conf = str(ev.get("decision_confidence") or "").upper() == "LOW"
    if _low_conf:
        st.caption(
            "Confianza de decisión baja en esta corrida: contrastar con fuentes primarias antes de ejecutar."
        )
    _ecf = (
        "#4ade80"
        if str(ev.get("decision_confidence")) == "HIGH"
        else ("#fbbf24" if str(ev.get("decision_confidence")) == "MEDIUM" else "#f87171")
    )
    _ns = str(ev.get("next_step") or "").strip()
    st.markdown(
        f"""
        <div style='padding:24px 26px;border:2px solid {DECISION_GOLD};border-radius:18px;background:linear-gradient(165deg,#090909 0%,#121212 100%);margin-bottom:16px;'>
            <p style='font-size:10px;font-weight:800;color:{DECISION_GOLD};letter-spacing:0.2em;text-transform:uppercase;margin:0 0 16px 0;'>Executive View</p>
            <p style='font-size:11px;font-weight:800;color:{SIGNAL_CYAN};text-transform:uppercase;letter-spacing:0.1em;margin:0 0 6px 0;'>Situación</p>
            <p style='font-size:16px;line-height:1.55;color:#e5e7eb;margin:0 0 18px 0;max-width:52ch;'>{_safe_html(str(ev.get("situation") or ""))}</p>
            <p style='font-size:11px;font-weight:800;color:{SIGNAL_SKY};text-transform:uppercase;letter-spacing:0.1em;margin:0 0 6px 0;'>Decisión</p>
            <p style='font-size:17px;font-weight:800;color:#e0f2fe;line-height:1.4;margin:0 0 18px 0;max-width:54ch;'>{_safe_html(str(ev.get("decision") or ""))}</p>
            <p style='font-size:11px;font-weight:800;color:{DECISION_GOLD};text-transform:uppercase;letter-spacing:0.1em;margin:0 0 6px 0;'>Acción crítica</p>
            <p style='font-size:19px;font-weight:800;color:#F9FAFB;line-height:1.35;margin:0 0 18px 0;border-left:4px solid {DECISION_GOLD};padding-left:14px;'>{_safe_html(str(ev.get("critical_action") or ""))}</p>
            <p style='font-size:11px;font-weight:800;color:{SIGNAL_SKY};text-transform:uppercase;letter-spacing:0.1em;margin:0 0 6px 0;'>Impacto</p>
            <p style='font-size:17px;font-weight:700;font-family:ui-monospace,'Courier New',monospace;color:#bbf7d0;margin:0 0 18px 0;'>{_safe_html(str(ev.get("impact") or ""))}</p>
            <p style='font-size:11px;font-weight:800;color:#fca5a5;text-transform:uppercase;letter-spacing:0.1em;margin:0 0 6px 0;'>Riesgo de no actuar</p>
            <p style='font-size:15px;line-height:1.5;color:#fecaca;margin:0 0 14px 0;max-width:52ch;'>{_safe_html(str(ev.get("risk") or ""))}</p>
            {scen_card_html}
            <p style='font-size:12px;color:{SIGNAL_NEUTRAL};margin:0;'>Confianza decisión: <span style='color:{_ecf};font-weight:800;'>{html.escape(str(ev.get("decision_confidence") or ""))}</span>{(" · Modo: preservar (sin intervención recomendada)" if ev.get("preserve_mode") else "")}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if _ns and not ev.get("preserve_mode"):
        st.markdown(
            f"<p style='font-size:14px;color:#d4d4d4;margin:0 0 12px 0;'><strong>Próximo paso:</strong> {_safe_html(_ns)}</p>",
            unsafe_allow_html=True,
        )
    causal_chain = core.get("causal_chain")
    if not isinstance(causal_chain, dict):
        causal_chain = build_causal_chain(
            core.get("signals_applied"),
            T,
            current_top_risk,
        )
    _steps = causal_chain.get("steps") or []
    _conc = str(causal_chain.get("conclusion") or "").strip()
    if _steps or _conc:
        st.markdown("### CADENA CAUSAL")
        for i, step in enumerate(_steps[:4], start=1):
            st.markdown(f"{i}. {_md_insight(str(step))}")
        st.markdown("**Conclusión:**")
        st.markdown(_md_insight(_conc))
    st.caption("Cierre operativo sugerido (acta interna): completar dueño asignado y fecha de revisión.")

    with st.expander("Diagnóstico completo · evidencia · mapa tensorial · palanca · trazabilidad", expanded=False):
        render_trabajo_detail_collapsed(
            core,
            T,
            flows,
            executive_surface=executive_surface,
            action_plan=action_plan,
            signal_color=signal_color,
            signal_text=signal_text,
        )

    st.markdown("#### Exportar y persistencia")
    report_html = build_oracular_report_html(
        client_name=client_name,
        project_name=project_name,
        analyst_name=analyst_name,
        target=target,
        current_integrity=integrity,
        current_friction=friction,
        current_top_risk=current_top_risk,
        report=report,
        final_reco=final_reco,
        one_liner=one_liner,
        decision_panel=decision_panel,
        benchmark_name=benchmark_name,
        benchmark_df=benchmark_df,
        archetype_universal=archetype_universal,
        ceo_insights=ceo_insights,
        evidence_df=evidence_df,
        trace_df=trace_df,
        tensor_T=T,
        future_scenario=future_scenario,
        run_at=run_at,
        app_version=app_version,
        input_fingerprint=input_fingerprint,
        executive_surface=executive_surface,
        action_plan=action_plan,
        executive_view=executive_view,
        decision_scenarios=decision_scenarios,
        causal_chain=causal_chain,
    )
    audit_pdf_name = professional_audit_pdf_filename(client_name, run_at=run_at)

    pdf_file_path = generate_pdf_from_html(report_html)
    with open(pdf_file_path, "rb") as pdf_file:
        st.download_button(
            label="Descargar informe (PDF)",
            data=pdf_file,
            file_name=audit_pdf_name,
            mime="application/pdf",
            key="download_pdf_consola",
            use_container_width=True,
        )

    if st.session_state.get("show_internal_tools"):
        _dbg = build_motor_debug_trace(core)
        with st.expander("Depuración motor (germinal / ingest / umbrales)", expanded=False):
            st.caption(
                "Misma instantánea que se guarda en el JSON (`motor_debug`) al pulsar «Guardar análisis actual»."
            )
            st.json(_dbg)
        st.download_button(
            label="Descargar motor_debug.json",
            data=json.dumps(_dbg, ensure_ascii=False, indent=2),
            file_name="noumenon_motor_debug.json",
            mime="application/json",
            key="download_motor_debug_json",
        )

    st.caption(
        "Guarda el estado (tensor, evidencias, flujos) en `noumenon_data/` y recupéralo desde "
        "«02 · Escenarios y persistencia» cuando lo necesites."
    )
    if st.button("Guardar análisis actual", key="save_analysis_consola"):
        payload = build_analysis_payload(
            client_name=client_name,
            project_name=project_name,
            analyst_name=analyst_name,
            target=target if target else "Unknown",
            T=T,
            flows=flows,
            result=result,
            evidence_df=evidence_df,
            contradictions=contradictions,
            trace_df=trace_df,
            core_for_debug=core,
        )
        saved_path = save_analysis_json(payload)
        st.success(f"Análisis guardado en: {saved_path}")
