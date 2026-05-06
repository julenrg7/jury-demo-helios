"""
Tres escenarios de decisión (presentación): acción prioritaria, alternativa del barrido, trayectoria sin actuar.

No modifica el motor; reusa ranked_meta de simulate_intervention_outcome y future_scenario del core.
"""

from __future__ import annotations

import html
from typing import Any

import numpy as np

from simulation import build_action_display_label


def _fmt_delta_line(delta_integrity: float, delta_friction: float) -> str:
    return f"{float(delta_integrity):+.1f} integridad · {float(delta_friction):+.1f} fricción"


def build_decision_scenarios(core: dict[str, Any]) -> dict[str, Any]:
    fr = core.get("final_reco") or {}
    io = core.get("intervention_outcome") or {}
    ev = core.get("executive_view") or {}
    ranked = list(io.get("ranked_meta") or [])
    act_lab = str(io.get("action_label") or "")
    preserve = bool(ev.get("preserve_mode")) or act_lab in (
        "Sin intervención necesaria",
        "Sin intervención recomendada",
    )

    if preserve:
        s1: dict[str, Any] = {
            "id": "primary",
            "title": "1. Acción crítica",
            "line": "—",
            "inactive": True,
            "note": "Sin intervención prioritaria en este ciclo.",
        }
    else:
        di1 = float(fr.get("delta_integrity") or 0.0)
        df1 = float(fr.get("delta_friction") or 0.0)
        s1 = {
            "id": "primary",
            "title": "1. Ejecutar acción crítica",
            "line": _fmt_delta_line(di1, df1),
            "inactive": False,
            "note": build_action_display_label(fr.get("action_label"), fr.get("acted_power")),
        }

    plan = core.get("action_plan") or {}
    support = plan.get("actions") or []
    support_hint = ""
    if support and str(support[0] or "").strip():
        t = str(support[0]).strip()
        support_hint = t if len(t) <= 200 else (t[:197] + "…")

    if (not preserve) and len(ranked) >= 2:
        alt = ranked[1]
        di2 = float(alt.get("delta_integrity") or 0.0)
        df2 = float(alt.get("delta_friction") or 0.0)
        alt_note = build_action_display_label(alt.get("label"), alt.get("acted_power"))
        if support_hint:
            alt_note = f"{alt_note} · Referencia plan: {support_hint}"
        s2: dict[str, Any] = {
            "id": "alt",
            "title": "2. Alternativa (2.ª opción del barrido)",
            "line": _fmt_delta_line(di2, df2),
            "inactive": False,
            "note": alt_note,
        }
    else:
        s2 = {
            "id": "alt",
            "title": "2. Alternativa",
            "line": "—",
            "inactive": True,
            "note": "No aplica en este ciclo (sin segunda variante en el barrido)."
            if preserve
            else "Menos de dos candidatos en el barrido numérico.",
        }

    report = core.get("report") or {}
    fut = core.get("future_scenario") or {}
    potency = np.asarray(report.get("potency100"), dtype=float)
    leak = np.asarray(report.get("leakscore"), dtype=float)
    fut_p_raw = fut.get("future_potency")

    if potency.size != 10 or fut_p_raw is None:
        s3 = {
            "id": "drift",
            "title": "3. No actuar",
            "line": "—",
            "inactive": True,
            "note": "Sin proyección de trayectoria disponible.",
        }
    else:
        fut_p = np.asarray(fut_p_raw, dtype=float)
        fut_l = np.asarray(fut.get("future_friction", leak), dtype=float)
        if fut_l.shape != leak.shape:
            fut_l = leak
        d_pot = float(np.mean(fut_p) - np.mean(potency))
        d_leak = float(np.mean(fut_l) - np.mean(leak))
        pot_bridge = 0.21
        di3 = d_pot * pot_bridge
        df3 = d_leak * 10.0
        s3 = {
            "id": "drift",
            "title": "3. No actuar (trayectoria tensada)",
            "line": _fmt_delta_line(di3, df3),
            "inactive": False,
            "note": (
                f"Ilustrativo — mismo modelo que la proyección por poderes (flujos y tensiones). "
                f"Puente integridad ≈ {pot_bridge:.2f}×Δ potencia media; Δ fricción = Δ fuga media×10."
            ),
        }

    return {"schema_version": 1, "scenarios": [s1, s2, s3]}


def merge_scenarios_executive_plain_text(
    executive_view: dict[str, Any] | None,
    decision_scenarios: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Añade ESCENARIOS al plain_text de la vista ejecutiva (export / paridad)."""
    if not executive_view or not decision_scenarios:
        return executive_view
    scen = decision_scenarios.get("scenarios") or []
    if not scen:
        return executive_view
    lines = ["", "ESCENARIOS", ""]
    for sc in scen:
        lines.append(str(sc.get("title") or ""))
        lines.append(str(sc.get("line") or ""))
        if str(sc.get("note") or "").strip():
            lines.append(str(sc.get("note") or ""))
        lines.append("")
    out = dict(executive_view)
    base = str(out.get("plain_text") or "").rstrip()
    out["plain_text"] = base + "\n" + "\n".join(lines).rstrip()
    return out


def scenarios_streamlit_inner_html(
    ds: dict[str, Any] | None,
    *,
    gold_hex: str,
    label_muted_hex: str,
    line_mono_hex: str,
    safe_html: Any,
) -> str:
    if not ds or not isinstance(ds, dict):
        return ""
    items = ds.get("scenarios") or []
    if not items:
        return ""
    rows: list[str] = [
        f"<p style='font-size:10px;font-weight:800;color:{gold_hex};letter-spacing:0.14em;"
        f"text-transform:uppercase;margin:14px 0 10px 0;padding-top:12px;border-top:1px solid rgba(212,175,55,0.25);'>Escenarios</p>",
        f"<p style='font-size:11px;color:{label_muted_hex};margin:0 0 12px 0;line-height:1.45;'>"
        f"Tres lecturas para decidir; números alineados con la simulación prioritaria y la trayectoria modelada.</p>",
    ]
    for sc in items:
        title = safe_html(str(sc.get("title") or ""))
        line = safe_html(str(sc.get("line") or ""))
        note = safe_html(str(sc.get("note") or ""))
        opacity = "0.85" if sc.get("inactive") else "1"
        rows.append(
            f"<div style='margin:0 0 10px 0;opacity:{opacity};'>"
            f"<p style='font-size:12px;font-weight:700;color:#e5e7eb;margin:0 0 4px 0;'>{title}</p>"
            f"<p style='font-size:15px;font-weight:700;font-family:ui-monospace,\"Courier New\",monospace;"
            f"color:{line_mono_hex};margin:0 0 4px 0;'>{line}</p>"
            f"<p style='font-size:11px;color:{label_muted_hex};line-height:1.45;margin:0;'>{note}</p>"
            f"</div>"
        )
    return "\n".join(rows)


def scenarios_pdf_html(
    ds: dict[str, Any] | None,
    *,
    gold: str,
    muted: str,
    mono: str,
    embedded: bool = False,
) -> str:
    if not ds or not isinstance(ds, dict):
        return ""
    items = ds.get("scenarios") or []
    if not items:
        return ""
    wrap_open = (
        '<div style="margin:10px 0 12px 0;padding-top:10px;border-top:1px solid rgba(212,175,55,0.35);">'
        if not embedded
        else '<div style="margin:8px 0 10px 0;">'
    )
    parts: list[str] = [
        wrap_open,
        f'<p style="margin:0 0 8px 0;font-size:10px;font-weight:800;letter-spacing:0.18em;text-transform:uppercase;color:{gold};">Escenarios</p>',
        f'<p style="margin:0 0 12px 0;font-size:10px;line-height:1.45;color:{muted};">'
        f"Tres lecturas para decidir; la alternativa es la 2.ª opción del mismo barrido numérico.</p>",
    ]
    for sc in items:
        t = html.escape(str(sc.get("title") or ""))
        ln = html.escape(str(sc.get("line") or ""))
        note = html.escape(str(sc.get("note") or ""))
        op = "0.88" if sc.get("inactive") else "1"
        parts.append(
            f'<div style="margin:0 0 10px 0;opacity:{op};">'
            f'<p style="margin:0 0 4px 0;font-size:11px;font-weight:700;color:#E5E7EB;">{t}</p>'
            f'<p style="margin:0 0 4px 0;font-size:13px;font-weight:700;font-family:Courier New,monospace;color:{mono};">{ln}</p>'
            f'<p style="margin:0;font-size:9px;line-height:1.45;color:{muted};">{note}</p>'
            f"</div>"
        )
    parts.append("</div>")
    return "".join(parts)
