import math
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from qc_converters import gravimetric_moisture, build_bridge_subgroup_entry, titratable_acidity
from constants import TOTOX_BRIDGE_PARAMETER_CONFIG


def test_gravimetric_moisture_basic_worked_example():
    # AOAC 925.10 gravimetrik nem tayini deseni: dara + yas + kuru agirlik
    # Tare (bos kap) = 25.000 g, Yas (kap+numune) = 30.000 g (net 5.000 g numune)
    # Kuru (kap+kalinti) = 29.400 g (net 4.400 g kuru kalinti)
    # Nem kaybi = 5.000 - 4.400 = 0.600 g -> %Nem = 0.600/5.000*100 = 12.0
    result = gravimetric_moisture(
        dish_tare_g=25.000, wet_with_dish_g=30.000, dry_with_dish_g=29.400
    )
    assert result["wet_sample_g"] == pytest.approx(5.000, abs=0.001)
    assert result["dry_sample_g"] == pytest.approx(4.400, abs=0.001)
    assert result["moisture_pct"] == pytest.approx(12.0, abs=0.01)
    assert result["dry_matter_pct"] == pytest.approx(88.0, abs=0.01)


def test_gravimetric_moisture_zero_wet_sample_raises():
    with pytest.raises(ValueError, match="net yas numune agirligi"):
        gravimetric_moisture(dish_tare_g=25.000, wet_with_dish_g=25.000, dry_with_dish_g=25.000)


def test_gravimetric_moisture_dry_heavier_than_wet_raises():
    # Kuru kalinti net agirligi, yas numune net agirligindan buyuk olamaz
    with pytest.raises(ValueError, match="kuru kalinti"):
        gravimetric_moisture(dish_tare_g=25.000, wet_with_dish_g=30.000, dry_with_dish_g=30.500)


def test_build_bridge_subgroup_entry_shape():
    entry = build_bridge_subgroup_entry(value=12.34, shift_label="QC Donusturucu - Test")
    assert entry == {"shift": "QC Donusturucu - Test", "values": [12.34]}


def test_build_bridge_subgroup_entry_rejects_non_finite_value():
    with pytest.raises(ValueError, match="sonlu"):
        build_bridge_subgroup_entry(value=float("nan"), shift_label="QC Donusturucu - Test")


def test_build_bridge_subgroup_entry_accepts_list_for_xbar_r():
    entry = build_bridge_subgroup_entry(
        value=[1.1, 1.2, 1.0, 1.3], shift_label="QC Donusturucu - Test XR",
    )
    assert entry == {"shift": "QC Donusturucu - Test XR", "values": [1.1, 1.2, 1.0, 1.3]}


def test_build_bridge_subgroup_entry_rejects_empty_list():
    with pytest.raises(ValueError, match="bos olamaz"):
        build_bridge_subgroup_entry(value=[], shift_label="QC Donusturucu - Test XR")


def test_build_bridge_subgroup_entry_rejects_non_finite_value_in_list():
    with pytest.raises(ValueError, match="sonlu"):
        build_bridge_subgroup_entry(
            value=[1.0, float("nan"), 1.2], shift_label="QC Donusturucu - Test XR",
        )


def test_build_bridge_subgroup_entry_single_float_still_works():
    # Faz 1 davranisi degismemeli - regresyon kontrolu
    entry = build_bridge_subgroup_entry(value=12.34, shift_label="QC Donusturucu - Test")
    assert entry == {"shift": "QC Donusturucu - Test", "values": [12.34]}


def test_totox_bridge_parameter_config_shape():
    cfg = TOTOX_BRIDGE_PARAMETER_CONFIG
    assert cfg["unit"] == "meq O2/kg"
    assert cfg["one_sided"] is True
    assert cfg["is_individual"] is True
    assert cfg["default_usl"] == 26.0
    assert cfg["category"] == "Proses"
    assert "products" not in cfg  # Altin Kural: tam parametre-registry uyeligi YOK


def test_titratable_acidity_worked_example_citric_acid():
    # Turetilmis meq faktoru (bkz. constants.TITRATABLE_ACID_MEQ_FACTORS
    # yorum satiri): sitrik asit = 0.0640 g/meq
    # V=9.2 mL, N=0.1, faktor=0.064, numune=10.0 mL
    # %TA = (9.2 * 0.1 * 0.064 * 100) / 10.0 = 5.888 / 10.0 = 0.5888
    result = titratable_acidity(
        titrant_volume_ml=9.2, titrant_normality=0.1, acid_meq_factor=0.064, sample_size_ml=10.0,
    )
    assert result["acidity_pct"] == pytest.approx(0.5888, abs=0.0001)


def test_titratable_acidity_zero_sample_size_raises():
    with pytest.raises(ValueError, match="numune miktari"):
        titratable_acidity(
            titrant_volume_ml=9.2, titrant_normality=0.1, acid_meq_factor=0.064, sample_size_ml=0.0,
        )


def test_titratable_acidity_negative_factor_raises():
    with pytest.raises(ValueError, match="asit faktoru"):
        titratable_acidity(
            titrant_volume_ml=9.2, titrant_normality=0.1, acid_meq_factor=-0.064, sample_size_ml=10.0,
        )
