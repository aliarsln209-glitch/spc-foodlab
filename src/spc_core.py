"""
X-bar/R ve I-MR kontrol grafiği ve Cpk hesaplama çekirdeği.

Kaynak (A2/D3/D4/d2 sabit tablosu ve formüller):
Montgomery, D.C., "Introduction to Statistical Quality Control" — standart SPC sabit tablosu.
Formüllerin çalıştığı örnek: LibreTexts Engineering, Chemical Process Dynamics and
Controls (Woolf), 13.2: SPC - Basic Control Charts (pH X-bar/R örneği, n=4).
Cpk formülü kaynağı: NIST/SEMATECH e-Handbook of Statistical Methods, Ch. 2 (Cpk).

I-MR (Individual-Moving Range) formülleri ve sabitleri de ayni Montgomery
kaynagindandir; dogrulama ornegi 6Sigma Toolkit I-MR Chart ornegi (kahve
sicakligi verisi) - bkz. tests/test_imr_validation.py.

NOT: subgroup_size (n), sidebar'dan kullanıcı tarafından seçilebilir
(varsayılan n=4, aralık n=2..10 — bkz. constants.py MIN/MAX_SUBGROUP_SIZE).
Alt sınır n=2'dir: n=1'de range her zaman 0 olacağından X-bar/R anlamsızdır
(bu durum için ayrı bir chart türü olan I-MR kullanılır). Üst sınır, aşağıdaki
CONTROL_CHART_CONSTANTS tablosunun kapsadığı n=10'dur.
"""

from dataclasses import dataclass

# n -> (A2, D3, D4, d2), Montgomery standart SPC sabit tablosu
CONTROL_CHART_CONSTANTS = {
    2: (1.880, 0.0, 3.267, 1.128),
    3: (1.023, 0.0, 2.574, 1.693),
    4: (0.729, 0.0, 2.282, 2.059),
    5: (0.577, 0.0, 2.114, 2.326),
    6: (0.483, 0.0, 2.004, 2.534),
    7: (0.419, 0.076, 1.924, 2.704),
    8: (0.373, 0.136, 1.864, 2.847),
    9: (0.337, 0.184, 1.816, 2.970),
    10: (0.308, 0.223, 1.777, 3.078),
}


@dataclass
class XbarRLimits:
    x_double_bar: float
    r_bar: float
    a2: float
    d3: float
    d4: float
    d2: float
    ucl_x: float
    lcl_x: float
    ucl_r: float
    lcl_r: float


def get_constants(n: int) -> tuple[float, float, float, float]:
    if n not in CONTROL_CHART_CONSTANTS:
        raise ValueError(
            f"n={n} icin sabit tanimli degil. Desteklenen n: {sorted(CONTROL_CHART_CONSTANTS)}"
        )
    return CONTROL_CHART_CONSTANTS[n]


def compute_xbar_r_limits(x_double_bar: float, r_bar: float, n: int) -> XbarRLimits:
    """X-bar ve R kontrol grafiği limitlerini hesaplar.

    UCL_x = x_double_bar + A2 * r_bar
    LCL_x = x_double_bar - A2 * r_bar
    UCL_r = D4 * r_bar
    LCL_r = D3 * r_bar
    """
    a2, d3, d4, d2 = get_constants(n)
    ucl_x = x_double_bar + a2 * r_bar
    lcl_x = x_double_bar - a2 * r_bar
    ucl_r = d4 * r_bar
    lcl_r = d3 * r_bar
    return XbarRLimits(
        x_double_bar=x_double_bar,
        r_bar=r_bar,
        a2=a2,
        d3=d3,
        d4=d4,
        d2=d2,
        ucl_x=ucl_x,
        lcl_x=lcl_x,
        ucl_r=ucl_r,
        lcl_r=lcl_r,
    )


def is_spec_valid(one_sided: bool, lsl: float, usl: float) -> bool:
    """Bir Cpk/Cpu hesabinin ANLAMLI olup olmadigini kontrol eder - compute_cpk()
    matematiksel olarak LSL >= USL icin de bir sayi doner (orn. -6.998), ama bu
    sayi anlamsizdir (alt limit ust limitten buyukse spesifikasyonun kendisi
    gecersizdir). Cagiran kod, spec_valid=False oldugunda Cpk/Cpu'yu HESAPLAMAMALI
    veya en azindan GOSTERMEMELIDIR - bkz. app.py'deki 'spec_valid' kullanimi
    (KPI karti, hesaplama adimlari, PDF export vb. gecersizken gizlenir/placeholder
    gosterir). Tek tarafli (one_sided=True) parametrelerde LSL yok sayildigi icin
    bu kontrol uygulanmaz - USL tek basina her zaman gecerlidir."""
    return one_sided or lsl < usl


def compute_cpk(
    x_double_bar: float, r_bar: float, n: int, lsl: float, usl: float, one_sided: bool = False
) -> float:
    """Cpk = min[(USL - x_double_bar) / (3*sigma_hat), (x_double_bar - LSL) / (3*sigma_hat)]

    sigma_hat = r_bar / d2  (subgroup-ici kisa vadeli varyasyon tahmini)

    one_sided=True ise sadece Cpu = (USL - x_double_bar) / (3*sigma_hat) dondurulur,
    LSL yok sayilir. Bu, aw (su aktivitesi) gibi sadece ust limitin anlamli oldugu
    parametreler icin kullanilir (alt limit tanimsizdir - mikrobiyal guvenlik acisindan
    sadece "asagida kal" onemlidir, "yukarida kal" degil).

    Sifira bolme korumasi: r_bar (veya I-MR icin mr_bar) tam 0 ise (olculen
    degerlerde hic varyasyon yoksa, orn. Peroksit/HMF'de ardisik olcumler
    birebir ayniysa) sigma_hat = r_bar/d2 de 0 olur ve normal formul
    ZeroDivisionError verir. Bu matematiksel olarak "surec kusursuz, hicbir
    varyasyon yok" anlamina gelir - pratikte Cpk/Cpu sonsuz (surec ne kadar
    dar olursa olsun sinirlar icinde kalir) sayilir, TABII x_double_bar zaten
    spesifikasyon disindaysa (varyasyon olmasa bile) surec yeterli DEGILDIR.
    """
    _, _, _, d2 = get_constants(n)
    sigma_hat = r_bar / d2

    if sigma_hat == 0:
        if one_sided:
            return float("inf") if x_double_bar <= usl else float("-inf")
        return float("inf") if lsl <= x_double_bar <= usl else float("-inf")

    cpu = (usl - x_double_bar) / (3 * sigma_hat)
    if one_sided:
        return cpu
    cpl = (x_double_bar - lsl) / (3 * sigma_hat)
    return min(cpu, cpl)


# I-MR (Individual-Moving Range) chart sabitleri - n=2 icin standart Montgomery
# sabitleriyle tutarlidir (bkz. CONTROL_CHART_CONSTANTS[2] = D4=3.267, d2=1.128),
# ancak I chart'in merkez-cizgi sabiti (2.66) X-bar/R'nin A2'sinden (n=2 icin 1.880)
# FARKLIDIR: A2, alt grup ORTALAMALARININ varyasyonuna gore turetilir; I-MR'de
# alt grup yoktur, tek tek olculen degerlerin kendisi noktadir - bu yuzden ayri,
# I-MR'ye ozgu bir sabit kullanilir (3/d2 ≈ 2.6596, pratikte 2.66 olarak yuvarlanir).
I_CHART_CONSTANT = 2.66
MR_CHART_D4 = 3.267  # CONTROL_CHART_CONSTANTS[2] ile ayni D4
MR_CHART_D2 = 1.128  # CONTROL_CHART_CONSTANTS[2] ile ayni d2 - Cpk icin compute_cpk(n=2) kullanilabilir


@dataclass
class IMRLimits:
    x_bar: float
    mr_bar: float
    ucl_i: float
    lcl_i: float
    ucl_mr: float
    lcl_mr: float


def compute_moving_ranges(values: list[float]) -> list[float]:
    """MR_i = |x_i - x_(i-1)| - ardisik olcumler arasindaki mutlak fark.

    Alt grup kavrami olmayan (I-MR) veriler icin kullanilir; en az 2 deger
    gerektirir, sonuc listesi girdi listesinden 1 eksik uzunluktadir.
    """
    return [abs(values[i] - values[i - 1]) for i in range(1, len(values))]


def compute_imr_limits(x_bar: float, mr_bar: float) -> IMRLimits:
    """I-MR kontrol grafigi limitlerini hesaplar.

    I chart:  UCL/LCL = x_bar ± 2.66 * mr_bar
    MR chart: UCL = 3.267 * mr_bar, LCL = 0

    Dogrulama: 6Sigma Toolkit I-MR ornegi (kahve sicakligi), x_bar=87.2,
    mr_bar=2.889 -> UCL=94.88, LCL=79.52 (bkz. tests/test_imr_validation.py).
    """
    ucl_i = x_bar + I_CHART_CONSTANT * mr_bar
    lcl_i = x_bar - I_CHART_CONSTANT * mr_bar
    ucl_mr = MR_CHART_D4 * mr_bar
    lcl_mr = 0.0
    return IMRLimits(
        x_bar=x_bar,
        mr_bar=mr_bar,
        ucl_i=ucl_i,
        lcl_i=lcl_i,
        ucl_mr=ucl_mr,
        lcl_mr=lcl_mr,
    )
