from __future__ import annotations

from html import escape
from typing import Any
import re

import numpy as np

from report_visuals import build_potency_radar_svg


def _clean_exec_text(text: str) -> str:
    cleaned = " ".join(str(text or "").split())
    cleaned = re.sub(r"\((P\d{1,2})\)\s+\(\1\)", r"(\1)", cleaned)
    cleaned = re.sub(
        r"en ([A-ZÁÉÍÓÚÜÑa-záéíóúüñ\s\-]+\(P\d{1,2}\)) hasta que \1 absorba",
        r"en \1 hasta absorber",
        cleaned,
    )
    return cleaned


def _confidence_copy(raw: str) -> str:
    value = str(raw or "").strip().upper()
    if value == "LOW":
        return "LOW · caso híbrido, exige validación ejecutiva"
    if value == "HIGH":
        return "HIGH · lectura robusta"
    return "MEDIUM · lectura accionable"


def _format_score(value: float, *, denominator: int | None = None) -> str:
    numeric = float(value)
    rounded = round(numeric, 1)
    if abs(rounded - round(rounded)) < 1e-9:
        base = f"{int(round(rounded))}"
    else:
        base = f"{rounded:.1f}"
    if denominator is not None:
        return f"{base} / {denominator}"
    return base


def describe_integrity(value: float) -> tuple[str, str]:
    numeric = float(value)
    if numeric >= 70.0:
        return (_format_score(numeric, denominator=100), "Integridad sólida")
    if numeric >= 55.0:
        return (_format_score(numeric, denominator=100), "Integridad intermedia")
    return (_format_score(numeric, denominator=100), "Integridad frágil")


def describe_friction(value: float) -> tuple[str, str]:
    numeric = float(value)
    if numeric >= 7.0:
        return (_format_score(numeric, denominator=10), "Fricción alta")
    if numeric >= 4.5:
        return (_format_score(numeric, denominator=10), "Fricción activa")
    return (_format_score(numeric, denominator=10), "Fricción contenida")


def build_structural_heatmap_svg(summary_rows: list[dict[str, Any]], *, width: int = 900, row_height: int = 42) -> str:
    if not summary_rows:
        return ""

    cols = [
        ("Potencia", 160, 100.0),
        ("Fricción", 160, 10.0),
        ("Estructura", 150, 10.0),
        ("Autoridad", 150, 10.0),
    ]
    left_band = 240
    title_h = 34
    header_h = 78
    height = header_h + row_height * len(summary_rows) + 24
    total_metric_width = sum(col_width for _, col_width, _ in cols)
    total_width = left_band + total_metric_width + 24
    width = max(width, total_width)

    def color_for(col_name: str, value: float, max_value: float) -> str:
        ratio = 0.0 if max_value <= 0 else max(0.0, min(1.0, value / max_value))
        if col_name == "Fricción":
            if ratio >= 0.7:
                return "#d46a6a"
            if ratio >= 0.45:
                return "#d8b36a"
            if ratio >= 0.2:
                return "#7da6c7"
            return "#253342"
        if col_name == "Autoridad":
            if ratio >= 0.7:
                return "#d8b36a"
            if ratio >= 0.45:
                return "#7da6c7"
            if ratio >= 0.2:
                return "#d46a6a"
            return "#253342"
        if col_name == "Estructura":
            if ratio >= 0.7:
                return "#d8b36a"
            if ratio >= 0.45:
                return "#7da6c7"
            if ratio >= 0.2:
                return "#d46a6a"
            return "#253342"
        if ratio >= 0.7:
            return "#d8b36a"
        if ratio >= 0.45:
            return "#7da6c7"
        return "#253342"

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-label="Mapa estructural Noumenon V2">',
        '<rect width="100%" height="100%" fill="#0f151c"/>',
        f'<rect x="0" y="0" width="{width}" height="{header_h}" fill="#141d26"/>',
    ]

    parts.append(
        '<text x="18" y="24" fill="#e8eef2" font-size="16" font-family="Helvetica, Arial, sans-serif" font-weight="700">Mapa estructural de tensión y capacidad</text>'
    )
    parts.append(f'<line x1="18" y1="{title_h}" x2="{width - 18}" y2="{title_h}" stroke="#25313d" stroke-width="1"/>')
    parts.append(
        f'<text x="18" y="{title_h + 24}" fill="#7f909d" font-size="10" font-family="Helvetica, Arial, sans-serif" letter-spacing="0.10em">PODER</text>'
    )

    x_cursor = left_band
    for col_name, col_width, _ in cols:
        parts.append(
            f'<text x="{x_cursor + (col_width / 2):.1f}" y="{title_h + 24}" text-anchor="middle" fill="#9fb0bd" font-size="10.5" font-family="Helvetica, Arial, sans-serif" letter-spacing="0.06em">{escape(col_name.upper())}</text>'
        )
        x_cursor += col_width

    for idx, row in enumerate(summary_rows):
        y = header_h + idx * row_height
        band_fill = "#121a22" if idx % 2 == 0 else "#10161d"
        parts.append(f'<rect x="0" y="{y}" width="{width}" height="{row_height}" fill="{band_fill}"/>')
        parts.append(
            f'<text x="18" y="{y + 18}" fill="#e8eef2" font-size="13" font-family="Helvetica, Arial, sans-serif" font-weight="700">{escape(str(row["Poder"]))}</text>'
        )
        parts.append(
            f'<text x="18" y="{y + 33}" fill="#8fa0ae" font-size="12" font-family="Helvetica, Arial, sans-serif">{escape(str(row["Título"]))}</text>'
        )
        x_cursor = left_band
        for col_name, col_width, max_value in cols:
            value = float(row[col_name])
            fill = color_for(col_name, value, max_value)
            inner_w = max(16.0, (col_width - 26) * max(0.0, min(1.0, value / max_value if max_value else 0.0)))
            parts.append(
                f'<rect x="{x_cursor + 10}" y="{y + 9}" width="{col_width - 20}" height="24" rx="8" fill="#1a2430"/>'
            )
            parts.append(
                f'<rect x="{x_cursor + 10}" y="{y + 9}" width="{inner_w:.1f}" height="24" rx="8" fill="{fill}"/>'
            )
            parts.append(
                f'<text x="{x_cursor + col_width - 18}" y="{y + 26}" text-anchor="end" fill="#f4f7f9" font-size="12" font-family="Helvetica, Arial, sans-serif" font-weight="700">{value:.1f}</text>'
            )
            x_cursor += col_width

    parts.append("</svg>")
    return "\n".join(parts)


def build_power_tension_map_svg(summary_rows: list[dict[str, Any]], *, width: int = 980, height: int = 560) -> str:
    if not summary_rows:
        return ""

    chart_left = 92
    chart_top = 58
    chart_right = width - 36
    chart_bottom = height - 96
    chart_width = chart_right - chart_left
    chart_height = chart_bottom - chart_top
    max_friction_value = max(float(row["Fricción"]) for row in summary_rows)
    friction_cap = max(12.0, float(np.ceil((max_friction_value * 1.15) / 5.0) * 5.0))
    friction_threshold = 15.0 if friction_cap >= 20.0 else 5.0
    potency_threshold = 50.0

    def x_scale(value: float) -> float:
        return chart_left + (max(0.0, min(100.0, value)) / 100.0) * chart_width

    def y_scale(value: float) -> float:
        ratio = max(0.0, min(1.0, value / friction_cap if friction_cap else 0.0))
        return chart_bottom - ratio * chart_height

    def radius_for(structure_value: float) -> float:
        ratio = max(0.0, min(1.0, structure_value / 10.0))
        return 10.0 + ratio * 12.0

    def color_for(authority_value: float) -> str:
        if authority_value >= 7.0:
            return "#d8b36a"
        if authority_value >= 5.0:
            return "#7da6c7"
        return "#d46a6a"

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" aria-label="Mapa de desequilibrio estructural Noumenon V2">',
        '<rect width="100%" height="100%" fill="#0f151c"/>',
        f'<rect x="0" y="0" width="{width}" height="{height}" rx="22" fill="#0f151c"/>',
        f'<rect x="{chart_left}" y="{chart_top}" width="{chart_width}" height="{chart_height}" rx="18" fill="#121a22" stroke="#25313d" stroke-width="1"/>',
    ]

    x_threshold = x_scale(potency_threshold)
    y_threshold = y_scale(friction_threshold)

    parts.extend(
        [
            f'<rect x="{chart_left}" y="{chart_top}" width="{x_threshold - chart_left}" height="{y_threshold - chart_top}" fill="rgba(36,57,48,0.38)"/>',
            f'<rect x="{x_threshold}" y="{chart_top}" width="{chart_right - x_threshold}" height="{y_threshold - chart_top}" fill="rgba(92,54,54,0.34)"/>',
            f'<rect x="{chart_left}" y="{y_threshold}" width="{x_threshold - chart_left}" height="{chart_bottom - y_threshold}" fill="rgba(32,44,58,0.34)"/>',
            f'<rect x="{x_threshold}" y="{y_threshold}" width="{chart_right - x_threshold}" height="{chart_bottom - y_threshold}" fill="rgba(106,78,38,0.26)"/>',
            f'<line x1="{x_threshold}" y1="{chart_top}" x2="{x_threshold}" y2="{chart_bottom}" stroke="#445767" stroke-dasharray="6 6" stroke-width="1.5"/>',
            f'<line x1="{chart_left}" y1="{y_threshold}" x2="{chart_right}" y2="{y_threshold}" stroke="#445767" stroke-dasharray="6 6" stroke-width="1.5"/>',
        ]
    )

    for value in [0, 25, 50, 75, 100]:
        x = x_scale(float(value))
        parts.append(f'<line x1="{x}" y1="{chart_bottom}" x2="{x}" y2="{chart_bottom + 6}" stroke="#607281" stroke-width="1"/>')
        parts.append(
            f'<text x="{x}" y="{chart_bottom + 24}" text-anchor="middle" fill="#8fa0ae" font-size="11" font-family="Helvetica, Arial, sans-serif">{value}</text>'
        )

    y_ticks = np.linspace(0.0, friction_cap, 5)
    for value in y_ticks:
        y = y_scale(float(value))
        parts.append(f'<line x1="{chart_left - 6}" y1="{y}" x2="{chart_left}" y2="{y}" stroke="#607281" stroke-width="1"/>')
        parts.append(
            f'<text x="{chart_left - 12}" y="{y + 4}" text-anchor="end" fill="#8fa0ae" font-size="11" font-family="Helvetica, Arial, sans-serif">{value:.0f}</text>'
        )

    parts.extend(
        [
            f'<text x="{(chart_left + x_threshold) / 2:.1f}" y="{chart_top + 22}" text-anchor="middle" fill="#7f909d" font-size="10.5" font-family="Helvetica, Arial, sans-serif" letter-spacing="0.06em">FRENTE SECUNDARIO</text>',
            f'<text x="{(x_threshold + chart_right) / 2:.1f}" y="{chart_top + 22}" text-anchor="middle" fill="#d8b36a" font-size="10.5" font-family="Helvetica, Arial, sans-serif" letter-spacing="0.06em">CAPACIDAD BAJO TENSIÓN</text>',
            f'<text x="{(chart_left + x_threshold) / 2:.1f}" y="{chart_bottom - 10}" text-anchor="middle" fill="#8fa0ae" font-size="10.5" font-family="Helvetica, Arial, sans-serif" letter-spacing="0.06em">POTENCIA CONTENIDA</text>',
            f'<text x="{(x_threshold + chart_right) / 2:.1f}" y="{chart_bottom - 10}" text-anchor="middle" fill="#8fa0ae" font-size="10.5" font-family="Helvetica, Arial, sans-serif" letter-spacing="0.06em">PALANCA ESTRATÉGICA</text>',
            f'<text x="{chart_left + chart_width / 2:.1f}" y="{height - 28}" text-anchor="middle" fill="#9fb0bd" font-size="12" font-family="Helvetica, Arial, sans-serif" letter-spacing="0.05em">POTENCIA (0-100)</text>',
            f'<text x="28" y="{chart_top + chart_height / 2:.1f}" transform="rotate(-90 28 {chart_top + chart_height / 2:.1f})" text-anchor="middle" fill="#9fb0bd" font-size="12" font-family="Helvetica, Arial, sans-serif" letter-spacing="0.05em">FRICCIÓN POR NODO</text>',
        ]
    )

    label_rects: list[tuple[float, float, float, float]] = []
    preferred_positions = {
        "P1": [(16, 22), (14, -18), (-88, 18)],
        "P2": [(12, -24), (14, 24), (-108, -12)],
        "P3": [(18, -18), (16, 22), (-112, -6)],
        "P4": [(-112, 18), (-112, -8), (18, 24)],
        "P5": [(16, -16), (18, 22), (-124, -8)],
        "P6": [(14, 20), (18, -16), (-108, 22)],
        "P7": [(18, -14), (18, 22), (-108, -6)],
        "P8": [(18, -10), (18, 24), (-110, -8)],
        "P9": [(18, 20), (18, -18), (-126, 18)],
        "P10": [(16, -18), (18, 24), (-138, -10)],
    }

    def intersects(rect_a: tuple[float, float, float, float], rect_b: tuple[float, float, float, float]) -> bool:
        ax1, ay1, ax2, ay2 = rect_a
        bx1, by1, bx2, by2 = rect_b
        return not (ax2 < bx1 or bx2 < ax1 or ay2 < by1 or by2 < ay1)

    ordered_rows = sorted(summary_rows, key=lambda row: (-float(row["Fricción"]), -float(row["Potencia"]), str(row["Poder"])))

    for row in ordered_rows:
        potency = float(row["Potencia"])
        friction = float(row["Fricción"])
        structure = float(row["Estructura"])
        authority = float(row["Autoridad"])
        x = x_scale(potency)
        y = y_scale(friction)
        radius = radius_for(structure)
        fill = color_for(authority)
        show_full_label = authority >= 7.0 or authority < 5.0
        label_text = str(row["Título"]) if show_full_label else str(row["Poder"])
        label = escape(label_text)
        label_width = max(34.0, len(label_text) * 6.2)
        label_height = 14.0

        candidate_origins = []
        if show_full_label:
            for dx, dy in preferred_positions.get(str(row["Poder"]), []):
                if dx >= 0:
                    candidate_origins.append((x + radius + dx, y + dy))
                else:
                    candidate_origins.append((x + dx, y + dy))
            candidate_origins.extend(
                [
                    (x + radius + 10.0, y - radius - 4.0),
                    (x + radius + 10.0, y + radius + 14.0),
                    (x - radius - label_width - 10.0, y - radius - 4.0),
                    (x - radius - label_width - 10.0, y + radius + 14.0),
                    (x - (label_width / 2.0), y - radius - 12.0),
                    (x - (label_width / 2.0), y + radius + 18.0),
                ]
            )
        else:
            candidate_origins.extend(
                [
                    (x + radius + 8.0, y - radius - 2.0),
                    (x + radius + 8.0, y + radius + 12.0),
                    (x - radius - label_width - 8.0, y - radius - 2.0),
                    (x - radius - label_width - 8.0, y + radius + 12.0),
                ]
            )

        chosen_x = x + radius + 10.0
        chosen_y = y - radius - 4.0
        best_score: tuple[int, float] | None = None
        for cand_x, cand_y in candidate_origins:
            rect = (cand_x - 2.0, cand_y - label_height + 2.0, cand_x + label_width + 2.0, cand_y + 4.0)
            out_of_bounds = (
                rect[0] < chart_left + 6.0
                or rect[2] > chart_right - 6.0
                or rect[1] < chart_top + 26.0
                or rect[3] > chart_bottom - 6.0
            )
            overlaps = sum(1 for other in label_rects if intersects(rect, other))
            score = (1 if out_of_bounds else 0) + overlaps
            distance = abs(cand_x - x) + abs(cand_y - y)
            candidate_score = (score, distance)
            if best_score is None or candidate_score < best_score:
                best_score = candidate_score
                chosen_x = cand_x
                chosen_y = cand_y
                chosen_rect = rect

        parts.extend(
            [
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius:.1f}" fill="{fill}" fill-opacity="0.28" stroke="{fill}" stroke-width="2.2"/>',
                f'<text x="{x:.1f}" y="{y + 4:.1f}" text-anchor="middle" fill="#eef3f6" font-size="12" font-family="Helvetica, Arial, sans-serif" font-weight="700">{escape(str(row["Poder"]))}</text>',
            ]
        )
        if show_full_label:
            parts.extend(
                [
                    f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{chosen_x - 4:.1f}" y2="{chosen_y - 5:.1f}" stroke="#5d7182" stroke-width="1" opacity="0.7"/>',
                    f'<text x="{chosen_x:.1f}" y="{chosen_y:.1f}" fill="#d7e1e8" font-size="11.5" font-family="Helvetica, Arial, sans-serif">{label}</text>',
                ]
            )
        label_rects.append(chosen_rect)

    legend_y = 14
    legend_width = 420
    legend_x = width - legend_width - 22
    authority_label_x = legend_x + 16
    group_start_x = legend_x + 108
    group_gap = 74
    red_x = group_start_x
    blue_x = group_start_x + group_gap
    gold_x = group_start_x + (group_gap * 2)
    parts.extend(
        [
            f'<rect x="{legend_x}" y="{legend_y}" width="{legend_width}" height="32" rx="12" fill="#10161d" stroke="#25313d" stroke-width="1"/>',
            f'<text x="{authority_label_x}" y="{legend_y + 20}" fill="#9fb0bd" font-size="11.2" font-family="Helvetica, Arial, sans-serif">AUTORIDAD:</text>',
            f'<circle cx="{red_x}" cy="{legend_y + 16}" r="6.5" fill="#d46a6a" fill-opacity="0.28" stroke="#d46a6a" stroke-width="2"/>',
            f'<text x="{red_x + 13}" y="{legend_y + 20}" fill="#c9d5de" font-size="11.5" font-family="Helvetica, Arial, sans-serif">baja</text>',
            f'<circle cx="{blue_x}" cy="{legend_y + 16}" r="6.5" fill="#7da6c7" fill-opacity="0.28" stroke="#7da6c7" stroke-width="2"/>',
            f'<text x="{blue_x + 13}" y="{legend_y + 20}" fill="#c9d5de" font-size="11.5" font-family="Helvetica, Arial, sans-serif">media</text>',
            f'<circle cx="{gold_x}" cy="{legend_y + 16}" r="6.5" fill="#d8b36a" fill-opacity="0.28" stroke="#d8b36a" stroke-width="2"/>',
            f'<text x="{gold_x + 13}" y="{legend_y + 20}" fill="#c9d5de" font-size="11.5" font-family="Helvetica, Arial, sans-serif">alta</text>',
        ]
    )

    parts.append("</svg>")
    return "\n".join(parts)


def build_diagnosis_brief_html(
    *,
    integrity: float,
    friction: float,
    archetype_name: str,
    structural_state_name: str,
    archetype_hybrid: bool,
    top_risk: str,
    lever_label: str,
    lever_note: str,
    executive_view: dict[str, Any],
) -> str:
    integrity_display, integrity_copy = describe_integrity(integrity)
    friction_display, friction_copy = describe_friction(friction)
    situation = escape(str(executive_view.get("situation") or ""))
    decision = escape(str(executive_view.get("decision") or ""))
    action = escape(_clean_exec_text(str(executive_view.get("critical_action") or "")))
    risk = escape(str(executive_view.get("risk") or ""))
    confidence = escape(_confidence_copy(str(executive_view.get("decision_confidence") or "MEDIUM")))
    classification_copy = "Híbrida o fronteriza" if archetype_hybrid else "Principal"

    return f"""
    <div style="background:linear-gradient(135deg,#121a22 0%,#18232f 100%);border:1px solid #2a3947;border-radius:24px;padding:24px 26px;">
      <div style="display:flex;justify-content:space-between;gap:18px;align-items:flex-start;flex-wrap:wrap;">
        <div style="max-width:680px;">
          <div style="font-size:12px;letter-spacing:0.16em;text-transform:uppercase;color:#9fb0bd;margin-bottom:10px;">Executive Diagnosis</div>
          <div style="font-size:32px;line-height:1.05;font-weight:800;color:#edf3f7;">{escape(archetype_name)}</div>
          <div style="margin-top:8px;font-size:12px;letter-spacing:0.12em;text-transform:uppercase;color:#d8b36a;">Estado estructural · {escape(structural_state_name)}</div>
          <div style="margin-top:12px;font-size:15px;line-height:1.7;color:#c9d5de;">{situation}</div>
        </div>
        <div style="display:grid;grid-template-columns:repeat(2,minmax(130px,1fr));gap:10px;min-width:280px;">
          <div style="background:#0f151c;border:1px solid #2a3947;border-radius:18px;padding:14px;">
            <div style="font-size:11px;letter-spacing:0.1em;text-transform:uppercase;color:#8ea1af;">Integridad</div>
            <div style="font-size:28px;font-weight:800;color:#eef3f6;margin-top:6px;">{escape(integrity_display)}</div>
            <div style="margin-top:4px;font-size:11px;letter-spacing:0.04em;color:#8ea1af;">{escape(integrity_copy)}</div>
          </div>
          <div style="background:#0f151c;border:1px solid #2a3947;border-radius:18px;padding:14px;">
            <div style="font-size:11px;letter-spacing:0.1em;text-transform:uppercase;color:#8ea1af;">Fricción</div>
            <div style="font-size:28px;font-weight:800;color:#eef3f6;margin-top:6px;">{escape(friction_display)}</div>
            <div style="margin-top:4px;font-size:11px;letter-spacing:0.04em;color:#8ea1af;">{escape(friction_copy)}</div>
          </div>
          <div style="background:#0f151c;border:1px solid #2a3947;border-radius:18px;padding:14px;grid-column:span 2;">
            <div style="font-size:11px;letter-spacing:0.1em;text-transform:uppercase;color:#8ea1af;">Riesgo dominante</div>
            <div style="font-size:18px;font-weight:700;color:#d8b36a;margin-top:6px;">{escape(top_risk)}</div>
          </div>
        </div>
      </div>
      <div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-top:18px;">
        <div style="background:#0f151c;border:1px solid #2a3947;border-radius:18px;padding:16px;">
          <div style="font-size:11px;letter-spacing:0.1em;text-transform:uppercase;color:#8ea1af;">Arquetipo dominante</div>
          <div style="font-size:16px;line-height:1.5;color:#edf3f7;margin-top:8px;font-weight:700;">{escape(archetype_name)}</div>
        </div>
        <div style="background:#0f151c;border:1px solid #2a3947;border-radius:18px;padding:16px;">
          <div style="font-size:11px;letter-spacing:0.1em;text-transform:uppercase;color:#8ea1af;">Estado estructural</div>
          <div style="font-size:16px;line-height:1.5;color:#edf3f7;margin-top:8px;font-weight:700;">{escape(structural_state_name)}</div>
        </div>
        <div style="background:#0f151c;border:1px solid #2a3947;border-radius:18px;padding:16px;">
          <div style="font-size:11px;letter-spacing:0.1em;text-transform:uppercase;color:#8ea1af;">Riesgo dominante</div>
          <div style="font-size:16px;line-height:1.5;color:#d8b36a;margin-top:8px;font-weight:700;">{escape(top_risk)}</div>
        </div>
        <div style="background:#0f151c;border:1px solid #2a3947;border-radius:18px;padding:16px;">
          <div style="font-size:11px;letter-spacing:0.1em;text-transform:uppercase;color:#8ea1af;">Palanca prioritaria</div>
          <div style="font-size:16px;line-height:1.45;color:#edf3f7;margin-top:8px;font-weight:700;">{escape(lever_label)}</div>
          <div style="margin-top:8px;font-size:12px;line-height:1.55;color:#9fb0bd;">{escape(lever_note)}</div>
        </div>
      </div>
      <div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin-top:12px;">
        <div style="background:#0f151c;border:1px solid #2a3947;border-radius:18px;padding:16px;">
          <div style="font-size:11px;letter-spacing:0.1em;text-transform:uppercase;color:#8ea1af;">Decisión</div>
          <div style="font-size:15px;line-height:1.6;color:#edf3f7;margin-top:8px;">{decision}</div>
        </div>
        <div style="background:#0f151c;border:1px solid #2a3947;border-radius:18px;padding:16px;">
          <div style="font-size:11px;letter-spacing:0.1em;text-transform:uppercase;color:#8ea1af;">Acción crítica</div>
          <div style="font-size:15px;line-height:1.6;color:#edf3f7;margin-top:8px;">{action}</div>
        </div>
        <div style="background:#0f151c;border:1px solid #2a3947;border-radius:18px;padding:16px;">
          <div style="font-size:11px;letter-spacing:0.1em;text-transform:uppercase;color:#8ea1af;">Riesgo de no actuar</div>
          <div style="font-size:15px;line-height:1.6;color:#edf3f7;margin-top:8px;">{risk}</div>
        </div>
      </div>
      <div style="margin-top:14px;font-size:12px;color:#9fb0bd;letter-spacing:0.04em;">Confianza de lectura: {confidence} · Clasificación: {escape(classification_copy)}</div>
      <div style="margin-top:4px;font-size:11px;color:#7f909d;line-height:1.5;">Robustez de la hipótesis con la evidencia y calibración actualmente cargadas.</div>
    </div>
    """


def build_radar_svg_from_core(core: dict[str, Any]) -> str:
    return build_radar_svg_from_core_with_size(core, size=430.0)


def build_radar_svg_from_core_with_size(core: dict[str, Any], *, size: float) -> str:
    report = core["report"]
    sim_report = core.get("sim_report")
    benchmark_df = core.get("benchmark_df")
    potency_current = report["potency100"]
    potency_simulated = sim_report["potency100"] if isinstance(sim_report, dict) else None
    potency_benchmark = benchmark_df["Benchmark"].tolist() if benchmark_df is not None and "Benchmark" in benchmark_df.columns else None
    return build_potency_radar_svg(
        potency_current=potency_current,
        potency_simulated=potency_simulated,
        potency_benchmark=potency_benchmark,
        size=size,
        label_prefix="Potencia estructural Noumenon V2",
    )
