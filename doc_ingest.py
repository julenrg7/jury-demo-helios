"""
doc_ingest.py

Fase 2: Ingesta documental mínima para proponer notas de evidencia por Pi (P1–P10).

No usamos LLM ni APIs externas: aplicamos heurísticas basadas en keywords ya definidas
en `engine_akxom.py` (keywords_short). Esto permite un MVP vendible y trazable.

Protocolo de veto estructural: `KEYWORDS_RUPTURA` en el texto asociado a un Pi fuerza colapso
a ruptura (score 1, tensor 1.0 en autofill) con prioridad absoluta sobre señales positivas.
"""

from __future__ import annotations

import io
import re
import unicodedata
from typing import Any, Dict, Sequence

from engine_akxom import PODERES_INFO


DOC_EXTRA_KEYWORDS: Dict[str, tuple[str, ...]] = {
    # P1 BIOLÓGICO: solo plantilla humana (salud, fatiga, vitalidad). No «seguridad del producto»
    # ni accidente industrial aquí: eso es P5 (norma) / P8 (maniobra); ver P5/P8.
    "P1": (
        "cuerpo",
        "somatic",
        "biologic",
        "biometr",
        "fatiga",
        "agotamiento",
        "baja medica",
        "baja laboral",
        "salud laboral",
        "salud clinica",
        "ausentismo",
        "incapacidad temporal",
        "enfermedad profesional",
        "ergonomia",
        "workforce health",
        "employee health",
        "sick leave",
        "medical leave",
        "metabolic",
        "metabolico",
        "ritmo biologico",
        "energia vital",
        "resistencia fisica",
        "presencia somatica",
        "plantilla",
        "dotacion humana",
        "health crisis",
        "crisis de salud",
        "mental health crisis",
        "public health crisis",
        "global health crisis",
        "occupational health crisis",
    ),
    # P2: vocabulario emocional que no cabe entero en keywords_short del motor.
    "P2": (
        "clima",
        "resentimiento",
        "miedo",
        "panico",
        "hostilidad",
        "cinismo",
        "desafeccion",
        "desconfianza",
        "moral",
        "compromiso",
        "engagement",
        "liturgia",
        "ritual",
        "simbolo",
        "marca",
        "lealtad",
        "devocion",
        "empatia",
        "afecto",
        "euforia",
        "culto",
        "veneracion",
        "traicion",
        "burnout",
    ),
    # P3: señal, canales, oficialidad, ruido horizontal (más allá de keywords_short).
    "P3": (
        "narrativa",
        "narrativas",
        "comunicado",
        "comunicados",
        "portavocia",
        "portavoz",
        "rumor",
        "rumores",
        "viralidad",
        "filtracion",
        "filtraciones",
        "senal",
        "senales",
        "mensaje",
        "mensajes",
        "broadcast",
        "contradictor",
        "contradictorios",
        "desinformacion",
        "alcance",
        "audiencia",
        "newsletter",
        "storytelling",
        "retorica",
        "dogma",
        "censura",
        "censuras",
        "algoritmo",
        "algoritmos",
        "plataforma",
        "plataformas",
        "canal",
        "canales",
        "town hall",
        "emisor",
        "receptor",
    ),
    # P4: capital relacional, grafo, membresía y movilización (más allá de keywords_short).
    "P4": (
        "red",
        "redes",
        "alianza",
        "alianzas",
        "coalicion",
        "coaliciones",
        "membresia",
        "networking",
        "elite",
        "masa",
        "movilizacion",
        "boicot",
        "tribu",
        "clan",
        "grafo",
        "conector",
        "conectores",
        "puente",
        "acceso",
        "exclusividad",
        "comunidad",
        "comunidades",
        "stakeholder",
        "stakeholders",
        "referido",
        "referidos",
        "patronazgo",
        "faccion",
        "facciones",
        "cisura",
        "fragmentacion",
        "ostracismo",
        "parche",
        "parches",
    ),
    # P5 INSTITUCIONAL: cumplimiento, norma, auditoría. Incl. seguridad operativa como *proceso*
    # (FAA, quality control, audit) — no confundir con P1 salud de plantilla.
    "P5": (
        "safety",
        "safeties",
        "regulatory",
        "regulation",
        "regulations",
        "faa",
        "easa",
        "quality control",
        "quality assurance",
        "audit",
        "audits",
        "auditor",
        "auditoria",
        "protocol",
        "protocols",
        "airworthiness",
        "certification",
        "oversight",
        "inspector",
        "inspectors",
        "inspection",
        "adherence",
        "noncompliance",
        "non compliance",
        "sop",
        "standard operating",
        "qms",
        "as9100",
        "part 145",
        "part 21",
        "reglamento",
        "reglamentos",
        "procedimiento",
        "procedimientos",
        "compliance",
        "organigrama",
        "cargo",
        "cargos",
        "estatuto",
        "estatutos",
        "jerarquia",
        "burocracia",
        "expediente",
        "expedientes",
        "nombramiento",
        "nombramientos",
        "convenio",
        "convenios",
        "comite",
        "comites",
        "disciplina",
        "administracion",
        "notarial",
        "firma",
        "firmas",
        "mando",
        "subordinacion",
        "cadena",
        "iso",
        "erp",
        "estatutario",
        "sancion",
        "sanciones",
        "despido",
        "notario",
        "expedientacion",
    ),
    # P6: liquidez, balance, crédito, mercado y deuda (más allá de keywords_short).
    "P6": (
        "cash",
        "tesoreria",
        "liquidez",
        "ebitda",
        "burn",
        "solvencia",
        "rating",
        "balance",
        "deuda",
        "credito",
        "capex",
        "opex",
        "apalancamiento",
        "quiebra",
        "default",
        "spread",
        "bono",
        "bonos",
        "dividendo",
        "fusion",
        "adquisicion",
        "valoracion",
        "patrimonio",
        "colateral",
        "rescate",
        "refinanciacion",
        "working",
        "mercado",
        "bursatil",
        "junk",
        "yield",
        "swap",
        "covenant",
        "covenants",
        "apalancado",
        "endeudamiento",
        "cashflow",
    ),
    # P7: soberanía, aparato coactivo, constitución, frontera, guerra/diplomacia (más allá de keywords_short).
    "P7": (
        "estado",
        "soberania",
        "constitucion",
        "ejercito",
        "policia",
        "frontera",
        "fronteras",
        "guerra",
        "diplomacia",
        "tratado",
        "tratados",
        "regimen",
        "parlamento",
        "gobierno",
        "nacion",
        "territorio",
        "defensa",
        "coaccion",
        "legitimidad",
        "eleccion",
        "elecciones",
        "insurgencia",
        "bloqueo",
        "sanciones",
        "geopolitica",
        "alianza",
        "otan",
        "onu",
        "fronterizo",
        "soberano",
        "ordenamiento",
        "violencia",
        "carcel",
        "inteligencia",
        "ciberdefensa",
        "fiscal",
        "recaudacion",
        "impuesto",
        "impuestos",
        "autarquia",
        "planificacion",
    ),
    # P8 ESTRATÉGICO: crisis, maniobra, planes ante escenarios; maniobra ante reguladores (no la norma en sí: P5).
    "P8": (
        "crisis",
        "crises",
        "crisis management",
        "contingency",
        "remediation",
        "response plan",
        "turnaround",
        "damage control",
        "war room",
        "regulators",
        "regulator",
        "regulatory strategy",
        "stakeholder strategy",
        "estrategia",
        "estrategico",
        "estrategica",
        "doctrina",
        "timing",
        "disrupcion",
        "escenario",
        "escenarios",
        "ooda",
        "playbook",
        "roadmap",
        "anticipacion",
        "ventaja",
        "competitiva",
        "competitivo",
        "benchmarking",
        "patron",
        "patrones",
        "inferencia",
        "wargame",
        "maniobra",
        "maniobras",
        "asimetria",
        "incertidumbre",
        "intel",
        "calculo",
        "tablero",
        "rival",
        "rivales",
        "competidor",
        "first",
        "mover",
        "planeacion",
        "plan",
        "planes",
        "priorizacion",
        "horizonte",
        "ciclo",
        "ciclos",
    ),
    # P9: hardware, software, automatización, patentes y estándares (más allá de keywords_short).
    "P9": (
        "hardware",
        "software",
        "servidor",
        "servidores",
        "datacenter",
        "nube",
        "cloud",
        "ia",
        "algoritmo",
        "algoritmos",
        "codigo",
        "encriptacion",
        "blockchain",
        "api",
        "apis",
        "rpa",
        "automatizacion",
        "robot",
        "robots",
        "patente",
        "patentes",
        "estandar",
        "estandares",
        "licencia",
        "licencias",
        "stack",
        "firmware",
        "chipset",
        "gpu",
        "fibra",
        "satelite",
        "ciberseguridad",
        "malware",
        "ransomware",
        "backup",
        "backups",
        "pipeline",
        "devops",
        "kubernetes",
        "microservicio",
        "microservicios",
        "saas",
        "paas",
        "iot",
        "sensor",
        "sensores",
        "flops",
    ),
    # P10 CULTURAL: sentido, valores, confianza y reputación (percepción pública, marca).
    "P10": (
        "trust",
        "trusted",
        "reputation",
        "reputational",
        "public perception",
        "perception",
        "credibility",
        "credible",
        "brand trust",
        "stakeholder trust",
        "verdad",
        "verdades",
        "cosmovision",
        "epistemologia",
        "hipotesis",
        "evidencia",
        "evidencias",
        "metodo",
        "cientifico",
        "cientifica",
        "academia",
        "academico",
        "academica",
        "filosofia",
        "etica",
        "deontologia",
        "canon",
        "doctrina",
        "doctrinas",
        "legitimidad",
        "legitimacion",
        "ideologia",
        "ideologias",
        "mito",
        "mitos",
        "dogma",
        "dogmas",
        "tabu",
        "tabues",
        "biblioteca",
        "bibliotecas",
        "museo",
        "museos",
        "archivo",
        "archivos",
        "patrimonio",
        "laboratorio",
        "laboratorios",
        "revista",
        "revistas",
        "peer",
        "seminario",
        "seminarios",
        "investigacion",
        "teorico",
        "teorica",
        "creatividad",
        "conceptual",
        "consenso",
        "proposito",
        "purpose",
        "valores",
        "sentido",
        "doxa",
        "hermeneutica",
        # Discurso «safety as culture» (percepción, confianza): complementa P5 normativo.
        "safety culture",
        "cultura de seguridad",
        "seguridad cultural",
        "just culture",
        "psychological safety",
        "high reliability culture",
    ),
}


def _normalize_text(text: str) -> str:
    # Limpieza suave para PDFs: colapsa saltos y espacios repetidos.
    t = text.replace("\u00a0", " ")
    t = re.sub(r"\s+", " ", t).strip()
    # Algunos extractores PDF sustituyen el símbolo € por «!» junto a cifras (dividendo, bn).
    t = re.sub(
        r"(?i)(dividend\s+of\s*)!(?=\s*[\d.,]+\s+per\s+share)",
        r"\1€",
        t,
    )
    t = re.sub(
        r"(?i)!\s*(?=[\d.,]+\s*(?:billion|bn)\b)",
        r"€ ",
        t,
    )
    # Normalizamos acentos para facilitar matching determinista.
    t = unicodedata.normalize("NFKD", t)
    t = "".join(c for c in t if not unicodedata.combining(c))
    return t


def _keyword_occurrences(text_lower: str, kw: str) -> tuple[int, int]:
    """
    Ocurrencias de kw como token (no subcadena dentro de otra palabra).
    Evita falsos positivos (ej. P7 'guerra' en 'guerras de pasillo').
    `kw` se normaliza como el texto (acentos) para alinear con `keywords_short`.
    """
    if not kw:
        return 0, -1
    kw_clean = _normalize_text(str(kw)).lower().strip()
    if len(kw_clean) < 2:
        return 0, -1
    try:
        pat = re.compile(rf"(?<!\w){re.escape(kw_clean)}(?!\w)", flags=re.IGNORECASE)
    except re.error:
        return 0, -1
    matches = list(pat.finditer(text_lower))
    if not matches:
        return 0, -1
    return len(matches), matches[0].start()


def _p8_strategic_crisis_occurrences(text_lower: str) -> tuple[int, int]:
    """
    Cuenta 'crisis' / 'crises' para P8 excluyendo crisis biológica/somática (P1) y
    'biological crisis' (inglés). La seguridad operativa normativa sigue en P5, no aquí.
    """
    pat = re.compile(r"(?<!\w)(crisis|crises)(?!\w)", flags=re.IGNORECASE)
    matches = list(pat.finditer(text_lower))
    if not matches:
        return 0, -1
    kept: list[re.Match[str]] = []
    for m in matches:
        window = text_lower[max(0, m.start() - 18) : m.end() + 40]
        if re.search(
            r"crisis\s*:?\s*("
            r"biologica|biologico|biologicos|biologicas|"
            r"somatica|somaticas|medica|medicas|fisiologica|metabolica|sanitaria"
            r")\b",
            window,
            flags=re.IGNORECASE,
        ):
            continue
        if re.search(r"\bbiological\s+crisis\b", window, flags=re.IGNORECASE):
            continue
        # Salud / sanidad (P1 o discurso público; no tablero estratégico P8).
        if re.search(
            r"(?:\b(?:public|mental|global|occupational|workplace|employee)\s+)?health\s+crisis\b",
            window,
            flags=re.IGNORECASE,
        ):
            continue
        if re.search(r"\bcrisis\s+de\s+salud\b", window, flags=re.IGNORECASE):
            continue
        if re.search(r"\bcrisis\s+del\s+sistema\s+de\s+salud\b", window, flags=re.IGNORECASE):
            continue
        kept.append(m)
    if not kept:
        return 0, -1
    return len(kept), kept[0].start()


def _p10_safety_narrative_bonus(text_lower: str) -> tuple[int, int]:
    """
    +1 si «safety»/«seguridad» coocurre con cultura/confianza/reputación en ventana corta (P10).
    No suma si ya hay frase fija («safety culture», «cultura de seguridad», etc.) para evitar doble conteo.
    Excluye «cultura de cumplimiento» / «culture of compliance» (sesgo P5 normativo, no discurso P10).
    """
    fixed = (
        r"\bsafety\s+culture\b",
        r"\bcultura\s+de\s+seguridad\b",
        r"\bseguridad\s+cultural\b",
        r"\bjust\s+culture\b",
        r"\bpsychological\s+safety\b",
        r"\bhigh\s+reliability\s+culture\b",
    )
    for fx in fixed:
        if re.search(fx, text_lower, flags=re.IGNORECASE):
            return 0, -1
    # Ancla «cultural» P10: no contar cultura/culture puramente de cumplimiento o control normativo.
    cult_p10 = (
        r"cultura(?! de cumplimiento)(?! del cumplimiento)(?! normativa\b)(?! regulatoria\b)"
        r"(?! de control\b)(?! del control\b)"
    )
    culture_p10 = (
        r"culture(?! of compliance)(?! of control)(?! of conformance)(?! and compliance\b)"
    )
    anchor = (
        r"(?:trust|trusted|reputation|reputacion|reputational|valores|perception|percepcion|"
        r"credibility|credible|brand|" + cult_p10 + r"|" + culture_p10 + r")"
    )
    pair_patterns = (
        rf"(?is)(?<!\w)(?:safety|seguridad)(?!\w).{{0,140}}?(?<!\w){anchor}(?!\w)",
        rf"(?is)(?<!\w){anchor}(?!\w).{{0,140}}?(?<!\w)(?:safety|seguridad)(?!\w)",
    )
    first = -1
    for pat in pair_patterns:
        m = re.search(pat, text_lower)
        if not m:
            continue
        span = text_lower[m.start() : m.end()]
        # Refuerzo: ventana con fuerte sesgo solo normativo (auditoría/FAA/procedimiento) sin señal blanda P10.
        if re.search(
            r"(?:faa|easa|audit|auditoria|as9100|part\s*21|part\s*145|"
            r"compliance|cumplimiento|normativa|regulatory|procedimiento obligatorio)",
            span,
            flags=re.IGNORECASE,
        ) and not re.search(
            r"(?:trust|reputation|reputacion|perception|percepcion|credibility|valores|brand)",
            span,
            flags=re.IGNORECASE,
        ):
            continue
        if first < 0 or m.start() < first:
            first = m.start()
    if first < 0:
        return 0, -1
    return 1, first


# Umbral: por debajo, sospechamos PDF imagen u OCR necesario (tras agotar extractores).
MIN_EXTRACTED_CHARS_WARNING = 100

# Protocolo de veto estructural — palabras de ruptura (texto normalizado sin tildes).
# Prioridad absoluta: no se promedian con señales positivas; fuerzan colapso a ruptura (score 1).
KEYWORDS_RUPTURA: tuple[str, ...] = (
    "vaciamiento",
    "insolvente",
    "critico",
    "desaparecido",
    "esqueleto",
    "caida",
    "ninguno",
)
# Multiplicador 5x de impacto negativo sobre el score si no hay colapso total por KEYWORDS_RUPTURA.
NEGATIVE_LEXICON_5X: tuple[str, ...] = ("vacio", "desaparecido", "critico", "ninguno")


def _keywords_ruptura_in_window(t_lower: str, center: int, radius: int = 280) -> bool:
    """True si alguna KEYWORDS_RUPTURA aparece en la ventana del ancla (nodo Pi asociado al match)."""
    if center < 0:
        return False
    a = max(0, center - radius)
    b = min(len(t_lower), center + radius)
    win = t_lower[a:b]
    for w in KEYWORDS_RUPTURA:
        if re.search(rf"(?<!\w){re.escape(w)}(?!\w)", win, flags=re.IGNORECASE):
            return True
    return False


def _rupture_hit_in_window(t_lower: str, center: int, radius: int = 280) -> bool:
    """Alias: ruptura = solo KEYWORDS_RUPTURA (veto estructural)."""
    return _keywords_ruptura_in_window(t_lower, center, radius=radius)


def _negative_lexicon_5x_penalty(t_lower: str, center: int, radius: int = 280) -> int:
    """Penalización adicional al score (5x por ocurrencia de términos críticos)."""
    if center < 0:
        return 0
    a = max(0, center - radius)
    b = min(len(t_lower), center + radius)
    win = t_lower[a:b]
    n = 0
    for w in NEGATIVE_LEXICON_5X:
        n += len(list(re.finditer(rf"(?<!\w){re.escape(w)}(?!\w)", win, flags=re.IGNORECASE)))
    return 5 * n


def _raw_pages_pdfplumber(pdf_bytes: bytes) -> list[str]:
    try:
        import pdfplumber  # type: ignore
    except ImportError:
        return []
    try:
        out: list[str] = []
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for page in pdf.pages:
                try:
                    out.append(page.extract_text() or "")
                except Exception:
                    out.append("")
        return out
    except Exception:
        return []


def _raw_pages_pypdf_family(pdf_bytes: bytes) -> tuple[list[str], str]:
    """
    Prueba pypdf y PyPDF2; devuelve la extracción con más caracteres en bruto.
    """
    readers: list[tuple[str, Any]] = []
    try:
        from pypdf import PdfReader as PR  # type: ignore

        readers.append(("pypdf", PR))
    except Exception:
        pass
    try:
        from PyPDF2 import PdfReader as PR2  # type: ignore

        readers.append(("PyPDF2", PR2))
    except Exception:
        pass

    best_pages: list[str] = []
    best_label = ""
    best_score = -1
    for label, Reader in readers:
        try:
            reader = Reader(io.BytesIO(pdf_bytes))
            pages: list[str] = []
            for page in reader.pages:
                try:
                    pages.append(page.extract_text() or "")
                except Exception:
                    pages.append("")
            score = sum(len(p) for p in pages)
            if score > best_score:
                best_score = score
                best_pages = pages
                best_label = label
        except Exception:
            continue
    return best_pages, best_label


def extract_page_chunks_from_pdf_bytes_detailed(pdf_bytes: bytes) -> tuple[list[str], dict[str, Any]]:
    """
    Por página: elige el texto más largo entre pdfplumber y pypdf/PyPDF2 (informes con layout raro).
    Devuelve fragmentos normalizados y metadatos para UI (caracteres por página, sospecha OCR).
    """
    meta: dict[str, Any] = {
        "method": None,
        "per_page_chars": [],
        "total_chars_raw": 0,
        "ocr_suspected": False,
        "pages_count": 0,
    }
    if not pdf_bytes:
        meta["ocr_suspected"] = True
        return [], meta

    r_pm = _raw_pages_pdfplumber(pdf_bytes)
    r_py, py_label = _raw_pages_pypdf_family(pdf_bytes)

    n = max(len(r_pm), len(r_py))
    meta["pages_count"] = n
    merged_raw: list[str] = []
    per_page_chars: list[int] = []
    for i in range(n):
        a = r_pm[i] if i < len(r_pm) else ""
        b = r_py[i] if i < len(r_py) else ""
        best = a if len(a) >= len(b) else b
        merged_raw.append(best)
        per_page_chars.append(len(best))

    method_bits = []
    if any(r_pm):
        method_bits.append("pdfplumber")
    if any(r_py):
        method_bits.append(py_label or "pypdf")
    meta["method"] = " + ".join(method_bits) if method_bits else "ninguno"
    meta["per_page_chars"] = per_page_chars
    meta["total_chars_raw"] = int(sum(per_page_chars))

    chunks: list[str] = []
    for raw in merged_raw:
        nrm = _normalize_text(raw)
        if nrm:
            chunks.append(nrm)

    total_norm = sum(len(c) for c in chunks)
    if meta["total_chars_raw"] < MIN_EXTRACTED_CHARS_WARNING and n > 0:
        meta["ocr_suspected"] = True
    elif total_norm < MIN_EXTRACTED_CHARS_WARNING and n > 0:
        meta["ocr_suspected"] = True

    return chunks, meta


def extract_page_chunks_from_pdf_bytes(pdf_bytes: bytes) -> list[str]:
    """Un fragmento por página con texto (normalizado)."""
    chunks, _ = extract_page_chunks_from_pdf_bytes_detailed(pdf_bytes)
    return chunks


def extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """
    Texto completo del PDF (páginas unidas). Para ingest por fragmentos usar
    `extract_page_chunks_from_pdf_bytes` + `propose_pi_notes_from_chunks`.
    """
    chunks = extract_page_chunks_from_pdf_bytes(pdf_bytes)
    if not chunks:
        return ""
    return _normalize_text("\n\n".join(chunks))


def extract_uploaded_pdfs_with_stats(uploaded_files: list[Any]) -> tuple[list[str], dict[str, Any]]:
    """
    Concatena fragmentos de todos los archivos. **Siempre hace seek(0) antes de read()**
    (Streamlit UploadedFile agota el buffer si no se rebobina).
    """
    if not uploaded_files:
        return [], {"files": [], "total_chars_raw": 0, "ocr_suspected": False}

    all_chunks: list[str] = []
    files_meta: list[dict[str, Any]] = []
    total_raw = 0
    any_ocr = False

    for f in uploaded_files:
        try:
            if hasattr(f, "seek"):
                f.seek(0)
            b = f.read()
        except Exception:
            b = b""
        if not b:
            continue
        chunks, meta = extract_page_chunks_from_pdf_bytes_detailed(b)
        all_chunks.extend(chunks)
        name = getattr(f, "name", "documento.pdf")
        files_meta.append({"name": name, **meta})
        total_raw += int(meta.get("total_chars_raw", 0))
        any_ocr = any_ocr or bool(meta.get("ocr_suspected"))

    return all_chunks, {
        "files": files_meta,
        "total_chars_raw": total_raw,
        "ocr_suspected": any_ocr,
    }


def extract_page_chunks_from_uploaded_pdfs(uploaded_files: list[Any]) -> list[str]:
    """Concatena fragmentos por página de todos los archivos (orden de subida)."""
    chunks, _ = extract_uploaded_pdfs_with_stats(uploaded_files)
    return chunks


def extract_text_from_uploaded_pdfs(uploaded_files: list[Any]) -> str:
    """Texto agregado (misma semántica que unir fragmentos de página)."""
    chunks = extract_page_chunks_from_uploaded_pdfs(uploaded_files)
    return join_text_chunks(chunks)


def _keywords_from_poder(p_code: str, power_keywords_short: str) -> list[str]:
    # keywords_short en engine_akxom viene con separadores tipo " · " y palabras puntuales.
    raw = power_keywords_short or ""
    parts = re.split(r"[·,;|/]+", raw)
    out: list[str] = []
    for p in parts:
        w = p.strip().lower()
        if len(w) >= 3:
            out.append(w)
    extra = DOC_EXTRA_KEYWORDS.get(p_code, ())
    for w in extra:
        ww = w.strip().lower()
        if len(ww) >= 3 and ww not in out:
            out.append(ww)
    return out


def _window_is_regulator_compliance_tone(text_lower: str, start: int, end: int) -> bool:
    """Informes anuales: 'regulatory compliance' no es crisis operativa."""
    a = max(0, start - 56)
    b = min(len(text_lower), end + 56)
    w = text_lower[a:b]
    if re.search(
        r"regulatory\s+(compliance|requirements|filings|oversight|reporting)|"
        r"meet\s+regulatory|regulatory\s+standards|regulators\s+expect",
        w,
        flags=re.IGNORECASE,
    ):
        return True
    return False


def _count_tension_token_hits(text_lower: str, token: str) -> tuple[int, int]:
    """
    Cuenta ocurrencias de un token de tensión separando:
    - positivas (señal de crisis real)
    - negadas/estables (ej: "sin deuda", "no hay liquidez tensionada")
    """
    escaped = re.escape(token)
    base_hits = list(re.finditer(escaped, text_lower))
    if not base_hits:
        return 0, 0

    neg_patterns = [
        rf"(no|sin|ausencia de|sin señales de)\s+[\w\s]{{0,18}}{escaped}",
        rf"{escaped}[\w\s]{{0,60}}(controlad[oa]s?|estable|en rango|sin tension|sin riesgo|acotad[oa]|minim[oa]|nul[oa]|limitad[oa]|contenid[oa]|moderad[oa]|bajo\s+y|baja\s+incidencia)",
    ]

    compliance_neg = 0
    to_check: list[re.Match[str]] = []
    for m in base_hits:
        if token == "regulator" and _window_is_regulator_compliance_tone(text_lower, m.start(), m.end()):
            compliance_neg += 1
            continue
        to_check.append(m)

    pattern_neg = 0
    for m in to_check:
        start = max(0, m.start() - 32)
        end = min(len(text_lower), m.end() + 60)
        window = text_lower[start:end]
        if any(re.search(pat, window) for pat in neg_patterns):
            pattern_neg += 1

    positive = max(0, len(to_check) - pattern_neg)
    negated_total = compliance_neg + pattern_neg
    return positive, negated_total


def _macro_risk_disclosure_context(text_lower: str) -> bool:
    """Riesgo macro / geopolítico típico de informe anual (no implica falla operativa propia)."""
    return bool(
        re.search(
            r"\b(war\s+in|ukraine|geopolitic|macro[-\s]?economic|global\s+instability|"
            r"economic\s+uncertainty|inflation(ary)?\s+pressures|sanctions?\b|russian\s+war)\b",
            text_lower,
            flags=re.IGNORECASE,
        )
    )


def _big_tech_financial_scale(text_lower: str) -> bool:
    """
    Escala tipo mega-cap US (Microsoft / Apple / Google): ingresos y beneficio neto en decenas
    de miles de millones USD. Sirve para no leer «fricción léxica» de annual masivo como crisis.
    """
    rev_mega = bool(
        re.search(
            r"(revenue|revenues|total\s+revenues?|sales).{0,160}\$[\s]*(?:2[0-9]{2}|1[89][0-9])\s*billion",
            text_lower,
            flags=re.IGNORECASE,
        )
        or re.search(
            r"\$[\s]*(?:2[0-9]{2}|1[89][0-9])\s*billion.{0,120}(revenue|revenues|sales|year)",
            text_lower,
            flags=re.IGNORECASE,
        )
    )
    # US GAAP 10-K: a veces «net income 88,308» en millones (≈ decenas de miles de millones USD), no «$88 billion».
    ni_mega = bool(
        re.search(
            r"net\s+income.{0,220}\$[\s]*(?:[4-9][0-9]|1[0-9]{2})\s*billion",
            text_lower,
            flags=re.IGNORECASE,
        )
        or re.search(
            r"net\s+income.{0,260}(?:[6-9][0-9]|1[0-9]{2})\s*,\s*[0-9]{3}\b",
            text_lower,
            flags=re.IGNORECASE,
        )
    )
    return rev_mega and ni_mega


def _large_cap_revenue_anchor(text_lower: str) -> bool:
    """
    Ingresos anuales muy elevados (large cap / enterprise consolidado), sin exigir escala «mega-cap»
    tipo $200B+ (p. ej. IBM ~$60B). Complementa big_tech para reglas de inercia / soberanía.
    """
    return bool(
        re.search(
            r"(revenue|revenues|total\s+revenues?|sales).{0,180}\$[\s]*(?:[4-9][0-9]|[1-9][0-9]{2})\s*billion",
            text_lower,
            flags=re.IGNORECASE,
        )
        or re.search(
            r"\$[\s]*(?:[4-9][0-9]|[1-9][0-9]{2})\s*billion.{0,120}(revenue|revenues|annual|year)",
            text_lower,
            flags=re.IGNORECASE,
        )
    )


def _p9_moat_hardening_narrative(text_lower: str) -> bool:
    """
    Iniciativas de seguridad / plataforma AI como refuerzo de foso, no como señal de crisis
    (evita que el autofill trate el disclosure como «tensión» en P9).
    """
    return bool(
        re.search(
            r"(secure\s+future\s+initiative|secure\s+by\s+design|secure\s+by\s+default|"
            r"trustworthy\s+ai|ai\s+platform\s+shift|second\s+year\s+of\s+the\s+ai\s+platform|"
            r"azure\s+openai|copilot\b|"
            r"cybersecurity.{0,96}(initiative|program|layered|invest|posture)|"
            r"zero\s+trust)",
            text_lower,
            flags=re.IGNORECASE,
        )
    )


def _financial_performance_anchor(text_lower: str) -> bool:
    """
    Señales de desempeño financiero/comercial fuerte (ancla frente al cinismo léxico).
    Por defecto exige 2 familias; con contexto macro (annual con guerra/IFRS) basta 1 señal fuerte.
    """
    hits = 0
    if re.search(
        r"(order\s+backlog|backlog\s*[\(€$]|\bbacklog\s+of|record\s+order|orders?\s+intake|"
        r"commercial\s+aircraft.{0,40}order)",
        text_lower,
        flags=re.IGNORECASE,
    ):
        hits += 1
    if re.search(
        r"(net\s+cash|gross\s+cash|strong(er)?\s+(year[\s-]end\s+)?net\s+cash|"
        r"net\s+cash\s+position|cash\s+position.{0,48}(strong|solid|robust))",
        text_lower,
        flags=re.IGNORECASE,
    ):
        hits += 1
    if re.search(
        r"(dividend\s+of\s*[!€$]?\s*[\d.,]+\s+per\s+share|dividend\s+of\s*[€$]|"
        r"proposed\s+dividend|[€$!]\s*[\d.,]+\s+per\s+share|"
        r"per\s+share.{0,20}dividend|special\s+dividend)",
        text_lower,
        flags=re.IGNORECASE,
    ):
        hits += 1
    if re.search(
        r"(record\s+revenues?|record\s+results?|revenues?\s+(of|reached|totalled)|"
        r"[€!]\s*[\d.]+\s*billion.{0,30}(revenue|turnover)|"
        r"[€!]\s*[\d.]+\s*bn\b|\b\d+\s*bn\b.{0,24}[€!])",
        text_lower,
        flags=re.IGNORECASE,
    ):
        hits += 1
    macro_local = _macro_risk_disclosure_context(text_lower)
    if macro_local and hits >= 1:
        return True
    return hits >= 2


def _hard_red_financial_distress(text_lower: str) -> bool:
    """
    Señales graves reales. NO usar la subcadena «going concern» sola: en IFRS/US GAAP
    aparece en el párrafo contable estándar («prepared on a going concern basis») y
    anulaba erróneamente el perfil con ancla financiera (p. ej. Airbus).
    """
    # «material weakness» en el alcance del auditor (PCAOB/ISA) no es admisión del emisor.
    if re.search(
        r"(identified|concluded\s+that|we\s+identified|there\s+were)\s+(a\s+)?material\s+weakness|"
        r"material\s+weaknesses?\s+in\s+our\s+internal\s+control.{0,120}(existed|not\s+been\s+remediated|"
        r"remain|continued)|"
        r"material\s+weakness\s+.*\s+has\s+not\s+been\s+remediated",
        text_lower,
        flags=re.IGNORECASE,
    ):
        return True
    if re.search(r"\bbankruptcy\s+filing\b|\bchapter\s+11\b", text_lower, flags=re.IGNORECASE):
        return True
    # No enlazar going concern → material uncertainty en ventana corta: el informe del auditor
    # (ISA) suele decir «continue as a going concern. If we conclude that a material uncertainty…»
    # sin que la compañía esté en distress.
    return bool(
        re.search(
            r"(substantial\s+doubt|material\s+uncertainty).{0,120}going\s+concern|"
            r"going\s+concern.{0,80}(substantial\s+doubt|"
            r"unable\s+to\s+continue|may\s+not\s+be\s+able\s+to\s+continue|"
            r"cease\s+(operations|trading))",
            text_lower,
            flags=re.IGNORECASE,
        )
    )


def _substantive_going_concern_crisis(text_lower: str) -> bool:
    """Cuenta «going concern» como crisis solo si va ligado a duda material explícita."""
    return bool(
        re.search(
            r"(substantial\s+doubt|material\s+uncertainty).{0,120}going\s+concern|"
            r"going\s+concern.{0,80}(substantial\s+doubt|"
            r"unable\s+to\s+continue|liquidity\s+shortfall|covenant\s+breach)",
            text_lower,
            flags=re.IGNORECASE,
        )
    )


def _critical_incident_evidence(text_lower: str) -> bool:
    """
    Daño operativo propio de aviación / control regulador directo sobre la compañía.
    Excluye grounding genérico de competidor (p. ej. 737 MAX en informe de Airbus) y
    fatalidades descontextualizadas (p. ej. guerra en nota de riesgo macro).
    """
    patterns = (
        r"separated\s+from\s+the\s+(airplane|aircraft|fuselage|plane)\b",
        r"separated\s+from\s+.{0,32}during\s+flight",
        r"\bdoor\s+plug\b",
        r"\bplug\s+door\b",
        r"\bmcas\b",
        r"mid[\s-]?flight\s+(blowout|decompression|emergency|incident)",
        r"explosive\s+decompression",
        r"\bin-flight\s+emergency\b",
        r"\bhull\s+loss\b",
        # DPA/consent solo si van ligados a regulación aeronáutica (no DPA anticorrupción tipo SFO en annual).
        r"\bdeferred\s+prosecution\b.{0,140}\b(faa|ntsb|easa|federal\s+aviation|"
        r"civil\s+aviation|flight\s+safety|airworthiness|type\s+certificate)\b",
        r"\bconsent\s+decree\b.{0,140}\b(faa|ntsb|easa|federal\s+aviation|civil\s+aviation|"
        r"airworthiness)\b",
        r"\bfatalit(y|ies)\b.{0,72}\b(aircraft|aviation|passengers?|on\s+board|in\s+flight)\b",
        r"\bloss\s+of\s+life\b.{0,72}\b(aircraft|aviation|passengers?|flight)\b",
        r"\bntsb\b",
        r"\bffaa\b.{0,72}\b(civil\s+penalt|penalt(y|ies)|enforcement\s+action|consent\s+decree)\b",
        # «investigation» genérico + fiscalía penal (p. ej. Airbus) no es incidente de flota; exigir regulador.
        r"\baccident\b.{0,48}\b(ntsb|national\s+transportation\s+safety|"
        r"\bfaa\b|easa|european\s+union\s+aviation\s+safety)\b",
        # No «investigation»+FAA genérico ni grounding con nombre OEM (falsos positivos en annuals).
        r"\bour\b.{0,56}\b(fleet|aircraft)\b.{0,40}\bground(ed|ing)\b",
        r"\bgrounding\s+of\s+our\b",
    )
    return any(re.search(p, text_lower, flags=re.IGNORECASE) for p in patterns)


def _established_sec_periodic_filing(text_lower: str) -> bool:
    """
    Informe periódico SEC de emisor ya cotizado (10-K), no prospecto de oferta.
    Si está presente, no debe activarse contexto S-1/IPO ni arquetipo Ignición por ese camino.

    Excluye menciones prospecto («upon becoming a public company… Form 10-K») típicas de un S-1.
    """
    if re.search(
        r"annual\s+report\s+pursuant\s+to\s+section\s+13\s+or\s+15\s*\(\s*d\s*\)",
        text_lower,
        flags=re.IGNORECASE,
    ):
        return True
    if re.search(
        r"\btransition\s+report\s+pursuant\s+to\s+section\s+13\s+or\s+15\s*\(\s*d\s*\)",
        text_lower,
        flags=re.IGNORECASE,
    ):
        return True
    for m in re.finditer(r"\bform\s+10-k\b", text_lower, flags=re.IGNORECASE):
        ctx = text_lower[max(0, m.start() - 420): min(len(text_lower), m.end() + 420)]
        if re.search(
            r"upon\s+becoming\s+a\s+public\s+company|prior\s+to\s+this\s+offering|"
            r"registration\s+statement\s+on\s+form\s+s-1|"
            r"as\s+a\s+public\s+company,\s+we\s+will\s+be\s+required",
            ctx,
            flags=re.IGNORECASE,
        ):
            continue
        return True
    return False


def _financial_decay_stress_signals(text_lower: str) -> bool:
    """
    Señales de decadencia operativa en large cap: ingresos a la baja, caja débil, pérdidas.
    (p. ej. Intel: revenue down, FCF bajo presión.)
    """
    return bool(
        re.search(
            r"(revenue|revenues|net\s+revenue|sales).{0,220}"
            r"(decreased|decline|declined|down\s+\d|fell|lower\s+than|"
            r"year[\s-]over[\s-]year.{0,20}(decrease|decline|down))",
            text_lower,
            flags=re.IGNORECASE,
        )
    ) or bool(
        re.search(
            r"(\d{1,2})\s*%\s*(decrease|decline|reduction).{0,120}(revenue|revenues|sales)",
            text_lower,
            flags=re.IGNORECASE,
        )
    ) or bool(
        re.search(
            r"free\s+cash\s+flow.{0,200}(negative|\(\s*\$|\(\$|\(1|,?\d+\)\s*million\s+of\s+free\s+cash)",
            text_lower,
            flags=re.IGNORECASE,
        )
    ) or bool(
        re.search(
            r"(net\s+loss|operating\s+loss).{0,120}(\$\s*\d|million|billion)",
            text_lower,
            flags=re.IGNORECASE,
        )
    )


def _eu_prospectus_regulation_boilerplate(text_lower: str) -> bool:
    """
    Informes europeos citan el Reglamento (UE) 2017/1129 («Prospectus Regulation»);
    no es un S-1 / IPO US. Evita falsos positivos en annuals tipo Airbus.
    """
    return bool(
        re.search(
            r"2017/1129|regulation\s*\(?\s*eu\s*\)?\s*2017|"
            r"prospectus\s+regulation\)?\s+without\s+prior\s+approval|"
            r"«prospectus\s+regulation»|\"prospectus\s+regulation\"",
            text_lower,
            flags=re.IGNORECASE,
        )
    )


def _offering_prospectus_ipo_context(text_lower: str) -> bool:
    """
    S-1, prospecto u oferta pública (IPO US): lenguaje de salida a bolsa, no nota al pie
    de cumplimiento en un annual IFRS europeo.
    """
    # Exclusión mutua: 10-K / informe anual SEC ≠ prospecto de oferta.
    if _established_sec_periodic_filing(text_lower):
        return False

    if re.search(
        r"\bform\s+s-1\b|\bregistration\s+statement\s+on\s+form\s+s-1\b|\bs-1\s+registration\b",
        text_lower,
        flags=re.IGNORECASE,
    ):
        return True

    # Tras S-1 inequívoco: bloquear heurísticas débiles en annuals UE (p. ej. Airbus)
    # que citan 2017/1129 y/o mencionan un IPO histórico en notas al pie.
    if _eu_prospectus_regulation_boilerplate(text_lower):
        return False

    if re.search(r"\binitial\s+public\s+offering\b", text_lower, flags=re.IGNORECASE):
        return True
    if re.search(r"\bipo\b", text_lower, flags=re.IGNORECASE) and re.search(
        r"\b(offering|underwrit|nasdaq|nyse|class\s+[a-z]\s+common|common\s+stock)\b",
        text_lower,
        flags=re.IGNORECASE,
    ):
        return True

    # Patrón débil: «prospectus» + mercado primario. Los annuals suelen tener
    # «registration statement» en otros contextos — no usarlo aquí.
    if re.search(r"\bprospectus\b", text_lower, flags=re.IGNORECASE) and re.search(
        r"\b(underwrit|selling\s+stockholder|common\s+stock|this\s+offering|class\s+[a-z]\s+common)\b",
        text_lower,
        flags=re.IGNORECASE,
    ):
        return True
    return False


def _prospectus_profitability_lift(text_lower: str) -> bool:
    """
    Relaja el cap P5/P6 en prospecto solo ante rentabilidad neta explícita y material en el texto.
    """
    if re.search(
        r"\bnet\s+income\s+of\s+\$?\s*[\d,]+\s*(million|billion)\b",
        text_lower,
        flags=re.IGNORECASE,
    ):
        return True
    if re.search(
        r"\bnet\s+income\b.{0,120}\b(positive|profit)\b",
        text_lower,
        flags=re.IGNORECASE,
    ) and re.search(r"\b(million|billion|\$\s*[\d,]{3,})\b", text_lower, flags=re.IGNORECASE):
        return True
    return False


def ingest_disclosure_profile(text_lower: str) -> dict[str, Any]:
    """
    Separa «contexto de riesgo / disclosure» (informe anual sano) de «evidencia de crisis».
    Usado para calibrar tensión de ingesta y auto-fill (Fase 2.7).
    """
    positive_markers = (
        "record revenue",
        "record year",
        "fiscal year",
        "annual report",
        "dear shareholder",
        "shareholders",
        "dividend",
        "strong momentum",
        "innovation",
        "proud to",
        "resilient",
        "trusted",
        "secure by design",
        "commitment to",
        "excellence",
        "milestone",
        "recognized as",
        "leading",
    )
    crisis_markers = (
        "material weakness",
        "bankruptcy",
        "layoff",
        "lawsuit",
        "subpoena",
        "catastrophic",
        "data breach",
        "ransomware",
        "impairment charge",
        "restructuring charge",
        "investigation by the",
        "criminal charges",
        "securities and exchange commission enforcement",
    )
    pos = sum(1 for m in positive_markers if m in text_lower)
    cr = sum(1 for m in crisis_markers if m in text_lower)
    if _substantive_going_concern_crisis(text_lower):
        cr += 4
    macro_ctx = _macro_risk_disclosure_context(text_lower)
    fin_anchor = _financial_performance_anchor(text_lower)
    big_tech_scale = _big_tech_financial_scale(text_lower)
    large_cap_revenue = _large_cap_revenue_anchor(text_lower)
    p9_moat_narrative = _p9_moat_hardening_narrative(text_lower)
    established_sec_filing = _established_sec_periodic_filing(text_lower)
    financial_decay_stress = _financial_decay_stress_signals(text_lower)
    critical_incident = _critical_incident_evidence(text_lower)
    offering_prospectus_context = _offering_prospectus_ipo_context(text_lower)
    if established_sec_filing:
        offering_prospectus_context = False
    prospectus_profitability_lift = _prospectus_profitability_lift(text_lower)

    for w in ("failure", "failures", "accident", "catastrophic loss"):
        add = min(6, text_lower.count(w))
        if macro_ctx and not critical_incident:
            add = min(add, 2)
        cr += add
    for w in ("growth", "innovation", "strong", "record"):
        pos += min(6, text_lower.count(w))

    if fin_anchor and not critical_incident:
        strong_crisis = False
        cr_eff = min(float(cr), 9.0)
        hard_red = _hard_red_financial_distress(text_lower)
        # Ancla financiera + ausencia de incidente; pos mínimo evita extractos vacíos.
        healthy = not hard_red and cr_eff <= 9.0 and pos >= 4
    else:
        strong_crisis = critical_incident or cr >= 10 or (cr >= 7 and pos < 10)
        healthy = (
            pos >= 14
            and cr <= max(5, pos // 5)
            and not strong_crisis
            and not critical_incident
        )

    tension_multiplier = 1.0
    autofill_tension_drop_scale = 1.0
    if healthy:
        tension_multiplier = 0.36
        autofill_tension_drop_scale = 0.42
    elif not strong_crisis and pos >= 12 and cr <= max(6, pos // 4) and pos > cr * 1.8:
        tension_multiplier = 0.52
        autofill_tension_drop_scale = 0.62

    # Mega-cap: el volumen de disclosure no debe traducirse 1:1 en caídas M3/A del autofill.
    if healthy and big_tech_scale:
        autofill_tension_drop_scale = float(min(autofill_tension_drop_scale, 0.36))
        tension_multiplier = float(min(tension_multiplier, 0.30))

    # Prospecto / S-1: no tratar como «informe anual sano» aunque el tono sea pulido.
    if offering_prospectus_context:
        healthy = False
        tension_multiplier = min(float(tension_multiplier), 0.88)
        autofill_tension_drop_scale = min(float(autofill_tension_drop_scale), 0.90)

    return {
        "positive_markers": pos,
        "crisis_markers": cr,
        "healthy_disclosure_bias": healthy,
        "strong_crisis_evidence": strong_crisis,
        "critical_incident_evidence": critical_incident,
        "financial_performance_anchor": fin_anchor,
        "big_tech_scale_anchor": bool(big_tech_scale),
        "large_cap_revenue_anchor": bool(large_cap_revenue),
        "established_sec_periodic_filing": bool(established_sec_filing),
        "financial_decay_stress": bool(financial_decay_stress),
        "p9_moat_hardening_narrative": bool(p9_moat_narrative),
        "macro_risk_disclosure_context": macro_ctx,
        "offering_prospectus_context": bool(offering_prospectus_context),
        "prospectus_profitability_lift": bool(prospectus_profitability_lift),
        "tension_multiplier": float(tension_multiplier),
        "autofill_tension_drop_scale": float(autofill_tension_drop_scale),
    }


def join_text_chunks(chunks: Sequence[str], *, separator: str = "\n\n") -> str:
    """
    Concatena fragmentos (páginas, bloques o ventanas de PDF) con la misma normalización
    que el texto pegado en un solo bloque.
    """
    parts: list[str] = []
    for c in chunks:
        if c is None:
            continue
        n = _normalize_text(str(c))
        if n:
            parts.append(n)
    return separator.join(parts)


def propose_pi_notes_from_text(text: str, snippet_chars: int = 220) -> Dict[str, Dict[str, Any]]:
    """
    Retorna:
      {
        "P1": {"note": "...", "confidence": 78, "score": 4, "keyword": "liquidez", "tension_matched": True},
        ...
      }

    Heurística:
    - Calcula score por keyword occurrences (keywords_short).
    - Si hay match, propone un snippet del primer match (centrado alrededor).
    - Confidence basada en score.
    """
    t_norm = _normalize_text(text)
    if not t_norm:
        return {
            p_code: {
                "note": "",
                "confidence": 50,
                "score": 0,
                "keyword": "",
                "tension_matched": False,
                "tension_keyword": "",
                "tension_score": 0,
                "rupture_collapse": False,
            }
            for p_code, _, _, _ in PODERES_INFO
        }

    t_lower = t_norm.lower()

    tension_tokens = (
        "friccion",
        "deuda",
        "liquidez",
        "regulator",
        "desgaste",
        "conflicto",
        "presion",
        # Tensión emocional / relacional (P2) sin mezclar con P6/P5.
        "miedo",
        "panico",
        "hostilidad",
        "resentimiento",
        "traicion",
        "desafeccion",
        "desconfianza",
        "cinismo",
        # Tensión comunicativa / señal (P3).
        "rumor",
        "filtracion",
        "censura",
        "contradictor",
        "desinformacion",
        "viralidad",
        # Tensión relacional / grafo (P4).
        "boicot",
        "fragmentacion",
        "cisura",
        "faccion",
        "ostracismo",
        # Tensión normativa / institucional (P5).
        "incumplimiento",
        "irregularidad",
        "paralisis",
        "insubordinacion",
        "fraude",
        # Tensión financiera / solvencia (P6).
        "quiebra",
        "insolvencia",
        "burbuja",
        "corrida",
        # Tensión política / soberanía (P7).
        "guerra",
        "golpe",
        "insurreccion",
        "secesion",
        # Tensión estratégica / sorpresa (P8).
        "ceguera",
        "derrota",
        "imprevisto",
        # Tensión tecnológica / ciber (P9).
        "obsolescencia",
        "vulnerabilidad",
        "ciberataque",
        "ransomware",
        "apagon",
        # Tensión cultural / epistémica (P10).
        "posverdad",
        "anomia",
        "nihilismo",
        "paradigma",
    )
    tension_pos_total = 0
    tension_neg_total = 0
    tension_pos_by_token: dict[str, int] = {}
    for tok in tension_tokens:
        pos_hits, neg_hits = _count_tension_token_hits(t_lower, tok)
        tension_pos_by_token[tok] = int(pos_hits)
        tension_pos_total += int(pos_hits)
        tension_neg_total += int(neg_hits)
    # Solo activamos tensión global si la señal positiva supera a la negada.
    global_has_tension = bool(tension_pos_total > tension_neg_total and tension_pos_total >= 1)

    _prof = ingest_disclosure_profile(t_lower)
    _tm = float(_prof.get("tension_multiplier", 1.0))
    if _tm < 1.0:
        for _k in tension_pos_by_token:
            tension_pos_by_token[_k] = max(0, int(round(tension_pos_by_token[_k] * _tm)))
        tension_pos_total = sum(tension_pos_by_token.values())
        global_has_tension = bool(tension_pos_total > tension_neg_total and tension_pos_total >= 1)

    results: Dict[str, Dict[str, Any]] = {}
    for p_code, _, _, kw_short in PODERES_INFO:
        keywords = _keywords_from_poder(p_code, kw_short)

        best_keyword = ""
        best_idx = -1
        score = 0
        match_indices: list[int] = []
        tension_matched = False
        tension_keyword = ""
        tension_score = 0

        p8_crisis_counted = False
        for kw in keywords:
            kw_clean = _normalize_text(str(kw)).lower().strip()
            if p_code == "P8" and kw_clean in ("crisis", "crises"):
                if p8_crisis_counted:
                    continue
                p8_crisis_counted = True
                cnt, idx = _p8_strategic_crisis_occurrences(t_lower)
            else:
                cnt, idx = _keyword_occurrences(t_lower, kw)
            # Contamos ocurrencias como tokens completos (evita subcadenas espurias).
            if cnt <= 0 or idx < 0:
                continue
            score += int(cnt)
            match_indices.append(int(idx))
            if best_idx == -1 or (idx != -1 and idx < best_idx):
                best_idx = idx
                best_keyword = kw

            # Sello de tensión:
            # - si el texto global contiene señales de tensión,
            # - y este poder tuvo un match (score>0),
            #   activamos caída estructural para no quedarnos en "plano".
            # (Así evitamos depender de que el keyword ontológico incluya literalmente "deuda".)
            if global_has_tension:
                tension_matched = True
                tension_score += int(cnt)
                if not tension_keyword:
                    # Preferimos token con señal positiva real (no negada).
                    best_tok = max(tension_pos_by_token, key=lambda k: tension_pos_by_token[k], default="")
                    if best_tok and tension_pos_by_token.get(best_tok, 0) > 0:
                        tension_keyword = best_tok
                    else:
                        for tok in tension_tokens:
                            if tok in t_lower:
                                tension_keyword = tok
                                break

        if p_code == "P10":
            p10_b, p10_i = _p10_safety_narrative_bonus(t_lower)
            if p10_b > 0:
                score += p10_b
                if global_has_tension:
                    tension_matched = True
                    tension_score += p10_b
                if p10_i >= 0:
                    match_indices.append(int(p10_i))
                if best_idx < 0 or (p10_i >= 0 and p10_i < best_idx):
                    best_idx = p10_i
                    if not best_keyword:
                        best_keyword = "safety narrative"

        rupture_collapse = False
        rupture_anchor = -1
        for midx in match_indices:
            if _keywords_ruptura_in_window(t_lower, midx):
                rupture_collapse = True
                rupture_anchor = midx
                break
        if rupture_collapse:
            # Ruptura manda sobre cualquier acumulación positiva (no promedio con halos).
            score = 1
            best_idx = rupture_anchor if rupture_anchor >= 0 else best_idx
            best_keyword = best_keyword or "ruptura estructural"

        nl_pen = _negative_lexicon_5x_penalty(t_lower, best_idx)
        if not rupture_collapse and nl_pen and score > 0:
            score = max(0, int(score) - nl_pen)

        if score <= 0 or best_idx < 0:
            results[p_code] = {
                "note": "",
                "confidence": 50,
                "score": 0,
                "keyword": "",
                "tension_matched": False,
                "tension_keyword": "",
                "tension_score": 0,
                "rupture_collapse": False,
            }
            continue

        start = max(0, best_idx - int(snippet_chars * 0.35))
        end = min(len(t_norm), best_idx + int(snippet_chars * 0.65))
        snippet = t_norm[start:end]
        snippet = re.sub(r"\s+", " ", snippet).strip()

        if len(snippet) > snippet_chars:
            snippet = snippet[: snippet_chars - 1].rstrip() + "..."

        # Confidence: baseline + intensidad de match.
        conf = 55 + min(40, score * 8)
        conf = int(min(95, max(55, conf)))

        results[p_code] = {
            "note": snippet,
            "confidence": conf,
            "score": int(score),
            "keyword": best_keyword,
            "tension_matched": bool(tension_matched),
            "tension_keyword": tension_keyword,
            "tension_score": int(tension_score),
            "rupture_collapse": bool(rupture_collapse),
        }

    return results


def propose_pi_notes_from_chunks(
    chunks: Sequence[str],
    snippet_chars: int = 220,
) -> Dict[str, Dict[str, Any]]:
    """
    Misma heurística que `propose_pi_notes_from_text`, con entrada = lista de fragmentos.
    Fase 2: listo para pipelines PDF por página o por chunk semántico.
    """
    text = join_text_chunks(chunks)
    return propose_pi_notes_from_text(text, snippet_chars=snippet_chars)


__all__ = [
    "KEYWORDS_RUPTURA",
    "ingest_disclosure_profile",
    "extract_text_from_uploaded_pdfs",
    "extract_page_chunks_from_pdf_bytes",
    "extract_page_chunks_from_pdf_bytes_detailed",
    "extract_page_chunks_from_uploaded_pdfs",
    "extract_uploaded_pdfs_with_stats",
    "join_text_chunks",
    "propose_pi_notes_from_text",
    "propose_pi_notes_from_chunks",
]

