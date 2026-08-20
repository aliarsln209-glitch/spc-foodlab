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
    "TPC/TMAB": "Toplam canli bakteri sayimi (KOB/g). Log-normal dagilir - grafik/Cpk log10 olceginde hesaplanir.",
    "Kuf-Maya": "Kuf ve maya sayimi (KOB/g). Log-normal dagilir - grafik/Cpk log10 olceginde hesaplanir.",
    "Koliform": "Genel hijyen/proses kontrol gostergesi (KOB/g). Log-normal dagilir - grafik/Cpk log10 olceginde hesaplanir.",
    "Enterobacteriaceae": "Fekal/cevresel kontaminasyon gostergesi (KOB/g). Log-normal dagilir - grafik/Cpk log10 olceginde hesaplanir.",
    "Kantitatif S. aureus": "Staphylococcus aureus sayimi (KOB/g). Log-normal dagilir - grafik/Cpk log10 olceginde hesaplanir.",
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
    "TPC/TMAB": (
        "TPC/TMAB (Toplam Canli Sayim / Toplam Mezofilik Aerobik Bakteri), "
        "bir numunedeki genel mikrobiyal yuku KOB/g (koloni olusturan "
        "birim/gram) cinsinden olcer. Mikrobiyal sayimlar log-normal "
        "dagildigindan HAM deger yerine log10-donusturulmus deger uzerinden "
        "SPC/Cpk hesaplanir - bkz. asagidaki 'Ham/log10 seffaflik tablosu'. "
        "LOD (tespit limiti) altindaki sonuclar ICMSF/FDA BAM konvensiyonuna "
        "gore LOD/2 ile ikame edilir, bu ikame HER ZAMAN acikca gosterilir."
    ),
    "Kuf-Maya": (
        "Kuf-Maya sayimi, bir numunedeki kuf ve maya yukunu KOB/g cinsinden "
        "olcer - yuksek Kuf-Maya, urunun raf omru/depolama kosullariyla "
        "ilgili bir bozulma riskine isaret eder. TPC/TMAB ile AYNI mimari: "
        "log10-donusturulmus deger uzerinden SPC/Cpk hesaplanir, LOD-alti "
        "sonuclar LOD/2 ile ikame edilir (bkz. 'Ham/log10 seffaflik tablosu')."
    ),
    "Koliform": (
        "Koliform sayimi (KOB/g), genel hijyen/proses kontrolunun bir "
        "gostergesidir - dogrudan bir patojen olmasa da yuksek koliform "
        "sayisi uretim hijyeninde bir sorunun isareti olabilir. TPC/TMAB "
        "ile AYNI mimari: log10-donusturulmus deger uzerinden SPC/Cpk "
        "hesaplanir, LOD-alti sonuclar LOD/2 ile ikame edilir."
    ),
    "Enterobacteriaceae": (
        "Enterobacteriaceae sayimi (KOB/g), Koliform'dan daha genis bir "
        "bakteri ailesini kapsayan bir fekal/cevresel kontaminasyon "
        "gostergesidir. TPC/TMAB ile AYNI mimari: log10-donusturulmus "
        "deger uzerinden SPC/Cpk hesaplanir, LOD-alti sonuclar LOD/2 ile "
        "ikame edilir."
    ),
    "Kantitatif S. aureus": (
        "Kantitatif S. aureus sayimi (KOB/g), Staphylococcus aureus "
        "yukunu olcer - yuksek sayilar hem urun guvenligi hem de uretim "
        "hijyeni acisindan onemlidir. TPC/TMAB ile AYNI mimari (log10-"
        "donusturulmus deger, LOD/2 ikamesi); TEK fark, tipik LOD'unun "
        "diger 3 mikrobiyoloji parametresine gore DAHA YUKSEK olmasidir "
        "(ISO 6888-1 dogrudan yuzey ekimi yontemi, dokme plaka yontemine "
        "gore daha az duyarlidir - bkz. constants.py PRODUCT_RANGES notu)."
    ),
}

# "Kaynak Rozeti" (urun secildikten sonra LSL/USL'in dayandigi kaynagin kisa
# ozeti) - detayli kaynak/tolerans notlari icin bkz. METHODOLOGY.md.
# Sidebar'da parametre secicisini gruplamak icin kategoriler - (id, etiket,
# parametre listesi) uclusu. id, radio widget key'lerinde kullanilan SABIT
# (emoji/Turkce karakter icermeyen) bir kimliktir - etiket degisse bile
# session_state key'i kirilmasin diye ayri tutuldu. Vardiya secimi (X-bar/R
# alt grup akisi) bu gruplamanin DISINDA, mevcut yerinde kalir - kategoriler
# sadece 9 parametreyi (pH..HMF) gruplar.
PARAMETER_CATEGORIES = [
    ("fiziksel", "\U0001F9EA Fiziksel/Duyusal", ["pH", "Brix", "Aw", "Viskozite"]),
    ("kimyasal", "\U00002697\U0000FE0F Kimyasal Kompozisyon", ["Nem/Rutubet", "Tuz/NaCl", "Titrasyon Asitligi"]),
    ("oksidasyon", "\U0001F6E2\U0000FE0F Oksidasyon/Bozulma", ["Peroksit Degeri", "HMF"]),
    (
        "mikrobiyoloji", "\U0001F9A0 Mikrobiyoloji (kantitatif)",
        ["TPC/TMAB", "Kuf-Maya", "Koliform", "Enterobacteriaceae", "Kantitatif S. aureus"],
    ),
]

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
    "TPC/TMAB": "ICMSF (International Commission on Microbiological Specifications for Foods) genel pratigi",
    "Kuf-Maya": "ICMSF genel pratigi",
    "Koliform": "ICMSF genel pratigi",
    "Enterobacteriaceae": "ICMSF genel pratigi",
    "Kantitatif S. aureus": "ICMSF genel pratigi, ISO 6888-1 yontem notu",
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

# Gosterge amacli TPC/TMAB (Toplam Canli Sayim / Toplam Mezofilik Aerobik
# Bakteri, KOB/g - koloni olusturan birim) UST limiti. Mikrobiyal sayimlar
# LOG-NORMAL dagildigindan, LSL/USL burada HAM KOB/g olarak (kullaniciya
# tanidik olceke) tutulur - Cpk hesabindan ONCE app.py bunlari log10'a
# cevirir (bkz. PARAMETER_CONFIG["TPC/TMAB"]["is_microbio"] ve
# src/microbiology.py). Sadece USL anlamlidir (alt limit kavrami yoktur -
# az bakteri her zaman iyidir). Kaynak: ICMSF (International Commission on
# Microbiological Specifications for Foods) genel gida kategorisi
# pratiginden esinlenen GOSTERGE degerleri - resmi/zorunlu bir TGK limiti
# DEGILDIR, kullanici kendi spesifikasyonuna gore degistirmelidir.
TPC_TMAB_PRODUCT_RANGES = {
    "Pastorize sut": (None, 20000.0),
    "Cig kirmizi et (parekende)": (None, 1000000.0),
    "Hazir yemek (sogutulmus)": (None, 100000.0),
    "Meyve suyu (pastorize)": (None, 100.0),
    "Ozel/Manuel gir": None,
}

# Gosterge amacli Kuf-Maya (KOB/g) UST limiti. TPC/TMAB ile AYNI mimari/
# ayni desen (bkz. yukaridaki not) - sadece USL anlamlidir, log10 donusumu
# app.py'de yapilir. Kaynak: ICMSF genel pratigi.
YEAST_MOLD_PRODUCT_RANGES = {
    "Yogurt": (None, 100.0),
    "Recel/marmelat": (None, 1000.0),
    "Meyve suyu (pastorize)": (None, 100.0),
    "Baharat/kuru gida": (None, 10000.0),
    "Ozel/Manuel gir": None,
}

# Gosterge amacli Koliform (KOB/g) UST limiti - genel hijyen/proses
# kontrol gostergesidir (dogrudan patojen degil). Ayni mimari/desen.
COLIFORM_PRODUCT_RANGES = {
    "Pastorize sut": (None, 10.0),
    "Icme suyu/proses suyu": (None, 1.0),
    "Hazir yemek (sogutulmus)": (None, 100.0),
    "Ozel/Manuel gir": None,
}

# Gosterge amacli Enterobacteriaceae (KOB/g) UST limiti - Koliform'dan
# daha genis bir aile (fekal/cevresel kontaminasyonun genel gostergesi).
# Ayni mimari/desen.
ENTEROBACTERIACEAE_PRODUCT_RANGES = {
    "Pastorize sut": (None, 10.0),
    "Hazir yemek (sogutulmus)": (None, 100.0),
    "Toz formul/bebek maması": (None, 3.0),
    "Ozel/Manuel gir": None,
}

# Gosterge amacli KANTITATIF S. aureus (KOB/g) UST limiti. DIGER 3
# mikrobiyoloji parametresiyle AYNI mimariyi (one_sided=True, sadece USL,
# log10 donusumu) kullanir - TEK fark, TIPIK LOD'unun daha YUKSEK olmasidir
# (bkz. PARAMETER_CONFIG["Kantitatif S. aureus"]["default_lod"] notu):
# yontem farkindan kaynaklanir (ISO 6888-1 dogrudan yuzey ekimi, TPC/Kuf-
# Maya/Koliform/Enterobacteriaceae'nin tipik dokme plaka yontemine gore
# daha az duyarlidir). Limit yapisi (one_sided/two_sided) AYNIDIR, FARKLI
# DEGILDIR.
STAPH_AUREUS_PRODUCT_RANGES = {
    "Hazir yemek (sogutulmus)": (None, 100.0),
    "Peynir (olgunlasmamis)": (None, 1000.0),
    "Et urunleri (isil islem gormus)": (None, 100.0),
    "Ozel/Manuel gir": None,
}

# --- Hammadde Kutuphanesi (v1.1.1) -----------------------------------------
# Bitmiş urun spesifikasyonlarindan (yukaridaki PRODUCT_*_RANGES) AYRI bir
# kategori: hammadde QC referanslari. Bitmiş urun tablolari TGK/sektor
# pratigine dayanip cogu zaman dogrudan urun tebligleriyle eslesirken,
# hammadde girdileri buyuk olcude ayri arastirmayla (web arama, TGK
# tebligleri, JECFA/Codex monograflari) toplandi ve COGUNUN sayisal
# kaynagi DOGRULANAMADI - bu durumda range=None birakildi (kullanici
# "Ozel/Manuel gir" davranisiyla kendi degerini girer, UYDURMA SAYI
# KONULMADI). "source"/"note" alanlari her hammadde-parametre ciftinin
# durumunu (dogrulandi / kaynak bulunamadi) app.py'de kullaniciya gosterir.
# Detay ve tam kaynak listesi icin bkz. METHODOLOGY.md "Hammadde
# Kutuphanesi Genislemesi".
RAW_MATERIAL_PREFIX = "\U0001F33E "  # 🌾 - secim listesinde bitmiş urunlerden gorsel ayrim

RAW_MATERIAL_QC_REFERENCE = {
    "Bugday unu": {
        "Nem/Rutubet": {
            "range": (None, 14.5),
            "source": "TGK Bugday Unu Tebligi (No: 2013/9)",
            "verified": "kismi",  # arama motoru snippet'i ile dogrulandi, tam metin taranmis PDF oldugu icin tablo dogrudan okunamadi
            "note": None,
        },
        "Aw": {"range": None, "source": None, "verified": False, "note": None},
        "pH": {"range": None, "source": None, "verified": False, "note": None},
    },
    "Sut tozu": {
        "Nem/Rutubet": {
            "range": None,
            "source": "TGK Fermente Sut Urunleri Tebligi (No: 2022/44) - 'toz fermente sut urunu' tanimindan; klasik sut tozu icin ayri tebligi bulunamadi",
            "verified": False,  # yanlis urun kategorisinden gelme riski var, sayi kullanilmadi
            "note": None,
        },
        "Aw": {"range": None, "source": None, "verified": False, "note": None},
        "pH": {"range": None, "source": None, "verified": False, "note": None},
        "Tuz/NaCl": {"range": None, "source": None, "verified": False, "note": "Opsiyonel olcum."},
        "Titrasyon Asitligi": {"range": None, "source": None, "verified": False, "note": "Opsiyonel olcum."},
    },
    "Glikoz surubu": {
        "Brix": {"range": None, "source": "TGK Seker Tebligi (No: 2022/10) glikoz surubunu tanimliyor, sayisal tablo dogrulanamadi", "verified": False, "note": None},
        "Viskozite": {"range": None, "source": None, "verified": False, "note": "Olcum kosullari (sicaklik, kayma hizi) urune/tesise bagli."},
        "pH": {"range": None, "source": None, "verified": False, "note": None},
        "Aw": {"range": None, "source": None, "verified": False, "note": None},
        "Nem/Rutubet": {"range": None, "source": None, "verified": False, "note": None},
        "Titrasyon Asitligi": {"range": None, "source": None, "verified": False, "note": "Opsiyonel olcum."},
    },
    "Maltodekstrin": {
        "Nem/Rutubet": {"range": None, "source": "JECFA/FCC genel tanimi tipik ~%5 nem belirtiyor, spesifik monograf sayisi dogrulanamadi", "verified": False, "note": None},
        "Aw": {"range": None, "source": None, "verified": False, "note": None},
        "Brix": {"range": None, "source": None, "verified": False, "note": "Toz halde dogrudan olculmez - cozelti hazirlanarak yapilan olcumdur, metodoloji standardize edilmelidir."},
        "Viskozite": {"range": None, "source": None, "verified": False, "note": "Opsiyonel; cozelti/surup halinde olculur."},
    },
    "Maltitol": {
        "Nem/Rutubet": {"range": None, "source": "JECFA Food Additives Series 40 'Maltitol syrup' monografi mevcut, sayisal loss-on-drying degeri dogrulanamadi", "verified": False, "note": None},
        "Aw": {"range": None, "source": None, "verified": False, "note": None},
        "Brix": {"range": None, "source": None, "verified": False, "note": "Toz halde dogrudan olculmez - cozelti hazirlanarak yapilan olcumdur."},
        "Viskozite": {"range": None, "source": None, "verified": False, "note": "Opsiyonel; cozelti/surup halinde olculur."},
    },
    "Nisasta": {
        "Nem/Rutubet": {"range": None, "source": "Ayri bir 'TGK Nisasta Tebligi' tespit edilemedi", "verified": False, "note": None},
        "Aw": {"range": None, "source": None, "verified": False, "note": None},
        "pH": {"range": None, "source": None, "verified": False, "note": "Opsiyonel olcum."},
    },
    "Bitkisel yag": {
        "Peroksit Degeri": {
            "range": None,
            "source": "TGK Bitki Adi ile Anilan Yaglar Tebligi (No: 2012/29, degisiklik No: 2026/14) peroksit degeri limiti iceriyor, sayisal meq O2/kg degeri metinden dogrulanamadi",
            "verified": False,
            "note": None,
        },
        "Viskozite": {"range": None, "source": None, "verified": False, "note": "Mevzuatta genelde zorunlu spesifikasyon degil, isletme ici QC parametresidir."},
    },
    "Peynir alti suyu tozu": {
        "Nem/Rutubet": {
            "range": (None, 5.0),
            "source": "TGK Peynir Tebligi (No: 2015/6)",
            "verified": True,
            "note": None,
        },
        "Aw": {"range": None, "source": None, "verified": False, "note": None},
        "pH": {"range": None, "source": None, "verified": False, "note": None},
        "Tuz/NaCl": {"range": None, "source": None, "verified": False, "note": "Opsiyonel olcum."},
        "Titrasyon Asitligi": {"range": None, "source": None, "verified": False, "note": "Opsiyonel olcum."},
    },
    "Kakao tozu": {
        "Nem/Rutubet": {
            "range": (None, 9.0),
            "source": "TGK Kakao ve Cikolata Urunleri Tebligi (No: 2017/29)",
            "verified": True,
            "note": None,
        },
        "Aw": {"range": None, "source": None, "verified": False, "note": None},
        "pH": {"range": None, "source": None, "verified": False, "note": "Opsiyonel olcum."},
    },
    "Toz seker": {
        "Nem/Rutubet": {"range": None, "source": "TGK Seker Tebligi (No: 2022/10) 'Bilesim ve Kalite Ozellikleri' bolumunde olabilir, sayisal deger metinden dogrulanamadi", "verified": False, "note": None},
        "Brix": {"range": None, "source": None, "verified": False, "note": "Toz halde dogrudan olculmez - cozelti hazirlanarak yapilan olcumdur, metodoloji standardize edilmelidir."},
        "Aw": {"range": None, "source": None, "verified": False, "note": "Opsiyonel olcum."},
    },
    "Fruktoz": {
        "Nem/Rutubet": {"range": None, "source": "TGK Seker Tebligi (No: 2022/10) fruktozu kapsiyor, sayisal nem limiti dogrulanamadi", "verified": False, "note": None},
        "Brix": {"range": None, "source": None, "verified": False, "note": "Toz halde dogrudan olculmez - cozelti hazirlanarak yapilan olcumdur, metodoloji standardize edilmelidir."},
        "Aw": {"range": None, "source": None, "verified": False, "note": "Opsiyonel olcum."},
    },
    "Pektin": {
        "Nem/Rutubet": {"range": None, "source": "JECFA/Codex GSFA Pectins (INS 440) monografinda 'loss on drying' spesifikasyonu bulunuyor, sayisal deger dogrulanamadi", "verified": False, "note": None},
        "Aw": {"range": None, "source": None, "verified": False, "note": None},
        "Viskozite": {"range": None, "source": None, "verified": False, "note": "Dogrudan olculmez - standart cozelti/jel sisteminde olculur, kosullar tesise gore degisir."},
        "pH": {"range": None, "source": None, "verified": False, "note": "Opsiyonel olcum."},
    },
    "Jelatin": {
        "Nem/Rutubet": {"range": None, "source": "Ayri bir 'TGK Jelatin Tebligi' tespit edilemedi", "verified": False, "note": None},
        "Aw": {"range": None, "source": None, "verified": False, "note": None},
        "Viskozite": {"range": None, "source": None, "verified": False, "note": "Dogrudan olculmez - standart cozelti/jel sisteminde olculur, kosullar tesise gore degisir."},
        "pH": {"range": None, "source": None, "verified": False, "note": "Opsiyonel olcum."},
    },
    "Konsantre meyve suyu": {
        "Brix": {"range": None, "source": "TGK Meyve Suyu ve Benzeri Urunler Tebligi mevcut, sayisal Brix tablosu dogrulanamadi", "verified": False, "note": None},
        "pH": {"range": None, "source": None, "verified": False, "note": None},
        "Viskozite": {"range": None, "source": None, "verified": False, "note": "Olcum kosullari urune (meyve turu, konsantrasyon) baglidir."},
        "Titrasyon Asitligi": {"range": None, "source": None, "verified": False, "note": None},
        "HMF": {
            "range": None,
            "source": None,
            "verified": False,
            "note": (
                "ONEMLI: HMF limiti meyve suyu urun tipine (elma/uzum/portakal vb.) "
                "gore degisir; genel/tek bir mevzuat limiti bulunamadi. Bal (TGK Bal "
                "Tebligi, USL=40 mg/kg) veya pekmez (TGK Pekmez Tebligi) limitleri "
                "BURAYA UYGULANMAMALIDIR - farkli urun kategorileridir."
            ),
        },
    },
    "Yumurta tozu": {
        "Nem/Rutubet": {"range": None, "source": "TGK Yumurta ve Yumurta Urunleri Tebligi (2024/7) mevcut, sayisal tablo taranmis PDF'lerden dogrulanamadi", "verified": False, "note": None},
        "Aw": {"range": None, "source": None, "verified": False, "note": None},
        "Peroksit Degeri": {"range": None, "source": None, "verified": False, "note": None},
        "pH": {"range": None, "source": None, "verified": False, "note": "Opsiyonel olcum."},
        "Titrasyon Asitligi": {"range": None, "source": None, "verified": False, "note": "Opsiyonel olcum."},
    },
    "Tuz": {
        "Tuz/NaCl": {
            "range": (98.0, 100.0),
            "source": (
                "TGK Tuz Tebligi (No: 2013/48) - LSL: kuru maddede NaCl orani "
                "en az %98 (kayatuzu/yeralti kaynakli tuzda %97); USL=100.0 "
                "mevzuattan degil, yuzdenin matematiksel ust siniridir (tebligde "
                "bir ust limit belirtilmez)."
            ),
            "verified": True,
            "note": None,
        },
        "Aw": {"range": None, "source": None, "verified": False, "note": "Opsiyonel olcum."},
    },
}

# Yukaridaki referansi ilgili PRODUCT_*_RANGES sozluklerine enjekte eder -
# her hammadde, sadece PARAMETRE EŞLEŞTİRMESİ tablosunda tanimlandigi
# parametrenin urun listesine "🌾 " onekiyle eklenir (baska parametrede
# GORUNMEZ - "hammadde secilince parametre filtrelenir" gereksinimi boylece
# ayri bir filtreleme mantigi yazmadan, mevcut parametre-once-urun mimarisi
# ile saglanmis olur). "Ozel/Manuel gir" her zaman listenin sonunda kalsin
# diye once cikarilip enjeksiyondan sonra geri eklenir.
_RAW_MATERIAL_TARGET_DICTS = {
    "pH": PRODUCT_PH_RANGES,
    "Brix": BRIX_PRODUCT_RANGES,
    "Aw": AW_PRODUCT_RANGES,
    "Viskozite": VISCOSITY_PRODUCT_RANGES,
    "Nem/Rutubet": MOISTURE_PRODUCT_RANGES,
    "Tuz/NaCl": SALT_PRODUCT_RANGES,
    "Titrasyon Asitligi": TITRATABLE_ACIDITY_PRODUCT_RANGES,
    "Peroksit Degeri": PEROXIDE_PRODUCT_RANGES,
    "HMF": HMF_PRODUCT_RANGES,
}

for _target in _RAW_MATERIAL_TARGET_DICTS.values():
    _target.pop("Ozel/Manuel gir", None)

for _material, _params in RAW_MATERIAL_QC_REFERENCE.items():
    for _param_name, _spec in _params.items():
        _RAW_MATERIAL_TARGET_DICTS[_param_name][f"{RAW_MATERIAL_PREFIX}{_material}"] = _spec["range"]

for _target in _RAW_MATERIAL_TARGET_DICTS.values():
    _target["Ozel/Manuel gir"] = None

del _target, _material, _params, _param_name, _spec


# Parametre bazli yapilandirma - Sekme 2'deki urun/birim/aralik mantigi buna gore dallanir.
PARAMETER_CONFIG = {
    "pH": {
        "unit": "pH",
        "min_value": 0.0,
        "max_value": 14.0,
        "decimal_places": 2,  # tipik pH metre hassasiyeti (orn. 4.55)
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
        "decimal_places": 1,  # tipik refraktometre hassasiyeti (orn. 12.5)
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
        "decimal_places": 3,  # tipik aw metre hassasiyeti (orn. 0.850)
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
        "decimal_places": 0,  # viskozimetre olcumleri buyuk tam sayilar (orn. 50000 cP)
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
        "decimal_places": 1,  # tipik nem tayin cihazi hassasiyeti (orn. 37.5)
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
        # NOT: bitmiş urunlerde tuz orani tipik olarak %0-10 arasindayken, "Tuz"
        # HAMMADDESININ kendisi (RAW_MATERIAL_QC_REFERENCE) %98-100 NaCl saflik
        # araliginda olabilir - bu yuzden max_value 20'den 100'e cikarildi.
        # Mevcut bitmiş urun degerleri (1.5-10 arasi) bu degisiklikten etkilenmez.
        "max_value": 100.0,
        "decimal_places": 2,  # tipik titrasyon/klorur analizi hassasiyeti (orn. 1.75)
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
        "decimal_places": 2,  # tipik titrasyon hassasiyeti (orn. 0.15)
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
        "decimal_places": 1,  # tipik titrasyon hassasiyeti (orn. 5.2)
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
        "decimal_places": 1,  # tipik HPLC/spektrofotometrik olcum hassasiyeti (orn. 18.4)
        "products": HMF_PRODUCT_RANGES,
        "default_lsl": 0.0,  # kullanilmiyor (one_sided=True) - sadece placeholder
        "default_usl": 40.0,
        "default_measurement": 20.0,
        "demo_target_mean": 20.0,
        "demo_target_sigma": 3.0,
        "one_sided": True,
        "is_individual": True,
    },
    "TPC/TMAB": {
        "unit": "KOB/g",
        # min_value=1.0 (0 DEGIL): 0 KOB/g log10-tanimsizdir (log10(0) yok) -
        # gercek "hic bakteri tespit edilemedi" durumu HAM SIFIR olarak degil,
        # "Bu deger LOD altinda" checkbox'i ile ayrica modellenir (bkz.
        # src/microbiology.py substitute_below_lod).
        "min_value": 1.0,
        "max_value": 10_000_000.0,
        "decimal_places": 0,  # ham KOB/g tam sayidir; log10 goruntusu ayri decimal_places (asagida) kullanir
        "products": TPC_TMAB_PRODUCT_RANGES,
        "default_lsl": 0.0,  # kullanilmiyor (one_sided=True) - sadece placeholder
        "default_usl": 100000.0,
        "default_measurement": 1000.0,
        # demo_target_mean DIGER parametrelerle AYNI sekilde HAM KOB/g'dir
        # (urun senaryosu secildiginde demo_scenario_targets() de HAM
        # olcekte bir ortalama uretir - bkz. result_helpers.py) - app.py demo
        # yukleme kodu bunu generate_demo_individual'a vermeden ONCE log10'a
        # cevirir. demo_target_sigma ise (RAW spread'in aksine) DOGRUDAN
        # LOG10 OLCEGINDE SABIT bir sigma'dir - urun senaryosunun HAM
        # spread'i (araligin genisligine bagli) log-normal dagilimda dogal
        # bir karsiliga sahip olmadigindan BILEREK kullanilmaz; bu, ilk
        # adimda (TPC/TMAB) kabul edilen bir sadelestirmedir.
        "demo_target_mean": 1000.0,
        "demo_target_sigma": 0.3,  # log10 olceginde sabit sigma
        "one_sided": True,
        "is_individual": True,
        "is_microbio": True,
        "default_lod": 10.0,  # KOB/g - kullanici LOD alaninda degistirebilir
        "log_axis_label": "log10(KOB/g)",
        "log_decimal_places": 3,  # grafikte/Cpk hesap adimlarinda log10 degerler icin
    },
    "Kuf-Maya": {
        # TPC/TMAB ile BIREBIR AYNI sema/mimari - tek farklar unit disi
        # alanlarin (products/default_lsl/default_usl/default_measurement/
        # demo_target_mean) parametreye ozgu degerleridir.
        "unit": "KOB/g",
        "min_value": 1.0,
        "max_value": 10_000_000.0,
        "decimal_places": 0,
        "products": YEAST_MOLD_PRODUCT_RANGES,
        "default_lsl": 0.0,
        "default_usl": 1000.0,
        "default_measurement": 100.0,
        "demo_target_mean": 100.0,
        "demo_target_sigma": 0.3,
        "one_sided": True,
        "is_individual": True,
        "is_microbio": True,
        "default_lod": 10.0,
        "log_axis_label": "log10(KOB/g)",
        "log_decimal_places": 3,
    },
    "Koliform": {
        "unit": "KOB/g",
        "min_value": 1.0,
        "max_value": 10_000_000.0,
        "decimal_places": 0,
        "products": COLIFORM_PRODUCT_RANGES,
        "default_lsl": 0.0,
        "default_usl": 100.0,
        "default_measurement": 10.0,
        "demo_target_mean": 10.0,
        "demo_target_sigma": 0.3,
        "one_sided": True,
        "is_individual": True,
        "is_microbio": True,
        "default_lod": 10.0,
        "log_axis_label": "log10(KOB/g)",
        "log_decimal_places": 3,
    },
    "Enterobacteriaceae": {
        "unit": "KOB/g",
        "min_value": 1.0,
        "max_value": 10_000_000.0,
        "decimal_places": 0,
        "products": ENTEROBACTERIACEAE_PRODUCT_RANGES,
        "default_lsl": 0.0,
        "default_usl": 100.0,
        "default_measurement": 10.0,
        "demo_target_mean": 10.0,
        "demo_target_sigma": 0.3,
        "one_sided": True,
        "is_individual": True,
        "is_microbio": True,
        "default_lod": 10.0,
        "log_axis_label": "log10(KOB/g)",
        "log_decimal_places": 3,
    },
    "Kantitatif S. aureus": {
        "unit": "KOB/g",
        "min_value": 1.0,
        "max_value": 10_000_000.0,
        "decimal_places": 0,
        "products": STAPH_AUREUS_PRODUCT_RANGES,
        "default_lsl": 0.0,
        "default_usl": 1000.0,
        "default_measurement": 100.0,
        "demo_target_mean": 100.0,
        "demo_target_sigma": 0.3,
        "one_sided": True,  # DIGER 3 mikrobiyoloji parametresiyle AYNI - limit yapisi FARKLI DEGIL
        "is_individual": True,
        "is_microbio": True,
        # TEK parametreye-ozgu fark: tipik LOD DAHA YUKSEK (100 vs 10) -
        # ISO 6888-1 dogrudan yuzey ekimi yonteminin tipik duyarliligi,
        # TPC/Kuf-Maya/Koliform/Enterobacteriaceae'nin dokme plaka
        # yontemine gore daha dusuktur (bkz. constants.py PRODUCT_RANGES
        # notu ve PARAMETER_INFO).
        "default_lod": 100.0,
        "log_axis_label": "log10(KOB/g)",
        "log_decimal_places": 3,
    },
}


# --- v1.4 Parameter Framework (Food Quality Parameters, fazli) --------------
# Faz 1/2/3'te eklenecek yeni parametreler (Protein, Yag, Kul, Kuru Madde,
# Yogunluk, Refraktif Indeks, L*/a*/b*, Bulaniklik, Iletkenlik) icin ortak
# "Internal Parameter Registry" semasi (bkz. METHODOLOGY.md "v1.4 -> v1.6 -
# Food Quality Parameters (fazli)"). Legacy PARAMETER_CONFIG (pH..Kantitatif
# S. aureus) BILEREK bu semaya retrofit EDILMEDI - onlarin kendi
# PARAMETER_CATEGORIES gruplamasi (4 grup: fiziksel/kimyasal/oksidasyon/
# mikrobiyoloji) zaten calisiyor; burasi FARKLI bir 3-gruplu semantik
# (Kimyasal/Fiziksel/Optik) kullandigi icin karistirilmamasi icin
# FOOD_QUALITY_PARAMETER_CONFIG ayri bir sozluk olarak tutulur.
#
# Her kayit (Faz 1'den itibaren doldurulacak) su alanlari icerir:
#   unit, decimal_places          - mevcut PARAMETER_CONFIG ile ayni anlam
#   physical_bounds: (min, max)   - LSL/USL giris siniri VE hesaplanan LCL'in
#                                    fiziksel olarak imkansiz bir degere
#                                    (orn. negatif yuzde) dusup dusmedigini
#                                    kontrol etmek icin kullanilir (bkz.
#                                    check_physical_bound_breach(), asagida
#                                    result_helpers.py'ye tasindi)
#   recommended_chart: "auto"     - sabit bir chart turu DAYATILMAZ; kullanici
#                                    subgroup_guidance metnine gore kendi
#                                    laboratuvar pratigine uygun olani secer
#   subgroup_guidance: str        - serbest metin, hangi chart'in NEDEN uygun
#                                    olabilecegine dair yonlendirme (orn.
#                                    Protein icin "genellikle I-MR, alt grup
#                                    alinabiliyorsa X-bar/R da uygun")
#   method_source: str            - AOAC/ISO metodolojisi + LSL/USL kaynagi
#   category: str                 - "Kimyasal" | "Fiziksel" | "Optik" - bu
#                                    UCUNUN disina cikilmaz, Food Quality
#                                    Parameters'a OZGU bir gruplamadir
FOOD_QUALITY_CATEGORIES = ["Kimyasal", "Fiziksel", "Optik"]

# Baslangic sirasi adim 3 (bkz. METHODOLOGY.md v1.4 Faz 1): LSL/USL kaynak
# arastirmasi tamamlandi. Asagidaki urun tablolari SADECE dogrulanmis TGK
# tebligi kaynagina dayanir (tam metin okunarak, snippet'ten DEGIL - bkz. her
# tablonun ustundeki not) - dogrulanamayan urun/parametre kombinasyonlari
# icin (Hammadde Kutuphanesi ile AYNI disiplin) sayi UYDURULMADI, "Ozel/
# Manuel gir"e birakildi. default_lsl/default_usl (urun secilmeden onceki
# baslangic degeri) HERHANGI BIR tek kaynaga dayanmaz, genis/genel bir
# baslangic araligidir - bu, mevcut pH/Brix parametrelerinin default_lsl/usl
# alanlarindaki desenle AYNIDIR.

# Protein (%) - kuru maddede minimum protein orani. Kaynak: TGK Bugday Unu
# Tebligi (Tebligg No: 99/1, 17.02.1999 R.G. 23614) Madde 5/d - TAM METIN
# okunarak dogrulandi (bu tebligin sonraki surumu 2013/9 muhtemelen ayni
# degerleri korur, ama 2013/9'un TAM METNI dogrudan dogrulanamadi - bu
# yuzden kaynak olarak 99/1 belirtilir, bkz. RAW_MATERIAL_QC_REFERENCE'daki
# "Bugday unu" notuyla AYNI durum). Protein icin sadece ALT limit (minimum)
# tanimlidir - TGK ust limit vermez; mevcut spc_core.py mimarisi SADECE
# "one_sided=USL-only" (Cpu) durumunu destekler, "LSL-only" (Cpl) YOKTUR -
# bu yuzden USL=100.0 MATEMATIKSEL TAVAN olarak eklenir (RAW_MATERIAL_
# QC_REFERENCE'daki "Tuz" girisiyle AYNI desen - mevzuattan degil, yuzdenin
# fiziksel ust siniridir).
PROTEIN_PRODUCT_RANGES = {
    "Bugday unu (ekmeklik)": (10.5, 100.0),
    "Bugday unu (ozel amacli)": (7.0, 100.0),
    "Ozel/Manuel gir": None,
}

# Yag (%) - sut yagi esasli surulebilir urunler. Kaynak: TGK Tereyagi, Diger
# Sut Yagi Esasli Surulebilir Urunler ve Sadeyag Tebligi (Tebligg No:
# 2005/19, 12.04.2005 R.G. 25784), Ek tablosu - TAM METIN okunarak
# dogrulandi (agirlikca % sut yagi). Sadeyag icin tebligde sadece ALT limit
# (%99'dan az olmayan) tanimlidir - Protein'deki AYNI mantikla USL=100.0
# matematiksel tavan olarak eklendi.
YAG_PRODUCT_RANGES = {
    "Tereyagi": (80.0, 90.0),
    "Yarim yagli tereyagi": (39.0, 41.0),
    "Sadeyag": (99.0, 100.0),
    "Ozel/Manuel gir": None,
}

# Kul (%) - buğday ununda kuru maddede maksimum kul orani. Kaynak: TGK
# Bugday Unu Tebligi (99/1) Madde 5/c - TAM METIN okunarak dogrulandi. Kul
# HER ZAMAN bir UST limit spesifikasyonudur (dusuk kul = daha az kepek
# karisimi/daha rafine un) - Peroksit Degeri/HMF ile AYNI mimari (mevcut
# one_sided=True/USL-only sema DOGRUDAN uyuyor, matematiksel tavan hilesine
# GEREK YOK).
KUL_PRODUCT_RANGES = {
    "Bugday unu (Tip 550)": (None, 0.55),
    "Bugday unu (Tip 650)": (None, 0.65),
    "Bugday unu (Tip 850)": (None, 0.85),
    "Ozel/Manuel gir": None,
}

# Kuru Madde (%) - reçel/marmelat urunlerinde refraktometre ile olculen
# COZUNEBILIR kuru madde (Brix'e yakin bir olcum, ama Kuru Madde parametresi
# GENEL bir % olarak burada tutulur - Brix parametresinden AYRIDIR, cunku
# Kuru Madde parametresi gelecekte reçel disi urunlerde de (orn. sut tozu,
# unlu mamuller) kullanilabilecek genel bir alan). Kaynak: TGK Recel, Jole,
# Marmelat ve Tatlandirilmis Kestane Puresi Tebligi (Tebligg No: 2006/55)
# Madde 5 - TAM METIN okunarak dogrulandi. Sadece ALT limit (minimum
# cozunebilir kuru madde) tanimlidir - Protein/Yag'daki AYNI matematiksel
# tavan (USL=100.0) hilesi burada da uygulanir.
KURU_MADDE_PRODUCT_RANGES = {
    "Recel (geleneksel)": (68.0, 100.0),
    "Marmelat (geleneksel)": (55.0, 100.0),
    "Ozel/Manuel gir": None,
}

FOOD_QUALITY_PARAMETER_CONFIG: dict = {
    "Protein": {
        "unit": "%",
        "min_value": 0.0,
        "max_value": 100.0,
        "decimal_places": 2,
        "products": PROTEIN_PRODUCT_RANGES,
        "default_lsl": 10.0,
        "default_usl": 30.0,
        "default_measurement": 20.0,
        "demo_target_mean": 20.0,
        "demo_target_sigma": 2.0,
        "one_sided": False,
        "is_individual": True,  # tahribatli/tekil analiz (Kjeldahl/Dumas tipi yontemler) - bkz. subgroup_guidance
        "physical_bounds": (0.0, 100.0),
        "recommended_chart": "auto",
        "subgroup_guidance": (
            "Genellikle I-MR (tahribatli/tekil analiz), ancak alt grup "
            "alinabiliyorsa X-bar/R da uygundur."
        ),
        "method_source": "TGK Bugday Unu Tebligi (No: 99/1) Madde 5/d - kuru maddede minimum protein (bkz. constants.py PROTEIN_PRODUCT_RANGES notu).",
        "category": "Kimyasal",
        "placeholder": False,
    },
    "Yag": {
        "unit": "%",
        "min_value": 0.0,
        "max_value": 100.0,
        "decimal_places": 2,
        "products": YAG_PRODUCT_RANGES,
        "default_lsl": 0.5,
        "default_usl": 40.0,
        "default_measurement": 20.0,
        "demo_target_mean": 20.0,
        "demo_target_sigma": 2.0,
        "one_sided": False,
        "is_individual": True,
        "physical_bounds": (0.0, 100.0),
        "recommended_chart": "auto",
        "subgroup_guidance": (
            "Genellikle I-MR (Soxhlet/Gerber tipi tahribatli tekil analiz), "
            "ancak alt grup alinabiliyorsa X-bar/R da uygundur."
        ),
        "method_source": "TGK Tereyagi, Diger Sut Yagi Esasli Surulebilir Urunler ve Sadeyag Tebligi (No: 2005/19), Ek tablosu (bkz. constants.py YAG_PRODUCT_RANGES notu).",
        "category": "Kimyasal",
        "placeholder": False,
    },
    "Kul": {
        "unit": "%",
        "min_value": 0.0,
        "max_value": 100.0,
        "decimal_places": 2,
        "products": KUL_PRODUCT_RANGES,
        "default_lsl": 0.0,  # kullanilmiyor (one_sided=True) - sadece placeholder
        "default_usl": 5.0,
        "default_measurement": 2.0,
        "demo_target_mean": 2.0,
        "demo_target_sigma": 0.3,
        "one_sided": True,  # kul HER ZAMAN bir ust limit spesifikasyonudur
        "is_individual": True,
        "physical_bounds": (0.0, 100.0),
        "recommended_chart": "auto",
        "subgroup_guidance": (
            "Genellikle I-MR (firinlama/kul firinini gerektiren tahribatli "
            "tekil analiz), ancak alt grup alinabiliyorsa X-bar/R da uygundur."
        ),
        "method_source": "TGK Bugday Unu Tebligi (No: 99/1) Madde 5/c - kuru maddede maksimum kul (bkz. constants.py KUL_PRODUCT_RANGES notu).",
        "category": "Kimyasal",
        "placeholder": False,
    },
    "Kuru Madde": {
        "unit": "%",
        "min_value": 0.0,
        "max_value": 100.0,
        "decimal_places": 2,
        "products": KURU_MADDE_PRODUCT_RANGES,
        "default_lsl": 10.0,
        "default_usl": 95.0,
        "default_measurement": 90.0,
        "demo_target_mean": 90.0,
        "demo_target_sigma": 1.5,
        "one_sided": False,
        "is_individual": True,
        "physical_bounds": (0.0, 100.0),
        "recommended_chart": "auto",
        "subgroup_guidance": (
            "Genellikle I-MR (nem tayininden turetilen tahribatli tekil "
            "analiz), ancak alt grup alinabiliyorsa X-bar/R da uygundur."
        ),
        "method_source": "TGK Recel, Jole, Marmelat ve Tatlandirilmis Kestane Puresi Tebligi (No: 2006/55) Madde 5 - refraktometre ile cozunebilir kuru madde (bkz. constants.py KURU_MADDE_PRODUCT_RANGES notu).",
        "category": "Fiziksel",
        "placeholder": False,
    },
}

# --- Faz 2 (v1.5): Yogunluk, Refraktif Indeks -------------------------------
# Kaynak: TGK Yemeklik Zeytinyagi ve Yemeklik Prina Yagi Tebligi (Tebligg No:
# 98/7, 25.04.1998 R.G. 23323), EK-1 "Saflik Kriterleri" 2.1 (Yogunluk) ve 2.2
# (Kirilma Indisi) - TAM METIN okunarak dogrulandi (madde numaralari dahil).
# Her iki ozellik de tebligde IKI TARAFLI (min-max) araliktir - matematiksel
# tavan hilesine GEREK YOK (Protein/Kuru Madde'deki LSL-only durumunun
# AKSINE).
YOGUNLUK_PRODUCT_RANGES = {
    "Zeytinyagi (naturel/rafine/riviera, 20C/20C su)": (0.910, 0.916),
    "Ozel/Manuel gir": None,
}

REFRAKTIF_INDEKS_PRODUCT_RANGES = {
    "Zeytinyagi (naturel/rafine/riviera, nD 20C)": (1.4677, 1.4700),
    "Zeytinyagi (karma prina yagi, nD 20C)": (1.4680, 1.4707),
    "Ozel/Manuel gir": None,
}

FOOD_QUALITY_PARAMETER_CONFIG.update({
    "Yogunluk": {
        "unit": "g/cm3",
        "min_value": 0.0,
        "max_value": 2.0,  # coğu gida sivisi/surubu icin genis bir ust sinir (bal ~1.4, seker surubu ~1.5)
        "decimal_places": 3,
        "products": YOGUNLUK_PRODUCT_RANGES,
        "default_lsl": 0.8,
        "default_usl": 1.5,
        "default_measurement": 1.0,
        "demo_target_mean": 1.0,
        "demo_target_sigma": 0.01,
        "one_sided": False,
        "is_individual": True,  # piknometre/hidrometre ile tekil olcum
        "physical_bounds": (0.0, 2.0),
        "recommended_chart": "auto",
        "subgroup_guidance": (
            "Genellikle I-MR (piknometre/hidrometre ile tekil olcum), ancak "
            "alt grup alinabiliyorsa X-bar/R da uygundur."
        ),
        "method_source": "TGK Yemeklik Zeytinyagi ve Yemeklik Prina Yagi Tebligi (No: 98/7), Ek-1 Madde 2.1 (bkz. constants.py YOGUNLUK_PRODUCT_RANGES notu).",
        "category": "Fiziksel",
        "placeholder": False,
    },
    "Refraktif Indeks": {
        "unit": "nD",
        "min_value": 1.333,  # su - fiziksel alt sinir (bkz. METHODOLOGY.md v1.5 notu)
        "max_value": 1.7,
        "decimal_places": 4,  # tipik refraktometre hassasiyeti (orn. 1.4690)
        "products": REFRAKTIF_INDEKS_PRODUCT_RANGES,
        "default_lsl": 1.40,
        "default_usl": 1.50,
        "default_measurement": 1.45,
        "demo_target_mean": 1.45,
        "demo_target_sigma": 0.001,
        "one_sided": False,
        "is_individual": True,  # Abbe refraktometre ile tekil olcum
        "physical_bounds": (1.333, 1.7),
        "recommended_chart": "auto",
        "subgroup_guidance": (
            "Genellikle I-MR (Abbe refraktometre ile tekil olcum), ancak alt "
            "grup alinabiliyorsa X-bar/R da uygundur."
        ),
        "method_source": "TGK Yemeklik Zeytinyagi ve Yemeklik Prina Yagi Tebligi (No: 98/7), Ek-1 Madde 2.2 (bkz. constants.py REFRAKTIF_INDEKS_PRODUCT_RANGES notu).",
        "category": "Fiziksel",
        "placeholder": False,
    },
})

# --- Faz 3 (v1.6): L*, a*, b*, Bulaniklik, Iletkenlik -----------------------
# KAYNAK ARASTIRMASI SONUCU: bu 5 parametre icin TGK/Codex/JECFA kaynakli,
# GIDA URUNUNE OZGU (icme suyu potabilite yonetmeligi DEGIL - farkli baglam,
# bkz. asagidaki not) dogrulanmis bir sayisal limit BULUNAMADI - rengin
# (L*/a*/b*) cogu gida urununde mevzuat DEGIL, isletme-ici/musteri-spesifik
# bir kalite hedefi olmasi beklenen bir durumdur; Bulaniklik/Iletkenlik icin
# de benzer sekilde urune ozgu resmi bir tebliğ limiti bulunamadi. Bu yuzden
# TUMU icin "products" sozlugu SADECE "Ozel/Manuel gir" icerir - Hammadde
# Kutuphanesi'ndeki (57/61 manuel) AYNI disiplin: kaynagi dogrulanamayan
# kombinasyon icin sayi UYDURULMAZ.
#
# ARASTIRILDI AMA KULLANILMADI: İnsani Tuketim Amacli Sular Hakkinda
# Yonetmelik (iceme suyu potabilite yonetmeligi) bulaniklik/iletkenlik icin
# sayisal limitler icerir (Ek-1 tablosu) - ama bu GIDA URUNU spesifikasyonu
# DEGIL, icme suyu potabilite standardidir; farkli bir urun kategorisi/
# baglamdir (aynen METHODOLOGY.md'deki "Bal/pekmez HMF limitleri konsantre
# meyve suyuna UYGULANMAZ" ilkesiyle ayni mantik) - bu yuzden BURAYA
# TASINMADI.
L_STAR_PRODUCT_RANGES = {"Ozel/Manuel gir": None}
A_STAR_PRODUCT_RANGES = {"Ozel/Manuel gir": None}
B_STAR_PRODUCT_RANGES = {"Ozel/Manuel gir": None}
BULANIKLIK_PRODUCT_RANGES = {"Ozel/Manuel gir": None}
ILETKENLIK_PRODUCT_RANGES = {"Ozel/Manuel gir": None}

FOOD_QUALITY_PARAMETER_CONFIG.update({
    "L*": {
        "unit": "L*",
        "min_value": 0.0,
        "max_value": 100.0,  # CIELAB standardi - 0=siyah, 100=beyaz
        "decimal_places": 2,
        "products": L_STAR_PRODUCT_RANGES,
        "default_lsl": 40.0,
        "default_usl": 90.0,
        "default_measurement": 65.0,
        "demo_target_mean": 65.0,
        "demo_target_sigma": 2.0,
        "one_sided": False,
        "is_individual": True,  # kolorimetre ile tekil olcum
        "physical_bounds": (0.0, 100.0),
        "recommended_chart": "auto",
        "subgroup_guidance": (
            "Genellikle I-MR (kolorimetre/spektrofotometre ile tekil olcum), "
            "ancak alt grup alinabiliyorsa X-bar/R da uygundur."
        ),
        "method_source": "Kaynak bulunamadi - CIELAB standardi (uluslararasi olcek tanimi, urune ozgu bir TGK/Codex limiti DEGIL). Kullanici kendi hedef degerini girer.",
        "category": "Optik",
        "placeholder": False,  # framework/olcek anlamnda DOGRULANMIS (CIELAB) - urun limiti DEGIL, bkz. method_source
    },
    "a*": {
        "unit": "a*",
        "min_value": -128.0,
        "max_value": 127.0,  # CIELAB standardi - L*'den FARKLI aralik (-yesil, +kirmizi)
        "decimal_places": 2,
        "products": A_STAR_PRODUCT_RANGES,
        "default_lsl": -10.0,
        "default_usl": 30.0,
        "default_measurement": 10.0,
        "demo_target_mean": 10.0,
        "demo_target_sigma": 1.0,
        "one_sided": False,
        "is_individual": True,
        "physical_bounds": (-128.0, 127.0),
        "recommended_chart": "auto",
        "subgroup_guidance": (
            "Genellikle I-MR (kolorimetre/spektrofotometre ile tekil olcum), "
            "ancak alt grup alinabiliyorsa X-bar/R da uygundur."
        ),
        "method_source": "Kaynak bulunamadi - CIELAB standardi (uluslararasi olcek tanimi, urune ozgu bir TGK/Codex limiti DEGIL). Kullanici kendi hedef degerini girer.",
        "category": "Optik",
        "placeholder": False,
    },
    "b*": {
        "unit": "b*",
        "min_value": -128.0,
        "max_value": 127.0,  # CIELAB standardi - a*'den ayni arlikta ama BAGIMSIZ eksen (-mavi, +sari)
        "decimal_places": 2,
        "products": B_STAR_PRODUCT_RANGES,
        "default_lsl": 0.0,
        "default_usl": 40.0,
        "default_measurement": 20.0,
        "demo_target_mean": 20.0,
        "demo_target_sigma": 1.5,
        "one_sided": False,
        "is_individual": True,
        "physical_bounds": (-128.0, 127.0),
        "recommended_chart": "auto",
        "subgroup_guidance": (
            "Genellikle I-MR (kolorimetre/spektrofotometre ile tekil olcum), "
            "ancak alt grup alinabiliyorsa X-bar/R da uygundur."
        ),
        "method_source": "Kaynak bulunamadi - CIELAB standardi (uluslararasi olcek tanimi, urune ozgu bir TGK/Codex limiti DEGIL). Kullanici kendi hedef degerini girer.",
        "category": "Optik",
        "placeholder": False,
    },
    "Bulaniklik": {
        "unit": "NTU",
        "min_value": 0.0,
        "max_value": 10000.0,  # genis sinir - meyve suyu/surup bulaniklik degerleri urune gore cok degisir
        "decimal_places": 1,
        "products": BULANIKLIK_PRODUCT_RANGES,
        "default_lsl": 0.0,  # kullanilmiyor (one_sided=True) - sadece placeholder
        "default_usl": 100.0,
        "default_measurement": 50.0,
        "demo_target_mean": 50.0,
        "demo_target_sigma": 5.0,
        "one_sided": True,  # bulaniklik HER ZAMAN bir ust limit spesifikasyonudur (berraklik hedefi)
        "is_individual": True,  # nefelometre ile tekil olcum
        "physical_bounds": (0.0, None),
        "recommended_chart": "auto",
        "subgroup_guidance": (
            "Genellikle I-MR (nefelometre ile tekil olcum), ancak alt grup "
            "alinabiliyorsa X-bar/R da uygundur."
        ),
        "method_source": "Kaynak bulunamadi - urune ozgu dogrulanmis bir TGK/Codex limiti YOK (icme suyu potabilite yonetmeliginin bulaniklik limiti FARKLI bir urun kategorisidir, buraya UYGULANMAZ). Kullanici kendi spesifikasyonunu girer.",
        "category": "Optik",
        "placeholder": False,
    },
    "Iletkenlik": {
        "unit": "µS/cm",
        "min_value": 0.0,
        "max_value": 100000.0,  # genis sinir - urun tipine gore (seker surubu vb.) cok degisebilir
        "decimal_places": 0,
        "products": ILETKENLIK_PRODUCT_RANGES,
        "default_lsl": 0.0,
        "default_usl": 2000.0,
        "default_measurement": 500.0,
        "demo_target_mean": 500.0,
        "demo_target_sigma": 50.0,
        "one_sided": False,
        "is_individual": True,  # iletkenlik metre ile tekil olcum
        "physical_bounds": (0.0, None),
        "recommended_chart": "auto",
        "subgroup_guidance": (
            "Genellikle I-MR (iletkenlik metre ile tekil olcum), ancak alt "
            "grup alinabiliyorsa X-bar/R da uygundur."
        ),
        "method_source": "Kaynak bulunamadi - urune ozgu dogrulanmis bir TGK/Codex limiti YOK (icme suyu potabilite yonetmeliginin iletkenlik limiti FARKLI bir urun kategorisidir, buraya UYGULANMAZ). Kullanici kendi spesifikasyonunu girer.",
        "category": "Optik",
        "placeholder": False,
    },
})

# Kisa sidebar aciklamalari (PARAMETER_DESCRIPTIONS ile ayni role, Food
# Quality Parameters icin AYRI tutuldu).
FOOD_QUALITY_PARAMETER_DESCRIPTIONS = {
    "Protein": "Toplam protein yuzdesi (%). Kjeldahl/Dumas tipi tahribatli analiz.",
    "Yag": "Toplam yag yuzdesi (%). Soxhlet/Gerber tipi tahribatli analiz.",
    "Kul": "Mineral kalinti yuzdesi (%) - urun rafinasyon derecesinin gostergesi.",
    "Kuru Madde": "Nem disi kalan katı madde yuzdesi (%).",
    "Yogunluk": "Kutle/hacim orani (g/cm3) - piknometre/hidrometre ile olculur.",
    "Refraktif Indeks": "Kirilma indisi (nD) - Abbe refraktometre ile olculur, safligin gostergesi.",
    "L*": "CIELAB parlaklik ekseni (0=siyah, 100=beyaz) - kolorimetre ile olculur.",
    "a*": "CIELAB yesil-kirmizi ekseni (-yesil, +kirmizi) - kolorimetre ile olculur.",
    "b*": "CIELAB mavi-sari ekseni (-mavi, +sari) - kolorimetre ile olculur.",
    "Bulaniklik": "Berraklik derecesinin tersi (NTU) - nefelometre ile olculur, sadece ust limit anlamlidir.",
    "Iletkenlik": "Elektriksel iletkenlik (uS/cm) - cozunmus iyon miktarinin dolayli gostergesi.",
}

# Sidebar'da Food Quality Parameters icin AYRI bir kategori grubu - legacy
# PARAMETER_CATEGORIES'e KARISTIRILMADAN eklenir (app.py her iki listeyi de
# gezip radio grubu olusturur). id "gida_kalite_v14" SABIT kalir (Faz 1'de
# baslatildigi ismi tasir, faz numarasi degil) - Faz 2 (v1.5) parametreleri
# (Yogunluk, Refraktif Indeks) AYNI gruba eklendi, Faz 3'te de (v1.6) ayni
# sekilde devam edecek.
FOOD_QUALITY_PARAMETER_CATEGORIES = [
    (
        "gida_kalite_v14",
        "\U0001F9EA\U0001F9EA Gida Kalite Parametreleri",
        [
            "Protein", "Yag", "Kul", "Kuru Madde", "Yogunluk", "Refraktif Indeks",
            "L*", "a*", "b*", "Bulaniklik", "Iletkenlik",
        ],
    ),
]

# Yeni Food Quality Parameters kayitlarini ana yapilara enjekte eder - app.py
# TEK bir PARAMETER_CONFIG/PARAMETER_CATEGORIES/PARAMETER_DESCRIPTIONS okur,
# iki ayri sozluk/liste arasinda dallanma yazmak zorunda kalmaz. Bu, planin
# "sidebar, CSV sablonu, PDF, validation, bilgi karti ve export hepsi ayni
# registry'den okur" gereksinimini karsilar - FOOD_QUALITY_PARAMETER_CONFIG
# yine de AYRI/isimlendirilmis kalir (yeni framework alanlarinin - physical_
# bounds, recommended_chart, subgroup_guidance, method_source, category,
# placeholder - kaynagi burasidir; result_helpers.build_parameter_info_card()
# bu alanlari PARAMETER_CONFIG uzerinden degil, gerektiginde bu sozlukten okur).
PARAMETER_CONFIG.update(FOOD_QUALITY_PARAMETER_CONFIG)
PARAMETER_CATEGORIES.extend(FOOD_QUALITY_PARAMETER_CATEGORIES)
PARAMETER_DESCRIPTIONS.update(FOOD_QUALITY_PARAMETER_DESCRIPTIONS)

# --- Totox Köprüsü: Minimal I-MR Parametresi (v1.7 - QC Veri Dönüştürücüler) ---
# Totox köprüsü: tam bir FOOD_QUALITY parametresi DEĞIL - ürün bazlı LSL/USL
# araştırması gerekmez, çünkü Totox = 2*PV + AnV zaten Codex/IOC'ten gelen
# TEK, evrensel bir USL'e (TOTOX_LIMIT = 26.0, app.py) sahiptir. Köprünün
# amacı sadece ham değeri I-MR zaman serisine kaydetmektir.
TOTOX_BRIDGE_PARAMETER_CONFIG = {
    "unit": "meq O2/kg",
    "decimal_places": 2,
    "one_sided": True,
    "is_individual": True,
    "default_usl": 26.0,
    "category": "Proses",
    "method_source": "Codex Alimentarius / IOC (International Olive Council) - Totox = 2xPV + AnV birlesik indeks",
}

# --- Titre Edilebilir Asitlik: Miliekivalan (meq) Faktorleri (v1.7 Faz 2) ---
# Turetme (birinci-ilke stokiyometri, KAYNAK DEGIL - her zaman yeniden
# hesaplanabilir bir gercek, ICUMSA Brix tablosu gibi erisilemez bir
# regulasyon kaynagi DEGIL): Es deger agirlik (g/eq) = Molekul Agirligi (MW)
# / bazisite (H+ sayisi); meq faktoru (g/meq) = Es deger agirlik / 1000.
# Atomik agirliklar: IUPAC standart degerleri (C=12.011, H=1.008, O=15.999).
# - Sitrik Asit (anhidrus, C6H8O7, MW=192.124, triprotik):
#   192.124 / 3 / 1000 = 0.064041 -> 0.0640
# - Malik Asit (C4H6O5, MW=134.087, diprotik):
#   134.087 / 2 / 1000 = 0.067044 -> 0.0670
# - Laktik Asit (C3H6O3, MW=90.078, monoprotik):
#   90.078 / 1000 = 0.090078 -> 0.0900
# - Asetik Asit (C2H4O2, MW=60.052, monoprotik):
#   60.052 / 1000 = 0.060052 -> 0.0600
# Formul: %Asitlik = (titrant_hacmi_mL x titrant_normalitesi x meq_faktoru x 100) / numune_mL
TITRATABLE_ACID_MEQ_FACTORS = {
    "Sitrik Asit (anhidrus)": 0.0640,
    "Malik Asit": 0.0670,
    "Laktik Asit": 0.0900,
    "Asetik Asit": 0.0600,
    "Ozel/Manuel gir": None,
}
