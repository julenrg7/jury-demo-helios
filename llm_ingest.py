"""
Ingesta vía LLM: texto → **señales** → `signals_to_akxom_json` → tensor → motor → `identify_archetype`.

Opcional: segunda llamada LLM de **desambiguación** entre 2–3 arquetipos candidatos (`NOUMENON_ARCHETYPE_DISAMBIGUATION`).

Requiere: `pip install openai` y `OPENAI_API_KEY` para llamadas al modelo.
Temperatura por defecto 0.1 (`NOUMENON_LLM_TEMPERATURE` opcional).
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Sequence

import numpy as np

from archetype_action_engine import build_action_plan
from causal_chain import build_causal_chain
from engine_akxom import PODERES_INFO, build_empty_tensor, set_power_structured

DEFAULT_LLM_MODEL = os.environ.get("NOUMENON_LLM_MODEL", "gpt-4o-mini")
# Menor temperatura → menos varianza en JSON; override con NOUMENON_LLM_TEMPERATURE si hace falta.
DEFAULT_LLM_TEMPERATURE = float(os.environ.get("NOUMENON_LLM_TEMPERATURE", "0.1"))

# Con una sola señal, se amortigua la desviación respecto al neutro (5 / flows 0) para que ningún
# token aislado fije el arquetipo; con 2+ señales, reglas a plena intensidad.
SINGLE_SIGNAL_DAMPEN = float(os.environ.get("NOUMENON_SIGNAL_SINGLE_DAMPEN", "0.62"))

# Señales estructurales que no deben ser suavizadas por amortiguación ni por floors de equilibrio.
STRONG_SIGNALS: frozenset[str] = frozenset(
    {
        "concentracion_poder",
        "debilidad_generalizada",
        "dependencia_critica",
    }
)

# Catálogo cerrado: solo estas cadenas son válidas en `signals` (el LLM no inventa otras).
KNOWN_SIGNALS: frozenset[str] = frozenset(
    {
        "ingresos_estables",
        "sin_innovacion",
        "burocracia",
        "marca_fuerte",
        "cultura_bloqueante",
        "lider_central",
        "aislamiento_externo",
        "tecnologia_fuerte",
        "estrategia_fuerte",
        "falta_estrategia",
        "dominancia_politica",
        "equilibrio_global",
        "alta_tecnologia",
        "hiper_eficiencia_economica",
        "dependencia_lider",
        "dependencia_critica",
        "legitimidad_historica",
        "ausencia_centro_decision",
        "estructura_fragmentada",
        "bloqueo_regulatorio",
        "presion_externa",
        "innovacion_activa",
        "equilibrio_estructural",
        "operacion_agresiva",
        "falta_gobierno",
        "escala_sin_direccion",
        "concentracion_poder",
        "debilidad_generalizada",
    }
)

# Requisitos semánticos mínimos por arquetipo (guardrail post-clasificación / desambiguación).
ARCHETYPE_REQUIREMENTS: dict[str, dict[str, set[str]]] = {
    "feudo_carismatico": {
        "any_of": {"lider_central", "dependencia_lider"},
        "all_of": set(),
        "none_of": set(),
    },
    "gigante_de_barro": {
        "any_of": {"escala_sin_direccion", "falta_gobierno", "estructura_fragmentada"},
        "all_of": set(),
        "none_of": set(),
    },
    "zombi_estrategico": {
        "any_of": {"sin_innovacion", "falta_estrategia", "ingresos_estables"},
        "all_of": set(),
        "none_of": set(),
    },
}

PROMPT_SIGNALS_TEMPLATE = """Eres un analista estructural del modelo AKXOM OS. Tu tarea es inferir **señales discretas** a partir del texto, pero **obligatoriamente** en dos fases internas.

══════════════════════════════════════════════════════════════════
REGLA OBLIGATORIA
══════════════════════════════════════════════════════════════════

No selecciones `signals` directamente del vocabulario del texto (palabras sueltas, cargas afectivas o etiquetas narrativas). Primero identifica la **estructura del sistema** (qué nodos de poder están fuertes, débiles, en deterioro y en tensión entre sí). Las etiquetas del catálogo son consecuencia de esa estructura, no del léxico literal.

**Disruptiva vs Zombi (regla explícita):** si el texto describe **crecimiento, innovación o expansión** activos, debes preferir `innovacion_activa` (y señales coherentes); **no** uses `sin_innovacion` en ese caso.

**Fortaleza sitiada vs Feudo:** un sistema **cercado** en el perímetro (`aislamiento_externo`: P3/P4 débiles, vínculos externos fríos) no es la misma lectura que un feudo por **figura**. No incluyas `lider_central` ni `dependencia_lider` en el mismo conjunto de señales que `aislamiento_externo`, salvo que el texto plantee **explícitamente** dos tensiones incompatibles y puedas justificarlas en FASE 1.

══════════════════════════════════════════════════════════════════
FASE 1 — Razonamiento estructural (NO va en la salida; hazlo antes de escribir JSON)
══════════════════════════════════════════════════════════════════

En tu razonamiento interno, enumera explícitamente:

0) **Distribución estructural obligatoria**: decide primero si el sistema es:
   - `equilibrado` (sin asimetría clara),
   - `concentrado` (uno/pocos nodos sostienen el sistema; asimetría fuerte),
   - `degradado` (debilidad extendida sin nodo claramente dominante).

   Si es `concentrado`, debes incluir `concentracion_poder` en `signals`.
   Si es `degradado`, debes incluir `debilidad_generalizada` en `signals`.
   Si detectas frases de dependencia extrema (p. ej. «todo depende de una persona», «sin él no funciona», «bloqueo en su ausencia», «no hay estructura/procesos»), debes incluir `dependencia_critica`.

1) **Poderes altos (P1–P10)**: qué nodos Pi están relativamente ALTOS según el texto (caja, norma, vínculo, tecnología, marca, coordinación, etc., según encaje semántico con cada P).

2) **Poderes bajos**: qué Pi están relativamente BAJOS o colapsados.

3) **Deterioro (flows)**: dónde el texto sugiere **fuga de futuro**, declive, obsolescencia o presión negativa sobre un nodo (aunque no calcules números: solo «deterioro en P8/P9», «presión en P4», etc.).

4) **Contradicción estructural**: tensiones del tipo «caja viva + innovación muerta», «norma densa + maniobra débil», «marca fuerte + tecnología rezagada», «líder central + institución fuerte», etc.

No emitas la FASE 1 en el JSON de respuesta; solo úsala para decidir `signals`.

══════════════════════════════════════════════════════════════════
FASE 2 — Salida JSON (única salida hacia el sistema)
══════════════════════════════════════════════════════════════════

Selecciona las `signals` **solo** en base a la FASE 1. Cada etiqueta debe estar **justificada** por un alto/bajo/deterioro/contradicción que hayas identificado, no por una palabra aislada del texto.

**Cardinalidad obligatoria**: entre **2 y 4** señales. **Nunca** una sola. Si el texto parece unidimensional, aún así elige **dos** señales: la principal y la **segunda más defendible** por el texto (incluso si es más débil).

Excepción: si el input está vacío o es ininteligible, devuelve `{{"signals": []}}`.

Catálogo cerrado (solo estos strings exactos, snake_case):

- ingresos_estables — caja, ingresos o escala económica sostenida
- sin_innovacion — ausencia de innovación, marcos viejos, futuro tecnológico débil
- burocracia — norma densa, procesos rígidos, institución pesada
- marca_fuerte — reputación, marca o reconocimiento simbólico dominante
- cultura_bloqueante — cultura o ritual que impide cambio técnico/operativo
- lider_central — dependencia fuerte de una figura o liderazgo carismático (no combinar con `aislamiento_externo` salvo contradicción explícita)
- aislamiento_externo — desconexión comunicativa (P3) y/o social/redes (P4); lectura de **cerco / fortaleza sitiada**, no de feudo por líder (evita emparejar con `lider_central` / `dependencia_lider`)
- tecnologia_fuerte — capacidad tecnológica, sistemas o I+D destacados
- estrategia_fuerte — maniobra o dirección estratégica clara
- falta_estrategia — ausencia de dirección estratégica o maniobra débil
- dominancia_politica — coaliciones, veto político o coordinación política dominante sobre el sistema
- equilibrio_global — sistema equilibrado en todos los frentes, sin nodos colapsados (suelo de potencias ≥ 6)
- equilibrio_estructural — arquitectura sólida en todos los nodos (suelo ≥ 7 en potencias + refuerzo de P8; perfil «soberano» vs. leviatán)
- operacion_agresiva — caja y maniobra ofensiva (escala, M&A, pricing, expansión) sin alma «zombi»
- escala_sin_direccion — masa o escala económica fuerte pero coordinación/maniobra débil (Gigante vs Disruptiva)
- concentracion_poder — sistema concentrado: uno/pocos nodos sostienen el conjunto (ej. “solo X funciona”, “todo depende de…”)
- debilidad_generalizada — degradación transversal de capacidades (ej. “todo está débil”, “sin capacidad”, “colapso parcial”)
- falta_gobierno — vacío de mano ejecutiva o centro de decisión en el gobierno del sistema (P7; no es feudo por líder)
- innovacion_activa — I+D, producto o maniobra tecnológica/estratégica claramente en marcha (disruptiva vs. zombi)
- alta_tecnologia — ventaja tecnológica fuerte, stack o I+D de primer nivel
- hiper_eficiencia_economica — máquina económica y de maniobra muy eficiente
- dependencia_lider — el sistema gira en torno a una figura; riesgo de feudo operativo (misma cautela de incompatibilidad con `aislamiento_externo` que `lider_central`)
- dependencia_critica — dependencia extrema de una persona sin estructura de respaldo (si falta esa figura, el sistema se bloquea)
- legitimidad_historica — legado, narrativa fundacional o reconocimiento acumulado en el tiempo
- ausencia_centro_decision — vacío de coordinación o mano ejecutiva clara
- estructura_fragmentada — autoridad o procesos partidos, poca unidad institucional
- bloqueo_regulatorio — fricción normativa o legal que comprime canales externos
- presion_externa — hostilidad o presión desde fuera sobre redes o vínculos (P4)

══════════════════════════════════════════════════════════════════
Anclas motor AKXOM (3 confusiones frecuentes; alinea señales con la firma tensorial)
══════════════════════════════════════════════════════════════════

**Organismo de asalto vs Zombi estratégico** — El clasificador exige **P6/P8 altos** y **P2 y P10 bajos** (extracción/velocidad; vínculo y cultura de cierre no dominan). El **Zombi** es **caja + futuro en fuga** (P8/P9 en deterioro), no «asalto» puro. Si el texto es **extracción y velocidad** sin narrativa de decadencia Nokia, prioriza **`operacion_agresiva`** y **no** ancles el caso solo con `ingresos_estables` + `sin_innovacion`.

**Fortaleza sitiada vs Feudo** — Fortaleza = **núcleo institucional/tecnológico (P5/P9) fuerte** y **perímetro comunicativo/social (P3/P4) débil** (cerco). Si el relato es ese **aislamiento estructural**, debes incluir **`aislamiento_externo`** y **no** uses `lider_central` ni `dependencia_lider` (el feudo es **carisma** dominante, no perímetro cercado).

**Gigante de barro vs Vanguardia disruptiva** — Gigante = **masa/fricción**, **mando difuso**, **P9 no hiper-dominante**. Vanguardia exige **P9 muy alto** frente a institución. Si el texto habla de **masa sin dirección** sin I+D o disrupción líder, usa **`escala_sin_direccion`** / `falta_gobierno` / `estructura_fragmentada` y **no** uses `innovacion_activa` ni `tecnologia_fuerte` como eje principal.

══════════════════════════════════════════════════════════════════
Ejemplos contrastivos (patrones; no copies literalmente)
══════════════════════════════════════════════════════════════════

**Zombi vs Disruptiva**
- Zombi (estructura): P6/P caja aún relevante; P8/P9 bajos o en deterioro; contradicción caja vs futuro. Señales típicas: p. ej. `ingresos_estables`, `sin_innovacion`, `falta_estrategia` (elige 2–4 coherentes con tu FASE 1).
- Disruptiva: P8/P9 o innovación/maniobra **altos** y dinamismo; no etiquetes como zombi solo por «empresa grande». Señales típicas: p. ej. `innovacion_activa`, `tecnologia_fuerte`, `estrategia_fuerte`, `operacion_agresiva`.

**Feudo vs Gigante (de barro)**
- Feudo: vínculo/liderazgo personalizado dominante; riesgo de dependencia de figura **sin** contrapeso institucional claro en el texto. Señales: p. ej. `lider_central` o `dependencia_lider` **más** señales de contexto (`estructura_fragmentada`, `falta_estrategia`, etc.) según FASE 1. Si el relato es de **aislamiento** del perímetro, prioriza `aislamiento_externo` y **no** fuerces feudo por líder.
- Gigante de barro: escala o masa **pero** gobierno/coordinación débil (P7), fisuras, peso sin mano ejecutiva; **no** reducir a «hay un CEO». Señales: p. ej. `falta_gobierno`, `hiper_eficiencia_economica` o `operacion_agresiva`, `estructura_fragmentada`.

**Leviatán vs Soberana**
- Leviatán: norma/burocracia/coordinación institucional muy desarrollada; riesgo de rigidez. Señales: p. ej. `burocracia`, `dominancia_politica`, `cultura_bloqueante` (2–4 según contradicciones detectadas).
- Soberana: equilibrio **global** de nodos sin colapso claro; perfil «todo fuerte en conjunto». Señales: p. ej. `equilibrio_estructural` o `equilibrio_global` **más** una o dos señales de refuerzo coherente con el texto (nunca una sola etiqueta).

══════════════════════════════════════════════════════════════════
Formato de salida (EXACTO; sin markdown, sin texto fuera del JSON)
══════════════════════════════════════════════════════════════════

{{"signals": ["etiqueta1", "etiqueta2"]}}

Ejemplo (FASE 1 mental: P6 alto, P8/P9 bajos, deterioro futuro → FASE 2):
{{"signals": ["ingresos_estables", "sin_innovacion", "falta_estrategia"]}}

Texto a analizar:
\"\"\"
{TEXT}
\"\"\"
"""

# Alias retrocompatible (prompt de señales).
PROMPT_TEMPLATE = PROMPT_SIGNALS_TEMPLATE

PROMPT_ARCHETYPE_DISAMBIGUATION_TEMPLATE = """Eres un auditor de desambiguación para AKXOM OS.

El motor (tensor + `identify_archetype`) ya calculó un arquetipo; varios universales pueden quedar **cercanos**.
Tu única tarea es leer el **texto original** y decidir cuál de los **candidatos listados** describe mejor el sistema.

NO recalcules tensores. NO inventes arquetipos fuera de la lista.

Arquetipo predicho por el motor:
- id: `{PREDICTED_ID}`
- nombre: {PREDICTED_NAME}

Candidatos (elige exactamente **uno** por su `id`):
{CANDIDATES_BLOCK}

Salida: UN SOLO JSON, sin markdown ni texto adicional:
{{"final_archetype": "<id_exacto>"}}

El valor de `final_archetype` DEBE ser uno de los ids listados arriba.

Texto original:
\"\"\"
{TEXT}
\"\"\"
"""


def _normalize_signal_token(raw: str) -> str:
    s = str(raw).strip().lower().replace("-", "_")
    return "_".join(s.split())


def _dampen_single_signal_tensor(
    p: dict[str, float],
    fl: dict[str, float],
    m: dict[str, float],
    ax: dict[str, float],
    damp: float,
) -> None:
    """Reduce desviaciones respecto al neutro para que un único token no fije el perfil."""
    d = float(np.clip(damp, 0.0, 1.0))
    for code in p:
        p[code] = 5.0 + (p[code] - 5.0) * d
    for k in m:
        m[k] = 5.0 + (m[k] - 5.0) * d
    for k in ax:
        ax[k] = 5.0 + (ax[k] - 5.0) * d
    for code in fl:
        fl[code] *= d


def _strong_power_candidates_from_signals(seen: set[str]) -> set[str]:
    """
    Candidatos de nodo fuerte para escenarios de concentración.
    No reemplaza deltas por señal; solo define qué Pi pueden quedar en banda 7–8.
    """
    out: set[str] = set()
    if "marca_fuerte" in seen or "legitimidad_historica" in seen:
        out.add("P10")
    if "tecnologia_fuerte" in seen or "alta_tecnologia" in seen:
        out.add("P9")
    if "innovacion_activa" in seen or "estrategia_fuerte" in seen:
        out.add("P8")
    if "ingresos_estables" in seen or "hiper_eficiencia_economica" in seen or "operacion_agresiva" in seen:
        out.add("P6")
    if "burocracia" in seen:
        out.add("P5")
    if "dominancia_politica" in seen:
        out.add("P7")
    if "lider_central" in seen or "dependencia_lider" in seen:
        out.add("P2")
    return out


def _medium_power_candidates_from_signals(seen: set[str], raw_tokens: set[str]) -> set[str]:
    """
    Nodos a sostener en banda media-alta (no dominante).
    - marca_fuerte implica canal comunicacional funcional mínimo (P3).
    - compatibilidad opcional con token libre `comunicacion_fuerte` (sin ampliar catálogo).
    """
    out: set[str] = set()
    if "marca_fuerte" in seen or "comunicacion_fuerte" in raw_tokens:
        out.add("P3")
    return out


def _apply_concentrated_distribution(
    p: dict[str, float],
    fl: dict[str, float],
    *,
    strong_codes: set[str] | None = None,
    medium_codes: set[str] | None = None,
) -> None:
    """
    Corrección estructural: evita aplanado cuando el caso describe asimetría.
    Fuertes en banda 7–8, resto en 2–4; flujos negativos más duros en débiles.
    """
    base_codes = [code for code, _, _, _ in PODERES_INFO]
    chosen: set[str] = set(strong_codes or set())
    medium: set[str] = set(medium_codes or set())
    if not chosen:
        # Fallback defensivo: al menos un nodo dominante (máximo actual).
        top = max(base_codes, key=lambda c: p[c])
        chosen = {top}
    for code in list(chosen):
        if code not in p:
            chosen.discard(code)
    for code in list(medium):
        if code not in p or code in chosen:
            medium.discard(code)
    if not chosen:
        chosen = {base_codes[0]}

    for code in base_codes:
        if code in chosen:
            # Mantiene orden relativo y banda fuerte.
            p[code] = float(np.clip(7.0 + 0.18 * (p[code] - 5.0), 7.0, 8.0))
            fl[code] = min(float(fl[code]), -0.5)
        elif code in medium:
            # Refuerzo no dominante (ej. canal comunicacional P3).
            p[code] = float(np.clip(max(6.0, p[code]), 6.0, 6.6))
            fl[code] = min(float(fl[code]), -0.8)
        else:
            # Penalización explícita por ausencia de capacidad: P -= 2 (clamp 2).
            penalized = max(2.0, float(p[code]) - 2.0)
            # Banda débil final 2–4 evitando plano en 5.
            p[code] = float(np.clip(penalized, 2.0, 4.0))
            fl[code] = min(float(fl[code]), -1.2)


def _apply_generalized_weakness_distribution(
    p: dict[str, float],
    fl: dict[str, float],
) -> None:
    """Degradación transversal: todos los nodos quedan en 2–4 y flujos levemente negativos."""
    for code, _, _, _ in PODERES_INFO:
        p[code] = float(np.clip(3.0 + 0.32 * (p[code] - 5.0), 2.0, 4.0))
        fl[code] = min(float(fl[code]), -0.6)


def _enforce_weakness_cap_max_three_above_five(p: dict[str, float], preferred: set[str]) -> None:
    """
    En contexto de debilidad estructural: no permitir >3 nodos por encima de 5.
    Conserva primero los preferidos y luego los más altos restantes.
    """
    above = [code for code, val in p.items() if float(val) > 5.0]
    if len(above) <= 3:
        return
    keep: list[str] = [code for code in above if code in preferred]
    for code in sorted(above, key=lambda c: float(p[c]), reverse=True):
        if code in keep:
            continue
        keep.append(code)
        if len(keep) >= 3:
            break
    keep_set = set(keep[:3])
    for code in above:
        if code not in keep_set:
            p[code] = min(float(p[code]), 4.0)


def signals_to_akxom_json(signals: list[str] | None) -> dict[str, Any]:
    """
    Convierte señales discretas en el dict AKXOM esperado por `validate_akxom_json` / tensor.
    Base neutra 5 en potencias; aplica deltas por señal (acumulativos, orden irrelevante).
    Con **una sola** señal distinta, amortigua desviaciones (`SINGLE_SIGNAL_DAMPEN`) antes de suelos
    de equilibrio (`equilibrio_global` ≥6, `equilibrio_estructural` ≥7 + refuerzo P8) y reglas
    `lider_central` / `dependencia_lider` (anulados si `aislamiento_externo`; anti-feudo si P5 y P8 ≥6).
    """
    p: dict[str, float] = {code: 5.0 for code, _, _, _ in PODERES_INFO}
    fl: dict[str, float] = {code: 0.0 for code, _, _, _ in PODERES_INFO}
    m = {"M1": 5.0, "M2": 5.0, "M3": 5.0}
    ax = {"R": 5.0, "C": 5.0, "A": 5.0}

    applied: list[str] = []
    seen: set[str] = set()
    raw_tokens: set[str] = set()
    lider_boost_applied = False
    for raw in signals or []:
        sig = _normalize_signal_token(raw)
        raw_tokens.add(sig)
        if sig not in KNOWN_SIGNALS or sig in seen:
            continue
        seen.add(sig)
        applied.append(sig)

        if sig == "ingresos_estables":
            p["P6"] += 2.5
        elif sig == "sin_innovacion":
            p["P8"] -= 3.0
            p["P9"] -= 3.0
            fl["P8"] -= 1.0
            fl["P9"] -= 1.1
        elif sig == "burocracia":
            p["P5"] += 2.5
            m["M3"] += 1.2
        elif sig == "marca_fuerte":
            p["P10"] += 2.5
        elif sig == "cultura_bloqueante":
            p["P10"] += 1.0
            p["P9"] -= 2.0
            p["P8"] -= 1.5
            p["P9"] -= 1.5
            fl["P9"] -= 0.6
            m["M3"] += 0.8
        elif sig == "lider_central":
            pass  # Tras resto de señales; solo si P5≥5.5 y P8≥5.5
        elif sig == "aislamiento_externo":
            p["P3"] -= 3.5
            p["P4"] -= 3.5
            fl["P3"] -= 1.2
            fl["P4"] -= 1.2
        elif sig == "innovacion_activa":
            p["P8"] += 2.5
            p["P9"] += 2.5
            fl["P8"] += 1.2
            fl["P9"] += 1.2
        elif sig == "tecnologia_fuerte":
            p["P9"] += 2.5
        elif sig == "estrategia_fuerte":
            p["P8"] += 2.5
        elif sig == "falta_estrategia":
            p["P8"] -= 2.5
        elif sig == "dominancia_politica":
            p["P7"] += 2.5
        elif sig == "equilibrio_global":
            pass  # Suelo P1–P10 ≥ 6 tras amortiguación
        elif sig == "equilibrio_estructural":
            pass  # Suelo P1–P10 ≥ 7 y +1 P8 tras amortiguación
        elif sig == "operacion_agresiva":
            p["P6"] += 3.0
            p["P8"] += 2.5
            p["P2"] -= 1.5
            p["P4"] -= 2.0
            p["P10"] -= 2.0
            fl["P6"] += 0.8
            fl["P8"] += 0.8
        elif sig == "escala_sin_direccion":
            p["P6"] += 2.5
            p["P7"] -= 2.5
            p["P8"] -= 2.5
            p["P9"] -= 1.5
            fl["P8"] -= 1.2
            fl["P9"] -= 0.45
        elif sig == "falta_gobierno":
            p["P7"] -= 2.5
            fl["P7"] -= 0.95
        elif sig == "alta_tecnologia":
            p["P9"] += 3.0
        elif sig == "hiper_eficiencia_economica":
            p["P6"] += 3.0
            p["P8"] += 2.0
        elif sig == "dependencia_lider":
            p["P2"] += 3.0
            p["P5"] -= 1.0
            ax["A"] += 2.2
            m["M2"] += 0.6
        elif sig == "dependencia_critica":
            p["P2"] += 2.5
            p["P5"] -= 2.5
            p["P8"] -= 1.5
            fl["P2"] -= 0.5
            fl["P5"] -= 1.2
        elif sig == "legitimidad_historica":
            p["P10"] += 2.0
        elif sig == "ausencia_centro_decision":
            p["P7"] -= 2.5
        elif sig == "estructura_fragmentada":
            p["P5"] -= 2.0
        elif sig == "bloqueo_regulatorio":
            p["P3"] -= 2.0
            p["P4"] -= 2.0
        elif sig == "presion_externa":
            p["P4"] -= 1.5

    # Dependencia estructural crítica: líder + falta de gobierno/fragmentación.
    if "lider_central" in seen and ("falta_gobierno" in seen or "estructura_fragmentada" in seen):
        if "dependencia_critica" not in seen:
            seen.add("dependencia_critica")
            applied.append("dependencia_critica")
        p["P2"] += 2.5
        p["P5"] -= 2.5
        p["P8"] -= 1.5
        fl["P2"] -= 0.5
        fl["P5"] -= 1.2

    # Marca fuerte sin palanca técnica explícita: baja P9 (evita «fantasma» solo cultural).
    if "marca_fuerte" in seen and "tecnologia_fuerte" not in seen:
        p["P9"] -= 1.0

    # Fortaleza vs Feudo: aislamiento anula el vector de dependencia_lider (mismo criterio que lider_central).
    if "dependencia_lider" in seen and "aislamiento_externo" in seen:
        p["P2"] -= 3.0
        p["P5"] += 1.0
        ax["A"] -= 2.2
        m["M2"] -= 0.6

    # lider_central solo si ya hay suficiente institución y estrategia (evita Feudo con estructura débil).
    if "lider_central" in seen and p["P5"] >= 5.5 and p["P8"] >= 5.5:
        p["P2"] += 1.0
        ax["A"] += 0.6
        m["M2"] += 0.8
        lider_boost_applied = True

    # Fortaleza vs Feudo: aislamiento externo anula por completo el empuje de lider_central (revertir si se aplicó).
    if "lider_central" in seen and "aislamiento_externo" in seen and lider_boost_applied:
        p["P2"] -= 1.0
        ax["A"] -= 0.6
        m["M2"] -= 0.8
        lider_boost_applied = False

    has_distribution_override = "concentracion_poder" in seen or "debilidad_generalizada" in seen
    has_strong_signal = bool(STRONG_SIGNALS & seen)
    if len(applied) == 1 and not has_distribution_override and not has_strong_signal:
        _dampen_single_signal_tensor(p, fl, m, ax, SINGLE_SIGNAL_DAMPEN)

    if "equilibrio_global" in seen and not has_strong_signal:
        for code, _, _, _ in PODERES_INFO:
            p[code] = max(p[code], 6.0)
    if "equilibrio_estructural" in seen and not has_strong_signal:
        for code, _, _, _ in PODERES_INFO:
            p[code] = max(p[code], 7.0)
        p["P8"] += 1.0

    # Líder + institución y estrategia ya altas → no es feudo puro: anula el empuje aplicado de lider_central.
    if lider_boost_applied and p["P5"] >= 6.0 and p["P8"] >= 6.0:
        p["P2"] -= 1.0
        ax["A"] -= 0.6

    # Corrección estructural de distribución (después de deltas por señal).
    if "debilidad_generalizada" in seen:
        _apply_generalized_weakness_distribution(p, fl)
    elif "concentracion_poder" in seen:
        strong = _strong_power_candidates_from_signals(seen)
        medium = _medium_power_candidates_from_signals(seen, raw_tokens)
        _apply_concentrated_distribution(p, fl, strong_codes=strong, medium_codes=medium)

    if "marca_fuerte" in seen:
        p["P10"] = max(float(p["P10"]), 7.0)
    if "comunicacion_fuerte" in raw_tokens:
        p["P3"] = max(float(p["P3"]), 6.0)

    if "debilidad_generalizada" in seen or "concentracion_poder" in seen:
        preferred = _strong_power_candidates_from_signals(seen) | _medium_power_candidates_from_signals(seen, raw_tokens)
        _enforce_weakness_cap_max_three_above_five(p, preferred)

    # Regla clave: no permitir P2 alto con P5 medio cuando hay dependencia crítica.
    if "dependencia_critica" in seen and p["P2"] > 6.0:
        p["P5"] = min(float(p["P5"]), 4.0)

    for code, _, _, _ in PODERES_INFO:
        p[code] = float(np.clip(p[code], 0.0, 10.0))
    for k in m:
        m[k] = float(np.clip(m[k], 0.0, 10.0))
    for k in ax:
        ax[k] = float(np.clip(ax[k], 0.0, 10.0))
    for code, _, _, _ in PODERES_INFO:
        fl[code] = float(np.clip(fl[code], -3.0, 3.0))

    sig_note = ", ".join(applied) if applied else "ninguna (neutro)"
    explanations: dict[str, str] = {}
    for code, _, _, _ in PODERES_INFO:
        explanations[code] = f"Inferido por motor desde señales: {sig_note}."[:160]

    return {
        "powers": {k: round(p[k], 2) for k in p},
        "materialities": {k: round(m[k], 2) for k in m},
        "axes": {k: round(ax[k], 2) for k in ax},
        "flows": {k: round(fl[k], 3) for k in fl},
        "explanations": explanations,
        "signals_applied": list(applied),
    }


def signals_to_tensor(signals: list[str] | None) -> np.ndarray:
    """`signals` → dict AKXOM → tensor (10,3,3). Para solo el dict, usa `signals_to_akxom_json`."""
    return akxom_json_to_tensor(signals_to_akxom_json(signals))


def build_archetype_candidate_ids(
    identify_out: dict[str, Any],
    report: dict[str, Any],
    *,
    executive_integrity: float,
    friction: float,
    flows: Sequence[float] | None,
    contradictions: list[dict[str, Any]] | None,
) -> list[str]:
    """
    2–3 ids: predicho, segundo por el motor (`runner_up_id`), y opcional tercero por proximidad
    euclídea en el vector de rasgos (sin modificar `identify_archetype`).
    """
    from akxom_archetypes import ARCHETYPES, build_archetype_feature_vector

    pred = str(identify_out.get("id") or "").strip()
    run = str(identify_out.get("runner_up_id") or "").strip()
    out: list[str] = []
    if pred:
        out.append(pred)
    if run and run not in out:
        out.append(run)

    x = build_archetype_feature_vector(
        report,
        executive_integrity=float(executive_integrity),
        friction=float(friction),
        flows=flows,
    )
    d_arr = np.asarray([float(np.linalg.norm(x - arch.ideal)) for arch in ARCHETYPES], dtype=float)
    order = np.argsort(d_arr)
    for idx in order:
        aid = str(ARCHETYPES[int(idx)].id).strip()
        if aid and aid not in out:
            out.append(aid)
        if len(out) >= 3:
            break
    return out[:3]


def llm_disambiguate_archetype(
    text: str,
    *,
    predicted_id: str,
    predicted_name: str,
    candidate_ids: Sequence[str],
    model: str | None = None,
    api_key: str | None = None,
    temperature: float | None = None,
) -> str:
    """
    Segunda capa: elige un `id` entre los candidatos. Devuelve siempre un id válido de la lista
    (o el predicho si el JSON es inválido).
    """
    from akxom_archetypes import ARCHETYPES

    ids = [str(x).strip() for x in candidate_ids if str(x).strip()]
    if not ids:
        return str(predicted_id).strip()
    uniq: list[str] = []
    for i in ids:
        if i not in uniq:
            uniq.append(i)
    ids = uniq

    by_id = {a.id: a for a in ARCHETYPES}
    lines: list[str] = []
    for aid in ids:
        a = by_id.get(aid)
        if a is None:
            lines.append(f"- id: `{aid}` (desconocido en catálogo)")
        else:
            desc = (a.description or "").replace("\n", " ").strip()
            if len(desc) > 220:
                desc = desc[:217] + "..."
            lines.append(f"- id: `{a.id}` | nombre: {a.name} | {desc}")

    prompt = PROMPT_ARCHETYPE_DISAMBIGUATION_TEMPLATE.replace("{TEXT}", str(text or "")).replace(
        "{PREDICTED_ID}", str(predicted_id or "")
    ).replace("{PREDICTED_NAME}", str(predicted_name or "")).replace(
        "{CANDIDATES_BLOCK}", "\n".join(lines)
    )

    try:
        from openai import OpenAI  # type: ignore[import-untyped]
    except ImportError as e:
        raise ImportError("Instala el paquete openai: pip install openai") from e

    key = api_key or os.environ.get("OPENAI_API_KEY")
    if not key or not str(key).strip():
        raise ValueError("Falta OPENAI_API_KEY en el entorno (o pasa api_key=...).")

    client = OpenAI(api_key=key)
    use_model = model or DEFAULT_LLM_MODEL
    temp = DEFAULT_LLM_TEMPERATURE if temperature is None else float(temperature)
    response = client.chat.completions.create(
        model=use_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=float(np.clip(temp, 0.0, 2.0)),
        response_format={"type": "json_object"},
    )
    content = (response.choices[0].message.content or "").strip()
    raw_json = _extract_json_text(content)
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError:
        return str(predicted_id).strip()
    fin = data.get("final_archetype")
    if not isinstance(fin, str) or not fin.strip():
        return str(predicted_id).strip()
    fin = fin.strip()
    if fin in ids:
        return fin
    # tolera si el modelo devuelve el id sin normalizar
    for aid in ids:
        if fin.lower() == aid.lower():
            return aid
    return str(predicted_id).strip()


def _merge_archetype_universal_with_id(
    base: dict[str, Any],
    final_id: str,
) -> dict[str, Any]:
    from akxom_archetypes import ARCHETYPES

    out = dict(base)
    for a in ARCHETYPES:
        if a.id == final_id:
            out["id"] = a.id
            out["name"] = a.name
            out["description"] = a.description
            return out
    out["id"] = final_id
    return out


def _apply_archetype_semantic_guardrails(
    *,
    candidate_ids: Sequence[str],
    applied_signals: set[str],
) -> list[str]:
    """
    Filtra candidatos por coherencia semántica en capa de desambiguación:
    1) Sin liderazgo personal explícito, no permitir `feudo_carismatico`.
    2) Con triada (ingresos_estables + falta_estrategia + estructura_fragmentada),
       restringir a familia gigante/zombi.
    """
    ids = [str(x).strip() for x in candidate_ids if str(x).strip()]
    if not ids:
        return []

    out = list(ids)

    # Requisitos mínimos por arquetipo.
    def _meets(archetype_id: str) -> bool:
        req = ARCHETYPE_REQUIREMENTS.get(str(archetype_id))
        if not req:
            return True
        any_of = set(req.get("any_of") or set())
        all_of = set(req.get("all_of") or set())
        none_of = set(req.get("none_of") or set())
        if any_of and not (any_of & applied_signals):
            return False
        if all_of and not all_of.issubset(applied_signals):
            return False
        if none_of and (none_of & applied_signals):
            return False
        return True

    out = [x for x in out if _meets(x)]
    has_personal_lead = "lider_central" in applied_signals or "dependencia_lider" in applied_signals
    if not has_personal_lead:
        out = [x for x in out if x != "feudo_carismatico"]

    triad = {"ingresos_estables", "falta_estrategia", "estructura_fragmentada"}
    if triad.issubset(applied_signals):
        allowed = {"gigante_de_barro", "zombi_estrategico"}
        triad_out = [x for x in out if x in allowed]
        if triad_out:
            out = triad_out
        else:
            out = [x for x in ids if x in allowed] or list(allowed)

    # Unicidad + orden estable
    uniq: list[str] = []
    for x in out:
        if x not in uniq:
            uniq.append(x)
    return uniq


def _parse_signals_response(data: Any) -> list[str]:
    if not isinstance(data, dict):
        raise ValueError("La respuesta del LLM no es un objeto JSON.")
    raw = data.get("signals")
    if not isinstance(raw, list):
        raise ValueError('Falta "signals" o no es una lista.')
    out: list[str] = []
    for item in raw:
        if not isinstance(item, str) or not str(item).strip():
            continue
        sig = _normalize_signal_token(item)
        if sig in KNOWN_SIGNALS:
            out.append(sig)
    return out


def _materiality_with_power_signal(p_val: float, m_global: float) -> float:
    """
    Inyecta la señal Pi (0–10) en la materialidad global sin promediar tipo 0.55*p+0.45*M.

    Usamos desviación respecto al neutro 5: si p=5, queda m_global; si p>5 sube el canal;
    si p<5 lo baja. Los ejes R,C,A van aparte como moduladores globales en set_power_structured.
    """
    return float(np.clip(float(m_global) + (float(p_val) - 5.0), 0.0, 10.0))


def _extract_json_text(raw: str) -> str:
    s = raw.strip()
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\s*", "", s, count=1, flags=re.IGNORECASE)
        s = re.sub(r"\s*```\s*$", "", s, count=1)
    return s.strip()


def akxom_json_to_tensor(data: dict[str, Any]) -> np.ndarray:
    """
    Mapea el JSON del LLM al tensor (10,3,3).

    Por cada poder Pi: `powers[Pi]` modula M1–M3 globales como desplazamiento (p−5), no como
    media con p. Los ejes R, C, A del JSON son moduladores globales compartidos; la composición
    en celdas la hace solo `set_power_structured` (engine sin cambios).
    """
    powers = data.get("powers") or {}
    mat = data.get("materialities") or {}
    ax = data.get("axes") or {}

    M1 = float(np.clip(float(mat.get("M1", 5.0)), 0.0, 10.0))
    M2 = float(np.clip(float(mat.get("M2", 5.0)), 0.0, 10.0))
    M3 = float(np.clip(float(mat.get("M3", 5.0)), 0.0, 10.0))
    R = float(np.clip(float(ax.get("R", 5.0)), 0.0, 10.0))
    C = float(np.clip(float(ax.get("C", 5.0)), 0.0, 10.0))
    A = float(np.clip(float(ax.get("A", 5.0)), 0.0, 10.0))

    T = build_empty_tensor()
    for i, (p_code, _, _, _) in enumerate(PODERES_INFO):
        p_val = float(np.clip(float(powers.get(p_code, 5.0)), 0.0, 10.0))
        m1 = _materiality_with_power_signal(p_val, M1)
        m2 = _materiality_with_power_signal(p_val, M2)
        m3 = _materiality_with_power_signal(p_val, M3)
        T = set_power_structured(T, i, m1, m2, m3, R, C, A)
    return T


def validate_akxom_json(data: dict[str, Any]) -> None:
    if not isinstance(data, dict):
        raise ValueError("La respuesta del LLM no es un objeto JSON.")
    powers = data.get("powers")
    if not isinstance(powers, dict):
        raise ValueError('Falta "powers" o no es un objeto.')
    for p_code, _, _, _ in PODERES_INFO:
        if p_code not in powers:
            raise ValueError(f'Falta "{p_code}" en powers.')
    for key in ("materialities", "axes"):
        if key not in data or not isinstance(data[key], dict):
            raise ValueError(f'Falta "{key}" o no es un objeto.')
    for k in ("M1", "M2", "M3"):
        if k not in data["materialities"]:
            raise ValueError(f'Falta materialities["{k}"].')
    for k in ("R", "C", "A"):
        if k not in data["axes"]:
            raise ValueError(f'Falta axes["{k}"].')
    fl = data.get("flows")
    if not isinstance(fl, dict):
        raise ValueError('Falta "flows" o no es un objeto.')
    for p_code, _, _, _ in PODERES_INFO:
        if p_code not in fl:
            raise ValueError(f'Falta flows["{p_code}"].')
        try:
            fv = float(fl[p_code])
        except (TypeError, ValueError) as e:
            raise ValueError(f'flows["{p_code}"] debe ser numérico.') from e
        if fv < -3.0 or fv > 3.0:
            raise ValueError(f'flows["{p_code}"] debe estar en [-3, 3].')


def akxom_flows_from_json(data: dict[str, Any]) -> list[float]:
    """Lista de 10 flows en orden P1–P10, recortada a [-3, 3]."""
    fl = data.get("flows") or {}
    out: list[float] = []
    for p_code, _, _, _ in PODERES_INFO:
        try:
            v = float((fl or {}).get(p_code, 0.0))
        except (TypeError, ValueError):
            v = 0.0
        out.append(float(np.clip(v, -3.0, 3.0)))
    return out


def llm_parse_text_to_akxom_json(
    text: str,
    *,
    model: str | None = None,
    api_key: str | None = None,
    temperature: float | None = None,
) -> dict[str, Any]:
    """
    Llama al modelo para extraer **señales** (`signals`), las convierte con `signals_to_akxom_json`
    y devuelve el mismo dict AKXOM que antes (`powers`, `materialities`, `axes`, `flows`, `explanations`).

    Requiere `openai` y API key. Temperatura por defecto baja (0.1); `NOUMENON_LLM_TEMPERATURE` o el
    argumento `temperature` la sobrescriben.
    """
    try:
        from openai import OpenAI  # type: ignore[import-untyped]
    except ImportError as e:
        raise ImportError(
            "Instala el paquete openai: pip install openai"
        ) from e

    key = api_key or os.environ.get("OPENAI_API_KEY")
    if not key or not str(key).strip():
        raise ValueError(
            "Falta OPENAI_API_KEY en el entorno (o pasa api_key=...)."
        )

    client = OpenAI(api_key=key)
    use_model = model or DEFAULT_LLM_MODEL
    temp = DEFAULT_LLM_TEMPERATURE if temperature is None else float(temperature)
    prompt = PROMPT_SIGNALS_TEMPLATE.replace("{TEXT}", str(text or ""))

    response = client.chat.completions.create(
        model=use_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=float(np.clip(temp, 0.0, 2.0)),
        response_format={"type": "json_object"},
    )
    content = (response.choices[0].message.content or "").strip()
    raw_json = _extract_json_text(content)

    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON inválido del LLM:\n{raw_json}") from e

    signals = _parse_signals_response(data)
    out = signals_to_akxom_json(signals)
    validate_akxom_json(out)
    out["signals"] = list(signals)
    return out


def build_selected_ranked_state_from_llm(
    data: dict[str, Any],
    *,
    max_powers: int = 5,
    min_note_chars: int = 70,
) -> list[dict[str, Any]]:
    """Construye la lista tipo `select_top_powers_state_from_text` para la UI."""
    powers = data.get("powers") or {}
    explanations = data.get("explanations") or {}
    filler = " Señal consolidada por modelo de lenguaje (AKXOM ingest)."

    ranked: list[tuple[str, float]] = []
    for p_code, _, _, _ in PODERES_INFO:
        try:
            v = float(powers.get(p_code, 0.0))
        except (TypeError, ValueError):
            v = 0.0
        ranked.append((p_code, float(np.clip(v, 0.0, 10.0))))

    ranked.sort(key=lambda x: x[1], reverse=True)
    ranked = ranked[:max_powers]

    out: list[dict[str, Any]] = []
    for p_code, p_val in ranked:
        note = str(explanations.get(p_code, "") or "").strip()
        if not note:
            note = f"Prioridad relativa en {p_code} según lectura estructural."
        while len(note) < min_note_chars:
            note = note + filler
        conf = int(np.clip(50.0 + 5.0 * p_val, 50.0, 100.0))
        score = int(np.clip(round(p_val), 0, 10))
        out.append(
            {
                "p_code": p_code,
                "note": note,
                "confidence": conf,
                "score": score,
                "keyword": "llm_akxom",
                "tension_matched": False,
                "tension_keyword": "",
                "rupture_collapse": False,
            }
        )
    return out


def build_report_from_text(
    text: str,
    *,
    target: str = "LLM ingest",
    benchmark_name: str = "Ideal estable",
    disambiguate_archetype: bool | None = None,
    api_key: str | None = None,
    model: str | None = None,
) -> dict[str, Any]:
    """
    Texto → LLM → JSON AKXOM → tensor → `build_core_output_impl`.

    Incluye `archetype_universal` (clasificador tensor). Si `disambiguate_archetype` es True y hay
    `OPENAI_API_KEY`, segunda llamada LLM elige entre 2–3 candidatos (predicho + alternativas).

    `disambiguate_archetype`: None → usa env `NOUMENON_ARCHETYPE_DISAMBIGUATION` (default activado si
    la variable no está en "0"/"false").
    """
    from analysis import get_auto_profile
    from motor_dictamen import build_core_output_impl

    data = llm_parse_text_to_akxom_json(text)
    T = akxom_json_to_tensor(data)
    flows = akxom_flows_from_json(data)
    core = build_core_output_impl(
        T,
        flows,
        target,
        benchmark_name,
        get_auto_profile("Estable"),
    )
    ev_df = core.get("evidence_df")
    ev_mean: float | None = None
    if ev_df is not None and not getattr(ev_df, "empty", True) and "Confianza" in ev_df.columns:
        try:
            ev_mean = float(np.mean(ev_df["Confianza"]))
        except (TypeError, ValueError):
            ev_mean = None

    au = core.get("archetype_universal")
    if not isinstance(au, dict):
        au = {}

    dis_meta: dict[str, Any] = {
        "candidates": [],
        "predicted_id": str(au.get("id") or ""),
        "final_id": str(au.get("id") or ""),
        "applied": False,
    }

    if disambiguate_archetype is None:
        _env = os.environ.get("NOUMENON_ARCHETYPE_DISAMBIGUATION", "1").strip().lower()
        disambiguate_archetype = _env not in ("0", "false", "no", "off")

    applied_signals = set(str(x).strip() for x in (data.get("signals_applied") or []) if str(x).strip())

    au_final: dict[str, Any] = dict(au)
    guarded_pred = _apply_archetype_semantic_guardrails(
        candidate_ids=[str(au.get("id") or "")],
        applied_signals=applied_signals,
    )
    if guarded_pred and guarded_pred[0] != str(au_final.get("id") or ""):
        au_final = _merge_archetype_universal_with_id(au_final, guarded_pred[0])
        dis_meta["final_id"] = guarded_pred[0]

    if disambiguate_archetype and str(au.get("id") or "").strip():
        key = api_key or os.environ.get("OPENAI_API_KEY")
        if key and str(key).strip():
            try:
                cands = build_archetype_candidate_ids(
                    au,
                    core["report"],
                    executive_integrity=float(core["integrity"]),
                    friction=float(core["friction"]),
                    flows=flows,
                    contradictions=core.get("contradictions") or [],
                )
                gcands = _apply_archetype_semantic_guardrails(
                    candidate_ids=cands,
                    applied_signals=applied_signals,
                )
                dis_meta["candidates"] = list(gcands)
                fin = llm_disambiguate_archetype(
                    text,
                    predicted_id=str(au.get("id") or ""),
                    predicted_name=str(au.get("name") or ""),
                    candidate_ids=gcands or cands,
                    api_key=key,
                    model=model,
                )
                fin_guarded = _apply_archetype_semantic_guardrails(
                    candidate_ids=[fin],
                    applied_signals=applied_signals,
                )
                if fin_guarded:
                    fin = fin_guarded[0]
                elif gcands:
                    fin = gcands[0]
                au_final = _merge_archetype_universal_with_id(au, fin)
                dis_meta["final_id"] = str(au_final.get("id") or fin)
                dis_meta["applied"] = True
            except (ImportError, ValueError, OSError, RuntimeError):
                au_final = dict(au)
                dis_meta["final_id"] = str(au.get("id") or "")
                dis_meta["applied"] = False

    _lev = core["decision_panel"].get("lever_power") or core.get("acted_power")
    _ap = build_action_plan(
        str(au_final.get("id") or ""),
        core.get("current_top_risk"),
        _lev,
    )

    return {
        "report": core["report"],
        "flows": flows,
        "executive_integrity": float(core["integrity"]),
        "friction": float(core["friction"]),
        "contradictions": core.get("contradictions") or [],
        "evidence_confidence_mean": ev_mean,
        "archetype_universal": au_final,
        "archetype_disambiguation": dis_meta,
        "action_plan": _ap,
        "signals_applied": list(data.get("signals_applied") or []),
        "causal_chain": build_causal_chain(
            list(data.get("signals_applied") or []),
            T,
            core.get("current_top_risk"),
        ),
    }
