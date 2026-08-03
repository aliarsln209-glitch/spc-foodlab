"""
I-MR (Individual-Moving Range) formul dogrulama testi.

Kaynak: 6Sigma Toolkit, I-MR Chart ornegi (kahve sicakligi verisi).
Girdi: x_bar=87.2, mr_bar (kaynakta "R-bar" olarak adlandirilmis, aslinda
ortalama moving range) = 2.889, d2=1.128 (n=2 sabiti, I-MR icin standart).
Beklenen: UCL=94.88, LCL=79.52.

Bu test mevcut pH/Brix/Aw dogrulama testinden (test_validation.py) tamamen
bagimsizdir ve onu etkilemez.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from spc_core import compute_imr_limits, compute_moving_ranges

TOLERANCE = 0.01


def test_imr_ucl_lcl_6sigma_example():
    limits = compute_imr_limits(x_bar=87.2, mr_bar=2.889)

    expected_ucl = 94.88
    expected_lcl = 79.52

    assert abs(limits.ucl_i - expected_ucl) <= TOLERANCE, (
        f"UCL uyusmuyor: hesaplanan={limits.ucl_i}, beklenen={expected_ucl}"
    )
    assert abs(limits.lcl_i - expected_lcl) <= TOLERANCE, (
        f"LCL uyusmuyor: hesaplanan={limits.lcl_i}, beklenen={expected_lcl}"
    )


def test_moving_ranges_basic():
    values = [10.0, 12.0, 9.0, 15.0]
    mrs = compute_moving_ranges(values)
    assert mrs == [2.0, 3.0, 6.0]


def test_moving_ranges_length():
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    mrs = compute_moving_ranges(values)
    assert len(mrs) == len(values) - 1


if __name__ == "__main__":
    limits = compute_imr_limits(x_bar=87.2, mr_bar=2.889)
    print(f"Hesaplanan UCL_i = {limits.ucl_i:.4f}  (beklenen: 94.88)")
    print(f"Hesaplanan LCL_i = {limits.lcl_i:.4f}  (beklenen: 79.52)")
    test_imr_ucl_lcl_6sigma_example()
    test_moving_ranges_basic()
    test_moving_ranges_length()
    print("I-MR DOGRULAMA GECTI (tolerans +/-0.01 icinde)")
