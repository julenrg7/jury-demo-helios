"""
Cadena causal determinista (sin LLM): señales + tensor + nodo de riesgo.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from engine_akxom import PODERES_INFO
from labels import format_power_label

CAUSAL_PATTERNS: dict[str, list[str]] = {
    "degradacion": [
        "No existe dirección operativa clara -> las decisiones son reactivas.",
        "El sistema no genera futuro útil -> no corrige su trayectoria.",
        "La organización no puede ejecutar de forma coherente -> las mejoras no se materializan.",
    ],
    "dependencia": [
        "El poder está concentrado en nodos individuales -> el mando no se institucionaliza.",
        "La estructura no sostiene la operación -> la continuidad queda expuesta.",
        "El sistema depende de decisiones personales -> cualquier ausencia bloquea ejecución.",
    ],
    "fantasma": [
        "La percepción excede la capacidad real -> la marca no compensa la operación.",
        "La base operativa es insuficiente -> el rendimiento no escala con la narrativa.",
        "Existe desconexión entre imagen y ejecución -> la fricción aumenta en cada ciclo.",
    ],
    "equilibrado": [
        "La arquitectura mantiene coordinación funcional -> los frentes críticos no se acumulan.",
        "La operación conserva capacidad de ajuste -> la fricción no domina el sistema.",
        "El gobierno sostiene continuidad estructural -> el riesgo se mantiene controlable.",
    ],
}


def _power_means_from_tensor(tensor: Any) -> np.ndarray:
    arr = np.asarray(tensor, dtype=float)
    if arr.ndim != 3 or arr.shape[0] < 1:
        return np.zeros(10, dtype=float)
    flat = arr.reshape(arr.shape[0], -1)
    means = np.mean(flat, axis=1)
    out = np.zeros(10, dtype=float)
    n = min(10, means.shape[0])
    out[:n] = means[:n]
    return out


def classify_causal_pattern(signals: list[str] | None, tensor: Any) -> str:
    sig_set = {str(s).strip().lower() for s in (signals or []) if str(s).strip()}
    means = _power_means_from_tensor(tensor)
    weak_count = int(np.sum(means < 4.5))

    if {"dependencia_critica", "dependencia_lider", "lider_central"} & sig_set:
        return "dependencia"
    if "marca_fuerte" in sig_set and not ({"tecnologia_fuerte", "alta_tecnologia", "innovacion_activa"} & sig_set):
        return "fantasma"
    if weak_count >= 3 or {"falta_estrategia", "sin_innovacion", "estructura_fragmentada", "falta_gobierno"} & sig_set:
        return "degradacion"
    return "equilibrado"


def build_causal_chain(signals: list[str] | None, tensor: Any, risk_node: str | None) -> dict[str, Any]:
    sigs = [str(s).strip().lower() for s in (signals or []) if str(s).strip()]
    sig_set = set(sigs)
    pattern = classify_causal_pattern(sigs, tensor)
    steps: list[str] = list(CAUSAL_PATTERNS.get(pattern, []))

    means = _power_means_from_tensor(tensor)
    weak_count = int(np.sum(means < 4.5))
    if weak_count >= 3 and pattern != "equilibrado" and len(steps) < 4:
        steps.append(
            f"{weak_count} poderes operan en zona débil (<4.5) -> la arquitectura entra en fricción sostenida."
        )

    # Ajustes menores por señales (consistencia, no creatividad libre).
    if "falta_gobierno" in sig_set and pattern in {"degradacion", "dependencia"} and len(steps) >= 2:
        steps[1] = "No hay capacidad de coordinación efectiva -> los frentes críticos compiten sin cierre."
    if "sin_innovacion" in sig_set and pattern == "degradacion" and len(steps) >= 2:
        steps[1] = "El sistema no genera futuro útil -> pierde capacidad de corregir su trayectoria."
    if "estructura_fragmentada" in sig_set and pattern in {"degradacion", "dependencia"} and len(steps) >= 3:
        steps[2] = "La organización no puede ejecutar de forma coherente -> la mejora no se materializa."

    if not steps:
        top_idx = int(np.argmin(means)) if means.size else 0
        top_code = PODERES_INFO[top_idx][0] if 0 <= top_idx < len(PODERES_INFO) else "P1"
        steps = [
            f"El nodo más tensionado es {format_power_label(top_code)} -> concentra bloqueo operativo.",
            "La coordinación no absorbe la tensión -> la fricción se acumula en la operación.",
            "Sin corrección del nodo crítico -> el sistema pierde capacidad de ejecución.",
        ]

    risk_lab = format_power_label(str(risk_node or "").strip()) if str(risk_node or "").strip() else "el nodo de riesgo dominante"
    conclusion = (
        f"La intervención en {risk_lab} no es opcional: es condición necesaria para recuperar capacidad estructural."
    )
    return {"steps": steps[:4], "conclusion": conclusion}

