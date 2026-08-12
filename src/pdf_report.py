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
import unicodedata
from datetime import datetime

from fpdf import FPDF

from result_helpers import format_cpk, get_cpk_level

# ğ/Ğ, ş/Ş, ı/İ - Turkce'nin Latin-1'de (ISO-8859-1) KARSILIGI OLMAYAN tek
# harfleri (ö/ü/ç gibi digerleri Latin-1'de mevcuttur, bu yuzden onlara
# dokunulmaz - PDF'te aksanli haliyle kalirlar). Bu 6 harf, parametre/urun/
# hammadde adlari gibi dinamik metinlerde kacip fpdf2'yi (core_fonts_encoding
# latin-1) FPDFUnicodeEncodingException ile cokertebiliyordu (bkz. manuel QA -
# canli PDF export "ğ" karakterinde patliyordu).
_TURKISH_LATIN1_GAP_MAP = str.maketrans({
    "ğ": "g", "Ğ": "G", "ş": "s", "Ş": "S", "ı": "i", "İ": "I",
})


def pdf_safe(text: str) -> str:
    """PDF'in temel Latin-1 fontuyla uyumsuz karakterleri ASCII karsiliklarina
    cevirir - fpdf2'nin gomulu (base14) fontlari Latin-1 disina cikan
    karakterleri kabul etmez. Once ozel SPC sembollerini (sonsuz, x-bar vb.)
    anlamli karsiliklarina, sonra Turkce'nin Latin-1'de karsiligi olmayan 6
    harfini (ğ/Ğ/ş/Ş/ı/İ) cevirir. Bunlardan SONRA hala latin-1'e
    sigdirilamayan bir seyler kalirsa (orn. ileride eklenecek yeni bir
    urun/hammadde adinda kacan beklenmedik bir unicode karakter - tek tek
    karakter eklemek yerine GENEL bir guvenlik agi), NFKD ile ayristirip
    ASCII'ye indirger; asla FPDFUnicodeEncodingException'a birakmaz."""
    text = (
        text.replace("∞", "Inf")
        .replace("x̄̄", "x-double-bar")
        .replace("x̄", "x-bar")
        .replace("σ̂", "sigma-hat")
        .replace("R̄", "R-bar")
        .replace("MR̄", "MR-bar")
        .translate(_TURKISH_LATIN1_GAP_MAP)
    )
    try:
        text.encode("latin-1")
        return text
    except UnicodeEncodeError:
        normalized = unicodedata.normalize("NFKD", text)
        return normalized.encode("ascii", "ignore").decode("ascii")


def build_pdf_report(parameter: str, product: str, chart_type_label: str,
                      n_samples: int, n_out_of_control: int, cpk: float,
                      cpk_label: str, quick_summary_text: str,
                      chart_images: list[tuple[str, bytes]] | None = None) -> bytes:
    """Grafik(ler) + KPI ozeti + Quick Summary'yi bir PDF'e dokumler. Mevcut PNG
    export'un (fig_to_png_bytes) genisletilmesi - ayni PNG byte'lari burada da
    kullanilir, ek bir grafik render islemi yapilmaz.

    chart_images: (baslik, PNG bayt dizisi) ciftlerinden olusan liste - ana
    kontrol grafigi + range/MR grafigi + surec yeterlilik histogrami gibi
    BIRDEN FAZLA gorseli sirayla ekler (gerekirse yeni sayfaya tasarak).
    ONCEDEN sadece TEK bir grafik (ana kontrol grafigi) gomuluyordu - R/MR
    chart ve histogram PDF'e hic dahil edilmiyordu (bkz. kullanici raporu:
    'sadece X-bar grafigi PDF'e dahil oluyor'). None/bos liste veya
    listedeki None girdiler guvenle atlanir."""
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

    for label, png_bytes in (chart_images or []):
        if not png_bytes:
            continue
        # Bir onceki gorsel sayfanin cogunu doldurduysa (A4 yuksekligi ~297mm,
        # alt kenar bosluguyla ~280mm kullanilabilir), yeni gorsel+baslik icin
        # yeni sayfa ac - aksi halde fpdf2 gorseli sayfa disina tasirir/kesebilir.
        if pdf.get_y() > 160:
            pdf.add_page()
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(0, 7, pdf_safe(label), ln=True)
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                tmp.write(png_bytes)
                tmp_path = tmp.name
            pdf.image(tmp_path, w=180)
        finally:
            if tmp_path:
                os.unlink(tmp_path)
        pdf.ln(3)

    return bytes(pdf.output())
