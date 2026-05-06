"""
UI tokens semánticos para Noumenon (Ax).

Centralizar colores para evitar divergencia entre `app.py` (HTML/PDF)
y `trabajo_view.py` (render en consola).
"""

SIGNAL_CYAN = "#00B8CC"  # señal/operación (no decisión)
SIGNAL_SKY = "#00E5FF"  # acento de panel/señal (más brillante)
# Dorado de decisión: un poco más profundo para mejorar contraste y legibilidad en botones.
DECISION_GOLD = "#C9A227"  # autoridad/decisión

# Señales Noumenon (Ax): semántica de cambio vs estabilidad.
SIGNAL_GOOD = "#6EE7B7"  # mejora / ascenso
SIGNAL_BAD = "#F87171"  # deterioro / fuga
SIGNAL_NEUTRAL = "#9CA3AF"  # estable / sin cambio relevante

# Azul estructural usado como valor “medio/estable” del flow.
STRUCT_MID_BLUE = "#2E4053"

# Azules de acento (intervención/paneles)
INTERVENTION_BLUE = "#1d4ed8"
INTERVENTION_LIGHT_BLUE = "#93C5FD"

# Clasificación export/PDF (riesgo operativo).
CLASSIFICATION_RED = "#B03A2E"

# Variantes doradas derivadas (UI).
GOLD_HOVER = "#D8B03A"
GOLD_GRADIENT_END = "#A9841E"
GOLD_CTA_BORDER = "#75622a"

# Alerta demo CEO (solo UI del demo).
DEMO_ALERT_BORDER = "#7f1d1d"
DEMO_ALERT_SUB = "#FCA5A5"

