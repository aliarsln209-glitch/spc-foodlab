"""Proje genelinde sabit kalan yapilandirma degerleri (v1 kapsami)."""

SUBGROUP_SIZE = 4  # v1'de sabit - kullanici degistiremez (bkz. proje karari)
SHIFT_OPTIONS = ["Sabah", "Ogle", "Gece"]

# Gosterge amacli pH araligi (LSL, USL). Kaynak: Oklahoma State University
# Extension (FDA Bacteriological Analytical Manual verilerine dayanan) ve
# Dairy Food Safety Victoria teknik bilgi notu (sut urunleri icin). Bu
# degerler Turk Gida Kodeksi'nin yerini tutmaz - TGK cogu urunde sayisal
# bir pH limiti belirlemez; bu tablo sadece kalite kontrol referansidir.
# Detay ve kaynak linkleri icin bkz. README.md "Urun pH referans tablosu".
PRODUCT_PH_RANGES = {
    "Sut (taze)": (6.6, 6.9),
    "Yogurt": (4.0, 4.6),
    "Beyaz peynir/Feta": (4.1, 4.5),
    "Kasar/Cheddar tipi peynir": (5.1, 5.3),
    "Tereyagi": (6.1, 6.4),
    "Kirmizi et (taze)": (5.4, 6.2),
    "Tavuk": (6.2, 6.4),
    "Balik (cogu tur)": (6.6, 6.8),
    "Ekmek (beyaz)": (5.1, 5.6),
    "Biskuvi/kraker": (4.9, 6.0),
    "Kek/kurabiye": (5.5, 7.5),
    "Domates": (4.3, 4.9),
    "Havuc": (5.9, 6.3),
    "Yesil fasulye": (5.6, 6.5),
    "Patates": (5.4, 6.0),
    "Elma": (3.3, 4.0),
    "Portakal": (3.1, 4.1),
    "Muz": (4.5, 5.2),
    "Tursu": (3.0, 3.5),
    "Ketcap": (3.7, 3.9),
    "Ozel/Manuel gir": None,  # kullanici kendi LSL/USL'ini girer
}

# Gosterge amacli Brix (derece Brix, °Bx) araligi (LSL, USL). Kaynak: 19 CFR
# 151.91 (ABD federal regülasyonu - meyve suyu ithalati icin resmi ortalama
# Brix tablosu) + sektor pratigi. 19 CFR 151.91 tek nokta ortalama deger
# verdigi icin, LSL/USL araligi elde etmek amaciyla bu ortalamaya ±0.5
# tolerans eklendi. Bu degerler resmi bir zorunlu limit degil, kalite
# kontrol referansidir. Detay icin bkz. README.md "Brix referans tablosu".
BRIX_PRODUCT_RANGES = {
    "Elma suyu": (12.8, 13.8),
    "Portakal suyu": (11.3, 12.3),
    "Uzum suyu": (21.0, 22.0),
    "Greyfurt suyu": (9.7, 10.7),
    "Seftali suyu": (11.3, 12.3),
    "Visne/kiraz suyu": (13.8, 14.8),
    "Nar suyu": (17.7, 18.7),
    "Cilek suyu": (7.5, 8.5),
    "Limon suyu": (8.4, 9.4),
    "Ananas suyu": (13.8, 14.8),
    "Domates (salca/konsantre)": (28.0, 30.0),
    "Sarap mustu (uzum, hasat)": (19.0, 24.0),
    "Recel/marmelat": (65.0, 68.0),
    "Bal": (78.0, 82.0),
    "Hafif/light icecek": (6.0, 10.0),
    "Ozel/Manuel gir": None,
}

# Gosterge amacli aw (su aktivitesi, birimsiz, 0-1 arasi) UST limiti. aw'de
# sadece USL anlamlidir - "aw su degeri gecmesin" mikrobiyal guvenlik riskini
# ifade eder (dusuk aw'de bakteri/mantar uremesi durur); LSL cogu urun icin
# tanimsiz/anlamsizdir, bu yuzden degerler (None, USL) seklinde tutulur.
# Kaynak: DRINC / UC Davis ve Virginia Tech Cooperative Extension aw referans
# tablolari. FDA, dusuk asitli/asitlendirilmis konserve gida regulasyonunda
# (21 CFR 113/114) aw=0.85 esigini "potansiyel olarak tehlikeli gida" siniri
# olarak kullanir. Detay icin bkz. README.md "Aw referans tablosu".
AW_PRODUCT_RANGES = {
    "Taze et/balik": (None, 0.99),
    "Ekmek": (None, 0.95),
    "Islenmis peynir": (None, 0.98),
    "Olgun kasar/cheddar": (None, 0.87),
    "Fermente sucuk/sosis": (None, 0.87),
    "Recel/marmelat": (None, 0.80),
    "Kuru meyve": (None, 0.75),
    "Biskuvi/kraker": (None, 0.40),
    "Sut tozu/baharat": (None, 0.60),
    "Hazir kahve": (None, 0.20),
    "Ozel/Manuel gir": None,
}

# Parametre bazli yapilandirma - Sekme 2'deki urun/birim/aralik mantigi buna gore dallanir.
PARAMETER_CONFIG = {
    "pH": {
        "unit": "pH",
        "min_value": 0.0,
        "max_value": 14.0,
        "products": PRODUCT_PH_RANGES,
        "default_lsl": 6.8,
        "default_usl": 7.2,
        "default_measurement": 7.0,
        "demo_target_mean": 7.01,
        "demo_target_r_bar": 0.12,
        "one_sided": False,
    },
    "Brix": {
        "unit": "°Bx",
        "min_value": 0.0,
        "max_value": 100.0,
        "products": BRIX_PRODUCT_RANGES,
        "default_lsl": 10.0,
        "default_usl": 14.0,
        "default_measurement": 12.0,
        "demo_target_mean": 12.0,
        "demo_target_r_bar": 0.3,
        "one_sided": False,
    },
    "Aw": {
        "unit": "aw",
        "min_value": 0.0,
        "max_value": 1.0,
        "products": AW_PRODUCT_RANGES,
        "default_lsl": 0.0,  # kullanilmiyor (one_sided=True) - sadece placeholder
        "default_usl": 0.95,
        "default_measurement": 0.85,
        "demo_target_mean": 0.85,
        "demo_target_r_bar": 0.015,
        "one_sided": True,
    },
}
