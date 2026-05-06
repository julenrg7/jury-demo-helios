"""
Capa de inteligencia narrativa Akxom (arquetipos, benchmark, panel ejecutivo).

La implementación vive en `reporting.py`; este módulo es el punto de entrada
nominal para importar el «cerebro» sin duplicar lógica.
"""

from archetype_actions import get_archetype_action
from akxom_archetypes import identify_archetype
from llm_ingest import build_report_from_text
from reporting import (
    get_stability_base_code,
    detect_narrative_mode,
    detect_structural_archetype,
    build_intervention_recommendations,
    get_benchmark_profile,
    build_benchmark_table,
    build_board_summary,
    build_ceo_insights,
    build_intervention_strategies,
    build_executive_decision_panel,
)

__all__ = [
    "get_archetype_action",
    "build_report_from_text",
    "identify_archetype",
    "get_stability_base_code",
    "detect_narrative_mode",
    "detect_structural_archetype",
    "build_intervention_recommendations",
    "get_benchmark_profile",
    "build_benchmark_table",
    "build_board_summary",
    "build_ceo_insights",
    "build_intervention_strategies",
    "build_executive_decision_panel",
]
