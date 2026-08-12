"""
src/nelson_rules.py testleri.

Nelson kurallari sayisal bir FORMUL degil, bir oruntu tanima algoritmasidir -
bu yuzden dogrulama, NIST/Montgomery'deki gibi "kaynaktaki sayiyla karsilastir"
seklinde degil, kuralin Nelson (1984) tanimindaki (bkz. nelson_rules.py
docstring'i) mantiga göre ELLE hazirlanmis, sonucu ELLE dogrulanabilir sentetik
veri setleriyle yapilir - ayni rigor, farkli yontem (compute_cpk'nin sifira
bolme edge case'lerinin tests/test_cpk_edge_cases.py'de elle dogrulanmasiyla
ayni yaklasim).
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from nelson_rules import check_rule_2of3_beyond_2sigma, check_rule_4of5_beyond_1sigma


# center=100, sigma=2 -> Zone A siniri: >=104 (ust) veya <=96 (alt)

def test_two_consecutive_points_beyond_2sigma_same_side_triggers():
    # indeks 3 ve 4, ikisi de >=104 (ust Zone A) - ardisik 3'lu pencere (2,3,4) icinde 2 tanesi
    values = [100, 101, 100, 105, 106, 100]
    flagged = check_rule_2of3_beyond_2sigma(values, center=100, sigma=2)
    assert 3 in flagged
    assert 4 in flagged


def test_two_out_of_three_with_one_normal_point_between_triggers():
    # pencere [104, 99, 105] -> ikisi ust Zone A'da, aralarinda normal bir nokta var
    values = [100, 100, 104, 99, 105, 100]
    flagged = check_rule_2of3_beyond_2sigma(values, center=100, sigma=2)
    assert flagged == {2, 4}


def test_opposite_sides_does_not_trigger():
    # biri ust Zone A (+2sigma), biri alt Zone A (-2sigma) - AYNI TARAF sarti saglanmiyor
    values = [100, 104, 96, 100]
    flagged = check_rule_2of3_beyond_2sigma(values, center=100, sigma=2)
    assert flagged == set()


def test_only_one_point_beyond_2sigma_does_not_trigger():
    values = [100, 100, 105, 100, 100]
    flagged = check_rule_2of3_beyond_2sigma(values, center=100, sigma=2)
    assert flagged == set()


def test_exactly_2sigma_boundary_counts_as_beyond():
    # tam olarak center+2*sigma = 104 -> ">=" ile Zone A'ya dahil (sinir dahil)
    values = [100, 104, 104, 100]
    flagged = check_rule_2of3_beyond_2sigma(values, center=100, sigma=2)
    assert flagged == {1, 2}


def test_three_of_three_all_beyond_2sigma_flags_all_three():
    values = [104, 105, 106]
    flagged = check_rule_2of3_beyond_2sigma(values, center=100, sigma=2)
    assert flagged == {0, 1, 2}


def test_zero_sigma_returns_empty_set():
    # varyasyon yok - "2 sigma disi" kavrami tanimsiz, kural anlamsiz
    values = [100, 100, 100, 100]
    flagged = check_rule_2of3_beyond_2sigma(values, center=100, sigma=0)
    assert flagged == set()


def test_fewer_than_three_points_returns_empty_set():
    values = [100, 106]
    flagged = check_rule_2of3_beyond_2sigma(values, center=100, sigma=2)
    assert flagged == set()


def test_overlapping_windows_do_not_duplicate_or_miss_flags():
    # 4 ardisik nokta hepsi ust Zone A'da - birden fazla pencere tetiklenir,
    # sonuc kumesi (set) hepsini bir kez icermeli
    values = [100, 105, 106, 107, 108, 100]
    flagged = check_rule_2of3_beyond_2sigma(values, center=100, sigma=2)
    assert flagged == {1, 2, 3, 4}


# --- check_rule_4of5_beyond_1sigma -----------------------------------------
# center=100, sigma=2 -> Zone C disi siniri: >=102 (ust) veya <=98 (alt)

def test_four_of_five_beyond_1sigma_same_side_triggers():
    values = [100, 103, 104, 99, 105, 106, 100]
    # pencere (indeks 1..5) = [103,104,99,105,106] -> ust: 1,2,4,5 (4 tane) -> tetiklenir
    flagged = check_rule_4of5_beyond_1sigma(values, center=100, sigma=2)
    assert {1, 2, 4, 5}.issubset(flagged)
    assert 3 not in flagged  # 99, Zone C'de (1 sigma icinde) - ihlal degil


def test_normal_point_in_middle_of_window_still_triggers():
    values = [100, 103, 104, 100, 105, 106]
    flagged = check_rule_4of5_beyond_1sigma(values, center=100, sigma=2)
    assert flagged == {1, 2, 4, 5}


def test_opposite_sides_does_not_reach_four_same_side():
    # 5'li pencerede 2 ust (+1sigma), 2 alt (-1sigma), 1 normal - hicbir taraf 4'e ulasmiyor
    values = [103, 104, 100, 97, 96]
    flagged = check_rule_4of5_beyond_1sigma(values, center=100, sigma=2)
    assert flagged == set()


def test_only_three_of_five_does_not_trigger():
    values = [103, 104, 105, 100, 100]
    flagged = check_rule_4of5_beyond_1sigma(values, center=100, sigma=2)
    assert flagged == set()


def test_exactly_1sigma_boundary_counts_as_beyond():
    # tam olarak center+1*sigma = 102 -> ">=" ile siniri gecmis sayilir
    values = [102, 102, 102, 102, 100]
    flagged = check_rule_4of5_beyond_1sigma(values, center=100, sigma=2)
    assert flagged == {0, 1, 2, 3}


def test_all_five_beyond_1sigma_flags_all_five():
    values = [103, 104, 105, 106, 107]
    flagged = check_rule_4of5_beyond_1sigma(values, center=100, sigma=2)
    assert flagged == {0, 1, 2, 3, 4}


def test_zero_sigma_returns_empty_set_4of5():
    values = [100, 100, 100, 100, 100]
    flagged = check_rule_4of5_beyond_1sigma(values, center=100, sigma=0)
    assert flagged == set()


def test_fewer_than_five_points_returns_empty_set():
    values = [103, 104, 105, 106]
    flagged = check_rule_4of5_beyond_1sigma(values, center=100, sigma=2)
    assert flagged == set()


def test_overlapping_windows_do_not_duplicate_or_miss_flags_4of5():
    # 6 ardisik nokta hepsi ust Zone C disinda - birden fazla pencere tetiklenir,
    # sonuc kumesi hepsini bir kez icermeli
    values = [103, 104, 105, 106, 107, 108]
    flagged = check_rule_4of5_beyond_1sigma(values, center=100, sigma=2)
    assert flagged == {0, 1, 2, 3, 4, 5}


if __name__ == "__main__":
    test_two_consecutive_points_beyond_2sigma_same_side_triggers()
    test_two_out_of_three_with_one_normal_point_between_triggers()
    test_opposite_sides_does_not_trigger()
    test_only_one_point_beyond_2sigma_does_not_trigger()
    test_exactly_2sigma_boundary_counts_as_beyond()
    test_three_of_three_all_beyond_2sigma_flags_all_three()
    test_zero_sigma_returns_empty_set()
    test_fewer_than_three_points_returns_empty_set()
    test_overlapping_windows_do_not_duplicate_or_miss_flags()
    test_four_of_five_beyond_1sigma_same_side_triggers()
    test_normal_point_in_middle_of_window_still_triggers()
    test_opposite_sides_does_not_reach_four_same_side()
    test_only_three_of_five_does_not_trigger()
    test_exactly_1sigma_boundary_counts_as_beyond()
    test_all_five_beyond_1sigma_flags_all_five()
    test_zero_sigma_returns_empty_set_4of5()
    test_fewer_than_five_points_returns_empty_set()
    test_overlapping_windows_do_not_duplicate_or_miss_flags_4of5()
    print("NELSON RULES TESTLERI GECTI")
