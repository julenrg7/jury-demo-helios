"""
Plan de acción estructural determinista (sin LLM).

Orden operativa: una acción crítica + hasta tres de soporte; lenguaje directo (verbos de mando).
No toca motor ni métricas.
"""

from __future__ import annotations

import re
from typing import Any

from archetype_actions import get_archetype_action
from labels import POWER_LABELS, format_power_label

# Verbos de mando preferidos (inicio de frase o cerca del inicio)
_OP_VERBS = frozenset(
    {
        "centralizar",
        "eliminar",
        "reasignar",
        "coordinar",
        "bloquear",
        "alinear",
        "congelar",
        "cortar",
        "suspender",
        "fijar",
        "designar",
        "publicar",
        "reducir",
        "abrir",
        "separar",
        "documentar",
        "auditar",
        "recortar",
    }
)

# Subcadenas prohibidas en líneas de acción (minúsculas para búsqueda)
_BANNED = ("mejorar ", "mejorar.", "optimizar", "reforzar", "potenciar ")


def _normalize_p(code: str | None) -> str | None:
    if code is None:
        return None
    s = str(code).strip().upper()
    if re.match(r"^P(10|[1-9])$", s) and s in POWER_LABELS:
        return s
    if "P" in s:
        m = re.search(r"P(10|[1-9])", s)
        if m:
            cand = f"P{m.group(1)}"
            if cand in POWER_LABELS:
                return cand
    return None


def _labels(risk: str | None, lev: str | None) -> tuple[str, str]:
    r = _normalize_p(risk)
    l = _normalize_p(lev)
    risk_s = format_power_label(r) if r else "el nodo en tensión"
    lev_s = format_power_label(l) if l else "la palanca prioritaria"
    return risk_s, lev_s


def _clean_banned(text: str) -> str:
    """Parche defensivo si una plantilla legacy contuviera términos consultivos."""
    t = text.strip()
    low = t.lower()
    for b in _BANNED:
        if b.strip() in low:
            t = re.sub(b, " ejecutar ", t, flags=re.IGNORECASE, count=1)
            break
    return t.strip()


def _collapse_repeated_power_phrases(text: str) -> str:
    t = " ".join(str(text or "").split())
    t = re.sub(r"\((P\d{1,2})\)\s+\(\1\)", r"(\1)", t)
    t = re.sub(
        r"en ([A-ZÁÉÍÓÚÜÑa-záéíóúüñ\s\-]+\(P\d{1,2}\)) con mandato explícito sobre el frente \1",
        r"en \1 con mandato explícito sobre ese frente",
        t,
    )
    t = re.sub(
        r"en ([A-ZÁÉÍÓÚÜÑa-záéíóúüñ\s\-]+\(P\d{1,2}\)) hasta que \1 absorba",
        r"en \1 hasta absorber",
        t,
    )
    return t.strip()


def _score_candidate(line: str, risk_s: str, lev_s: str, risk_code: str | None) -> int:
    """Mayor puntuación = más directo sobre el nodo de riesgo (prioridad para ACCIÓN CRÍTICA)."""
    low = line.lower()
    score = 0
    for b in _BANNED:
        if b.strip() in low or b in low:
            score -= 200
    if risk_s and risk_s in line:
        score += 40
    if risk_code and f"({risk_code})" in line:
        score += 25
    if risk_code and risk_code in line:
        score += 15
    first = line.split()
    if first:
        w0 = re.sub(r"[^a-záéíóúñ]", "", first[0].lower())
        if w0 in _OP_VERBS:
            score += 12
    # Penalizar líneas que solo hablan de palanca sin riesgo
    if lev_s and lev_s in line and risk_s and risk_s not in line:
        score -= 8
    return score


def _pick_primary_and_support(
    candidates: list[str],
    risk_s: str,
    lev_s: str,
    risk_code: str | None,
) -> tuple[str, list[str]]:
    """Elige la acción crítica entre candidatos; el resto (hasta 3) son soporte."""
    cleaned = [_collapse_repeated_power_phrases(_clean_banned(c)) for c in candidates if str(c).strip()]
    if not cleaned:
        return _collapse_repeated_power_phrases(
            f"Coordinar decisión escrita sobre {risk_s} y {lev_s}."
        ), []
    scored = [(i, _score_candidate(c, risk_s, lev_s, risk_code), c) for i, c in enumerate(cleaned)]
    scored.sort(key=lambda x: (-x[1], x[0]))
    primary = scored[0][2]
    others = [x[2] for x in scored[1:]]
    support: list[str] = []
    for r in others:
        if len(support) >= 3:
            break
        if r.strip() == primary.strip():
            continue
        if len(primary) >= 40 and (primary[:40] in r or r[:40] in primary):
            continue
        support.append(r)
    return primary, support[:3]


# (objective, intervention_kind, [4 plantillas candidatas — se elige crítica por score])
_ARCHETYPE_PLANS: dict[str, tuple[str, str, list[str]]] = {
    "arquitectura_soberana": (
        "Mantener coherencia global sin abrir frentes que descentren el sistema.",
        "contención",
        [
            "Bloquear nuevas iniciativas en {risk} hasta firma de criterio de salida desde {leverage}.",
            "Centralizar el mapa de dependencias entre {risk} y {leverage}; eliminar duplicidades de mando.",
            "Alinear la cadencia quincenal: toda decisión en {risk} pasa visación de {leverage}.",
            "Coordinar un único registro de conflictos abiertos en {risk}; escalar a {leverage} al cruce de umbral.",
        ],
    ),
    "vanguardia_disruptiva": (
        "Institucionalizar lo validado antes de escalar volumen o territorio.",
        "reconstrucción",
        [
            "Reasignar el dueño de proceso en {leverage} con mandato explícito sobre el frente {risk}.",
            "Congelar el escalado en {risk} hasta que {leverage} absorba la operación en checklist escrito.",
            "Centralizar playbooks mínimos en {leverage}; bloquear improvisación en {risk} sin checklist.",
            "Cortar una iniciativa concurrente en {risk} que compita con la palanca {leverage}.",
        ],
    ),
    "gigante_de_barro": (
        "Instaurar centro de mando real: datos, cadencia y responsables.",
        "reconstrucción",
        [
            "Centralizar el tablero semanal de riesgos reales en {risk}; una sola lectura desde {leverage}.",
            "Eliminar capas intermedias entre {risk} y {leverage}; publicar cadena de escalado en un folio.",
            "Bloquear presupuesto simbólico en {leverage} hasta cierre del incidente en {risk}.",
            "Auditar una decisión grande en {risk}: firmas y datos; reasignar correcciones en {leverage}.",
        ],
    ),
    "zombi_estrategico": (
        "Reconectar estructura con futuro útil o recortar lo que consume oxígeno.",
        "reconstrucción",
        [
            "Congelar líneas en {risk} mientras {leverage} publica el norte en una página.",
            "Fijar un solo proyecto vivo en {leverage} con KPI externo; bloquear vetos en {risk} sin alternativa escrita.",
            "Alinear comunicación interna: prioridad de {leverage} frente al estancamiento en {risk}.",
            "Recortar alcance en {risk} si en trimestre no mueve indicador acordado; coordinar con {leverage}.",
        ],
    ),
    "leviatan_ciego": (
        "Reintroducir dirección explícita; menos norma ciega, más criterio publicado.",
        "contención",
        [
            "Suspender nuevas reglas en {risk} hasta objetivo de negocio firmado en {leverage}.",
            "Fijar en {leverage} tres decisiones pendientes sobre {risk} con dueño y fecha.",
            "Eliminar pasos redundantes en un trámite crítico de {risk}; validar cierre con {leverage}.",
            "Publicar línea de prioridades desde {leverage}; bloquear cola paralela en {risk}.",
        ],
    ),
    "estructura_fosilizada": (
        "Romper rigidez con experimentos acotados y criterio de corte.",
        "ofensiva",
        [
            "Fijar experimento de 30 días en {risk} con una métrica; sponsor obligatorio en {leverage}.",
            "Reasignar talento clave entre {risk} y {leverage} en rotación escrita.",
            "Cortar un ritual bloqueante en {risk}; sustituto firmado desde {leverage}.",
            "Centralizar recompensa explícita a quien ejecute cambio en {risk} con visto bueno de {leverage}.",
        ],
    ),
    "feudo_carismatico": (
        "Transferir poder del líder a mecanismos: roles, datos y sucesión.",
        "reconstrucción",
        [
            "Reasignar suplencia formal del rol crítico en {risk}; refrendo institucional en {leverage}.",
            "Separar carisma de decisión: firmas relevantes en {leverage}, no solo en {risk}.",
            "Documentar criterios de decisión en {risk}; auditoría cruzada con {leverage}.",
            "Centralizar mensaje: proceso sobre heroísmo; una sola narrativa desde {leverage} hacia {risk}.",
        ],
    ),
    "organismo_de_asalto": (
        "Sostener legitimidad y límites antes de la reacción externa.",
        "contención",
        [
            "Coordinar mapa de stakeholders externos ligados a {risk}; una ventana de respuesta desde {leverage}.",
            "Bloquear acciones agresivas en {risk} sin checklist legal/comunicación firmado por {leverage}.",
            "Reducir exposición pública en {risk} si no hay narrativa común acordada en {leverage}.",
            "Fijar simulacro de crisis con {risk} como escenario; umbrales de parada en {leverage}.",
        ],
    ),
    "fortaleza_sitiada": (
        "Abrir canales externos; dejar de priorizar solo el interior.",
        "ofensiva",
        [
            "Abrir dos canales externos (cliente/aliado/regulador) bajo mandato de {leverage}; alinear meta de {risk}.",
            "Centralizar métrica de interfaz externa; bloquear solo-métricas internas en {risk} sin contraparte fuera.",
            "Coordinar misión conjunta {risk} y {leverage} con entregable visible fuera del muro.",
            "Eliminar proyecto interno en {risk} que no abra canal externo en el trimestre; validar en {leverage}.",
        ],
    ),
    "resonancia_fantasma": (
        "Reconstruir capacidad operativa real detrás de la imagen.",
        "reconstrucción",
        [
            "Centralizar inventario: promesa vs entrega real en {risk}; cierre de brechas mandado por {leverage}.",
            "Congelar narrativa nueva hasta entregable tangible en {leverage}; bloquear storytelling vacío en {risk}.",
            "Fijar sala semanal sobre {risk} con usuario interno; deuda técnica visible en {leverage}.",
            "Eliminar indicador vanidoso en {risk}; sustituir por throughput validado por {leverage}.",
        ],
    ),
}

_FALLBACK_TEMPLATES: list[str] = [
    "Reasignar autoridad ejecutiva en {risk}: un responsable único con mandato escrito hacia {leverage}.",
    "Bloquear cambios paralelos en {risk} hasta decisión fechada en {leverage}.",
    "Centralizar tres indicadores semanales: uno en {risk}, uno en {leverage}, uno de interfaz.",
    "Documentar criterio de escalado: cuándo {risk} eleva y cuándo {leverage} decide.",
]


def build_action_plan(
    archetype_id: str | None,
    risk_node: str | None,
    leverage_node: str | None,
) -> dict[str, Any]:
    """
    Devuelve objetivo, intervention_kind, primary_action, actions de soporte (≤3), notes, plain_text.

    La acción crítica se elige automáticamente entre cuatro candidatos (énfasis en el nodo de riesgo).
    """
    risk_s, lev_s = _labels(risk_node, leverage_node)
    r_code = _normalize_p(risk_node)
    base = get_archetype_action(archetype_id)
    err = str(base.get("error") or "").strip()
    doc = str(base.get("doctrina") or "").strip()

    key = None
    if archetype_id:
        k = str(archetype_id).strip().lower().replace("-", "_").replace(" ", "_")
        if k in _ARCHETYPE_PLANS:
            key = k

    if key is not None:
        objective, kind, templates = _ARCHETYPE_PLANS[key]
    else:
        objective = "Cerrar la brecha entre frente de riesgo y palanca sin dispersar mandos."
        kind = "contención"
        templates = list(_FALLBACK_TEMPLATES)

    candidates: list[str] = []
    for t in templates[:4]:
        line = t.format(risk=risk_s, leverage=lev_s).strip()
        candidates.append(_clean_banned(line))

    primary_action, support_actions = _pick_primary_and_support(candidates, risk_s, lev_s, r_code)

    notes_parts: list[str] = []
    if doc:
        notes_parts.append(doc)
    if err:
        notes_parts.append(f"No caer en: {err}")
    notes = " ".join(notes_parts).strip() or "Validar mandos y fechas en el próximo ciclo de gobierno."

    out = {
        "objective": objective,
        "intervention_kind": kind,
        "primary_action": primary_action,
        "actions": support_actions,
        "notes": notes,
        "archetype_id": str(archetype_id or "").strip() or None,
        "risk_node": r_code,
        "leverage_node": _normalize_p(leverage_node),
    }
    out["plain_text"] = format_action_plan_plain(out)
    return out


def format_action_plan_plain(plan: dict[str, Any]) -> str:
    """Formato fijo para export / CEO."""
    primary = str(plan.get("primary_action") or "").strip()
    support = plan.get("actions") or []
    notes = str(plan.get("notes") or "").strip()
    lines = [
        "=== PLAN DE ACCIÓN ===",
        "",
        "ACCIÓN CRÍTICA",
        primary,
        "",
        "PLAN DE SOPORTE",
        "",
    ]
    for i, a in enumerate(support[:3], start=1):
        lines.append(f"{i}. {str(a).strip()}")
    lines.append("")
    lines.append(f"NOTA {notes}")
    return "\n".join(lines)
