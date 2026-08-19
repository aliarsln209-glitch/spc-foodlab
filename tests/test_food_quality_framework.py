"""
v1.4 Parameter Framework (Food Quality Parameters) smoke testleri.

Bu istatistiksel bir formulu DOGRULAMAZ (Faz 1'in gercek LSL/USL kaynak
arastirmasi + worked example'lari validation/chemistry/ ve
validation/physical/ altina Adim 3-4'te eklenecek) - sadece:
  1) FOOD_QUALITY_PARAMETER_CONFIG'deki her kaydin framework semasina
     (physical_bounds, recommended_chart, subgroup_guidance, method_source,
     category, placeholder) uydugunu,
  2) bu kayitlarin ana PARAMETER_CONFIG/PARAMETER_CATEGORIES/
     PARAMETER_DESCRIPTIONS yapilarina dogru enjekte edildigini
dogrular - Adim 2'nin (UI entegrasyonu, placeholder limitlerle mimari testi)
gercekten "tek registry'den okunuyor" iddiasinin kanitidir.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from constants import (
    FOOD_QUALITY_CATEGORIES,
    FOOD_QUALITY_PARAMETER_CONFIG,
    PARAMETER_CATEGORIES,
    PARAMETER_CONFIG,
    PARAMETER_DESCRIPTIONS,
)

REQUIRED_FRAMEWORK_KEYS = {
    "unit", "physical_bounds", "recommended_chart", "subgroup_guidance",
    "method_source", "category", "placeholder",
}


def test_all_food_quality_entries_have_required_framework_keys():
    for param_name, config in FOOD_QUALITY_PARAMETER_CONFIG.items():
        missing = REQUIRED_FRAMEWORK_KEYS - config.keys()
        assert not missing, f"{param_name}: eksik framework alanlari {missing}"


def test_all_food_quality_entries_use_a_valid_category():
    for param_name, config in FOOD_QUALITY_PARAMETER_CONFIG.items():
        assert config["category"] in FOOD_QUALITY_CATEGORIES, (
            f"{param_name}: gecersiz kategori {config['category']!r}"
        )


def test_faz1_parameters_are_marked_as_placeholder():
    # Adim 2'de bilerek TASLAK - Adim 3'te gercek kaynakla degistirilecek
    for param_name in ("Protein", "Yag", "Kul", "Kuru Madde"):
        assert FOOD_QUALITY_PARAMETER_CONFIG[param_name]["placeholder"] is True


def test_food_quality_entries_merged_into_main_parameter_config():
    for param_name in FOOD_QUALITY_PARAMETER_CONFIG:
        assert param_name in PARAMETER_CONFIG
        # PARAMETER_CONFIG kaydi, app.py'nin dogrudan kullandigi legacy
        # alanlari (unit/min_value/max_value/products/...) da icermeli -
        # framework alanlariyla CAKISMADAN ayni sozlukte bir arada durur.
        assert "min_value" in PARAMETER_CONFIG[param_name]
        assert "products" in PARAMETER_CONFIG[param_name]


def test_food_quality_category_group_present_in_sidebar_categories():
    category_ids = [cat_id for cat_id, _label, _params in PARAMETER_CATEGORIES]
    assert "gida_kalite_v14_taslak" in category_ids


def test_food_quality_parameters_have_sidebar_descriptions():
    for param_name in FOOD_QUALITY_PARAMETER_CONFIG:
        assert param_name in PARAMETER_DESCRIPTIONS
        assert PARAMETER_DESCRIPTIONS[param_name]  # bos olmamali


if __name__ == "__main__":
    test_all_food_quality_entries_have_required_framework_keys()
    test_all_food_quality_entries_use_a_valid_category()
    test_faz1_parameters_are_marked_as_placeholder()
    test_food_quality_entries_merged_into_main_parameter_config()
    test_food_quality_category_group_present_in_sidebar_categories()
    test_food_quality_parameters_have_sidebar_descriptions()
    print("FOOD QUALITY FRAMEWORK TESTLERI GECTI")
