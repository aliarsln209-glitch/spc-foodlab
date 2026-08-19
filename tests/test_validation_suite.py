"""
validation/*.csv icindeki referans satirlarini OKUYUP spc_core
fonksiyonlarina karsi calistiran veri-guduml testler.

test_validation.py / test_imr_validation.py / test_cpk_edge_cases.py'daki
hardcoded karsilastirmalarla AYNI degerleri dogrular, ama kaynagi kod
icine gommek yerine validation/ klasorundeki CSV'lerden okur - boylece
yeni bir referans ornegi eklemek (orn. v1.2'de Nelson, v1.3'te
mikrobiyoloji) kod degil veri eklemek anlamina gelir (bkz.
validation/README.md).
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pandas as pd

from spc_core import compute_cpk, compute_imr_limits, compute_pp, compute_ppk, compute_xbar_r_limits

VALIDATION_DIR = os.path.join(os.path.dirname(__file__), "..", "validation")


def _load(filename: str, subdir: str = "shared") -> pd.DataFrame:
    return pd.read_csv(os.path.join(VALIDATION_DIR, subdir, filename))


def test_xbar_r_reference_csv_matches_formula():
    df = _load("xbar_r_reference.csv")
    assert len(df) >= 1, "xbar_r_reference.csv bos olmamali"

    for _, row in df.iterrows():
        result = compute_xbar_r_limits(
            x_double_bar=row["input_x_double_bar"], r_bar=row["input_r_bar"], n=int(row["input_n"])
        )
        assert abs(result.ucl_x - row["expected_ucl"]) <= row["tolerance"], (
            f"[{row['source']}] UCL uyusmuyor: hesaplanan={result.ucl_x}, "
            f"beklenen={row['expected_ucl']}"
        )
        if row["lcl_check"] == "symmetry_only":
            ucl_offset = result.ucl_x - result.x_double_bar
            lcl_offset = result.x_double_bar - result.lcl_x
            assert abs(ucl_offset - lcl_offset) < 1e-9, (
                f"[{row['source']}] UCL/LCL formul geregi simetrik olmali"
            )


def test_imr_reference_csv_matches_formula():
    df = _load("imr_reference.csv")
    assert len(df) >= 1, "imr_reference.csv bos olmamali"

    for _, row in df.iterrows():
        limits = compute_imr_limits(x_bar=row["input_x_bar"], mr_bar=row["input_mr_bar"])
        assert abs(limits.ucl_i - row["expected_ucl"]) <= row["tolerance"], (
            f"[{row['source']}] UCL uyusmuyor: hesaplanan={limits.ucl_i}, "
            f"beklenen={row['expected_ucl']}"
        )
        assert abs(limits.lcl_i - row["expected_lcl"]) <= row["tolerance"], (
            f"[{row['source']}] LCL uyusmuyor: hesaplanan={limits.lcl_i}, "
            f"beklenen={row['expected_lcl']}"
        )


def test_cpk_reference_csv_matches_formula():
    df = _load("cpk_reference.csv")
    assert len(df) >= 1, "cpk_reference.csv bos olmamali"

    for _, row in df.iterrows():
        cpk = compute_cpk(
            x_double_bar=row["x_double_bar"], r_bar=row["r_bar"], n=int(row["n"]),
            lsl=row["lsl"], usl=row["usl"], one_sided=bool(row["one_sided"]),
        )
        expected = float(row["expected_cpk"])  # "inf"/"-inf" stringleri de dogru parse edilir
        if expected in (float("inf"), float("-inf")):
            assert cpk == expected, (
                f"[{row['source']}] Cpk uyusmuyor: hesaplanan={cpk}, beklenen={expected}"
            )
        else:
            assert abs(cpk - expected) <= row["tolerance"], (
                f"[{row['source']}] Cpk uyusmuyor: hesaplanan={cpk}, beklenen={expected}"
            )


def _assert_cpk_csv_matches_formula(df: pd.DataFrame):
    """cpk_reference.csv semasini (source,x_double_bar,r_bar,n,lsl,usl,
    one_sided,expected_cpk,tolerance,notes) okuyup compute_cpk()'ye karsi
    calistirir - validation/shared/cpk_reference.csv icin kullanilan
    test_cpk_reference_csv_matches_formula() ile AYNI mantik, chemistry/
    physical altindaki v1.4 Faz 1 referanslariyla da paylasilir."""
    assert len(df) >= 1
    for _, row in df.iterrows():
        cpk = compute_cpk(
            x_double_bar=row["x_double_bar"], r_bar=row["r_bar"], n=int(row["n"]),
            lsl=row["lsl"], usl=row["usl"], one_sided=bool(row["one_sided"]),
        )
        expected = float(row["expected_cpk"])
        assert abs(cpk - expected) <= row["tolerance"], (
            f"[{row['source']}] Cpk uyusmuyor: hesaplanan={cpk}, beklenen={expected}"
        )


def test_chemistry_cpk_reference_csv_matches_formula():
    # v1.4 Faz 1: Protein/Kul (I-MR + Cpk/Cpu) - bkz. validation/chemistry/README
    # yerine bu dosyanin ustundeki notlar sutunu (ayri bir README henuz yok,
    # tek dosya oldugu icin gereksiz duplikasyon olurdu).
    _assert_cpk_csv_matches_formula(_load("cpk_reference.csv", subdir="chemistry"))


def test_physical_cpk_reference_csv_matches_formula():
    # v1.4 Faz 1: Kuru Madde (I-MR + Cpk)
    _assert_cpk_csv_matches_formula(_load("cpk_reference.csv", subdir="physical"))


def test_ppk_reference_csv_matches_formula():
    df = _load("ppk_reference.csv")
    assert len(df) >= 1, "ppk_reference.csv bos olmamali"

    for _, row in df.iterrows():
        values = [float(v) for v in str(row["values"]).split(";")]
        ppk = compute_ppk(values, lsl=row["lsl"], usl=row["usl"])
        pp = compute_pp(values, lsl=row["lsl"], usl=row["usl"])
        assert abs(ppk - float(row["expected_ppk"])) <= row["tolerance"], (
            f"[{row['source']}] Ppk uyusmuyor: hesaplanan={ppk}, beklenen={row['expected_ppk']}"
        )
        assert abs(pp - float(row["expected_pp"])) <= row["tolerance"], (
            f"[{row['source']}] Pp uyusmuyor: hesaplanan={pp}, beklenen={row['expected_pp']}"
        )


if __name__ == "__main__":
    test_xbar_r_reference_csv_matches_formula()
    test_imr_reference_csv_matches_formula()
    test_cpk_reference_csv_matches_formula()
    test_chemistry_cpk_reference_csv_matches_formula()
    test_physical_cpk_reference_csv_matches_formula()
    test_ppk_reference_csv_matches_formula()
    print("VALIDATION SUITE (CSV-guduml) TESTLERI GECTI")
