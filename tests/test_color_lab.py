import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from color_lab import lab_to_hex, append_color_sample, color_samples_to_series


def test_lab_to_hex_black_is_mathematical_identity():
    # L*=0,a*=0,b*=0 CIE Lab->XYZ donusumunde XYZ=(0,0,0)'a esittir -
    # bu bir olcum degil, formulun kendi tanimindan gelen matematiksel
    # ozdeslik (bkz. docstring), bu yuzden ayri bir kaynak dogrulamasi
    # gerektirmez.
    assert lab_to_hex(0.0, 0.0, 0.0) == "#000000"


def test_lab_to_hex_white_is_mathematical_identity():
    # L*=100,a*=0,b*=0 -> D65 referans beyaz noktasinin kendisi -> (255,255,255).
    assert lab_to_hex(100.0, 0.0, 0.0) == "#ffffff"


def test_lab_to_hex_returns_lowercase_six_digit_hex():
    result = lab_to_hex(65.0, 10.0, 20.0)
    assert result.startswith("#")
    assert len(result) == 7
    assert result == result.lower()


def test_append_color_sample_adds_entry_without_mutating_original():
    original = [{"L": 60.0, "a": 5.0, "b": 10.0}]
    result = append_color_sample(original, 61.0, 5.5, 10.5)
    assert len(original) == 1
    assert len(result) == 2
    assert result[1] == {"L": 61.0, "a": 5.5, "b": 10.5}


def test_color_samples_to_series_splits_into_three_lists():
    samples = [
        {"L": 60.0, "a": 5.0, "b": 10.0},
        {"L": 61.0, "a": 5.5, "b": 10.5},
    ]
    l_vals, a_vals, b_vals = color_samples_to_series(samples)
    assert l_vals == [60.0, 61.0]
    assert a_vals == [5.0, 5.5]
    assert b_vals == [10.0, 10.5]


def test_color_samples_to_series_empty_input():
    assert color_samples_to_series([]) == ([], [], [])
