"""
Hammadde Kutuphanesi (v1.1.1) testleri.

Mimari: hammaddeler yeni bir istatistik motoru veya secim akisi
eklemeden, mevcut PARAMETER_CONFIG[...]['products'] sozluklerine
"RAW_MATERIAL_PREFIX" (bkz. constants.py) onekiyle enjekte edilir.
'Hammadde secilince parametre listesi otomatik filtrelenir' gereksinimi,
bir hammaddenin SADECE ilgili oldugu parametrenin urun sozlugunde
bulunmasiyla (baska parametrede hic gorunmemesiyle) saglanir - ayri bir
filtreleme fonksiyonu yoktur, bu yuzden asagidaki testler dogrudan
constants.py veri yapisini kontrol eder.

Bu dosya spc_core.py'ye (X-bar/R, I-MR, Cpk hesaplama motoru) hic
dokunmuyor - hammadde eklemenin hesaplama motorunu etkilemedigi, motor
degismedigi (bkz. test_validation.py/test_imr_validation.py/
test_cpk_edge_cases.py'nin bu PR'da HİÇ degismemis olmasi) ile zaten
garanti altindadir.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from constants import (
    AW_PRODUCT_RANGES,
    BRIX_PRODUCT_RANGES,
    HMF_PRODUCT_RANGES,
    MOISTURE_PRODUCT_RANGES,
    PARAMETER_CONFIG,
    PEROXIDE_PRODUCT_RANGES,
    PRODUCT_PH_RANGES,
    RAW_MATERIAL_PREFIX,
    RAW_MATERIAL_QC_REFERENCE,
    SALT_PRODUCT_RANGES,
    TITRATABLE_ACIDITY_PRODUCT_RANGES,
    VISCOSITY_PRODUCT_RANGES,
)

ALL_PARAM_DICTS = {
    "pH": PRODUCT_PH_RANGES,
    "Brix": BRIX_PRODUCT_RANGES,
    "Aw": AW_PRODUCT_RANGES,
    "Viskozite": VISCOSITY_PRODUCT_RANGES,
    "Nem / Kuru Madde": MOISTURE_PRODUCT_RANGES,
    "Tuz/NaCl": SALT_PRODUCT_RANGES,
    "Titrasyon Asitligi": TITRATABLE_ACIDITY_PRODUCT_RANGES,
    "Peroksit Degeri": PEROXIDE_PRODUCT_RANGES,
    "HMF": HMF_PRODUCT_RANGES,
}


def _key(material: str) -> str:
    return f"{RAW_MATERIAL_PREFIX}{material}"


# --- 16 hammadde tanimli mi -------------------------------------------------

def test_exactly_16_raw_materials_defined():
    assert len(RAW_MATERIAL_QC_REFERENCE) == 16


def test_all_16_raw_material_names_present():
    expected = {
        "Bugday unu", "Sut tozu", "Glikoz surubu", "Maltodekstrin",
        "Maltitol", "Nisasta", "Bitkisel yag", "Peynir alti suyu tozu",
        "Kakao tozu", "Toz seker", "Fruktoz", "Pektin", "Jelatin",
        "Konsantre meyve suyu", "Yumurta tozu", "Tuz",
    }
    assert set(RAW_MATERIAL_QC_REFERENCE.keys()) == expected


# --- Urun -> parametre filtrelemesi (en az 3 hammadde, spec'te istenen) ----

def test_bitkisel_yag_only_in_peroxide_and_viscosity():
    # Bitkisel yag: SADECE Peroksit Degeri + Viskozite parametrelerinde
    # gorunmeli, digerlerinde (pH, Brix, Aw, Nem, Tuz, TA, HMF) HIC
    # gorunmemeli - bu, "hammadde secilince parametre filtrelenir"
    # gereksiniminin dogrudan kanitidir.
    key = _key("Bitkisel yag")
    expected_present = {"Peroksit Degeri", "Viskozite"}
    for param_name, product_dict in ALL_PARAM_DICTS.items():
        if param_name in expected_present:
            assert key in product_dict, f"{key} {param_name} icinde olmali"
        else:
            assert key not in product_dict, f"{key} {param_name} icinde OLMAMALI"


def test_bugday_unu_only_in_moisture_aw_ph():
    key = _key("Bugday unu")
    expected_present = {"Nem / Kuru Madde", "Aw", "pH"}
    for param_name, product_dict in ALL_PARAM_DICTS.items():
        if param_name in expected_present:
            assert key in product_dict
        else:
            assert key not in product_dict


def test_konsantre_meyve_suyu_only_in_brix_ph_viscosity_ta_hmf():
    key = _key("Konsantre meyve suyu")
    expected_present = {"Brix", "pH", "Viskozite", "Titrasyon Asitligi", "HMF"}
    for param_name, product_dict in ALL_PARAM_DICTS.items():
        if param_name in expected_present:
            assert key in product_dict
        else:
            assert key not in product_dict


def test_tuz_only_in_salt_and_aw():
    key = _key("Tuz")
    expected_present = {"Tuz/NaCl", "Aw"}
    for param_name, product_dict in ALL_PARAM_DICTS.items():
        if param_name in expected_present:
            assert key in product_dict
        else:
            assert key not in product_dict


# --- Mevcut bitmiş urunler degismedi (regresyon) ----------------------------

def test_existing_finished_products_unchanged():
    # Bu degerler v1.1.1 oncesinde de ayniydi - hammadde eklemesi mevcut
    # bitmiş urun spesifikasyonlarini DEGISTIRMEMELI.
    assert PRODUCT_PH_RANGES["Sut (taze)"] == (6.6, 6.9)
    assert PRODUCT_PH_RANGES["Ozel/Manuel gir"] is None
    assert MOISTURE_PRODUCT_RANGES["Bal"] == (None, 20.0)
    assert AW_PRODUCT_RANGES["Kuru meyve"] == (None, 0.75)
    assert SALT_PRODUCT_RANGES["Beyaz peynir"] == (2.0, 4.0)
    assert PEROXIDE_PRODUCT_RANGES["Zeytinyagi (naturel sizma)"] == (None, 20.0)
    assert HMF_PRODUCT_RANGES["Bal"] == (None, 40.0)


def test_ozel_manuel_gir_still_last_key_in_every_parameter_dict():
    # Hammadde enjeksiyonu sozluklerin SONUNA (Ozel/Manuel gir'den once)
    # eklenmeli - "Ozel/Manuel gir" her zaman en sonda kalmali (mevcut
    # UI'da varsayilan secim indeksi buna dayanir, bkz. app.py
    # 'default_index = products.index("Ozel/Manuel gir")').
    for product_dict in ALL_PARAM_DICTS.values():
        assert list(product_dict.keys())[-1] == "Ozel/Manuel gir"


def test_parameter_config_products_reference_same_dicts():
    # PARAMETER_CONFIG['products'] hala ayni dict nesnelerine isaret ediyor
    # (hammadde enjeksiyonu PARAMETER_CONFIG tanimindan ONCE calisiyor).
    for param_name, product_dict in ALL_PARAM_DICTS.items():
        assert PARAMETER_CONFIG[param_name]["products"] is product_dict


# --- Kaynak durustlugu: dogrulanmamis kombinasyonlarda UYDURMA SAYI YOK ----

def test_unverified_raw_material_params_have_no_fabricated_range():
    # KRITIK KURAL: kaynagi dogrulanamayan hicbir hammadde-parametre
    # kombinasyonu icin sayisal LSL/USL uydurulmamali - bu durumda range
    # MUTLAKA None olmali (kullanici manuel girer).
    for material, params in RAW_MATERIAL_QC_REFERENCE.items():
        for param_name, spec in params.items():
            if spec["verified"] is False:
                assert spec["range"] is None, (
                    f"{material}/{param_name} 'verified=False' ama range "
                    f"None degil: {spec['range']!r} - kaynaksiz sayi olmamali."
                )


def test_verified_raw_material_params_have_a_range():
    for material, params in RAW_MATERIAL_QC_REFERENCE.items():
        for param_name, spec in params.items():
            if spec["verified"] in (True, "kismi"):
                assert spec["range"] is not None
                assert spec["source"], f"{material}/{param_name} kaynaksiz ama verified"


def test_exactly_four_sourced_pairs_three_full_one_partial():
    # Arastirma turunda kaynakli (tebligi+sayisi bulunan) toplam 4
    # hammadde-parametre cifti bulundu: 3 tam dogrulanmis (verified=True)
    # + 1 kismi dogrulanmis (verified="kismi" - arama snippet'i ile
    # dogrulandi, tam metin taranmis PDF oldugu icin tablo dogrudan
    # okunamadi). Kalan ~57 kombinasyonun hepsi manuel giris.
    fully_sourced = [
        (m, p) for m, params in RAW_MATERIAL_QC_REFERENCE.items()
        for p, spec in params.items() if spec["verified"] is True
    ]
    partially_sourced = [
        (m, p) for m, params in RAW_MATERIAL_QC_REFERENCE.items()
        for p, spec in params.items() if spec["verified"] == "kismi"
    ]
    assert set(fully_sourced) == {
        ("Peynir alti suyu tozu", "Nem / Kuru Madde"),
        ("Kakao tozu", "Nem / Kuru Madde"),
        ("Tuz", "Tuz/NaCl"),
    }
    assert partially_sourced == [("Bugday unu", "Nem / Kuru Madde")]
    assert len(fully_sourced) + len(partially_sourced) == 4


# --- Tuz hammaddesi icin genisletilmis max_value ----------------------------

def test_salt_parameter_max_value_widened_for_raw_salt_purity():
    # Tuz hammaddesinin NaCl safligi (%98-100) bitmiş urun tuz oranindan
    # (tipik %0-10) cok daha yuksek - number_input widget'inin bunu kabul
    # edebilmesi icin max_value 20'den 100'e cikarildi. Mevcut bitmiş urun
    # degerleri (1.5-10 arasi) bu araligin icinde kaldigi icin etkilenmez.
    assert PARAMETER_CONFIG["Tuz/NaCl"]["max_value"] == 100.0
    tuz_range = SALT_PRODUCT_RANGES[_key("Tuz")]
    assert tuz_range == (98.0, 100.0)
    lsl, usl = tuz_range
    assert PARAMETER_CONFIG["Tuz/NaCl"]["min_value"] <= lsl <= PARAMETER_CONFIG["Tuz/NaCl"]["max_value"]
    assert PARAMETER_CONFIG["Tuz/NaCl"]["min_value"] <= usl <= PARAMETER_CONFIG["Tuz/NaCl"]["max_value"]


if __name__ == "__main__":
    test_exactly_16_raw_materials_defined()
    test_all_16_raw_material_names_present()
    test_bitkisel_yag_only_in_peroxide_and_viscosity()
    test_bugday_unu_only_in_moisture_aw_ph()
    test_konsantre_meyve_suyu_only_in_brix_ph_viscosity_ta_hmf()
    test_tuz_only_in_salt_and_aw()
    test_existing_finished_products_unchanged()
    test_ozel_manuel_gir_still_last_key_in_every_parameter_dict()
    test_parameter_config_products_reference_same_dicts()
    test_unverified_raw_material_params_have_no_fabricated_range()
    test_verified_raw_material_params_have_a_range()
    test_exactly_four_sourced_pairs_three_full_one_partial()
    test_salt_parameter_max_value_widened_for_raw_salt_purity()
    print("HAMMADDE KUTUPHANESI TESTLERI GECTI")
