"""
Formul dogrulama testi.

Kaynak: LibreTexts Engineering, Chemical Process Dynamics and Controls (Woolf),
13.2: SPC - Basic Control Charts, pH X-bar/R ornegi.

Kaynaktaki x_double_bar (7.01) ve r_bar (0.12) degerleri 2 ondaliga
yuvarlanmis goruntu degerleridir; kaynagin kendi UCL sonucu (7.0982) tam
hassasiyetli ham veriden hesaplanmis, bu yuzden tam esitlik yerine +/-0.001
tolerans kullaniliyor (kullanicinin onayladigi (a) secenegi).

NOT - LCL degeri kaynakta dogrulanamadi: Kaynaktaki UCL=7.0982 ve LCL=6.9251
degerleri x_double_bar=7.01 etrafinda SIMETRIK degil (UCL ofseti=0.0882,
LCL ofseti=0.0849 - farkli). Formul geregi UCL ve LCL, x_double_bar +/- A2*R_bar
olarak matematiksel olarak simetrik olmak ZORUNDA. Bu yuzden kaynaktaki LCL
rakami muhtemelen bir transkripsiyon/yuvarlama hatasi iceriyor. Karar
(kullanici onayi ile): sadece UCL kaynakla dogrulanir; LCL, formulun
simetrisinden turetilerek (x_double_bar - A2*R_bar) ayrica test edilir.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from spc_core import compute_xbar_r_limits

TOLERANCE = 0.001


def test_ph_example_ucl():
    result = compute_xbar_r_limits(x_double_bar=7.01, r_bar=0.12, n=4)

    expected_ucl = 7.0982

    assert abs(result.ucl_x - expected_ucl) <= TOLERANCE, (
        f"UCL uyusmuyor: hesaplanan={result.ucl_x}, beklenen={expected_ucl}"
    )


def test_lcl_is_symmetric_to_ucl():
    result = compute_xbar_r_limits(x_double_bar=7.01, r_bar=0.12, n=4)

    ucl_offset = result.ucl_x - result.x_double_bar
    lcl_offset = result.x_double_bar - result.lcl_x

    assert abs(ucl_offset - lcl_offset) < 1e-9, (
        "UCL/LCL formul geregi simetrik olmali (ikisi de x_double_bar +/- A2*R_bar)"
    )


if __name__ == "__main__":
    r = compute_xbar_r_limits(x_double_bar=7.01, r_bar=0.12, n=4)
    print(f"A2={r.a2}, D3={r.d3}, D4={r.d4}, d2={r.d2}")
    print(f"Hesaplanan UCL_x = {r.ucl_x:.4f}  (kaynak beklenen: 7.0982)")
    print(f"Hesaplanan LCL_x = {r.lcl_x:.4f}  (kaynak LCL=6.9251 ile DOGRULANAMADI, simetriden turetildi)")
    print(f"Fark UCL: {abs(r.ucl_x - 7.0982):.5f}")
    test_ph_example_ucl()
    test_lcl_is_symmetric_to_ucl()
    print("DOGRULAMA GECTI: UCL kaynakla +/-0.001 icinde eslesiyor, LCL formul simetrisiyle tutarli")
