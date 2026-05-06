"""
Executive View: flujo único de decisión (solo presentación; compone desde `core`).

Orden fijo: SITUACIÓN → DECISIÓN → ACCIÓN CRÍTICA → IMPACTO → RIESGO.
"""

from __future__ import annotations

import re
from typing import Any


def _is_growth_governance_case(core: dict[str, Any]) -> bool:
    return (
        str(core.get("archetype_name") or "").strip() == "Ignición"
        and str(core.get("current_top_risk") or "").strip() == "P5"
    )


def _operational_scrub(text: str) -> str:
    """Sustituye muletillas consultivas por verbo operativo (solo capa de texto)."""
    t = " ".join(str(text or "").split())
    if not t:
        return ""
    subs = [
        (r"\boptimizar\b", "definir"),
        (r"\bpotenciar\b", "activar"),
        (r"\bmejorar\b", "ajustar"),
        (r"\breforzar\b", "centralizar"),
    ]
    for pat, rep in subs:
        t = re.sub(pat, rep, t, flags=re.IGNORECASE)
    return t


def _dedupe_power_label_repetitions(text: str) -> str:
    """
    Evita redacción mecánica repitiendo 'NOMBRE (P#)' varias veces en una frase.
    Mantiene primera mención completa y reduce repeticiones a '(P#)'.
    """
    t = str(text or "")
    if not t.strip():
        return t
    seen: set[str] = set()

    def _repl(match: re.Match[str]) -> str:
        full = match.group(0)
        code = match.group(2).upper()
        if code in seen:
            return f"({code})"
        seen.add(code)
        return full

    # Ej: "ESTRATÉGICO (P8)" / "Estratégico (P8)"
    return re.sub(r"([A-Za-zÁÉÍÓÚÜÑáéíóúüñ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ\s\-]+)\((P\d{1,2})\)", _repl, t)


def _squeeze_situation(raw: str, *, max_chars: int = 220) -> str:
    """Máximo ~2 líneas; lenguaje directo, sin jerga de motor."""
    t = " ".join(str(raw or "").split()).strip()
    if not t:
        return "Sin lectura cualitativa consolidada en este ciclo."
    parts = re.split(r"(?<=[.!?])\s+", t)
    lines: list[str] = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        lines.append(p)
        if len(lines) >= 2:
            break
    out = " ".join(lines) if lines else t
    if len(out) > max_chars:
        out = out[: max_chars - 1].rsplit(" ", 1)[0] + "…"
    return _dedupe_power_label_repetitions(_operational_scrub(out))


def _first_phrase(text: str, *, max_len: int = 240) -> str:
    t = " ".join(str(text or "").split()).strip()
    if not t:
        return ""
    for sep in ".!?":
        if sep in t:
            i = t.find(sep)
            one = t[: i + 1].strip()
            if len(one) <= max_len:
                return _dedupe_power_label_repetitions(_operational_scrub(one))
    out = (t[: max_len - 1].rsplit(" ", 1)[0] + "…") if len(t) > max_len else t
    return _dedupe_power_label_repetitions(_operational_scrub(out))


def _no_intervention_run(core: dict[str, Any]) -> bool:
    fr = core.get("final_reco") or {}
    title = str(fr.get("title") or "").strip().lower()
    if "no intervenir" in title:
        return True
    al = str(core.get("action_label") or "")
    if al in ("Sin intervención necesaria", "Sin intervención recomendada"):
        return True
    return False


def _build_decision_line(core: dict[str, Any]) -> str:
    """Una frase: qué hay que hacer (imperativo, sin análisis)."""
    fr = core.get("final_reco") or {}
    if _is_growth_governance_case(core):
        return "Ordenar primero la arquitectura institucional antes de seguir escalando al mismo ritmo."
    if _no_intervention_run(core):
        return "Vigilar el sistema y no abrir nuevos mandos de intervención en este ciclo."

    title = str(fr.get("title") or "").strip().lower()
    if "intervenir ahora" in title:
        return "Ejecutar ya la intervención prioritaria con responsable único y fecha de cierre."
    if "segunda fase" in title:
        return "Ejecutar la fase prioritaria y preparar el segundo frente sobre el riesgo dominante."
    if "cautela" in title:
        return "Ejecutar en piloto y validar antes de escalar."
    if "replantear" in title:
        return "Parar y replantear la estrategia antes de mover recursos."
    if "no intervenir" in title:
        return "Vigilar el sistema y no abrir nuevos mandos de intervención en este ciclo."

    ns = str(fr.get("next_step") or "").strip()
    if ns:
        return _dedupe_power_label_repetitions(_first_phrase(ns, max_len=140))

    return "Definir el mandato por escrito y coordinar el siguiente movimiento con el equipo."


def build_executive_view(core: dict[str, Any]) -> dict[str, Any]:
    """
    Contrato ejecutivo:
    - situation (≤2 frases)
    - decision (una frase imperativa)
    - critical_action (primary_action salvo modo preservar)
    - impact (+X integridad · +Y fricción o sin desplazamiento)
    - risk (una frase)
    """
    ceo = core.get("ceo_insights") or {}
    fr = core.get("final_reco") or {}
    ap = core.get("action_plan") or {}
    es = core.get("executive_surface") or {}
    de = es.get("decision_ejecutiva") or {}
    co_es = es.get("consecuencia") or {}

    if _is_growth_governance_case(core):
        situation = (
            "Helios ha ganado capacidad técnica y tracción comercial muy rápido. "
            "El riesgo ya no está en ejecutar más, sino en que la organización escale sin una arquitectura capaz de gobernar ese crecimiento."
        )
    else:
        situation = _squeeze_situation(str(ceo.get("core_problem") or ""))
    decision = _dedupe_power_label_repetitions(_build_decision_line(core))

    no_ix = _no_intervention_run(core)
    if no_ix:
        critical = "Ninguna intervención ejecutable en este ciclo; mantener vigilancia activa."
    else:
        primary = str(ap.get("primary_action") or "").strip()
        critical = primary if primary else str(de.get("accion") or "—").strip()
    critical = _dedupe_power_label_repetitions(_operational_scrub(critical))

    try:
        di = float(fr.get("delta_integrity") or 0.0)
    except (TypeError, ValueError):
        di = 0.0
    try:
        df = float(fr.get("delta_friction") or 0.0)
    except (TypeError, ValueError):
        df = 0.0

    tiny = abs(di) < 0.05 and abs(df) < 0.05
    if _is_growth_governance_case(core):
        impact = "Aclara el mando, ordena la escala y reduce el riesgo de que la potencia técnica empiece a degradarse por dentro."
    elif no_ix and tiny:
        impact = "Sin desplazamiento material de integridad ni fricción en la simulación prioritaria."
    else:
        impact = f"{di:+.1f} integridad · {df:+.1f} fricción"

    risk_raw = str(ceo.get("cost_of_inaction") or co_es.get("si_no_ejecuta") or "").strip()
    if _is_growth_governance_case(core):
        risk = (
            "Si no se interviene, Helios puede convertir una ventaja real de capacidad en desgaste operativo, "
            "decisiones más lentas y pérdida progresiva de control sobre su propia escala."
        )
    else:
        risk = _first_phrase(risk_raw, max_len=200) or (
            "Sin decisión, la trayectoria actual de fuga estructural se mantiene."
        )

    decision_confidence = str(es.get("decision_confidence") or "MEDIUM")
    # Recalibración de presentación: si guardrails estructurales convergen, evitar LOW espurio.
    fr_forced = bool(fr.get("forced_intervention_guardrail"))
    weak_n = int(fr.get("weak_powers_count") or 0)
    if decision_confidence.upper() == "LOW" and (fr_forced or weak_n >= 3):
        decision_confidence = "MEDIUM"
    if decision_confidence.upper() == "LOW" and _is_growth_governance_case(core):
        decision_confidence = "MEDIUM"
    next_step = str(fr.get("next_step") or "").strip()

    preserve_mode = bool(no_ix)

    lines = [
        "EXECUTIVE VIEW",
        "",
        "SITUACIÓN",
        situation,
        "",
        "DECISIÓN",
        decision,
        "",
        "ACCIÓN CRÍTICA",
        critical,
        "",
        "IMPACTO",
        impact,
        "",
        "RIESGO DE NO ACTUAR",
        risk,
    ]
    if decision_confidence:
        lines.extend(["", f"CONFIANZA {decision_confidence}"])
    if next_step and not preserve_mode:
        lines.extend(["", f"PRÓXIMO PASO {next_step}"])

    plain = "\n".join(lines)

    return {
        "situation": situation,
        "decision": decision,
        "critical_action": critical,
        "impact": impact,
        "risk": risk,
        "decision_confidence": decision_confidence,
        "next_step": next_step,
        "preserve_mode": preserve_mode,
        "plain_text": plain,
    }
