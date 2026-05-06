"""
Doctrina operativa por arquetipo universal (AKXOM).

Capa de decisión encima del clasificador: no modifica umbrales ni `identify_archetype`.
"""

from __future__ import annotations

# Claves fijas del bloque «Motor de acción» (informe dirección).
ACTION_KEYS = ("doctrina", "error", "palanca")

_ARCHETYPE_ACTIONS: dict[str, dict[str, str]] = {
    "arquitectura_soberana": {
        "doctrina": "Mantener equilibrio y control del sistema completo.",
        "error": "Sobreexpandirse o perder coherencia interna.",
        "palanca": "P7 (político), P8 (estratégico).",
    },
    "vanguardia_disruptiva": {
        "doctrina": "Convertir innovación en estructura antes de colapsar.",
        "error": "Escalar sin institucionalizar.",
        "palanca": "P5 (institucional), M3.",
    },
    "gigante_de_barro": {
        "doctrina": "Construir centro de mando real.",
        "error": "Confiar en tamaño o recursos.",
        "palanca": "P7 (político), P5 (institucional).",
    },
    "zombi_estrategico": {
        "doctrina": "Reconectar con el futuro o desmantelar.",
        "error": "Optimizar lo existente.",
        "palanca": "P8 (estratégico), P9 (tecnológico).",
    },
    "leviatan_ciego": {
        "doctrina": "Reintroducir voluntad estratégica.",
        "error": "Añadir más norma.",
        "palanca": "P8 (estratégico).",
    },
    "estructura_fosilizada": {
        "doctrina": "Romper rigidez cultural.",
        "error": "Proteger tradición.",
        "palanca": "P9 (tecnológico), P10 (cultural).",
    },
    "feudo_carismatico": {
        "doctrina": "Transferir poder del líder a la estructura.",
        "error": "Reforzar dependencia personal.",
        "palanca": "P5 (institucional), M3.",
    },
    "organismo_de_asalto": {
        "doctrina": "Sostener legitimidad antes de reacción externa.",
        "error": "Ignorar impacto social/regulatorio.",
        "palanca": "P10 (cultural), P7 (político).",
    },
    "fortaleza_sitiada": {
        "doctrina": "Abrir canales externos.",
        "error": "Optimizar el interior.",
        "palanca": "P3 (comunicativo), P4 (social).",
    },
    "resonancia_fantasma": {
        "doctrina": "Reconstruir capacidad real.",
        "error": "Vivir de la marca.",
        "palanca": "P9 (tecnológico), P8 (estratégico).",
    },
}

_EMPTY: dict[str, str] = {"doctrina": "", "error": "", "palanca": ""}


def _normalize_archetype_id(raw: str | None) -> str | None:
    if raw is None:
        return None
    s = str(raw).strip().lower()
    if not s:
        return None
    return s.replace("-", "_").replace(" ", "_")


def get_archetype_action(archetype: str | None) -> dict[str, str]:
    """
    Devuelve doctrina, error crítico y palanca estructural para el id universal (p. ej. `fortaleza_sitiada`).
    Si el id no está catalogado, las tres cadenas van vacías (misma forma útil para tests/UI).
    """
    key = _normalize_archetype_id(archetype)
    if not key:
        return dict(_EMPTY)
    row = _ARCHETYPE_ACTIONS.get(key)
    if not row:
        return dict(_EMPTY)
    return {k: str(row.get(k) or "") for k in ACTION_KEYS}


def archetype_action_block_lines(archetype_id: str | None) -> list[str]:
    """
    Líneas listas para `board_summary_lines`: etiquetas en mayúsculas y textos en líneas separadas.
    Lista vacía si no hay doctrina definida para ese id.
    """
    act = get_archetype_action(archetype_id)
    if not any(str(act.get(k) or "").strip() for k in ACTION_KEYS):
        return []
    return [
        "DOCTRINA OPERATIVA",
        act["doctrina"].strip(),
        "ERROR CRÍTICO",
        act["error"].strip(),
        "PALANCA ESTRUCTURAL",
        act["palanca"].strip(),
    ]
