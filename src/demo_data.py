"""
Demo/simulasyon veri ureteci.

Amac: Streamlit arayuzunu gostermek icin gercekci gorunumlu ama tamamen
kontrollu (rastgele degil, belirlenmis parametrelerle) pH alt grup verisi
uretmek. Gercek kullanici verisiyle karistirilmamali.

Std sapma tahmini: sigma = R_bar / d2  (d2, n=4 icin 2.059 - bkz. spc_core.py
CONTROL_CHART_CONSTANTS, kaynak: Montgomery SPC sabit tablosu).
"""

import numpy as np

from spc_core import get_constants


def generate_demo_subgroups(
    n_subgroups: int = 24,
    subgroup_size: int = 4,
    target_mean: float = 7.01,
    target_r_bar: float = 0.12,
    shift_subgroup_index: int = 18,
    shift_amount: float = 0.35,
    seed: int = 42,
) -> list[list[float]]:
    """target_mean/target_r_bar etrafinda n_subgroups adet alt grup uretir.

    shift_subgroup_index'teki alt grubun ortalamasi bilerek shift_amount kadar
    kaydirilir (UCL disina cikan bir nokta gorebilmek icin).
    """
    _, _, _, d2 = get_constants(subgroup_size)
    sigma = target_r_bar / d2

    rng = np.random.default_rng(seed)
    subgroups = []
    for i in range(n_subgroups):
        mean = target_mean
        if i == shift_subgroup_index:
            mean += shift_amount
        values = rng.normal(loc=mean, scale=sigma, size=subgroup_size)
        subgroups.append([round(float(v), 3) for v in values])

    return subgroups


def generate_demo_individual(
    n_points: int = 24,
    target_mean: float = 50000.0,
    target_sigma: float = 3000.0,
    shift_index: int = 18,
    shift_amount: float | None = None,
    seed: int = 42,
) -> list[float]:
    """I-MR (alt grup olmayan, tek tek olculen) parametreler icin demo veri.

    generate_demo_subgroups()'tan farkli: burada alt grup ortalama/range'i
    yok, dogrudan hedef ortalama etrafinda tek deger serisi uretilir (viskozite
    gibi). shift_amount verilmezse target_sigma'nin 3 kati kullanilir (UCL
    disina belirgin sekilde cikan bir nokta gorebilmek icin).
    """
    if shift_amount is None:
        shift_amount = target_sigma * 3

    rng = np.random.default_rng(seed)
    values = []
    for i in range(n_points):
        mean = target_mean
        if i == shift_index:
            mean += shift_amount
        values.append(round(float(rng.normal(loc=mean, scale=target_sigma)), 3))

    return values


if __name__ == "__main__":
    data = generate_demo_subgroups()
    for i, sg in enumerate(data):
        mean = sum(sg) / len(sg)
        r = max(sg) - min(sg)
        flag = "  <-- kaydirilmis" if i == 18 else ""
        print(f"Grup {i+1:2d}: {sg}  mean={mean:.3f} range={r:.3f}{flag}")
