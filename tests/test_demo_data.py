"""
demo_data.py (v1.2 Madde 12, Demo senaryo galerisi) icin testler.

Bu bir istatistiksel FORMUL testi degildir (Method Validation kapsaminda
degil) - rastgele veri ureten bir yardimci fonksiyonun DAVRANIS
GARANTILERINI (hangi pattern hangi sekli uretiyor, varsayilan davranis
degismiyor) dogrular.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from demo_data import generate_demo_subgroups, generate_demo_individual


# --- generate_demo_subgroups ------------------------------------------------

def test_default_pattern_is_point_shift_backward_compatible():
    # pattern parametresi ONCESINDE var olan davranis - varsayilan cagrida
    # SADECE index 18'deki grup kaymis olmali, digerleri target_mean civarinda.
    data = generate_demo_subgroups(target_mean=7.0, target_r_bar=0.1, shift_amount=0.35)
    means = [sum(sg) / len(sg) for sg in data]
    assert means[18] > 7.0 + 0.2
    for i in [0, 5, 10, 17, 19, 23]:
        assert abs(means[i] - 7.0) < 0.2


def test_pattern_none_has_no_shift_anywhere():
    data = generate_demo_subgroups(target_mean=7.0, target_r_bar=0.1, pattern="none")
    means = [sum(sg) / len(sg) for sg in data]
    assert all(abs(m - 7.0) < 0.2 for m in means)


def test_pattern_persistent_shift_stays_shifted_after_start():
    data = generate_demo_subgroups(
        target_mean=7.0, target_r_bar=0.1, pattern="persistent_shift",
        shift_subgroup_index=18, shift_amount=0.35,
    )
    means = [sum(sg) / len(sg) for sg in data]
    # kaymadan ONCE normal
    assert abs(means[10] - 7.0) < 0.2
    # kaymadan SONRA (dahil), HEPSI kaymis kalmali - tek nokta degil
    for i in range(18, 24):
        assert means[i] > 7.0 + 0.2


def test_pattern_high_variation_widens_spread_without_shifting_mean():
    baseline = generate_demo_subgroups(target_mean=7.0, target_r_bar=0.1, pattern="none")
    widened = generate_demo_subgroups(
        target_mean=7.0, target_r_bar=0.1, pattern="high_variation", r_bar_multiplier=3.0,
    )
    baseline_spread = sum(max(sg) - min(sg) for sg in baseline) / len(baseline)
    widened_spread = sum(max(sg) - min(sg) for sg in widened) / len(widened)
    assert widened_spread > baseline_spread * 1.5
    # ortalama hala target_mean civarinda - sadece yayilim genisledi
    widened_means = [sum(sg) / len(sg) for sg in widened]
    assert abs(sum(widened_means) / len(widened_means) - 7.0) < 0.2


def test_pattern_trend_increases_linearly_from_first_to_last():
    data = generate_demo_subgroups(
        target_mean=7.0, target_r_bar=0.05, pattern="trend", trend_total_shift=0.6,
    )
    means = [sum(sg) / len(sg) for sg in data]
    assert abs(means[0] - 7.0) < 0.15
    assert abs(means[-1] - 7.6) < 0.15
    assert means[-1] > means[0]


def test_clip_min_max_still_applied_with_new_patterns():
    data = generate_demo_subgroups(
        target_mean=0.95, target_r_bar=0.05, pattern="persistent_shift",
        shift_subgroup_index=10, shift_amount=0.5, clip_min=0.0, clip_max=1.0,
    )
    for sg in data:
        assert all(0.0 <= v <= 1.0 for v in sg)


# --- generate_demo_individual ------------------------------------------------

def test_individual_default_pattern_is_point_shift_backward_compatible():
    data = generate_demo_individual(target_mean=100.0, target_sigma=2.0, shift_amount=10.0)
    assert data[18] > 100.0 + 5.0
    for i in [0, 5, 10, 17, 19, 23]:
        assert abs(data[i] - 100.0) < 5.0


def test_individual_pattern_persistent_shift_stays_shifted():
    data = generate_demo_individual(
        target_mean=100.0, target_sigma=2.0, pattern="persistent_shift",
        shift_index=18, shift_amount=10.0,
    )
    assert abs(data[10] - 100.0) < 5.0
    for i in range(18, 24):
        assert data[i] > 100.0 + 5.0


def test_individual_pattern_high_variation_widens_spread():
    baseline = generate_demo_individual(target_mean=100.0, target_sigma=2.0, pattern="none")
    widened = generate_demo_individual(
        target_mean=100.0, target_sigma=2.0, pattern="high_variation", sigma_multiplier=3.0,
    )
    baseline_range = max(baseline) - min(baseline)
    widened_range = max(widened) - min(widened)
    assert widened_range > baseline_range * 1.5


def test_individual_pattern_trend_increases_from_first_to_last():
    data = generate_demo_individual(
        target_mean=100.0, target_sigma=1.0, pattern="trend", trend_total_shift=20.0,
    )
    assert abs(data[0] - 100.0) < 5.0
    assert abs(data[-1] - 120.0) < 5.0
    assert data[-1] > data[0]


if __name__ == "__main__":
    test_default_pattern_is_point_shift_backward_compatible()
    test_pattern_none_has_no_shift_anywhere()
    test_pattern_persistent_shift_stays_shifted_after_start()
    test_pattern_high_variation_widens_spread_without_shifting_mean()
    test_pattern_trend_increases_linearly_from_first_to_last()
    test_clip_min_max_still_applied_with_new_patterns()
    test_individual_default_pattern_is_point_shift_backward_compatible()
    test_individual_pattern_persistent_shift_stays_shifted()
    test_individual_pattern_high_variation_widens_spread()
    test_individual_pattern_trend_increases_from_first_to_last()
    print("DEMO DATA TESTLERI GECTI")
