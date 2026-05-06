import numpy as np
import pandas as pd

from analysis import (
    GERMINAL_P5_BENCHMARK_GAP_NOTE_MIN,
    compute_executive_integrity,
    decadence_sovereign_active,
    germinal_startup_stage_active,
    ignition_archetype_active,
)
from engine_akxom import PODERES_INFO
from archetype_actions import archetype_action_block_lines
from labels import format_power_label

_SEVERE_ARCHETYPES_STABILITY_COPY = frozenset(
    {"Colapso inminente", "Gigante de barro", "Estructura en combustión"}
)


def _severe_stability_wording(
    executive_integrity: float | None,
    archetype_name: str | None,
) -> bool:
    """True cuando el resumen global es de crisis: no llamar «base operativa sana» al mejor nodo tensorial."""
    if executive_integrity is not None and float(executive_integrity) < 40.0:
        return True
    an = (archetype_name or "").strip()
    return an in _SEVERE_ARCHETYPES_STABILITY_COPY


def _relative_fragility_stability_narrative(
    executive_integrity: float | None,
    archetype_name: str | None,
) -> bool:
    """Crisis, severidad alta o Ignición: usar siempre la nota de menor fragilidad relativa, no «base sana»."""
    if _severe_stability_wording(executive_integrity, archetype_name):
        return True
    return (archetype_name or "").strip() == "Ignición"


def _narrative_stability_excluded_indices(report: dict, archetype_name: str | None) -> set[int]:
    """
    Índices que no deben presentarse como «base de estabilidad operativa» en narrativa:
    P5/P6 bajo filtro prospecto/S-1; P5 en Ignición (deuda institucional, no pedestal).
    """
    ex: set[int] = set()
    prof = report.get("ingest_disclosure") or {}
    if bool(prof.get("offering_prospectus_context")):
        ex.add(4)
        ex.add(5)
    if (archetype_name or "").strip() == "Ignición":
        ex.add(4)
    return ex


def get_stability_focal_poder_code(report: dict, archetype_name: str | None = None) -> str:
    """
    Poder focal para copy de estabilidad (board, CEO, panel): argmax de stability_score
    excluyendo nodos con cap de escepticismo o P5 en Ignición.
    """
    scores = np.asarray(report["stability_score"], dtype=float)
    excluded = _narrative_stability_excluded_indices(report, archetype_name)
    order = list(np.argsort(-scores))
    for i in order:
        idx = int(i)
        if idx not in excluded:
            return PODERES_INFO[idx][0]
    return PODERES_INFO[int(np.argmax(scores))][0]


def stability_operativa_sentence(
    poder_code: str,
    *,
    executive_integrity: float | None = None,
    archetype_name: str | None = None,
) -> str:
    """
    Frase sobre el poder con mayor stability_score.
    En severidad alta, evita contradecir colapso / integridad crítica.
    """
    lab = format_power_label(str(poder_code))
    if _severe_stability_wording(executive_integrity, archetype_name):
        return (
            "Con severidad global alta, el nodo con menor fragilidad relativa según el tensor es "
            f"{lab} (referencia comparativa; no describe una base operativa sana en sentido absoluto)."
        )
    if (archetype_name or "").strip() == "Ignición":
        return (
            f"En Ignición, el nodo con menor fragilidad relativa según el tensor es {lab} "
            "(referencia comparativa; no sustituye construcción explícita de institución ni base cotizada madura)."
        )
    return f"La base de estabilidad operativa es {lab}."


def get_stability_base_code(report):
    """Compatibilidad: focal sin exclusiones narrativas (p. ej. CEO Demo)."""
    return get_stability_focal_poder_code(report, None)


def detect_narrative_mode(report):
    leak = np.asarray(report["leakscore"], dtype=float)
    avgm3 = np.asarray(report["avgm3"], dtype=float)

    global_friction = float(np.mean(leak) * 10.0)
    avg_integrity = float(np.mean(avgm3) * 10.0)

    if global_friction <= 5:
        return "stable"

    if global_friction >= 80 or avg_integrity <= 45:
        return "critical"

    return "leak"


def detect_structural_archetype(report):
    potency = np.asarray(report["potency100"], dtype=float)
    leak = np.asarray(report["leakscore"], dtype=float)

    avg_power = float(np.mean(potency))
    max_power = float(np.max(potency))
    power_std = float(np.std(potency))
    avg_leak = float(np.mean(leak))
    max_leak = float(np.max(leak))
    std_leak = float(np.std(leak))
    prof = report.get("ingest_disclosure") or {}
    healthy_doc = (
        bool(prof.get("healthy_disclosure_bias"))
        and not bool(prof.get("strong_crisis_evidence"))
        and not bool(prof.get("critical_incident_evidence"))
    )
    if healthy_doc:
        avg_leak *= 0.90
        std_leak *= 0.94
    # Misma escala que la UI de fricción global: mean(leakscore) * 10.
    friction_global = avg_leak * 10.0
    # Calibración Fase 0: umbral «sistema sano» (p. ej. Citadel ~1.7) subido respecto a 1.2 implícito.
    EQUILIBRADA_MAX_FRICTION_LOOSE = 1.8
    EQUILIBRADA_MAX_FRICTION_LEGACY = 3.8  # coherente con avg_leak < 0.38 histórico
    EQUILIBRADA_POWER_STD_LOOSE = 14.0
    EQUILIBRADA_POWER_STD_TIGHT = 10.0

    # Ignición: germinal (P8+P9 altos, P5 bajo) o S-1/prospecto con P8+P9 altos (P5 como deuda institucional).
    if ignition_archetype_active(report):
        prof = report.get("ingest_disclosure") or {}
        if bool(prof.get("offering_prospectus_context")) and not germinal_startup_stage_active(report):
            return (
                "Ignición",
                "Oferta pública (S-1/prospecto): impulso fuerte en P8 y P9; el P5 institucional refleja "
                "deuda de gobierno real bajo normativa de oferta, no madurez de empresa cotizada consolidada.",
            )
        return (
            "Ignición",
            "Sistema en fase de expansión acelerada; la potencia estratégica y tecnológica compensa "
            "la falta de madurez institucional (estructura germinal).",
        )

    # Prioridad: lecturas fuertes primero (tragedia / peso aparente sin sostén).
    if max_leak > 2.55 or avg_leak > 1.02:
        return (
            "Colapso inminente",
            "La fuga estructural es extrema o generalizada: el sistema pierde coherencia antes que peso simbólico; la tragedia organizativa está al borde del salto cualitativo."
        )

    if decadence_sovereign_active(report):
        return (
            "Decadencia Soberana",
            "Large cap con base institucional aún sólida pero estrés económico y alta fricción en el nodo "
            "tecnológico: el sistema vive de escala e historia instalada más que de liderazgo competitivo pleno.",
        )

    # No confundir homogeneidad + fuga tensorial moderada con «barro» si el juicio ejecutivo es sólido.
    try:
        ei_exec = float(compute_executive_integrity(report))
    except Exception:
        ei_exec = 0.0

    inertial = report.get("inertial_sovereignty") or {}
    if (
        bool(inertial.get("active"))
        and ei_exec > 65.0
        and friction_global < 7.0
    ):
        return (
            "Soberanía Inercial",
            "Sistema de alta solvencia basado en inercia institucional y económica; riesgo de erosión por falta de "
            "tiro estratégico dinámico frente a la narrativa tecnológica actual.",
        )

    if ei_exec > 70.0 and friction_global < 7.0:
        return (
            "Arquitectura Soberana",
            "Integridad ejecutiva alta con fricción global acotada: capacidad estructural consolidada; "
            "la tensión residual en el tensor no implica pérdida de mando institucional ni fragilidad tipo «torre blanda».",
        )

    if avg_leak > 0.58 and avg_power > 54.0 and power_std < 13.5:
        return (
            "Gigante de barro",
            "Potencia homogénea y elevada con fuga persistente: el peso del sistema es real, pero la cohesión no sostiene la forma; la torre crece y se resquebraja."
        )

    if avg_leak > 0.42 and max_leak > 1.45:
        return (
            "Estructura en combustión",
            "La fricción se concentra y arde en focos: capacidad y tensión chocan sin válvula institucional suficiente."
        )

    # Equilibrio: o bien dispersión ajustada + fricción baja (legacy), o fricción muy baja (≤1.8) + dispersión algo mayor.
    if (power_std < EQUILIBRADA_POWER_STD_TIGHT and friction_global <= EQUILIBRADA_MAX_FRICTION_LEGACY) or (
        power_std < EQUILIBRADA_POWER_STD_LOOSE and friction_global <= EQUILIBRADA_MAX_FRICTION_LOOSE
    ):
        return (
            "Arquitectura equilibrada",
            "Poder relativamente distribuido y fuga estructural acotada: sistema estable sin drama organizativo dominante."
        )

    if max_power > 70 and power_std > 15:
        return (
            "Centralización de poder",
            "El sistema muestra concentración significativa de poder en uno o pocos nodos."
        )

    if avg_power < 40 and power_std < 8:
        return (
            "Sistema fragmentado",
            "Ningún poder logra estructurar el sistema. La arquitectura carece de nodo dominante."
        )

    if avg_power > 50 and avg_leak > 1.8:
        return (
            "Potencia con fuga estructural",
            "El sistema posee capacidad pero pierde eficiencia por desalineación estructural."
        )

    if avg_power < 45 and avg_leak > 1.8:
        return (
            "Arquitectura en riesgo",
            "La arquitectura del sistema muestra debilidad estructural significativa."
        )

    t_std, t_avg = (0.40, 0.48) if healthy_doc else (0.32, 0.35)
    if std_leak > t_std and avg_leak > t_avg:
        return (
            "Tragedia distribuida",
            "La tensión no vive en un solo poder: se reparte; el sistema sufre sin culpable único, lo que hace el deterioro más difícil de contener."
        )

    return (
        "Arquitectura híbrida",
        "El sistema combina rasgos de múltiples configuraciones estructurales."
    )


def build_intervention_recommendations(report):
    top_risks = report["top3_risks_idx"]
    avgm3 = report["avgm3"]
    avga = report["avga"]
    potency = report["potency100"]
    leak = report["leakscore"]

    recommendations = []

    if not top_risks:
        return [
            {
                "titulo": "Preservar arquitectura actual",
                "detalle": "No se detectan zonas de fricción prioritaria por encima del umbral. La recomendación es preservar coherencia, vigilar desviaciones y evitar sobreintervención."
            }
        ]

    for idx in top_risks:
        p_code, p_title, _, _ = PODERES_INFO[idx]
        power_label = format_power_label(p_code)

        m3_val = float(avgm3[idx])
        a_val = float(avga[idx])
        p_val = float(potency[idx])
        l_val = float(leak[idx])

        if m3_val < 4.0 and a_val < 4.0:
            rec = {
                "titulo": f"Intervenir {power_label} en estructura y autoridad",
                "detalle": f"{power_label} muestra fricción alta ({l_val:.2f}) con debilidad simultánea de estructura y autoridad. La prioridad es reforzar M3 y A para consolidar forma y legitimidad."
            }
        elif m3_val < 4.0:
            rec = {
                "titulo": f"Reforzar estructura en {power_label}",
                "detalle": f"{power_label} concentra potencia relevante ({p_val:.1f}) pero no dispone de estructura suficiente. La prioridad es reforzar M3 para convertir capacidad en estabilidad."
            }
        elif a_val < 4.0:
            rec = {
                "titulo": f"Reforzar autoridad en {power_label}",
                "detalle": f"{power_label} opera con fricción alta ({l_val:.2f}) y validación insuficiente. La prioridad es reforzar A para sostener legitimidad y mando."
            }
        else:
            rec = {
                "titulo": f"Reducir fricción interna en {power_label}",
                "detalle": f"{power_label} tiene potencia significativa ({p_val:.1f}) pero presenta fuga estructural. La prioridad es alinear materialidades y autoridad para reducir pérdida de eficiencia."
            }

        recommendations.append(rec)

    return recommendations


def get_benchmark_profile(benchmark_name):
    if benchmark_name == "Ideal estable":
        return np.array([72, 72, 74, 71, 76, 73, 72, 72, 71, 72], dtype=float)

    if benchmark_name == "Crecimiento agresivo":
        return np.array([68, 70, 78, 72, 70, 80, 74, 76, 73, 75], dtype=float)

    if benchmark_name == "Turnaround / crisis":
        return np.array([62, 65, 68, 66, 78, 72, 64, 67, 66, 68], dtype=float)

    return np.array([70, 70, 70, 70, 70, 70, 70, 70, 70, 70], dtype=float)


def build_benchmark_table(report, benchmark_name):
    current = np.asarray(report["potency100"], dtype=float)
    benchmark = get_benchmark_profile(benchmark_name)
    gap = benchmark - current

    priorities = []
    for g in gap:
        if g >= 15:
            priorities.append("Brecha crítica")
        elif g >= 8:
            priorities.append("Brecha relevante")
        elif g >= 3:
            priorities.append("Ajuste moderado")
        elif g <= -8:
            priorities.append("Sobredesarrollo relativo")
        else:
            priorities.append("En rango")

    df = pd.DataFrame({
        "Poder": [p[0] for p in PODERES_INFO],
        "Nombre": [p[1] for p in PODERES_INFO],
        "Potencia actual": np.round(current, 1),
        "Benchmark": np.round(benchmark, 1),
        "Gap": np.round(gap, 1),
        "Prioridad": priorities
    })

    return df


def build_board_summary(
    report,
    integrity,
    friction,
    archetype_name,
    benchmark_df,
    future_scenario,
    evidence_df,
    *,
    acted_power: str | None = None,
    action_label: str | None = None,
    archetype_universal_name: str | None = None,
    archetype_universal_id: str | None = None,
):
    top_risks = report["top3_risks_labels"]
    stability_base = get_stability_focal_poder_code(report, archetype_name)

    top_gap_df = benchmark_df.sort_values("Gap", ascending=False)
    positive_gaps = top_gap_df[top_gap_df["Gap"] > 0].head(3)

    future_potency = np.asarray(future_scenario["future_potency"], dtype=float)
    current_potency = np.asarray(report["potency100"], dtype=float)
    future_delta = future_potency - current_potency

    strongest_future_idx = int(np.argmax(future_delta))
    weakest_future_idx = int(np.argmin(future_delta))

    if strongest_future_idx == weakest_future_idx:
        sorted_worst = np.argsort(future_delta)
        for idx in sorted_worst:
            if int(idx) != strongest_future_idx:
                weakest_future_idx = int(idx)
                break

    avg_confidence = float(np.mean(evidence_df["Confianza"]))

    if archetype_name == "Ignición":
        _ip = (report.get("ingest_disclosure") or {}).get("offering_prospectus_context")
        if _ip:
            system_msg = (
                "Prospecto / S-1: narrativa y producto pueden ir por delante del gobierno institucional real; "
                "prioriza cumplimiento y control sin confundir el documento SEC con operación ya cotizada madura."
            )
        else:
            system_msg = (
                "Etapa germinal: alto impulso en estrategia y tecnología con institución aún en formación; "
                "refuerza gobierno y cumplimiento sin asfixiar la expansión."
            )
    elif integrity >= 78 and friction <= 16:
        system_msg = "Arquitectura global sólida; fricción acotada."
    elif integrity >= 58 and friction <= 38:
        system_msg = (
            "Capacidad estructural activa; los frentes abiertos exigen intervención selectiva."
        )
    else:
        system_msg = (
            "Vulnerabilidad estructural manifiesta: prioriza contención e intervención focalizada."
        )

    # Una sola etiqueta de arquetipo en dirección: clasificación AKXOM (10 universales) si existe.
    _au = (archetype_universal_name or "").strip()
    if _au:
        archetype_line = f"Arquetipo dominante: {_au}."
    elif archetype_name == "Tragedia distribuida":
        archetype_line = (
            "Arquetipo: Tragedia distribuida — tensión repartida sin culpable único; "
            "predominan inercia, erosión coordinada y vaciamiento progresivo de eficacia."
        )
    elif archetype_name == "Ignición":
        if (report.get("ingest_disclosure") or {}).get("offering_prospectus_context"):
            archetype_line = (
                "Arquetipo: Ignición (oferta pública) — P8/P9 altos con P5 capado por escepticismo prospecto; "
                "el riesgo es escala y narrativa antes que gobierno de sociedad cotizada consolidada."
            )
        else:
            archetype_line = (
                "Arquetipo: Ignición (estructura germinal) — expansión acelerada con P5 rezagado; "
                "el riesgo principal es escala sin contrapeso institucional, no colapso inmediato."
            )
    else:
        archetype_line = f"Arquetipo dominante: {archetype_name}."

    if len(positive_gaps) > 0:
        gap_text = ", ".join(
            [f"{row['Poder']} ({row['Gap']:.1f})" for _, row in positive_gaps.iterrows()]
        )
        benchmark_msg = f"Mayores brechas vs benchmark: {gap_text}."
    else:
        benchmark_msg = "Sin brechas positivas relevantes frente al benchmark elegido."

    future_up = PODERES_INFO[strongest_future_idx][0]
    future_down = PODERES_INFO[weakest_future_idx][0]

    future_msg = (
        f"Proyección a 6 meses: mayor tracción en {future_up}; "
        f"deterioro relativo máximo en {future_down}."
    )

    no_intervention = not action_label or action_label in (
        "Sin intervención necesaria",
        "Sin intervención recomendada",
    )

    if top_risks and acted_power and not no_intervention:
        risk_fmt = format_power_label(str(top_risks[0]))
        lever_fmt = format_power_label(str(acted_power))
        if str(top_risks[0]) == str(acted_power):
            intervention_msg = (
                f"Riesgo crítico detectado en {risk_fmt}. "
                f"La simulación prioriza el mismo nodo para maximizar la mejora sistémica (riesgo y palanca alineados)."
            )
        else:
            intervention_msg = (
                f"Riesgo crítico detectado en {risk_fmt}. "
                f"Se recomienda intervención prioritaria en {lever_fmt} para estabilizar el sistema global "
                f"(palanca de impacto entre los nodos de mayor riesgo)."
            )
    elif top_risks:
        intervention_msg = f"Prioridad táctica: intervenir primero {format_power_label(str(top_risks[0]))}."
    else:
        intervention_msg = (
            "Sin frente crítico único; preserva coherencia y vigila deriva operativa."
        )

    stability_msg = stability_operativa_sentence(
        stability_base,
        executive_integrity=float(integrity),
        archetype_name=str(archetype_name),
    )

    if avg_confidence >= 70:
        confidence_msg = "Confianza analítica del diagnóstico: alta."
    elif avg_confidence >= 55:
        confidence_msg = "Confianza analítica del diagnóstico: media."
    else:
        confidence_msg = "Confianza analítica baja; valida evidencia antes de ejecutar."

    action_lines = archetype_action_block_lines(archetype_universal_id)

    summary_lines = [
        system_msg,
        archetype_line,
        *action_lines,
        benchmark_msg,
        future_msg,
        intervention_msg,
        stability_msg,
        confidence_msg,
    ]

    return summary_lines


def build_ceo_insights(
    report,
    benchmark_df,
    future_scenario,
    contradictions,
    *,
    executive_integrity: float | None = None,
    archetype_name: str | None = None,
):
    potency = report["potency100"]
    leak = report["leakscore"]

    top_risks = report["top3_risks_labels"]
    low_risks = report["bottom3_lowrisk_labels"]

    risk_dominant = top_risks[0] if top_risks else "Sin riesgo prioritario"

    if (archetype_name or "").strip() == "Ignición" and str(risk_dominant) == "P5":
        core_problem = (
            "La organización ha escalado capacidad técnica y tracción más rápido que su capacidad institucional para ordenarlas. "
            "El problema no es falta de potencia, sino falta de estructura para gobernarla con claridad."
        )
    elif top_risks:
        core_problem = (
            f"La fricción estructural máxima opera en {top_risks[0]}: "
            "la arquitectura pierde coherencia operativa en ese nodo."
        )
    else:
        core_problem = (
            "Sin fricción estructural dominante: el sistema conserva coherencia operativa relativa."
        )

    benchmark_sorted = benchmark_df.sort_values("Gap", ascending=False)
    positive_gap_df = benchmark_sorted[benchmark_sorted["Gap"] > 0]

    if (archetype_name or "").strip() == "Ignición":
        if str(risk_dominant) == "P5":
            decision_priority = (
                f"Prioridad ejecutiva: {format_power_label('P5')} — construir capacidad de gobierno antes de seguir escalando "
                "la potencia tecnológica y comercial al mismo ritmo."
            )
        else:
            decision_priority = (
                f"Prioridad ejecutiva: {format_power_label('P5')} — construir institución (gobernanza, cumplimiento y proceso) "
                "como palanca de escala; cerrar brechas vs benchmark en paralelo, sin confundir producto con madurez de sociedad."
            )
    elif len(positive_gap_df) > 0:
        lever_power = positive_gap_df.iloc[0]["Poder"]
        decision_priority = (
            f"Prioridad ejecutiva: {format_power_label(lever_power)} — "
            "mayor brecha frente al benchmark estructural."
        )
    else:
        decision_priority = (
            "Prioridad ejecutiva: preservar la arquitectura actual y frenar degradación progresiva."
        )

    current_mean = float(np.mean(potency))
    future_mean = float(np.mean(future_scenario["future_potency"]))
    delta_mean = future_mean - current_mean

    if delta_mean <= -4:
        cost_of_inaction = "Si no se interviene, el sistema proyecta deterioro estructural significativo en los próximos meses."
    elif delta_mean <= -1:
        cost_of_inaction = "Si no se interviene, el sistema muestra señales de desgaste estructural moderado."
    else:
        cost_of_inaction = "El sistema proyecta estabilidad relativa si no se producen shocks externos relevantes."

    if (archetype_name or "").strip() == "Ignición" and str(risk_dominant) == "P5":
        cost_of_inaction = (
            "Si no se refuerza la arquitectura institucional, la expansión puede convertir fortaleza técnica en desgaste operativo, "
            "decisiones lentas y pérdida progresiva de control sobre el crecimiento."
        )
    elif (archetype_name or "").strip() == "Ignición" and delta_mean > -1:
        cost_of_inaction = (
            "Sin reforzar P5 institucional, la escala y la narrativa pueden adelantarse al gobierno real del sistema."
        )

    focal = get_stability_focal_poder_code(report, archetype_name)
    structural_asset = stability_operativa_sentence(
        focal,
        executive_integrity=executive_integrity,
        archetype_name=archetype_name,
    )

    if contradictions:
        first_contradiction = contradictions[0]
        contradiction_msg = f"Existe una contradicción relevante en {format_power_label(first_contradiction['poder'])}, donde la estructura y la práctica organizativa están desalineadas."
    else:
        contradiction_msg = "No se detectan contradicciones estructurales críticas."

    return {
        "core_problem": core_problem,
        "decision_priority": decision_priority,
        "cost_of_inaction": cost_of_inaction,
        "structural_asset": structural_asset,
        "critical_contradiction": contradiction_msg
    }


def build_intervention_strategies(
    report,
    benchmark_df,
    future_scenario,
    contradictions,
    *,
    executive_integrity: float | None = None,
    archetype_name: str | None = None,
):
    top_risks = report["top3_risks_labels"]
    stability_base = get_stability_focal_poder_code(report, archetype_name)

    risk_focus = top_risks[0] if top_risks else "núcleo estructural del sistema"
    support_base = stability_base

    benchmark_sorted = benchmark_df.sort_values("Gap", ascending=False)
    positive_gap_df = benchmark_sorted[benchmark_sorted["Gap"] > 0]

    if len(positive_gap_df) > 0:
        gap_focus = positive_gap_df.iloc[0]["Poder"]
    else:
        gap_focus = support_base

    current_mean = float(np.mean(report["potency100"]))
    future_mean = float(np.mean(future_scenario["future_potency"]))
    delta_mean = future_mean - current_mean

    contradiction_total = sum(len(item["issues"]) for item in contradictions)

    if delta_mean <= -3:
        impact_1 = "Reduce deterioro probable a corto plazo."
        impact_2 = "Mejora estabilidad si se sostiene la intervención."
        impact_3 = "Puede transformar el equilibrio si la organización acepta el cambio."
    else:
        impact_1 = "Contiene fugas y preserva estabilidad relativa."
        impact_2 = "Refuerza coherencia interna y capacidad de mando."
        impact_3 = "Abre margen de ventaja estructural si se ejecuta con disciplina."

    if contradiction_total >= 5:
        risk_1 = "Puede ser insuficiente si las contradicciones ya son sistémicas."
        risk_2 = "Exige disciplina interna y tiempo de consolidación."
        risk_3 = "Puede generar resistencia política y fricción interna."
    else:
        risk_1 = "Puede quedarse corta si el deterioro acelera."
        risk_2 = "Puede ralentizar la operación en el corto plazo."
        risk_3 = "Puede sobrecargar al sistema si no hay foco real."

    support_lab = format_power_label(str(support_base))
    if _relative_fragility_stability_narrative(executive_integrity, archetype_name):
        anchor_phrase = (
            f"contener fricción y anclar el margen relativo donde el tensor marca menor fragilidad ({support_lab})"
        )
    else:
        anchor_phrase = f"contener fricción y proteger la base estable en {support_lab}"

    strategies = [
        {
            "title": "Contención inmediata",
            "focus": risk_focus,
            "logic": f"Reducir fuga estructural de forma rápida empezando por {risk_focus}.",
            "action": f"La prioridad ejecutiva inmediata es actuar sobre {risk_focus}, {anchor_phrase}.",
            "risk": risk_1,
            "impact": impact_1
        },
        {
            "title": "Refuerzo estructural",
            "focus": gap_focus,
            "logic": f"Cerrar la mayor brecha frente al benchmark, concentrada en {gap_focus}.",
            "action": f"Reforzar estructura, autoridad y coordinación en {gap_focus} para acercar el sistema a la arquitectura objetivo.",
            "risk": risk_2,
            "impact": impact_2
        },
        {
            "title": "Reordenación ofensiva",
            "focus": support_base,
            "logic": (
                f"Usar el nodo de menor fragilidad relativa ({support_lab}) como palanca para reordenar el resto del sistema."
                if _relative_fragility_stability_narrative(executive_integrity, archetype_name)
                else f"Usar el poder más estable ({support_lab}) como palanca para reordenar el resto del sistema."
            ),
            "action": (
                f"Articular capacidad desde {support_lab} hacia los poderes con mayor contradicción y fuga, "
                f"sin asumir que {support_lab} dispone de colchón estructural amplio."
                if _relative_fragility_stability_narrative(executive_integrity, archetype_name)
                else f"Expandir capacidad desde {support_lab} y redistribuir coherencia hacia los poderes con mayor contradicción y fuga."
            ),
            "risk": risk_3,
            "impact": impact_3
        }
    ]

    return strategies


def build_executive_decision_panel(
    report,
    benchmark_df,
    future_scenario,
    recommendations,
    contradictions,
    *,
    executive_integrity: float | None = None,
    archetype_name: str | None = None,
):
    top_risks = report["top3_risks_labels"]

    risk_dominant = top_risks[0] if top_risks else "Sin riesgo prioritario"
    stability_base = get_stability_focal_poder_code(report, archetype_name)

    benchmark_sorted = benchmark_df.sort_values("Gap", ascending=False)
    positive_gap_df = benchmark_sorted[benchmark_sorted["Gap"] > 0]

    if (archetype_name or "").strip() == "Ignición" and str(risk_dominant) == "P5":
        lever_power = "P5"
        lever_msg = (
            f"{format_power_label('P5')} concentra la brecha que más condiciona la escala. "
            "La organización puede ejecutar mucho más de lo que hoy puede ordenar con claridad."
        )
    elif len(positive_gap_df) > 0:
        lever_power = positive_gap_df.iloc[0]["Poder"]
        lever_gap = float(positive_gap_df.iloc[0]["Gap"])
        lever_msg = f"{lever_power} presenta la mayor brecha frente al benchmark (+{lever_gap:.1f})."
    else:
        lever_power = stability_base
        sl = format_power_label(str(stability_base))
        if _relative_fragility_stability_narrative(executive_integrity, archetype_name):
            lever_msg = (
                f"{sl} muestra la menor fragilidad tensorial relativa en este contexto; "
                f"no equivale a una base de estabilidad consolidada ni a institución cotizada madura."
            )
        else:
            lever_msg = f"{sl} actúa como principal base de estabilidad relativa."

    if (archetype_name or "").strip() == "Ignición" and str(risk_dominant) != "P5":
        lever_msg += (
            f" Estado de ignición: priorizar también {format_power_label('P5')} (construcción institucional) "
            "además del cierre de brechas frente a la base de referencia."
        )

    if recommendations:
        intervention_title = recommendations[0]["titulo"]
        intervention_detail = recommendations[0]["detalle"]
    else:
        intervention_title = "Preservar arquitectura actual"
        intervention_detail = "No se detectan frentes críticos por encima de umbral."

    current_mean = float(np.mean(report["potency100"]))
    future_mean = float(np.mean(future_scenario["future_potency"]))
    delta_mean = future_mean - current_mean

    contradiction_total = sum(len(item["issues"]) for item in contradictions)

    if (archetype_name or "").strip() == "Ignición" and str(risk_dominant) == "P5":
        impact_msg = (
            "Si se interviene a tiempo, la organización puede convertir crecimiento rápido en escala gobernable "
            "sin degradar la potencia que hoy la hace valiosa."
        )
    elif delta_mean >= 4:
        impact_msg = "La estructura proyecta una mejora material de potencia en el horizonte estimado."
    elif delta_mean >= 1:
        impact_msg = "La estructura proyecta una mejora moderada de potencia en el horizonte estimado."
    elif delta_mean <= -4:
        impact_msg = "La estructura proyecta deterioro significativo si no se interviene."
    elif delta_mean <= -1:
        impact_msg = "La estructura proyecta desgaste moderado si no se corrigen fugas."
    else:
        impact_msg = "La estructura proyecta estabilidad relativa, con mejoras limitadas."

    if contradiction_total > 0:
        impact_msg += f" Se detectan {contradiction_total} contradicciones estructurales activas."

    opportunity_note = ""
    _ign_tail = (
        f"Prioridad Ignición: {format_power_label('P5')} (construcción institucional) es palanca central "
        "aunque la fricción global sea baja; no sustituye la simulación sobre el riesgo dominante."
    )
    if (archetype_name or "").strip() == "Ignición":
        _chunks: list[str] = []
        if len(benchmark_df) > 0:
            p5_rows = benchmark_df[benchmark_df["Poder"] == "P5"]
            if not p5_rows.empty:
                p5_gap = float(p5_rows.iloc[0]["Gap"])
                if p5_gap >= GERMINAL_P5_BENCHMARK_GAP_NOTE_MIN:
                    _chunks.append(
                        "Potencial de futuro: el tensor lee alto tiro en P8/P9 con institución (P5) aún por construir; "
                        "cerrar brecha en P5 amplía opcionalidad. No implica que el riesgo operativo o de gobierno haya desaparecido."
                    )
        _chunks.append(_ign_tail)
        opportunity_note = " ".join(_chunks)

    return {
        "risk_dominant": risk_dominant,
        "lever_power": lever_power,
        "lever_msg": lever_msg,
        "intervention_title": intervention_title,
        "intervention_detail": intervention_detail,
        "impact_msg": impact_msg,
        "opportunity_note": opportunity_note,
    }
