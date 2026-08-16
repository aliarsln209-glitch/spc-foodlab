"""
microbiology.py birim testleri + validation/microbiology_reference.csv'ye
karsi entegrasyon testi (I-MR/Cpk zincirinin log10-CFU verisiyle uctan
uca dogru calistigini kanitlar).

Kaynak/konvensiyon: ICMSF/FDA BAM LOD/2 ikame kurali. Referans degerler
elle hesaplanip validation/README.md'deki disiplinle CSV'ye yazildi (bkz.
validation/microbiology_reference.csv notlar sutunu - her satir adim adim
elle capraz kontrol edilebilir).
"""

import math
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pandas as pd

from constants import PARAMETER_CONFIG
from microbiology import build_subgroup_entry, substitute_below_lod, to_log10
from spc_core import compute_cpk, compute_moving_ranges

VALIDATION_DIR = os.path.join(os.path.dirname(__file__), "..", "validation")
TOLERANCE = 0.001


# --- substitute_below_lod ---

def test_substitute_below_lod_uses_raw_when_not_below():
    assert substitute_below_lod(raw=120.0, is_below_lod=False, lod=10.0) == 120.0


def test_substitute_below_lod_uses_lod_half_when_below():
    assert substitute_below_lod(raw=None, is_below_lod=True, lod=10.0) == 5.0


def test_substitute_below_lod_raises_without_lod_when_below():
    with pytest.raises(ValueError):
        substitute_below_lod(raw=None, is_below_lod=True, lod=None)


def test_substitute_below_lod_raises_on_zero_lod():
    with pytest.raises(ValueError):
        substitute_below_lod(raw=None, is_below_lod=True, lod=0.0)


def test_substitute_below_lod_raises_without_raw_when_not_below():
    with pytest.raises(ValueError):
        substitute_below_lod(raw=None, is_below_lod=False, lod=10.0)


def test_substitute_below_lod_boundary_raw_equals_lod():
    # raw == lod (LOD-uzerinde ama sinirda) - is_below_lod=False oldugu surece ham deger aynen kullanilir
    assert substitute_below_lod(raw=10.0, is_below_lod=False, lod=10.0) == 10.0


def test_substitute_below_lod_boundary_raw_equals_lod_half():
    # raw == lod/2 - kullanicinin LOD-alti checkbox'i isaretleMEdigi bir sinir durum,
    # ikame mantigina girmez, ham deger aynen kullanilir
    assert substitute_below_lod(raw=5.0, is_below_lod=False, lod=10.0) == 5.0


# --- to_log10 ---

def test_to_log10_basic():
    assert abs(to_log10(100.0) - 2.0) <= 1e-9


def test_to_log10_raises_on_zero():
    with pytest.raises(ValueError):
        to_log10(0.0)


def test_to_log10_raises_on_negative():
    with pytest.raises(ValueError):
        to_log10(-5.0)


def test_to_log10_allows_negative_result_for_small_value():
    # 0 < value < 1 -> log10 NEGATIF ama matematiksel olarak GECERLI (hata degil).
    # Kucuk LOD'larda (orn. LOD=1) LOD/2=0.5 ikamesi tam olarak bu durumu
    # dogurur - grafikte/PDF'de negatif log-KOB degeri sasirtici gorunse de
    # istatistiksel olarak dogrudur, bu yuzden reddedilMEmelidir.
    assert to_log10(0.5) == pytest.approx(-0.30103, abs=1e-5)


# --- build_subgroup_entry ---

def test_build_subgroup_entry_above_lod():
    entry = build_subgroup_entry(raw=120.0, is_below_lod=False, lod=10.0)
    assert entry["raw"] == 120.0
    assert entry["is_below_lod"] is False
    assert entry["lod"] == 10.0
    assert abs(entry["log_value"] - math.log10(120.0)) <= 1e-9


def test_build_subgroup_entry_below_lod():
    entry = build_subgroup_entry(raw=None, is_below_lod=True, lod=10.0)
    assert entry["raw"] is None
    assert entry["is_below_lod"] is True
    assert abs(entry["log_value"] - math.log10(5.0)) <= 1e-9


def test_build_subgroup_entry_below_lod_with_small_lod_yields_negative_log():
    # LOD=1 -> ikame=0.5 -> log10(0.5) negatif. build_subgroup_entry bunu
    # HATA olarak degil, gecerli (ama UI'da dikkat cekilmesi gereken) bir
    # sonuc olarak uretmeli - to_log10'un negatif-ama-gecerli davranisiyla
    # tutarli olmasi gerekir.
    entry = build_subgroup_entry(raw=None, is_below_lod=True, lod=1.0)
    assert entry["log_value"] == pytest.approx(-0.30103, abs=1e-5)


def test_build_subgroup_entry_raises_when_below_lod_missing_lod():
    with pytest.raises(ValueError):
        build_subgroup_entry(raw=None, is_below_lod=True, lod=None)


# --- validation/microbiology_reference.csv entegrasyon testi ---

def _load(filename: str) -> pd.DataFrame:
    return pd.read_csv(os.path.join(VALIDATION_DIR, filename))


def test_microbiology_reference_csv_matches_pipeline():
    df = _load("microbiology_reference.csv")
    assert len(df) >= 1, "microbiology_reference.csv bos olmamali"

    for _, row in df.iterrows():
        lod = float(row["lod"])
        raw_tokens = str(row["raw_values"]).split(";")
        log_values = []
        for token in raw_tokens:
            token = token.strip()
            if token == "LOD":
                entry = build_subgroup_entry(raw=None, is_below_lod=True, lod=lod)
            else:
                entry = build_subgroup_entry(raw=float(token), is_below_lod=False, lod=lod)
            log_values.append(entry["log_value"])

        log_mean = sum(log_values) / len(log_values)
        assert abs(log_mean - float(row["expected_log_mean"])) <= row["tolerance"], (
            f"[{row['source']}] log10-ortalama uyusmuyor: hesaplanan={log_mean}, "
            f"beklenen={row['expected_log_mean']}"
        )

        mrs = compute_moving_ranges(log_values)
        mr_bar = sum(mrs) / len(mrs)
        assert abs(mr_bar - float(row["expected_mr_bar"])) <= row["tolerance"], (
            f"[{row['source']}] mr_bar uyusmuyor: hesaplanan={mr_bar}, "
            f"beklenen={row['expected_mr_bar']}"
        )

        usl_log = to_log10(float(row["usl"]))  # spesifikasyon ham KOB/g olarak girilir, Cpk oncesi log10'a cevrilir
        one_sided = bool(row["one_sided"])
        cpk = compute_cpk(
            x_double_bar=log_mean, r_bar=mr_bar, n=2, lsl=0.0, usl=usl_log, one_sided=one_sided,
        )
        assert abs(cpk - float(row["expected_cpk"])) <= row["tolerance"], (
            f"[{row['source']}] Cpk uyusmuyor: hesaplanan={cpk}, beklenen={row['expected_cpk']}"
        )


# --- PARAMETER_CONFIG smoke test (v1.3 - 5 mikrobiyoloji parametresi) ------

MICROBIO_PARAMS = ["TPC/TMAB", "Kuf-Maya", "Koliform", "Enterobacteriaceae", "Kantitatif S. aureus"]

REQUIRED_MICROBIO_KEYS = {
    "unit": str, "min_value": float, "max_value": float, "decimal_places": int,
    "products": dict, "default_lsl": float, "default_usl": float,
    "default_measurement": float, "demo_target_mean": float, "demo_target_sigma": float,
    "one_sided": bool, "is_individual": bool, "is_microbio": bool,
    "default_lod": float, "log_axis_label": str, "log_decimal_places": int,
}


@pytest.mark.parametrize("param_name", MICROBIO_PARAMS)
def test_microbio_parameter_config_present_and_well_typed(param_name):
    assert param_name in PARAMETER_CONFIG, f"{param_name} PARAMETER_CONFIG'de tanimli degil"
    cfg = PARAMETER_CONFIG[param_name]
    for key, expected_type in REQUIRED_MICROBIO_KEYS.items():
        assert key in cfg, f"{param_name}: '{key}' anahtari eksik"
        assert isinstance(cfg[key], expected_type), (
            f"{param_name}['{key}'] tipi {type(cfg[key])}, beklenen {expected_type}"
        )


@pytest.mark.parametrize("param_name", MICROBIO_PARAMS)
def test_microbio_parameter_is_individual_and_one_sided(param_name):
    # TUM 5 mikrobiyoloji parametresi AYNI mimariyi kullanir: I-MR (alt
    # grup yok) + tek tarafli (sadece USL anlamlidir) - bkz. Kantitatif
    # S. aureus icin bile bu yapinin FARKLI OLMADIGINI dogrulayan not
    # (constants.py PARAMETER_CONFIG).
    cfg = PARAMETER_CONFIG[param_name]
    assert cfg["is_individual"] is True
    assert cfg["one_sided"] is True
    assert cfg["is_microbio"] is True


def test_staph_aureus_has_higher_default_lod_than_others():
    # Bilinen parametreye-ozgu fark: ISO 6888-1 dogrudan yuzey ekimi
    # yontemi digerlerinin dokme plaka yontemine gore daha az duyarli -
    # tipik LOD daha yuksektir (100 vs 10).
    staph_lod = PARAMETER_CONFIG["Kantitatif S. aureus"]["default_lod"]
    for other in ["TPC/TMAB", "Kuf-Maya", "Koliform", "Enterobacteriaceae"]:
        assert staph_lod > PARAMETER_CONFIG[other]["default_lod"]


if __name__ == "__main__":
    test_substitute_below_lod_uses_raw_when_not_below()
    test_substitute_below_lod_uses_lod_half_when_below()
    test_to_log10_basic()
    test_build_subgroup_entry_above_lod()
    test_microbiology_reference_csv_matches_pipeline()
    print("MIKROBIYOLOJI TESTLERI GECTI")
