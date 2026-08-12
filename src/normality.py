"""
Shapiro-Wilk normallik testi - capability analizinin (Cpk/Ppk) dayandigi
"veri yaklasik normal dagilir" varsayimini SEFFAF sekilde raporlar.

spc_core.py/nelson_rules.py ile ayni gerekce: Streamlit'e bagimli olmayan,
pytest ile dogrudan test edilebilen saf mantik. Ayri bir modul olarak
tutulmasinin nedeni: bu, X-bar/R/Cpk/Nelson'dan FARKLI bir istatistik
ailesi (dagilim testi) - spc_core.py'nin "kontrol grafigi/Cpk cekirdegi"
kapsamini bulaniklastirmasin diye.

ONEMLI (METHODOLOGY.md v1.2 "Normality / dagilim kontrolu" maddesi):
bu, otomatik bir "normal degil -> SPC yapilamaz" KAPISI DEGILDIR - sadece
seffaflik amacli bir uyaridir. Cagiran taraf (app.py) sonucu HER ZAMAN
gosterir, hicbir hesaplamayi ENGELLEMEZ/GIZLEMEZ.
"""

from scipy import stats

MIN_SAMPLE_SIZE_FOR_SHAPIRO = 3  # scipy.stats.shapiro'nun kendi kisiti


def check_normality(values: list[float]) -> tuple[float, float]:
    """Shapiro-Wilk testinin (W istatistigi, p-degeri) ciftini dondurur.

    Kendi algoritmamizi YENIDEN IMPLEMENTE ETMIYORUZ - scipy.stats.shapiro
    zaten standart, dogrulanmis bir uygulamadir; bu fonksiyon ince bir
    sarmalayicidir. Dogrulama (bkz. tests/test_normality.py), KENDI
    formulumuzu degil, scipy CAGRISINI DOGRU YAPTIGIMIZI kanitlar - scipy'nin
    resmi dokumantasyon ornegiyle (x=[148,154,158,160,161,162,166,170,182,
    195,236] -> W≈0.7888146948353875, p≈0.006703814056502984) capraz
    kontrol edildi.

    len(values) < MIN_SAMPLE_SIZE_FOR_SHAPIRO ise ValueError firlatir -
    cagiran taraf bu kontrolu ONCEDEN yapip yetersiz veri icin testi HIC
    CAGIRMAMALIDIR (bkz. app.py'deki n>=3 kontrolu)."""
    if len(values) < MIN_SAMPLE_SIZE_FOR_SHAPIRO:
        raise ValueError(
            f"Shapiro-Wilk testi en az {MIN_SAMPLE_SIZE_FOR_SHAPIRO} deger gerektirir, "
            f"{len(values)} verildi."
        )
    result = stats.shapiro(values)
    return float(result.statistic), float(result.pvalue)


def interpret_normality(w: float, p: float, alpha: float = 0.05) -> tuple[str, str]:
    """(mesaj, seviye) cifti dondurur - seviye 'info' (normallikten anlamli
    sapma tespit edilmedi) veya 'warning' (anlamli sapma var) olabilir;
    cagiran taraf (app.py) buna gore st.info/st.warning secer.

    p > alpha ise H0 (normal dagilim) REDDEDILEMEZ - bu 'veri KESINLIKLE
    normaldir' anlamina GELMEZ, sadece mevcut ornekle normallikten anlamli
    bir sapma TESPIT EDILEMEDI demektir (istatistiksel testlerin dogasi
    geregi - 'kanit yoklugu, yokluk kaniti degildir')."""
    if p > alpha:
        return (
            f"Shapiro-Wilk testi (W={w:.4f}, p={p:.4f}): normal dagilimdan "
            f"anlamli bir sapma tespit edilmedi (p>{alpha}) - capability "
            "analizi (Cpk/Ppk) icin normal dagilim varsayimi bu veriyle makul gorunuyor.",
            "info",
        )
    return (
        f"Shapiro-Wilk testi (W={w:.4f}, p={p:.4f}): veri normal dagilimdan "
        f"ANLAMLI SEKILDE sapiyor (p<={alpha}) - Cpk/Ppk gibi capability "
        "indeksleri normal dagilim VARSAYAR, bu veri icin sonuclar dikkatli "
        "yorumlanmalidir (otomatik bir engelleme YOK, sadece seffaflik amacli bir uyari).",
        "warning",
    )
