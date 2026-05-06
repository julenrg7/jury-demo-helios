# simulation.py

import numpy as np

from analysis import apply_executive_verdict_to_report, compute_executive_integrity
from engine_akxom import run_engine, PODERES_INFO
from labels import format_power_label


def build_final_recommendation(
    report,
    decision_panel,
    intervention_outcome,
    current_integrity,
    current_friction,
    simulated_integrity,
    simulated_friction,
    current_top_risk,
    simulated_top_risk,
    manual_sim=None,
    archetype_name: str | None = None,
):
    acted_power = intervention_outcome["acted_power"]
    action_label = intervention_outcome["action_label"]

    delta_integrity = simulated_integrity - current_integrity
    delta_friction = simulated_friction - current_friction

    # Umbrales adaptativos:
    # Antes se usaba `delta_friction <= -4` como regla fija para "Intervenir ahora".
    # Pero el propio motor escala la fricción (LeakScore*10) en un rango 0..~5,
    # así que con `current_friction ~ 1-2` es matemáticamente casi imposible
    # conseguir una mejora absoluta de 4 puntos.
    # Usamos una mejora relativa para que el dictamen sea sensible a crisis reales.
    improve_ratio = 0.0
    if current_friction > 0:
        improve_ratio = (-delta_friction) / max(1e-6, current_friction)

    # Guardrail estructural de intervención forzada:
    # si hay 3+ poderes débiles (<4.5 en escala 0..10), nunca concluir "No intervenir".
    pcm = np.asarray(report.get("power_cell_mean"), dtype=float).reshape(-1)
    weak_count = int(np.sum(pcm < 4.5)) if pcm.size else 0
    forced_intervene = weak_count >= 3

    # CASO 1: mejora fuerte + cambia el riesgo dominante
    if delta_friction <= -4 and simulated_top_risk != current_top_risk:
        level = "Alta"
        title = "Intervenir ahora"
        summary = (
            f"Prioriza {acted_power}. Recorta {abs(delta_friction):.1f} puntos de fricción "
            f"y reconfigura el riesgo dominante."
        )
        next_step = "Ejecutar intervención inmediata con responsable y seguimiento."

    # Variante proporcional: misma idea, pero escalada al rango real de fricción.
    elif delta_friction < 0 and improve_ratio >= 0.6 and simulated_top_risk != current_top_risk:
        level = "Alta"
        title = "Intervenir ahora"
        summary = (
            f"Prioriza {acted_power}. Recorta {abs(delta_friction):.1f} puntos de fricción "
            f"({improve_ratio*100:.0f} % relativo) y cambia el riesgo dominante."
        )
        next_step = "Ejecutar intervención inmediata con responsable y seguimiento."

    # CASO 2: mejora fuerte pero no cambia el núcleo del problema
    elif delta_friction <= -4 or (delta_friction < 0 and improve_ratio >= 0.6):
        level = "Media-Alta"
        title = "Intervenir con segunda fase"
        summary = (
            f"Mejora clara (Δ fricción {delta_friction:+.1f}), pero el núcleo sigue en {current_top_risk}. "
            f"Prepara segunda fase sobre ese frente."
        )
        next_step = f"Ejecutar esta intervención y preparar una segunda acción sobre {current_top_risk}."

    # CASO 3: mejora parcial
    elif delta_friction < 0 or delta_integrity > 0:
        # Evitar sobreintervención cuando el sistema ya está en fricción baja
        # y la mejora proyectada es pequeña/incremental.
        low_friction = current_friction <= 2.8
        small_gain = abs(delta_friction) <= 1.2 and abs(delta_integrity) <= 0.3
        # Solo “no sobreintervenir” si no hay riesgo dominante real:
        # si ya hay P prioritario (ej. P2 crisis), una mejora parcial sigue siendo acción.
        no_dominant_risk = not current_top_risk or str(current_top_risk).strip() in (
            "",
            "Sin riesgo prioritario",
        )
        _ignition = str(archetype_name or "").strip() == "Ignición"
        if low_friction and small_gain and no_dominant_risk and not _ignition:
            level = "Baja"
            title = "No intervenir"
            summary = (
                "La arquitectura actual está en rango estable y la mejora simulada es incremental. "
                "No se recomienda sobreintervenir en este ciclo."
            )
            next_step = "Mantener vigilancia y revalidar en la siguiente corrida."
        else:
            level = "Media"
            title = "Intervenir con cautela"
            summary = (
                f"Mejora parcial: Δ fricción {delta_friction:+.1f}, Δ integridad {delta_integrity:+.1f} "
                f"({improve_ratio*100:.0f} % relativo). Valida en piloto antes de escalar."
            )
            next_step = "Validar en entorno controlado antes de escalar."

    # CASO 4A: sistema ya estable, no intervenir
    else:
        if (
            current_top_risk == "Sin riesgo prioritario"
            and current_friction <= 5
            and str(archetype_name or "").strip() != "Ignición"
        ):
            level = "Baja"
            title = "No intervenir"
            summary = (
                "La arquitectura actual no muestra fricción estructural relevante. "
                "No se recomienda intervenir; la prioridad es preservar estabilidad y vigilancia."
            )
            next_step = "Mantener seguimiento periódico y evitar sobreintervención."

        # CASO 4B: no hay mejora suficiente, replantear
        else:
            level = "Baja"
            title = "Replantear estrategia"
            summary = (
                "La simulación no muestra una mejora estructural suficiente como para recomendar esta intervención."
            )
            next_step = "Redefinir la estrategia antes de intervenir."

    integrity_threshold_alert = None
    if (
        title != "No intervenir"
        and (simulated_integrity < 60.0 or current_integrity < 60.0)
    ):
        integrity_threshold_alert = (
            "Integridad ejecutiva por debajo del 60 %: la mejora simulada no restaura soberanía estructural. "
            "El sistema sigue en crisis de gobierno."
        )

    if forced_intervene and title == "No intervenir":
        level = "Alta"
        title = "Intervenir ahora"
        summary = (
            f"Se detectan {weak_count} poderes en zona débil (<4.5): "
            "no procede preservar arquitectura; se requiere intervención."
        )
        next_step = "Activar intervención prioritaria con responsable y fecha de revisión."

    return {
        "level": level,
        "title": title,
        "summary": summary,
        "next_step": next_step,
        "acted_power": acted_power,
        "action_label": action_label,
        "delta_integrity": delta_integrity,
        "delta_friction": delta_friction,
        "integrity_threshold_alert": integrity_threshold_alert,
        "forced_intervention_guardrail": bool(forced_intervene),
        "weak_powers_count": int(weak_count),
    }


def build_action_display_label(action_label, acted_power):
    if not action_label or action_label == "Sin intervención recomendada":
        return "Sin intervención recomendada"

    power_label = format_power_label(acted_power) if acted_power else "sistema"

    if "Intervención 1" in action_label:
        return f"Ajuste estructural en {power_label}"
    elif "Intervención 2" in action_label:
        return f"Refuerzo operativo en {power_label}"
    elif "Intervención 3" in action_label:
        return f"Reordenación mixta en {power_label}"
    elif "Intervención 4" in action_label:
        return f"Intervención estructural intensiva en {power_label}"
    elif "Intervención 5" in action_label:
        return f"Refuerzo de autoridad y cohesión en {power_label}"

    return action_label


def _ranked_intervention_meta(
    candidates: list[dict],
    base_integrity: float,
    base_friction: float,
    *,
    limit: int = 5,
) -> list[dict]:
    """Mismo orden que el dictamen; Δ en convención final_reco (sim − actual)."""
    rows: list[dict] = []
    for c in candidates[:limit]:
        rows.append(
            {
                "acted_power": c["acted_power"],
                "label": c["label"],
                "delta_integrity": float(c["integrity"] - base_integrity),
                "delta_friction": float(c["friction"] - base_friction),
            }
        )
    return rows


def simulate_intervention_outcome(
    T,
    report,
    intervention_strategies,
    target,
    *,
    prioritize_institutional_build: bool = False,
):
    """El barrido numérico usa top3_risks del report (intervention_strategies mantiene firma estable)."""
    _ = intervention_strategies
    T_base = np.array(T, dtype=float, copy=True)
    target_name = target if target else "Unknown"

    base_result = run_engine(T_base, target_name)
    base_report = base_result["report_data"]
    apply_executive_verdict_to_report(base_report)
    base_integrity = compute_executive_integrity(base_report)
    base_friction = np.mean(base_report["leakscore"]) * 10

    top_risks_idx = list(report.get("top3_risks_idx", []))
    if prioritize_institutional_build and top_risks_idx:
        p5 = 4
        merged: list[int] = [p5] + [int(i) for i in top_risks_idx if int(i) != p5]
        seen: set[int] = set()
        new_top: list[int] = []
        for i in merged:
            if i not in seen:
                new_top.append(i)
                seen.add(i)
            if len(new_top) >= 3:
                break
        for i in top_risks_idx:
            if len(new_top) >= 3:
                break
            ii = int(i)
            if ii not in seen:
                new_top.append(ii)
                seen.add(ii)
        top_risks_idx = new_top[:3]

    if not top_risks_idx:
        return {
            "sim_report": base_report,
            "acted_power": None,
            "action_label": "Sin intervención necesaria",
            "ranked_meta": [],
        }

    candidates: list[dict] = []

    for acted_idx in top_risks_idx[:3]:
        acted_power = PODERES_INFO[int(acted_idx)][0]

        intervention_patterns = [
            {"m3_row": 0.8, "a_col": 0.8, "c_col": 0.4, "m1_row": 0.0, "m2_row": 0.0},
            {"m3_row": 0.3, "a_col": 0.4, "c_col": 0.2, "m1_row": -0.8, "m2_row": -0.4},
            {"m3_row": 0.6, "a_col": 0.5, "c_col": 0.2, "m1_row": -0.4, "m2_row": -0.2},
            {"m3_row": 1.2, "a_col": 1.0, "c_col": 0.5, "m1_row": -0.6, "m2_row": -0.3},
            {"m3_row": 0.2, "a_col": 0.9, "c_col": 0.5, "m1_row": -0.2, "m2_row": -0.2},
        ]

        for idx_pattern, pattern in enumerate(intervention_patterns, start=1):
            T_sim = np.array(T_base, dtype=float, copy=True)

            T_sim[acted_idx, 0, :] = np.clip(T_sim[acted_idx, 0, :] + pattern["m1_row"], 0.0, 10.0)
            T_sim[acted_idx, 1, :] = np.clip(T_sim[acted_idx, 1, :] + pattern["m2_row"], 0.0, 10.0)
            T_sim[acted_idx, 2, :] = np.clip(T_sim[acted_idx, 2, :] + pattern["m3_row"], 0.0, 10.0)

            T_sim[acted_idx, :, 1] = np.clip(T_sim[acted_idx, :, 1] + pattern["c_col"], 0.0, 10.0)
            T_sim[acted_idx, :, 2] = np.clip(T_sim[acted_idx, :, 2] + pattern["a_col"], 0.0, 10.0)

            sim_result = run_engine(T_sim, target_name)
            sim_report = sim_result["report_data"]

            sim_integrity = compute_executive_integrity(sim_report)
            sim_friction = np.mean(sim_report["leakscore"]) * 10

            delta_friction_sort = base_friction - sim_friction
            delta_integrity_sort = sim_integrity - base_integrity

            candidates.append({
                "label": f"Intervención {idx_pattern} sobre {acted_power}",
                "report": sim_report,
                "acted_power": acted_power,
                "integrity": sim_integrity,
                "friction": sim_friction,
                "delta_friction": delta_friction_sort,
                "delta_integrity": delta_integrity_sort,
            })

    candidates.sort(
        key=lambda x: (x["delta_friction"], x["delta_integrity"]),
        reverse=True
    )

    ranked_meta = _ranked_intervention_meta(candidates, base_integrity, base_friction, limit=5)
    best = candidates[0]

    if best["delta_friction"] <= 0 and best["delta_integrity"] <= 0:
        return {
            "sim_report": base_report,
            "acted_power": None,
            "action_label": "Sin intervención recomendada",
            "ranked_meta": ranked_meta,
        }

    apply_executive_verdict_to_report(best["report"])
    return {
        "sim_report": best["report"],
        "acted_power": best["acted_power"],
        "action_label": best["label"],
        "ranked_meta": ranked_meta,
    }


def simulate_forced_intervention(T, report, target, forced_idx):
    T_sim = np.array(T, dtype=float, copy=True)
    target_name = target if target else "Unknown"

    acted_power = PODERES_INFO[int(forced_idx)][0]

    T_sim[forced_idx, 0, :] = np.clip(T_sim[forced_idx, 0, :] - 0.8, 0.0, 10.0)
    T_sim[forced_idx, 1, :] = np.clip(T_sim[forced_idx, 1, :] - 0.4, 0.0, 10.0)
    T_sim[forced_idx, 2, :] = np.clip(T_sim[forced_idx, 2, :] + 0.6, 0.0, 10.0)

    T_sim[forced_idx, :, 1] = np.clip(T_sim[forced_idx, :, 1] + 0.2, 0.0, 10.0)
    T_sim[forced_idx, :, 2] = np.clip(T_sim[forced_idx, :, 2] + 0.5, 0.0, 10.0)

    sim_result = run_engine(T_sim, target_name)
    sim_report = sim_result["report_data"]
    apply_executive_verdict_to_report(sim_report)

    sim_integrity = compute_executive_integrity(sim_report)
    sim_friction = np.mean(sim_report["leakscore"]) * 10
    sim_top_risk = sim_report["top3_risks_labels"][0] if sim_report["top3_risks_labels"] else "Sin riesgo prioritario"

    return {
        "acted_power": acted_power,
        "sim_report": sim_report,
        "integrity": sim_integrity,
        "friction": sim_friction,
        "top_risk": sim_top_risk
    }