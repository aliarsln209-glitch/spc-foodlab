"""
result_helpers.py (sonuc rozeti, trend gostergesi, quick summary, demo
senaryosu hedefleri) icin testler.

Bu fonksiyonlar bir istatistiksel formulu DOGRULAMAZ (o testler
test_validation.py / test_imr_validation.py / test_cpk_edge_cases.py'da) -
sadece mevcut Cpk/ornek sonuclarinin dogru siniflandirildigini/metne
cevrildigini ve demo veri hedeflerinin dogru hesaplandigini kontrol eder.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from result_helpers import (
    build_quick_summary,
    compute_trend,
    demo_scenario_targets,
    format_cpk,
    get_cpk_level,
)


# --- format_cpk ---------------------------------------------------------

def test_format_cpk_infinite():
    assert format_cpk(float("inf")) == "∞"
    assert format_cpk(float("-inf")) == "-∞"


def test_format_cpk_normal():
    assert format_cpk(1.30699) == "1.307"


# --- get_cpk_level -------------------------------------------------------

def test_cpk_level_excellent_at_and_above_threshold():
    assert get_cpk_level(1.67)[1] == "Mukemmel"
    assert get_cpk_level(2.5)[1] == "Mukemmel"
    assert get_cpk_level(float("inf"))[1] == "Mukemmel"


def test_cpk_level_capable_band():
    assert get_cpk_level(1.33)[1] == "Yeterli"
    assert get_cpk_level(1.66)[1] == "Yeterli"


def test_cpk_level_marginal_band():
    assert get_cpk_level(1.0)[1] == "Sinirda"
    assert get_cpk_level(1.32)[1] == "Sinirda"


def test_cpk_level_colors_are_outside_the_brand_green_amber_family():
    # v1.1.1 tema paleti marka rengi olarak yesil+amber kullaniyor (bkz.
    # inject_theme_css) - Cpk/istatistiksel sonuc renkleri kullanicinin
    # 'marka rengi mi yoksa sonuc mu iyi' diye karismamasi icin BILINCLI
    # OLARAK farkli bir renk ailesinden (mavi->mor->kirmizi) secildi.
    brand_green_amber_prefixes = ("#15", "#22", "#2f", "#d9", "#f0", "#bb")
    for cpk in (2.5, 1.4, 1.1, 0.5):
        _, _, color = get_cpk_level(cpk)
        assert color.lower().startswith(("#25", "#7c", "#dc")), (
            f"Cpk={cpk} rengi ({color}) beklenen mavi/mor/kirmizi ailesinde degil"
        )
        assert not color.lower().startswith(brand_green_amber_prefixes)


def test_cpk_level_not_capable_band():
    assert get_cpk_level(0.99)[1] == "Yetersiz"
    assert get_cpk_level(float("-inf"))[1] == "Yetersiz"


# --- compute_trend ---------------------------------------------------------

def test_trend_insufficient_data_returns_none():
    assert compute_trend([1.0, 2.0, 3.0]) is None


def test_trend_detects_upward_direction():
    # son yari (5,6,7,8) onceki yariden (1,2,3,4) yuksek
    direction, delta = compute_trend([1, 2, 3, 4, 5, 6, 7, 8], window=4)
    assert direction == "up"
    assert delta > 0


def test_trend_detects_downward_direction():
    direction, delta = compute_trend([8, 7, 6, 5, 4, 3, 2, 1], window=4)
    assert direction == "down"
    assert delta < 0


def test_trend_detects_flat_direction():
    direction, delta = compute_trend([5, 5, 5, 5, 5, 5], window=3)
    assert direction == "flat"
    assert delta == 0


def test_trend_window_capped_at_half_series_length():
    # window=6 istense de sadece 4 nokta var -> w = 4//2 = 2 kullanilir, crash olmamali
    result = compute_trend([1, 2, 3, 4], window=6)
    assert result is not None


# --- build_quick_summary ---------------------------------------------------

def test_quick_summary_mentions_no_oot_or_oos_points():
    text = build_quick_summary("alt grup", 24, 0, 0, 1.5, "Cpk")
    assert "OOT (kontrol disi) nokta yok" in text
    assert "OOS (spesifikasyon disi) nokta yok" in text
    assert "24 alt grup analiz edildi" in text
    assert "Cpk=1.500" in text


def test_quick_summary_mentions_oot_count():
    text = build_quick_summary("olcum", 24, 3, 0, 0.8, "Cpu (tek tarafli)")
    assert "3 OOT (kontrol disi) nokta var" in text
    assert "surec yeterli degil" in text


def test_quick_summary_mentions_oos_count_independently_of_oot():
    # OOT=0 ama OOS=2 - iki sayi BIRBIRINDEN BAGIMSIZ raporlanmali
    text = build_quick_summary("olcum", 24, 0, 2, 1.5, "Cpk")
    assert "OOT (kontrol disi) nokta yok" in text
    assert "2 OOS (spesifikasyon disi) nokta var" in text


# --- demo_scenario_targets --------------------------------------------------

TWO_SIDED_CONFIG = {
    "demo_target_mean": 7.0,
    "demo_target_r_bar": 0.1,
    "demo_shift_amount": 0.35,
    "products": {
        "Yogurt": (4.0, 4.6),
        "Ozel/Manuel gir": None,
    },
}

ONE_SIDED_CONFIG = {
    "demo_target_mean": 10.0,
    "demo_target_sigma": 1.0,
    "products": {
        "Zeytinyagi": (None, 20.0),
        "Ozel/Manuel gir": None,
    },
}


def test_demo_scenario_none_falls_back_to_parameter_defaults():
    mean, spread, shift = demo_scenario_targets(TWO_SIDED_CONFIG, None)
    assert mean == TWO_SIDED_CONFIG["demo_target_mean"]
    assert spread == TWO_SIDED_CONFIG["demo_target_r_bar"]
    assert shift == TWO_SIDED_CONFIG["demo_shift_amount"]


def test_demo_scenario_two_sided_product_centers_on_midpoint():
    mean, spread, shift = demo_scenario_targets(TWO_SIDED_CONFIG, "Yogurt")
    assert mean == 4.3  # (4.0 + 4.6) / 2
    assert spread > 0
    assert shift == spread * 3


def test_demo_scenario_one_sided_product_centers_below_usl():
    mean, spread, shift = demo_scenario_targets(ONE_SIDED_CONFIG, "Zeytinyagi")
    assert mean < 20.0
    assert spread > 0


def test_demo_scenario_individual_param_shift_defaults_to_three_sigma():
    # demo_shift_amount tanimli degil (I-MR parametresi) -> spread*3 kullanilir
    mean, spread, shift = demo_scenario_targets(ONE_SIDED_CONFIG, None)
    assert mean == ONE_SIDED_CONFIG["demo_target_mean"]
    assert spread == ONE_SIDED_CONFIG["demo_target_sigma"]
    assert shift == spread * 3


if __name__ == "__main__":
    test_format_cpk_infinite()
    test_format_cpk_normal()
    test_cpk_level_excellent_at_and_above_threshold()
    test_cpk_level_capable_band()
    test_cpk_level_marginal_band()
    test_cpk_level_not_capable_band()
    test_cpk_level_colors_are_outside_the_brand_green_amber_family()
    test_trend_insufficient_data_returns_none()
    test_trend_detects_upward_direction()
    test_trend_detects_downward_direction()
    test_trend_detects_flat_direction()
    test_trend_window_capped_at_half_series_length()
    test_quick_summary_mentions_no_oot_or_oos_points()
    test_quick_summary_mentions_oot_count()
    test_quick_summary_mentions_oos_count_independently_of_oot()
    test_demo_scenario_none_falls_back_to_parameter_defaults()
    test_demo_scenario_two_sided_product_centers_on_midpoint()
    test_demo_scenario_one_sided_product_centers_below_usl()
    test_demo_scenario_individual_param_shift_defaults_to_three_sigma()
    print("RESULT HELPER TESTLERI GECTI")
