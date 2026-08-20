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


def bridge_value_count_matches(values: float | list[float], required_n: int) -> bool:
    """X-bar/R koprusu icin, verilen degerlerin TAM OLARAK required_n adet olup
    olmadigini kontrol eder - render_bridge_widget()'in (app.py) X-bar/R gating
    mantiginin saf/test edilebilir cekirdegi. UI tarafi (st.warning/buton
    gosterme kararlari) app.py'de kalir, burasi sadece dogru/yanlis dondurur.
    """
    if not isinstance(values, list):
        values = [values]
    return len(values) == required_n


def bridge_value_is_single(value: float | list[float]) -> bool:
    """I-MR koprusu icin, verilen degerin TEK bir olcum olup olmadigini kontrol
    eder (duz bir float, veya tam 1 elemanli bir liste). Bu, X-bar/R kopru
    yolunun aksine bir hedefe yanlislikla coklu deger koprulenmesini engeller -
    bridge_value_count_matches()'in I-MR karsiligi (bkz. o fonksiyonun
    docstring'i).
    """
    if isinstance(value, list):
        return len(value) == 1
    return True


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


# NaCl meq faktoru: MW(NaCl) = 22.990(Na) + 35.453(Cl) = 58.443 g/mol
# (IUPAC standart atomik agirliklari), tek degerlikli (bazisite=1) ->
# meq faktoru = MW/1000 = 0.058443 -> 0.05844 (Mohr yontemi, AgNO3
# titrasyonu ile klorur tayini, %NaCl olarak raporlanir).
NACL_MEQ_FACTOR = 0.05844


def salt_content_mohr(
    titrant_volume_ml: float, titrant_normality: float, sample_size_g: float,
) -> dict:
    """Mohr yontemi (AgNO3 titrasyonu ile klorur tayini): %NaCl = (V x N x 0.05844 x 100) / numune(g).

    titrant_volume_ml: harcanan AgNO3 hacmi (mL)
    titrant_normality: AgNO3 normalitesi (N, eq/L)
    sample_size_g: numune agirligi (g)
    """
    if sample_size_g <= 0:
        raise ValueError("numune agirligi sifir veya negatif olamaz")
    if titrant_volume_ml < 0 or titrant_normality < 0:
        raise ValueError("titre hacmi/normalite negatif olamaz")
    salt_pct = (titrant_volume_ml * titrant_normality * NACL_MEQ_FACTOR * 100.0) / sample_size_g
    return {"salt_pct": salt_pct}


def thermal_lethality_f0(
    temperatures_c: list[float],
    delta_t_minutes: float,
    reference_temp_c: float = 121.1,
    z_value: float = 10.0,
) -> dict:
    """Bigelow/Ball formulu ile termal letalite (F0) hesabi.

    F0 = delta_t * sum(10 ** ((T_i - reference_temp_c) / z_value))

    temperatures_c: retort/proses sirasinda esit araliklarla okunan
        sicaklik degerleri listesi (C), zaman sirasina gore.
    delta_t_minutes: ardisik okumalar arasindaki sabit zaman araligi (dk).
    reference_temp_c: referans sicaklik (varsayilan 121.1C = 250F, standart).
    z_value: z-degeri (varsayilan 10C, standart - Clostridium botulinum
        icin termal direnc egrisinin egimi).

    Kaynak (formul): Bigelow (1921) / Ball (1923) genel letalite formulu -
    gida muhendisligi ders kitabi matematigi, ICUMSA Brix tablosu gibi
    erisilemez bir kaynak DEGIL.
    """
    if not temperatures_c:
        raise ValueError("en az bir sicaklik okumasi gereklidir")
    if delta_t_minutes <= 0:
        raise ValueError("delta_t_minutes sifir veya negatif olamaz")

    lethality_sum = sum(10 ** ((t - reference_temp_c) / z_value) for t in temperatures_c)
    return {"f0_minutes": delta_t_minutes * lethality_sum}
