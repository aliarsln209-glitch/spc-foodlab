"""
X-bar/R kontrol grafiği ve Cpk hesaplama çekirdeği.

Kaynak (A2/D3/D4/d2 sabit tablosu ve formüller):
Montgomery, D.C., "Introduction to Statistical Quality Control" — standart SPC sabit tablosu.
Formüllerin çalıştığı örnek: LibreTexts Engineering, Chemical Process Dynamics and
Controls (Woolf), 13.2: SPC - Basic Control Charts (pH X-bar/R örneği, n=4).
Cpk formülü kaynağı: NIST/SEMATECH e-Handbook of Statistical Methods, Ch. 2 (Cpk).

NOT: subgroup_size (n) bu projede v1 kapsamında SABİTTİR (bkz. constants.py).
Kullanıcının n'yi değiştirebilmesi MVP'de desteklenmiyor.
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


def compute_cpk(x_double_bar: float, r_bar: float, n: int, lsl: float, usl: float) -> float:
    """Cpk = min[(USL - x_double_bar) / (3*sigma_hat), (x_double_bar - LSL) / (3*sigma_hat)]

    sigma_hat = r_bar / d2  (subgroup-ici kisa vadeli varyasyon tahmini)
    """
    _, _, _, d2 = get_constants(n)
    sigma_hat = r_bar / d2
    cpu = (usl - x_double_bar) / (3 * sigma_hat)
    cpl = (x_double_bar - lsl) / (3 * sigma_hat)
    return min(cpu, cpl)
