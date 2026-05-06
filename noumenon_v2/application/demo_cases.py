from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable

from noumenon_v2.domain.models import CaseRecord, EvidenceItem


@dataclass(frozen=True)
class FrontierCaseDefinition:
    label: str
    dominant_archetype: str
    neighbor_archetype: str
    decisive_question: str
    builder: Callable[[], CaseRecord]


def _build_base_case(
    *,
    case_id: str,
    client_name: str,
    project_name: str,
    analyst_name: str,
    objective: str,
    context: str,
    benchmark_name: str = "Estable",
    case_status: str = "Informe listo",
    analyst_notes: str = "",
    tags: list[str] | None = None,
) -> CaseRecord:
    case = CaseRecord.create_blank()
    case.case_id = case_id
    case.client_name = client_name
    case.project_name = project_name
    case.analyst_name = analyst_name
    case.benchmark_name = benchmark_name
    case.case_status = case_status
    case.objective = objective
    case.context = context
    case.tags = list(tags or [])
    case.analyst_notes = analyst_notes
    return case


def _assign_power(
    case: CaseRecord,
    power_code: str,
    *,
    m1: float,
    m2: float,
    m3: float,
    r: float,
    c: float,
    a: float,
    flow: float,
    summary: str,
    excerpts: str,
    source: str,
    confidence: int,
    analyst_note: str,
) -> None:
    assessment = case.assessments[power_code]
    assessment.m1 = m1
    assessment.m2 = m2
    assessment.m3 = m3
    assessment.r = r
    assessment.c = c
    assessment.a = a
    assessment.flow = flow
    assessment.evidence = EvidenceItem(
        summary=summary,
        excerpts=excerpts,
        source=source,
        confidence=confidence,
        analyst_note=analyst_note,
    )


def build_helios_ai_demo_case() -> CaseRecord:
    case = _build_base_case(
        case_id="demo_helios_ai",
        client_name="Helios AI",
        project_name="Executive Growth Stress Test",
        analyst_name="Noumenon Intelligence Unit",
        objective=(
            "Determinar si la empresa puede sostener su expansión sin convertir potencia tecnológica "
            "en fragilidad institucional, fuga cultural y riesgo de mando."
        ),
        context=(
            "Helios AI es una compañía de infraestructura y agentes de IA en fase de hipercrecimiento. "
            "Ha multiplicado contratos enterprise, talento técnico y visibilidad de mercado en poco tiempo. "
            "La pregunta ejecutiva no es si tiene potencia, sino si su arquitectura de poder puede sostener esa escala "
            "sin entrar en desalineación entre estrategia, institución, comunicación y legitimidad interna."
        ),
        analyst_notes=(
            "Potencia estratégica y tecnológica alta, deuda institucional visible y decisión ejecutiva clara. "
            "La lectura dominante es crecimiento bajo estrés, no crisis declarada."
        ),
        tags=["demo", "ai", "scale-up", "growth", "executive"],
    )

    _assign_power(case, "P1", m1=6.2, m2=6.7, m3=5.3, r=6.0, c=6.4, a=5.4, flow=-0.1,
        summary="La intensidad operativa del equipo empieza a tensionar la base humana.",
        excerpts="Aumento de carga en equipos críticos, ventanas de entrega comprimidas y desgaste creciente en managers intermedios.",
        source="Documento", confidence=72,
        analyst_note="No es colapso biológico, pero ya aparece erosión de capacidad sostenida.")
    _assign_power(case, "P2", m1=6.4, m2=7.8, m3=5.6, r=6.3, c=7.3, a=5.6, flow=0.0,
        summary="La empresa conserva carisma e impulso, pero la cohesión emocional se vuelve desigual.",
        excerpts="Fuerte adhesión al relato de misión en capas fundacionales, combinada con cansancio y distancia creciente en equipos incorporados recientemente.",
        source="Mixto", confidence=77,
        analyst_note="La energía de crecimiento existe, aunque ya no distribuye lealtad de forma homogénea.")
    _assign_power(case, "P3", m1=7.4, m2=8.2, m3=4.9, r=7.5, c=8.0, a=4.9, flow=-0.1,
        summary="La narrativa externa es fuerte, pero la coherencia comunicativa interna pierde resolución.",
        excerpts="Mensajes estratégicos muy sólidos hacia mercado e inversores; mayor ruido interno sobre prioridades, ownership y secuencia de ejecución.",
        source="Mixto", confidence=83,
        analyst_note="P3 alto hacia fuera, menos integrado hacia dentro.")
    _assign_power(case, "P4", m1=7.1, m2=7.3, m3=5.7, r=6.8, c=7.4, a=5.8, flow=0.1,
        summary="Helios ha construido red comercial y acceso de alto nivel, pero depende demasiado de pocos nodos tractores.",
        excerpts="Partnerships estratégicos relevantes, entrada rápida en cuentas enterprise y alta concentración del acceso relacional en leadership y founders.",
        source="Documento", confidence=75,
        analyst_note="La red existe y funciona, aunque todavía no está distribuida institucionalmente.")
    _assign_power(case, "P5", m1=4.2, m2=4.8, m3=2.8, r=4.0, c=4.2, a=2.9, flow=-1.4,
        summary="La estructura institucional no acompaña todavía la complejidad alcanzada por el negocio.",
        excerpts="Procesos de gobierno en construcción, roles solapados, escalado de decisiones sin criterios totalmente estabilizados y dependencia de excepciones.",
        source="Manual", confidence=86,
        analyst_note="Aquí está la deuda estructural decisiva del caso y el frente que exige intervención.")
    _assign_power(case, "P6", m1=7.8, m2=7.2, m3=5.9, r=7.9, c=7.1, a=5.8, flow=0.2,
        summary="La potencia económica es real y sostiene expansión, contratación y credibilidad externa.",
        excerpts="Crecimiento de contratos, pipeline enterprise robusto y señal de mercado positiva sobre capacidad de captura.",
        source="Documento", confidence=81,
        analyst_note="P6 es una de las bases visibles de legitimidad de Helios.")
    _assign_power(case, "P7", m1=5.5, m2=5.9, m3=5.1, r=5.6, c=5.7, a=5.2, flow=-0.1,
        summary="El centro de decisión existe, pero aún no está plenamente desacoplado de las figuras fundacionales.",
        excerpts="Alta velocidad de decisión en momentos críticos, combinada con dependencia de alineación personal entre pocos decisores clave.",
        source="Manual", confidence=74,
        analyst_note="No hay vacío de mando, pero sí riesgo de estrechamiento soberano.")
    _assign_power(case, "P8", m1=8.2, m2=8.4, m3=6.1, r=8.3, c=7.8, a=6.5, flow=1.0,
        summary="La maniobra estratégica es una de las fortalezas centrales de la compañía.",
        excerpts="Expansión rápida a cuentas enterprise, claridad de timing competitivo y fuerte capacidad para reordenar foco de producto y go-to-market.",
        source="Documento", confidence=88,
        analyst_note="P8 es tractor de crecimiento y una de las bases visibles de la expansión.")
    _assign_power(case, "P9", m1=9.1, m2=8.8, m3=7.1, r=9.0, c=8.4, a=7.0, flow=1.3,
        summary="La capacidad tecnológica y de producto es excepcional y explica buena parte de la potencia total del sistema.",
        excerpts="Stack robusto, velocidad de despliegue, credibilidad técnica y ventaja visible en infraestructura aplicada a IA enterprise.",
        source="Documento", confidence=91,
        analyst_note="P9 es la principal prueba de potencia estructural del caso.")
    _assign_power(case, "P10", m1=6.3, m2=7.4, m3=4.5, r=6.1, c=7.0, a=4.7, flow=-0.1,
        summary="La legitimidad cultural sigue siendo alta, pero el crecimiento empieza a introducir fisuras entre relato y experiencia interna.",
        excerpts="Marca empleadora potente y misión ilusionante, pero con señales de desalineación entre narrativa de excelencia y sensación operativa de improvisación.",
        source="Mixto", confidence=84,
        analyst_note="P10 no está roto; está entrando en fase de tensión si P5 no madura.")

    return case


def build_atlas_public_systems_demo_case() -> CaseRecord:
    case = _build_base_case(
        case_id="demo_atlas_public_systems",
        client_name="Atlas Public Systems",
        project_name="Institutional Drag Review",
        analyst_name="Noumenon Intelligence Unit",
        objective="Determinar si la organización conserva capacidad estratégica real o si su densidad institucional ya opera como freno ciego.",
        context=(
            "Atlas Public Systems coordina infraestructuras críticas, compliance multirregional y grandes procesos de ejecución. "
            "La institución funciona, pero cada decisión relevante tarda demasiado en traducirse en maniobra."
        ),
        analyst_notes="Caso canónico de Leviatán Ciego: mucha forma, poca maniobra, sin colapso caótico.",
        tags=["demo", "institution", "legacy", "governance"],
    )
    values = {
        "P1": (5.4, 5.1, 6.0, 5.3, 5.2, 5.5, -0.1),
        "P2": (4.9, 4.8, 5.8, 4.8, 4.9, 5.1, -0.2),
        "P3": (4.7, 4.8, 5.6, 4.8, 4.7, 5.0, -0.4),
        "P4": (4.8, 4.9, 5.7, 4.9, 5.0, 5.1, -0.3),
        "P5": (7.0, 6.5, 8.9, 7.0, 6.7, 7.8, -0.8),
        "P6": (6.0, 5.8, 6.4, 6.0, 5.9, 6.2, 0.0),
        "P7": (5.3, 5.4, 6.7, 5.4, 5.3, 6.1, -0.2),
        "P8": (3.5, 3.4, 3.6, 3.5, 3.4, 3.5, -1.1),
        "P9": (4.5, 4.3, 5.1, 4.6, 4.4, 4.7, -0.6),
        "P10": (5.8, 5.6, 7.1, 5.8, 5.7, 6.6, -0.2),
    }
    summaries = {
        "P5": "La densidad de proceso y norma es altísima, pero convierte casi cualquier excepción en cuello de botella.",
        "P8": "La maniobra estratégica queda absorbida por el sistema de cumplimiento y secuencia interna.",
        "P10": "La legitimidad formal es fuerte y sostiene obediencia, aunque no garantiza lectura de futuro.",
    }
    for power_code, values_row in values.items():
        summary = summaries.get(power_code, f"El nodo {power_code} opera con disciplina, pero sin protagonismo decisivo en la lectura.")
        _assign_power(
            case,
            power_code,
            m1=values_row[0], m2=values_row[1], m3=values_row[2], r=values_row[3], c=values_row[4], a=values_row[5], flow=values_row[6],
            summary=summary,
            excerpts=f"Observaciones de gobierno y ejecución sobre {power_code}.",
            source="Manual",
            confidence=82 if power_code in {"P5", "P8", "P10"} else 68,
            analyst_note="La lectura favorece burocracia densa por encima de maniobra." if power_code == "P5" else "Nodo secundario dentro del caso.",
        )
    return case


def build_bastion_defense_demo_case() -> CaseRecord:
    case = _build_base_case(
        case_id="demo_bastion_defense",
        client_name="Bastion Defense Systems",
        project_name="Perimeter Access Blockage",
        analyst_name="Noumenon Intelligence Unit",
        objective="Distinguir si el problema real es debilidad interna o cerco externo sobre una arquitectura todavía potente.",
        context=(
            "Bastion mantiene ingeniería e institución fuertes, pero su acceso a alianzas, relato público y canales relacionales está fuertemente deteriorado por el entorno."
        ),
        analyst_notes="Caso canónico de Fortaleza Sitiada: potencia real dentro, circuito de legitimación roto fuera.",
        tags=["demo", "defense", "perimeter", "access"],
    )
    values = {
        "P1": (5.8, 5.6, 5.9, 5.7, 5.5, 5.8, -0.1),
        "P2": (4.6, 4.4, 5.1, 4.5, 4.3, 4.7, -0.3),
        "P3": (3.1, 3.0, 3.8, 3.2, 3.0, 3.1, -1.2),
        "P4": (3.3, 3.2, 3.9, 3.2, 3.1, 3.2, -1.0),
        "P5": (6.4, 6.0, 7.3, 6.5, 6.1, 6.8, 0.1),
        "P6": (5.6, 5.4, 5.9, 5.8, 5.5, 5.8, -0.2),
        "P7": (5.4, 5.2, 5.8, 5.4, 5.2, 5.5, -0.1),
        "P8": (5.2, 5.3, 5.6, 5.4, 5.1, 5.3, -0.2),
        "P9": (6.6, 6.2, 6.8, 6.7, 6.1, 6.4, 0.1),
        "P10": (4.2, 4.0, 4.6, 4.1, 3.9, 4.2, -0.7),
    }
    for power_code, values_row in values.items():
        _assign_power(
            case,
            power_code,
            m1=values_row[0], m2=values_row[1], m3=values_row[2], r=values_row[3], c=values_row[4], a=values_row[5], flow=values_row[6],
            summary={
                "P3": "La narrativa está técnicamente defendida, pero el entorno no la deja circular con normalidad.",
                "P4": "Las alianzas y canales de acceso están parcialmente cerrados; el poder no escala hacia fuera.",
                "P5": "La institución interna sigue operativa y da contención real al sistema.",
                "P9": "La potencia tecnológica permanece fuerte incluso bajo aislamiento.",
            }.get(power_code, f"El nodo {power_code} contribuye a una arquitectura fuerte pero cercada."),
            excerpts=f"Registro analítico del nodo {power_code}.",
            source="Manual",
            confidence=84 if power_code in {"P3", "P4", "P5", "P9"} else 70,
            analyst_note="El perímetro explica más que el núcleo." if power_code in {"P3", "P4"} else "Nodo de soporte dentro del caso.",
        )
    return case


def build_velora_heritage_demo_case() -> CaseRecord:
    case = _build_base_case(
        case_id="demo_velora_heritage",
        client_name="Velora Heritage",
        project_name="Residual Prestige Review",
        analyst_name="Noumenon Intelligence Unit",
        objective="Determinar si el valor actual sigue apoyado en capacidad real o si la marca vive ya sobre eco cultural residual.",
        context=(
            "Velora conserva reconocimiento simbólico y prestigio histórico, pero sus capacidades económica, tecnológica e institucional muestran degradación sostenida."
        ),
        analyst_notes="Caso canónico de Resonancia Fantasma: el imaginario sigue vivo aunque el cuerpo operativo ya no acompaña.",
        tags=["demo", "brand", "heritage", "decline"],
    )
    values = {
        "P1": (3.1, 3.0, 3.3, 3.1, 3.0, 3.0, -0.6),
        "P2": (3.2, 3.5, 3.4, 3.1, 3.3, 3.2, -0.5),
        "P3": (3.8, 4.0, 3.7, 3.6, 3.8, 3.7, -0.4),
        "P4": (3.4, 3.6, 3.5, 3.4, 3.5, 3.4, -0.4),
        "P5": (2.9, 2.8, 3.2, 2.9, 2.8, 2.8, -0.6),
        "P6": (3.6, 3.5, 3.4, 3.6, 3.4, 3.4, -0.7),
        "P7": (3.0, 2.9, 3.2, 3.0, 2.9, 3.0, -0.4),
        "P8": (3.3, 3.2, 3.4, 3.3, 3.1, 3.2, -0.8),
        "P9": (3.1, 3.0, 3.3, 3.1, 3.0, 3.1, -0.9),
        "P10": (6.1, 6.2, 8.4, 5.8, 6.0, 6.3, 0.1),
    }
    for power_code, values_row in values.items():
        _assign_power(
            case,
            power_code,
            m1=values_row[0], m2=values_row[1], m3=values_row[2], r=values_row[3], c=values_row[4], a=values_row[5], flow=values_row[6],
            summary={
                "P10": "La marca conserva aura, prestigio y memoria, aunque el resto del sistema ya no responde con igual densidad.",
                "P6": "La base económica sobrevive, pero sin potencia suficiente para justificar el mito.",
                "P9": "La capacidad tecnológica está claramente por debajo del capital simbólico heredado.",
            }.get(power_code, f"El nodo {power_code} muestra degradación más visible que capacidad nueva."),
            excerpts=f"Señales de vaciamiento estructural en {power_code}.",
            source="Mixto",
            confidence=86 if power_code == "P10" else 72,
            analyst_note="El mito dura más que el cuerpo." if power_code == "P10" else "Nodo en degradación relativa.",
        )
    return case


def build_orbit_foundry_demo_case() -> CaseRecord:
    case = _build_base_case(
        case_id="demo_orbit_foundry",
        client_name="Orbit Foundry",
        project_name="Founder Dependence Review",
        analyst_name="Noumenon Intelligence Unit",
        objective="Evaluar si la organización ya puede transferir mando a estructura o si sigue dependiendo del núcleo biográfico del fundador.",
        context=(
            "Orbit Foundry creció gracias a la visión del fundador y a una cohesión emocional muy concentrada. "
            "La transición a escala exige probar si la institución puede sostener esa legitimidad sin presencia constante del líder."
        ),
        analyst_notes="Caso canónico de Feudo Carismático: mucho vínculo y autoridad biográfica, poca norma equivalente.",
        tags=["demo", "founder", "succession", "leadership"],
    )
    values = {
        "P1": (6.5, 7.0, 4.8, 6.4, 6.9, 6.5, -0.2),
        "P2": (6.3, 8.6, 5.0, 6.4, 8.2, 7.9, 0.2),
        "P3": (5.0, 5.4, 4.5, 5.0, 5.2, 4.8, -0.3),
        "P4": (5.2, 5.6, 4.8, 5.2, 5.5, 5.0, -0.2),
        "P5": (4.4, 4.8, 4.2, 4.5, 4.6, 4.3, -0.9),
        "P6": (5.7, 5.8, 5.0, 5.8, 5.7, 5.2, -0.1),
        "P7": (4.9, 5.0, 4.7, 4.9, 4.8, 4.8, -0.3),
        "P8": (5.3, 5.4, 5.0, 5.4, 5.3, 5.1, 0.0),
        "P9": (5.5, 5.7, 5.2, 5.5, 5.6, 5.3, 0.1),
        "P10": (4.8, 5.4, 4.7, 4.8, 5.2, 4.9, -0.2),
    }
    for power_code, values_row in values.items():
        _assign_power(
            case,
            power_code,
            m1=values_row[0], m2=values_row[1], m3=values_row[2], r=values_row[3], c=values_row[4], a=values_row[5], flow=values_row[6],
            summary={
                "P2": "La adhesión emocional y la legitimidad efectiva pasan todavía por la figura del fundador.",
                "P5": "La norma no iguala todavía el peso del vínculo personal en la toma de decisiones.",
                "P1": "La biografía del liderazgo sigue estructurando el ritmo del sistema.",
            }.get(power_code, f"El nodo {power_code} acompaña una arquitectura aún muy biografizada."),
            excerpts=f"Observaciones estructurales sobre {power_code}.",
            source="Manual",
            confidence=85 if power_code in {"P1", "P2", "P5"} else 71,
            analyst_note="El liderazgo personal pesa más que la norma." if power_code == "P2" else "Nodo secundario del patrón.",
        )
    return case


def build_nova_constellation_gold_case() -> CaseRecord:
    case = _build_base_case(
        case_id="gold_nova_constellation",
        client_name="Nova Constellation",
        project_name="Sovereign Continuity Review",
        analyst_name="Noumenon Intelligence Unit",
        objective="Comprobar si la arquitectura conserva soberanía real y continuidad de mando por encima de cualquier figura individual.",
        context=(
            "Nova Constellation lidera una red industrial-tecnológica con alta capacidad de coordinación, expansión y sucesión sin señales de dependencia biográfica extrema."
        ),
        analyst_notes="Caso oro de Arquitectura Soberana: mando, forma y maniobra siguen vivos al mismo tiempo.",
        tags=["gold", "sovereign", "continuity"],
    )
    values = {
        "P1": (6.2, 6.1, 6.2, 6.1, 6.0, 6.0, 0.1),
        "P2": (5.8, 5.9, 6.0, 5.8, 5.9, 5.9, 0.1),
        "P3": (6.0, 6.1, 6.2, 6.0, 6.1, 6.0, 0.1),
        "P4": (6.1, 6.2, 6.2, 6.1, 6.2, 6.1, 0.1),
        "P5": (6.4, 6.2, 6.8, 6.4, 6.2, 6.3, 0.1),
        "P6": (6.8, 6.7, 6.6, 6.9, 6.7, 6.6, 0.2),
        "P7": (9.1, 9.0, 8.2, 9.2, 8.8, 8.0, 0.5),
        "P8": (9.2, 9.1, 8.0, 9.3, 8.9, 7.8, 0.6),
        "P9": (6.8, 6.8, 6.5, 6.9, 6.8, 6.6, 0.2),
        "P10": (5.2, 5.2, 5.8, 5.2, 5.2, 5.4, 0.0),
    }
    for power_code, values_row in values.items():
        _assign_power(
            case,
            power_code,
            m1=values_row[0], m2=values_row[1], m3=values_row[2], r=values_row[3], c=values_row[4], a=values_row[5], flow=values_row[6],
            summary="La arquitectura muestra coherencia de mando, continuidad y maniobra por encima de dependencia personal.",
            excerpts=f"Lectura soberana consistente en {power_code}.",
            source="Manual",
            confidence=83,
            analyst_note="La estructura conserva el mando incluso bajo transición o escala.",
        )
    return case


def build_titan_industrials_gold_case() -> CaseRecord:
    case = _build_base_case(
        case_id="gold_titan_industrials",
        client_name="Titan Industrials",
        project_name="Mass Without Skeleton Review",
        analyst_name="Noumenon Intelligence Unit",
        objective="Determinar si el peso industrial y económico del sistema se sostiene por forma real o solo por inercia de masa.",
        context=(
            "Titan Industrials conserva tamaño, contratos y volumen, pero arrastra una estructura de mando incompleta y fricción distribuida en sus nodos críticos."
        ),
        analyst_notes="Caso oro de Gigante de Barro: masa real, cohesión insuficiente y peso sin esqueleto bastante claro.",
        tags=["gold", "giant", "mass"],
    )
    values = {
        "P1": (6.4, 6.0, 4.6, 6.2, 6.0, 4.8, -0.4),
        "P2": (6.1, 5.8, 4.7, 6.0, 5.9, 4.7, -0.3),
        "P3": (6.0, 5.8, 4.6, 6.0, 5.8, 4.6, -0.3),
        "P4": (6.2, 6.0, 4.8, 6.1, 6.0, 4.8, -0.3),
        "P5": (4.8, 4.9, 4.1, 4.9, 4.8, 4.3, -0.6),
        "P6": (7.8, 7.3, 5.1, 7.8, 7.0, 5.0, -0.2),
        "P7": (3.9, 4.0, 4.0, 4.0, 4.0, 4.0, -0.3),
        "P8": (5.6, 5.4, 4.9, 5.5, 5.3, 4.9, -0.3),
        "P9": (5.7, 5.5, 4.9, 5.7, 5.5, 5.0, -0.3),
        "P10": (5.8, 5.5, 4.8, 5.6, 5.5, 4.8, -0.2),
    }
    for power_code, values_row in values.items():
        _assign_power(
            case,
            power_code,
            m1=values_row[0], m2=values_row[1], m3=values_row[2], r=values_row[3], c=values_row[4], a=values_row[5], flow=values_row[6],
            summary="El tamaño del sistema supera la capacidad de convertir masa en coordinación estable.",
            excerpts=f"Señal de peso sin esqueleto suficiente en {power_code}.",
            source="Manual",
            confidence=81,
            analyst_note="La organización pesa más de lo que ordena.",
        )
    return case


def build_meridian_devices_gold_case() -> CaseRecord:
    case = _build_base_case(
        case_id="gold_meridian_devices",
        client_name="Meridian Devices",
        project_name="Strategic Drift Review",
        analyst_name="Noumenon Intelligence Unit",
        objective="Determinar si el sistema sigue vivo estratégicamente o si su base económica ya financia una obsolescencia latente.",
        context=(
            "Meridian Devices mantiene caja, reputación y presencia comercial, pero sus vectores estratégicos y tecnológicos se degradan de forma persistente."
        ),
        analyst_notes="Caso oro de Zombi Estratégico: el cuerpo económico respira, pero el cerebro pierde futuro.",
        tags=["gold", "zombie", "drift"],
    )
    values = {
        "P1": (4.8, 4.7, 4.9, 4.8, 4.7, 4.8, -0.1),
        "P2": (4.8, 4.7, 4.9, 4.8, 4.7, 4.8, -0.1),
        "P3": (5.2, 5.1, 5.2, 5.2, 5.1, 5.1, -0.1),
        "P4": (5.8, 5.7, 5.9, 5.8, 5.7, 5.6, -0.1),
        "P5": (5.0, 4.9, 5.3, 5.0, 4.9, 5.0, -0.2),
        "P6": (7.6, 7.4, 6.4, 7.6, 7.3, 6.4, -0.1),
        "P7": (4.9, 4.8, 5.0, 4.9, 4.8, 4.9, -0.1),
        "P8": (4.0, 3.9, 4.2, 4.0, 3.9, 4.0, -0.9),
        "P9": (4.1, 4.0, 4.2, 4.1, 4.0, 4.1, -1.0),
        "P10": (5.1, 5.0, 5.4, 5.1, 5.0, 5.1, -0.1),
    }
    for power_code, values_row in values.items():
        _assign_power(
            case,
            power_code,
            m1=values_row[0], m2=values_row[1], m3=values_row[2], r=values_row[3], c=values_row[4], a=values_row[5], flow=values_row[6],
            summary="La base instalada se mantiene, pero la lectura de futuro cae por debajo de la inercia del sistema.",
            excerpts=f"Deterioro del vector estratégico en {power_code}.",
            source="Manual",
            confidence=82,
            analyst_note="El sistema todavía factura, pero ya no orienta con claridad el siguiente tiempo.",
        )
    return case


def build_aurora_canon_gold_case() -> CaseRecord:
    case = _build_base_case(
        case_id="gold_aurora_canon",
        client_name="Aurora Canon Works",
        project_name="Metabolic Rigidity Review",
        analyst_name="Noumenon Intelligence Unit",
        objective="Comprobar si el prestigio acumulado sigue siendo estructura viva o si el canon ya está bloqueando la adaptación del sistema.",
        context=(
            "Aurora Canon Works conserva legitimidad, hábito y excelencia histórica, pero su metabolismo de adaptación tecnológica y organizativa se ha endurecido."
        ),
        analyst_notes="Caso oro de Estructura Fosilizada: todavía hay cuerpo, pero el canon pesa demasiado.",
        tags=["gold", "fossilized", "canon"],
    )
    values = {
        "P1": (5.7, 5.4, 6.0, 5.6, 5.4, 5.6, -0.1),
        "P2": (5.4, 5.2, 5.9, 5.3, 5.2, 5.4, -0.1),
        "P3": (5.6, 5.3, 6.0, 5.5, 5.4, 5.5, -0.1),
        "P4": (5.7, 5.5, 6.1, 5.6, 5.5, 5.6, -0.1),
        "P5": (5.9, 5.6, 6.5, 5.8, 5.6, 5.9, -0.1),
        "P6": (6.1, 5.8, 6.4, 6.0, 5.8, 5.9, -0.1),
        "P7": (5.4, 5.2, 6.0, 5.3, 5.2, 5.4, -0.1),
        "P8": (4.7, 4.5, 5.2, 4.7, 4.5, 4.6, -0.2),
        "P9": (4.9, 4.7, 5.2, 4.8, 4.7, 4.8, -0.5),
        "P10": (7.4, 7.0, 8.8, 7.2, 7.0, 7.1, 0.0),
    }
    for power_code, values_row in values.items():
        _assign_power(
            case,
            power_code,
            m1=values_row[0], m2=values_row[1], m3=values_row[2], r=values_row[3], c=values_row[4], a=values_row[5], flow=values_row[6],
            summary="El legado sigue vivo, pero su peso cultural condiciona demasiado la capacidad de adaptación.",
            excerpts=f"Rigidez por canon acumulado en {power_code}.",
            source="Manual",
            confidence=82,
            analyst_note="La estructura existe, pero el metabolismo ya se endurece por prestigio y hábito.",
        )
    return case


def build_raptor_capital_gold_case() -> CaseRecord:
    case = _build_base_case(
        case_id="gold_raptor_capital",
        client_name="Raptor Capital Systems",
        project_name="Extraction Logic Review",
        analyst_name="Noumenon Intelligence Unit",
        objective="Determinar si la organización está instituyendo orden nuevo o si su arquitectura está diseñada sobre todo para captura rápida de valor.",
        context=(
            "Raptor Capital Systems muestra máxima eficiencia en maniobra y captura económica, con muy poco espesor cultural o legitimidad relacional profunda."
        ),
        analyst_notes="Caso oro de Organismo de Asalto: eficiencia agresiva, bajo espesor simbólico y vocación claramente extractiva.",
        tags=["gold", "assault", "extraction"],
    )
    values = {
        "P1": (4.0, 4.2, 4.3, 4.1, 4.0, 4.0, 0.0),
        "P2": (2.2, 2.4, 3.0, 2.3, 2.5, 2.4, -0.1),
        "P3": (4.5, 4.7, 4.6, 4.6, 4.5, 4.4, 0.1),
        "P4": (4.3, 4.4, 4.5, 4.4, 4.3, 4.2, 0.0),
        "P5": (4.8, 4.6, 4.7, 4.8, 4.7, 4.6, -0.1),
        "P6": (8.7, 8.2, 6.1, 8.8, 7.9, 6.0, 0.4),
        "P7": (4.0, 4.0, 4.2, 4.1, 4.0, 4.0, 0.0),
        "P8": (8.2, 8.4, 6.0, 8.3, 8.0, 5.8, 0.5),
        "P9": (5.6, 5.8, 5.4, 5.7, 5.6, 5.4, 0.2),
        "P10": (2.1, 2.4, 2.8, 2.1, 2.2, 2.3, -0.2),
    }
    for power_code, values_row in values.items():
        _assign_power(
            case,
            power_code,
            m1=values_row[0], m2=values_row[1], m3=values_row[2], r=values_row[3], c=values_row[4], a=values_row[5], flow=values_row[6],
            summary="La arquitectura está optimizada para maniobra y captura más que para legitimación profunda o institución de largo plazo.",
            excerpts=f"Señal de extracción eficiente en {power_code}.",
            source="Manual",
            confidence=83,
            analyst_note="El sistema captura valor con gran velocidad y poco espesor simbólico.",
        )
    return case


def build_asterion_grid_frontier_case() -> CaseRecord:
    case = build_nova_constellation_gold_case().clone()
    case.case_id = "frontier_asterion_grid"
    case.client_name = "Asterion Grid"
    case.project_name = "Succession Transfer Boundary"
    case.objective = "Determinar si el sistema ya gobierna por estructura transferible o si aún depende demasiado del núcleo biográfico."
    case.context = (
        "Asterion Grid ha institucionalizado gran parte de su mando, pero conserva una huella personal muy fuerte en la "
        "cohesión del centro ejecutivo. La frontera real es si la arquitectura ya puede gobernar sin apoyarse tanto en la figura central."
    )
    case.analyst_notes = "Caso frontera Arquitectura Soberana / Feudo Carismático. Debe salir Soberana, pero con vecindad personal visible."
    case.tags = ["frontier", "sovereign", "charismatic", "succession"]
    for power_code in ["P1", "P2"]:
        assessment = case.assessments[power_code]
        assessment.m2 += 1.2
        assessment.c += 1.0
        assessment.a += 1.0
    for power_code in ["P7", "P8"]:
        assessment = case.assessments[power_code]
        assessment.m3 -= 0.8
        assessment.a -= 0.6
    return case


def build_orbit_succession_frontier_case() -> CaseRecord:
    case = build_orbit_foundry_demo_case().clone()
    case.case_id = "frontier_orbit_succession"
    case.client_name = "Orbit Foundry"
    case.project_name = "Founder Dependency Boundary"
    case.objective = "Determinar si el sistema ya puede absorber una transición de liderazgo o si la continuidad sigue anclada en el fundador."
    case.context = (
        "Orbit ya ha reforzado estructura, gobierno y continuidad de operación, pero la cohesión simbólica sigue descansando en la figura central "
        "más de lo que conviene para una sucesión limpia."
    )
    case.analyst_notes = "Caso frontera Feudo Carismático / Arquitectura Soberana. Debe salir Feudo con vecindad soberana real."
    case.tags = ["frontier", "charismatic", "sovereign", "leadership"]
    for power_code in ["P5", "P7", "P8"]:
        assessment = case.assessments[power_code]
        assessment.m3 += 0.8
        assessment.a += 0.5
    return case


def build_raptor_delta_frontier_case() -> CaseRecord:
    case = build_raptor_capital_gold_case().clone()
    case.case_id = "frontier_raptor_delta"
    case.client_name = "Raptor Delta"
    case.project_name = "Extraction vs Future Build Boundary"
    case.objective = "Distinguir si la arquitectura está empezando a instituirse o si sigue operando principalmente como depredador de valor."
    case.context = (
        "Raptor Delta ha empezado a reforzar capacidad tecnológica propia, pero su sesgo dominante sigue siendo la maniobra económica de captura rápida."
    )
    case.analyst_notes = "Caso frontera Organismo de Asalto / Vanguardia Disruptiva. Debe salir Organismo con proximidad real a Vanguardia."
    case.tags = ["frontier", "assault", "disruptive", "capture"]
    case.assessments["P9"].m1 += 1.0
    case.assessments["P9"].m2 += 0.9
    case.assessments["P9"].m3 += 0.7
    case.assessments["P9"].r += 0.8
    case.assessments["P9"].a += 0.6
    case.assessments["P6"].m1 -= 1.0
    case.assessments["P6"].r -= 0.7
    return case


def build_atlas_canon_frontier_case() -> CaseRecord:
    case = build_atlas_public_systems_demo_case().clone()
    case.case_id = "frontier_atlas_canon"
    case.client_name = "Atlas Process Works"
    case.project_name = "Bureaucracy vs Canon Boundary"
    case.objective = "Distinguir si la rigidez dominante nace del aparato institucional o del peso cultural acumulado."
    case.context = (
        "Atlas Process Works conserva una cultura de legitimidad muy asentada, pero el cuello de botella sigue apareciendo sobre todo en proceso, compliance y secuencia."
    )
    case.analyst_notes = "Caso frontera Leviatán Ciego / Estructura Fosilizada. Debe salir Leviatán con vecindad fosilizada visible."
    case.tags = ["frontier", "leviathan", "fossilized", "bureaucracy"]
    case.assessments["P10"].m3 += 0.5
    case.assessments["P10"].a += 0.4
    case.assessments["P8"].m2 -= 0.3
    case.assessments["P8"].r -= 0.3
    return case


def build_velora_residual_frontier_case() -> CaseRecord:
    case = build_velora_heritage_demo_case().clone()
    case.case_id = "frontier_velora_residual"
    case.client_name = "Velora Residual"
    case.project_name = "Body vs Echo Boundary"
    case.objective = "Determinar si todavía queda cuerpo operativo suficiente o si el valor actual vive sobre todo del eco cultural."
    case.context = (
        "Velora conserva algo más de disciplina operativa que una marca vacía pura, pero el imaginario sigue pesando bastante más que la capacidad real disponible."
    )
    case.analyst_notes = "Caso frontera Resonancia Fantasma / Estructura Fosilizada. Debe salir Fantasma con proximidad fosilizada."
    case.tags = ["frontier", "phantom", "fossilized", "legacy"]
    for power_code in ["P1", "P5", "P6", "P9"]:
        assessment = case.assessments[power_code]
        assessment.m1 += 0.6
        assessment.m3 += 0.5
        assessment.r += 0.5
        assessment.a += 0.4
        assessment.flow += 0.2
    return case


def build_demo_case_catalog() -> dict[str, Callable[[], CaseRecord]]:
    return {
        "Helios AI · Vanguardia Disruptiva": build_helios_ai_demo_case,
        "Atlas Public Systems · Leviatán Ciego": build_atlas_public_systems_demo_case,
        "Bastion Defense Systems · Fortaleza Sitiada": build_bastion_defense_demo_case,
        "Velora Heritage · Resonancia Fantasma": build_velora_heritage_demo_case,
        "Orbit Foundry · Feudo Carismático": build_orbit_foundry_demo_case,
    }


def build_gold_case_catalog() -> dict[str, Callable[[], CaseRecord]]:
    return {
        "Nova Constellation · Arquitectura Soberana": build_nova_constellation_gold_case,
        "Helios AI · Vanguardia Disruptiva": build_helios_ai_demo_case,
        "Titan Industrials · Gigante de Barro": build_titan_industrials_gold_case,
        "Meridian Devices · Zombi Estratégico": build_meridian_devices_gold_case,
        "Atlas Public Systems · Leviatán Ciego": build_atlas_public_systems_demo_case,
        "Aurora Canon Works · Estructura Fosilizada": build_aurora_canon_gold_case,
        "Orbit Foundry · Feudo Carismático": build_orbit_foundry_demo_case,
        "Raptor Capital Systems · Organismo de Asalto": build_raptor_capital_gold_case,
        "Bastion Defense Systems · Fortaleza Sitiada": build_bastion_defense_demo_case,
        "Velora Heritage · Resonancia Fantasma": build_velora_heritage_demo_case,
    }


def build_frontier_case_catalog() -> dict[str, FrontierCaseDefinition]:
    return {
        "Asterion Grid · Arquitectura Soberana / Feudo Carismático": FrontierCaseDefinition(
            label="Asterion Grid · Arquitectura Soberana / Feudo Carismático",
            dominant_archetype="Arquitectura Soberana",
            neighbor_archetype="Feudo Carismático",
            decisive_question="¿La arquitectura seguiría gobernando con coherencia si desaparece la figura central?",
            builder=build_asterion_grid_frontier_case,
        ),
        "Orbit Foundry · Feudo Carismático / Arquitectura Soberana": FrontierCaseDefinition(
            label="Orbit Foundry · Feudo Carismático / Arquitectura Soberana",
            dominant_archetype="Feudo Carismático",
            neighbor_archetype="Arquitectura Soberana",
            decisive_question="¿La continuidad del sistema sigue descansando más en la figura central que en la norma?",
            builder=build_orbit_succession_frontier_case,
        ),
        "Raptor Delta · Organismo de Asalto / Vanguardia Disruptiva": FrontierCaseDefinition(
            label="Raptor Delta · Organismo de Asalto / Vanguardia Disruptiva",
            dominant_archetype="Organismo de Asalto",
            neighbor_archetype="Vanguardia Disruptiva",
            decisive_question="¿La lógica principal es construir orden nuevo o capturar valor con máxima velocidad?",
            builder=build_raptor_delta_frontier_case,
        ),
        "Titan Industrials · Gigante de Barro / Leviatán Ciego": FrontierCaseDefinition(
            label="Titan Industrials · Gigante de Barro / Leviatán Ciego",
            dominant_archetype="Gigante de Barro",
            neighbor_archetype="Leviatán Ciego",
            decisive_question="¿El sistema falla por falta de esqueleto suficiente o por exceso de aparato sin maniobra?",
            builder=build_titan_industrials_gold_case,
        ),
        "Atlas Process Works · Leviatán Ciego / Estructura Fosilizada": FrontierCaseDefinition(
            label="Atlas Process Works · Leviatán Ciego / Estructura Fosilizada",
            dominant_archetype="Leviatán Ciego",
            neighbor_archetype="Estructura Fosilizada",
            decisive_question="¿La rigidez nace del aparato institucional o del canon acumulado?",
            builder=build_atlas_canon_frontier_case,
        ),
        "Atlas Public Systems · Leviatán Ciego / Gigante de Barro": FrontierCaseDefinition(
            label="Atlas Public Systems · Leviatán Ciego / Gigante de Barro",
            dominant_archetype="Leviatán Ciego",
            neighbor_archetype="Gigante de Barro",
            decisive_question="¿Domina el aparato burocrático o sigue pesando más la masa operativa que la estructura consigue ordenar?",
            builder=build_atlas_public_systems_demo_case,
        ),
        "Bastion Defense Systems · Fortaleza Sitiada / Zombi Estratégico": FrontierCaseDefinition(
            label="Bastion Defense Systems · Fortaleza Sitiada / Zombi Estratégico",
            dominant_archetype="Fortaleza Sitiada",
            neighbor_archetype="Zombi Estratégico",
            decisive_question="¿El problema principal está en el perímetro de acceso o en la pérdida de lectura de futuro?",
            builder=build_bastion_defense_demo_case,
        ),
        "Meridian Devices · Zombi Estratégico / Fortaleza Sitiada": FrontierCaseDefinition(
            label="Meridian Devices · Zombi Estratégico / Fortaleza Sitiada",
            dominant_archetype="Zombi Estratégico",
            neighbor_archetype="Fortaleza Sitiada",
            decisive_question="¿La arquitectura ya no produce dirección nueva o todavía la produce pero el entorno le bloquea la entrada?",
            builder=build_meridian_devices_gold_case,
        ),
        "Velora Residual · Resonancia Fantasma / Estructura Fosilizada": FrontierCaseDefinition(
            label="Velora Residual · Resonancia Fantasma / Estructura Fosilizada",
            dominant_archetype="Resonancia Fantasma",
            neighbor_archetype="Estructura Fosilizada",
            decisive_question="¿Todavía queda cuerpo operativo suficiente o queda sobre todo eco?",
            builder=build_velora_residual_frontier_case,
        ),
    }
