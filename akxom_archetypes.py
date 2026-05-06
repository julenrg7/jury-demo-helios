"""
Clasificación arquetípica de arquitecturas de poder (AKXOM Unit).

1) Reglas duras (orden): **Organismo de Asalto** → **Fortaleza Sitiada (tensor core)** → **Leviatán Ciego duro** → **Arquitectura Soberana** → halo/Fantasma;
   halo P10 vs colapso M3
   → Fantasma solo si no aplica **firma Leviatán** (P5/P8/P10) ni P5≥70 legacy; P10 potency ≥ 40; **veto hardware basal** (media M1 en P1/P6/P9 <3.5)
   → Zombi o Fantasma (mismo gate P10); núcleo M3<4 en P1/P6/P9 → Zombi o Fantasma; cascade narrativo;
   tensor degenerado → Gigante; **Gigante tensor** (P6↑, P7↓) antes de Nokia→Zombi. En `identify_archetype`, asalto → override duro sin softmax.
2) Soberana (soft/eligible): integridad >60 %, fricción <4, sin veto M1 núcleo; gate M3 en P1/P6/P9. Fortaleza Sitiada (tensor core): min(P5,P9) por encima de max(P3,P4) con brecha, sin fricción/leak/flows.
3) Distancia euclídea con penalizaciones si no hay regla dura (Soberana/Fortaleza castigadas si hardware débil).

Confianza vía softmax sobre -d² combinada con evidencia media. El arquetipo «legacy» del motor
(detect_structural_archetype) permanece para narrativa interna; este módulo alimenta el Protocolo Oracular.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np

# Índices fijos en ARCHETYPES (orden de definición)
_IDX_SOBERANA = 0
_IDX_VANGUARDIA = 1
_IDX_GIGANTE = 2
_IDX_ZOMBI = 3
_IDX_LEVIATAN = 4
_IDX_FOSIL = 5
_IDX_FEUDO = 6
_IDX_ORGANISMO = 7
_IDX_FORTALEZA = 8
_IDX_FANTASMA = 9

FEATURE_DIM = 42
# 0–1: integridad ejecutiva, fricción global
# 2–11: potencia Pi (P1..P10) / 100
# 12–21: leak Pi / 10
# 22–31: M3 medio por poder / 10
# 32–41: flow por poder → (flow/3 + 1) / 2  (0 flow → 0.5)


def _clip01(x: float) -> float:
    return float(np.clip(x, 0.0, 1.0))


def _potency_p10_allows_fantasma(report: dict[str, Any]) -> bool:
    """Resonancia Fantasma exige eco en P10: ≥4 en escala 0–10 → potency100 ≥ 40."""
    p = np.asarray(report.get("potency100"), dtype=float).ravel()
    return p.size > 9 and float(p[9]) >= 40.0


def leviatan_ciego_tensor_anti_fantasma(report: dict[str, Any]) -> bool:
    """
    Firma amplia: institución vs maniobra + cultura — **no** «eco vacío» Fantasma.
    Usada para vetar halo/resonancia/máscara softmax; exige P5 > P8 para no activar en tensor plano.
    """
    p = np.asarray(report.get("potency100"), dtype=float).ravel()
    if p.size < 10:
        return False
    p5, p8, p10 = float(p[4]), float(p[7]), float(p[9])
    return (
        p5 >= 52.0
        and p8 <= 52.0
        and p10 >= 38.0
        and p5 >= p8 + 5.0
    )


def leviatan_ciego_tensor_core(report: dict[str, Any]) -> bool:
    """
    Firma **estricta** para prioridad fija (antes de halo): no pisar Fortaleza / Fósil / casos P8 medio-alto.
    """
    p = np.asarray(report.get("potency100"), dtype=float).ravel()
    if p.size < 10:
        return False
    p5, p8, p10 = float(p[4]), float(p[7]), float(p[9])
    return (
        p5 >= 58.0
        and p8 <= 45.0
        and p10 >= 38.0
        and p5 >= p8 + 8.0
    )


def _debug_archetype(msg: str) -> None:
    """Activa con NOUMENON_DEBUG_ARCHETYPE=1 (temporal / diagnóstico)."""
    if os.environ.get("NOUMENON_DEBUG_ARCHETYPE", "").strip().lower() in ("1", "true", "yes"):
        print(f"[akxom_archetypes] {msg}", flush=True)


def _fantasma_excluded_by_strong_p5(report: dict[str, Any]) -> bool:
    """P5 muy alto (legacy): institución fuerte sin firma Leviatán explícita → no Fantasma."""
    p = np.asarray(report.get("potency100"), dtype=float).ravel()
    return p.size > 4 and float(p[4]) >= 70.0


def _fantasma_blocked_by_institution(report: dict[str, Any]) -> bool:
    """
    Bloquea Resonancia Fantasma si hay cuerpo institucional/normativo (Leviatán) o P5 extremo.
    Usa firma **anti-Fantasma** (más amplia) además del legacy P5≥70.
    """
    if leviatan_ciego_tensor_anti_fantasma(report):
        return True
    return _fantasma_excluded_by_strong_p5(report)


def _mask_fantasma_distance(d_arr: np.ndarray, report: dict[str, Any]) -> np.ndarray:
    """Excluye Fantasma del argmin si P10 bajo o firma Leviatán / institución fuerte."""
    out = np.asarray(d_arr, dtype=float, copy=True)
    if not _potency_p10_allows_fantasma(report):
        out[_IDX_FANTASMA] = 1e9
    if leviatan_ciego_tensor_anti_fantasma(report):
        out[_IDX_FANTASMA] = 1e9
    return out


def build_archetype_feature_vector(
    report: dict[str, Any],
    *,
    executive_integrity: float,
    friction: float,
    flows: Sequence[float] | None = None,
) -> np.ndarray:
    """Vector [0,1] comparable con perfiles ideales."""
    p = np.asarray(report["potency100"], dtype=float).ravel()
    lk = np.asarray(report["leakscore"], dtype=float).ravel()
    m3 = np.asarray(report["avgm3"], dtype=float).ravel()
    if p.size < 10 or lk.size < 10 or m3.size < 10:
        raise ValueError("report incompleto para arquetipo")

    v = np.zeros(FEATURE_DIM, dtype=float)
    v[0] = _clip01(float(executive_integrity) / 100.0)
    v[1] = _clip01(float(friction) / 10.0)
    v[2:12] = np.clip(p, 0.0, 100.0) / 100.0
    v[12:22] = np.clip(lk, 0.0, 10.0) / 10.0
    v[22:32] = np.clip(m3, 0.0, 10.0) / 10.0

    fl = np.zeros(10, dtype=float)
    if flows is not None and len(flows) >= 10:
        for i in range(10):
            fl[i] = float(flows[i])
    v[32:42] = np.clip((fl / 3.0 + 1.0) / 2.0, 0.0, 1.0)
    return v


@dataclass(frozen=True)
class UniversalArchetype:
    id: str
    name: str
    description: str
    ideal: np.ndarray


def nokia_zombi_destino_pattern(
    report: dict[str, Any],
    flows: Sequence[float] | None,
    contradictions: list[dict[str, Any]] | None,
) -> bool:
    """
    Patrón tipo Nokia / Zombi estratégico: nodo capital (P6) con peso y fuga, mientras el **futuro**
    (P8 y/o P9) muestra desgaste en flujo o fuga acumulada — **no** exigir P8 y P9 negativos a la vez:
    basta con uno (p. ej. P9 en deterioro y P8 en 0: narrativa estratégica quieta pero tesis tecnológica en fuga).

    Distingue de Feudo (centralidad carismática P2): aquí el drama es **destino vs caja**, no vínculo P2/P5.
    """
    p = np.asarray(report["potency100"], dtype=float).ravel()
    lk = np.asarray(report["leakscore"], dtype=float).ravel()
    if p.size < 10 or lk.size < 10:
        return False
    if flows is None or len(flows) < 10:
        return False
    f = np.asarray(flows, dtype=float)
    p6 = float(p[5])
    lk6 = float(lk[5])
    if p6 < 50.0:
        return False

    f8, f9 = float(f[7]), float(f[8])
    # Al menos un eje P8 o P9 en tendencia negativa (no ambos obligatorios).
    if f8 >= -0.04 and f9 >= -0.04:
        return False

    p8, p9 = float(p[7]), float(p[8])
    # Potencias altas en P8/P9 con fuga concentrada = fuerza aparente / vacío operativo (Nokia).
    leak_future_nodes = float(lk[7]) + float(lk[8]) > 0.62
    weak_future_vs_capital = (p8 + p9) < 1.22 * p6
    capital_bleeding = lk6 >= 1.05

    contra_p8p9 = False
    contra_p6 = False
    if contradictions:
        for it in contradictions:
            pc = str(it.get("poder", ""))
            if pc in ("P8", "P9"):
                contra_p8p9 = True
            if pc == "P6":
                contra_p6 = True

    top_labs = report.get("top3_risks_labels") or []
    p6_among_top = any("P6" in str(lab) for lab in top_labs[:3])

    return bool(
        leak_future_nodes
        or weak_future_vs_capital
        or capital_bleeding
        or contra_p8p9
        or contra_p6
        or p6_among_top
    )


def _flows_ok(flows: Sequence[float] | None) -> np.ndarray:
    if flows is None or len(flows) < 10:
        return np.zeros(10, dtype=float)
    return np.asarray([float(flows[i]) for i in range(10)], dtype=float)


def _potency_signal(p: np.ndarray) -> float:
    return float(np.max(p)) if p.size else 0.0


def hardware_basal_veto_active(report: dict[str, Any]) -> bool:
    """
    Veto de hardware basal: media M1 en P1, P6, P9 por debajo del umbral (coherente con engine/analysis).
    Si no viene precalculado en el reporte, se infiere desde avgm1.
    """
    hb = report.get("hardware_basal_veto")
    if isinstance(hb, dict) and "active" in hb:
        return bool(hb.get("active"))
    avgm1 = report.get("avgm1")
    if avgm1 is None:
        return False
    arr = np.asarray(avgm1, dtype=float).ravel()
    if arr.size < 10:
        return False
    return float((arr[0] + arr[5] + arr[8]) / 3.0) < 3.5


def positive_archetype_body_gate(report: dict[str, Any]) -> bool:
    """
    Arquetipos de «dominio» (Soberana, Fortaleza) exigen núcleo biológico/económico/tecnológico (P1, P6, P9)
    por encima de vulnerabilidad estructural (M3 < 4) y con media mínima > 5 en escala 0–10.
    """
    m3 = np.asarray(report.get("avgm3"), dtype=float).ravel()
    if m3.size < 10:
        return True
    core = np.array([float(m3[0]), float(m3[5]), float(m3[8])], dtype=float)
    if np.any(core < 4.0):
        return False
    if float(np.mean(core)) <= 5.0:
        return False
    return True


def halo_vacuum_fantasma_pattern(report: dict[str, Any]) -> bool:
    """
    Máxima prioridad: halo P10 (M3 cultural > 7) con colapso del resto (media M3 P1–P9 < 4).
    Contrarresta el efecto de prestigio que oculta vaciamiento operativo.
    """
    if _fantasma_blocked_by_institution(report):
        return False
    m3 = np.asarray(report.get("avgm3"), dtype=float).ravel()
    if m3.size < 10:
        return False
    if float(m3[9]) <= 7.0:
        return False
    return float(np.mean(m3[:9])) < 4.0


def resonancia_fantasma_pattern(
    report: dict[str, Any],
    flows: Sequence[float] | None,
    contradictions: list[dict[str, Any]] | None,
) -> bool:
    """
    Marca vacía: P10 domina el tensor y el resto está en degradación; núcleo económico/tecnológico
    en estrés. Excluye Zombi (capital aún «camina» con P6 fuerte + patrón Nokia).

    No aplica si P10 (potency100) no alcanza umbral de «eco cultural» fuerte: por debajo de ~40/100
    (equivalente a <4 en escala 0–10) el patrón de Fantasma sería falso positivo frente a asalto/extracción.
    """
    p = np.asarray(report["potency100"], dtype=float).ravel()
    lk = np.asarray(report["leakscore"], dtype=float).ravel()
    if p.size < 10 or lk.size < 10:
        return False
    if _fantasma_blocked_by_institution(report):
        return False
    if float(p[9]) < 40.0:
        return False
    if _potency_signal(p) < 14.0:
        return False
    if nokia_zombi_destino_pattern(report, flows, contradictions) and float(p[5]) >= 52.5:
        return False

    p10 = float(p[9])
    rest = p[:9]
    med = float(np.median(rest))
    mean_rest = float(np.mean(rest))
    if p10 < med + 5.5:
        return False
    if mean_rest > 59.0:
        return False

    order = np.argsort(-p)
    if int(order[0]) != 9 and int(order[1]) != 9:
        return False

    fl = _flows_ok(flows)
    p6, p9 = float(p[5]), float(p[8])
    econ_stress = p6 < 57.0 or float(lk[5]) >= 0.62 or float(fl[5]) < -0.18
    tech_stress = p9 < 55.0 or float(lk[8]) >= 0.55 or float(fl[8]) < -0.18
    if not (econ_stress and tech_stress):
        return False

    if p6 >= 59.0 and p9 >= 56.0:
        return False

    return True


def leviatan_ciego_pattern(
    report: dict[str, Any],
    flows: Sequence[float] | None,
) -> bool:
    """P5 institucional fuerte en forma; P8 estratégico débil o en fuga."""
    p = np.asarray(report["potency100"], dtype=float).ravel()
    m3 = np.asarray(report["avgm3"], dtype=float).ravel()
    lk = np.asarray(report["leakscore"], dtype=float).ravel()
    if p.size < 10:
        return False
    fl = _flows_ok(flows)
    if float(m3[4]) < 6.5:
        return False
    if float(p[4]) < 54.0:
        return False
    if float(p[7]) > 50.0 and float(lk[7]) < 0.28:
        return False
    return float(p[7]) <= 48.0 or float(lk[7]) >= 0.32 or float(fl[7]) < -0.12


def fortaleza_sitiada_tensor_core(report: dict[str, Any]) -> bool:
    """
    Ontología AKXOM: núcleo institucional + tecnológico (P5, P9) por encima del perímetro comunicativo
    y social (P3, P4) — aislamiento estructural, no «colapso plano» (Gigante).

    No usa fricción ni integridad global (evita confundir con Gigante/Zombi por severidad ejecutiva).

    Calibración: umbrales absolutos 60/60 en potency100 excluían casos reales (~5.5 y ~4.5 en 0–10 → ~54/44).
    Se exige además brecha mínima min(P5,P9) ≥ max(P3,P4)+8 para fijar la lectura «fuerte dentro / débil fuera».
    """
    if organismo_asalto_pattern(report):
        return False
    p = np.asarray(report.get("potency100"), dtype=float).ravel()
    if p.size < 10:
        return False
    p3, p4 = float(p[2]), float(p[3])
    p5, p9 = float(p[4]), float(p[8])
    if p3 > 42.0 or p4 > 42.0:
        return False
    inner = min(p5, p9)
    outer = max(p3, p4)
    if inner < outer + 8.0:
        return False
    if p5 < 48.0 or p9 < 42.0:
        return False
    return True


def fortaleza_zombi_frontier_signal(
    report: dict[str, Any],
    flows: Sequence[float] | None = None,
) -> bool:
    """
    Señal de frontera entre Fortaleza Sitiada y Zombi Estratégico.

    Fortaleza: cuerpo interno suficiente y perímetro degradado.
    Zombi: además del perímetro, aparece desgaste en lectura de futuro.

    Esta señal no decide el arquetipo ganador; solo sirve para fijar el vecino correcto
    cuando la frontera doctrinal está activa.
    """
    p = np.asarray(report.get("potency100"), dtype=float).ravel()
    lk = np.asarray(report.get("leakscore"), dtype=float).ravel()
    if p.size < 10 or lk.size < 10:
        return False
    fl = _flows_ok(flows)
    p3, p4 = float(p[2]), float(p[3])
    p5, p8, p9 = float(p[4]), float(p[7]), float(p[8])
    inner_ok = p5 >= 48.0 and p9 >= 40.0
    perimeter_broken = p3 <= 42.0 and p4 <= 42.0
    future_stressed = p8 <= 46.0 or float(lk[7]) >= 0.55 or float(lk[8]) >= 0.55 or float(fl[7]) < -0.12 or float(fl[8]) < -0.12
    return bool(inner_ok and perimeter_broken and future_stressed)


def zombi_fortaleza_frontier_signal(
    report: dict[str, Any],
    flows: Sequence[float] | None = None,
    contradictions: list[dict[str, Any]] | None = None,
) -> bool:
    """
    Señal inversa de frontera: el caso cae en Zombi, pero su lectura cercana natural es Fortaleza
    porque aún conserva cierto cuerpo interno y empieza a mostrar deterioro de acceso/perímetro.
    """
    p = np.asarray(report.get("potency100"), dtype=float).ravel()
    if p.size < 10:
        return False
    p3, p4 = float(p[2]), float(p[3])
    p5, p9 = float(p[4]), float(p[8])
    perimeter_soft = p3 <= 58.0 and p4 <= 58.0
    inner_body = p5 >= 48.0 and p9 >= 40.0
    return bool(
        inner_body
        and perimeter_soft
        and nokia_zombi_destino_pattern(report, flows, contradictions)
    )


def gigante_leviatan_frontier_signal(report: dict[str, Any]) -> bool:
    """
    Señal de frontera Gigante de Barro -> Leviatán Ciego.

    Hay masa real y déficit de esqueleto, pero empieza a aparecer densidad institucional
    suficiente como para que la lectura vecina natural sea Leviatán y no un patrón carismático.
    """
    p = np.asarray(report.get("potency100"), dtype=float).ravel()
    lk = np.asarray(report.get("leakscore"), dtype=float).ravel()
    m3 = np.asarray(report.get("avgm3"), dtype=float).ravel()
    if p.size < 10 or lk.size < 10 or m3.size < 10:
        return False
    p5, p6, p7, p8, p10 = float(p[4]), float(p[5]), float(p[6]), float(p[7]), float(p[9])
    return bool(
        gigante_barro_tensor_core(report)
        and p6 >= 58.0
        and p7 <= 45.0
        and 42.0 <= p5 <= 55.0
        and float(m3[4]) >= 4.0
        and (p8 <= 55.0 or float(lk[7]) >= 0.30)
        and p10 >= 45.0
    )


def leviatan_gigante_frontier_signal(
    report: dict[str, Any],
    flows: Sequence[float] | None = None,
) -> bool:
    """
    Señal inversa Leviatán Ciego -> Gigante de Barro.

    El aparato domina, pero el caso sigue arrastrando mucha masa operativa y económica, por lo que
    su vecino natural no es Fosilizada sino Gigante.
    """
    p = np.asarray(report.get("potency100"), dtype=float).ravel()
    lk = np.asarray(report.get("leakscore"), dtype=float).ravel()
    m3 = np.asarray(report.get("avgm3"), dtype=float).ravel()
    if p.size < 10 or lk.size < 10 or m3.size < 10:
        return False
    fl = _flows_ok(flows)
    p1, p2, p5, p6, p7, p8, p10 = float(p[0]), float(p[1]), float(p[4]), float(p[5]), float(p[6]), float(p[7]), float(p[9])
    mass_loaded = (p1 + p2 + p6) / 3.0 >= 54.0
    apparatus_dominant = p5 >= 60.0 and (p8 <= 40.0 or float(lk[7]) >= 0.32 or float(fl[7]) < -0.12)
    canon_heavy = p10 >= 63.0 and float(m3[9]) >= 6.7
    return bool(apparatus_dominant and mass_loaded and p7 >= 50.0 and not canon_heavy)


def organismo_asalto_pattern(report: dict[str, Any]) -> bool:
    """
    Dominancia relativa P6/P8 con vínculo emocional y cultura bajos (extracción / asalto).

    Umbrales alineados con lectura 0–10 vía potency100 (×10): P6≥5.5, P8≥5.0, P2≤3, P10≤3.
    """
    p = np.asarray(report["potency100"], dtype=float).ravel()
    if p.size < 10:
        return False
    if float(p[5]) < 55.0 or float(p[7]) < 50.0:
        return False
    if float(p[1]) > 30.0 or float(p[9]) > 30.0:
        return False
    return True


def vanguardia_disruptiva_pattern(report: dict[str, Any]) -> bool:
    """P9 hiper-potente; institución P5 en tensión."""
    p = np.asarray(report["potency100"], dtype=float).ravel()
    lk = np.asarray(report["leakscore"], dtype=float).ravel()
    m3 = np.asarray(report["avgm3"], dtype=float).ravel()
    if p.size < 10:
        return False
    if float(p[8]) < 64.0:
        return False
    return float(m3[4]) < 6.0 or float(lk[4]) >= 0.48


def feudo_carismatico_pattern(report: dict[str, Any]) -> bool:
    """P2 (vínculo) domina frente a P5 institucional."""
    p = np.asarray(report["potency100"], dtype=float).ravel()
    m3 = np.asarray(report["avgm3"], dtype=float).ravel()
    if p.size < 10:
        return False
    if float(p[1]) < 58.0:
        return False
    if float(p[1]) <= float(p[4]) + 4.0:
        return False
    return float(m3[4]) < 6.4


def estructura_fosilizada_pattern(
    report: dict[str, Any],
    flows: Sequence[float] | None,
) -> bool:
    """P10 cultural alto en forma; P9 tecnológico bloqueado o bajo."""
    p = np.asarray(report["potency100"], dtype=float).ravel()
    m3 = np.asarray(report["avgm3"], dtype=float).ravel()
    if p.size < 10:
        return False
    fl = _flows_ok(flows)
    if float(p[9]) < 56.0:
        return False
    if float(m3[9]) < 6.2:
        return False
    return float(p[8]) <= 53.0 or float(fl[8]) < -0.1


def gigante_barro_tensor_core(report: dict[str, Any]) -> bool:
    """
    Firma «volumen sin mando»: masa económica (P6) sin coordinación política (P7).

    Lectura de producto: P7 bajo = falta de centro de decisión / mando político claro en el tensor,
    no solo «debilidad diplomática». P5 capado evita confundir con institución muy consolidada
    (otros arquetipos); institución fragmentada o inconsistente encaja con el relato Gigante.

    Independiente de flows — precede a Nokia→Zombi cuando el tensor ya describe Gigante.
    """
    p = np.asarray(report.get("potency100"), dtype=float).ravel()
    if p.size < 10:
        return False
    if float(p[5]) < 55.0:
        return False
    if float(p[6]) > 45.0:
        return False
    if float(p[4]) > 50.0:
        return False
    return True


def gigante_barro_pattern(
    executive_integrity: float,
    friction: float,
    report: dict[str, Any],
) -> bool:
    """Masa con fricción alta e integridad baja; ilusión de poder — o firma tensor P6↑ P7↓."""
    if gigante_barro_tensor_core(report):
        return True
    p = np.asarray(report["potency100"], dtype=float).ravel()
    if p.size < 10:
        return False
    if friction < 5.2:
        return False
    if executive_integrity > 56.0:
        return False
    return float(np.mean(p[:10])) >= 38.0


def arquitectura_soberana_eligible(
    report: dict[str, Any],
    *,
    executive_integrity: float,
    friction: float,
    flows: Sequence[float] | None,
) -> bool:
    """Mando P7/P8 y norma sólida; además integridad >60%, fricción <4 y sin veto de hardware basal (M1 núcleo)."""
    if executive_integrity <= 60.0:
        return False
    if friction >= 4.0:
        return False
    if hardware_basal_veto_active(report):
        return False
    p = np.asarray(report["potency100"], dtype=float).ravel()
    m3 = np.asarray(report["avgm3"], dtype=float).ravel()
    fl = _flows_ok(flows)
    if p.size < 10 or m3.size < 10:
        return False
    if float(p[6]) < 61.0 or float(p[7]) < 60.0:
        return False
    if float(m3[6]) < 6.8 or float(m3[7]) < 6.6:
        return False
    if float(fl[6]) < -0.22 or float(fl[7]) < -0.22:
        return False
    if resonancia_fantasma_pattern(report, flows, None):
        return False
    if nokia_zombi_destino_pattern(report, flows, None) and float(p[5]) >= 50.0:
        return False
    if not positive_archetype_body_gate(report):
        return False
    return True


def arquitectura_soberana_hard_pattern(
    report: dict[str, Any],
    *,
    executive_integrity: float,
    friction: float,
    flows: Sequence[float] | None = None,
) -> bool:
    """
    Mando político-estratégico muy alto (P7/P8), sistema global estable (integridad ≥60, fricción ≤5).

    Override duro frente a Fortaleza Sitiada cuando el tensor describe soberanía sobre el entorno.
    P5 institucional: umbral suave ≥60 (si <60, no aplica; ≥70 refuerza el patrón típico).
    """
    p = np.asarray(report.get("potency100"), dtype=float).ravel()
    if p.size < 10:
        return False
    if float(p[6]) < 80.0 or float(p[7]) < 80.0:
        return False
    if float(executive_integrity) < 60.0:
        return False
    if float(friction) > 5.0:
        return False
    if float(p[4]) < 60.0:
        return False
    if hardware_basal_veto_active(report):
        return False
    fl = _flows_ok(flows)
    if float(fl[6]) < -0.35 or float(fl[7]) < -0.35:
        return False
    if organismo_asalto_pattern(report):
        return False
    return True


def leviatan_ciego_hard_pattern(
    report: dict[str, Any],
    *,
    executive_integrity: float,
    friction: float,
    flows: Sequence[float] | None = None,
) -> bool:
    """
    Institución muy fuerte (P5), maniobra estratégica débil (P8), cultura normativa (P10),
    sistema operativo sin colapso caótico (fricción no extrema).

    P5 en potency100 ≥60 (alineado con lectura 0–10). Fricción global hasta 10/10: en runtime
    `friction = mean(leak)×10` suele ser alta sin ser «Gigante»; un toque demasiado bajo anulaba
    el override y Nokia empujaba Zombi.

    No filtra por integridad ejecutiva global (antes ≥25 excluía casos reales): la firma P5/P8/P10
    basta para Leviatán degradado — burocracia rígida en crisis sin absorber el caso en Zombi por
    flows negativos en P8/P9 o por Nokia.

    Separa burocracia densa de Resonancia Fantasma (vacío simbólico).
    """
    p = np.asarray(report.get("potency100"), dtype=float).ravel()
    if p.size < 10:
        return False
    if float(p[4]) < 60.0:
        return False
    if float(p[7]) > 40.0:
        return False
    if float(p[9]) < 40.0:
        return False
    if float(friction) > 10.0:
        return False
    if organismo_asalto_pattern(report):
        return False
    if arquitectura_soberana_hard_pattern(
        report,
        executive_integrity=executive_integrity,
        friction=friction,
        flows=flows,
    ):
        return False
    return True


def priority_archetype_index(
    report: dict[str, Any],
    *,
    executive_integrity: float,
    friction: float,
    flows: Sequence[float] | None,
    contradictions: list[dict[str, Any]] | None,
) -> int | None:
    """
    Desempate semántico por orden fijo (el primero que cumpla reglas duras).
    Leviatán Ciego duro va antes de ramas Nokia→Zombi; además Nokia comprueba de nuevo el hard Leviatán.
    None → usar solo distancia + penalizaciones.
    """
    p = np.asarray(report.get("potency100"), dtype=float).ravel()
    if p.size < 10:
        return None
    pmax = _potency_signal(p)
    # Tensor degenerado (sin señal de potencia): fricción alta + integridad mínima → Gigante de Barro.
    if pmax < 12.0:
        if friction >= 8.0 and executive_integrity <= 45.0:
            return _IDX_GIGANTE
        return None

    # Override estructural por dominancia P6/P8 y P2/P10 bajos (antes de halo/Fantasma).
    if organismo_asalto_pattern(report):
        return _IDX_ORGANISMO

    # Fortaleza Sitiada antes de Leviatán/Nokia→Zombi: potencia interna + P3/P4 bajos (aislamiento).
    if fortaleza_sitiada_tensor_core(report):
        return _IDX_FORTALEZA

    if leviatan_ciego_hard_pattern(
        report,
        executive_integrity=executive_integrity,
        friction=friction,
        flows=flows,
    ):
        return _IDX_LEVIATAN

    if arquitectura_soberana_hard_pattern(
        report, executive_integrity=executive_integrity, friction=friction, flows=flows
    ):
        return _IDX_SOBERANA

    # Firma tensor Leviatán antes que halo/Fantasma (fricción alta puede anular solo el hard pattern).
    if leviatan_ciego_tensor_core(report):
        return _IDX_LEVIATAN

    # Gigante (P6↑, P7↓, P5 no alto) antes de Nokia→Zombi: mando estructural antes del drama «futuro/caja».
    if gigante_barro_tensor_core(report):
        return _IDX_GIGANTE

    if halo_vacuum_fantasma_pattern(report) and _potency_p10_allows_fantasma(report):
        return _IDX_FANTASMA
    if hardware_basal_veto_active(report):
        if nokia_zombi_destino_pattern(report, flows, contradictions):
            if leviatan_ciego_hard_pattern(
                report,
                executive_integrity=executive_integrity,
                friction=friction,
                flows=flows,
            ):
                return _IDX_LEVIATAN
            return _IDX_ZOMBI
        if _potency_p10_allows_fantasma(report) and not _fantasma_blocked_by_institution(report):
            return _IDX_FANTASMA
        return None
    m3_core = np.asarray(report.get("avgm3"), dtype=float).ravel()
    if m3_core.size >= 10:
        if any(float(m3_core[i]) < 4.0 for i in (0, 5, 8)):
            if nokia_zombi_destino_pattern(report, flows, contradictions):
                if leviatan_ciego_hard_pattern(
                    report,
                    executive_integrity=executive_integrity,
                    friction=friction,
                    flows=flows,
                ):
                    return _IDX_LEVIATAN
                return _IDX_ZOMBI
            if _potency_p10_allows_fantasma(report) and not _fantasma_blocked_by_institution(report):
                return _IDX_FANTASMA
            return None
    if resonancia_fantasma_pattern(report, flows, contradictions):
        return _IDX_FANTASMA
    if nokia_zombi_destino_pattern(report, flows, contradictions):
        if leviatan_ciego_hard_pattern(
            report,
            executive_integrity=executive_integrity,
            friction=friction,
            flows=flows,
        ):
            return _IDX_LEVIATAN
        return _IDX_ZOMBI
    if leviatan_ciego_pattern(report, flows):
        return _IDX_LEVIATAN
    if vanguardia_disruptiva_pattern(report):
        return _IDX_VANGUARDIA
    if feudo_carismatico_pattern(report):
        return _IDX_FEUDO
    if estructura_fosilizada_pattern(report, flows):
        return _IDX_FOSIL
    if gigante_barro_pattern(executive_integrity, friction, report):
        return _IDX_GIGANTE
    return None


def _ideal_vector(values: dict[int, float]) -> np.ndarray:
    """Base 0.5 + sparse overrides (índices FEATURE_DIM)."""
    a = np.full(FEATURE_DIM, 0.5, dtype=float)
    for idx, val in values.items():
        a[int(idx)] = _clip01(float(val))
    return a


# Perfiles ideales (referencia). Valores en [0,1] salvo nota.
ARCHETYPES: tuple[UniversalArchetype, ...] = (
    UniversalArchetype(
        id="arquitectura_soberana",
        name="Arquitectura Soberana",
        description=(
            "Integridad ejecutiva alta (>60 %), fricción global baja (<4/10) y sin veto de hardware basal "
            "(M1 fuerte en el núcleo P1/P6/P9): el Leviatán conserva coherencia de mando y la Capa Basal "
            "tensorial muestra potencia en P7/P8. Sistema consolidado, no torre blanda ni relato sin cuerpo."
        ),
        ideal=_ideal_vector(
            {
                0: 0.88,
                1: 0.30,
                2 + 6: 0.78,
                2 + 7: 0.76,
                2 + 5: 0.62,
                2 + 4: 0.58,
                12 + 6: 0.24,
                12 + 7: 0.26,
                22 + 6: 0.68,
                22 + 7: 0.66,
            }
        ),
    ),
    UniversalArchetype(
        id="vanguardia_disruptiva",
        name="Vanguardia Disruptiva",
        description=(
            "Tiro alto en innovación y narrativa (P9) con intención visible (M2 reflejada en potencia/asimetría) "
            "y déficit relativo de forma instituida en P5: crecimiento y disrupción por delante de la institución "
            "cotizada. Típico de fases de expansión o ofertas en construcción de gobierno."
        ),
        ideal=_ideal_vector(
            {
                0: 0.58,
                1: 0.44,
                2 + 8: 0.84,
                2 + 7: 0.72,
                2 + 4: 0.36,
                22 + 4: 0.38,
                12 + 4: 0.48,
            }
        ),
    ),
    UniversalArchetype(
        id="gigante_de_barro",
        name="Gigante de Barro",
        description=(
            "Fricción global elevada con potencia aún distribuida o aparentemente sólida: el peso del sistema es real, "
            "pero la forma (M3) no amortigua la tensión de manera uniforme. Riesgo de fisuras antes que de colapso "
            "instantáneo: cohesión que no sostiene del todo la estructura."
        ),
        ideal=_ideal_vector(
            {
                0: 0.46,
                1: 0.70,
                2: 0.62,
                3: 0.60,
                4: 0.61,
                5: 0.63,
                12: 0.58,
                13: 0.56,
                22: 0.42,
                23: 0.55,
                24: 0.38,
                25: 0.52,
            }
        ),
    ),
    UniversalArchetype(
        id="zombi_estrategico",
        name="Zombi Estratégico",
        description=(
            "Capital y apalancamiento narrativo (P6) aún reconocibles, pero el vector de flujo hacia futuro "
            "(P8/P9) muestra deriva o extracción de opcionalidad: el sistema financia apariencia de normalidad "
            "mientras la tesis estratégica se erosiona. Vigilar desalineación cash/narrativa."
        ),
        ideal=_ideal_vector(
            {
                0: 0.52,
                1: 0.52,
                2 + 5: 0.74,
                32 + 7: 0.38,
                32 + 8: 0.36,
                12 + 7: 0.52,
                12 + 8: 0.54,
            }
        ),
    ),
    UniversalArchetype(
        id="leviatan_ciego",
        name="Leviatán Ciego",
        description=(
            "Institución y construcción normativa (P5) hiperdesarrolladas en forma (M3) mientras la lectura "
            "de mercado/tecnología (P8) queda anémica: mando sin brújula competitiva. Riesgo de soberanía ritual "
            "frente a entorno que ya cambió las reglas del juego."
        ),
        ideal=_ideal_vector(
            {
                0: 0.55,
                1: 0.48,
                2 + 4: 0.80,
                2 + 7: 0.22,
                22 + 4: 0.82,
                12 + 7: 0.45,
            }
        ),
    ),
    UniversalArchetype(
        id="estructura_fosilizada",
        name="Estructura Fosilizada",
        description=(
            "El arco de trascendencia y cierre (P10) solidifica la forma instituida mientras la opcionalidad "
            "futura (P9) queda subordinada o bloqueada: excelencia en gobierno y ritual, riesgo de rigidez frente "
            "a shocks. No implica desaparición inmediata, sí resistencia al cambio de segunda orden."
        ),
        ideal=_ideal_vector(
            {
                0: 0.50,
                1: 0.46,
                2 + 9: 0.70,
                2 + 8: 0.40,
                22 + 9: 0.74,
                22 + 8: 0.42,
                12 + 8: 0.48,
            }
        ),
    ),
    UniversalArchetype(
        id="feudo_carismatico",
        name="Feudo Carismático",
        description=(
            "Legitimidad y relación con autoridad (A, reflejada en P2) desproporcionadas frente a la institución "
            "codificada (P5/M3): dependencia de un nodo central de confianza. Fase de inestabilidad de transición "
            "—no colapso instantáneo—: el sistema puede funcionar mientras dure el vínculo carismático; la "
            "sucesión y la formalización son la palanca de riesgo dominante."
        ),
        ideal=_ideal_vector(
            {
                0: 0.56,
                1: 0.50,
                2 + 1: 0.72,
                2 + 4: 0.48,
                22 + 1: 0.58,
                22 + 4: 0.44,
                12 + 1: 0.36,
            }
        ),
    ),
    UniversalArchetype(
        id="organismo_de_asalto",
        name="Organismo de Asalto",
        description=(
            "Máxima potencia en ejecución y narrativa corto plazo (P6/P8) con baja inversión relativa en "
            "trascendencia (P10) y en vínculo bilateral (P2): organismo orientado a captura de mercado y "
            "velocidad, expuesto a fatiga institucional si no se cierra el anillo de gobierno."
        ),
        ideal=_ideal_vector(
            {
                0: 0.54,
                1: 0.56,
                2 + 5: 0.78,
                2 + 7: 0.76,
                2 + 9: 0.28,
                2 + 1: 0.30,
                12 + 5: 0.52,
                12 + 7: 0.50,
            }
        ),
    ),
    UniversalArchetype(
        id="fortaleza_sitiada",
        name="Fortaleza Sitiada",
        description=(
            "Potencia interna alta en institución (P5) y tecnología (P9) con aislamiento externo: comunicación (P3) "
            "y acceso relacional (P4) débiles — el poder existe pero no circula al ecosistema. "
            "La firma tensorial contrasta núcleo vs perímetro (no exige integridad ejecutiva alta: puede coincidir con crisis global). "
            "No es colapso plano tipo Gigante ni extracción tipo Zombi: sistema funcional cercado en su propio perímetro."
        ),
        ideal=_ideal_vector(
            {
                0: 0.48,
                1: 0.62,
                2 + 8: 0.72,
                2 + 4: 0.68,
                2 + 2: 0.42,
                2 + 3: 0.40,
                12 + 2: 0.62,
                12 + 3: 0.64,
            }
        ),
    ),
    UniversalArchetype(
        id="resonancia_fantasma",
        name="Resonancia Fantasma",
        description=(
            "Solo el nodo de cierre/trascendencia (P10) mantiene lectura positiva clara frente a degradación "
            "generalizada del resto del tensor: eco institucional sin masa suficiente detrás. Sistema en riesgo de "
            "irrelevancia operativa pese a símbolos persistentes; exige recomposición o poda deliberada."
        ),
        ideal=_ideal_vector(
            {
                0: 0.38,
                1: 0.58,
                2 + 9: 0.64,
                2: 0.32,
                2 + 1: 0.30,
                2 + 2: 0.28,
                12: 0.62,
                12 + 1: 0.60,
                22 + 9: 0.55,
            }
        ),
    ),
)


def identify_archetype(
    report: dict[str, Any],
    *,
    executive_integrity: float,
    friction: float,
    flows: Sequence[float] | None = None,
    evidence_confidence_mean: float | None = None,
    contradictions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Devuelve el arquetipo universal de mayor afinidad y metadatos de confianza.

    Orden: (1) reglas duras por arquetipo (prioridad fija), (2) distancia al perfil ideal
    con penalizaciones (Soberana sin requisitos, Fantasma con tensor casi vacío, Nokia→Zombi).

    - confidence_pct: combinación de separación entre candidatos (softmax sobre -d²) y evidencia media.
    - hybrid: True si confianza < 50 % o segunda opción demasiado cercana.

    Override duro: patrón Organismo de Asalto (P6/P8 altos, P2/P10 bajos en potency100) fuerza salida
    sin depender de softmax; **Fortaleza Sitiada** (tensor core: núcleo P5/P9 vs perímetro P3/P4) fuerza Fortaleza
    antes de Leviatán duro y antes de Nokia→Zombi en prioridad. Resonancia Fantasma queda excluida si
    P10 (potency) < 40 o si P5 (institución) ≥ 70. Patrón Arquitectura Soberana fuerza Soberana tras Leviatán
    cuando aplique. Patrón Leviatán Ciego fuerza Leviatán frente a Fantasma y Zombi/Nokia en softmax.
    Depuración: variable de entorno NOUMENON_DEBUG_ARCHETYPE=1.
    """
    pten = np.asarray(report.get("potency100"), dtype=float).ravel()

    _lev_hard_pre = (
        pten.size >= 10
        and leviatan_ciego_hard_pattern(
            report,
            executive_integrity=executive_integrity,
            friction=friction,
            flows=flows,
        )
    )
    _debug_archetype(
        f"leviatan_ciego_hard_pattern={_lev_hard_pre} "
        f"tensor_core={bool(pten.size >= 10 and leviatan_ciego_tensor_core(report))} "
        f"anti_fantasma={bool(pten.size >= 10 and leviatan_ciego_tensor_anti_fantasma(report))} "
        f"friction={float(friction):.3f}"
    )

    # --- Override duro (sin softmax como decisión final): patrón estructural de asalto ---
    if pten.size >= 10 and organismo_asalto_pattern(report):
        x = build_archetype_feature_vector(
            report,
            executive_integrity=executive_integrity,
            friction=friction,
            flows=flows,
        )
        d_arr = np.asarray([float(np.linalg.norm(x - arch.ideal)) for arch in ARCHETYPES], dtype=float)
        d_arr = _mask_fantasma_distance(d_arr, report)
        best_i = _IDX_ORGANISMO
        tmp_second = d_arr.copy()
        tmp_second[best_i] = 1e9
        second_i = int(np.argmin(tmp_second))
        d1 = float(d_arr[best_i])
        d2 = float(d_arr[second_i])
        nokia_on = nokia_zombi_destino_pattern(report, flows, contradictions)
        ev = float(evidence_confidence_mean) if evidence_confidence_mean is not None else 62.0
        ev = float(np.clip(ev, 0.0, 100.0))
        confidence_pct = float(np.clip(0.72 * 92.0 + 0.28 * ev, 0.0, 100.0))
        best = ARCHETYPES[best_i]
        second = ARCHETYPES[second_i]
        _debug_archetype(f"chosen_archetype={best.id} (hard_override organismo_de_asalto)")
        return {
            "id": best.id,
            "name": best.name,
            "description": best.description,
            "confidence_pct": round(confidence_pct, 1),
            "hybrid": False,
            "runner_up_name": second.name,
            "runner_up_id": second.id,
            "distance_best": round(d1, 4),
            "distance_second": round(d2, 4),
            "nokia_calibration_applied": bool(nokia_on),
            "priority_rule_applied": True,
            "hard_override_organismo_asalto": True,
            "hard_override_arquitectura_soberana": False,
            "hard_override_leviatan_ciego": False,
            "hard_override_fortaleza_sitiada": False,
            "halo_vacuum_applied": bool(halo_vacuum_fantasma_pattern(report)),
            "positive_body_gate_ok": bool(positive_archetype_body_gate(report)),
            "hardware_basal_veto_active": bool(hardware_basal_veto_active(report)),
        }

    # --- Override duro: Fortaleza Sitiada (aislamiento tensor; tras Organismo, antes de Leviatán duro) ---
    if pten.size >= 10 and fortaleza_sitiada_tensor_core(report):
        x = build_archetype_feature_vector(
            report,
            executive_integrity=executive_integrity,
            friction=friction,
            flows=flows,
        )
        d_arr = np.asarray([float(np.linalg.norm(x - arch.ideal)) for arch in ARCHETYPES], dtype=float)
        d_arr = _mask_fantasma_distance(d_arr, report)
        best_i = _IDX_FORTALEZA
        tmp_second = d_arr.copy()
        tmp_second[best_i] = 1e9
        second_i = int(np.argmin(tmp_second))
        if fortaleza_zombi_frontier_signal(report, flows):
            second_i = _IDX_ZOMBI
        d1 = float(d_arr[best_i])
        d2 = float(d_arr[second_i])
        nokia_on = nokia_zombi_destino_pattern(report, flows, contradictions)
        ev = float(evidence_confidence_mean) if evidence_confidence_mean is not None else 62.0
        ev = float(np.clip(ev, 0.0, 100.0))
        confidence_pct = float(np.clip(0.72 * 91.0 + 0.28 * ev, 0.0, 100.0))
        best = ARCHETYPES[best_i]
        second = ARCHETYPES[second_i]
        _debug_archetype(f"chosen_archetype={best.id} (hard_override fortaleza_sitiada)")
        return {
            "id": best.id,
            "name": best.name,
            "description": best.description,
            "confidence_pct": round(confidence_pct, 1),
            "hybrid": False,
            "runner_up_name": second.name,
            "runner_up_id": second.id,
            "distance_best": round(d1, 4),
            "distance_second": round(d2, 4),
            "nokia_calibration_applied": bool(nokia_on),
            "priority_rule_applied": True,
            "hard_override_organismo_asalto": False,
            "hard_override_arquitectura_soberana": False,
            "hard_override_leviatan_ciego": False,
            "hard_override_fortaleza_sitiada": True,
            "halo_vacuum_applied": bool(halo_vacuum_fantasma_pattern(report)),
            "positive_body_gate_ok": bool(positive_archetype_body_gate(report)),
            "hardware_basal_veto_active": bool(hardware_basal_veto_active(report)),
        }

    # --- Override duro: Leviatán Ciego (antes que Soberana y antes de softmax / Nokia→Zombi) ---
    if pten.size >= 10 and leviatan_ciego_hard_pattern(
        report,
        executive_integrity=executive_integrity,
        friction=friction,
        flows=flows,
    ):
        _debug_archetype(
            "leviatan_ciego_hard_pattern=True chosen_archetype=leviatan_ciego (override)"
        )
        x = build_archetype_feature_vector(
            report,
            executive_integrity=executive_integrity,
            friction=friction,
            flows=flows,
        )
        d_arr = np.asarray([float(np.linalg.norm(x - arch.ideal)) for arch in ARCHETYPES], dtype=float)
        d_arr = _mask_fantasma_distance(d_arr, report)
        best_i = _IDX_LEVIATAN
        tmp_second = d_arr.copy()
        tmp_second[best_i] = 1e9
        second_i = int(np.argmin(tmp_second))
        if leviatan_gigante_frontier_signal(report, flows):
            second_i = _IDX_GIGANTE
        d1 = float(d_arr[best_i])
        d2 = float(d_arr[second_i])
        nokia_on = nokia_zombi_destino_pattern(report, flows, contradictions)
        ev = float(evidence_confidence_mean) if evidence_confidence_mean is not None else 62.0
        ev = float(np.clip(ev, 0.0, 100.0))
        confidence_pct = float(np.clip(0.72 * 91.0 + 0.28 * ev, 0.0, 100.0))
        best = ARCHETYPES[best_i]
        second = ARCHETYPES[second_i]
        return {
            "id": best.id,
            "name": best.name,
            "description": best.description,
            "confidence_pct": round(confidence_pct, 1),
            "hybrid": False,
            "runner_up_name": second.name,
            "runner_up_id": second.id,
            "distance_best": round(d1, 4),
            "distance_second": round(d2, 4),
            "nokia_calibration_applied": bool(nokia_on),
            "priority_rule_applied": True,
            "hard_override_organismo_asalto": False,
            "hard_override_arquitectura_soberana": False,
            "hard_override_leviatan_ciego": True,
            "hard_override_fortaleza_sitiada": False,
            "halo_vacuum_applied": bool(halo_vacuum_fantasma_pattern(report)),
            "positive_body_gate_ok": bool(positive_archetype_body_gate(report)),
            "hardware_basal_veto_active": bool(hardware_basal_veto_active(report)),
        }

    # --- Override duro: Arquitectura Soberana (P7/P8, integridad, fricción) ---
    if pten.size >= 10 and arquitectura_soberana_hard_pattern(
        report,
        executive_integrity=executive_integrity,
        friction=friction,
        flows=flows,
    ):
        x = build_archetype_feature_vector(
            report,
            executive_integrity=executive_integrity,
            friction=friction,
            flows=flows,
        )
        d_arr = np.asarray([float(np.linalg.norm(x - arch.ideal)) for arch in ARCHETYPES], dtype=float)
        d_arr = _mask_fantasma_distance(d_arr, report)
        best_i = _IDX_SOBERANA
        tmp_second = d_arr.copy()
        tmp_second[best_i] = 1e9
        second_i = int(np.argmin(tmp_second))
        d1 = float(d_arr[best_i])
        d2 = float(d_arr[second_i])
        nokia_on = nokia_zombi_destino_pattern(report, flows, contradictions)
        ev = float(evidence_confidence_mean) if evidence_confidence_mean is not None else 62.0
        ev = float(np.clip(ev, 0.0, 100.0))
        confidence_pct = float(np.clip(0.72 * 93.0 + 0.28 * ev, 0.0, 100.0))
        best = ARCHETYPES[best_i]
        second = ARCHETYPES[second_i]
        _debug_archetype(f"chosen_archetype={best.id} (hard_override arquitectura_soberana)")
        return {
            "id": best.id,
            "name": best.name,
            "description": best.description,
            "confidence_pct": round(confidence_pct, 1),
            "hybrid": False,
            "runner_up_name": second.name,
            "runner_up_id": second.id,
            "distance_best": round(d1, 4),
            "distance_second": round(d2, 4),
            "nokia_calibration_applied": bool(nokia_on),
            "priority_rule_applied": True,
            "hard_override_organismo_asalto": False,
            "hard_override_arquitectura_soberana": True,
            "hard_override_leviatan_ciego": False,
            "hard_override_fortaleza_sitiada": False,
            "halo_vacuum_applied": bool(halo_vacuum_fantasma_pattern(report)),
            "positive_body_gate_ok": bool(positive_archetype_body_gate(report)),
            "hardware_basal_veto_active": bool(hardware_basal_veto_active(report)),
        }

    x = build_archetype_feature_vector(
        report,
        executive_integrity=executive_integrity,
        friction=friction,
        flows=flows,
    )

    distances: list[float] = []
    for arch in ARCHETYPES:
        d = float(np.linalg.norm(x - arch.ideal))
        distances.append(d)

    d_arr = np.asarray(distances, dtype=float)
    pmax = _potency_signal(pten) if pten.size >= 10 else 0.0

    forced_i = priority_archetype_index(
        report,
        executive_integrity=executive_integrity,
        friction=friction,
        flows=flows,
        contradictions=contradictions,
    )
    if forced_i == _IDX_FANTASMA and (
        not _potency_p10_allows_fantasma(report) or _fantasma_blocked_by_institution(report)
    ):
        if leviatan_ciego_tensor_anti_fantasma(report):
            forced_i = _IDX_LEVIATAN
        else:
            forced_i = None

    nokia_on = nokia_zombi_destino_pattern(report, flows, contradictions)

    # Firma tensor Leviatán (P5/P8/P10) manda sobre Zombi por Nokia / flows P8–P9 (p. ej. fricción global alta).
    if forced_i == _IDX_ZOMBI and leviatan_ciego_tensor_anti_fantasma(report):
        forced_i = _IDX_LEVIATAN
    if forced_i is None and nokia_on and leviatan_ciego_tensor_anti_fantasma(report):
        forced_i = _IDX_LEVIATAN

    priority_rule = forced_i is not None

    if forced_i is None:
        d_arr = d_arr.copy()
        d_arr = _mask_fantasma_distance(d_arr, report)
        if pmax < 10.0:
            d_arr[_IDX_FANTASMA] *= 1.68
        if not positive_archetype_body_gate(report):
            d_arr[_IDX_SOBERANA] *= 1.95
            d_arr[_IDX_FORTALEZA] *= 1.95
        if hardware_basal_veto_active(report):
            d_arr[_IDX_SOBERANA] *= 2.1
            d_arr[_IDX_FORTALEZA] *= 2.1
        if not arquitectura_soberana_eligible(
            report,
            executive_integrity=executive_integrity,
            friction=friction,
            flows=flows,
        ):
            d_arr[_IDX_SOBERANA] *= 1.55
        if nokia_on and not leviatan_ciego_tensor_anti_fantasma(report):
            d_arr[_IDX_ZOMBI] *= 0.42
            d_arr[_IDX_FEUDO] *= 1.28
            d_arr[_IDX_GIGANTE] *= 1.12

    order = np.argsort(d_arr)
    best_i = int(forced_i) if forced_i is not None else int(order[0])
    second_i = int(order[1]) if len(order) > 1 else best_i
    if forced_i is not None:
        alt = [i for i in order if i != forced_i]
        second_i = int(alt[0]) if alt else best_i

    if best_i == _IDX_ZOMBI and zombi_fortaleza_frontier_signal(report, flows, contradictions):
        second_i = _IDX_FORTALEZA
    if best_i == _IDX_GIGANTE and gigante_leviatan_frontier_signal(report):
        second_i = _IDX_LEVIATAN

    # Último recurso: softmax puede seguir eligiendo Fantasma por distancia si la máscara falló por matices.
    if forced_i is None and best_i == _IDX_FANTASMA and leviatan_ciego_tensor_anti_fantasma(report):
        best_i = _IDX_LEVIATAN
        alt2 = [i for i in order if i != best_i]
        second_i = int(alt2[0]) if alt2 else int(order[0])

    # Similitud tipo softmax sobre scores = -d² (más cercano → más probabilidad)
    scores = -(d_arr**2)
    scores = scores - float(np.max(scores))
    exp_s = np.exp(scores)
    probs = exp_s / (float(np.sum(exp_s)) + 1e-12)
    sep_confidence = float(100.0 * probs[best_i])

    ev = float(evidence_confidence_mean) if evidence_confidence_mean is not None else 62.0
    ev = float(np.clip(ev, 0.0, 100.0))

    confidence_pct = float(np.clip(0.58 * sep_confidence + 0.42 * ev, 0.0, 100.0))

    d1 = float(d_arr[best_i])
    d2 = float(d_arr[second_i])
    close_race = (d2 - d1) < max(0.06, 0.12 * max(d1, 0.05))

    hybrid = confidence_pct < 50.0 or close_race or (pmax < 10.0)

    best = ARCHETYPES[best_i]
    second = ARCHETYPES[second_i]

    _hard_leviatan_soft_path = bool(
        forced_i == _IDX_LEVIATAN
        and (
            leviatan_ciego_tensor_core(report)
            or leviatan_ciego_tensor_anti_fantasma(report)
            or leviatan_ciego_hard_pattern(
                report,
                executive_integrity=executive_integrity,
                friction=friction,
                flows=flows,
            )
        )
    )
    _debug_archetype(
        f"chosen_archetype={best.id} (softmax path) priority_rule={priority_rule} "
        f"hard_override_leviatan_ciego={_hard_leviatan_soft_path}"
    )

    return {
        "id": best.id,
        "name": best.name,
        "description": best.description,
        "confidence_pct": round(confidence_pct, 1),
        "hybrid": hybrid,
        "runner_up_name": second.name,
        "runner_up_id": second.id,
        "distance_best": round(d1, 4),
        "distance_second": round(d2, 4),
        "nokia_calibration_applied": bool(nokia_on),
        "priority_rule_applied": bool(priority_rule),
        "hard_override_organismo_asalto": False,
        "hard_override_arquitectura_soberana": False,
        "hard_override_leviatan_ciego": _hard_leviatan_soft_path,
        "hard_override_fortaleza_sitiada": False,
        "halo_vacuum_applied": bool(halo_vacuum_fantasma_pattern(report)),
        "positive_body_gate_ok": bool(positive_archetype_body_gate(report)),
        "hardware_basal_veto_active": bool(hardware_basal_veto_active(report)),
    }
