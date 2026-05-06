"""
Detalle colapsable de la consola Trabajo (dictamen ampliado, diagnóstico, simulación).
La vista ejecutiva vive en `trabajo_view`; aquí solo lo secundario.
"""

from __future__ import annotations

import html
from typing import Any

import numpy as np
import streamlit as st

from engine_akxom import PODERES_INFO
from labels import format_power_label, replace_power_codes_in_text
from report_visuals import build_potency_radar_svg
from simulation import build_action_display_label

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


def _md_insight(s: str) -> str:
    return replace_power_codes_in_text(s or "")


def _safe_html(s: str) -> str:
    return html.escape(_md_insight(s))


def _perceptualize_text(text: str | None) -> str:
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


def render_trabajo_detail_collapsed(
    core: dict[str, Any],
    T: Any,
    flows: list[float],
    *,
    executive_surface: dict[str, Any],
    action_plan: dict[str, Any],
    signal_color: str,
    signal_text: str,
) -> None:
    report = core["report"]
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

    es = executive_surface
    de = es.get("decision_ejecutiva") or {}
    mo = es.get("movimiento_operativo") or {}
    co = es.get("consecuencia") or {}
    es_conf = str(es.get("decision_confidence") or "MEDIUM")
    _conf_color = "#4ade80" if es_conf == "HIGH" else ("#fbbf24" if es_conf == "MEDIUM" else "#f87171")
    try:
        _de_di = float(de.get("delta_integridad", 0))
    except (TypeError, ValueError):
        _de_di = 0.0
    try:
        _de_df = float(de.get("delta_friccion", 0))
    except (TypeError, ValueError):
        _de_df = 0.0
    _tipo_raw = str(mo.get("tipo_intervencion") or "")
    _tipo_disp = _tipo_raw[:1].upper() + _tipo_raw[1:] if _tipo_raw else ""

    with st.expander("01 · Superficie técnica del panel (motivo, nodos, deltas)", expanded=False):
        st.caption("Desglose técnico; la decisión operativa está en la Executive View.")
        st.markdown(
            f"""
            <div style='padding:20px 22px;border:2px solid {DECISION_GOLD};border-radius:16px;background:#0a0a0a;margin-bottom:14px;'>
                <p style='font-size:11px;font-weight:800;color:{DECISION_GOLD};text-transform:uppercase;letter-spacing:0.12em;margin:0 0 12px 0;'>
                    Panel — mandato estructural
                </p>
                <p style='font-size:16px;font-weight:800;color:#F9FAFB;margin:0 0 10px 0;line-height:1.35;'>
                    {_safe_html(str(de.get("accion") or "—"))}
                </p>
                <p style='font-size:14px;line-height:1.6;margin:0 0 8px 0;color:#e5e7eb;'><strong>Nodo objetivo:</strong>
                    {_safe_html(format_power_label(str(de.get("nodo_objetivo") or "")) if de.get("nodo_objetivo") else "—")}</p>
                <p style='font-size:14px;line-height:1.6;margin:0 0 8px 0;color:#d4d4d4;'><strong>Motivo:</strong>
                    {_safe_html(str(de.get("motivo_estructural") or ""))}</p>
                <p style='font-size:14px;line-height:1.6;margin:0 0 8px 0;color:#e5e7eb;'>
                    <strong>Impacto esperado (panel):</strong> Δ integridad {_de_di:+g} · Δ fricción {_de_df:+g}
                </p>
                <p style='font-size:14px;line-height:1.6;margin:0 0 8px 0;color:#fca5a5;'><strong>Riesgo de no actuar:</strong>
                    {_safe_html(str(de.get("riesgo_inaccion") or ""))}</p>
                <p style='font-size:14px;line-height:1.6;margin:0;color:#e5e7eb;'>
                    <strong>Prioridad:</strong> {_safe_html(str(de.get("prioridad") or ""))}
                    <span style='margin-left:12px;font-size:12px;color:{_conf_color};font-weight:800;'>decision_confidence: {html.escape(es_conf)}</span>
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            f"""
            <div style='padding:18px 20px;border:1px solid {STRUCT_MID_BLUE};border-radius:14px;background:#081317;margin-bottom:12px;'>
                <p style='font-size:11px;font-weight:800;color:{SIGNAL_CYAN};text-transform:uppercase;letter-spacing:0.1em;margin:0 0 10px 0;'>
                    Movimiento operativo
                </p>
                <p style='font-size:14px;line-height:1.6;margin:0 0 8px 0;color:#e5e7eb;'><strong>Estructura:</strong>
                    {_safe_html(str(mo.get("estructura") or ""))}</p>
                <p style='font-size:14px;line-height:1.6;margin:0 0 8px 0;color:#e5e7eb;'><strong>Evitar (error del arquetipo):</strong>
                    {_safe_html(str(mo.get("error_arquetipo") or ""))}</p>
                <p style='font-size:14px;line-height:1.6;margin:0;color:#e5e7eb;'><strong>Tipo:</strong>
                    {_safe_html(_tipo_disp)}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        _det = str(co.get("tipo_deterioro") or "")
        _det_disp = _det[:1].upper() + _det[1:] if _det else ""
        st.markdown(
            f"""
            <div style='padding:18px 20px;border:1px solid rgba(248,113,113,0.45);border-radius:14px;background:#140808;margin-bottom:8px;'>
                <p style='font-size:11px;font-weight:800;color:#fca5a5;text-transform:uppercase;letter-spacing:0.1em;margin:0 0 10px 0;'>
                    Consecuencia
                </p>
                <p style='font-size:14px;line-height:1.6;margin:0 0 8px 0;color:#fecaca;'><strong>Si no se ejecuta:</strong>
                    {_safe_html(str(co.get("si_no_ejecuta") or ""))}</p>
                <p style='font-size:14px;line-height:1.55;margin:0;color:#f87171;'><strong>Deterioro:</strong> {_safe_html(_det_disp)}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    ap = action_plan or {}
    _ap_obj = str(ap.get("objective") or "")
    _ap_kind = str(ap.get("intervention_kind") or "")
    _ap_kind_disp = _ap_kind[:1].upper() + _ap_kind[1:] if _ap_kind else ""
    _ap_notes = str(ap.get("notes") or "")
    _ap_primary = str(ap.get("primary_action") or "")
    _ap_actions = ap.get("actions") or []
    _ap_lines = "".join(
        f"<li style='margin-bottom:8px;line-height:1.55;color:#e5e7eb;'>{_safe_html(str(x))}</li>"
        for x in _ap_actions[:3]
    )
    with st.expander("01b · Plan de acción — objetivo y soporte", expanded=False):
        st.caption("La acción ejecutable en una línea está en la Executive View; aquí el contexto del plan.")
        st.markdown(
            f"""
            <div style='padding:18px 20px;border:1px solid #334155;border-radius:14px;background:#0c0d10;margin-bottom:12px;'>
                <p style='font-size:11px;font-weight:800;color:{DECISION_GOLD};text-transform:uppercase;letter-spacing:0.1em;margin:0 0 8px 0;'>
                    Plan de acción
                </p>
                <p style='font-size:12px;color:#9ca3af;margin:0 0 12px 0;'>Tipo: {_safe_html(_ap_kind_disp)}</p>
                <p style='font-size:15px;font-weight:700;color:#F9FAFB;margin:0 0 14px 0;line-height:1.5;'>
                    <strong style='color:{SIGNAL_CYAN};'>Objetivo:</strong> {_safe_html(_ap_obj)}
                </p>
                <p style='font-size:12px;font-weight:800;color:{SIGNAL_SKY};text-transform:uppercase;margin:0 0 8px 0;'>Plan de soporte</p>
                <ol style='margin:0;padding-left:20px;font-size:14px;'>
                    {_ap_lines}
                </ol>
                <p style='font-size:13px;line-height:1.55;color:#a3a3a3;margin:14px 0 0 0;'>
                    <strong>Nota:</strong> {_safe_html(_ap_notes)}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ----- 02 · Diagnóstico -----
    st.markdown("### 02 · Diagnóstico")
    board_html = f"""
    <div style='padding:22px;border:1px solid #2a2a2a;border-radius:14px;background:linear-gradient(135deg,#0f0f0f 0%,#151515 100%);margin-bottom:16px;'>
        <p style='font-size:13px;font-weight:800;color:{DECISION_GOLD};text-transform:uppercase;letter-spacing:0.1em;margin:0 0 12px 0;'>
            Resumen para dirección
        </p>
    """
    for idx, line in enumerate(board_summary_lines, start=1):
        safe_line = _safe_html(line)
        board_html += (
            f"<p style='margin-bottom:10px;line-height:1.7;font-size:15px;color:#e5e7eb;'>"
            f"<strong>{idx}.</strong> {safe_line}</p>"
        )
    board_html += "</div>"
    st.markdown(board_html, unsafe_allow_html=True)

    k1, k2, k3 = st.columns(3)
    k1.metric("Integridad estructural", f"{integrity:.1f}")
    k2.metric("Fricción global", f"{friction:.1f}")
    k3.metric("Riesgo dominante", format_power_label(current_top_risk))

    q1, q2, q3 = st.columns(3)
    _au_name = (archetype_universal.get("name") or "").strip() or archetype_name
    q1.metric("Arquetipo (clasificación AKXOM)", _au_name)
    q2.metric("Confianza media", f"{float(np.mean(evidence_df['Confianza'])):.1f}")
    q3.metric("Gap medio vs benchmark", f"{float(np.mean(benchmark_df['Gap'])):.1f}")

    with st.expander("Matriz CEO — lectura complementaria", expanded=False):
        st.caption("Complemento cualitativo a la Executive View.")
        st.markdown(f"**Activo estructural**  \n{_md_insight(ceo_insights.get('structural_asset', ''))}")
        st.markdown(f"**Contradicción crítica**  \n{_md_insight(ceo_insights.get('critical_contradiction', ''))}")

    # ----- 03 · Palanca (secundario; riesgo/palanca ya nombrados arriba) -----
    with st.expander("03 · Palanca y maniobra del panel", expanded=False):
        st.caption("Desglose del panel de decisión; no duplica la Executive View.")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(
                f"""
                <div style='padding:16px;border:1px solid {STRUCT_MID_BLUE};border-radius:12px;background:#081317;margin-bottom:12px;box-shadow: 0 0 0 1px rgba(0,229,255,0.12), 0 0 22px rgba(0,229,255,0.08);'>
                    <p style='font-size:12px;font-weight:800;color:{SIGNAL_CYAN};margin:0 0 6px 0;text-transform:uppercase;'>Riesgo dominante</p>
                    <p style='font-size:17px;font-weight:700;margin:0;color:#F9FAFB;'>{html.escape(format_power_label(decision_panel["risk_dominant"]))}</p>
                    <p style='margin:10px 0 0 0;font-size:12px;font-weight:900;color:{signal_color};text-transform:uppercase;letter-spacing:0.08em;'>{signal_text}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown(
                f"""
                <div style='padding:16px;border:1px solid {STRUCT_MID_BLUE};border-radius:12px;background:#081317;margin-bottom:12px;box-shadow: 0 0 0 1px rgba(0,229,255,0.08), 0 0 26px rgba(0,229,255,0.06);'>
                    <p style='font-size:12px;font-weight:800;color:{SIGNAL_CYAN};margin:0 0 6px 0;text-transform:uppercase;'>Palanca estructural</p>
                    <p style='font-size:17px;font-weight:700;margin:0 0 8px 0;color:#F9FAFB;'>{html.escape(format_power_label(decision_panel["lever_power"]))}</p>
                    <p style='font-size:14px;line-height:1.6;margin:0;color:#d4d4d4;'>{_safe_html(_perceptualize_text(decision_panel.get("lever_msg", "")))}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c3:
            st.markdown(
                f"""
                <div style='padding:16px;border:1px solid {INTERVENTION_BLUE};border-radius:12px;background:#0d1420;margin-bottom:12px;'>
                    <p style='font-size:12px;font-weight:800;color:{INTERVENTION_LIGHT_BLUE};margin:0 0 6px 0;text-transform:uppercase;'>Intervención prioritaria</p>
                    <p style='font-size:16px;font-weight:700;margin:0 0 8px 0;color:#F9FAFB;'>{_safe_html(decision_panel.get("intervention_title", ""))}</p>
                    <p style='font-size:14px;line-height:1.6;margin:0;color:#d4d4d4;'>{_safe_html(decision_panel.get("intervention_detail", ""))}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with st.expander("Impacto esperado — detalle del panel", expanded=False):
            st.markdown(
                f"""
                <div style='padding:14px 16px;border:1px solid {STRUCT_MID_BLUE};border-radius:12px;background:#081317;margin-bottom:4px;'>
                    <p style='font-size:15px;line-height:1.65;margin:0;color:#e5e7eb;'>{_safe_html(_perceptualize_text(decision_panel.get("impact_msg", "")))}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

        _opp = (decision_panel.get("opportunity_note") or "").strip()
        if _opp:
            st.markdown(
                f"""
                <div style='padding:14px 18px;border:1px solid rgba(34,197,94,0.35);border-radius:12px;background:#0a1410;margin-bottom:8px;'>
                    <p style='font-size:12px;font-weight:800;color:#4ade80;margin:0 0 8px 0;text-transform:uppercase;letter-spacing:0.08em;'>Opcionalidad (germinal)</p>
                    <p style='font-size:15px;line-height:1.65;margin:0;color:#e5e7eb;'>{_safe_html(_perceptualize_text(_opp))}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with st.expander("Evidencias y contradicciones (fundamento del motor)", expanded=False):
        st.markdown(
            f"""
            <div style='padding:14px 16px;border:1px solid {STRUCT_MID_BLUE};border-radius:12px;background:#081317;margin-bottom:12px;box-shadow: 0 0 0 1px rgba(0,229,255,0.10), 0 0 22px rgba(0,229,255,0.06);'>
                <p style='font-size:12px;font-weight:800;color:{SIGNAL_CYAN};margin:0;text-transform:uppercase;letter-spacing:0.08em;'>Evidencia por poder</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # evidence_df: Poder, Nombre, Origen, Confianza, Evidencia, Nota + trazabilidad ingest (sesión)
        evid_rows = []
        for _, row in evidence_df.iterrows():
            poder_code = str(row.get("Poder", ""))
            poder = html.escape(poder_code)
            nombre = html.escape(str(row.get("Nombre", "")))
            origen = html.escape(str(row.get("Origen", "")))
            confianza = html.escape(str(row.get("Confianza", "")))
            nota_raw = str(row.get("Nota", "") or "")
            nota = html.escape(replace_power_codes_in_text(nota_raw) or "")
            kw_raw = (st.session_state.get(f"{poder_code}_ingest_keyword") or "").strip()
            tk_raw = (st.session_state.get(f"{poder_code}_ingest_tension_keyword") or "").strip()
            kw = html.escape(kw_raw)
            tk = html.escape(tk_raw)

            evid_rows.append(
                "<tr>"
                f"<td style='padding:6px 6px;border-bottom:1px solid #2a2a2a;white-space:nowrap;'>{poder}</td>"
                f"<td style='padding:6px 6px;border-bottom:1px solid #2a2a2a;'>{nombre}</td>"
                f"<td style='padding:6px 6px;border-bottom:1px solid #2a2a2a;white-space:nowrap;'>{origen}</td>"
                f"<td style='padding:6px 6px;border-bottom:1px solid #2a2a2a;white-space:nowrap;'>{confianza}</td>"
                f"<td style='padding:6px 6px;border-bottom:1px solid #2a2a2a;white-space:nowrap;font-size:11px;'>{kw}</td>"
                f"<td style='padding:6px 6px;border-bottom:1px solid #2a2a2a;white-space:nowrap;font-size:11px;'>{tk}</td>"
                f"<td style='padding:6px 6px;border-bottom:1px solid #2a2a2a;'>{nota}</td>"
                "</tr>"
            )

        evidence_html = (
            "<div style='overflow-x:auto;'>"
            "<table style='width:100%;border-collapse:collapse;font-size:13px;color:#E5E7EB;'>"
            "<thead>"
            "<tr>"
            f"<th style='text-align:left;padding:6px 6px;border-bottom:1px solid #2a2a2a;color:{SIGNAL_CYAN};'>Poder</th>"
            f"<th style='text-align:left;padding:6px 6px;border-bottom:1px solid #2a2a2a;color:{SIGNAL_CYAN};'>Nombre</th>"
            f"<th style='text-align:left;padding:6px 6px;border-bottom:1px solid #2a2a2a;color:{SIGNAL_CYAN};'>Origen</th>"
            f"<th style='text-align:left;padding:6px 6px;border-bottom:1px solid #2a2a2a;color:{SIGNAL_CYAN};'>Conf.</th>"
            f"<th style='text-align:left;padding:6px 6px;border-bottom:1px solid #2a2a2a;color:{SIGNAL_CYAN};'>Kw ingest</th>"
            f"<th style='text-align:left;padding:6px 6px;border-bottom:1px solid #2a2a2a;color:{SIGNAL_CYAN};'>Tensión</th>"
            f"<th style='text-align:left;padding:6px 6px;border-bottom:1px solid #2a2a2a;color:{SIGNAL_CYAN};'>Nota</th>"
            "</tr>"
            "</thead>"
            "<tbody>"
            + "".join(evid_rows)
            + "</tbody>"
            "</table>"
            "</div>"
        )
        st.markdown(evidence_html, unsafe_allow_html=True)

        # Para trazabilidad: conectamos la nota del mismo Pi con la fila de lectura.
        evidence_note_by_power: dict[str, str] = {}
        for _, row in evidence_df.iterrows():
            poder_code = str(row.get("Poder", ""))
            nota_raw = str(row.get("Nota", "") or "")
            nota = html.escape(replace_power_codes_in_text(nota_raw) or "")
            evidence_note_by_power[poder_code] = (nota[:80] + "...") if len(nota) > 80 else nota

        # ----- Trazabilidad del ajuste -----
        if trace_df is not None and len(trace_df) > 0:
            st.markdown("#### Trazabilidad del ajuste (Auto base → Valor final)")

            trace_rows = []
            for _, row in trace_df.iterrows():
                poder = html.escape(str(row.get("Poder", "")))
                nombre = html.escape(str(row.get("Nombre", "")))
                auto_base = row.get("Auto base", "")
                valor_final = row.get("Valor final", "")
                delta = row.get("Delta", "")
                lectura = html.escape(str(row.get("Lectura", "")))
                note_snippet = evidence_note_by_power.get(str(row.get("Poder", "")), "")

                # Normalizamos numéricos a string para evitar HTML con numpy types raros.
                def _fmt(x: Any) -> str:
                    try:
                        return f"{float(x):.2f}"
                    except Exception:
                        return html.escape(str(x))

                trace_rows.append(
                    "<tr>"
                    f"<td style='padding:6px 6px;border-bottom:1px solid #2a2a2a;white-space:nowrap;'>{poder}</td>"
                    f"<td style='padding:6px 6px;border-bottom:1px solid #2a2a2a;'>{nombre}</td>"
                    f"<td style='padding:6px 6px;border-bottom:1px solid #2a2a2a;white-space:nowrap;'>{_fmt(auto_base)}</td>"
                    f"<td style='padding:6px 6px;border-bottom:1px solid #2a2a2a;white-space:nowrap;'>{_fmt(valor_final)}</td>"
                    f"<td style='padding:6px 6px;border-bottom:1px solid #2a2a2a;white-space:nowrap;'>{_fmt(delta)}</td>"
                    f"<td style='padding:6px 6px;border-bottom:1px solid #2a2a2a;'>{lectura}</td>"
                    f"<td style='padding:6px 6px;border-bottom:1px solid #2a2a2a;'>{note_snippet}</td>"
                    "</tr>"
                )

            trace_html = (
                "<div style='overflow-x:auto;'>"
                "<table style='width:100%;border-collapse:collapse;font-size:13px;color:#E5E7EB;'>"
                "<thead>"
                "<tr>"
                f"<th style='text-align:left;padding:6px 6px;border-bottom:1px solid #2a2a2a;color:{SIGNAL_CYAN};'>Poder</th>"
                f"<th style='text-align:left;padding:6px 6px;border-bottom:1px solid #2a2a2a;color:{SIGNAL_CYAN};'>Nombre</th>"
                f"<th style='text-align:left;padding:6px 6px;border-bottom:1px solid #2a2a2a;color:{SIGNAL_CYAN};'>Auto base</th>"
                f"<th style='text-align:left;padding:6px 6px;border-bottom:1px solid #2a2a2a;color:{SIGNAL_CYAN};'>Valor final</th>"
                f"<th style='text-align:left;padding:6px 6px;border-bottom:1px solid #2a2a2a;color:{SIGNAL_CYAN};'>Delta</th>"
                f"<th style='text-align:left;padding:6px 6px;border-bottom:1px solid #2a2a2a;color:{SIGNAL_CYAN};'>Lectura</th>"
                f"<th style='text-align:left;padding:6px 6px;border-bottom:1px solid #2a2a2a;color:{SIGNAL_CYAN};'>Nota (evidencia Pi)</th>"
                "</tr>"
                "</thead>"
                "<tbody>"
                + "".join(trace_rows)
                + "</tbody>"
                "</table>"
                "</div>"
            )
            st.markdown(trace_html, unsafe_allow_html=True)

        # ----- Mapa compacto: input → motor → contradicciones -----
        st.markdown("#### Mapa compacto: input → motor → contradicciones")
        try:
            contra_map: dict[str, list[str]] = {}
            for item in contradictions:
                poder = str(item.get("poder", ""))
                issues = item.get("issues") or []
                contra_map[poder] = [str(x) for x in issues]

            motor_potency = report.get("potency100", [])
            motor_leak = report.get("leakscore", [])

            compact_rows = []
            if trace_df is not None and len(trace_df) >= 10:
                for i, (p_code, p_title, _, _) in enumerate(PODERES_INFO):
                    tr = trace_df.iloc[i]
                    lectura = str(tr.get("Lectura", ""))
                    auto_base = tr.get("Auto base", "")
                    valor_final = tr.get("Valor final", "")
                    delta = tr.get("Delta", "")

                    pval = float(motor_potency[i]) if i < len(motor_potency) else 0.0
                    lval = float(motor_leak[i]) if i < len(motor_leak) else 0.0

                    fv = float(flows[i]) if flows and i < len(flows) else 0.0
                    flabel = flow_labels[i] if flow_labels and i < len(flow_labels) else ""

                    issues = contra_map.get(p_code, [])
                    issues_count = len(issues)
                    first_issue = issues[0] if issues else ""
                    if first_issue:
                        first_issue = (first_issue[:72] + "...") if len(first_issue) > 75 else first_issue

                    compact_rows.append(
                        "<tr>"
                        f"<td style='padding:6px 6px;border-bottom:1px solid #2a2a2a;white-space:nowrap;'>{html.escape(str(p_code))}</td>"
                        f"<td style='padding:6px 6px;border-bottom:1px solid #2a2a2a;'>{html.escape(lectura)}</td>"
                        f"<td style='padding:6px 6px;border-bottom:1px solid #2a2a2a;white-space:nowrap;'>{float(auto_base):.2f}</td>"
                        f"<td style='padding:6px 6px;border-bottom:1px solid #2a2a2a;white-space:nowrap;'>{float(valor_final):.2f}</td>"
                        f"<td style='padding:6px 6px;border-bottom:1px solid #2a2a2a;white-space:nowrap;'>{pval:.1f}</td>"
                        f"<td style='padding:6px 6px;border-bottom:1px solid #2a2a2a;white-space:nowrap;'>{lval:.2f}</td>"
                        f"<td style='padding:6px 6px;border-bottom:1px solid #2a2a2a;white-space:nowrap;'>{fv:+.1f}</td>"
                        f"<td style='padding:6px 6px;border-bottom:1px solid #2a2a2a;'>{issues_count}{' — ' + html.escape(first_issue) if first_issue else ''}</td>"
                        "</tr>"
                    )

            compact_html = (
                "<div style='overflow-x:auto;'>"
                "<table style='width:100%;border-collapse:collapse;font-size:12.5px;color:#E5E7EB;'>"
                "<thead>"
                "<tr>"
                f"<th style='text-align:left;padding:6px 6px;border-bottom:1px solid #2a2a2a;color:{SIGNAL_CYAN};'>Poder</th>"
                f"<th style='text-align:left;padding:6px 6px;border-bottom:1px solid #2a2a2a;color:{SIGNAL_CYAN};'>Lectura</th>"
                f"<th style='text-align:left;padding:6px 6px;border-bottom:1px solid #2a2a2a;color:{SIGNAL_CYAN};'>Auto base</th>"
                f"<th style='text-align:left;padding:6px 6px;border-bottom:1px solid #2a2a2a;color:{SIGNAL_CYAN};'>Valor final</th>"
                f"<th style='text-align:left;padding:6px 6px;border-bottom:1px solid #2a2a2a;color:{SIGNAL_CYAN};'>Potencia100</th>"
                f"<th style='text-align:left;padding:6px 6px;border-bottom:1px solid #2a2a2a;color:{SIGNAL_CYAN};'>Leakscore</th>"
                f"<th style='text-align:left;padding:6px 6px;border-bottom:1px solid #2a2a2a;color:{SIGNAL_CYAN};'>Flow</th>"
                f"<th style='text-align:left;padding:6px 6px;border-bottom:1px solid #2a2a2a;color:{SIGNAL_CYAN};'>Contradicción</th>"
                "</tr>"
                "</thead>"
                "<tbody>"
                + "".join(compact_rows)
                + "</tbody>"
                "</table>"
                "</div>"
            )
            st.markdown(compact_html, unsafe_allow_html=True)
        except Exception:
            st.caption("Mapa compacto no disponible en esta corrida.")

        st.markdown(
            f"""
            <div style='padding:14px 16px;border:1px solid {STRUCT_MID_BLUE};border-radius:12px;background:#081317;margin:12px 0 12px 0;box-shadow: 0 0 0 1px rgba(0,229,255,0.10), 0 0 22px rgba(0,229,255,0.06);'>
                <p style='font-size:12px;font-weight:800;color:{SIGNAL_SKY};margin:0;text-transform:uppercase;letter-spacing:0.08em;'>Contradicciones estructurales</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if not contradictions:
            st.caption("No se detectan contradicciones críticas en el tensor actual.")
        else:
            for item in contradictions:
                poder = str(item.get("poder", ""))
                nombre = str(item.get("nombre", ""))
                issues = item.get("issues") or []
                st.markdown(
                    f"<span style='color:{SIGNAL_CYAN};font-weight:900;text-shadow:0 0 16px rgba(0,229,255,0.12);'>{html.escape(format_power_label(poder))}</span> — {html.escape(nombre)}",
                    unsafe_allow_html=True,
                )
                for issue in issues:
                    st.caption(f"- {issue}")

        snap = st.session_state.get("noumenon_traceability_snapshot")
        if snap and isinstance(snap, dict):
            with st.expander("Auditoría: instantánea del último JSON cargado", expanded=False):
                src = st.session_state.get("noumenon_audit_source_file") or "—"
                saved_at = st.session_state.get("noumenon_payload_saved_at") or "—"
                st.caption(f"Archivo: {src} · Timestamp en JSON: {saved_at}")
                c_frozen = snap.get("contradictions") or []
                p6_issues: list[str] = []
                for it in c_frozen:
                    if str(it.get("poder")) == "P6":
                        p6_issues = [str(x) for x in (it.get("issues") or [])]
                        break
                st.markdown("**Motor — P6 (contradicciones en el guardado)**")
                if p6_issues:
                    for iss in p6_issues:
                        st.caption(iss)
                else:
                    st.caption("En la instantánea no constan alertas de contradicción para P6.")
                ikw = (st.session_state.get("P6_ingest_keyword") or "").strip()
                itk = (st.session_state.get("P6_ingest_tension_keyword") or "").strip()
                if ikw or itk:
                    st.markdown("**Ingest — señales asociadas a P6 en el guardado**")
                    if ikw:
                        st.caption(f"Keyword ontológica: {ikw}")
                    if itk:
                        st.caption(f"Tensión detectada: {itk}")
                note_p6 = (st.session_state.get("P6_note") or "").strip()
                if note_p6:
                    st.markdown("**Fragmento de evidencia (nota P6 recuperada)**")
                    st.text(note_p6[:4000])

    with st.expander("Tres estrategias de intervención", expanded=False):
        for strat in intervention_strategies:
            st.markdown(
                f"**{strat.get('title', '')}** — foco: {strat.get('focus', '')}"
            )
            st.caption(_md_insight(str(strat.get("logic", ""))))
            st.markdown(_md_insight(str(strat.get("action", ""))))
            st.caption(
                f"Riesgo: {_md_insight(str(strat.get('risk', '')))} · "
                f"Impacto: {_md_insight(str(strat.get('impact', '')))}"
            )
            st.divider()

    # ----- 04 · Proyección -----
    st.markdown("### 04 · Proyección y simulación")

    # Flow de poder: tendencia estratégica (vector de entrada) por poder.
    if flows and len(flows) >= 10:
        st.markdown("#### Flow de poder (tendencia)")
        max_abs = 3.0
        POS = SIGNAL_GOOD
        NEG = SIGNAL_BAD
        MID = STRUCT_MID_BLUE

        flow_rows = []
        for i, (p_code, p_title, _, _) in enumerate(PODERES_INFO):
            v = float(flows[i]) if i < len(flows) else 0.0
            label = flow_labels[i] if i < len(flow_labels) else ""
            pct = min(abs(v) / max_abs, 1.0) * 100.0
            if v > 0.1:
                color = POS
            elif v < -0.1:
                color = NEG
            else:
                color = MID

            flow_rows.append(
                "<tr>"
                f"<td style='padding:6px 6px;border-bottom:1px solid #2a2a2a;white-space:nowrap;'>{html.escape(str(p_code))}</td>"
                f"<td style='padding:6px 6px;border-bottom:1px solid #2a2a2a;'>{html.escape(str(p_title))}</td>"
                f"<td style='padding:6px 6px;border-bottom:1px solid #2a2a2a;white-space:nowrap;'>{v:+.1f}</td>"
                f"<td style='padding:6px 6px;border-bottom:1px solid #2a2a2a;'>{html.escape(str(label))}</td>"
                "<td style='padding:6px 6px;border-bottom:1px solid #2a2a2a;min-width:180px;'>"
                "<div style='height:10px;background:#111;border:1px solid #2a2a2a;border-radius:8px;overflow:hidden;'>"
                f"<div style='height:100%;width:{pct:.1f}%;background:{color};border-radius:7px;'></div>"
                "</div>"
                "</td>"
                "</tr>"
            )

        flow_html = (
            "<div style='overflow-x:auto;'>"
            "<table style='width:100%;border-collapse:collapse;font-size:13px;color:#E5E7EB;'>"
            "<thead>"
            "<tr>"
            f"<th style='text-align:left;padding:6px 6px;border-bottom:1px solid #2a2a2a;color:{SIGNAL_CYAN};'>Poder</th>"
            f"<th style='text-align:left;padding:6px 6px;border-bottom:1px solid #2a2a2a;color:{SIGNAL_CYAN};'>Nombre</th>"
            f"<th style='text-align:left;padding:6px 6px;border-bottom:1px solid #2a2a2a;color:{SIGNAL_CYAN};'>Flow</th>"
            f"<th style='text-align:left;padding:6px 6px;border-bottom:1px solid #2a2a2a;color:{SIGNAL_CYAN};'>Lectura</th>"
            f"<th style='text-align:left;padding:6px 6px;border-bottom:1px solid #2a2a2a;color:{SIGNAL_CYAN};'>Intensidad</th>"
            "</tr>"
            "</thead>"
            "<tbody>"
            + "".join(flow_rows)
            + "</tbody>"
            "</table>"
            "</div>"
        )
        st.markdown(flow_html, unsafe_allow_html=True)
        st.caption("Convención: barras verdes = ASCENDENTE/crecimiento; rojas = EN DETERIORO/Desgaste; gris = ESTABLE.")

    radar_svg = build_potency_radar_svg(
        report["potency100"],
        sim_report.get("potency100"),
    )
    st.markdown(
        f'<div style="max-width:520px;margin:0 auto 12px auto;text-align:center;border:1px solid {STRUCT_MID_BLUE};border-radius:16px;padding:16px;background:#050505;">{radar_svg}</div>',
        unsafe_allow_html=True,
    )
    st.caption("Figura — Potencia por poder (Pi). Dorado: hoy; rojo discontinuo: tras la intervención simulada.")

    sim_col1, sim_col2, sim_col3, sim_col4 = st.columns(4)
    sim_col1.metric("Integridad (ahora)", f"{integrity:.1f}")
    sim_col2.metric("Integridad (sim)", f"{simulated_integrity:.1f}", delta=f"{simulated_integrity - integrity:+.1f}")
    sim_col3.metric("Fricción (ahora)", f"{friction:.1f}")
    sim_col4.metric("Fricción (sim)", f"{simulated_friction:.1f}", delta=f"{simulated_friction - friction:+.1f}")

    delta_integrity = simulated_integrity - integrity
    delta_friction = simulated_friction - friction
    integrity_eps = 0.05
    friction_eps = 0.05
    NOU_GOOD = SIGNAL_GOOD
    NOU_BAD = SIGNAL_BAD
    NOU_NEUTRAL = SIGNAL_NEUTRAL
    if abs(delta_integrity) <= integrity_eps:
        integrity_delta_color = NOU_NEUTRAL
    else:
        integrity_delta_color = NOU_GOOD if delta_integrity >= 0 else NOU_BAD
    if abs(delta_friction) <= friction_eps:
        friction_delta_color = NOU_NEUTRAL
    else:
        # Menos fricción = mejora.
        friction_delta_color = NOU_GOOD if delta_friction <= 0 else NOU_BAD

    st.markdown(
        f"""
        <div style='padding:18px;border:1px solid {STRUCT_MID_BLUE};border-radius:12px;background:#081317;margin-bottom:8px;box-shadow: 0 0 0 1px rgba(0,229,255,0.10), 0 0 26px rgba(0,229,255,0.06);'>
            <p style='font-size:13px;font-weight:800;color:{DECISION_GOLD};margin:0 0 10px 0;text-transform:uppercase;'>Resultado de la simulación</p>
            <p style='margin:6px 0;font-size:14px;color:#e5e7eb;'><strong>Acción modelada:</strong> {html.escape(build_action_display_label(action_label, acted_power))}</p>
            <p style='margin:6px 0;font-size:14px;color:#e5e7eb;'><strong>Riesgo dominante:</strong> {html.escape(format_power_label(current_top_risk))} → {html.escape(format_power_label(simulated_top_risk))}</p>
            <p style='margin:6px 0;font-size:14px;color:#e5e7eb;'>
                <strong>Δ Integridad:</strong> <span style='color:{integrity_delta_color};'>
                    {delta_integrity:+.1f}
                </span>
            </p>
            <p style='margin:6px 0;font-size:14px;color:#e5e7eb;'>
                <strong>Δ Fricción:</strong> <span style='color:{friction_delta_color};'>
                    {delta_friction:+.1f}
                </span>
            </p>
            <p style='margin:6px 0;font-size:14px;color:#e5e7eb;'><strong>Veredicto:</strong> {html.escape(str(report["global_verdict"]))} → {html.escape(str(sim_report["global_verdict"]))}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _ita = final_reco.get("integrity_threshold_alert") if isinstance(final_reco, dict) else None
    if _ita:
        st.markdown(
            f"""
            <div style="margin:14px 0 8px 0;padding:14px 18px;border-radius:12px;
                border:1px solid rgba(245,158,11,0.55);border-left:5px solid #f59e0b;
                background:rgba(245,158,11,0.14);
                box-shadow:0 0 0 1px rgba(245,158,11,0.12);">
                <p style="font-family:ui-monospace,'Courier New',monospace;font-size:11px;font-weight:800;
                letter-spacing:0.1em;text-transform:uppercase;color:#fcd34d;margin:0 0 8px 0;">
                    Nota ejecutiva · Umbral 60 %
                </p>
                <p style="font-size:14px;line-height:1.55;color:#e5e7eb;margin:0;">
                    {html.escape(str(_ita))}
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ----- 05 · Decisión -----
    st.markdown("### 05 · Decisión y entregables")
    st.markdown(
        f"""
        <div style='padding:24px;border:2px solid {DECISION_GOLD};border-radius:18px;background:#0a0a0a;margin-bottom:16px;'>
            <p style='font-size:12px;font-weight:800;color:{DECISION_GOLD};text-transform:uppercase;letter-spacing:0.12em;margin:0 0 10px 0;'>Dictamen</p>
            <p style='font-size:26px;font-weight:800;color:#F9FAFB;margin:0 0 12px 0;line-height:1.25;'>
                {html.escape(str(final_reco["title"]))}
            </p>
            <p style='font-size:16px;line-height:1.7;color:#d4d4d4;margin:0 0 14px 0;'>
                {html.escape(str(final_reco["summary"]))}
            </p>
            <p style='font-size:13px;color:{SIGNAL_NEUTRAL};margin:0 0 18px 0;border-bottom:1px solid #262626;padding-bottom:14px;'>
                Nivel de decisión: {html.escape(str(final_reco["level"]))} · {html.escape(str(one_liner))}
            </p>
            <p style='font-size:12px;font-weight:800;color:{DECISION_GOLD};margin:0 0 6px 0;text-transform:uppercase;'>Próximo paso ejecutivo</p>
            <p style='font-size:16px;line-height:1.65;color:#F3F4F6;margin:0;'>
                {html.escape(str(final_reco["next_step"]))}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
