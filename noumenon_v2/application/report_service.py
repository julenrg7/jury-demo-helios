from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path

from noumenon_v2.application.case_service import (
    DiagnosisSnapshot,
    build_archetype_comparison,
    build_editorial_frame,
    build_power_summary_rows,
    build_snapshot_comparison,
    build_structural_reading,
)
from noumenon_v2.application.visual_service import (
    _clean_exec_text,
    build_power_tension_map_svg,
    build_radar_svg_from_core_with_size,
    build_structural_heatmap_svg,
    describe_friction,
    describe_integrity,
)
from noumenon_v2.brand_assets import load_brand_svg
from noumenon_v2.domain.models import CaseRecord


def _lead_sentence(case: CaseRecord, diagnosis: DiagnosisSnapshot) -> str:
    return (
        f"{case.client_name or 'El sistema analizado'} muestra una combinación de potencia visible y tensión estructural "
        f"que exige una decisión ejecutiva explícita. El arquetipo dominante es "
        f"{diagnosis.archetype_name.lower()} y el estado estructural actual se expresa como "
        f"{diagnosis.structural_state_name.lower()}, con foco prioritario en {diagnosis.top_risk}."
    )


def _client_safe_copy(text: str) -> str:
    cleaned = " ".join(str(text or "").split())
    replacements = {
        "benchmark": "base de referencia",
        "Benchmark": "Base de referencia",
        "snapshot": "lectura anterior",
        "Snapshot": "Lectura anterior",
        "core": "motor",
        "Core": "Motor",
    }
    for source, target in replacements.items():
        cleaned = cleaned.replace(source, target)
    return cleaned


def _page_footer(page_number: int, total_pages: int, footer_case: str, footer_date: str) -> str:
    return (
        '<div class="page-footer">'
        '<div class="page-footer-top">'
        '<span>Noumenon Intelligence Unit</span>'
        '<span>Lectura estructural de poder</span>'
        f"<span>p. {page_number}/{total_pages}</span>"
        "</div>"
        '<div class="page-footer-bottom">'
        f"<span>{escape(footer_case)}</span>"
        f"<span>{escape(footer_date)}</span>"
        "</div>"
        "</div>"
    )


def _classification_signal(diagnosis: DiagnosisSnapshot) -> tuple[str, str]:
    robustness = "Frontera activa" if diagnosis.archetype_hybrid else "Lectura bien separada"
    resolution = "Criterio decisivo" if diagnosis.priority_rule_applied else "Señal predominante"
    return robustness, resolution


def _confidence_label_es(raw: str) -> str:
    value = str(raw or "").strip().upper()
    if value == "HIGH":
        return "ALTA"
    if value == "LOW":
        return "BAJA"
    return "MEDIA"


def _strip_lever_prefix(note: str, lever_label: str) -> str:
    cleaned_note = " ".join(str(note or "").split())
    label = " ".join(str(lever_label or "").split())
    if cleaned_note.upper().startswith(label.upper()):
        trimmed = cleaned_note[len(label):].lstrip(" .,:;")
        return trimmed[:1].upper() + trimmed[1:] if trimmed else cleaned_note
    return cleaned_note


def _pdf_summary_situation(text: str) -> str:
    cleaned = _client_safe_copy(text)
    replacements = {
        "muy rápido": "rápido",
        "ya no está en ejecutar más, sino en que la organización escale": "ya no está en ejecutar más, sino en escalar",
        "una arquitectura capaz de gobernar ese crecimiento": "una arquitectura capaz de gobernarlo",
    }
    for source, target in replacements.items():
        cleaned = cleaned.replace(source, target)
    return cleaned


def _pdf_summary_risk(text: str) -> str:
    cleaned = _client_safe_copy(text)
    replacements = {
        "una ventaja real de capacidad": "su ventaja de capacidad",
        "pérdida progresiva de control sobre su propia escala": "pérdida progresiva de control sobre la escala",
    }
    for source, target in replacements.items():
        cleaned = cleaned.replace(source, target)
    return cleaned


def build_report_html(case: CaseRecord, diagnosis: DiagnosisSnapshot, *, variant: str = "default") -> str:
    total_pages = 10
    cover_logo_svg = load_brand_svg("noumenon_imagotipo_horizontal_compact.svg")
    integrity_display, integrity_copy = describe_integrity(diagnosis.integrity)
    friction_display, friction_copy = describe_friction(diagnosis.friction)
    summary_rows = build_power_summary_rows(diagnosis.core)
    radar_svg = build_radar_svg_from_core_with_size(diagnosis.core, size=560.0)
    tension_map_svg = build_power_tension_map_svg(summary_rows, width=1080, height=560)
    heatmap_svg = build_structural_heatmap_svg(summary_rows, width=1080, row_height=48)
    structural_reading = build_structural_reading(case, diagnosis)
    snapshot_comparison = build_snapshot_comparison(case, diagnosis)
    executive_view = diagnosis.executive_view or {}
    decision_panel = diagnosis.decision_panel or {}
    situation = str(executive_view.get("situation") or "")
    decision = _client_safe_copy(str(executive_view.get("decision") or diagnosis.one_liner))
    critical_action = _clean_exec_text(str(executive_view.get("critical_action") or ""))
    impact = _client_safe_copy(str(executive_view.get("impact") or ""))
    risk = _client_safe_copy(str(executive_view.get("risk") or ""))
    confidence = str(executive_view.get("decision_confidence") or "MEDIUM")
    confidence_es = _confidence_label_es(confidence)
    next_step = str(executive_view.get("next_step") or "")
    structural_state = diagnosis.structural_state_name
    classification_copy = "Con frontera activa" if diagnosis.archetype_hybrid else "Lectura principal"
    intervention_title = _client_safe_copy(str(decision_panel.get("intervention_title") or ""))
    intervention_detail = _client_safe_copy(str(decision_panel.get("intervention_detail") or ""))
    lever_msg = _client_safe_copy(str(decision_panel.get("lever_msg") or ""))
    impact_msg = _client_safe_copy(str(decision_panel.get("impact_msg") or ""))
    editorial_frame = build_editorial_frame(diagnosis)
    archetype_comparison = build_archetype_comparison(diagnosis)
    robustness_label, resolution_label = _classification_signal(diagnosis)
    lead_sentence = _lead_sentence(case, diagnosis)
    footer_case = " · ".join(
        part for part in [case.client_name or "", case.project_name or "Lectura estructural"] if part
    )
    footer_date = datetime.now().strftime("%d.%m.%Y")
    analyst_master_notes = case.analyst_notes.strip() or "Sin nota maestra añadida para esta entrega."
    executive_recommendation = _client_safe_copy(
        str(
            decision_panel.get("executive_decision")
            or executive_view.get("decision")
            or diagnosis.one_liner
        )
    )
    jury_variant = variant == "jury"
    page2_lever_note = _strip_lever_prefix(editorial_frame["lever_note"], editorial_frame["lever_label"])
    summary_situation = _pdf_summary_situation(situation) if jury_variant else _client_safe_copy(situation)
    summary_risk = _pdf_summary_risk(risk) if jury_variant else risk
    comparison_html = (
        f"""
        <div class="panel">
          <div class="label">Comparación con lectura anterior</div>
          <h2 style="margin-top:0;">Evolución de la lectura</h2>
          <p>{escape(snapshot_comparison['direction'])}</p>
          <p><strong>Lectura anterior.</strong> {escape(snapshot_comparison['previous_label'])} · {escape(snapshot_comparison['previous_archetype'])} · {escape(snapshot_comparison['previous_state'])}</p>
          <p><strong>Riesgo anterior.</strong> {escape(snapshot_comparison['previous_risk'])}</p>
          <p><strong>Nodo anterior.</strong> {escape(snapshot_comparison['previous_power'])}</p>
        </div>
        """
        if snapshot_comparison
        else """
        <div class="panel">
          <div class="label">Comparación con lectura anterior</div>
          <h2 style="margin-top:0;">Primera iteración trazada</h2>
          <p>No hay una lectura anterior comparable todavía. Esta exportación fija una línea base para iteraciones siguientes.</p>
        </div>
        """
    )
    if jury_variant:
        comparison_html = f"""
        <div class="panel">
          <div class="label">Señal revelada</div>
          <h2 style="margin-top:0;">Lo que cambia la conversación</h2>
          <p>{escape(situation)}</p>
          <p><strong>Clave del caso.</strong> {escape(lever_msg or editorial_frame['lever_note'])}</p>
          <p><strong>Pregunta decisiva.</strong> {escape(archetype_comparison['decisive'])}</p>
        </div>
        """

    rows_html = "\n".join(
        f"""
        <tr>
            <td>{escape(str(row["Poder"]))}</td>
            <td>{escape(str(row["Título"]))}</td>
            <td>{row["Potencia"]}</td>
            <td>{row["Fricción"]}</td>
            <td>{row["Estructura"]}</td>
            <td>{row["Autoridad"]}</td>
        </tr>
        """
        for row in summary_rows
    )

    return f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>Noumenon Report</title>
  <style>
    @page {{
      size: A4;
      margin: 0;
    }}
    :root {{
      --panel: #121a22;
      --text: #ebf1f5;
      --muted: #9fb0bd;
      --accent: #d8b36a;
      --line: #2c3946;
    }}
    html, body {{
      margin: 0;
      min-height: 100%;
      background: #050505;
    }}
    body {{
      margin: 0;
      font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
      background: #050505;
      color: var(--text);
      print-color-adjust: exact;
      -webkit-print-color-adjust: exact;
    }}
    .pdf-page {{
      width: 210mm;
      min-height: 297mm;
      box-sizing: border-box;
      margin: 0 auto;
      padding: 16mm 18mm 18mm;
      background: #050505;
      overflow: hidden;
    }}
    .pdf-page + .pdf-page {{
      break-before: page;
      page-break-before: always;
    }}
    .page-inner {{
      max-width: 1080px;
      margin: 0 auto;
      min-height: calc(297mm - 34mm);
      display: flex;
      flex-direction: column;
    }}
    .page-content {{
      flex: 1 1 auto;
    }}
    .eyebrow {{
      letter-spacing: 0.16em;
      text-transform: uppercase;
      color: var(--muted);
      font-size: 12px;
      margin-bottom: 12px;
    }}
    h1, h2 {{
      margin: 0 0 12px;
      font-family: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", Georgia, serif;
    }}
    h1 {{
      font-size: 41px;
      line-height: 1.02;
      letter-spacing: -0.03em;
    }}
    h2 {{
      font-size: 20px;
      margin-top: 34px;
      letter-spacing: -0.02em;
    }}
    p {{
      color: var(--muted);
      line-height: 1.65;
    }}
    .hero {{
      background: radial-gradient(circle at top right, rgba(216,179,106,0.18), transparent 28%), var(--panel);
      border: 1px solid var(--line);
      border-radius: 22px;
      padding: 28px 30px 30px;
      break-inside: avoid;
      page-break-inside: avoid;
    }}
    .hero-lead {{
      max-width: 860px;
      color: #d7e1e8;
      font-size: 16px;
      line-height: 1.7;
      margin-top: 18px;
    }}
    .cover-brand {{
      width: 286px;
      margin: 0 0 24px -2px;
    }}
    .cover-brand svg {{
      display: block;
      width: 100%;
      height: auto;
      overflow: visible;
    }}
    .hero-meta {{
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      gap: 12px;
      margin-top: 22px;
      padding-top: 14px;
      border-top: 1px solid rgba(216,179,106,0.18);
    }}
    .hero-meta-item {{
      padding: 10px 0 0;
    }}
    .hero-meta-label {{
      font-size: 10px;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      color: var(--muted);
      margin-bottom: 6px;
    }}
    .hero-meta-value {{
      font-size: 14px;
      line-height: 1.45;
      color: var(--text);
      font-weight: 700;
    }}
    .editorial-strip {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 12px;
      margin-top: 18px;
    }}
    .editorial-card {{
      background: #0f151c;
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 14px 15px;
      break-inside: avoid;
      page-break-inside: avoid;
    }}
    .editorial-card .k {{
      font-size: 10px;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--muted);
      margin-bottom: 8px;
    }}
    .editorial-card .v {{
      font-size: 16px;
      line-height: 1.45;
      color: var(--text);
      font-weight: 700;
    }}
    .editorial-card .s {{
      margin-top: 7px;
      font-size: 12px;
      line-height: 1.55;
      color: var(--muted);
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 14px;
      margin-top: 20px;
    }}
    .classification-band {{
      display: grid;
      grid-template-columns: 1.1fr 1.8fr 1.1fr;
      gap: 12px;
      margin-top: 16px;
    }}
    .classification-band .panel {{
      padding: 15px 16px;
    }}
    .classification-band .value-compact {{
      font-size: 15px;
      line-height: 1.55;
      color: var(--text);
      font-weight: 700;
    }}
    .classification-band .value-note {{
      margin-top: 8px;
      font-size: 12px;
      line-height: 1.6;
      color: var(--muted);
    }}
    .metric, .panel {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 18px;
      break-inside: avoid;
      page-break-inside: avoid;
    }}
    .metric .label {{
      font-size: 12px;
      text-transform: uppercase;
      color: var(--muted);
      letter-spacing: 0.08em;
    }}
    .metric .value {{
      font-size: 28px;
      margin-top: 8px;
      color: var(--text);
      font-weight: 700;
    }}
    .two-col {{
      display: grid;
      grid-template-columns: 1.2fr 1fr;
      gap: 18px;
      margin-top: 20px;
    }}
    .three-col {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 18px;
      margin-top: 20px;
    }}
    .trace-grid {{
      display: flex;
      flex-direction: column;
      gap: 14px;
      margin-top: 16px;
    }}
    .trace-row {{
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 14px;
    }}
    .trace-panel {{
      padding: 16px;
    }}
    .trace-panel h2 {{
      font-size: 18px;
      margin: 0 0 8px;
    }}
    .trace-panel p {{
      margin: 0 0 10px;
      line-height: 1.5;
      font-size: 14px;
    }}
    .visual-grid {{
      display: block;
      margin-top: 20px;
    }}
    .compact-summary p {{
      margin: 0 0 10px;
      line-height: 1.56;
      font-size: 14.5px;
    }}
    .compact-summary h2 {{
      margin-bottom: 10px;
    }}
    .svg-panel svg {{
      width: 100%;
      height: auto;
      display: block;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 14px;
      font-size: 13px;
    }}
    th, td {{
      text-align: left;
      padding: 9px 12px;
      border-bottom: 1px solid var(--line);
    }}
    th {{
      color: var(--muted);
      font-weight: 600;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.06em;
    }}
    .note {{
      margin-top: 24px;
      padding: 14px 18px;
      border-left: 3px solid var(--accent);
      background: rgba(216,179,106,0.08);
      border-radius: 10px;
      color: var(--muted);
    }}
    .label {{
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.10em;
      color: var(--muted);
      margin-bottom: 8px;
      font-weight: 700;
    }}
    .decision-callout {{
      margin-top: 20px;
      background: linear-gradient(135deg, rgba(216,179,106,0.10), rgba(18,26,34,1));
      border: 1px solid rgba(216,179,106,0.35);
      border-radius: 22px;
      padding: 22px;
      break-inside: avoid;
      page-break-inside: avoid;
    }}
    .decision-callout .title {{
      font-size: 13px;
      text-transform: uppercase;
      letter-spacing: 0.16em;
      color: var(--accent);
      margin-bottom: 10px;
      font-weight: 800;
    }}
    .decision-callout .body {{
      font-size: 26px;
      line-height: 1.2;
      color: var(--text);
      font-weight: 800;
      margin-bottom: 10px;
    }}
    .recommendation-page {{
      display: flex;
      flex-direction: column;
      justify-content: space-between;
      gap: 18px;
    }}
    .recommendation-hero {{
      background:
        radial-gradient(circle at top right, rgba(216,179,106,0.18), transparent 24%),
        linear-gradient(135deg, #121a22 0%, #10161d 100%);
      border: 1px solid rgba(216,179,106,0.28);
      border-radius: 24px;
      padding: 26px;
    }}
    .recommendation-title {{
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.18em;
      color: var(--accent);
      margin-bottom: 10px;
      font-weight: 800;
    }}
    .recommendation-body {{
      font-family: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", Georgia, serif;
      font-size: 34px;
      line-height: 1.05;
      letter-spacing: -0.03em;
      color: var(--text);
      max-width: 900px;
    }}
    .recommendation-grid {{
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 18px;
    }}
    .kicker {{
      color: #d7e1e8;
      font-size: 14px;
      line-height: 1.65;
    }}
    .footer-meta {{
      margin-top: 18px;
      color: var(--muted);
      font-size: 11px;
      line-height: 1.6;
      border-top: 1px solid var(--line);
      padding-top: 12px;
    }}
    .page-footer {{
      margin-top: 10mm;
      padding-top: 12px;
      color: var(--muted);
      font-size: 10px;
      line-height: 1.4;
      letter-spacing: 0.12em;
      text-transform: uppercase;
    }}
    .page-footer::before {{
      content: "";
      display: block;
      height: 1px;
      width: 100%;
      margin-bottom: 10px;
      background: linear-gradient(90deg, rgba(216,179,106,0.95), rgba(216,179,106,0.25));
    }}
    .page-footer-top {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 4px;
    }}
    .page-footer-bottom {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      color: #7f909d;
      letter-spacing: 0.08em;
      text-transform: none;
    }}
  </style>
</head>
<body>
  <section class="pdf-page">
    <div class="page-inner">
      <div class="page-content">
        <div class="hero">
          <div class="cover-brand">
            {cover_logo_svg}
          </div>
          <div class="eyebrow">Noumenon Intelligence Unit · {"Lectura estructural para jurado" if jury_variant else "Lectura estructural de poder"}</div>
          <h1>{escape(case.client_name or "Caso Noumenon")} · {escape(case.project_name or "Informe ejecutivo")}</h1>
          <p>{escape(case.objective or "Lectura estructural para decisión ejecutiva.")}</p>
          <div class="hero-lead">{escape(lead_sentence)}</div>
          <div class="hero-meta">
            <div class="hero-meta-item">
              <div class="hero-meta-label">Integridad</div>
              <div class="hero-meta-value">{escape(integrity_display)}</div>
              <div style="font-size:11px;line-height:1.4;color:#9fb0bd;margin-top:4px;">{escape(integrity_copy)}</div>
            </div>
            <div class="hero-meta-item">
              <div class="hero-meta-label">Fricción</div>
              <div class="hero-meta-value">{escape(friction_display)}</div>
              <div style="font-size:11px;line-height:1.4;color:#9fb0bd;margin-top:4px;">{escape(friction_copy)}</div>
            </div>
            <div class="hero-meta-item">
              <div class="hero-meta-label">Arquetipo dominante</div>
              <div class="hero-meta-value">{escape(diagnosis.archetype_name)}</div>
            </div>
            <div class="hero-meta-item">
              <div class="hero-meta-label">Estado estructural</div>
              <div class="hero-meta-value">{escape(structural_state)}</div>
            </div>
            <div class="hero-meta-item">
              <div class="hero-meta-label">Riesgo prioritario</div>
              <div class="hero-meta-value">{escape(diagnosis.top_risk)}</div>
            </div>
            <div class="hero-meta-item">
              <div class="hero-meta-label">Clasificación</div>
              <div class="hero-meta-value">{escape(classification_copy)}</div>
            </div>
          </div>
          <div class="decision-callout">
            <div class="title">{"Decisión revelada" if jury_variant else "Decisión ejecutiva"}</div>
            <div class="body">{escape(decision)}</div>
            <div class="kicker">{escape(critical_action)}</div>
          </div>
        </div>
      </div>
      {_page_footer(1, total_pages, footer_case, footer_date)}
    </div>
  </section>

  <section class="pdf-page">
    <div class="page-inner">
      <div class="page-content">
        <div class="editorial-strip" style="margin-bottom:18px;">
          <div class="editorial-card">
            <div class="k">Arquetipo dominante</div>
            <div class="v">{escape(editorial_frame['archetype'])}</div>
          </div>
          <div class="editorial-card">
            <div class="k">Estado estructural</div>
            <div class="v">{escape(editorial_frame['structural_state'])}</div>
          </div>
          <div class="editorial-card">
            <div class="k">Riesgo dominante</div>
            <div class="v">{escape(editorial_frame['top_risk'])}</div>
          </div>
          <div class="editorial-card">
            <div class="k">Palanca prioritaria</div>
            <div class="v">{escape(editorial_frame['lever_label'])}</div>
            <div class="s">{escape(page2_lever_note)}</div>
          </div>
        </div>
        <div class="classification-band">
          <div class="panel">
            <div class="label">Lectura vecina</div>
            <div class="value-compact">{escape(archetype_comparison['runner_up_name'])}</div>
            <div class="value-note">{escape(robustness_label)}</div>
          </div>
          <div class="panel">
            <div class="label">Pregunta decisiva</div>
            <div class="value-compact">{escape(archetype_comparison['decisive'])}</div>
          </div>
          <div class="panel">
            <div class="label">Cómo se cerró la lectura</div>
            <div class="value-compact">{escape(resolution_label)}</div>
            <div class="value-note">{escape(archetype_comparison['priority'])}</div>
          </div>
        </div>
      </div>
      {_page_footer(2, total_pages, footer_case, footer_date)}
    </div>
  </section>

  <section class="pdf-page">
    <div class="page-inner">
      <div class="page-content">
        <div class="two-col">
          <div class="panel compact-summary">
            <h2>Síntesis ejecutiva</h2>
            <p><strong>Arquetipo dominante.</strong> {escape(diagnosis.archetype_name)}</p>
            <p><strong>Estado estructural.</strong> {escape(structural_state)}</p>
            <p><strong>Riesgo dominante.</strong> {escape(editorial_frame['top_risk'])}</p>
            <p><strong>Palanca prioritaria.</strong> {escape(editorial_frame['lever_label'])}</p>
            <p><strong>Situación.</strong> {escape(summary_situation)}</p>
            <p><strong>Decisión.</strong> {escape(decision)}</p>
            <p><strong>Acción crítica.</strong> {escape(critical_action)}</p>
            <p><strong>Impacto.</strong> {escape(impact)}</p>
            <p><strong>Riesgo de no actuar.</strong> {escape(summary_risk)}</p>
          </div>
          <div class="panel compact-summary">
            <h2>Contexto del caso</h2>
            <p><strong>Cliente.</strong> {escape(case.client_name or "—")}</p>
            <p><strong>Proyecto.</strong> {escape(case.project_name or "—")}</p>
            <p><strong>Analista.</strong> {escape(case.analyst_name or "—")}</p>
            <p><strong>Base de referencia.</strong> {escape(case.benchmark_name or "—")}</p>
            <p><strong>Contexto.</strong> {escape(case.context or "Sin contexto añadido en esta versión.")}</p>
          </div>
        </div>
      </div>
      {_page_footer(3, total_pages, footer_case, footer_date)}
    </div>
  </section>

  <section class="pdf-page">
    <div class="page-inner">
      <div class="page-content">
        <div class="trace-grid">
          <div class="trace-row">
            <div class="panel trace-panel">
              <div class="label">Base estructural</div>
              <h2 style="margin-top:0;">Por qué esta lectura se sostiene</h2>
              <p>{escape(structural_reading['causal_reading'])}</p>
              <p>{escape(structural_reading['principal_leak'])}</p>
            </div>
            <div class="panel trace-panel">
              <div class="label">Evidencia que más pesa</div>
              <h2 style="margin-top:0;">{escape(structural_reading['dominant_power'])}</h2>
              <p>{escape(structural_reading['dominant_evidence'])}</p>
              <p><strong>Nota del analista.</strong> {escape(structural_reading['dominant_note'])}</p>
            </div>
          </div>
          <div class="trace-row">
            <div class="panel trace-panel">
              <div class="label">Movimiento mínimo recomendado</div>
              <h2 style="margin-top:0;">Movimiento recomendado</h2>
              <p>{escape(structural_reading['minimum_intervention'])}</p>
              <p><strong>Notas maestras del caso.</strong> {escape(analyst_master_notes)}</p>
            </div>
            {comparison_html.replace('class="panel"', 'class="panel trace-panel"', 1)}
          </div>
        </div>
      </div>
      {_page_footer(4, total_pages, footer_case, footer_date)}
    </div>
  </section>

  <section class="pdf-page">
    <div class="page-inner">
      <div class="page-content">
        <div class="three-col">
          <div class="panel">
            <div class="label">{"Palanca crítica" if jury_variant else "Palanca prioritaria"}</div>
            <h2 style="margin-top:0;">{escape(intervention_title or "Intervención estructural")}</h2>
            <p>{escape(intervention_detail or "La lectura prioriza reforzar el nodo donde la potencia ya no se convierte en estabilidad.")}</p>
          </div>
          <div class="panel">
            <div class="label">{"Por qué esto importa" if jury_variant else "Por qué ahora"}</div>
            <h2 style="margin-top:0;">Foco de riesgo y brecha</h2>
            <p>{escape(lever_msg or "La arquitectura muestra una brecha visible entre capacidad y forma instituida.")}</p>
            <p>{escape(impact_msg or "La presión acumulada sugiere actuar antes de que la fuga gane inercia.")}</p>
          </div>
          <div class="panel">
            <div class="label">Confianza y siguiente paso</div>
            <h2 style="margin-top:0;">Confianza {escape(confidence_es)}</h2>
            <p>{escape(next_step or "Validar esta lectura con hechos primarios y cerrar el siguiente movimiento ejecutivo.")}</p>
          </div>
        </div>
      </div>
      {_page_footer(5, total_pages, footer_case, footer_date)}
    </div>
  </section>

  <section class="pdf-page">
    <div class="page-inner">
      <div class="page-content">
        <div class="visual-grid">
          <div class="panel svg-panel">
            <h2 style="margin-top:0;">Radar de potencia</h2>
            <p style="margin-top:0;margin-bottom:12px;color:#9fb0bd;">No mide calidad moral ni desempeño absoluto. Muestra cómo se distribuye la potencia entre poderes dentro del caso.</p>
            {radar_svg}
          </div>
        </div>
      </div>
      {_page_footer(6, total_pages, footer_case, footer_date)}
    </div>
  </section>

  <section class="pdf-page">
    <div class="page-inner">
      <div class="page-content">
        <div class="visual-grid">
          <div class="panel svg-panel">
            <h2 style="margin-top:0;">Mapa de desequilibrio</h2>
            <p style="margin-top:0;margin-bottom:12px;color:#9fb0bd;">Cruza potencia y fricción por nodo. El tamaño expresa estructura y el color expresa autoridad operativa.</p>
            {tension_map_svg}
          </div>
        </div>
      </div>
      {_page_footer(7, total_pages, footer_case, footer_date)}
    </div>
  </section>

  <section class="pdf-page">
    <div class="page-inner">
      <div class="page-content">
        <div class="visual-grid">
          <div class="panel svg-panel">
            <h2 style="margin-top:0;">Matriz de tensión</h2>
            <p style="margin-top:0;margin-bottom:12px;color:#9fb0bd;">Lectura horizontal por poder: capacidad visible, fricción, forma estructural y autoridad operativa en paralelo.</p>
            {heatmap_svg}
          </div>
        </div>
      </div>
      {_page_footer(8, total_pages, footer_case, footer_date)}
    </div>
  </section>

  <section class="pdf-page">
    <div class="page-inner">
      <div class="page-content">
        <div class="panel">
          <h2 style="margin-top:0;">Mapa estructural de poderes</h2>
          <p style="margin-top:0;margin-bottom:10px;color:#9fb0bd;">Ordenado de mayor a menor fricción estructural. En caso de empate, prioriza mayor potencia y después código de poder.</p>
          <p style="margin-top:0;margin-bottom:10px;color:#9fb0bd;">Potencia se lee en escala 0-100. Estructura y autoridad se leen en escala 0-10.</p>
          <table>
            <thead>
              <tr>
                <th>Poder</th>
                <th>Título</th>
                <th>Potencia</th>
                <th>Fricción</th>
                <th>Estructura</th>
                <th>Autoridad</th>
              </tr>
            </thead>
            <tbody>
              {rows_html}
            </tbody>
          </table>
        </div>

        <div class="note">
          {escape(
              "Noumenon no sustituye el juicio experto. Hace visible antes la tensión que normalmente solo se entiende cuando el deterioro ya ha empezado."
              if jury_variant
              else "Noumenon no sustituye el juicio experto. Esta salida organiza evidencia, tensiones y arquitectura de poder para facilitar una conversación de decisión más clara, trazable y accionable."
          )}
        </div>
        <div class="footer-meta">
          Documento preparado en Noumenon. Cliente: {escape(case.client_name or "—")} · Proyecto: {escape(case.project_name or "—")} · Analista: {escape(case.analyst_name or "—")} · Base de referencia: {escape(case.benchmark_name or "—")}
        </div>
      </div>
      {_page_footer(9, total_pages, footer_case, footer_date)}
    </div>
  </section>

  <section class="pdf-page">
    <div class="page-inner recommendation-page">
      <div class="page-content">
        <div class="recommendation-hero">
          <div class="recommendation-title">Recomendación ejecutiva</div>
          <div class="recommendation-body">{escape(executive_recommendation)}</div>
        </div>
        <div class="recommendation-grid" style="margin-top:18px;">
          <div class="panel">
            <div class="label">Por qué ahora</div>
            <h2 style="margin-top:0;">Ventana de decisión</h2>
            <p>{escape(lever_msg or impact_msg or "La lectura indica una brecha visible entre potencia y estructura que conviene cerrar antes de escalar más.")}</p>
          </div>
          <div class="panel">
            <div class="label">Riesgo de no actuar</div>
            <h2 style="margin-top:0;">Coste esperado</h2>
            <p>{escape(risk or "La organización puede convertir crecimiento en desgaste si mantiene la expansión sin reordenar el frente crítico.")}</p>
          </div>
          <div class="panel">
            <div class="label">Movimiento ejecutivo</div>
            <h2 style="margin-top:0;">Intervención mínima</h2>
            <p>{escape(critical_action)}</p>
          </div>
          <div class="panel">
            <div class="label">Siguiente conversación</div>
            <h2 style="margin-top:0;">Próximo paso</h2>
            <p>{escape(next_step or "Validar la lectura con hechos primarios y asignar dueño ejecutivo del frente crítico.")}</p>
          </div>
        </div>
        <div class="note" style="margin-top:18px;">
          La lectura concluye en una recomendación ejecutiva clara: decidir ahora reduce el riesgo de que la tensión crítica se convierta en desgaste estructural.
        </div>
      </div>
      {_page_footer(10, total_pages, footer_case, footer_date)}
    </div>
  </section>
</body>
</html>
"""


def save_report_html(case: CaseRecord, diagnosis: DiagnosisSnapshot, reports_dir: Path | None = None, *, variant: str = "default") -> Path:
    reports_dir = reports_dir or Path("noumenon_data_v2") / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    html = build_report_html(case, diagnosis, variant=variant)
    output_path = reports_dir / f"{case.case_id}.html"
    output_path.write_text(html, encoding="utf-8")
    return output_path
