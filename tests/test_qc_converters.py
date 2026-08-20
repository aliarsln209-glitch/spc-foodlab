import math
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from qc_converters import gravimetric_moisture, build_bridge_subgroup_entry, titratable_acidity, salt_content_mohr, thermal_lethality_f0, NACL_MEQ_FACTOR, bridge_value_count_matches, bridge_value_is_single
from constants import TOTOX_BRIDGE_PARAMETER_CONFIG, F0_BRIDGE_PARAMETER_CONFIG, TITRATABLE_ACID_MEQ_FACTORS


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


def test_salt_content_mohr_worked_example():
    # Turetilmis meq faktoru: NaCl (MW=58.44 g/mol, tek degerlikli) ->
    # meq faktoru = 58.44 / 1000 = 0.05844 g/meq
    # V=12.0 mL AgNO3, N=0.1, numune=10.0 g
    # %NaCl = (12.0 * 0.1 * 0.05844 * 100) / 10.0 = 7.0128 / 10.0 = 0.70128
    result = salt_content_mohr(titrant_volume_ml=12.0, titrant_normality=0.1, sample_size_g=10.0)
    assert result["salt_pct"] == pytest.approx(0.70128, abs=0.0001)


def test_salt_content_mohr_zero_sample_raises():
    with pytest.raises(ValueError, match="numune agirligi"):
        salt_content_mohr(titrant_volume_ml=12.0, titrant_normality=0.1, sample_size_g=0.0)


def test_nacl_meq_factor_matches_derivation():
    # IUPAC standart atomik agirliklar: Na=22.990, Cl=35.453
    nacl_mw = 22.990 + 35.453
    assert NACL_MEQ_FACTOR == pytest.approx(nacl_mw / 1000, abs=1e-5)


def test_titratable_acid_meq_factors_match_derivation():
    # IUPAC standart atomik agirliklar (constants.py'deki yorumla ayni)
    C, H, O = 12.011, 1.008, 15.999

    # Sitrik asit (anhidrus, C6H8O7), triprotik
    citric_mw = 6 * C + 8 * H + 7 * O
    assert TITRATABLE_ACID_MEQ_FACTORS["Sitrik Asit (anhidrus)"] == pytest.approx(
        citric_mw / 3 / 1000, abs=0.0001
    )

    # Malik asit (C4H6O5), diprotik
    malic_mw = 4 * C + 6 * H + 5 * O
    assert TITRATABLE_ACID_MEQ_FACTORS["Malik Asit"] == pytest.approx(
        malic_mw / 2 / 1000, abs=0.0001
    )

    # Laktik asit (C3H6O3), monoprotik
    lactic_mw = 3 * C + 6 * H + 3 * O
    assert TITRATABLE_ACID_MEQ_FACTORS["Laktik Asit"] == pytest.approx(
        lactic_mw / 1000, abs=0.0001
    )

    # Asetik asit (C2H4O2), monoprotik
    acetic_mw = 2 * C + 4 * H + 2 * O
    assert TITRATABLE_ACID_MEQ_FACTORS["Asetik Asit"] == pytest.approx(
        acetic_mw / 1000, abs=0.0001
    )


def test_bridge_value_count_matches_exact_n():
    assert bridge_value_count_matches([1.0, 2.0, 3.0, 4.0], required_n=4) is True


def test_bridge_value_count_matches_too_few():
    assert bridge_value_count_matches([1.0, 2.0], required_n=4) is False


def test_bridge_value_count_matches_too_many():
    assert bridge_value_count_matches([1.0, 2.0, 3.0, 4.0, 5.0], required_n=4) is False


def test_bridge_value_count_matches_coerces_non_list():
    # required_n=1 ile tek bir float, 1 elemanli listeye esdeger sayilir
    assert bridge_value_count_matches(12.34, required_n=1) is True
    assert bridge_value_count_matches(12.34, required_n=4) is False


def test_bridge_value_is_single_plain_float():
    assert bridge_value_is_single(12.34) is True


def test_bridge_value_is_single_one_element_list():
    assert bridge_value_is_single([12.34]) is True


def test_bridge_value_is_single_rejects_multi_element_list():
    assert bridge_value_is_single([1.0, 2.0]) is False


def test_thermal_lethality_f0_worked_example():
    # Bigelow/Ball formulu: F0 = dt * sum(10^((T_i - Tref)/z))
    # Tref=121.1, z=10.0 (sabit), dt=1.0 dk, 7 okumali bir come-up/hold/
    # come-down profili: 100.0, 115.0, 121.1, 121.1, 121.1, 115.0, 100.0
    # Elle hesaplama:
    #   100.0 -> 10^((100.0-121.1)/10) = 10^-2.11 = 0.0077624711...
    #   115.0 -> 10^((115.0-121.1)/10) = 10^-0.61  = 0.2454708915...
    #   121.1 -> 10^0 = 1.0 (x3)
    #   Toplam = 0.0077624711 + 0.2454708915 + 1 + 1 + 1 + 0.2454708915 + 0.0077624711
    #          = 3.5064667254...
    #   F0 = 1.0 * 3.5064667254... = 3.5064667254...
    result = thermal_lethality_f0(
        temperatures_c=[100.0, 115.0, 121.1, 121.1, 121.1, 115.0, 100.0],
        delta_t_minutes=1.0,
    )
    assert result["f0_minutes"] == pytest.approx(3.5065, abs=0.001)


def test_thermal_lethality_f0_at_exact_reference_temp():
    # Tum okumalar tam Tref'te ise her terim 10^0=1, toplam=n, F0=dt*n
    result = thermal_lethality_f0(
        temperatures_c=[121.1, 121.1, 121.1, 121.1], delta_t_minutes=0.5,
    )
    assert result["f0_minutes"] == pytest.approx(2.0, abs=0.0001)  # 0.5 * 4


def test_thermal_lethality_f0_empty_temperatures_raises():
    with pytest.raises(ValueError, match="sicaklik okumasi"):
        thermal_lethality_f0(temperatures_c=[], delta_t_minutes=1.0)


def test_thermal_lethality_f0_non_positive_delta_t_raises():
    with pytest.raises(ValueError, match="delta_t"):
        thermal_lethality_f0(temperatures_c=[121.1, 121.1], delta_t_minutes=0.0)


def test_f0_bridge_parameter_config_shape():
    cfg = F0_BRIDGE_PARAMETER_CONFIG
    assert cfg["unit"] == "dakika"
    assert cfg["decimal_places"] == 2
    assert cfg["one_sided"] is True
    assert cfg["is_individual"] is True
    assert cfg["default_lsl"] == 3.0
    assert cfg["category"] == "Proses"
    assert "FDA 21 CFR 113" in cfg["method_source"]
    assert "products" not in cfg  # Altin Kural: tam parametre-registry uyeligi YOK


def test_f0_bridge_parameter_config_not_merged_into_registry():
    from constants import PARAMETER_CONFIG
    assert "F0 (Termal Letalite)" not in PARAMETER_CONFIG
