"""
src/normality.py testleri.

Dogrulama kaynagi: scipy'nin KENDI resmi dokumantasyon ornegi
(https://docs.scipy.org/doc/scipy/tutorial/stats/hypothesis_shapiro.html) -
yetiskin erkek agirliklari veri seti. Burada dogrulanan sey KENDI
formulumuz DEGIL (Shapiro-Wilk algoritmasini yeniden implemente etmiyoruz)
- check_normality()'nin scipy.stats.shapiro'yu DOGRU CAGIRDIGINI ve
sonuclari DOGRU DONDURDUGUNU kanitlar.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest

from normality import check_normality, interpret_normality

# scipy resmi dokumantasyon ornegi: yetiskin erkek agirliklari
SCIPY_DOC_EXAMPLE_VALUES = [148, 154, 158, 160, 161, 162, 166, 170, 182, 195, 236]
SCIPY_DOC_EXPECTED_W = 0.7888146948353875
SCIPY_DOC_EXPECTED_P = 0.006703814056502984


def test_check_normality_matches_scipy_doc_example():
    w, p = check_normality(SCIPY_DOC_EXAMPLE_VALUES)
    assert abs(w - SCIPY_DOC_EXPECTED_W) < 1e-9
    assert abs(p - SCIPY_DOC_EXPECTED_P) < 1e-9


def test_check_normality_raises_for_fewer_than_three_values():
    with pytest.raises(ValueError):
        check_normality([1.0, 2.0])


def test_check_normality_accepts_exactly_three_values():
    # Crash ETMEMELI - MIN_SAMPLE_SIZE_FOR_SHAPIRO=3 sinirinda
    w, p = check_normality([1.0, 2.0, 3.0])
    assert 0.0 <= w <= 1.0
    assert 0.0 <= p <= 1.0


def test_interpret_normality_info_when_p_above_alpha():
    # scipy'nin ideal-normal ornegine yakin bir W/p ciftiyle - p>0.05
    message, level = interpret_normality(w=0.98, p=0.80)
    assert level == "info"
    assert "anlamli bir sapma tespit edilmedi" in message
    assert "W=0.9800" in message
    assert "p=0.8000" in message


def test_interpret_normality_warning_when_p_at_or_below_alpha():
    # scipy dokumantasyon orneginin GERCEK W/p degerleriyle - p<0.05
    message, level = interpret_normality(w=SCIPY_DOC_EXPECTED_W, p=SCIPY_DOC_EXPECTED_P)
    assert level == "warning"
    assert "ANLAMLI SEKILDE sapiyor" in message


def test_interpret_normality_boundary_p_equals_alpha_is_warning():
    # p == alpha (tam sinirda) -> "p > alpha" YANLIS, dolayisiyla warning
    # (H0 REDDEDILIR kabul edilir - >= alpha degil, > alpha REDDETMEME siniri)
    message, level = interpret_normality(w=0.9, p=0.05, alpha=0.05)
    assert level == "warning"


def test_interpret_normality_respects_custom_alpha():
    message, level = interpret_normality(w=0.9, p=0.03, alpha=0.01)
    assert level == "info"  # p=0.03 > alpha=0.01 -> reddedilemez


if __name__ == "__main__":
    test_check_normality_matches_scipy_doc_example()
    test_check_normality_raises_for_fewer_than_three_values()
    test_check_normality_accepts_exactly_three_values()
    test_interpret_normality_info_when_p_above_alpha()
    test_interpret_normality_warning_when_p_at_or_below_alpha()
    test_interpret_normality_boundary_p_equals_alpha_is_warning()
    test_interpret_normality_respects_custom_alpha()
    print("NORMALITY TESTLERI GECTI")
