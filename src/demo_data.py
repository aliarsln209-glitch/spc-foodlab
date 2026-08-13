"""
Demo/simulasyon veri ureteci.

Amac: Streamlit arayuzunu gostermek icin gercekci gorunumlu ama tamamen
kontrollu (rastgele degil, belirlenmis parametrelerle) pH alt grup verisi
uretmek. Gercek kullanici verisiyle karistirilmamali.

Std sapma tahmini: sigma = R_bar / d2  (d2, n=4 icin 2.059 - bkz. spc_core.py
CONTROL_CHART_CONSTANTS, kaynak: Montgomery SPC sabit tablosu).

v1.2 Madde 12 (Demo senaryo galerisi) ile 'pattern' parametresi eklendi -
DEFAULT DEGER ("point_shift") ONCEKI DAVRANISLA BIREBIR AYNIDIR, mevcut
cagiran kodun (urun bazli demo senaryosu, bkz. app.py demo_scenario_targets)
davranisi DEGISMEZ. Yeni pattern'ler SADECE Nelson kurallarini/farkli surec
davranislarini gostermek icin eklenen 'Demo senaryo galerisi' UI'inde
kullanilir:
- "none": duz/iyi surec - hicbir kayma/genisleme yok.
- "point_shift" (varsayilan): TEK bir alt grup ani kayar (mevcut davranis).
- "persistent_shift": bir noktadan itibaren ortalama KALICI olarak kayar
  ("kayan ortalama" senaryosu) - Nelson Test 2'yi (9 ardisik ayni taraf)
  tetiklemek icin tasarlandi.
- "high_variation": R_bar/sigma carpanla genisletilir, ortalama kaymaz -
  "dusuk Cpk" senaryosu (surec ortalanmis ama fazla degisken).
- "trend": ortalama, ilk noktadan son noktaya DOGRUSAL olarak kayar -
  "trend" senaryosu (result_helpers.compute_trend'in yakalamasi icin).
"""

import numpy as np

from spc_core import get_constants


def generate_demo_subgroups(
    n_subgroups: int = 24,
    subgroup_size: int = 4,
    target_mean: float = 7.01,
    target_r_bar: float = 0.12,
    pattern: str = "point_shift",
    shift_subgroup_index: int = 18,
    shift_amount: float = 0.35,
    r_bar_multiplier: float = 2.5,
    trend_total_shift: float | None = None,
    seed: int = 42,
    clip_min: float | None = None,
    clip_max: float | None = None,
) -> list[list[float]]:
    """target_mean/target_r_bar etrafinda n_subgroups adet alt grup uretir.

    pattern="point_shift" (varsayilan, ESKI DAVRANIS): shift_subgroup_index'teki
    TEK alt grubun ortalamasi shift_amount kadar kaydirilir (UCL disina cikan
    bir nokta gorebilmek icin).

    shift_amount parametreye gore olceklenmelidir - sabit bir deger (orn.
    pH icin uygun olan 0.35) her parametrede anlamli olmayabilir. Ornegin
    aw (0-1 arasi, tipik ortalama ~0.85) icin +0.35 kaydirma fiziksel olarak
    IMKANSIZ bir deger (>1) uretir. Cagiran taraf (bkz. constants.py
    PARAMETER_CONFIG["demo_shift_amount"]) parametreye uygun bir deger
    gecirmelidir.

    clip_min/clip_max verilirse (varsayilan None - clip uygulanmaz, eski
    davranis aynen korunur), uretilen degerler bu araliga sikistirilir -
    shift_amount yanlis ayarlansa bile fiziksel olarak imkansiz degerlerin
    (orn. aw > 1) uretilmesine karsi ek bir guvenlik onlemi.
    """
    _, _, _, d2 = get_constants(subgroup_size)
    r_bar = target_r_bar * r_bar_multiplier if pattern == "high_variation" else target_r_bar
    sigma = r_bar / d2
    total_trend = shift_amount if trend_total_shift is None else trend_total_shift

    rng = np.random.default_rng(seed)
    subgroups = []
    for i in range(n_subgroups):
        mean = target_mean
        if pattern == "point_shift" and i == shift_subgroup_index:
            mean += shift_amount
        elif pattern == "persistent_shift" and i >= shift_subgroup_index:
            mean += shift_amount
        elif pattern == "trend" and n_subgroups > 1:
            mean += total_trend * (i / (n_subgroups - 1))
        values = rng.normal(loc=mean, scale=sigma, size=subgroup_size)
        if clip_min is not None or clip_max is not None:
            values = np.clip(values, clip_min, clip_max)
        subgroups.append([round(float(v), 3) for v in values])

    return subgroups


def generate_demo_individual(
    n_points: int = 24,
    target_mean: float = 50000.0,
    target_sigma: float = 3000.0,
    pattern: str = "point_shift",
    shift_index: int = 18,
    shift_amount: float | None = None,
    sigma_multiplier: float = 2.5,
    trend_total_shift: float | None = None,
    seed: int = 42,
) -> list[float]:
    """I-MR (alt grup olmayan, tek tek olculen) parametreler icin demo veri.

    generate_demo_subgroups()'tan farkli: burada alt grup ortalama/range'i
    yok, dogrudan hedef ortalama etrafinda tek deger serisi uretilir (viskozite
    gibi). shift_amount verilmezse target_sigma'nin 3 kati kullanilir (UCL
    disina belirgin sekilde cikan bir nokta gorebilmek icin).

    pattern anlamlari icin bkz. generate_demo_subgroups() docstring'i (ayni
    dort deger burada da gecerlidir - "none"/"point_shift"/"persistent_shift"/
    "high_variation"/"trend"), tek fark r_bar yerine sigma kullanilmasidir.
    """
    if shift_amount is None:
        shift_amount = target_sigma * 3
    sigma = target_sigma * sigma_multiplier if pattern == "high_variation" else target_sigma
    total_trend = shift_amount if trend_total_shift is None else trend_total_shift

    rng = np.random.default_rng(seed)
    values = []
    for i in range(n_points):
        mean = target_mean
        if pattern == "point_shift" and i == shift_index:
            mean += shift_amount
        elif pattern == "persistent_shift" and i >= shift_index:
            mean += shift_amount
        elif pattern == "trend" and n_points > 1:
            mean += total_trend * (i / (n_points - 1))
        values.append(round(float(rng.normal(loc=mean, scale=sigma)), 3))

    return values


if __name__ == "__main__":
    data = generate_demo_subgroups()
    for i, sg in enumerate(data):
        mean = sum(sg) / len(sg)
        r = max(sg) - min(sg)
        flag = "  <-- kaydirilmis" if i == 18 else ""
        print(f"Grup {i+1:2d}: {sg}  mean={mean:.3f} range={r:.3f}{flag}")
