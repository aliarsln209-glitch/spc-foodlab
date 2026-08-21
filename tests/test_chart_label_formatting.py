"""
Manuel QA'da bulunan hata: KPI kartlari/tablo parametrenin decimal_places
degerine (orn. pH=2) uyuyordu, ama X-bar/R ve I-MR kontrol grafiklerinin
uzerindeki etiketler (annotate_hline ile cizilen UCL/LCL/x-bar/R-bar
metinleri) sabit ".3f" ile formatlaniyordu - KPI kartinda "7.02" derken
grafikte "x̄=7.024" gibi tutarsiz bir gorunume yol aciyordu.

app.py Streamlit'e bagimli top-level kod calistirdigi icin import
edilemiyor (bkz. src/csv_io.py, src/pdf_report.py docstring'leri - proje
genelinde bu sinir boyle) - bu yuzden burada davranisi degil, KAYNAK
KODUNU (annotate_hline() cagrilarinin format spec'ini) statik olarak
kontrol ediyoruz. Bu, "birisi bu duzeltmeyi yanlislikla geri alirsa"
senaryosunu yakalayan dogrudan bir regresyon testidir.
"""

import os
import re

APP_PY_PATH = os.path.join(os.path.dirname(__file__), "..", "src", "app.py")


def _read_app_source() -> str:
    with open(APP_PY_PATH, encoding="utf-8") as f:
        return f.read()


def _annotate_hline_calls(source: str) -> list[str]:
    """Kaynak kodundaki tum annotate_hline(...) cagrilarini (tanimi haric)
    tek satir/blok metin olarak dondurur."""
    calls = []
    for match in re.finditer(r"annotate_hline\(", source):
        start = match.end()
        depth = 1
        i = start
        while depth > 0:
            if source[i] == "(":
                depth += 1
            elif source[i] == ")":
                depth -= 1
            i += 1
        calls.append(source[start:i])
    return calls


def _real_calls(source: str) -> list[str]:
    """_annotate_hline_calls()'un fonksiyon TANIMINI (parametre listesi de
    'ax, ...' ile basladigi icin) degil, sadece gercek cagrilari dondurur -
    tanimda tip anotasyonu (': float', ': str') olur, gercek cagrilarda olmaz."""
    return [c for c in _annotate_hline_calls(source) if c.strip().startswith("ax") and ": float" not in c]


def test_annotate_hline_call_sites_are_all_present():
    # Regresyon: X-bar/R (UCL/LCL/x̄̄, UCL/LCL/R̄) + I-MR (UCL/LCL/x̄, UCL/MR̄)
    # icin 10 + v1.2 OOS/OOT ayrimiyla I-MR I chart'ina eklenen USL/LSL
    # etiketleri (2 yeni) = 12 + Renk Paneli v2 (Task 3) L*/a*/b* I-MR
    # kartlarina eklenen USL/LSL etiketleri (2 yeni) = 14 annotate_hline
    # cagrisi olmali. X-bar chart'ina BILEREK USL/LSL etiketi EKLENMEDI (o
    # grafik alt grup ORTALAMASINI cizer, ham olcumu degil - bkz. app.py'deki
    # OOS/OOT yorumu). Bu sayi degisirse (yeni bir etiket eklendi/silindi)
    # test bilerek guncellenmelidir.
    source = _read_app_source()
    calls = _real_calls(source)
    assert len(calls) == 14, (
        f"Beklenen 14 annotate_hline cagrisi, {len(calls)} bulundu - "
        "yeni/eksik bir grafik etiketi olabilir, decimal_places kontrolunu guncelleyin."
    )


def test_annotate_hline_calls_use_decimal_places_not_hardcoded_precision():
    source = _read_app_source()
    calls = _real_calls(source)
    assert calls, "annotate_hline cagrisi bulunamadi - test dosya yolunu/regex'i kontrol edin"

    hardcoded_precision = re.compile(r":\.\d+f")
    for call in calls:
        assert hardcoded_precision.search(call) is None, (
            f"Sabit basamak formati (orn. .3f) bulundu, decimal_places kullanilmali: {call!r}"
        )
        assert "decimal_places" in call, (
            f"annotate_hline cagrisi decimal_places'i kullanmiyor: {call!r}"
        )


if __name__ == "__main__":
    test_annotate_hline_call_sites_are_all_present()
    test_annotate_hline_calls_use_decimal_places_not_hardcoded_precision()
    print("CHART LABEL FORMATTING TESTLERI GECTI")
