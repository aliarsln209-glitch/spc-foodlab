"""
Sonuc sunumu icin saf (Streamlit'e bagimli olmayan) yardimci fonksiyonlar.

spc_core.py'daki formullerden farkli olarak burada dogrulanmasi gereken bir
istatistiksel formul yok - bunlar mevcut Cpk/Cpu, ornek listesi gibi
sonuclarin OKUNAKLI hale getirilmesiyle ilgili (rozet, trend oku, ozet metni,
demo senaryosu hedefleri). Ayri dosyada tutulmasinin nedeni: Streamlit
import'u olmadan pytest ile dogrudan test edilebilmesi (bkz.
tests/test_result_helpers.py).
"""


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
    Esikler: >=1.67 Excellent, 1.33-1.67 Capable, 1.0-1.33 Marginal, <1.0
    Not Capable - yaygin SPC kabulu (bkz. render_cpk_message esikleri)."""
    if cpk == float("-inf"):
        return "\U0001F534", "Not Capable", "#e03131"
    if cpk == float("inf") or cpk >= 1.67:
        return "\U0001F7E2", "Excellent", "#2f9e44"
    if cpk >= 1.33:
        return "\U0001F7E2", "Capable", "#2f9e44"
    if cpk >= 1.0:
        return "\U0001F7E1", "Marginal", "#f08c00"
    return "\U0001F534", "Not Capable", "#e03131"


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


def build_quick_summary(sample_word: str, n_samples: int, n_out_of_control: int,
                         cpk: float, cpk_label: str) -> str:
    """Analiz sonrasi otomatik olusturulan kisa metin ozeti (if-else ile,
    formul degil - sadece mevcut sonuclarin duz dile cevrilmesi)."""
    _, level_label, _ = get_cpk_level(cpk)
    oos_text = (
        "kontrol disi nokta yok" if n_out_of_control == 0
        else f"{n_out_of_control} kontrol disi nokta var"
    )
    level_text = {
        "Excellent": "surec mukemmel yeterli",
        "Capable": "surec yeterli",
        "Marginal": "surec marjinal yeterli",
        "Not Capable": "surec yeterli degil",
    }[level_label]
    return (
        f"{n_samples} {sample_word} analiz edildi, {oos_text}, "
        f"{cpk_label}={format_cpk(cpk)} ile {level_text}."
    )


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
