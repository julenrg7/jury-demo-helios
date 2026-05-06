"""
Gráficos ligeros para informes HTML/PDF (sin matplotlib).
Estética alineada con briefings Akxom (dark / oro / acento rojo).
"""

from __future__ import annotations

import html
import math
from typing import Sequence

import numpy as np

from engine_akxom import PODERES_INFO
from ui_tokens import DECISION_GOLD, STRUCT_MID_BLUE, CLASSIFICATION_RED

AKX_GOLD = DECISION_GOLD
AKX_RISK = CLASSIFICATION_RED
AKX_GRID = STRUCT_MID_BLUE
AKX_BG = "#050505"
AKX_MUTED = "#7F8C8D"


def _scale_potency(p: Sequence[float]) -> np.ndarray:
    a = np.asarray(p, dtype=float).ravel()
    return np.clip(a / 10.0, 0.0, 10.0)


def build_potency_radar_svg(
    potency_current: Sequence[float],
    potency_simulated: Sequence[float] | None = None,
    potency_benchmark: Sequence[float] | None = None,
    *,
    size: float = 460.0,
    label_prefix: str = "Potencia relativa (0–10)",
) -> str:
    """
    Radar polar: 10 ejes (P1–P10). Valores motor en 0–100 → escala 0–10.
    Opcional: contorno simulado (trazo discontinuo, color riesgo) y/o perfil benchmark (trazo discontinuo).
    """
    v_cur = _scale_potency(potency_current)
    n = int(v_cur.size)
    if n < 3:
        return ""

    v_sim = None
    if potency_simulated is not None:
        v_sim = _scale_potency(potency_simulated)
        if v_sim.size != n:
            v_sim = None

    v_bench = None
    if potency_benchmark is not None:
        v_bench = _scale_potency(potency_benchmark)
        if v_bench.size != n:
            v_bench = None

    cx = size / 2.0
    cy = size / 2.0 - 26.0
    # Más margen para etiquetas largas (TÍTULO + código) sin cortes.
    r_max = size / 2.0 - 108.0

    def vertex(angle: float, radius: float) -> tuple[float, float]:
        return cx + radius * math.cos(angle), cy + radius * math.sin(angle)

    # Empieza arriba (-90°) y avanza en sentido horario (como matplotlib polar típico)
    def poly_points(vals: np.ndarray) -> list[tuple[float, float]]:
        pts: list[tuple[float, float]] = []
        for i in range(n):
            ang = -math.pi / 2.0 + 2.0 * math.pi * (i / n)
            r = r_max * (float(vals[i]) / 10.0)
            pts.append(vertex(ang, r))
        return pts

    cur_pts = poly_points(v_cur)
    d_cur = "M " + " L ".join(f"{x:.2f},{y:.2f}" for x, y in cur_pts) + " Z"

    d_sim = ""
    if v_sim is not None:
        sim_pts = poly_points(v_sim)
        d_sim = "M " + " L ".join(f"{x:.2f},{y:.2f}" for x, y in sim_pts) + " Z"

    d_bench = ""
    if v_bench is not None:
        bench_pts = poly_points(v_bench)
        d_bench = "M " + " L ".join(f"{x:.2f},{y:.2f}" for x, y in bench_pts) + " Z"

    parts: list[str] = []
    safe_lbl = html.escape(label_prefix, quote=True)
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" class="fig-svg" viewBox="0 0 {size} {size}" role="img" aria-label="{safe_lbl}">'
    )
    parts.append(f'<rect width="100%" height="100%" fill="{AKX_BG}"/>')

    # Anillos 3 / 6 / 9
    for ring in (0.3, 0.6, 0.9):
        rr = r_max * ring
        parts.append(
            f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{rr:.2f}" fill="none" stroke="{AKX_GRID}" stroke-width="1.2" opacity="0.65"/>'
        )

    # Ejes
    for i in range(n):
        ang = -math.pi / 2.0 + 2.0 * math.pi * (i / n)
        x2, y2 = vertex(ang, r_max)
        parts.append(
            f'<line x1="{cx:.2f}" y1="{cy:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="{AKX_GRID}" stroke-width="1" opacity="0.55"/>'
        )

    # Etiquetas en el perímetro: TÍTULO y código (P#) en dos líneas.
    power_labels: list[tuple[str, str]] = []
    for i in range(n):
        if i < len(PODERES_INFO):
            p_code, p_title, _, _ = PODERES_INFO[i]
            power_labels.append((str(p_title or p_code).upper(), str(p_code)))
        else:
            power_labels.append((f"P{i + 1}", f"P{i + 1}"))

    for i in range(n):
        ang = -math.pi / 2.0 + 2.0 * math.pi * (i / n)
        lx, ly = vertex(ang, r_max + 38.0)
        c = math.cos(ang)
        if c > 0.25:
            anchor = "start"
            lx += 6.0
        elif c < -0.25:
            anchor = "end"
            lx -= 6.0
        else:
            anchor = "middle"
        title, code = power_labels[i]
        safe_title = html.escape(title, quote=True)
        safe_code = html.escape(code, quote=True)
        parts.append(
            f'<text x="{lx:.2f}" y="{ly:.2f}" text-anchor="{anchor}" dominant-baseline="middle" '
            f'fill="{AKX_GOLD}" font-family="Courier New, Courier, monospace" font-weight="700">'
            f'<tspan x="{lx:.2f}" dy="-4.2" font-size="6.6">{safe_title}</tspan>'
            f'<tspan x="{lx:.2f}" dy="8.4" font-size="6.4">({safe_code})</tspan>'
            "</text>"
        )

    # Anillo de lectura de nivel (capacidad/potencia): bajo → medio → alto.
    r_labels = [("BAJO", 3), ("MEDIO", 6), ("ALTO", 9)]
    la = math.radians(48)
    for lab, rv in r_labels:
        rx, ry = vertex(la, r_max * (rv / 10.0) * 0.92)
        parts.append(
            f'<text x="{rx:.2f}" y="{ry:.2f}" text-anchor="middle" dominant-baseline="middle" fill="#E0E0E0" font-size="7.5" font-family="Helvetica, Arial, sans-serif" font-weight="700">{lab}</text>'
        )

    # Benchmark debajo del trazo principal (Actual vs estándar).
    if d_bench:
        parts.append(
            f'<path d="{d_bench}" fill="none" stroke="#B8A878" stroke-width="2.0" stroke-dasharray="6 4" opacity="0.9"/>'
        )

    if d_sim:
        parts.append(
            f'<path d="{d_sim}" fill="none" stroke="{AKX_RISK}" stroke-width="2.4" stroke-dasharray="7 5" opacity="0.95"/>'
        )

    parts.append(
        f'<path d="{d_cur}" fill="{AKX_GOLD}" fill-opacity="0.22" stroke="{AKX_GOLD}" stroke-width="2.2"/>'
    )

    parts.append(
        f'<text x="{cx:.2f}" y="{cy:.2f}" text-anchor="middle" dominant-baseline="middle" fill="{AKX_MUTED}" font-size="8" font-family="Courier New, Courier, monospace">TENSOR</text>'
    )

    parts.append("</svg>")
    return "\n".join(parts)
