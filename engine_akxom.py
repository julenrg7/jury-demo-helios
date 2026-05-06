#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
engine_akxom.py
Motor reutilizable de AKXOM OS / Noumenon

Incluye:
- ontología base
- helpers de tensor
- sanitización
- motor matemático
- diagnóstico
- construcción de report_data
- session_id UTC

NO incluye:
- CLI
- gráficos
- PDFs
- Streamlit
"""

from __future__ import annotations

import os
import hashlib
import datetime
from typing import Any, Dict, List, Tuple

import numpy as np


# ============================================================
# 1) CONSTANTES DE DOMINIO
# ============================================================
RISK_THRESHOLD = 1.0

# Etiquetas UI / negocio (no alteran cálculo)
LBL_POTENCY = "POTENCIA DE EJECUCIÓN"
LBL_FRICTION = "FRICCIÓN ESTRATÉGICA"
LBL_ENTROPY = "ENTROPÍA OPERATIVA"
LBL_STRUCT_FRAG = "VULNERABILIDAD ESTRUCTURAL"
LBL_AUTH_VOID = "DÉFICIT DE SOBERANÍA"
LBL_LEVEL_STRUCT = "INTEGRIDAD ESTRUCTURAL (M3)"
LBL_LEVEL_AUTH = "VALIDEZ DE AUTORIDAD (A)"

LABEL_POTENCY = "POTENCIA DE EJECUCIÓN"
LABEL_LEAK = "FRICCIÓN ESTRATÉGICA"
LABEL_ENTROPY = "ENTROPÍA OPERATIVA"
LABEL_DEF_M3 = "INTEGRIDAD ESTRUCTURAL (M3)"
LABEL_DEF_A = "VALIDEZ DE AUTORIDAD (A)"


# ============================================================
# 2) ONTOLOGÍA OBLIGATORIA
# ============================================================
poderes = ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9", "P10"]
materialidades = ["M1", "M2", "M3"]
ejes = ["R", "C", "A"]

AKXOM_DIAMOND: Dict[str, Dict[str, Any]] = {
    "P1": {
        "title": "BIOLÓGICO",
        "tagline": "Sin energía, no hay mando.",
        "keywords_short": "salud laboral · vitalidad · fatiga · bajas · biometría",
    },
    "P2": {
        "title": "EMOCIONAL",
        "tagline": "Quien regula las subjetividades, gobierna.",
        "keywords_short": "dopamina · carisma · símbolo · lealtad · Devoción",
    },
    "P3": {
        "title": "COMUNICATIVO",
        "tagline": "El marco vence al argumento.",
        "keywords_short": "infraestructura · narrativa · dogma · censura · autoridad",
    },
    "P4": {
        "title": "SOCIAL",
        "tagline": "El acceso decide.",
        "keywords_short": "masa · favores · membresía · networking · élite",
    },
    "P5": {
        "title": "INSTITUCIONAL",
        "tagline": "La posición opera antes que la voluntad.",
        "keywords_short": "cumplimiento · norma · disciplina · cargo · jerarquía",
    },
    "P6": {
        "title": "ECONÓMICO",
        "tagline": "El recurso es posibilidad organizada.",
        "keywords_short": "liquidez · expectativas · crédito · mercado · deuda",
    },
    "P7": {
        "title": "POLÍTICO",
        "tagline": "La soberanía decide en nombre del todo.",
        "keywords_short": "coacción · decisionismo · constitución · guerra · diplomacia",
    },
    "P8": {
        "title": "ESTRATÉGICO",
        "tagline": "El máximo poder define el tablero.",
        "keywords_short": "crisis · maniobra · timing · escenarios · disrupción",
    },
    "P9": {
        "title": "TECNOLÓGICO",
        "tagline": "Quien controla sistemas, escala efectos.",
        "keywords_short": "hardware · software · patentes · plataformas · IA",
    },
    "P10": {
        "title": "CULTURAL",
        "tagline": "Lo más fuerte parece natural.",
        "keywords_short": "confianza · reputación · valores · canon · legitimidad",
    },
}

PODERES_INFO: List[Tuple[str, str, str, str]] = [
    (
        p,
        AKXOM_DIAMOND[p]["title"],
        AKXOM_DIAMOND[p]["tagline"],
        AKXOM_DIAMOND[p]["keywords_short"],
    )
    for p in poderes
]


# ============================================================
# 3) HELPERS DE TENSOR
# ============================================================
def build_empty_tensor() -> np.ndarray:
    """
    Devuelve tensor vacío shape (10,3,3).
    """
    return np.zeros((10, 3, 3), dtype=float)


def sanitize_tensor(T: np.ndarray) -> np.ndarray:
    """
    Sanitiza tensor de entrada:
    - convierte a float
    - reemplaza NaN/inf por 0
    - clamp [0,10]
    - valida shape exacto (10,3,3)
    """
    arr = np.asarray(T, dtype=float)

    if arr.shape != (10, 3, 3):
        raise ValueError(
            f"T debe tener shape (10,3,3). Recibido: {arr.shape}"
        )

    arr = np.array(arr, dtype=float, copy=True)
    arr[~np.isfinite(arr)] = 0.0
    arr = np.clip(arr, 0.0, 10.0)
    return arr


def set_power_standard(T: np.ndarray, power_idx: int, value: float) -> np.ndarray:
    """
    Aplica broadcast de un valor a todo el poder T[power_idx,:,:].
    """
    arr = sanitize_tensor(T)
    arr[power_idx, :, :] = float(np.clip(value, 0.0, 10.0))
    return arr


def set_power_structured(
    T: np.ndarray,
    power_idx: int,
    m1: float,
    m2: float,
    m3: float,
    r: float,
    c: float,
    a: float,
) -> np.ndarray:
    """
    Construye la matriz 3x3 de un poder a partir de 6 entradas:
    - materialidades: M1, M2, M3
    - ejes: R, C, A

    Regla de composición:
    cada celda = media entre materialidad y eje
    """
    arr = sanitize_tensor(T)

    materiality = np.array([m1, m2, m3], dtype=float)
    axes = np.array([r, c, a], dtype=float)

    matrix = np.zeros((3, 3), dtype=float)

    for m_idx in range(3):
        for e_idx in range(3):
            matrix[m_idx, e_idx] = (materiality[m_idx] + axes[e_idx]) / 2.0

    matrix[~np.isfinite(matrix)] = 0.0
    matrix = np.clip(matrix, 0.0, 10.0)

    arr[power_idx, :, :] = matrix
    return arr


def recover_structured_params_from_matrix(M: np.ndarray) -> tuple[float, float, float, float, float, float]:
    """
    Inversa numérica de set_power_structured.

    Si la matriz 3×3 proviene de set_power_structured(m1…a), entonces
    2*M[i,j] = materialidad[i] + eje[j]. Recuperamos los seis valores por mínimos
    cuadrados (exacto salvo ruido numérico). Cualquier solución equivalente
    (m+=c, eje-=c) reproduce la misma matriz al volver a set_power_structured.
    """
    A = 2.0 * np.asarray(M, dtype=float).reshape(3, 3)
    design: list[list[float]] = []
    target: list[float] = []
    for i in range(3):
        for j in range(3):
            row = [0.0] * 6
            row[i] = 1.0
            row[3 + j] = 1.0
            design.append(row)
            target.append(float(A[i, j]))
    x, _, _, _ = np.linalg.lstsq(np.array(design, dtype=float), np.array(target, dtype=float), rcond=None)
    m1, m2, m3, r, c, a = (float(np.clip(v, 0.0, 10.0)) for v in x)
    return m1, m2, m3, r, c, a


def set_power_by_materiality(
    T: np.ndarray,
    power_idx: int,
    m1: float,
    m2: float,
    m3: float,
) -> np.ndarray:
    """
    Ajuste por materialidades: replica valor en todos los ejes.
    """
    arr = sanitize_tensor(T)
    arr[power_idx, 0, :] = float(np.clip(m1, 0.0, 10.0))
    arr[power_idx, 1, :] = float(np.clip(m2, 0.0, 10.0))
    arr[power_idx, 2, :] = float(np.clip(m3, 0.0, 10.0))
    return arr


def set_power_by_axis(
    T: np.ndarray,
    power_idx: int,
    r: float,
    c: float,
    a: float,
) -> np.ndarray:
    """
    Ajuste por ejes: replica valor en todas las materialidades.
    """
    arr = sanitize_tensor(T)
    arr[power_idx, :, 0] = float(np.clip(r, 0.0, 10.0))
    arr[power_idx, :, 1] = float(np.clip(c, 0.0, 10.0))
    arr[power_idx, :, 2] = float(np.clip(a, 0.0, 10.0))
    return arr


def set_power_full_matrix(T: np.ndarray, power_idx: int, matrix_3x3: np.ndarray) -> np.ndarray:
    """
    Ajuste completo 3x3 para un poder.
    """
    arr = sanitize_tensor(T)
    m = np.asarray(matrix_3x3, dtype=float)
    if m.shape != (3, 3):
        raise ValueError(f"matrix_3x3 debe tener shape (3,3). Recibido: {m.shape}")
    m[~np.isfinite(m)] = 0.0
    m = np.clip(m, 0.0, 10.0)
    arr[power_idx, :, :] = m
    return arr


# ============================================================
# 4) SESSION ID
# ============================================================
def generate_session_id_utc() -> str:
    """
    Formato: YYYYMMDD_HHMMSS_<4hex> (UTC)
    Ejemplo: 20260204_143712_A9F3
    """
    ts = datetime.datetime.now(datetime.UTC).strftime("%Y%m%d_%H%M%S")
    seed = f"{ts}|{os.getpid()}".encode("utf-8", "strict")
    h4 = hashlib.sha256(seed).hexdigest()[:4].upper()
    return f"{ts}_{h4}"


# ============================================================
# 5) MOTOR MATEMÁTICO
# ============================================================
def compute_metrics(T: np.ndarray) -> Dict[str, Any]:
    """
    Implementa el modelo AKXOM ponderado.
    Entrada:
        T shape (10,3,3), valores [0,10]

    Devuelve diccionario con:
        - pesos
        - potency
        - entropy
        - leakscore
        - avgm3
        - avga
        - rankings
    """
    T = sanitize_tensor(T)

    # Pesos doctrinales
    Wm = np.array([1.00, 1.00, 1.30], dtype=float)  # M1, M2, M3
    We = np.array([1.00, 1.00, 1.30], dtype=float)  # R, C, A

    # A) RawPotency
    weights = Wm.reshape(1, 3, 1) * We.reshape(1, 1, 3)  # (1,3,3)
    raw_potency = (T * weights).sum(axis=(1, 2))

    # B) Potency100
    max_cell = 10.0
    max_theoretical = (max_cell * (Wm.reshape(3, 1) * We.reshape(1, 3))).sum()
    potency100 = (raw_potency / max_theoretical) * 100.0
    potency100 = np.clip(potency100, 0.0, 100.0)

    # C) Valores por plano material
    val_m1 = (T[:, 0, :] * We.reshape(1, 3)).sum(axis=1)
    val_m2 = (T[:, 1, :] * We.reshape(1, 3)).sum(axis=1)
    val_m3 = (T[:, 2, :] * We.reshape(1, 3)).sum(axis=1)

    # D) Entropy raw
    gap12 = np.abs(val_m1 - val_m2)
    gap13 = np.abs(val_m1 - val_m3)
    gap23 = np.abs(val_m2 - val_m3)
    entropy = gap12 + gap13 + gap23

    # E) Promedios estructurales
    avg_m1 = T[:, 0, :].mean(axis=1)
    avg_m3 = T[:, 2, :].mean(axis=1)
    avg_a = T[:, :, 2].mean(axis=1)

    # Media simple de celdas por poder (0–10): lectura de nivel del nodo (p. ej. etapa germinal).
    power_cell_mean = T.mean(axis=(1, 2))

    # G) StabilityScore
    stability_score = avg_m3 * 0.6 + avg_a * 0.4

    # F) LeakScore recalibrado a escala utilizable
    # Entropy teórica máxima aproximada:
    # cada plano puede llegar a 33 (10 * (1 + 1 + 1.3))
    # la suma de gaps puede llegar a ~99
    # lo normalizamos a una banda cercana a 0-10
    entropy_norm = entropy / 9.9

    # fricción interna base
    base_leak = entropy_norm * (0.55 + 0.45 * (potency100 / 100.0))

    # déficits estructurales
    struct_deficit = np.maximum(0.0, 5.0 - avg_m3)
    auth_deficit = np.maximum(0.0, 5.0 - avg_a)

    # fragilidad combinada
    combined_fragility = struct_deficit * auth_deficit

    leakscore = (
        base_leak
        + 0.35 * struct_deficit
        + 0.30 * auth_deficit
        + 0.08 * combined_fragility
    )

    # muy importante: mantener escala estable para la app
    leakscore = np.clip(leakscore, 0.0, 10.0)

    # Rankings deterministas
    idxs = np.arange(10, dtype=int)

    top_sorted_all = sorted(
        idxs.tolist(),
        key=lambda i: (-float(leakscore[i]), -float(potency100[i]), int(i))
    )

    bottom_sorted = sorted(
        idxs.tolist(),
        key=lambda i: (float(leakscore[i]), -float(potency100[i]), int(i))
    )

    thr = float(RISK_THRESHOLD)
    risk_candidates = [i for i in idxs.tolist() if float(leakscore[i]) > thr]

    risk_sorted = sorted(
        risk_candidates,
        key=lambda i: (-float(leakscore[i]), -float(potency100[i]), int(i))
    )

    top3 = risk_sorted[:3]
    bottom3 = bottom_sorted[:3]
    top1 = top_sorted_all[0]

    return {
        "Tensor": T,
        "Wm": Wm,
        "We": We,
        "RawPotency": raw_potency,
        "Potency100": potency100,
        "Val_M1": val_m1,
        "AvgM1": avg_m1,
        "Val_M2": val_m2,
        "Val_M3": val_m3,
        "Gap12": gap12,
        "Gap13": gap13,
        "Gap23": gap23,
        "Entropy": entropy,
        "EntropyNorm": entropy_norm,
        "LeakScore": leakscore,
        "AvgM3": avg_m3,
        "AvgA": avg_a,
        "PowerCellMean": power_cell_mean,
        "StabilityScore": stability_score,
        "Top3": top3,
        "Bottom3": bottom3,
        "Top1": top1,
        "TopSortedAll": top_sorted_all,
        "BottomSortedAll": bottom_sorted,
        "MaxTheoreticalPerPower": float(max_theoretical),
    }

# ============================================================
# 6) DIAGNÓSTICO
# ============================================================
def build_diagnostics(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """
    Construye:
    - flags por poder
    - diagnóstico textual
    - veredicto global
    """
    potency = np.asarray(metrics["Potency100"], dtype=float)
    leak = np.asarray(metrics["LeakScore"], dtype=float)
    avg_m3 = np.asarray(metrics["AvgM3"], dtype=float)
    avg_a = np.asarray(metrics["AvgA"], dtype=float)

    power_contradictions = detect_power_contradictions(potency)

    top3 = set(metrics["Top3"])
    bottom3 = set(metrics["Bottom3"])
    top1 = int(metrics["Top1"])

    fragility = (avg_m3 < 4.0) | (avg_a < 4.0)
    risk_priority = np.array([i in top3 for i in range(10)], dtype=bool)

    per_power: List[Dict[str, Any]] = []

    for i, (p_code, p_title, _, _) in enumerate(PODERES_INFO):
        flags: List[str] = []

        if fragility[i]:
            flags.append("VULNERABILIDAD ESTRUCTURAL")
        if risk_priority[i]:
            flags.append("PUNTO DE INTERVENCIÓN")

        if fragility[i]:
            diag = (
                f"DÉFICIT CRÍTICO: El eje {p_title} opera sin integridad "
                f"estructural (M3) o sin validez de autoridad (A)."
            )
        else:
            if i in bottom3:
                diag = "ESTADO ÓPTIMO: Integridad estructural sólida y mínima fricción operativa."
            elif i in top3:
                diag = "PÉRDIDA DE TRACCIÓN: Alta potencia detectada, pero con fuga operativa por fricción interna."
            else:
                diag = "EQUILIBRIO FUNCIONAL: Estabilidad operativa con margen de optimización."

        per_power.append({
            "index": i,
            "code": p_code,
            "title": p_title,
            "Potency100": float(potency[i]),
            "LeakScore": float(leak[i]),
            "AvgM3": float(avg_m3[i]),
            "AvgA": float(avg_a[i]),
            "Fragility": bool(fragility[i]),
            "RiskPriority": bool(risk_priority[i]),
            "Flags": flags,
            "Text": diag,
        })

    n_frag = int(fragility.sum())
    avg_potency = float(np.mean(potency))
    avg_leak = float(np.mean(leak))
    top_leak = float(leak[top1])

    # veredicto global calibrado
    if n_frag >= 3 or (avg_potency < 45 and avg_leak >= 2.5):
        verdict = "FALLO SISTÉMICO: Arquitectura en riesgo de colapso."
    elif top_leak >= 5.0 or avg_leak >= 1.8:
        verdict = "SOBERANÍA EXPUESTA: Fuga de autoridad en ejes críticos."
    else:
        verdict = "ARQUITECTURA SOBERANA: Integridad estructural y mando consolidado."

    return {
        "PerPower": per_power,
        "FragilityFlags": fragility.tolist(),
        "FragilityCount": n_frag,
        "RiskPriorityFlags": risk_priority.tolist(),
        "Top3": metrics["Top3"],
        "Bottom3": metrics["Bottom3"],
        "Top1": metrics["Top1"],
        "FugaPrioritaria": bool(top_leak >= 5.0),
        "Verdict": verdict,
        "PowerContradictions": power_contradictions,
    }


def detect_power_contradictions(potency):

    contradictions = []

    p = np.asarray(potency, dtype=float)

    # Tecnología fuerte sin estrategia
    if p[8] > 70 and p[7] < 40:
        contradictions.append(
            "Tecnología fuerte (P9) sin estrategia suficiente (P8): riesgo de disrupción externa."
        )

    # Narrativa fuerte sin base cultural / de legitimidad
    if p[2] > 70 and p[9] < 45:
        contradictions.append(
            "Comunicación fuerte (P3) sin base cultural suficiente (P10): narrativa vulnerable."
        )

    # Dinero fuerte sin institución
    if p[5] > 70 and p[4] < 45:
        contradictions.append(
            "Capital fuerte (P6) sin estructura institucional suficiente (P5): riesgo de captura o desorden interno."
        )

    # Estrategia fuerte sin ejecución tecnológica
    if p[7] > 70 and p[8] < 45:
        contradictions.append(
            "Estrategia fuerte (P8) sin capacidad tecnológica suficiente (P9): incapacidad de ejecución."
        )

    return contradictions


# ============================================================
# 7) REPORT DATA
# ============================================================
def build_report_data(
    session_id: str,
    target: str,
    metrics: Dict[str, Any],
    diag: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Single source of truth para reporting / app / API.
    """
    potency100 = np.asarray(metrics["Potency100"], dtype=float)
    leakscore = np.asarray(metrics["LeakScore"], dtype=float)
    avgm1 = np.asarray(metrics["AvgM1"], dtype=float)
    avgm3 = np.asarray(metrics["AvgM3"], dtype=float)
    avga = np.asarray(metrics["AvgA"], dtype=float)
    power_cell_mean = np.asarray(metrics["PowerCellMean"], dtype=float)
    entropy = np.asarray(metrics["Entropy"], dtype=float)
    stability_score = np.asarray(metrics["StabilityScore"], dtype=float)

    fragility_flags = [(float(avgm3[i]) < 4.0) or (float(avga[i]) < 4.0) for i in range(10)]

    top3_idx = list(metrics["Top3"])
    bottom3_idx = list(metrics["Bottom3"])

    top3_labels = [poderes[i] for i in top3_idx]
    bottom3_labels = [poderes[i] for i in bottom3_idx]

    diagnostic_by_power = [diag["PerPower"][i]["Text"] for i in range(10)]
    global_verdict = diag["Verdict"]
    power_contradictions = diag.get("PowerContradictions", [])

    # Núcleo físico/caja/capacidad (P1, P6, P9): materialidad operativa M1 — techo para la narrativa institucional.
    m1_p1_p6_p9_mean = float((float(avgm1[0]) + float(avgm1[5]) + float(avgm1[8])) / 3.0)

    report_data = {
        "session_id": str(session_id),
        "target": str(target),
        "potency100": potency100,
        "leakscore": leakscore,
        "entropy": entropy,
        "avgm1": avgm1,
        "m1_p1_p6_p9_mean": m1_p1_p6_p9_mean,
        "avgm3": avgm3,
        "avga": avga,
        "power_cell_mean": power_cell_mean,
        "stability_score": stability_score,
        "fragility_flags": fragility_flags,
        "top3_risks_idx": top3_idx,
        "top3_risks_labels": top3_labels,
        "power_contradictions": power_contradictions,
        "bottom3_lowrisk_idx": bottom3_idx,
        "bottom3_lowrisk_labels": bottom3_labels,
        "diagnostic_by_power": diagnostic_by_power,
        "global_verdict": global_verdict,
    }
    return report_data


# ============================================================
# 8) PIPELINE DE MOTOR
# ============================================================
def run_engine(
    T: np.ndarray,
    target: str,
    session_id: str | None = None,
) -> Dict[str, Any]:
    """
    Pipeline completo del motor:
        T -> metrics -> diagnostics -> report_data

    Devuelve:
    {
        "session_id": ...,
        "target": ...,
        "metrics": ...,
        "diag": ...,
        "report_data": ...,
    }
    """
    if session_id is None:
        session_id = generate_session_id_utc()

    T = sanitize_tensor(T)
    metrics = compute_metrics(T)
    diag = build_diagnostics(metrics)
    report_data = build_report_data(session_id=session_id, target=target, metrics=metrics, diag=diag)

    return {
        "session_id": session_id,
        "target": target,
        "metrics": metrics,
        "diag": diag,
        "report_data": report_data,
    }


# ============================================================
# 8B) FLOW DE PODER
# ============================================================

def compute_power_flow(flow_vector):
    """
    Interpreta la tendencia estratégica de cada poder.

    flow_vector: lista o array de 10 valores entre -3 y +3

    Devuelve:
        labels: etiqueta estratégica por poder
    """

    labels = []

    for v in flow_vector:

        if v >= 1.5:
            labels.append("ASCENDENTE")

        elif v <= -1.5:
            labels.append("EN DETERIORO")

        elif v > 0.4:
            labels.append("CRECIMIENTO LENTO")

        elif v < -0.4:
            labels.append("DESGASTE")

        else:
            labels.append("ESTABLE")

    return labels


# ============================================================
# 9) SERIALIZACIÓN SEGURA
# ============================================================
def _to_py(v: Any) -> Any:
    """
    Convierte numpy scalars/arrays a tipos Python para JSON/API.
    """
    if isinstance(v, np.ndarray):
        return v.tolist()
    if isinstance(v, (np.floating,)):
        return float(v)
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, dict):
        return {k: _to_py(val) for k, val in v.items()}
    if isinstance(v, list):
        return [_to_py(x) for x in v]
    if isinstance(v, tuple):
        return [_to_py(x) for x in v]
    return v


def to_serializable(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convierte un payload del motor a dict serializable puro.
    """
    return _to_py(payload)


# ============================================================
# 10) AUTOTEST MÍNIMO
# ============================================================
if __name__ == "__main__":
    # Smoke test mínimo
    T = build_empty_tensor()

    # ejemplo simple: todos los poderes a 5
    for i in range(10):
        T = set_power_standard(T, i, 5.0)

    result = run_engine(T, target="TEST_TARGET")
    serializable = to_serializable(result)

    print("SESSION_ID:", serializable["session_id"])
    print("TARGET:", serializable["target"])
    print("VEREDICTO:", serializable["report_data"]["global_verdict"])
    print("TOP3:", serializable["report_data"]["top3_risks_labels"])
