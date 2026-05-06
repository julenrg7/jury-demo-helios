"""
Pipeline «Auto-evaluar (1 click)» sin Streamlit: auto base + evidencia + auto-fill.
La UI en app.py sincroniza el tensor resultante a session_state.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from analysis import generate_auto_base
from doc_ingest import (
    _normalize_text,
    ingest_disclosure_profile,
    propose_pi_notes_from_chunks,
    propose_pi_notes_from_text,
)
from engine_akxom import (
    PODERES_INFO,
    build_empty_tensor,
    recover_structured_params_from_matrix,
    set_power_structured,
)

# Fase 2.6: perfiles estructurales por poder (orden: m1, m2, m3, r, c, a)
DOC_PROFILE_OFFSETS = {
    "P3": (-0.2, 0.5, -0.4, 0.7, 0.4, 0.3),
    "P4": (0.4, 0.1, -0.35, 0.55, 0.45, 0.25),
    "P5": (0.1, -0.2, 0.7, 0.2, -0.2, 0.8),
    "P6": (0.9, 0.1, -0.8, 1.0, 0.2, -0.6),
    "P7": (0.35, 0.25, 0.45, 0.55, 0.3, 0.7),
    "P8": (0.2, 0.4, -0.5, 0.5, -0.1, 0.6),
    "P9": (0.8, 0.2, 0.1, 0.7, 0.2, -0.2),
    "P10": (-0.3, 0.7, 0.2, -0.2, 0.4, 0.9),
}
DOC_TENSION_KEYWORDS = ("friccion", "deuda", "liquidez", "regulator", "desgaste", "conflicto", "presion")

DOC_AUTOFILL_DEFAULT_PARAMS = {
    "drop_m3_base": 2.8,
    "drop_m3_slope": 2.4,
    "drop_a_base": 2.6,
    "drop_a_slope": 2.2,
    "flow_drop_base": 0.9,
    "flow_drop_slope": 0.8,
}


def _apply_prospectus_cap_to_tensor(T: np.ndarray, ingest_prof: dict[str, Any]) -> np.ndarray:
    """Misma lógica que el camino heurístico: tope P5/P6 en contexto prospecto."""
    if not bool(ingest_prof.get("offering_prospectus_context")):
        return T
    cap56 = 7.25 if bool(ingest_prof.get("prospectus_profitability_lift")) else 6.0
    out = T
    for idx in (4, 5):
        m1, m2, m3, r, c, a = recover_structured_params_from_matrix(out[idx])
        out = set_power_structured(
            out,
            idx,
            min(float(m1), cap56),
            min(float(m2), cap56),
            min(float(m3), cap56),
            min(float(r), cap56),
            min(float(c), cap56),
            min(float(a), cap56),
        )
    return out


def select_top_powers_state_from_text(
    text: str,
    *,
    ingest_chunks: list[str] | None = None,
    min_note_chars: int = 70,
    max_powers_to_apply: int = 5,
) -> list[dict[str, Any]]:
    """Selección top-N poderes desde texto (Fase 2.3) o desde fragmentos (Fase 2 PDF por página)."""
    if ingest_chunks:
        suggestions = propose_pi_notes_from_chunks(ingest_chunks)
    else:
        suggestions = propose_pi_notes_from_text(text)
    ranked_candidates = []
    for p_code, _, _, _ in PODERES_INFO:
        s = suggestions.get(
            p_code,
            {
                "note": "",
                "confidence": 50,
                "score": 0,
                "keyword": "",
                "tension_matched": False,
                "tension_keyword": "",
                "rupture_collapse": False,
            },
        )
        note = str(s.get("note", "") or "").strip()
        conf = int(s.get("confidence", 50))
        score = int(s.get("score", 0))
        keyword = str(s.get("keyword", "") or "")
        tension_matched = bool(s.get("tension_matched", False))
        tension_keyword = str(s.get("tension_keyword", "") or "")
        rupture_collapse = bool(s.get("rupture_collapse", False))

        if len(note) < min_note_chars:
            continue
        ranked_candidates.append(
            (p_code, note, conf, score, keyword, tension_matched, tension_keyword, rupture_collapse)
        )

    ranked_candidates.sort(key=lambda x: (x[2], x[3]), reverse=True)
    selected_ranked = ranked_candidates[:max_powers_to_apply]
    return [
        {
            "p_code": p_code,
            "note": note,
            "confidence": conf,
            "score": score,
            "keyword": keyword,
            "tension_matched": tension_matched,
            "tension_keyword": tension_keyword,
            "rupture_collapse": rupture_collapse,
        }
        for p_code, note, conf, score, keyword, tension_matched, tension_keyword, rupture_collapse in selected_ranked
    ]


def apply_autofill_to_tensor_and_flows(
    selected_ranked_state: list[dict[str, Any]],
    *,
    autofill_mode: str = "Fuerte",
    min_conf_for_fill: int = 60,
    params: dict[str, float] | None = None,
) -> tuple[np.ndarray, list[float]]:
    """
    Auto-fill estructural (2.5 + 2.6) sobre tensor base todo 5 + flows 0.
    (Calibración interna; no incluye auto base organizacional.)
    """
    params = params or DOC_AUTOFILL_DEFAULT_PARAMS

    if autofill_mode == "Conservador":
        lo, hi = 5.8, 7.2
        mode_scale = 0.75
    elif autofill_mode == "Fuerte":
        lo, hi = 6.8, 8.8
        mode_scale = 1.10
    else:
        lo, hi = 6.2, 8.0
        mode_scale = 0.9

    dims = ["m1", "m2", "m3", "r", "c", "a"]
    T = build_empty_tensor()
    for i, (_, _, _, _) in enumerate(PODERES_INFO):
        T = set_power_structured(T, i, 5.0, 5.0, 5.0, 5.0, 5.0, 5.0)

    flows = [0.0 for _ in range(10)]

    for item in selected_ranked_state:
        p_code = str(item.get("p_code", ""))
        conf = int(item.get("confidence", 50))
        tension_matched = bool(item.get("tension_matched", False))
        rupture_collapse = bool(item.get("rupture_collapse", False))

        if conf < int(min_conf_for_fill):
            continue

        idx = int([i for i, (pc, _, _, _) in enumerate(PODERES_INFO) if pc == p_code][0])

        if rupture_collapse:
            # Ruptura estructural: valor fijo 1.0 (KEYWORDS_RUPTURA); sin promedio con halos positivos.
            col = 1.0
            T = set_power_structured(T, idx, col, col, col, col, col, col)
            flows[idx] = float(np.clip(flows[idx] - 2.2, -3.0, 3.0))
            continue

        conf_norm = max(0.0, min(1.0, (conf - 50) / 45.0))
        score = int(item.get("score", 0))
        score_norm = max(0.0, min(1.0, score / 6.0))
        strength = 0.75 * conf_norm + 0.25 * score_norm
        target = float(round(lo + (hi - lo) * strength, 2))

        offsets = DOC_PROFILE_OFFSETS.get(p_code, (0.0, 0.0, 0.0, 0.0, 0.0, 0.0))
        tension_factor = conf_norm if tension_matched else 0.0

        drop_m3 = float(params["drop_m3_base"] + params["drop_m3_slope"] * tension_factor) if tension_matched else 0.0
        drop_a = float(params["drop_a_base"] + params["drop_a_slope"] * tension_factor) if tension_matched else 0.0
        flow_drop = float(params["flow_drop_base"] + params["flow_drop_slope"] * tension_factor) if tension_matched else 0.0

        after_vals: list[float] = []
        for d, off in zip(dims, offsets):
            val = float(np.clip(target + off * mode_scale, 0.0, 10.0))
            if tension_matched:
                if d == "m3":
                    val = float(np.clip(val - drop_m3, 0.0, 10.0))
                if d == "a":
                    val = float(np.clip(val - drop_a, 0.0, 10.0))
                if d == "r":
                    val = float(np.clip(val - 0.35 * drop_m3, 0.0, 10.0))
                if d == "c":
                    val = float(np.clip(val - 0.20 * drop_m3, 0.0, 10.0))
            after_vals.append(val)

        m1, m2, m3, r, c, a = after_vals
        T = set_power_structured(T, idx, m1, m2, m3, r, c, a)
        flows[idx] = float(np.clip(flows[idx] - flow_drop, -3.0, 3.0))

    return T, flows


def run_one_click_pipeline(
    text: str,
    *,
    ingest_chunks: list[str] | None = None,
    org_type: str = "Corporación tecnológica",
    tech_intensity: float = 7.0,
    regulation_level: float = 5.0,
    capital_intensity: float = 6.0,
    competitive_pressure: float = 6.0,
    min_conf_for_fill: int | None = None,
    autofill_params: dict[str, float] | None = None,
    use_llm_ingest: bool = False,
) -> dict[str, Any]:
    """
    Replica la lógica del botón «Auto-evaluar (1 click)»: generate_auto_base + top5 + auto-fill.

    Con use_llm_ingest=True, el tensor se construye desde JSON AKXOM vía LLM (sin reglas de keywords).
    Requiere OPENAI_API_KEY y el paquete openai.
    """
    _tl = _normalize_text(str(text or "")).lower()
    _ingest_prof = ingest_disclosure_profile(_tl)
    mcf_out = 65 if min_conf_for_fill is None else int(min_conf_for_fill)

    if use_llm_ingest:
        from llm_ingest import (
            akxom_flows_from_json,
            akxom_json_to_tensor,
            build_selected_ranked_state_from_llm,
            llm_parse_text_to_akxom_json,
        )

        parts = [str(text or "").strip()]
        if ingest_chunks:
            parts.extend(str(c or "").strip() for c in ingest_chunks if str(c or "").strip())
        llm_text = "\n\n".join(parts)
        if not llm_text.strip():
            raise ValueError("use_llm_ingest requiere texto no vacío (nota o fragmentos).")
        data = llm_parse_text_to_akxom_json(llm_text)
        T = akxom_json_to_tensor(data)
        T = _apply_prospectus_cap_to_tensor(T, _ingest_prof)
        flows_list = akxom_flows_from_json(data)
        selected_ranked_state = build_selected_ranked_state_from_llm(data)
        return {
            "T": T,
            "flows": flows_list,
            "selected_ranked_state": selected_ranked_state,
            "auto_mode": "LLM",
            "autofill_applied": 10,
            "min_conf_used": mcf_out,
            "ingest_profile": _ingest_prof,
            "llm_akxom_json": data,
        }

    auto_base = generate_auto_base(
        org_type, tech_intensity, regulation_level, capital_intensity, competitive_pressure
    )
    state: dict[str, dict[str, float]] = {}
    flows_map: dict[str, float] = {}
    for p_code, vals in auto_base.items():
        m1, m2, m3, r, c, a = vals
        state[p_code] = {
            "m1": float(m1),
            "m2": float(m2),
            "m3": float(m3),
            "r": float(r),
            "c": float(c),
            "a": float(a),
        }
        flows_map[p_code] = 0.0

    selected_ranked_state = select_top_powers_state_from_text(
        text, ingest_chunks=ingest_chunks
    )
    auto_mode = "Fuerte" if any(bool(x.get("tension_matched")) for x in selected_ranked_state) else "Estandar"

    _tension_drop_scale = float(_ingest_prof.get("autofill_tension_drop_scale", 1.0))
    _critical_incident = bool(_ingest_prof.get("critical_incident_evidence"))

    mcf = 65 if min_conf_for_fill is None else int(min_conf_for_fill)
    if selected_ranked_state and all(int(x.get("confidence", 50)) < mcf for x in selected_ranked_state):
        mcf = 60

    params = autofill_params or DOC_AUTOFILL_DEFAULT_PARAMS

    if auto_mode == "Conservador":
        lo, hi = 5.8, 7.2
        mode_scale = 0.75
    elif auto_mode == "Fuerte":
        lo, hi = 6.8, 8.8
        mode_scale = 1.10
    else:
        lo, hi = 6.2, 8.0
        mode_scale = 0.9

    dims = ["m1", "m2", "m3", "r", "c", "a"]
    autofill_applied = 0

    for item in selected_ranked_state:
        p_code = str(item.get("p_code", ""))
        conf = int(item.get("confidence", 50))
        score = int(item.get("score", 0))
        if conf < mcf:
            continue
        autofill_applied += 1

        if bool(item.get("rupture_collapse", False)):
            col = 1.0
            state[p_code] = {"m1": col, "m2": col, "m3": col, "r": col, "c": col, "a": col}
            flows_map[p_code] = float(np.clip(flows_map[p_code] - 2.2, -3.0, 3.0))
            continue

        conf_norm = max(0.0, min(1.0, (conf - 50) / 45.0))
        score_norm = max(0.0, min(1.0, score / 6.0))
        strength = 0.75 * conf_norm + 0.25 * score_norm
        target_auto = float(round(lo + (hi - lo) * strength, 2))
        if _critical_incident and p_code in ("P5", "P8", "P9"):
            target_auto = min(target_auto, 6.05)

        offsets = DOC_PROFILE_OFFSETS.get(p_code, (0.0, 0.0, 0.0, 0.0, 0.0, 0.0))
        tension = bool(item.get("tension_matched", False))
        if (
            p_code == "P9"
            and bool(_ingest_prof.get("p9_moat_hardening_narrative"))
            and target_auto > 7.5
        ):
            tension = False
        tension_factor = conf_norm if tension else 0.0

        drop_m3 = 0.0
        drop_a = 0.0
        if tension:
            drop_m3 = float(params["drop_m3_base"] + params["drop_m3_slope"] * tension_factor) * _tension_drop_scale
            drop_a = float(params["drop_a_base"] + params["drop_a_slope"] * tension_factor) * _tension_drop_scale

        after_vals = []
        for d, off in zip(dims, offsets):
            val = float(target_auto + off * mode_scale)
            if tension:
                if d == "m3":
                    val -= drop_m3
                if d == "a":
                    val -= drop_a
                if d == "r":
                    val -= 0.35 * drop_m3
                if d == "c":
                    val -= 0.20 * drop_m3
            val = float(np.clip(val, 0.0, 10.0))
            after_vals.append(val)

        m1, m2, m3, r, c, a = after_vals
        state[p_code] = {"m1": m1, "m2": m2, "m3": m3, "r": r, "c": c, "a": a}

        if tension:
            flow_before = flows_map[p_code]
            flow_drop = (
                float(params["flow_drop_base"] + params["flow_drop_slope"] * tension_factor)
                * _tension_drop_scale
            )
            flows_map[p_code] = float(np.clip(flow_before - flow_drop, -3.0, 3.0))

    # S-1 / prospecto: cap P5 y P6 (madurez institucional y economía consolidada no infiere del vestido legal).
    if bool(_ingest_prof.get("offering_prospectus_context")):
        cap56 = 7.25 if bool(_ingest_prof.get("prospectus_profitability_lift")) else 6.0
        for pc in ("P5", "P6"):
            s = state.get(pc)
            if not s:
                continue
            for k in dims:
                s[k] = float(min(float(s[k]), cap56))

    T = build_empty_tensor()
    flows_list: list[float] = []
    for i, (p_code, _, _, _) in enumerate(PODERES_INFO):
        s = state[p_code]
        T = set_power_structured(T, i, s["m1"], s["m2"], s["m3"], s["r"], s["c"], s["a"])
        flows_list.append(flows_map[p_code])

    return {
        "T": T,
        "flows": flows_list,
        "selected_ranked_state": selected_ranked_state,
        "auto_mode": auto_mode,
        "autofill_applied": autofill_applied,
        "min_conf_used": mcf,
        "ingest_profile": _ingest_prof,
    }
