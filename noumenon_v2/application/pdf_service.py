from __future__ import annotations

import tempfile
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

from noumenon_v2.domain.models import CaseRecord


def build_v2_pdf_filename(case: CaseRecord) -> str:
    stem_client = (case.client_name or "CLIENTE").strip().replace(" ", "_")
    stem_project = (case.project_name or "V2").strip().replace(" ", "_")
    stamp = datetime.now().strftime("%Y%m%d")
    return f"NOUMENON_V2_{stem_client}_{stem_project}_{stamp}.pdf"


def render_pdf_bytes_from_html(html_content: str) -> bytes:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".html", mode="w", encoding="utf-8") as html_file:
        html_file.write(html_content)
        html_path = Path(html_file.name)

    pdf_path = html_path.with_suffix(".pdf")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 2200})
            page.goto(f"file://{html_path}", wait_until="networkidle")
            page.emulate_media(media="print")
            page.pdf(
                path=str(pdf_path),
                format="A4",
                print_background=True,
                prefer_css_page_size=True,
                margin={
                    "top": "0mm",
                    "right": "0mm",
                    "bottom": "0mm",
                    "left": "0mm",
                },
            )
            browser.close()
        return pdf_path.read_bytes()
    finally:
        if html_path.exists():
            html_path.unlink()
        if pdf_path.exists():
            pdf_path.unlink()


def save_pdf_bytes(case: CaseRecord, pdf_bytes: bytes, reports_dir: Path | None = None) -> Path:
    reports_dir = reports_dir or Path("noumenon_data_v2") / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    output_path = reports_dir / build_v2_pdf_filename(case)
    output_path.write_bytes(pdf_bytes)
    return output_path
