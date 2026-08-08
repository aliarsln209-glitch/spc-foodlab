"""
Tek sayfalik PDF analiz raporu uretimi - Streamlit'e bagimli olmayan saf
mantik (fpdf2 disinda hicbir UI kutuphanesine ihtiyac duymaz).

app.py'den ayri tutulmasinin nedeni spc_core.py/result_helpers.py ile
ayni: Streamlit calistirmadan pytest ile dogrudan test edilebilmesi
(bkz. tests/test_pdf_report.py) - "PDF export testi" (v1.1 roadmap
maddesi), rapor uretiminin gercekten calistigini otomatik dogrular.
"""

import os
import tempfile
from datetime import datetime

from fpdf import FPDF

from result_helpers import format_cpk, get_cpk_level


def pdf_safe(text: str) -> str:
    """PDF'in temel Latin-1 fontuyla uyumsuz karakterleri (orn. sonsuz
    isareti) ASCII karsiliklarina cevirir - fpdf2'nin gomulu (base14)
    fontlari Latin-1 disina cikan karakterleri kabul etmez."""
    return (
        text.replace("∞", "Inf")
        .replace("x̄̄", "x-double-bar")
        .replace("x̄", "x-bar")
        .replace("σ̂", "sigma-hat")
        .replace("R̄", "R-bar")
        .replace("MR̄", "MR-bar")
    )


def build_pdf_report(parameter: str, product: str, chart_type_label: str,
                      n_samples: int, n_out_of_control: int, cpk: float,
                      cpk_label: str, quick_summary_text: str,
                      chart_png_bytes: bytes | None) -> bytes:
    """Grafik + KPI ozeti + Quick Summary'yi tek sayfalik bir PDF'e dokumler.
    Mevcut PNG export'un (fig_to_png_bytes) genisletilmesi - ayni PNG byte'lari
    burada da kullanilir, ek bir grafik render islemi yapilmaz."""
    _, level_label, _ = get_cpk_level(cpk)

    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "SPC FoodLab - Analiz Raporu", ln=True)

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(110, 110, 110)
    pdf.cell(0, 6, f"Olusturma: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}", ln=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Analiz Bilgisi", ln=True)
    pdf.set_font("Helvetica", "", 10)
    for line in [
        f"Parametre: {parameter}",
        f"Urun: {product}",
        f"Chart Tipi: {chart_type_label}",
        f"Ornek Sayisi: {n_samples}",
        f"Kontrol Disi Nokta: {n_out_of_control}",
        f"{pdf_safe(cpk_label)}: {pdf_safe(format_cpk(cpk))} ({level_label})",
    ]:
        pdf.cell(0, 6, pdf_safe(line), ln=True)
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Ozet", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 6, pdf_safe(quick_summary_text))
    pdf.ln(3)

    if chart_png_bytes:
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp.write(chart_png_bytes)
                tmp_path = tmp.name
            pdf.image(tmp_path, w=180)
        finally:
            if tmp_path:
                os.unlink(tmp_path)

    return bytes(pdf.output())
