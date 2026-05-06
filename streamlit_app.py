from __future__ import annotations

from pathlib import Path

import streamlit as st
import pandas as pd

from engine_akxom import PODERES_INFO
from noumenon_v2.application.case_service import (
    append_case_snapshot,
    build_archetype_comparison,
    build_case_snapshot,
    build_editorial_frame,
    build_flow_progress,
    build_power_summary_rows,
    build_snapshot_comparison,
    build_structural_reading,
    recommend_next_step,
    run_case_diagnosis,
)
from noumenon_v2.application.demo_cases import build_demo_case_catalog, build_helios_ai_demo_case
from noumenon_v2.application.pdf_service import (
    build_v2_pdf_filename,
    render_pdf_bytes_from_html,
    save_pdf_bytes,
)
from noumenon_v2.application.report_service import build_report_html, save_report_html
from noumenon_v2.application.visual_service import (
    build_diagnosis_brief_html,
    build_power_tension_map_svg,
    build_radar_svg_from_core_with_size,
    build_structural_heatmap_svg,
    describe_friction,
    describe_integrity,
)
from noumenon_v2.brand_assets import load_brand_svg_data_uri
from noumenon_v2.domain.models import CaseRecord
from noumenon_v2.infrastructure.json_repository import JsonCaseRepository

REPO = JsonCaseRepository()
BENCHMARK_OPTIONS = ["Estable", "Tensión", "Base"]
CASE_STATUS_OPTIONS = ["Borrador", "Lectura en revisión", "Informe listo"]
POWER_LABELS = {power_code: title for power_code, title, _, _ in PODERES_INFO}
SECTION_ORDER = ["01 · Caso", "02 · Evidencia", "03 · Estructura", "04 · Diagnóstico", "05 · Informe"]
DEMO_CASE_BUILDERS = build_demo_case_catalog()


def _clear_generated_outputs() -> None:
    st.session_state.pop("v2_diagnosis", None)
    st.session_state.pop("v2_comparison", None)
    st.session_state.pop("v2_pdf_bytes", None)
    st.session_state.pop("v2_pdf_filename", None)


def _load_demo_case(builder_key: str) -> None:
    builder = DEMO_CASE_BUILDERS.get(builder_key)
    if builder is None:
        return
    _set_case(builder())
    _clear_generated_outputs()
    st.rerun()


def _reset_jury_demo() -> None:
    _set_case(build_helios_ai_demo_case())
    _clear_generated_outputs()
    st.session_state["v2_nav_section"] = "04 · Diagnóstico"
    st.rerun()


def _ensure_case_state() -> CaseRecord:
    if "v2_case" not in st.session_state:
        st.session_state["v2_case"] = CaseRecord.create_blank()
    return st.session_state["v2_case"]


def _set_case(case: CaseRecord) -> None:
    st.session_state["v2_case"] = case


def _is_demo_mode() -> bool:
    return bool(st.session_state.get("v2_demo_mode", False))


def _is_public_jury_mode() -> bool:
    return bool(st.session_state.get("v2_public_jury_mode", False))


def _sync_demo_mode_state() -> None:
    current = _is_demo_mode()
    previous = bool(st.session_state.get("v2_demo_mode_previous", False))
    case = _ensure_case_state()
    if current and not previous:
        st.session_state["v2_demo_mode_previous"] = True
        if case.client_name != "Helios AI":
            _set_case(build_helios_ai_demo_case())
            _clear_generated_outputs()
        st.session_state["v2_nav_section"] = "04 · Diagnóstico"
        st.rerun()
    if not current and previous:
        st.session_state["v2_demo_mode_previous"] = False


def _sync_public_jury_state() -> None:
    if not _is_public_jury_mode():
        return
    st.session_state["v2_demo_mode"] = True
    st.session_state["v2_demo_mode_previous"] = True
    case = _ensure_case_state()
    if case.client_name != "Helios AI":
        case = build_helios_ai_demo_case()
        _set_case(case)
        _clear_generated_outputs()
    st.session_state.setdefault("v2_nav_section", "04 · Diagnóstico")
    if st.session_state["v2_nav_section"] not in {"04 · Diagnóstico", "05 · Informe"}:
        st.session_state["v2_nav_section"] = "04 · Diagnóstico"
    if "v2_diagnosis" not in st.session_state:
        diagnosis = run_case_diagnosis(case)
        st.session_state["v2_diagnosis"] = diagnosis
        st.session_state["v2_comparison"] = None
        if case.case_status == "Borrador":
            case.case_status = "Lectura en revisión"


def _queue_nav(next_section: str) -> None:
    st.session_state["v2_nav_target"] = next_section
    st.rerun()


def _save_current_case() -> Path:
    case = _ensure_case_state()
    return REPO.save(case)


def _render_sidebar() -> None:
    case = _ensure_case_state()
    pending_nav = st.session_state.pop("v2_nav_target", None)
    allowed_sections = ["04 · Diagnóstico", "05 · Informe"] if _is_public_jury_mode() else SECTION_ORDER
    if pending_nav in allowed_sections:
        st.session_state["v2_nav_section"] = pending_nav
    st.sidebar.markdown(
        """
        <div style="font-family:'Aptos Narrow','Arial Narrow',Inter,'Space Grotesk',Arial,sans-serif;
        font-size:28px;font-weight:500;letter-spacing:0.18em;color:#E6E6E6;line-height:1;text-transform:uppercase;
        margin:2px 0 6px 0;">Noumenon</div>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.caption("Lectura estructural · recorrido ejecutivo")
    st.sidebar.markdown("---")
    if _is_public_jury_mode():
        st.session_state.setdefault("v2_nav_section", "04 · Diagnóstico")
        st.sidebar.info(
            "Demo pública de jurado: Helios queda fijado como caso único y la navegación se limita a diagnóstico e informe."
        )
        st.sidebar.radio(
            "Recorrido",
            options=allowed_sections,
            key="v2_nav_section",
        )
        st.sidebar.markdown("---")
        st.sidebar.markdown("**Caso público**: `Helios AI`")
        st.sidebar.markdown("**Modo**: `solo lectura`")
        st.sidebar.markdown("**Salida**: `diagnóstico + informe`")
        st.sidebar.markdown(f"**Estado**: `{case.case_status}`")
        return
    st.sidebar.toggle(
        "Modo demo jurado",
        key="v2_demo_mode",
        help="Carga Helios como caso principal y limpia la interfaz para una demostración de concurso o sala.",
    )
    if _is_demo_mode():
        st.sidebar.info(
            "Modo demo jurado activo: Helios queda fijado como caso principal, el recorrido se simplifica y la lectura se centra en decisión e informe."
        )
        if st.sidebar.button("Reiniciar demo jurado", use_container_width=True, type="primary", key="reset_jury_demo"):
            _reset_jury_demo()
        with st.sidebar.expander("Otros casos demo", expanded=False):
            demo_options = list(DEMO_CASE_BUILDERS.keys())
            selected_demo = st.selectbox(
                "Caso demo alternativo",
                options=demo_options,
                index=0,
                format_func=lambda key: key,
                key="v2_demo_case_select_top",
            )
            if st.button("Cargar caso alternativo", use_container_width=True, key="load_demo_top"):
                _load_demo_case(selected_demo)
        st.sidebar.markdown("---")
    st.session_state.setdefault("v2_nav_section", "01 · Caso")
    st.sidebar.radio(
        "Recorrido",
        options=allowed_sections,
        key="v2_nav_section",
    )
    st.sidebar.markdown("---")
    with st.sidebar.expander("Operativa del caso", expanded=not _is_demo_mode()):
        if st.button("Nuevo caso", use_container_width=True, key="new_case_sidebar"):
            _set_case(CaseRecord.create_blank())
            st.rerun()

        if not _is_demo_mode() and st.button("Cargar demo Helios AI", use_container_width=True, key="load_demo_inside"):
            _set_case(build_helios_ai_demo_case())
            st.session_state.pop("v2_diagnosis", None)
            st.session_state.pop("v2_pdf_bytes", None)
            st.session_state.pop("v2_pdf_filename", None)
            st.rerun()

        if st.button("Guardar caso", use_container_width=True, key="save_case_sidebar"):
            saved_path = _save_current_case()
            st.sidebar.success(f"Guardado en {saved_path}")

        available_cases = REPO.list_case_ids()
        if available_cases and not _is_demo_mode():
            selected_case_id = st.selectbox(
                "Abrir caso guardado",
                options=[""] + available_cases,
                index=0,
                key="saved_case_select_sidebar",
            )
            action_col1, action_col2 = st.columns(2)
            if selected_case_id and action_col1.button("Cargar caso", use_container_width=True, key="load_case_sidebar"):
                _set_case(REPO.load(selected_case_id))
                st.rerun()
            confirm_delete = st.checkbox(
                "Confirmar borrado",
                value=False,
                key="confirm_delete_case_sidebar",
                help="Activa esta casilla antes de eliminar un caso guardado.",
            )
            if selected_case_id and action_col2.button("Eliminar caso", use_container_width=True, key="delete_case_sidebar"):
                if not confirm_delete:
                    st.warning("Activa 'Confirmar borrado' antes de eliminar el caso.")
                else:
                    deleted = REPO.delete(selected_case_id)
                    if deleted:
                        if case.case_id == selected_case_id:
                            _set_case(CaseRecord.create_blank())
                            st.session_state.pop("v2_diagnosis", None)
                            st.session_state.pop("v2_pdf_bytes", None)
                            st.session_state.pop("v2_pdf_filename", None)
                        st.success(f"Caso eliminado: {selected_case_id}")
                        st.rerun()
                    else:
                        st.warning("No se ha podido eliminar el caso seleccionado.")

    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**Referencia del caso**: `{case.case_id}`")
    st.sidebar.markdown(f"**Versión del caso**: `{case.schema_version}`")
    st.sidebar.markdown(f"**Estado**: `{case.case_status}`")
    st.sidebar.markdown(f"**Actualizado**: `{case.updated_at}`")


def _render_header() -> None:
    header_logo_src = load_brand_svg_data_uri("noumenon_imagotipo_horizontal_compact.svg")
    st.set_page_config(page_title="Noumenon", layout="wide")
    st.markdown(
        """
        <style>
        :root {
            --v2-bg: #0f151c;
            --v2-panel: #121a22;
            --v2-panel-soft: #10161d;
            --v2-line: #2a3947;
            --v2-text: #edf3f7;
            --v2-muted: #9fb0bd;
            --v2-gold: #d8b36a;
            --v2-success: #6EE7B7;
        }
        .stApp {
            background:
              radial-gradient(circle at top right, rgba(201,162,39,0.10), transparent 18%),
              linear-gradient(180deg, #0b1015 0%, #121a22 100%);
            color: #edf3f7;
        }
        .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4 {
            color: #edf3f7;
        }
        .stMarkdown h1 {
            font-family: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", Georgia, serif;
            font-weight: 700;
            letter-spacing: -0.03em;
        }
        .stMarkdown h2 {
            font-family: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", Georgia, serif;
            letter-spacing: -0.02em;
        }
        .stCaption {
            color: #9fb0bd !important;
        }
        div[data-testid="stMetric"] {
            background: #121a22;
            border: 1px solid #2a3947;
            border-radius: 18px;
            padding: 14px;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.02);
        }
        div[data-testid="stMetricLabel"] {
            color: #9fb0bd !important;
        }
        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0d1319 0%, #121a22 100%);
            border-right: 1px solid #22313d;
        }
        div[data-baseweb="select"] > div,
        .stTextInput input,
        .stTextArea textarea {
            background: #10161d !important;
            border: 1px solid #2a3947 !important;
            border-radius: 14px !important;
            color: #edf3f7 !important;
        }
        .stTextArea textarea {
            line-height: 1.55 !important;
        }
        .stButton > button,
        .stDownloadButton > button {
            border-radius: 14px !important;
            border: 1px solid #344656 !important;
            background: linear-gradient(180deg, #17222d 0%, #121a22 100%) !important;
            color: #edf3f7 !important;
            font-weight: 700 !important;
            min-height: 42px !important;
        }
        .stButton > button[kind="primary"],
        .stDownloadButton > button[kind="primary"] {
            background: linear-gradient(180deg, #d8b36a 0%, #b99347 100%) !important;
            color: #0b1015 !important;
            border: 1px solid #d8b36a !important;
        }
        .stDataFrame {
            border: 1px solid #2a3947;
            border-radius: 18px;
            overflow: hidden;
        }
        details {
            border: 1px solid #2a3947;
            border-radius: 16px;
            background: #10161d;
            padding: 8px 12px;
        }
        .v2-progress-card {
            background:
              radial-gradient(circle at top right, rgba(0, 240, 255, 0.035), transparent 28%),
              linear-gradient(180deg, #121a22 0%, #10161d 100%);
            border: 1px solid #2a3947;
            border-radius: 18px;
            padding: 14px 15px;
            min-height: 98px;
            box-shadow:
              inset 0 1px 0 rgba(255,255,255,0.02),
              0 10px 26px rgba(0,0,0,0.18);
        }
        .v2-section-shell {
            background:
              radial-gradient(circle at top right, rgba(216,179,106,0.07), transparent 24%),
              linear-gradient(180deg, #121a22 0%, #10161d 100%);
            border: 1px solid #2a3947;
            border-radius: 22px;
            padding: 20px 20px 10px 20px;
            margin-bottom: 16px;
        }
        .v2-section-kicker {
            font-size: 11px;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            color: #d8b36a;
            margin-bottom: 8px;
            font-weight: 800;
        }
        .v2-header-shell {
            margin: 2px 0 18px 0;
        }
        .v2-premium-panel {
            padding: 18px 20px;
            border: 1px solid #2a3947;
            border-radius: 18px;
            background:
              radial-gradient(circle at top right, rgba(216,179,106,0.06), transparent 28%),
              linear-gradient(180deg, #121a22 0%, #10161d 100%);
            box-shadow:
              inset 0 1px 0 rgba(255,255,255,0.02),
              0 16px 40px rgba(0,0,0,0.18);
        }
        .v2-premium-label {
            font-size: 11px;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            color: #d8b36a;
            margin-bottom: 8px;
            font-weight: 800;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.components.v1.html(
        f"""
        <div style="margin:0 0 16px -8px;padding:4px 0 6px 0;">
            <img alt="Noumenon" src="{header_logo_src}" style="display:block;width:560px;height:auto;" />
        </div>
        """,
        height=96,
    )
    if _is_demo_mode():
        st.caption(
            "Lectura estructural preparada para sala. La metodología conduce; la interfaz hace visible la decisión."
        )
    else:
        st.caption(
            "Consola de lectura estructural guiada por analista. La metodología manda; la interfaz ordena, visualiza y exporta."
        )
    st.markdown(
        (
        f"""
        <div class="v2-header-shell" style="padding:18px 20px;border:1px solid #2a3947;border-radius:22px;
        background:linear-gradient(135deg,rgba(201,162,39,0.10),rgba(18,26,34,0.95));">
            <div style="font-size:12px;letter-spacing:0.16em;text-transform:uppercase;color:#9fb0bd;margin-bottom:8px;">
                Lectura estructural de poder
            </div>
            <div style="font-size:28px;line-height:1.08;font-weight:800;color:#edf3f7;max-width:860px;">
                Una consola para convertir lectura estructural experta en decisión clara, criterio visible y salida exportable.
            </div>
            <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:14px;">
                <span style="padding:6px 10px;border:1px solid #2a3947;border-radius:999px;font-size:11px;color:#d6e0e8;">Metodología propietaria</span>
                <span style="padding:6px 10px;border:1px solid #2a3947;border-radius:999px;font-size:11px;color:#d6e0e8;">Juicio experto asistido</span>
                <span style="padding:6px 10px;border:1px solid #2a3947;border-radius:999px;font-size:11px;color:#d6e0e8;">Diagnóstico + informe</span>
                <span style="padding:6px 10px;border:1px solid #2a3947;border-radius:999px;font-size:11px;color:#d6e0e8;">Salida ejecutiva</span>
            </div>
        </div>
        """
        if not _is_demo_mode()
        else f"""
        <div class="v2-header-shell" style="padding:22px 24px;border:1px solid #2a3947;border-radius:24px;
        background:
          radial-gradient(circle at top right, rgba(216,179,106,0.14), transparent 24%),
          radial-gradient(circle at 18% 22%, rgba(0,240,255,0.06), transparent 18%),
          linear-gradient(135deg,rgba(14,20,27,0.96),rgba(18,26,34,0.98));">
            <div style="font-size:12px;letter-spacing:0.18em;text-transform:uppercase;color:#d8b36a;margin-bottom:10px;">
                Lectura estructural para jurado
            </div>
            <div style="font-family:'Iowan Old Style','Palatino Linotype','Book Antiqua',Georgia,serif;font-size:34px;line-height:1.02;font-weight:700;color:#edf3f7;max-width:920px;">
                Hacer visible dónde el poder produce capacidad, dónde abre fuga y qué decisión conviene tomar antes de que la estructura pierda coherencia.
            </div>
            <div style="max-width:780px;margin-top:14px;font-size:15px;line-height:1.72;color:#c8d4dc;">
                Noumenon organiza evidencia, tensión y arquitectura de poder en una lectura ejecutiva clara, defendible y exportable.
            </div>
            <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:16px;">
                <span style="padding:6px 10px;border:1px solid #2a3947;border-radius:999px;font-size:11px;color:#d6e0e8;">Caso Helios preparado</span>
                <span style="padding:6px 10px;border:1px solid #2a3947;border-radius:999px;font-size:11px;color:#d6e0e8;">Lectura estructural guiada</span>
                <span style="padding:6px 10px;border:1px solid #2a3947;border-radius:999px;font-size:11px;color:#d6e0e8;">Decisión + informe</span>
            </div>
        </div>
        """
        ),
        unsafe_allow_html=True,
    )


def _open_section_shell(kicker: str, title: str, caption: str) -> None:
    st.markdown(
        f"""
        <div class="v2-section-shell">
            <div class="v2-section-kicker">{kicker}</div>
            <div style="font-size:28px;line-height:1.08;font-weight:800;color:#edf3f7;margin-bottom:8px;">{title}</div>
            <div style="font-size:14px;line-height:1.65;color:#9fb0bd;max-width:860px;">{caption}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_home_band(case: CaseRecord) -> None:
    snapshot = build_case_snapshot(case)
    has_diagnosis = "v2_diagnosis" in st.session_state
    progress = build_flow_progress(case, has_diagnosis)
    next_section, next_hint = recommend_next_step(case, has_diagnosis)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Evidencias activas", snapshot["evidence_count"])
    col2.metric("Frentes calibrados", snapshot["calibrated_count"])
    col3.metric("Evidencia sólida", snapshot["high_confidence_count"])
    col4.metric(
        "Mandato",
        "Definido" if snapshot["objective_set"] else "Pendiente",
    )
    st.caption(
        f"Estado del caso: {case.case_status} · Lecturas guardadas: {snapshot['snapshot_count']}"
    )
    st.markdown("### Recorrido")
    cols = st.columns(len(progress))
    for col, step in zip(cols, progress):
        status = step["status"]
        if status == "done":
            tone = "#6EE7B7"
            badge = "Hecho"
        elif status == "current":
            tone = "#D8B36A"
            badge = "Ahora"
        else:
            tone = "#8fa0ae"
            badge = "Luego"
        col.markdown(
            f"""
            <div class="v2-progress-card">
                <div style="font-size:11px;letter-spacing:0.12em;text-transform:uppercase;color:{tone};margin-bottom:8px;">{badge}</div>
                <div style="font-size:17px;font-weight:800;color:#edf3f7;margin-bottom:8px;">{step['label']}</div>
                <div style="font-size:12px;line-height:1.5;color:#9fb0bd;">{step['hint']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown("### Siguiente mejor paso")
    cta_col, hint_col = st.columns([0.28, 0.72])
    if cta_col.button(f"Ir a {next_section}", use_container_width=True):
        _queue_nav(next_section)
    hint_col.markdown(
        f"""
        <div style="margin-top:6px;padding:12px 14px;border:1px solid #2a3947;border-radius:16px;background:#10161d;">
            <div style="font-size:11px;letter-spacing:0.12em;text-transform:uppercase;color:#8ea1af;margin-bottom:6px;">Recomendación operativa</div>
            <div style="font-size:12px;color:#d6e0e8;line-height:1.6;">{next_hint}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("---")


def _render_demo_stage_band(case: CaseRecord) -> None:
    has_diagnosis = "v2_diagnosis" in st.session_state
    active_section = st.session_state.get("v2_nav_section", "04 · Diagnóstico")
    cards = [
        ("Caso", "Helios cargado", "done" if case.client_name == "Helios AI" else "current"),
        ("Lectura", "Generar diagnóstico", "done" if has_diagnosis else ("current" if active_section == "04 · Diagnóstico" else "pending")),
        ("Decisión", "Señalar contradicción", "current" if has_diagnosis and active_section == "04 · Diagnóstico" else "pending"),
        ("Informe", "Cerrar salida", "current" if active_section == "05 · Informe" else "pending"),
    ]
    st.markdown("### Recorrido de demo")
    cols = st.columns(len(cards))
    for col, (title, hint, status) in zip(cols, cards):
        tone = "#6EE7B7" if status == "done" else "#D8B36A" if status == "current" else "#8fa0ae"
        badge = "Listo" if status == "done" else "Ahora" if status == "current" else "Luego"
        col.markdown(
            f"""
            <div class="v2-progress-card">
                <div style="font-size:11px;letter-spacing:0.12em;text-transform:uppercase;color:{tone};margin-bottom:8px;">{badge}</div>
                <div style="font-size:17px;font-weight:800;color:#edf3f7;margin-bottom:8px;">{title}</div>
                <div style="font-size:12px;line-height:1.5;color:#9fb0bd;">{hint}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown("---")


def _render_section_footer(next_section: str, label: str) -> None:
    st.markdown("---")
    col1, col2 = st.columns([0.28, 0.72])
    if col1.button(label, use_container_width=True, key=f"goto_{next_section}_{label}"):
        _queue_nav(next_section)
    col2.caption(f"Siguiente tramo recomendado del recorrido: {next_section}")


def _render_case_tab(case: CaseRecord) -> None:
    _open_section_shell(
        "01 · Caso",
        "Mandato y encuadre",
        "Definimos aquí la decisión que queremos iluminar. Todo lo demás debe servir a este mandato ejecutivo.",
    )
    col1, col2 = st.columns(2)
    case.client_name = col1.text_input("Cliente", value=case.client_name)
    case.project_name = col2.text_input("Proyecto", value=case.project_name)
    case.analyst_name = col1.text_input("Analista", value=case.analyst_name)
    case.benchmark_name = col2.selectbox(
        "Base de referencia",
        options=BENCHMARK_OPTIONS,
        index=BENCHMARK_OPTIONS.index(case.benchmark_name)
        if case.benchmark_name in BENCHMARK_OPTIONS
        else 0,
    )
    case.case_status = col1.selectbox(
        "Estado del caso",
        options=CASE_STATUS_OPTIONS,
        index=CASE_STATUS_OPTIONS.index(case.case_status) if case.case_status in CASE_STATUS_OPTIONS else 0,
    )
    case.objective = st.text_area("Objetivo ejecutivo de lectura", value=case.objective, height=100)
    case.context = st.text_area("Contexto del caso", value=case.context, height=120)
    case.analyst_notes = st.text_area(
        "Notas maestras del analista",
        value=case.analyst_notes,
        height=140,
        help="Hipótesis, cautelas y claves de lectura que conviene arrastrar durante todo el caso.",
    )
    if not case.objective.strip() or not case.context.strip():
        st.warning("Antes de seguir, deja claro qué decisión quieres iluminar y en qué contexto se da.")
    _render_section_footer("02 · Evidencia", "Continuar a Evidencia")


def _render_evidence_tab(case: CaseRecord) -> None:
    _open_section_shell(
        "02 · Evidencia",
        "Base factual",
        "Una evidencia breve, concreta y defendible vale más que una automatización brillante pero dudosa. Aquí anclamos la lectura en hechos.",
    )
    power_code = st.selectbox(
        "Selecciona un poder",
        options=[power for power, _, _, _ in PODERES_INFO],
        format_func=lambda code: f"{code} · {POWER_LABELS[code]}",
    )
    assessment = case.assessments[power_code]
    st.markdown(f"### {power_code} · {assessment.power_title}")
    col1, col2 = st.columns([2, 1])
    assessment.evidence.summary = col1.text_area(
        "Síntesis de evidencia",
        value=assessment.evidence.summary,
        height=140,
        key=f"{power_code}_summary",
    )
    assessment.evidence.excerpts = col1.text_area(
        "Extractos o hechos",
        value=assessment.evidence.excerpts,
        height=140,
        key=f"{power_code}_excerpts",
    )
    assessment.evidence.analyst_note = col1.text_area(
        "Comentario del analista",
        value=assessment.evidence.analyst_note,
        height=110,
        key=f"{power_code}_analyst_note",
    )
    assessment.evidence.source = col2.selectbox(
        "Origen",
        options=["Manual", "Documento", "Entrevista", "Mixto"],
        index=["Manual", "Documento", "Entrevista", "Mixto"].index(assessment.evidence.source)
        if assessment.evidence.source in ["Manual", "Documento", "Entrevista", "Mixto"]
        else 0,
        key=f"{power_code}_source",
    )
    assessment.evidence.confidence = int(
        col2.slider(
            "Confianza",
            min_value=0,
            max_value=100,
            value=int(assessment.evidence.confidence),
            key=f"{power_code}_confidence",
        )
    )
    snapshot = build_case_snapshot(case)
    if snapshot["evidence_count"] < 3:
        st.info("Añade evidencia defendible en al menos tres poderes para que el diagnóstico tenga densidad suficiente.")
    else:
        st.success("La base factual ya tiene densidad mínima para una lectura expresiva.")
    _render_section_footer("03 · Estructura", "Pasar a Estructura")


def _render_structure_tab(case: CaseRecord) -> None:
    _open_section_shell(
        "03 · Estructura",
        "Ajuste estructural",
        "Aquí convertimos la metodología en una lectura ajustable de capacidad, estructura, autoridad y movimiento.",
    )
    power_code = st.selectbox(
        "Frente a ajustar",
        options=[power for power, _, _, _ in PODERES_INFO],
        format_func=lambda code: f"{code} · {POWER_LABELS[code]}",
        key="structure_power_code",
    )
    assessment = case.assessments[power_code]
    st.markdown(f"### {power_code} · {assessment.power_title}")
    st.markdown(
        """
        <div style="margin:0 0 16px 0;padding:14px 16px;border:1px solid #2a3947;border-radius:16px;background:#10161d;">
            <div style="font-size:11px;letter-spacing:0.12em;text-transform:uppercase;color:#d8b36a;margin-bottom:8px;">Guía de calibración</div>
            <div style="font-size:13px;line-height:1.65;color:#c9d5de;">
                M1 recoge potencia material. M2 expresa impulso intencional. M3 traduce forma instituida.
                R mide dominio operativo. C mide cohesión relacional. A expresa legitimidad angular.
                El vector de tendencia indica retracción o proyección del frente.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    row1 = st.columns(3)
    assessment.m1 = float(row1[0].slider("M1 · Potencia material", 0.0, 10.0, float(assessment.m1), 0.1, key=f"{power_code}_m1", help="La densidad física: cuerpos, dinero y hardware."))
    assessment.m2 = float(row1[1].slider("M2 · Impulso intencional", 0.0, 10.0, float(assessment.m2), 0.1, key=f"{power_code}_m2", help="La energía de la voluntad y la moral organizada."))
    assessment.m3 = float(row1[2].slider("M3 · Forma instituida", 0.0, 10.0, float(assessment.m3), 0.1, key=f"{power_code}_m3", help="El protocolo, la ley y el algoritmo que permanece."))
    row2 = st.columns(3)
    assessment.r = float(row2[0].slider("R · Dominio operativo", 0.0, 10.0, float(assessment.r), 0.1, key=f"{power_code}_r", help="Relación Hombre-Cosa: control técnico del entorno."))
    assessment.c = float(row2[1].slider("C · Cohesión relacional", 0.0, 10.0, float(assessment.c), 0.1, key=f"{power_code}_c", help="Relación Hombre-Hombre: fuerza de la red social."))
    assessment.a = float(row2[2].slider("A · Legitimidad angular", 0.0, 10.0, float(assessment.a), 0.1, key=f"{power_code}_a", help="Relación Hombre-Idea: respaldo de entes superiores."))
    assessment.flow = float(st.slider("Vector de tendencia · Retracción / Proyección", -3.0, 3.0, float(assessment.flow), 0.1, key=f"{power_code}_flow"))

    st.markdown("#### Vista rápida de conjunto")
    summary_rows = []
    for code, title, _, _ in PODERES_INFO:
        item = case.assessments[code]
        summary_rows.append(
            {
                "Poder": code,
                "Título": title,
                "Estructura disponible": round(item.m3, 1),
                "Autoridad operativa": round(item.a, 1),
                "Dirección": round(item.flow, 1),
            }
        )
    st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)
    if build_case_snapshot(case)["calibrated_count"] < 3:
        st.info("Ajusta varios frentes clave. Una lectura totalmente neutra suele producir conclusiones poco expresivas.")
    _render_section_footer("04 · Diagnóstico", "Ir a Diagnóstico")


def _render_diagnosis_tab(case: CaseRecord) -> None:
    _open_section_shell(
        "04 · Diagnóstico",
        "Lectura estructural",
        "Leemos la arquitectura del caso y priorizamos tensión, fragilidad y decisión ejecutiva.",
    )
    if st.button("Generar lectura ejecutiva", type="primary"):
        diagnosis = run_case_diagnosis(case)
        st.session_state["v2_diagnosis"] = diagnosis
        st.session_state["v2_comparison"] = build_snapshot_comparison(case, diagnosis)
        append_case_snapshot(case, diagnosis)
        if case.case_status == "Borrador":
            case.case_status = "Lectura en revisión"

    diagnosis = st.session_state.get("v2_diagnosis")
    if diagnosis is None:
        st.info("Todavía no se ha generado la lectura para este caso. Cuando la base factual y el ajuste estructural estén listos, genérala aquí.")
        return

    demo_mode = _is_demo_mode()
    structural_reading = build_structural_reading(case, diagnosis)
    editorial_frame = build_editorial_frame(diagnosis)
    archetype_comparison = build_archetype_comparison(diagnosis)
    comparison = st.session_state.get("v2_comparison")
    integrity_display, integrity_copy = describe_integrity(diagnosis.integrity)
    friction_display, friction_copy = describe_friction(diagnosis.friction)

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Integridad", integrity_display)
    k2.metric("Fricción", friction_display)
    k3.metric("Arquetipo dominante", diagnosis.archetype_name)
    k4.metric("Estado estructural", diagnosis.structural_state_name)
    sub1, sub2, _, _ = st.columns(4)
    sub1.caption(integrity_copy)
    sub2.caption(friction_copy)
    st.caption("La confianza de lectura expresa cuán sólida resulta la hipótesis con la evidencia y calibración hoy disponibles.")

    robustness_label = "Frontera activa" if diagnosis.archetype_hybrid else "Lectura bien separada"
    resolution_label = "Criterio decisivo" if diagnosis.priority_rule_applied else "Señal predominante"
    st.markdown(
        f"""
        <div style="display:grid;grid-template-columns:1fr 1.7fr 1fr;gap:12px;margin:18px 0 10px 0;">
            <div style="padding:16px 18px;border:1px solid #2a3947;border-radius:18px;background:#10161d;">
                <div style="font-size:11px;letter-spacing:0.12em;text-transform:uppercase;color:#8ea1af;margin-bottom:8px;">Lectura vecina</div>
                <div style="font-size:17px;line-height:1.45;font-weight:800;color:#edf3f7;">{archetype_comparison['runner_up_name']}</div>
                <div style="margin-top:8px;font-size:12px;line-height:1.55;color:#9fb0bd;">{robustness_label}</div>
            </div>
            <div style="padding:16px 18px;border:1px solid #2a3947;border-radius:18px;background:#10161d;">
                <div style="font-size:11px;letter-spacing:0.12em;text-transform:uppercase;color:#8ea1af;margin-bottom:8px;">Pregunta decisiva</div>
                <div style="font-size:15px;line-height:1.68;color:#dce6ed;">{archetype_comparison['decisive']}</div>
            </div>
            <div style="padding:16px 18px;border:1px solid #2a3947;border-radius:18px;background:#10161d;">
                <div style="font-size:11px;letter-spacing:0.12em;text-transform:uppercase;color:#8ea1af;margin-bottom:8px;">Cómo se cerró la lectura</div>
                <div style="font-size:17px;line-height:1.45;font-weight:800;color:#edf3f7;">{resolution_label}</div>
                <div style="margin-top:8px;font-size:12px;line-height:1.55;color:#9fb0bd;">{archetype_comparison['priority']}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        build_diagnosis_brief_html(
            integrity=diagnosis.integrity,
            friction=diagnosis.friction,
            archetype_name=diagnosis.archetype_name,
            structural_state_name=diagnosis.structural_state_name,
            archetype_hybrid=diagnosis.archetype_hybrid,
            top_risk=diagnosis.top_risk,
            lever_label=editorial_frame["lever_label"],
            lever_note=editorial_frame["lever_note"],
            executive_view=diagnosis.executive_view,
        ),
        unsafe_allow_html=True,
    )

    st.markdown('<div style="height:20px;"></div>', unsafe_allow_html=True)
    if not demo_mode:
        with st.expander("Ver criterio comparativo de clasificación", expanded=False):
            cmp_a, cmp_b, cmp_c = st.columns(3)
            cmp_a.markdown(
                f"""
                <div style="padding:18px;border:1px solid #2a3947;border-radius:18px;background:#10161d;min-height:230px;">
                    <div style="font-size:11px;letter-spacing:0.12em;text-transform:uppercase;color:#d8b36a;margin-bottom:8px;">Se activa por</div>
                    <div style="font-size:15px;line-height:1.68;color:#dce6ed;">{archetype_comparison['activation']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            cmp_b.markdown(
                f"""
                <div style="padding:18px;border:1px solid #2a3947;border-radius:18px;background:#10161d;min-height:230px;">
                    <div style="font-size:11px;letter-spacing:0.12em;text-transform:uppercase;color:#d8b36a;margin-bottom:8px;">No es {archetype_comparison['runner_up_name']}</div>
                    <div style="font-size:15px;line-height:1.68;color:#dce6ed;">{archetype_comparison['exclusion']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            cmp_c.markdown(
                f"""
                <div style="padding:18px;border:1px solid #2a3947;border-radius:18px;background:#10161d;min-height:230px;">
                    <div style="font-size:11px;letter-spacing:0.12em;text-transform:uppercase;color:#d8b36a;margin-bottom:8px;">Criterio decisivo</div>
                    <div style="font-size:15px;line-height:1.68;color:#dce6ed;">{archetype_comparison['decisive']}</div>
                    <div style="margin-top:12px;font-size:12px;line-height:1.6;color:#9fb0bd;">{archetype_comparison['framing']}</div>
                    <div style="margin-top:6px;font-size:12px;line-height:1.6;color:#7f909d;">{archetype_comparison['priority']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown('<div style="height:20px;"></div>', unsafe_allow_html=True)
    if demo_mode:
        st.markdown("### Lectura dominante")
        d1, d2, d3 = st.columns(3)
        d1.markdown(
            f"""
            <div style="padding:18px;border:1px solid #2a3947;border-radius:18px;background:#10161d;min-height:224px;">
                <div style="font-size:11px;letter-spacing:0.12em;text-transform:uppercase;color:#d8b36a;margin-bottom:8px;">Base estructural</div>
                <div style="font-size:15px;line-height:1.7;color:#dce6ed;">{structural_reading['causal_reading']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        d2.markdown(
            f"""
            <div style="padding:18px;border:1px solid #2a3947;border-radius:18px;background:#10161d;min-height:224px;">
                <div style="font-size:11px;letter-spacing:0.12em;text-transform:uppercase;color:#d8b36a;margin-bottom:8px;">Brecha principal</div>
                <div style="font-size:15px;line-height:1.7;color:#edf3f7;">{structural_reading['principal_leak']}</div>
                <div style="margin-top:14px;font-size:11px;letter-spacing:0.12em;text-transform:uppercase;color:#8ea1af;">Poder dominante</div>
                <div style="margin-top:8px;font-size:14px;line-height:1.65;color:#c3d0da;">{structural_reading['dominant_power']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        d3.markdown(
            f"""
            <div style="padding:18px;border:1px solid #2a3947;border-radius:18px;background:#10161d;min-height:224px;">
                <div style="font-size:11px;letter-spacing:0.12em;text-transform:uppercase;color:#d8b36a;margin-bottom:8px;">Movimiento mínimo</div>
                <div style="font-size:15px;line-height:1.7;color:#edf3f7;">{structural_reading['minimum_intervention']}</div>
                <div style="margin-top:14px;font-size:11px;letter-spacing:0.12em;text-transform:uppercase;color:#8ea1af;">Criterio decisivo</div>
                <div style="margin-top:8px;font-size:14px;line-height:1.65;color:#c3d0da;">{archetype_comparison['decisive']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown("### Fundamento de la lectura")
        col_a, col_b = st.columns(2)
        col_a.markdown(
            f"""
            <div style="padding:18px;border:1px solid #2a3947;border-radius:18px;background:#10161d;">
                <div style="font-size:11px;letter-spacing:0.12em;text-transform:uppercase;color:#d8b36a;margin-bottom:8px;">Base estructural</div>
                <div style="font-size:15px;line-height:1.7;color:#dce6ed;">{structural_reading['causal_reading']}</div>
                <div style="margin-top:14px;font-size:11px;letter-spacing:0.12em;text-transform:uppercase;color:#8ea1af;">Brecha principal</div>
                <div style="margin-top:8px;font-size:14px;line-height:1.65;color:#c3d0da;">{structural_reading['principal_leak']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        col_b.markdown(
            f"""
            <div style="padding:18px;border:1px solid #2a3947;border-radius:18px;background:#10161d;">
                <div style="font-size:11px;letter-spacing:0.12em;text-transform:uppercase;color:#d8b36a;margin-bottom:8px;">Evidencia que más pesa</div>
                <div style="font-size:14px;line-height:1.65;color:#edf3f7;margin-bottom:10px;">{structural_reading['dominant_power']}</div>
                <div style="font-size:14px;line-height:1.65;color:#c3d0da;">{structural_reading['dominant_evidence']}</div>
                <div style="margin-top:14px;font-size:11px;letter-spacing:0.12em;text-transform:uppercase;color:#8ea1af;">Lectura experta</div>
                <div style="margin-top:8px;font-size:14px;line-height:1.65;color:#c3d0da;">{structural_reading['dominant_note']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        col_c, col_d = st.columns(2)
        col_c.markdown(
            f"""
            <div style="padding:18px;border:1px solid #2a3947;border-radius:18px;background:#10161d;">
                <div style="font-size:11px;letter-spacing:0.12em;text-transform:uppercase;color:#d8b36a;margin-bottom:8px;">Movimiento mínimo recomendado</div>
                <div style="font-size:15px;line-height:1.7;color:#edf3f7;">{structural_reading['minimum_intervention']}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if comparison:
            col_d.markdown(
                f"""
                <div style="padding:18px;border:1px solid #2a3947;border-radius:18px;background:#10161d;">
                    <div style="font-size:11px;letter-spacing:0.12em;text-transform:uppercase;color:#d8b36a;margin-bottom:8px;">Comparación con lectura anterior</div>
                    <div style="font-size:14px;line-height:1.65;color:#edf3f7;">{comparison['direction']}</div>
                    <div style="margin-top:12px;font-size:13px;line-height:1.6;color:#9fb0bd;">Anterior: {comparison['previous_label']} · {comparison['previous_archetype']} · {comparison['previous_state']} · {comparison['previous_risk']}</div>
                    <div style="margin-top:8px;font-size:13px;line-height:1.6;color:#9fb0bd;">Nodo anterior: {comparison['previous_power']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            col_d.info("Todavía no hay una lectura anterior comparable. Ejecuta una nueva iteración tras ajustar evidencia o estructura.")

    st.markdown('<div style="height:20px;"></div>', unsafe_allow_html=True)
    rows = build_power_summary_rows(diagnosis.core)
    df = pd.DataFrame(rows)
    st.markdown("#### Radar de potencia")
    st.caption("No mide calidad moral ni desempeño absoluto. Muestra cómo se distribuye la potencia entre poderes dentro del caso.")
    radar_svg = build_radar_svg_from_core_with_size(diagnosis.core, size=600.0)
    st.components.v1.html(radar_svg, height=860)
    st.markdown('<div style="height:18px;"></div>', unsafe_allow_html=True)
    st.markdown("#### Mapa de desequilibrio")
    st.caption("Cruza potencia y fricción por nodo. El tamaño expresa estructura y el color expresa autoridad operativa.")
    tension_map_svg = build_power_tension_map_svg(rows, width=1100, height=560)
    st.components.v1.html(tension_map_svg, height=560)
    if not demo_mode:
        st.markdown('<div style="height:18px;"></div>', unsafe_allow_html=True)
        st.markdown("#### Matriz de tensión")
        st.caption("Lectura horizontal por poder: capacidad visible, fricción, forma estructural y autoridad operativa en paralelo.")
        heatmap_svg = build_structural_heatmap_svg(rows, width=1100, row_height=48)
        st.components.v1.html(heatmap_svg, height=580)
        st.markdown('<div style="height:18px;"></div>', unsafe_allow_html=True)
        st.markdown("#### Tabla analítica")
        st.caption("Potencia se lee en escala 0-100. Estructura y autoridad se leen en escala 0-10. La tabla está ordenada por fricción estructural descendente.")
        st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown('<div style="height:20px;"></div>', unsafe_allow_html=True)
    st.markdown("### Decisión")
    panel = diagnosis.decision_panel
    st.write(panel.get("executive_decision") or panel.get("risk_msg") or diagnosis.one_liner)

    if not demo_mode:
        with st.expander("Ver salida técnica interna", expanded=False):
            st.json(
                {
                    "one_liner": diagnosis.one_liner,
                    "decision_panel": diagnosis.decision_panel,
                    "executive_view": diagnosis.executive_view,
                }
            )
    _render_section_footer("05 · Informe", "Cerrar con Informe")


def _render_report_tab(case: CaseRecord) -> None:
    _open_section_shell(
        "05 · Informe",
        "Salida ejecutiva",
        "Convertimos la lectura en una pieza entregable, exportable y defendible frente a cliente o comité.",
    )
    diagnosis = st.session_state.get("v2_diagnosis")
    if diagnosis is None:
        st.info("Genera primero la lectura: el informe es la salida final, no el punto de partida.")
        return

    public_jury_mode = _is_public_jury_mode()
    if case.case_status != "Informe listo":
        case.case_status = "Informe listo"

    report_variant = "jury" if _is_demo_mode() else "default"
    html = build_report_html(case, diagnosis, variant=report_variant)
    st.success(
        "La lectura ya está en fase de salida para jurado." if _is_demo_mode()
        else "La lectura ya está en fase de salida comercial. Aquí conviertes el caso en entregable."
    )
    editorial_note = (
        "El informe está maquetado como pieza de concurso: apertura nítida, revelación estructural, decisión y cierre ejecutivo."
        if _is_demo_mode()
        else "El informe ya está maquetado como salida ejecutiva: apertura, mandato, priorización, visualización estructural y cierre metodológico."
    )
    board_ready_note = (
        "Esta salida ya contiene tesis central, contradicción principal, decisión ejecutiva y visualización estructural lista para sala."
        if _is_demo_mode()
        else "Esta salida ya contiene tesis central, decisión ejecutiva, visualización estructural y criterio claro de priorización. Está pensada para leerse bien tanto en revisión individual como en conversación de comité."
    )

    report_col, delivery_col = st.columns([1.25, 0.75])
    report_col.markdown(
        f"""
        <div class="v2-premium-panel" style="margin:10px 0 18px 0;">
            <div class="v2-premium-label">Revisión editorial</div>
            <div style="font-size:15px;line-height:1.7;color:#d7e1e8;">
                {editorial_note}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    report_col.markdown(
        f"""
        <div class="v2-premium-panel" style="margin:0 0 18px 0;">
            <div class="v2-premium-label" style="color:#8ea1af;">Checklist de sala</div>
            <div style="font-size:14px;line-height:1.75;color:#d7e1e8;">
                {board_ready_note}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    delivery_col.markdown(
        """
        <div class="v2-premium-panel" style="margin:10px 0 18px 0;">
            <div class="v2-premium-label">Salida disponible</div>
            <div style="font-size:18px;line-height:1.3;font-weight:800;color:#edf3f7;margin-bottom:10px;">
                El caso ya puede cerrarse como entregable real.
            </div>
            <div style="font-size:13px;line-height:1.7;color:#c7d3db;">
                Puedes revisar la maqueta HTML, preparar la exportación en PDF y conservar una versión lista para jurado, cliente o comité.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    html_actions_col, pdf_actions_col = st.columns(2)
    html_actions_col.download_button(
        "Descargar informe HTML",
        data=html,
        file_name=f"{case.case_id}.html",
        mime="text/html",
        use_container_width=True,
    )
    if (not public_jury_mode) and html_actions_col.button("Guardar HTML en disco", use_container_width=True):
        saved = save_report_html(case, diagnosis, variant=report_variant)
        st.success(f"Informe guardado en {saved}")

    if public_jury_mode:
        st.markdown(
            """
            <div class="v2-premium-panel" style="margin:18px 0 18px 0;">
                <div class="v2-premium-label" style="color:#8ea1af;">Exportación PDF</div>
                <div style="font-size:14px;line-height:1.75;color:#d7e1e8;">
                    En la demo pública priorizamos estabilidad y lectura directa en pantalla. La exportación PDF queda reservada para demostración controlada y sesión presencial.
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown("### Exportación PDF")
        st.caption("Generación real en PDF usando Playwright. Si falta Chromium, normalmente basta con `playwright install chromium`.")
        if pdf_actions_col.button("Generar PDF", type="primary", use_container_width=True):
            try:
                pdf_bytes = render_pdf_bytes_from_html(html)
                st.session_state["v2_pdf_bytes"] = pdf_bytes
                st.session_state["v2_pdf_filename"] = build_v2_pdf_filename(case)
                st.success("PDF preparado correctamente.")
            except Exception as exc:
                st.error(f"No se pudo generar el PDF: {exc}")

        pdf_bytes = st.session_state.get("v2_pdf_bytes")
        pdf_filename = st.session_state.get("v2_pdf_filename") or build_v2_pdf_filename(case)
        if pdf_bytes:
            pdf_dl_col, pdf_save_col = st.columns(2)
            pdf_dl_col.download_button(
                "Descargar informe PDF",
                data=pdf_bytes,
                file_name=pdf_filename,
                mime="application/pdf",
                use_container_width=True,
            )
            if pdf_save_col.button("Guardar PDF en disco", use_container_width=True):
                saved_pdf = save_pdf_bytes(case, pdf_bytes)
                st.success(f"PDF guardado en {saved_pdf}")

    with st.expander("Vista previa HTML", expanded=True):
        st.components.v1.html(html, height=840, scrolling=True)


def render_app() -> None:
    _sync_public_jury_state()
    _render_header()
    _render_sidebar()
    _sync_demo_mode_state()
    case = _ensure_case_state()
    if _is_demo_mode():
        _render_demo_stage_band(case)
    else:
        _render_home_band(case)

    section = st.session_state.get("v2_nav_section", "01 · Caso")
    if _is_public_jury_mode() and section not in {"04 · Diagnóstico", "05 · Informe"}:
        section = "04 · Diagnóstico"
        st.session_state["v2_nav_section"] = section
    if section == "01 · Caso":
        _render_case_tab(case)
    elif section == "02 · Evidencia":
        _render_evidence_tab(case)
    elif section == "03 · Estructura":
        _render_structure_tab(case)
    elif section == "04 · Diagnóstico":
        _render_diagnosis_tab(case)
    elif section == "05 · Informe":
        _render_report_tab(case)
