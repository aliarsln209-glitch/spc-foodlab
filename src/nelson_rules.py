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


def _check_k_of_n_beyond_sigma(
    values: list[float], center: float, sigma: float, k: int, n: int, sigma_multiplier: float
) -> set[int]:
    """Nelson Kural 5 (k=2,n=3,mult=2) ve Kural 6 (k=4,n=5,mult=1) AYNI
    'k-of-n, ayni tarafta, m-sigma otesinde' oruntusunu paylasir - bu ortak
    kaydirmali-pencere mantigi burada tek yerde tutulur, iki kural da kendi
    parametreleriyle bunu cagirir (kopyala-yapistir kaymasini onlemek icin).

    'Ayni taraf' sarti onemlidir: karsit taraflardaki noktalar sureci tek
    yone kaydiran bir ozel-neden degil, iki yonlu rastgele sicrama olabilir
    - bu yuzden AYRI AYRI ust/alt taraf sayilir, toplam degil.

    Sinir dahil (>=) kabul edildi: tam olarak m*sigma uzaklikta bir nokta
    "otesinde" sayilir. sigma<=0 veya n'den az nokta durumunda kural
    ANLAMSIZDIR - bos kume doner."""
    if sigma <= 0 or len(values) < n:
        return set()

    upper = center + sigma_multiplier * sigma
    lower = center - sigma_multiplier * sigma
    flagged: set[int] = set()

    for end in range(n - 1, len(values)):
        window = range(end - n + 1, end + 1)
        above = [i for i in window if values[i] >= upper]
        below = [i for i in window if values[i] <= lower]
        if len(above) >= k:
            flagged.update(above)
        if len(below) >= k:
            flagged.update(below)

    return flagged


def check_rule_2of3_beyond_2sigma(values: list[float], center: float, sigma: float) -> set[int]:
    """Nelson Kural 5: ardisik herhangi 3 noktadan EN AZ 2'si, merkez
    cizginin AYNI tarafinda 2 sigma veya otesindeyse (Zone A veya disinda),
    o ihlal eden nokta(lar) isaretlenir. Detay/gerekce: bkz. _check_k_of_n_beyond_sigma."""
    return _check_k_of_n_beyond_sigma(values, center, sigma, k=2, n=3, sigma_multiplier=2)


def check_rule_4of5_beyond_1sigma(values: list[float], center: float, sigma: float) -> set[int]:
    """Nelson Kural 6: ardisik herhangi 5 noktadan EN AZ 4'u, merkez
    cizginin AYNI tarafinda 1 sigma veya otesindeyse (Zone B/A veya
    disinda, yani Zone C'nin - merkeze en yakin bolgenin - disinda), o
    ihlal eden nokta(lar) isaretlenir.

    Kural 5'ten (2/3, 2 sigma) FARKI: burada sinir daha gevsek (1 sigma) ama
    pencere/esik daha genis (5 noktadan 4'u) - normal dagilimda bir noktanin
    1 sigma disinda olmasi zaten ~%32 ihtimalle beklenir, bu yuzden TEK
    basina anlamsizdir; 5 noktadan 4'unun AYNI TARAFTA olmasi rastgele
    beklenenin cok otesinde, gercek bir kaymaya isaret eder.
    Detay/gerekce: bkz. _check_k_of_n_beyond_sigma."""
    return _check_k_of_n_beyond_sigma(values, center, sigma, k=4, n=5, sigma_multiplier=1)
