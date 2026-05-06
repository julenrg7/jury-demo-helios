import re

POWER_LABELS = {
    "P1": "BIOLÓGICO",
    "P2": "EMOCIONAL",
    "P3": "COMUNICATIVO",
    "P4": "SOCIAL",
    "P5": "INSTITUCIONAL",
    "P6": "ECONÓMICO",
    "P7": "POLÍTICO",
    "P8": "ESTRATÉGICO",
    "P9": "TECNOLÓGICO",
    "P10": "CULTURAL",
}

INTERVENTION_LABELS = {
    1: "Ajuste estructural",
    2: "Refuerzo operativo",
    3: "Reordenación mixta",
    4: "Intervención estructural intensiva",
    5: "Refuerzo de autoridad y cohesión",
}


def format_power_label(power_code: str) -> str:
    if power_code in POWER_LABELS:
        return f"{POWER_LABELS[power_code]} ({power_code})"
    return power_code


def parse_intervention_number(action_label: str | None) -> int | None:
    if not action_label:
        return None

    if "Intervención 1" in action_label:
        return 1
    elif "Intervención 2" in action_label:
        return 2
    elif "Intervención 3" in action_label:
        return 3
    elif "Intervención 4" in action_label:
        return 4
    elif "Intervención 5" in action_label:
        return 5

    return None


def replace_power_codes_in_text(text: str | None) -> str | None:
    if not text:
        return text

    return re.sub(
        r"(?<!\()(?<![A-ZÁÉÍÓÚÑ])\b(P10|P[1-9])\b(?!\))",
        lambda m: format_power_label(m.group(1)),
        text,
    )