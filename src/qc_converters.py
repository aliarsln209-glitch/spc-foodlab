"""QC Veri Donusturucu formulleri - Streamlit'ten bagimsiz, saf mantik.

Mimari ilke microbiology.py ile aynidir: hicbir fonksiyon st.session_state'e
dokunmaz, sadece deger hesaplar/dondurur. session_state entegrasyonu app.py'de
build_bridge_subgroup_entry() ciktisini subgroups listesine ekleyerek yapilir.
"""

import math


def gravimetric_moisture(
    dish_tare_g: float, wet_with_dish_g: float, dry_with_dish_g: float
) -> dict:
    """AOAC 925.10 gravimetrik nem/kuru madde tayini.

    dish_tare_g: bos kabin agirligi (g)
    wet_with_dish_g: kap + yas numune agirligi (g)
    dry_with_dish_g: kap + kurutma sonrasi kalinti agirligi (g)
    """
    wet_sample_g = wet_with_dish_g - dish_tare_g
    dry_sample_g = dry_with_dish_g - dish_tare_g

    if wet_sample_g <= 0:
        raise ValueError("net yas numune agirligi sifir veya negatif olamaz")
    if dry_sample_g > wet_sample_g:
        raise ValueError("kuru kalinti agirligi, yas numune agirligindan buyuk olamaz")

    moisture_pct = (wet_sample_g - dry_sample_g) / wet_sample_g * 100.0
    dry_matter_pct = 100.0 - moisture_pct

    return {
        "wet_sample_g": wet_sample_g,
        "dry_sample_g": dry_sample_g,
        "moisture_pct": moisture_pct,
        "dry_matter_pct": dry_matter_pct,
    }


def build_bridge_subgroup_entry(value: float, shift_label: str) -> dict:
    """QC donusturucu sonucunu, mevcut subgroups sema formatina cevirir.

    app.py:96-97'deki st.session_state.subgroups listesi
    {"shift": str, "values": list[float]} sekli bekler; koprubu format
    degistirmez, sadece dogru sekli uretir - spc_core.py'ye HICBIR
    degisiklik gerekmez.
    """
    if not math.isfinite(value):
        raise ValueError("kopru degeri sonlu bir sayi olmalidir (NaN/inf kabul edilmez)")
    return {"shift": shift_label, "values": [value]}
