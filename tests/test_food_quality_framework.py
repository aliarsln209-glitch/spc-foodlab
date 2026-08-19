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


def test_faz1_parameters_are_no_longer_placeholder_after_source_research():
    # Adim 3 (LSL/USL kaynak arastirmasi) tamamlandi - artik dogrulanmis
    # TGK tebligi kaynagina dayanirlar (bkz. constants.py PROTEIN/YAG/KUL/
    # KURU_MADDE_PRODUCT_RANGES notlari), placeholder=False olmalidir.
    for param_name in ("Protein", "Yag", "Kul", "Kuru Madde"):
        assert FOOD_QUALITY_PARAMETER_CONFIG[param_name]["placeholder"] is False


def test_faz1_parameters_have_at_least_one_verified_product():
    # Her parametrenin "Ozel/Manuel gir" DISINDA en az bir gercek urun
    # girisi olmali - aksi halde kaynak arastirmasi hicbir seye baglanmamis
    # olur.
    for param_name in ("Protein", "Yag", "Kul", "Kuru Madde"):
        products = FOOD_QUALITY_PARAMETER_CONFIG[param_name]["products"]
        real_products = [p for p in products if p != "Ozel/Manuel gir"]
        assert real_products, f"{param_name}: dogrulanmis urun girisi yok"


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
    assert "gida_kalite_v14" in category_ids


def test_ash_is_one_sided_upper_limit_only():
    # Kul HER ZAMAN bir ust limit spesifikasyonudur (dusuk kul = daha
    # rafine urun) - Peroksit Degeri/HMF ile ayni mimari, matematiksel
    # tavan hilesine GEREK yoktur (bkz. constants.py KUL_PRODUCT_RANGES notu).
    assert FOOD_QUALITY_PARAMETER_CONFIG["Kul"]["one_sided"] is True
    for product, rng in FOOD_QUALITY_PARAMETER_CONFIG["Kul"]["products"].items():
        if product == "Ozel/Manuel gir":
            continue
        lsl, usl = rng
        assert lsl is None
        assert usl is not None


def test_faz2_parameters_present_and_verified():
    # v1.5 Faz 2: Yogunluk, Refraktif Indeks - AYNI disiplin (dogrulanmis
    # TGK tebligi kaynagi, kaynagi bulunamayan urun icin sayi uydurulmadi).
    for param_name in ("Yogunluk", "Refraktif Indeks"):
        assert param_name in FOOD_QUALITY_PARAMETER_CONFIG
        config = FOOD_QUALITY_PARAMETER_CONFIG[param_name]
        assert config["placeholder"] is False
        real_products = [p for p in config["products"] if p != "Ozel/Manuel gir"]
        assert real_products, f"{param_name}: dogrulanmis urun girisi yok"


def test_refraktif_indeks_physical_lower_bound_is_water():
    # nD >= 1.333 (su) - METHODOLOGY.md v1.5 notu
    lower, _upper = FOOD_QUALITY_PARAMETER_CONFIG["Refraktif Indeks"]["physical_bounds"]
    assert lower == 1.333


def test_yogunluk_and_refraktif_indeks_are_two_sided():
    # Zeytinyagi Tebligi (98/7) her ikisini de min-max araligi olarak tanimlar
    # - matematiksel tavan hilesine GEREK yok (Protein/Kuru Madde'nin AKSINE).
    for param_name in ("Yogunluk", "Refraktif Indeks"):
        assert FOOD_QUALITY_PARAMETER_CONFIG[param_name]["one_sided"] is False


def test_faz3_optics_parameters_present_with_correct_physical_bounds():
    # v1.6 Faz 3: L*, a*, b*, Bulaniklik, Iletkenlik - urune ozgu dogrulanmis
    # bir kaynak BULUNAMADI (bkz. constants.py notlari), bu yuzden TUMU
    # sadece "Ozel/Manuel gir" icerir - Hammadde Kutuphanesi'ndeki AYNI
    # disiplin (kaynagi dogrulanamayan kombinasyon icin sayi uydurulmaz).
    for param_name in ("L*", "a*", "b*", "Bulaniklik", "Iletkenlik"):
        assert param_name in FOOD_QUALITY_PARAMETER_CONFIG
        config = FOOD_QUALITY_PARAMETER_CONFIG[param_name]
        assert config["category"] == "Optik"
        assert list(config["products"].keys()) == ["Ozel/Manuel gir"]

    # L* 0-100, a*/b* -128/+127 (CIELAB) - L*'nin AYNISI DEGIL (METHODOLOGY.md
    # v1.6 notu: "ayni bound'u ucune birden uygulama").
    assert FOOD_QUALITY_PARAMETER_CONFIG["L*"]["physical_bounds"] == (0.0, 100.0)
    for param_name in ("a*", "b*"):
        assert FOOD_QUALITY_PARAMETER_CONFIG[param_name]["physical_bounds"] == (-128.0, 127.0)


def test_bulaniklik_is_one_sided_upper_limit_only():
    # Bulaniklik HER ZAMAN bir ust limit spesifikasyonudur (berraklik hedefi)
    assert FOOD_QUALITY_PARAMETER_CONFIG["Bulaniklik"]["one_sided"] is True


def test_protein_and_kuru_madde_use_mathematical_ceiling_for_lsl_only_specs():
    # spc_core.py sadece USL-only (Cpu) tek tarafli hesaplamayi destekler,
    # LSL-only (Cpl) YOKTUR - bu yuzden gercekte sadece minimum tanimli olan
    # Protein/Kuru Madde urunlerinde USL=100.0 matematiksel tavan olarak
    # eklenir (RAW_MATERIAL_QC_REFERENCE'daki "Tuz" girisiyle AYNI desen).
    for param_name in ("Protein", "Kuru Madde"):
        for product, rng in FOOD_QUALITY_PARAMETER_CONFIG[param_name]["products"].items():
            if product == "Ozel/Manuel gir":
                continue
            lsl, usl = rng
            assert lsl is not None
            assert usl == 100.0


def test_food_quality_parameters_have_sidebar_descriptions():
    for param_name in FOOD_QUALITY_PARAMETER_CONFIG:
        assert param_name in PARAMETER_DESCRIPTIONS
        assert PARAMETER_DESCRIPTIONS[param_name]  # bos olmamali


if __name__ == "__main__":
    test_all_food_quality_entries_have_required_framework_keys()
    test_all_food_quality_entries_use_a_valid_category()
    test_faz1_parameters_are_no_longer_placeholder_after_source_research()
    test_faz1_parameters_have_at_least_one_verified_product()
    test_food_quality_entries_merged_into_main_parameter_config()
    test_food_quality_category_group_present_in_sidebar_categories()
    test_ash_is_one_sided_upper_limit_only()
    test_faz2_parameters_present_and_verified()
    test_refraktif_indeks_physical_lower_bound_is_water()
    test_yogunluk_and_refraktif_indeks_are_two_sided()
    test_faz3_optics_parameters_present_with_correct_physical_bounds()
    test_bulaniklik_is_one_sided_upper_limit_only()
    test_protein_and_kuru_madde_use_mathematical_ceiling_for_lsl_only_specs()
    test_food_quality_parameters_have_sidebar_descriptions()
    print("FOOD QUALITY FRAMEWORK TESTLERI GECTI")
