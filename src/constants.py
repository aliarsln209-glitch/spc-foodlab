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
