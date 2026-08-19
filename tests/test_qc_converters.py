import math
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from qc_converters import gravimetric_moisture, build_bridge_subgroup_entry


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
