"""
Nelson kurallari - UCL/LCL asimi disinda, oruntu tabanli "ozel neden"
sinyallerini tespit eder.

Kaynak: Nelson, L.S. (1984), "The Shewhart Control Chart - Tests for
Special Causes", Journal of Quality Technology, 16(4), 237-239.

spc_core.py'den AYRI bir modul olarak tutulmasinin nedeni: bu, X-bar/R/
Cpk'dan FARKLI bir kural ailesi (oruntu tanima, tek bir sayisal formul
degil) - ayri tutmak spc_core.py'yi (surekli-veri kontrol limiti/Cpk
hesaplarina ozgu) sade tutar. csv_io.py/pdf_report.py ile ayni gerekce:
Streamlit'e bagimli olmayan, pytest ile dogrudan test edilebilen saf
mantik (bkz. tests/test_nelson_rules.py).

Her kural fonksiyonu, ihlal EDEN noktalarin 0-tabanli indekslerini bir
kume (set[int]) olarak dondurur - cagiran taraf (app.py) bu indeksleri
mevcut highlight_oos_segments() ile AYNI desende grafikte isaretleyebilir.
center/sigma parametreleri cagiran tarafin ZATEN hesapladigi degerlerdir
(x_double_bar/sigma_hat=r_bar/d2 veya x_bar/sigma_hat=mr_bar/d2) - burada
yeniden hesaplanmaz.
"""


def check_rule_2of3_beyond_2sigma(values: list[float], center: float, sigma: float) -> set[int]:
    """Nelson Kural 5: ardisik herhangi 3 noktadan EN AZ 2'si, merkez
    cizginin AYNI tarafinda 2 sigma veya otesindeyse (Zone A veya disinda),
    o ihlal eden nokta(lar) isaretlenir.

    'Ayni taraf' sarti onemlidir: biri +2sigma ustunde biri -2sigma altinda
    olan 2 nokta bu kurali TETIKLEMEZ - sinyal, surecin tek bir yone dogru
    kaymasidir, iki yonlu rastgele sicramalar degil.

    Sinir dahil (>=) kabul edildi: tam olarak 2 sigma uzaklikta bir nokta
    "Zone A" icinde sayilir (Zone B'nin degil).

    sigma<=0 (varyasyon yok) veya 3'ten az nokta durumunda kural
    ANLAMSIZDIR - bos kume doner (sigma=0 iken her sey merkeze esittir,
    '2 sigma disi' kavraminin kendisi tanimsizdir)."""
    if sigma <= 0 or len(values) < 3:
        return set()

    upper = center + 2 * sigma
    lower = center - 2 * sigma
    flagged: set[int] = set()

    for end in range(2, len(values)):
        window = range(end - 2, end + 1)
        above = [i for i in window if values[i] >= upper]
        below = [i for i in window if values[i] <= lower]
        if len(above) >= 2:
            flagged.update(above)
        if len(below) >= 2:
            flagged.update(below)

    return flagged
