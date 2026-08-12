"""
src/spc_core.py - compute_overall_sigma / compute_ppk / compute_pp testleri.

Dogrulama kaynagi: NIST/SEMATECH e-Handbook of Statistical Methods, Ch. 2
(Process Capability) - Cpk'nin GENEL (s-tabanli, alt gruba OZGU R-bar/d2
tahminine gecmeden ONCE sunulan) formulunun worked example'i:
USL=20, LSL=8, x̄=16, s=2 -> Ĉp=1.0, Ĉpk=0.6667.

Ppk/Pp, matematiksel olarak AYNI formul yapisini (min[(USL-x̄)/(3s),
(x̄-LSL)/(3s)] ve (USL-LSL)/(6s)) TUM ham veriye (alt gruplama olmadan)
uygulamaktan baska bir sey degildir - bkz. spc_core.py compute_ppk/
compute_pp docstring'leri. Bu yuzden NIST'in s=2, x̄=16 ornegini BIREBIR
URETEN bir veri seti (mean=16, ornek std sapmasi N-1 ile TAM 2.0 olacak
sekilde) elle insa edilip ayni USL/LSL ile capraz kontrol edildi.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from spc_core import compute_overall_sigma, compute_pp, compute_ppk

# mean=16, s=2 (N-1) ureten elle insa edilmis veri seti:
# sapmalar: -2, 0, +2 -> kareler: 4, 0, 4 -> varyans = 8/(3-1) = 4 -> s = 2
NIST_LIKE_VALUES = [14.0, 16.0, 18.0]


def test_overall_sigma_matches_hand_built_dataset():
    assert compute_overall_sigma(NIST_LIKE_VALUES) == 2.0


def test_overall_sigma_requires_at_least_two_values():
    assert compute_overall_sigma([16.0]) == 0.0
    assert compute_overall_sigma([]) == 0.0


def test_ppk_matches_nist_worked_example():
    # NIST e-Handbook: USL=20, LSL=8, x̄=16, s=2 -> Cpk(genel s-formulu)=0.6667
    ppk = compute_ppk(NIST_LIKE_VALUES, lsl=8.0, usl=20.0)
    assert abs(ppk - 0.6667) < 0.001


def test_pp_matches_nist_worked_example():
    # Ayni veriyle Cp(genel s-formulu) = (20-8)/(6*2) = 1.0
    pp = compute_pp(NIST_LIKE_VALUES, lsl=8.0, usl=20.0)
    assert abs(pp - 1.0) < 1e-9


def test_ppk_one_sided_returns_only_upper_side():
    # one_sided=True -> sadece Ppu = (USL - x̄)/(3s) = (20-16)/(3*2) = 0.6667
    ppk = compute_ppk(NIST_LIKE_VALUES, lsl=8.0, usl=20.0, one_sided=True)
    assert abs(ppk - 0.6667) < 0.001


def test_ppk_zero_variation_in_spec_is_infinite():
    # Varyasyon yok (tum degerler ayni) ve ortalama spec icinde -> +inf
    ppk = compute_ppk([10.0, 10.0, 10.0], lsl=8.0, usl=20.0)
    assert ppk == float("inf")


def test_ppk_zero_variation_out_of_spec_is_negative_infinite():
    # Varyasyon yok ama ortalama zaten spec disinda -> -inf
    ppk = compute_ppk([25.0, 25.0, 25.0], lsl=8.0, usl=20.0)
    assert ppk == float("-inf")


def test_pp_zero_variation_returns_infinite():
    pp = compute_pp([10.0, 10.0, 10.0], lsl=8.0, usl=20.0)
    assert pp == float("inf")


def test_ppk_can_differ_from_naive_expectation_when_data_has_a_shift():
    # Ppk, alt gruplama olmadan TUM veriye bakar - bir "sicrama" iceren
    # veri setinde, sicramanin genel varyansi buyutmesi Ppk'yi DUSURMELIDIR
    # (Cpk'nin alt-grup-ici tahmininin BUNU KACIRABILECEGI senaryonun temel
    # mantigi budur).
    stable = [15.9, 16.0, 16.1, 15.9, 16.0, 16.1]
    shifted = [15.9, 16.0, 16.1, 19.9, 20.0, 20.1]  # son 3 deger sicramis
    ppk_stable = compute_ppk(stable, lsl=8.0, usl=20.0)
    ppk_shifted = compute_ppk(shifted, lsl=8.0, usl=20.0)
    assert ppk_shifted < ppk_stable


if __name__ == "__main__":
    test_overall_sigma_matches_hand_built_dataset()
    test_overall_sigma_requires_at_least_two_values()
    test_ppk_matches_nist_worked_example()
    test_pp_matches_nist_worked_example()
    test_ppk_one_sided_returns_only_upper_side()
    test_ppk_zero_variation_in_spec_is_infinite()
    test_ppk_zero_variation_out_of_spec_is_negative_infinite()
    test_pp_zero_variation_returns_infinite()
    test_ppk_can_differ_from_naive_expectation_when_data_has_a_shift()
    print("PPK TESTLERI GECTI")
