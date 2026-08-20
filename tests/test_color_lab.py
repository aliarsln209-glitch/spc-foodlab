import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from color_lab import lab_to_hex


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
