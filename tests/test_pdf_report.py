"""
src/pdf_report.py testleri: PDF rapor uretiminin gercekten calistigini ve
gecerli bir PDF byte dizisi urettigini otomatik dogrular (bkz. METHODOLOGY.md
v1.1 "PDF export testi" maddesi) - onceden bu sadece manuel/gorsel kontrole
birakilmisti, app.py hicbir zaman import edilemedigi icin (Streamlit'e
bagimli top-level kod calistirir) test edilemiyordu; pdf_report.py'nin
Streamlit'ten bagimsiz ayri bir modul olmasi bunu mumkun kilar.
"""

import io
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pdf_report import build_pdf_report, pdf_safe


def _tiny_png_bytes() -> bytes:
    """Gercek bir matplotlib figurunden kucuk, gecerli bir PNG uretir -
    build_pdf_report'un pdf.image() cagrisini gercek bir dosyayla test
    etmek icin (sahte/bozuk byte dizisi degil)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(1, 1))
    ax.plot([1, 2, 3], [1, 2, 3])
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


# --- pdf_safe --------------------------------------------------------------

def test_pdf_safe_converts_infinity_symbol():
    assert pdf_safe("Cpk = ∞") == "Cpk = Inf"


def test_pdf_safe_converts_math_notation():
    assert pdf_safe("x̄̄ ± A2×R̄") == "x-double-bar ± A2×R-bar"
    assert pdf_safe("σ̂ = R̄/d2") == "sigma-hat = R-bar/d2"


def test_pdf_safe_leaves_plain_text_unchanged():
    assert pdf_safe("Parametre: pH") == "Parametre: pH"


def test_pdf_safe_converts_turkish_letters_missing_from_latin1():
    # Canli QA'da bulunan gercek hata: 'ğ' (ve ş/ı/İ/Ğ/Ş) Latin-1'de
    # (fpdf2'nin temel font kodlamasi) KARSILIGI OLMAYAN tek Turkce
    # harflerdir - donusturulmezse FPDFUnicodeEncodingException firlatir.
    assert pdf_safe("Peroksit değeri") == "Peroksit degeri"
    assert pdf_safe("İşlenmiş peynir - Kırmızı Şarap") == "Islenmis peynir - Kirmizi Sarap"


def test_pdf_safe_keeps_latin1_safe_accented_letters():
    # ö/ü/ç Latin-1'de MEVCUTTUR (ISO-8859-1) - bunlara dokunulmamali,
    # gereksiz yere ASCII'ye indirgemek okunakligi düşürür.
    assert pdf_safe("Süt tozu, çözelti") == "Süt tozu, çözelti"


def test_pdf_safe_generic_fallback_for_unmapped_unicode():
    # Elle eslenmeyen (haritada olmayan) beklenmedik bir unicode karakter
    # gelirse bile crash etmemeli - NFKD + ascii-ignore guvenlik agina duser.
    result = pdf_safe("Emoji test \U0001F33E sonu")
    assert "\U0001F33E" not in result
    result.encode("latin-1")  # crash etmemeli


# --- build_pdf_report --------------------------------------------------------

def test_build_pdf_report_produces_valid_pdf_bytes_without_chart():
    pdf_bytes = build_pdf_report(
        parameter="pH", product="Yogurt", chart_type_label="X-bar/R",
        n_samples=24, n_out_of_control=0, cpk=1.45, cpk_label="Cpk",
        quick_summary_text="24 alt grup analiz edildi, kontrol disi nokta yok, Cpk=1.450 ile surec yeterli.",
        chart_png_bytes=None,
    )
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 500


def test_build_pdf_report_produces_valid_pdf_bytes_with_chart():
    pdf_bytes = build_pdf_report(
        parameter="Brix", product="Elma suyu", chart_type_label="X-bar/R",
        n_samples=30, n_out_of_control=2, cpk=0.85, cpk_label="Cpk",
        quick_summary_text="30 alt grup analiz edildi, 2 kontrol disi nokta var, Cpk=0.850 ile surec yeterli degil.",
        chart_png_bytes=_tiny_png_bytes(),
    )
    assert pdf_bytes.startswith(b"%PDF")
    # Grafik goruntusu eklendigi icin grafiksiz rapordan belirgin sekilde
    # daha buyuk olmali (regresyon kontrolu: pdf.image() gercekten calisti).
    assert len(pdf_bytes) > 2000


def test_build_pdf_report_handles_infinite_cpk_without_crashing():
    # sigma_hat=0 uc durumunda Cpk = inf/-inf donebilir (bkz. spc_core.compute_cpk);
    # pdf_safe bu sembolu donusturmezse fpdf2 Latin-1 disi karakterde patlar.
    pdf_bytes = build_pdf_report(
        parameter="Peroksit Degeri", product="Zeytinyagi (naturel sizma)",
        chart_type_label="I-MR", n_samples=10, n_out_of_control=0,
        cpk=float("inf"), cpk_label="Cpu (tek tarafli)",
        quick_summary_text="10 olcum analiz edildi, kontrol disi nokta yok, Cpu=∞ ile surec mukemmel yeterli.",
        chart_png_bytes=None,
    )
    assert pdf_bytes.startswith(b"%PDF")


def test_build_pdf_report_handles_turkish_letters_in_product_name():
    # Regresyon: canli QA'da 'ğ' iceren bir metin (quick_summary/urun adi)
    # PDF export'unu FPDFUnicodeEncodingException ile cokertiyordu.
    pdf_bytes = build_pdf_report(
        parameter="Peroksit Degeri", product="Değirmen yağı - Iğdır",
        chart_type_label="I-MR", n_samples=10, n_out_of_control=0,
        cpk=1.2, cpk_label="Cpu (tek tarafli)",
        quick_summary_text="10 olcum analiz edildi, kontrol disi nokta yok, Cpu=1.200 ile surec yeterli.",
        chart_png_bytes=None,
    )
    assert pdf_bytes.startswith(b"%PDF")


if __name__ == "__main__":
    test_pdf_safe_converts_infinity_symbol()
    test_pdf_safe_converts_math_notation()
    test_pdf_safe_leaves_plain_text_unchanged()
    test_pdf_safe_converts_turkish_letters_missing_from_latin1()
    test_pdf_safe_keeps_latin1_safe_accented_letters()
    test_pdf_safe_generic_fallback_for_unmapped_unicode()
    test_build_pdf_report_produces_valid_pdf_bytes_without_chart()
    test_build_pdf_report_produces_valid_pdf_bytes_with_chart()
    test_build_pdf_report_handles_infinite_cpk_without_crashing()
    test_build_pdf_report_handles_turkish_letters_in_product_name()
    print("PDF_REPORT TESTLERI GECTI")
