"""
compute_cpk() sifira bolme korumasi testleri.

r_bar (veya I-MR icin mr_bar) tam 0 oldugunda (olculen degerlerde hic
varyasyon yoksa) sigma_hat = r_bar/d2 de 0 olur; normal formul
ZeroDivisionError verirdi. Bu testler, sonucun artik crash yerine
matematiksel olarak anlamli bir deger (sonsuz - surec kusursuz, veya
eksi sonsuz - varyasyon olmasa da ortalama zaten spesifikasyon disinda)
dondurdugunu dogrular.

Bu test dosyasi mevcut test_validation.py ve test_imr_validation.py'dan
bagimsizdir, onlari etkilemez.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from spc_core import compute_cpk


def test_two_sided_zero_variation_within_spec_is_infinite():
    # Tum degerler 7.0, spesifikasyon 6.8-7.2 icinde -> surec kusursuz
    cpk = compute_cpk(x_double_bar=7.0, r_bar=0.0, n=4, lsl=6.8, usl=7.2)
    assert cpk == float("inf")


def test_two_sided_zero_variation_outside_spec_is_negative_infinite():
    # Tum degerler 7.5, spesifikasyon 6.8-7.2 disinda -> varyasyon olmasa da yetersiz
    cpk = compute_cpk(x_double_bar=7.5, r_bar=0.0, n=4, lsl=6.8, usl=7.2)
    assert cpk == float("-inf")


def test_one_sided_zero_variation_within_spec_is_infinite():
    # aw/peroksit gibi tek tarafli: tum degerler USL altinda -> kusursuz
    cpk = compute_cpk(x_double_bar=5.0, r_bar=0.0, n=2, lsl=0.0, usl=20.0, one_sided=True)
    assert cpk == float("inf")


def test_one_sided_zero_variation_outside_spec_is_negative_infinite():
    cpk = compute_cpk(x_double_bar=25.0, r_bar=0.0, n=2, lsl=0.0, usl=20.0, one_sided=True)
    assert cpk == float("-inf")


def test_normal_nonzero_variation_still_works():
    # Regresyon kontrolu: r_bar > 0 oldugunda eski davranis aynen calismali
    cpk = compute_cpk(x_double_bar=7.01, r_bar=0.12, n=4, lsl=6.8, usl=7.2)
    assert 1.08 < cpk < 1.09


if __name__ == "__main__":
    test_two_sided_zero_variation_within_spec_is_infinite()
    test_two_sided_zero_variation_outside_spec_is_negative_infinite()
    test_one_sided_zero_variation_within_spec_is_infinite()
    test_one_sided_zero_variation_outside_spec_is_negative_infinite()
    test_normal_nonzero_variation_still_works()
    print("CPK EDGE CASE TESTLERI GECTI")
