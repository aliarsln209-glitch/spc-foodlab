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

from color_lab import lab_to_hex
from qc_converters import salt_content_mohr, thermal_lethality_f0, titratable_acidity
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


def test_physical_yogunluk_refraktif_cpk_reference_csv_matches_formula():
    # v1.5 Faz 2: Yogunluk, Refraktif Indeks (I-MR + Cpk)
    _assert_cpk_csv_matches_formula(
        _load("yogunluk_refraktif_cpk_reference.csv", subdir="physical")
    )


def test_optics_cpk_reference_csv_matches_formula():
    # v1.6 Faz 3: L*, Bulanıklık (I-MR + Cpk/Cpu) - urun spesifikasyonu
    # DEGIL, framework mekanizma testi (bkz. validation/optics/cpk_reference.csv
    # ve constants.py'deki L_STAR/BULANIKLIK_PRODUCT_RANGES notlari - bu 5
    # parametre icin dogrulanmis bir TGK/Codex urun limiti bulunamadi).
    _assert_cpk_csv_matches_formula(_load("cpk_reference.csv", subdir="optics"))


def test_lab_to_hex_reference_csv():
    import csv
    path = os.path.join(
        os.path.dirname(__file__), "..", "validation", "optics", "lab_to_hex_reference.csv"
    )
    with open(path, newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f, ) if not r["l_star"].startswith("#")]
    for row in rows:
        result = lab_to_hex(float(row["l_star"]), float(row["a_star"]), float(row["b_star"]))
        assert result == row["expected_hex"], f"{row}: beklenen {row['expected_hex']}, alinan {result}"


def test_process_cpk_reference_csv_matches_formula():
    # v1.7 Faz 1: QC Donusturucu formulleri icin Method Validation
    _assert_cpk_csv_matches_formula(_load("cpk_reference.csv", subdir="process"))


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


def test_process_titration_reference_csv_matches_formulas():
    df = _load("titration_reference.csv", subdir="process")
    for _, row in df.iterrows():
        if row["formula"] == "titratable_acidity":
            result = titratable_acidity(
                titrant_volume_ml=row["titrant_volume_ml"],
                titrant_normality=row["titrant_normality"],
                acid_meq_factor=row["factor"],
                sample_size_ml=row["sample_size"],
            )
            actual = result["acidity_pct"]
        elif row["formula"] == "salt_content_mohr":
            result = salt_content_mohr(
                titrant_volume_ml=row["titrant_volume_ml"],
                titrant_normality=row["titrant_normality"],
                sample_size_g=row["sample_size"],
            )
            actual = result["salt_pct"]
        else:
            raise AssertionError(f"Bilinmeyen formul: {row['formula']}")

        assert abs(actual - row["expected_pct"]) <= row["tolerance"], (
            f"{row['formula']} uyusmuyor: hesaplanan={actual}, "
            f"beklenen={row['expected_pct']} (kaynak: {row['source']})"
        )


def test_process_thermal_lethality_reference_csv_matches_formula():
    df = _load("thermal_lethality_reference.csv", subdir="process")
    for _, row in df.iterrows():
        temps = [float(t) for t in str(row["temperatures_c"]).split(";")]
        result = thermal_lethality_f0(
            temperatures_c=temps, delta_t_minutes=row["delta_t_minutes"],
        )
        actual = result["f0_minutes"]
        assert abs(actual - row["expected_f0_minutes"]) <= row["tolerance"], (
            f"thermal_lethality_f0 uyusmuyor: hesaplanan={actual}, "
            f"beklenen={row['expected_f0_minutes']} (kaynak: {row['source']})"
        )


if __name__ == "__main__":
    test_xbar_r_reference_csv_matches_formula()
    test_imr_reference_csv_matches_formula()
    test_cpk_reference_csv_matches_formula()
    test_chemistry_cpk_reference_csv_matches_formula()
    test_physical_cpk_reference_csv_matches_formula()
    test_physical_yogunluk_refraktif_cpk_reference_csv_matches_formula()
    test_optics_cpk_reference_csv_matches_formula()
    test_lab_to_hex_reference_csv()
    test_process_cpk_reference_csv_matches_formula()
    test_ppk_reference_csv_matches_formula()
    test_process_titration_reference_csv_matches_formulas()
    test_process_thermal_lethality_reference_csv_matches_formula()
    print("VALIDATION SUITE (CSV-guduml) TESTLERI GECTI")
