"""Proje genelinde sabit kalan yapilandirma degerleri (v1 kapsami)."""

DEFAULT_SUBGROUP_SIZE = 4  # kullanici degistirebilir (sidebar) - bu sadece baslangic degeri
# n=1 icin X-bar/R anlamli degildir (range=0 olur); bu durumda zaten ayri bir
# chart turu olan I-MR kullanilir (bkz. PARAMETER_CONFIG["is_individual"]).
# Ust sinir CONTROL_CHART_CONSTANTS (spc_core.py) tablosunun kapsadigi n=10'dur.
MIN_SUBGROUP_SIZE = 2
MAX_SUBGROUP_SIZE = 10
SHIFT_OPTIONS = ["Sabah", "Ogle", "Gece"]

# Sidebar'da parametre secici radyo'nun altinda gosterilen kisa aciklamalar
# (st.radio captions=). Sadece bilgilendirme amaclidir, hesaplamayi etkilemez.
PARAMETER_DESCRIPTIONS = {
    "pH": "Asit/baz dengesi (0-14). Cogu gida urununde iki tarafli spesifikasyon.",
    "Brix": "Cozunur kuru madde / seker orani (°Bx). Meyve suyu, salca, recel.",
    "Aw": "Su aktivitesi (0-1) - mikrobiyal bozulma riski gostergesi. Genelde tek tarafli (ust limit).",
    "Viskozite": "Akiskanliga direnc (cP). Tek tek olculur - I-MR chart kullanilir.",
    "Nem/Rutubet": "Numunedeki nem yuzdesi (%). Bal gibi urunlerde tek tarafli olabilir.",
    "Tuz/NaCl": "Sodyum klorur yuzdesi (%). Salamura, sarkuteri urunlerinde kritik.",
    "Titrasyon Asitligi": "Titre edilebilir toplam asitlik (%). pH'tan farkli, toplam asit miktarini olcer.",
    "Peroksit Degeri": "Yaglarda oksidatif bozulma gostergesi (meq O2/kg). Tek tek olculur, tek tarafli.",
    "HMF": "Isil islem/depolama sirasinda olusan bozulma belirteci (mg/kg). Tek tek olculur, tek tarafli.",
}

# "Parametre Bilgi Karti" (tab_chart ustunde) icin daha uzun (2-3 cumle)
# aciklamalar - ne olcer, neden onemli. PARAMETER_DESCRIPTIONS'dan (sidebar
# caption) farkli olarak burada "neden onemli" kismi da var.
PARAMETER_INFO = {
    "pH": (
        "pH, bir urunun asit/baz dengesini (0-14 olcek, 7=notr) gosterir. "
        "Gida guvenliginde kritiktir: dusuk pH (asidik ortam) cogu patojen "
        "bakterinin uremesini engeller, bu yuzden fermente/konserve "
        "urunlerde siki takip edilir."
    ),
    "Brix": (
        "Brix (°Bx), bir cozeltideki cozunur kuru madde (agirlikli olarak "
        "seker) oranini yuzde olarak gosterir. Meyve suyu, salca, recel gibi "
        "urunlerde hem tat/kalite tutarliligi hem de raf omru (yuksek Brix, "
        "mikrobiyal uremeyi kisitlar) acisindan onemlidir."
    ),
    "Aw": (
        "Su aktivitesi (aw), gidadaki suyun ne kadarinin mikroorganizmalar "
        "tarafindan kullanilabilir oldugunu gosterir (0-1 olcek, saf su=1). "
        "Toplam nem miktarindan farklidir - mikrobiyal bozulma riskini "
        "dogrudan tahmin eden, gida guvenligi acisindan kritik bir gostergedir."
    ),
    "Viskozite": (
        "Viskozite, bir sivinin akiskanliga karsi direncini olcer (cP). "
        "Urun tutarliligi (agiz hissi, dokum/doldurma hizi, ambalaj "
        "performansi) acisindan onemlidir - hedeften sapma, uretim "
        "hattinda dolum/paketleme sorunlarina yol acabilir."
    ),
    "Nem/Rutubet": (
        "Nem/rutubet, numunedeki su icerigini yuzde olarak gosterir. "
        "Raf omru, mikrobiyal stabilite ve bazi urunlerde (orn. bal) yasal "
        "kalite tanimi acisindan dogrudan etkilidir."
    ),
    "Tuz/NaCl": (
        "Tuz/NaCl orani, hem tat/kalite standardizasyonu hem de bazi "
        "urunlerde (salamura, sarkuteri) mikrobiyal stabilite acisindan "
        "kontrol edilen bir parametredir."
    ),
    "Titrasyon Asitligi": (
        "Titrasyon asitligi, bir numunedeki toplam titre edilebilir asit "
        "miktarini olcer - pH'tan farkli olarak zayif asitlerin toplam "
        "miktarini yansitir. Tat profili ve mikrobiyal stabilite ile "
        "iliskilidir."
    ),
    "Peroksit Degeri": (
        "Peroksit degeri, yaglarda/yaglı urunlerde oksidatif bozulmanin "
        "(acilasma) erken gostergesidir. Deger ne kadar dusukse yag o kadar "
        "taze/stabildir; sadece bir ust limit (USL) anlamlidir."
    ),
    "HMF": (
        "HMF (hidroksimetilfurfural), isil islem veya uzun sureli depolama "
        "sirasinda sekerlerin bozunmasiyla olusan bir belirtectir. Yuksek "
        "HMF, asiri isil islem veya kotu depolama kosullarina isaret eder."
    ),
}

# "Kaynak Rozeti" (urun secildikten sonra LSL/USL'in dayandigi kaynagin kisa
# ozeti) - detayli kaynak/tolerans notlari icin bkz. METHODOLOGY.md.
PARAMETER_SOURCES = {
    "pH": "Oklahoma State University Extension, Dairy Food Safety Victoria",
    "Brix": "19 CFR 151.91 (ABD federal regulasyonu) + sektor pratigi",
    "Aw": "DRINC/UC Davis, Virginia Tech Cooperative Extension",
    "Nem/Rutubet": "Sektor pratigi (Bal: TGK Bal Tebligi)",
    "Tuz/NaCl": "Sektor pratigi",
    "Titrasyon Asitligi": "Sektor pratigi",
    "Viskozite": "Prime Resins, Sculpture Supply (teknik viskozite tablolari)",
    "Peroksit Degeri": "Codex Alimentarius / IOC (International Olive Council)",
    "HMF": "TGK Bal Tebligi, TGK Uzum Pekmezi Tebligi, sektor pratigi",
}

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

# Gosterge amacli viskozite (cP - santipoaz) araligi (LSL, USL). Kaynak: Prime
# Resins ve Sculpture Supply teknik viskozite tablolari (gercek marka
# olcumlerine dayanan sektor referanslari) - resmi/zorunlu bir standart degil,
# kalite kontrol referansidir. Detay icin bkz. README.md "Viskozite referans
# tablosu". NOT: Ketcap, hardal gibi urunler tiksotropiktir - karistirma/
# basinc arttikca viskoziteleri azalir; olcum kosullari (karistirma hizi,
# bekleme suresi) standardize edilmeden yapilan olcumler tutarsiz olabilir.
VISCOSITY_PRODUCT_RANGES = {
    "Sut": (3, 4),
    "Meyve suyu": (40, 60),
    "Akcaagac surubu": (150, 200),
    "Bal": (2000, 3000),
    "Melas": (5000, 10000),
    "Cikolata surubu": (10000, 25000),
    "Ketcap": (45000, 55000),
    "Hardal": (65000, 75000),
    "Misir surubu (yogun)": (100000, 120000),
    "Domates salcasi": (180000, 200000),
    "Fistik ezmesi": (240000, 260000),
    "Ozel/Manuel gir": None,
}

# Gosterge amacli nem/rutubet (%) araligi (LSL, USL). Bal icin (None, 20.0) -
# TGK Bal Tebliginde tek taraflı (sadece ust limit) bir sinir olarak
# tanimlanmistir; diger urunler iki tarafli araliga sahiptir. Bu, PARAMETRE
# bazinda degil URUN bazinda tek/iki tarafli Cpk secimine bir ornektir - bkz.
# app.py'deki one_sided hesaplama mantigi (urunun LSL'i None ise o urun icin
# tek tarafli Cpu hesaplanir, parametrenin geri kalani iki tarafli kalabilir).
MOISTURE_PRODUCT_RANGES = {
    "Ekmek": (35.0, 40.0),
    "Biskuvi/kraker": (2.0, 5.0),
    "Kasar peyniri": (40.0, 45.0),
    "Bal": (None, 20.0),  # TGK Bal Tebligi - tek tarafli, sadece ust limit
    "Makarna (kuru)": (10.0, 12.5),
    "Domates salcasi": (70.0, 72.0),
    "Ozel/Manuel gir": None,
}

# Gosterge amacli tuz/NaCl (%) araligi (LSL, USL). Sektor pratigine dayanan
# kalite kontrol referansi, TGK'nin yerini tutmaz.
SALT_PRODUCT_RANGES = {
    "Ekmek": (1.5, 2.0),
    "Beyaz peynir": (2.0, 4.0),
    "Kasar peyniri": (1.5, 2.5),
    "Sucuk/salam": (2.0, 3.0),
    "Tursu salamurasi": (5.0, 10.0),
    "Zeytin (sofralik, salamura)": (4.0, 8.0),
    "Ozel/Manuel gir": None,
}

# Gosterge amacli titrasyon asitligi (%) araligi (LSL, USL). Sektor
# pratigine dayanan kalite kontrol referansi.
TITRATABLE_ACIDITY_PRODUCT_RANGES = {
    "Sut (taze)": (0.14, 0.16),
    "Yogurt": (0.6, 1.0),
    "Domates salcasi": (0.4, 0.6),
    "Meyve suyu (genel)": (0.3, 1.5),
    "Tursu": (0.6, 1.2),
    "Ozel/Manuel gir": None,
}

# Gosterge amacli peroksit degeri (meq O2/kg) UST limiti. Yaglarda oksidasyon
# derecesini gosterir - sadece USL anlamlidir (peroksit degeri ne kadar
# dusukse o kadar iyi; alt limit kavrami yoktur). Kaynak: Codex Alimentarius/
# IOC (International Olive Council) standardi (zeytinyagi icin). Her olcum
# tek basina bir batch/parti sonucu oldugundan (alt grup yok), I-MR chart
# kullanilir (bkz. PARAMETER_CONFIG["Peroksit Degeri"]["is_individual"]).
PEROXIDE_PRODUCT_RANGES = {
    "Zeytinyagi (naturel sizma)": (None, 20.0),  # Codex Alimentarius/IOC standardi
    "Aycicek yagi (rafine)": (None, 10.0),
    "Ozel/Manuel gir": None,
}

# Gosterge amacli HMF (Hidroksimetilfurfural, mg/kg) UST limiti. Isil islem/
# depolama sirasinda sekerlerin bozunmasinin gostergesi - sadece USL
# anlamlidir. Kaynak: TGK Bal Tebligi (bal), TGK Uzum Pekmezi Tebligi
# (pekmez), genel sektor pratigi (meyve suyu konsantresi). I-MR chart
# kullanilir (alt grup yok, her olcum tek bir parti sonucu).
HMF_PRODUCT_RANGES = {
    "Bal": (None, 40.0),  # TGK Bal Tebligi
    "Pekmez (sivi)": (None, 75.0),  # TGK Uzum Pekmezi Tebligi
    "Pekmez (kati)": (None, 100.0),  # TGK Uzum Pekmezi Tebligi
    "Meyve suyu (konsantre)": (None, 20.0),  # genel sektor pratigi
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
        "demo_shift_amount": 0.35,
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
        "demo_shift_amount": 0.35,
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
        # NOT: aw 0-1 arasi bir olcektir; pH/Brix'te kullanilan 0.35'lik
        # kaydirma burada 0.85+0.35=1.2 gibi FIZIKSEL OLARAK IMKANSIZ (aw>1)
        # bir demo degeri uretiyordu - bu hatanin kok nedeniydi. 0.05, tipik
        # sigma'ya (~0.007) gore hala belirgin sekilde kontrol disi ama 1.0'i
        # asmayan bir kaydirma sagliyor (0.85+0.05=0.90).
        "demo_shift_amount": 0.05,
        "one_sided": True,
    },
    "Viskozite": {
        "unit": "cP",
        "min_value": 0.0,
        "max_value": 300000.0,
        "products": VISCOSITY_PRODUCT_RANGES,
        "default_lsl": 40000.0,
        "default_usl": 60000.0,
        "default_measurement": 50000.0,
        "demo_target_mean": 50000.0,
        "demo_target_sigma": 3000.0,  # I-MR demo icin dogrudan std sapma (R_bar/d2 degil)
        "one_sided": False,
        "is_individual": True,  # X-bar/R degil, I-MR chart kullanilir (alt grup yok)
    },
    "Nem/Rutubet": {
        "unit": "%",
        "min_value": 0.0,
        "max_value": 100.0,
        "products": MOISTURE_PRODUCT_RANGES,
        "default_lsl": 35.0,
        "default_usl": 40.0,
        "default_measurement": 37.5,
        "demo_target_mean": 37.5,
        "demo_target_r_bar": 0.5,
        "demo_shift_amount": 2.0,
        "one_sided": False,  # "Ozel/Manuel gir" icin varsayilan; urun bazinda override edilebilir (bkz. Bal)
    },
    "Tuz/NaCl": {
        "unit": "%",
        "min_value": 0.0,
        "max_value": 20.0,
        "products": SALT_PRODUCT_RANGES,
        "default_lsl": 1.5,
        "default_usl": 2.0,
        "default_measurement": 1.75,
        "demo_target_mean": 1.75,
        "demo_target_r_bar": 0.05,
        "demo_shift_amount": 0.3,
        "one_sided": False,
    },
    "Titrasyon Asitligi": {
        "unit": "%",
        "min_value": 0.0,
        "max_value": 5.0,
        "products": TITRATABLE_ACIDITY_PRODUCT_RANGES,
        "default_lsl": 0.14,
        "default_usl": 0.16,
        "default_measurement": 0.15,
        "demo_target_mean": 0.15,
        "demo_target_r_bar": 0.005,
        "demo_shift_amount": 0.03,
        "one_sided": False,
    },
    "Peroksit Degeri": {
        "unit": "meq O2/kg",
        "min_value": 0.0,
        "max_value": 50.0,
        "products": PEROXIDE_PRODUCT_RANGES,
        "default_lsl": 0.0,  # kullanilmiyor (one_sided=True) - sadece placeholder
        "default_usl": 20.0,
        "default_measurement": 10.0,
        "demo_target_mean": 10.0,
        "demo_target_sigma": 1.0,
        "one_sided": True,  # "Ozel/Manuel gir" icin varsayilan (tum tanimli urunler zaten tek tarafli)
        "is_individual": True,  # her olcum tek bir parti/batch sonucu - alt grup yok
    },
    "HMF": {
        "unit": "mg/kg",
        "min_value": 0.0,
        "max_value": 150.0,
        "products": HMF_PRODUCT_RANGES,
        "default_lsl": 0.0,  # kullanilmiyor (one_sided=True) - sadece placeholder
        "default_usl": 40.0,
        "default_measurement": 20.0,
        "demo_target_mean": 20.0,
        "demo_target_sigma": 3.0,
        "one_sided": True,
        "is_individual": True,
    },
}
