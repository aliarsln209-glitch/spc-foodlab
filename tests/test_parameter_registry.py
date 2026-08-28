import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from parameter_registry import (
    custom_parameter_to_config_entry,
    merge_parameter_config,
    merge_parameter_categories,
    CUSTOM_CATEGORY_ID,
    CUSTOM_CATEGORY_LABEL,
)


def _row(**overrides):
    row = dict(
        id=1, name="Ekstraksiyon Verimi", unit="%", chart_type="I-MR",
        subgroup_size=None, data_type="continuous", lsl=None, usl=85.0,
        has_specification=1, one_sided=1, log_scale=0, decimal_places=2,
        min_value=None, max_value=None, created_at="2026-08-27T10:00:00",
    )
    row.update(overrides)
    return row


def test_custom_parameter_to_config_entry_one_sided_usl_only():
    entry = custom_parameter_to_config_entry(_row())
    assert entry["unit"] == "%"
    assert entry["is_individual"] is True
    assert entry["one_sided"] is True
    assert entry["default_usl"] == 85.0
    assert entry["default_lsl"] == 0.0
    assert entry["has_specification"] is True
    assert entry["is_custom"] is True
    assert entry["products"] == {"Ozel/Manuel gir": None}
    assert entry["category"] == CUSTOM_CATEGORY_LABEL
    assert entry["custom_parameter_id"] == 1
    assert entry["default_measurement"] == 0.0


def test_custom_parameter_to_config_entry_no_specification():
    entry = custom_parameter_to_config_entry(
        _row(has_specification=0, one_sided=0, lsl=None, usl=None)
    )
    assert entry["has_specification"] is False
    assert entry["default_lsl"] == 0.0
    assert entry["default_usl"] == 0.0


def test_custom_parameter_to_config_entry_xbar_r_carries_subgroup_size():
    entry = custom_parameter_to_config_entry(
        _row(chart_type="Xbar-R", subgroup_size=4, is_individual=False)
    )
    assert entry["is_individual"] is False
    assert entry["custom_subgroup_size"] == 4


def test_custom_parameter_to_config_entry_count_forces_zero_decimals():
    entry = custom_parameter_to_config_entry(_row(data_type="count", decimal_places=2))
    assert entry["decimal_places"] == 0


def test_custom_parameter_to_config_entry_carries_min_max_and_log_scale():
    entry = custom_parameter_to_config_entry(
        _row(min_value=0.0, max_value=100.0, log_scale=1)
    )
    assert entry["min_value"] == 0.0
    assert entry["max_value"] == 100.0
    assert entry["log_scale"] is True


def test_merge_parameter_config_does_not_mutate_builtin():
    builtin = {"pH": {"unit": "-", "min_value": 0.0}}
    merged = merge_parameter_config(builtin, [_row()])
    assert "Ekstraksiyon Verimi" in merged
    assert "Ekstraksiyon Verimi" not in builtin
    assert merged["pH"] == builtin["pH"]
    # Verify nested dicts are separate objects (deep copy, not shallow copy)
    assert merged["pH"] is not builtin["pH"]
    # Mutate a nested value in the merged dict
    merged["pH"]["min_value"] = 999
    # Verify the original builtin is unchanged (would fail with shallow copy)
    assert builtin["pH"]["min_value"] == 0.0


def test_merge_parameter_config_empty_custom_rows_returns_copy():
    builtin = {"pH": {"unit": "-", "min_value": 0.0}}
    merged = merge_parameter_config(builtin, [])
    assert merged == builtin
    assert merged is not builtin
    # Verify nested dicts are also separate (deep copy, not shallow copy)
    assert merged["pH"] is not builtin["pH"]
    # Mutate a nested value in the merged dict
    merged["pH"]["min_value"] = 999
    # Verify the original builtin is unchanged (would fail with shallow copy)
    assert builtin["pH"]["min_value"] == 0.0


def test_merge_parameter_categories_adds_custom_category_when_rows_exist():
    builtin_categories = [("fiziksel", "Fiziksel", ["pH"])]
    merged = merge_parameter_categories(builtin_categories, [_row()])
    assert merged[0] == builtin_categories[0]
    assert merged[-1] == (CUSTOM_CATEGORY_ID, CUSTOM_CATEGORY_LABEL, ["Ekstraksiyon Verimi"])


def test_merge_parameter_categories_no_custom_category_when_no_rows():
    builtin_categories = [("fiziksel", "Fiziksel", ["pH"])]
    merged = merge_parameter_categories(builtin_categories, [])
    assert merged == builtin_categories


# --- Fix 9: regresyon koruyucusu -------------------------------------------
#
# Fix 1 (default_measurement) ve Fix 2 (products) bulgulari, custom_parameter_
# to_config_entry()'nin urettigi sozlukte app.py'nin KOSULSUZ olarak
# param_config["..."] ile okudugu bir anahtarin EKSIK olmasindan kaynaklandi.
# Var olan testler (yukaridaki gibi) hep "bilinen belirli anahtarlar dogru mu"
# sekilde yazildigi icin, YENI bir eksik-anahtar hatasini yapisal olarak
# YAKALAYAMAZLAR - bu yuzden asagidaki test, app.py kaynagini regex ile
# tarayip KULLANILAN TUM bare param_config["key"] anahtarlarini cikarir ve
# custom entry'de hepsinin (mikrobiyoloji-ozel olanlar haric) var oldugunu
# dogrular.
_APP_PY_PATH = os.path.join(os.path.dirname(__file__), "..", "src", "app.py")

# Custom parametreler icin YAPISAL OLARAK anlamsiz/gerekmeyen anahtarlar -
# is_microbio HER ZAMAN False oldugu icin (bkz. custom_parameter_to_config_
# entry docstring'i) mikrobiyoloji-ozel LOD/log-sigma alanlari custom
# entry'de hic bulunmaz ve bulunmasi da gerekmez.
_MICROBIO_ONLY_KEYS = {
    "demo_target_sigma", "default_lod", "log_axis_label", "log_decimal_places",
}


def _param_config_keys_used_in_app_py() -> set[str]:
    with open(_APP_PY_PATH, encoding="utf-8") as f:
        source = f.read()
    return set(re.findall(r'param_config\["([a-z_]+)"\]', source)) | set(
        re.findall(r"param_config\.get\(\"([a-z_]+)\"", source)
    )


def test_custom_parameter_entry_has_every_key_app_py_reads_unconditionally():
    used_keys = _param_config_keys_used_in_app_py()
    assert used_keys, "regex hicbir anahtar bulamadi - app.py'deki desen degismis olabilir"
    entry = custom_parameter_to_config_entry(_row())
    missing = (used_keys - _MICROBIO_ONLY_KEYS) - set(entry.keys())
    assert not missing, (
        f"custom_parameter_to_config_entry() su anahtar(lar)i EKSIK birakiyor, "
        f"app.py bunlari param_config[...] ile okuyor: {sorted(missing)}"
    )


def test_custom_parameter_entry_products_always_contains_manual_entry_key():
    # app.py, 'Ozel/Manuel gir'in HER parametrenin urun haritasinda VAR
    # oldugunu varsayarak products.index("Ozel/Manuel gir") cagirir
    # (Fix 2) - bu anahtar eksik olursa ValueError firlar.
    entry = custom_parameter_to_config_entry(_row())
    assert "Ozel/Manuel gir" in entry["products"]
