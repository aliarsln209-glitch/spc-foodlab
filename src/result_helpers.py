"""
Sonuc sunumu icin saf (Streamlit'e bagimli olmayan) yardimci fonksiyonlar.

spc_core.py'daki formullerden farkli olarak burada dogrulanmasi gereken bir
istatistiksel formul yok - bunlar mevcut Cpk/Cpu, ornek listesi gibi
sonuclarin OKUNAKLI hale getirilmesiyle ilgili (rozet, trend oku, ozet metni,
demo senaryosu hedefleri). Ayri dosyada tutulmasinin nedeni: Streamlit
import'u olmadan pytest ile dogrudan test edilebilmesi (bkz.
tests/test_result_helpers.py).
"""

from spc_core import is_spec_valid


def format_cpk(cpk: float) -> str:
    """Cpk/Cpu metrik gosterimi - r_bar/mr_bar=0 (varyasyon yok) durumunda
    compute_cpk() sonsuz dondurur; bunu okunakli sekilde gosterir."""
    if cpk == float("inf"):
        return "∞"
    if cpk == float("-inf"):
        return "-∞"
    return f"{cpk:.3f}"


def get_cpk_level(cpk: float) -> tuple[str, str, str]:
    """Cpk/Cpu degerine gore (emoji, seviye etiketi, renk) rozet bilgisi.
    Esikler: >=1.67 Mukemmel, 1.33-1.67 Yeterli, 1.0-1.33 Sinirda, <1.0
    Yetersiz - yaygin SPC kabulu (bkz. render_cpk_message esikleri).
    Etiketler Turkce'dir (tum arayuzde tek dil kullanmak icin - bkz.
    build_quick_summary'deki yorum cumleleri de ayni etiketlerle eslesir).

    Renkler mavi->mor->kirmizi ailesinden secildi (klasik yesil/turuncu/
    kirmizi degil) - kullanicinin sidebar'dan sectigi 'Vurgu rengi' (varsayilan
    mavi, ama serbestce degistirilebilir) ile bu istatistiksel sonuc renkleri
    arasinda olasi bir karisikligi onlemek icin ayri bir renk ailesi
    kullanilir."""
    if cpk == float("-inf"):
        return "\U0001F534", "Yetersiz", "#dc2626"
    if cpk == float("inf") or cpk >= 1.67:
        return "\U0001F535", "Mukemmel", "#2563eb"
    if cpk >= 1.33:
        return "\U0001F535", "Yeterli", "#2563eb"
    if cpk >= 1.0:
        return "\U0001F7E3", "Sinirda", "#7c3aed"
    return "\U0001F534", "Yetersiz", "#dc2626"


def compute_trend(series: list[float], window: int = 6) -> tuple[str, float] | None:
    """Son 'window' nokta ile ondan onceki 'window' nokta arasindaki ortalama
    farkini karsilastiran basit bir trend gostergesi (yukselen/dusen/sabit).
    En az 4 nokta gerekir; daha az veride anlamli bir trend cikarilamaz."""
    n = len(series)
    if n < 4:
        return None
    w = min(window, n // 2)
    recent_avg = sum(series[-w:]) / w
    previous_avg = sum(series[-2 * w:-w]) / w
    delta = recent_avg - previous_avg
    direction = "up" if delta > 0 else ("down" if delta < 0 else "flat")
    return direction, delta


def build_quick_summary(sample_word: str, n_samples: int, n_oot: int, n_oos: int,
                         cpk: float, cpk_label: str) -> str:
    """Analiz sonrasi otomatik olusturulan kisa metin ozeti (if-else ile,
    formul degil - sadece mevcut sonuclarin duz dile cevrilmesi).

    n_oot (Out of Trend - UCL/LCL asimi VEYA Nelson oruntu sinyali) ve n_oos
    (Out of Specification - LSL/USL disina cikan ham olcum) BAGIMSIZ iki
    sayidir - ONCEDEN (v1.1.1 ve oncesi) burada tek bir 'kontrol disi' sayisi
    vardi ve o aslinda SADECE bugunku n_oot'a karsilik geliyordu; LSL/USL
    hic ayri degerlendirilmiyordu. Bkz. METHODOLOGY.md v1.2 'OOS/OOT ayrimi'."""
    _, level_label, _ = get_cpk_level(cpk)
    oot_text = (
        "OOT (kontrol disi) nokta yok" if n_oot == 0
        else f"{n_oot} OOT (kontrol disi) nokta var"
    )
    oos_text = (
        "OOS (spesifikasyon disi) nokta yok" if n_oos == 0
        else f"{n_oos} OOS (spesifikasyon disi) nokta var"
    )
    level_text = {
        "Mukemmel": "surec mukemmel yeterli",
        "Yeterli": "surec yeterli",
        "Sinirda": "surec sinirda yeterli",
        "Yetersiz": "surec yeterli degil",
    }[level_label]
    return (
        f"{n_samples} {sample_word} analiz edildi, {oot_text}, {oos_text}, "
        f"{cpk_label}={format_cpk(cpk)} ile {level_text}."
    )


def build_trend_nelson_comment(trend: tuple[str, float] | None, nelson_triggered: bool) -> str:
    """v1.2 Madde 11: trend yonu + Nelson sinyaline dayanan kisa yorum
    cumlesi - build_quick_summary()'nin URETTIGI metne EKLENIR (hem in-app
    'Ozet' karti hem PDF raporu AYNI quick_summary metnini paylastigi icin
    bu cumle BURADA uretilip cagiran tarafta birlestirilir, iki ayri yerde
    tekrar yazilmaz).

    trend=None veya direction='flat' ise trend hakkinda hicbir sey
    SOYLENMEZ - 'sabit' bir sey rapor edilecek kadar dikkat cekici degildir.
    nelson_triggered, UCL/LCL asimindan BAGIMSIZ olarak SADECE Nelson
    oruntu kurallarindan (2/3-2σ, 4/5-1σ, 9-ayni-taraf) en az birinin
    tetiklenip tetiklenmedigini belirtir - cagiran taraf bunu
    compute_nelson_oot_indices() sonucundan (UCL/LCL kumesiyle
    BIRLESTIRILMEDEN once) turetmelidir."""
    parts = []
    if trend is not None:
        direction, _ = trend
        if direction == "up":
            parts.append("son noktalarda yukselen bir egilim gozlemleniyor")
        elif direction == "down":
            parts.append("son noktalarda dusen bir egilim gozlemleniyor")
    if nelson_triggered:
        parts.append(
            "Nelson kurallarindan biri tetiklendi (oruntu tabanli sinyal - "
            "tek bir noktanin limit asmasindan farkli olarak surecin "
            "sistematik bir sapma gosterebilecegine isaret eder)"
        )
    if not parts:
        return ""
    return " Ayrica " + "; ".join(parts) + "."


def demo_scenario_targets(param_config: dict, product_name: str | None) -> tuple[float, float, float]:
    """Secilen demo senaryosuna (urun) gore hedef ortalama, alt grup (R̄) /
    tekli-olcum (sigma) yayilimi ve shift_amount hesaplar. product_name=None
    veya urunun tanimli bir araligi yoksa (orn. 'Ozel/Manuel gir'), parametrenin
    genel varsayilanlarina (PARAMETER_CONFIG) geri doner - onceki tek-senaryolu
    davranisla birebir ayni sonucu verir."""
    product_range = param_config["products"].get(product_name) if product_name else None

    if product_range is None:
        mean = param_config["demo_target_mean"]
        spread = param_config.get("demo_target_r_bar") or param_config.get("demo_target_sigma")
        # demo_shift_amount sadece alt grup bazli parametrelerde tanimli (bkz.
        # PARAMETER_CONFIG); tanimsizsa (I-MR parametreleri) spread*3 kullanilir -
        # bu, generate_demo_individual()'in kendi ic varsayilaniyla (shift_amount=
        # None -> target_sigma*3) birebir aynidir, davranis degismez.
        shift_amount = param_config.get("demo_shift_amount") or spread * 3
        return mean, spread, shift_amount

    range_lsl, range_usl = product_range
    if range_lsl is not None:
        mean = (range_lsl + range_usl) / 2
        span = range_usl - range_lsl
    else:
        mean = range_usl - range_usl * 0.08
        span = range_usl * 0.16
    spread = max(span / 8, 1e-6)
    shift_amount = spread * 3
    return mean, spread, shift_amount


def measurement_plausibility_warnings(
    labeled_values: list[tuple[str, float]], lsl: float, usl: float, one_sided: bool
) -> list[str]:
    """Girilen olcumlerden MEVCUT spesifikasyon (LSL/USL) araligi disinda
    kalanlar icin uyari metni uretir - bir HATA/engelleme DEGILDIR, deger
    yine de kaydedilir (SPC'nin spesifikasyon disi noktalari da GORMESI
    gerekir). Amac, tipik veri girisi hatalarini (orn. 7.01 yerine
    yanlislikla 70.1 yazilmasi - pH'in fiziksel araligi olan 0-14'un
    icinde kaldigi icin number_input'un min/max sinirlamasi bunu YAKALAMAZ,
    ama urunun spesifikasyonuna gore acikca olagan disidir) YAKALAMAKTIR.

    is_spec_valid() ile LSL/USL GECERSIZSE (orn. henuz urun secilmemis)
    hicbir uyari uretilmez - boyle bir durumda spesifikasyonun kendisi
    guvenilir degildir, kiyaslama anlamsiz olur."""
    if not is_spec_valid(one_sided, lsl, usl):
        return []
    warnings = []
    for label, value in labeled_values:
        if value > usl:
            warnings.append(f"{label}={value:g}, mevcut USL'nin ({usl:g}) uzerinde")
        elif not one_sided and value < lsl:
            warnings.append(f"{label}={value:g}, mevcut LSL'nin ({lsl:g}) altinda")
    return warnings
