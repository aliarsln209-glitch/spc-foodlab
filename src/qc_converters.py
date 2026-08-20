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


def build_bridge_subgroup_entry(value: float | list[float], shift_label: str) -> dict:
    """QC donusturucu sonucunu, mevcut subgroups sema formatina cevirir.

    app.py:96-97'deki st.session_state.subgroups listesi
    {"shift": str, "values": list[float]} sekli bekler; koprubu format
    degistirmez, sadece dogru sekli uretir - spc_core.py'ye HICBIR
    degisiklik gerekmez.

    value bir float ise (I-MR koprusu - tek olcum): {"values": [value]}.
    value bir list[float] ise (X-bar/R koprusu - n adet tekrar olcumu,
    ayni numunenin n kez titre edilmesi gibi gercek bir alt grup): tum
    liste dogrudan {"values": ...} olarak kullanilir. Hedefin X-bar/R
    olup olmadigina ve n'in dogru sayida olup olmadigina bu fonksiyon
    KARAR VERMEZ - o kontrol render_bridge_widget()'ta (app.py) yapilir,
    burasi sadece sekil/gecerlilik kontrolu yapan saf bir donusum katmanidir.
    """
    if isinstance(value, list):
        if not value:
            raise ValueError("kopru degerleri listesi bos olamaz")
        for v in value:
            if not math.isfinite(v):
                raise ValueError("kopru degeri sonlu bir sayi olmalidir (NaN/inf kabul edilmez)")
        return {"shift": shift_label, "values": list(value)}
    if not math.isfinite(value):
        raise ValueError("kopru degeri sonlu bir sayi olmalidir (NaN/inf kabul edilmez)")
    return {"shift": shift_label, "values": [value]}


def titratable_acidity(
    titrant_volume_ml: float, titrant_normality: float, acid_meq_factor: float, sample_size_ml: float,
) -> dict:
    """AOAC titre edilebilir asitlik: %Asitlik = (V x N x meq_faktoru x 100) / numune.

    titrant_volume_ml: harcanan titrant (orn. NaOH) hacmi (mL)
    titrant_normality: titrant normalitesi (N, eq/L)
    acid_meq_factor: baskin asidin miliekivalan faktoru (g/meq) - bkz.
        constants.TITRATABLE_ACID_MEQ_FACTORS turetme notu
    sample_size_ml: numune miktari (mL)
    """
    if sample_size_ml <= 0:
        raise ValueError("numune miktari sifir veya negatif olamaz")
    if titrant_volume_ml < 0 or titrant_normality < 0:
        raise ValueError("titre hacmi/normalite negatif olamaz")
    if acid_meq_factor <= 0:
        raise ValueError("asit faktoru sifir veya negatif olamaz")
    acidity_pct = (titrant_volume_ml * titrant_normality * acid_meq_factor * 100.0) / sample_size_ml
    return {"acidity_pct": acidity_pct}
