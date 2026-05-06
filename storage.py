import os
import json
import datetime
import numpy as np
import pandas as pd
import streamlit as st

from analysis import build_motor_debug_trace
from engine_akxom import PODERES_INFO, recover_structured_params_from_matrix

# Payload JSON: subir cuando cambie el contrato (tensor + evidencias + núcleo motor).
PAYLOAD_SCHEMA_VERSION = 4


def _ingest_meta_from_session() -> dict[str, dict]:
    """Metadatos del ingestor por poder (keyword / tensión) para trazabilidad Fase 1."""
    meta: dict[str, dict] = {}
    for p_code, _, _, _ in PODERES_INFO:
        kw = st.session_state.get(f"{p_code}_ingest_keyword", "")
        tk = st.session_state.get(f"{p_code}_ingest_tension_keyword", "")
        tm = st.session_state.get(f"{p_code}_ingest_tension_matched", False)
        if kw or tk or tm:
            meta[p_code] = {
                "keyword": str(kw or ""),
                "tension_keyword": str(tk or ""),
                "tension_matched": bool(tm),
            }
    return meta


def _apply_ingest_meta_to_session(meta_by_power: dict | None) -> None:
    if not meta_by_power:
        return
    for p_code, row in meta_by_power.items():
        if not isinstance(row, dict):
            continue
        st.session_state[f"{p_code}_ingest_keyword"] = str(row.get("keyword") or "")
        st.session_state[f"{p_code}_ingest_tension_keyword"] = str(
            row.get("tension_keyword") or ""
        )
        st.session_state[f"{p_code}_ingest_tension_matched"] = bool(
            row.get("tension_matched", False)
        )


def _apply_evidence_table_rows_to_session(rows: list | None) -> None:
    """Restaura notas/origen/confianza desde la tabla guardada (fuente de verdad)."""
    if not rows:
        return
    for row in rows:
        if not isinstance(row, dict):
            continue
        pc = row.get("Poder")
        if not pc:
            continue
        st.session_state[f"{pc}_note"] = str(row.get("Nota") or "")
        st.session_state[f"{pc}_source"] = str(row.get("Origen") or "Manual")
        try:
            st.session_state[f"{pc}_confidence"] = int(row.get("Confianza") or 50)
        except (TypeError, ValueError):
            st.session_state[f"{pc}_confidence"] = 50


DATA_DIR = "noumenon_data"


def ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def make_json_safe(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, pd.DataFrame):
        return make_json_safe(value.to_dict(orient="records"))
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, dict):
        return {k: make_json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [make_json_safe(v) for v in value]
    if isinstance(value, tuple):
        return [make_json_safe(v) for v in value]
    return value


def build_analysis_payload(
    client_name,
    project_name,
    analyst_name,
    target,
    T,
    flows,
    result,
    evidence_df: pd.DataFrame | None = None,
    contradictions: list | None = None,
    trace_df: pd.DataFrame | None = None,
    core_for_debug: dict | None = None,
):
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    notes = {
        p_code: st.session_state.get(f"{p_code}_note", "")
        for p_code, _, _, _ in PODERES_INFO
    }
    sources = {
        p_code: st.session_state.get(f"{p_code}_source", "Manual")
        for p_code, _, _, _ in PODERES_INFO
    }
    confidences = {
        p_code: st.session_state.get(f"{p_code}_confidence", 50)
        for p_code, _, _, _ in PODERES_INFO
    }
    evidence_by_power = {
        p_code: {
            "text": notes.get(p_code, ""),
            "source": sources.get(p_code, "Manual"),
            "confidence": int(confidences.get(p_code, 50)),
            "ingest_keyword": str(st.session_state.get(f"{p_code}_ingest_keyword", "") or ""),
            "ingest_tension_keyword": str(
                st.session_state.get(f"{p_code}_ingest_tension_keyword", "") or ""
            ),
            "ingest_tension_matched": bool(
                st.session_state.get(f"{p_code}_ingest_tension_matched", False)
            ),
        }
        for p_code, _, _, _ in PODERES_INFO
    }

    trace_records: list = []
    if trace_df is not None and not trace_df.empty:
        try:
            trace_records = make_json_safe(trace_df)
        except Exception:
            trace_records = []

    benchmark_name = str(st.session_state.get("benchmark_name") or "")

    payload = {
        "schema_version": PAYLOAD_SCHEMA_VERSION,
        "saved_at": now,
        "client_name": client_name,
        "project_name": project_name,
        "analyst_name": analyst_name,
        "target": target,
        "tensor": np.asarray(T, dtype=float).tolist(),
        "flows": list(flows),
        "notes": notes,
        "sources": sources,
        "confidences": confidences,
        "evidence_by_power": evidence_by_power,
        "context_note": (st.session_state.get("consola_context_note") or "").strip(),
        "result": make_json_safe(result),
        "ingest": {
            "ranked_selection": st.session_state.get("doc_selected_ranked") or [],
            "meta_by_power": _ingest_meta_from_session(),
        },
        "traceability_snapshot": {
            "benchmark_name": benchmark_name,
            "contradictions": make_json_safe(contradictions or []),
            "trace_df": trace_records,
        },
    }

    if evidence_df is not None and not evidence_df.empty:
        try:
            payload["evidence_table"] = make_json_safe(evidence_df)
        except Exception:
            payload["evidence_table"] = []
    else:
        payload["evidence_table"] = []

    if core_for_debug is not None:
        payload["motor_debug"] = make_json_safe(build_motor_debug_trace(core_for_debug))
        ev = core_for_debug.get("executive_view")
        if isinstance(ev, dict) and ev:
            payload["executive_view"] = make_json_safe(ev)
        ds = core_for_debug.get("decision_scenarios")
        if isinstance(ds, dict) and ds:
            payload["decision_scenarios"] = make_json_safe(ds)

    return payload


def save_analysis_json(payload):
    ensure_data_dir()

    safe_client = payload["client_name"].strip().replace(" ", "_") or "client"
    safe_project = payload["project_name"].strip().replace(" ", "_") or "project"
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    filename = f"{safe_client}__{safe_project}__{ts}.json"
    filepath = os.path.join(DATA_DIR, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    return filepath


def list_saved_analyses():
    ensure_data_dir()

    files = []
    for name in os.listdir(DATA_DIR):
        if name.endswith(".json"):
            files.append(name)

    files.sort(reverse=True)
    return files


def load_analysis_json(filename):
    filepath = os.path.join(DATA_DIR, filename)

    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def apply_loaded_analysis_to_session(payload, source_filename: str | None = None):
    tensor = np.asarray(payload["tensor"], dtype=float)
    flows = payload["flows"]

    st.session_state["loaded_target"] = payload["target"]
    st.session_state["loaded_client_name"] = payload["client_name"]
    st.session_state["loaded_project_name"] = payload["project_name"]
    st.session_state["loaded_analyst_name"] = payload["analyst_name"]

    for i, (p_code, _, _, _) in enumerate(PODERES_INFO):
        matrix = tensor[i]
        m1, m2, m3, r, c, a = recover_structured_params_from_matrix(matrix)
        st.session_state[f"{p_code}_m1"] = m1
        st.session_state[f"{p_code}_m2"] = m2
        st.session_state[f"{p_code}_m3"] = m3
        st.session_state[f"{p_code}_r"] = r
        st.session_state[f"{p_code}_c"] = c
        st.session_state[f"{p_code}_a"] = a

        st.session_state[f"{p_code}_flow"] = float(flows[i])

    et = payload.get("evidence_table")
    if et and isinstance(et, list) and len(et) > 0:
        _apply_evidence_table_rows_to_session(et)
    elif "notes" in payload:
        for p_code, note in payload["notes"].items():
            st.session_state[f"{p_code}_note"] = note

    if "sources" in payload and not (et and isinstance(et, list) and len(et) > 0):
        for p_code, source in payload["sources"].items():
            st.session_state[f"{p_code}_source"] = source

    if "confidences" in payload and not (et and isinstance(et, list) and len(et) > 0):
        for p_code, confidence in payload["confidences"].items():
            st.session_state[f"{p_code}_confidence"] = int(confidence)

    if et and isinstance(et, list) and len(et) > 0:
        for p_code, _, _, _ in PODERES_INFO:
            st.session_state.setdefault(f"{p_code}_source", "Manual")
            st.session_state.setdefault(f"{p_code}_confidence", 50)

    ingest = payload.get("ingest") if isinstance(payload.get("ingest"), dict) else {}
    _apply_ingest_meta_to_session(ingest.get("meta_by_power"))
    ranked = ingest.get("ranked_selection")
    if isinstance(ranked, list):
        st.session_state["doc_selected_ranked"] = ranked

    evp = payload.get("evidence_by_power")
    if isinstance(evp, dict) and evp:
        for p_code, row in evp.items():
            if not isinstance(row, dict):
                continue
            if row.get("ingest_keyword") or row.get("ingest_tension_keyword"):
                st.session_state[f"{p_code}_ingest_keyword"] = str(row.get("ingest_keyword") or "")
                st.session_state[f"{p_code}_ingest_tension_keyword"] = str(
                    row.get("ingest_tension_keyword") or ""
                )
                st.session_state[f"{p_code}_ingest_tension_matched"] = bool(
                    row.get("ingest_tension_matched", False)
                )

    if payload.get("context_note"):
        st.session_state["consola_context_note"] = str(payload["context_note"])

    if "evidence_table" in payload and payload["evidence_table"]:
        st.session_state["loaded_evidence_table"] = payload["evidence_table"]

    snap = payload.get("traceability_snapshot")
    if isinstance(snap, dict) and snap:
        st.session_state["noumenon_traceability_snapshot"] = snap
        bn = snap.get("benchmark_name")
        if bn:
            st.session_state["benchmark_name"] = str(bn)
    if source_filename:
        st.session_state["noumenon_audit_source_file"] = source_filename
    st.session_state["noumenon_payload_saved_at"] = str(payload.get("saved_at") or "")