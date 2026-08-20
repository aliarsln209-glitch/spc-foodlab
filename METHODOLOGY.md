# SPC FoodLab — Metodoloji ve Doğrulama

Bu doküman, [README.md](README.md)'de kısaca değinilen SPC FoodLab'in
kullandığı formülleri, sabit tablolarını, doğrulama testlerini ve ürün
referans tablolarının kaynaklarını detaylı şekilde açıklar. README hızlı
bir genel bakış içindir; burada projenin "neden doğru" olduğunun kanıtı var.

## İçindekiler

1. [Yöntem ve formüller](#yöntem-ve-formüller)
2. [Doğrulama](#doğrulama)
3. [Ürün referans tabloları ve kaynaklar](#ürün-referans-tabloları-ve-kaynaklar)
4. [Yol haritası (v1.0 → v3.0)](#yol-haritası-v10--v30)

## Yöntem ve formüller

### X-bar/R (alt grup bazlı parametreler)

pH, Brix, Aw, Nem/Rutubet, Tuz/NaCl, Titrasyon Asitliği — bu parametreler
vardiya başına birden çok ölçümden oluşan **alt gruplar** halinde girilir.

```
UCL_x = x̄̄ + A2 · R̄          LCL_x = x̄̄ - A2 · R̄
UCL_R = D4 · R̄               LCL_R = D3 · R̄
```

A2, D3, D4, d2 alt grup büyüklüğüne (n) bağlı standart tablo
sabitleridir. **Kaynak:** Montgomery, D.C., *Introduction to
Statistical Quality Control*.

| n | A2 | D3 | D4 | d2 |
|---|-----|-----|------|-------|
| 2 | 1.880 | 0 | 3.267 | 1.128 |
| 3 | 1.023 | 0 | 2.574 | 1.693 |
| 4 | 0.729 | 0 | 2.282 | 2.059 |
| 5 | 0.577 | 0 | 2.114 | 2.326 |
| 6 | 0.483 | 0 | 2.004 | 2.534 |
| 7 | 0.419 | 0.076 | 1.924 | 2.704 |
| 8 | 0.373 | 0.136 | 1.864 | 2.847 |
| 9 | 0.337 | 0.184 | 1.816 | 2.970 |
| 10 | 0.308 | 0.223 | 1.777 | 3.078 |

Alt grup büyüklüğü (n) sidebar'dan kullanıcı tarafından seçilebilir
(varsayılan n=4). Alt sınır **n=2**'dir: n=1'de range her zaman 0
olacağından X-bar/R istatistiksel olarak anlamsızdır — bu durum için
zaten ayrı bir chart türü olan I-MR kullanılır (aşağıya bakınız). Üst
sınır **n=10**'dur — yukarıdaki tablonun kapsadığı Montgomery sabit
aralığı budur. n değiştirildiğinde mevcut alt gruplar geçersiz hale
geldiği için (eski n'e göre girilmiş oldukları için) uygulama onay
isteyip verileri sıfırlar.

### I-MR (tek tek ölçülen parametreler — Viskozite, Peroksit, HMF)

X-bar/R'de bir **alt grup** kavramı vardır (vardiya başına 4 ölçüm) —
kontrol limitleri alt grup *ortalamalarının* ve *aralıklarının*
varyasyonuna dayanır. Viskozite, peroksit değeri, HMF gibi parametreler
pratikte her seferinde **tek bir değer** olarak ölçülür (her ölçüm bir
parti/batch sonucudur); bu yüzden alt grup yerine ardışık iki ölçüm
arasındaki fark (**moving range**) kullanılır:

```
MR_i = |x_i - x_(i-1)|                MR̄ = ortalama moving range
σ̂ = MR̄ / d2  (d2 = 1.128, n=2 sabiti)

I chart:  UCL/LCL = x̄ ± 2.66 × MR̄
MR chart: UCL = 3.267 × MR̄, LCL = 0
```

**Önemli:** I chart'ın merkez sabiti (**2.66**) X-bar'ın A2'sinden
(n=2 için 1.880) **farklıdır** — A2 alt grup *ortalamalarının*
varyasyonundan türetilirken, 2.66 ardışık *bireysel* değerler
arasındaki farktan türetilir (≈3/d2). Farklı bir varyasyon kaynağını
modelledikleri için farklı sabitlerdir. MR chart'ın D4 sabiti (3.267)
X-bar/R'nin n=2 D4'üyle aynıdır — bu tesadüf değil, MR de n=2'lik bir
"alt grubun" range'i olarak yorumlanabilir (iki ardışık nokta).

### Cpk / Cpu (süreç yeterlilik indeksi)

```
İki taraflı:  Cpk = min[ (USL - x̄̄)/(3σ̂), (x̄̄ - LSL)/(3σ̂) ]
Tek taraflı:  Cpu = (USL - x̄̄)/(3σ̂)                          (LSL yok sayılır)
```

**Kaynak:** NIST/SEMATECH e-Handbook of Statistical Methods, Ch. 2 —
[Process Capability (Cpk)](https://itl.nist.gov/div898/software/dataplot/refman2/ch2/cpk.pdf).
σ̂, X-bar/R'de R̄/d2, I-MR'de MR̄/d2 ile tahmin edilir — `compute_cpk(n, ...)`
fonksiyonu n=4 (X-bar/R) veya n=2 (I-MR) ile çağrılarak aynı formül
her iki chart tipi için de yeniden kullanılır (`src/spc_core.py`).

Uygulama içinde her Cpk/Cpu kartının altındaki **"Hesaplama adımlarını
göster"** paneli, bu formülleri o anki verinin gerçek sayılarıyla
adım adım gösterir.

#### Tek taraflı / iki taraflı seçimi — ürün bazında

Tek/iki taraflı seçimi **parametre değil ürün bazındadır**: ürün
referans tablosundaki `(LSL, USL)` çiftinde `LSL = None` ise o ürün
için Cpu hesaplanır (örn. Nem/Rutubet'te "Bal" — TGK Bal Tebliği'nde
nem için sadece üst limit tanımlı); "Özel/Manuel gir" seçildiğinde
parametrenin kendi varsayılanına dönülür. Bu sayede aynı parametre
içinde bazı ürünler iki taraflı, bazıları tek taraflı olabilir.

Tek taraflı analizde arayüz LSL alanını devre dışı bırakır ve X-bar/I
chart'ta LSL/LCL çizgisini çizmez (sadece USL/UCL gösterilir) —
istatistiksel kontrol-dışı tespiti (bir noktanın LCL altında kalması)
buna rağmen aynen çalışmaya devam eder, sadece çizgi görsel olarak
gizlenir.

#### Sıfıra bölme koruması

Bir seri/alt grupta hiç varyasyon yoksa (R̄ veya MR̄ = 0 — örn.
Peroksit/HMF'de ardışık ölçümler birebir aynıysa), `σ̂ = R̄/d2` de 0
çıkar. `compute_cpk()` bu durumu ZeroDivisionError yerine matematiksel
olarak anlamlı bir sonuçla ele alır:

- Varyasyon yok VE ortalama spesifikasyon içindeyse → Cpk/Cpu = **∞**
  (süreç kusursuz)
- Varyasyon yok AMA ortalama zaten spesifikasyon dışındaysa → Cpk/Cpu =
  **-∞** (varyasyon olmasa da süreç yetersiz)

Bu davranış hem X-bar/R hem I-MR yolları için geçerlidir (ikisi de aynı
`compute_cpk()` fonksiyonunu kullanır).

#### Sonuç seviyesi rozeti

KPI panelindeki Cpk/Cpu kartında görülen 🟢/🟡/🔴 rozet, `get_cpk_level()`
fonksiyonundaki (`src/result_helpers.py`) şu eşiklere dayanır — bu,
hesaplamayı etkilemeyen, salt görsel bir sınıflandırmadır. Etiketler
Türkçedir (arayüzde tek dil tutmak için — önceki sürümde İngilizce
etiket + Türkçe yorum cümlesi karışık kullanılıyordu):

| Cpk/Cpu | Rozet |
|---|---|
| ≥ 1.67 | 🟢 Mükemmel |
| 1.33 – 1.67 | 🟢 Yeterli |
| 1.0 – 1.33 | 🟡 Sınırda |
| < 1.0 | 🔴 Yetersiz |

`render_cpk_message()`'in metin uyarısı (başarı/uyarı/hata kutusu) daha
kaba bir 3'lü eşik kullanır (<1.0 / 1.0–1.33 / ≥1.33); ikisi birbirini
tamamlar, çelişmez — rozet daha ince taneli bir okuma sağlar.

#### Trend göstergesi

"Ortalama" KPI kartındaki ▲/▼/→ ok, istatistiksel bir kontrol testi
DEĞİLDİR — `compute_trend()` (`src/app.py`) son N noktanın ortalamasıyla
(N = min(6, örnek sayısı/2)) ondan önceki N noktanın ortalamasını
karşılaştıran basit, tanımlayıcı bir gösterge. Yön ve büyüklük bir
sürecin "iyi" ya da "kötü" gittiğini değil, sadece son verilerin genel
ortalamaya göre nereye kaydığını gösterir; süreç yeterliliği için tek
başına Cpk/Cpu ve kontrol limitlerine bakılmalıdır.

## Doğrulama

Her formül, kodlamadan önce elle çözülmüş literatür örnekleriyle test
edildi (`pytest tests/`; her push'ta GitHub Actions ile otomatik çalışır,
`pytest-cov` ile kapsam raporu üretir). Güncel test sayısı sabit
yazılmıyor — v1.1'den bu yana her fazda büyüdü (bir denetimde `pytest`
gerçekten çalıştırılmadan aktarılan 56/222/229 gibi farklı rakamlar
birbiriyle çelişip dokümantasyon güvenilirliğini zedeledi); doğru sayı
için `pytest tests/ --collect-only -q` çalıştırılmalı. İlk 3 dosya
(17 test) aşağıda anlatılan formül doğrulamalarını kapsar;
`test_result_helpers.py` (10 test) `src/result_helpers.py`'daki
hesaplama-DIŞI sunum yardımcılarını (Cpk rozet eşikleri, trend
göstergesi, quick summary metni, demo senaryosu hedef hesaplaması) test
eder. v1.1 ile eklenen 3 dosya: `test_csv_io.py` (20 test — CSV şema
doğrulama, hata mesajı üretimi, boş/yinelenen satır temizleme, export→
import round-trip), `test_pdf_report.py` (6 test — PDF rapor üretiminin
gerçekten çalıştığının otomatik kanıtı) ve `test_validation_suite.py`
(3 test — aşağıdaki `validation/*.csv` referans dosyalarını okuyup
`spc_core` fonksiyonlarına karşı çalıştırır, bkz. `validation/README.md`).

### X-bar/R

**Kaynak:** LibreTexts Engineering, *Chemical Process Dynamics and
Controls* (Woolf), [13.2: SPC Basic Control Charts](https://eng.libretexts.org/Bookshelves/Industrial_and_Systems_Engineering/Chemical_Process_Dynamics_and_Controls_(Woolf)/13:_Statistics_and_Probability_Background/13.02:_SPC-_Basic_Control_Charts-_Theory_and_Construction_Sample_Size_X-Bar_R_charts_S_charts)
— pH örneği (n=4, k=24 alt grup, x̄̄=7.01, R̄=0.12, A2=0.729).

| | Hesaplanan | Kaynak | Fark |
|---|---|---|---|
| UCL | 7.0975 | 7.0982 | 0.00072 |
| LCL | 6.9225 | 6.9251 | 0.00258 |

Kaynaktaki x̄̄/R̄ değerleri 2 ondalığa yuvarlanmış görüntü değerleri
olduğu için tam eşitlik yerine **±0.001 tolerans** kullanıldı (UCL bu
toleransın içinde). Ayrıca kaynaktaki UCL/LCL'in x̄̄ etrafında
**simetrik olmadığı** tespit edildi (bir transkripsiyon hatası olarak
değerlendirildi); bu yüzden test LCL'i kaynaktaki rakamla değil, UCL
ile matematiksel simetrisiyle doğruluyor (`tests/test_validation.py`).

### I-MR

**Kaynak:** 6Sigma Toolkit, I-MR Chart örneği (kahve sıcaklığı verisi,
x̄=87.2, MR̄=2.889).

| | Hesaplanan | Kaynak | Fark |
|---|---|---|---|
| UCL | 94.88474 | 94.88 | 0.00474 |
| LCL | 79.51526 | 79.52 | 0.00474 |

±0.01 tolerans ile test edildi (`tests/test_imr_validation.py`) —
X-bar/R testinden tamamen bağımsız.

### Cpk edge case'leri

R̄/MR̄=0 → ∞/-∞ davranışı `tests/test_cpk_edge_cases.py` ile ayrıca
doğrulandı (5 test: iki taraflı/tek taraflı × spesifikasyon
içinde/dışında + normal varyasyon regresyon kontrolü).

### Mikrobiyoloji (log10-CFU, v1.3)

`src/microbiology.py`'deki `substitute_below_lod()`/`to_log10()`
fonksiyonları ve LOD-sınır uç durumları (`raw=LOD`, `raw=LOD/2`, küçük
LOD'da negatif log10 sonucu) `tests/test_microbiology.py` ile birim
seviyesinde test edildi. Ayrıca `validation/microbiology_reference.csv`
— 5 mikrobiyoloji parametresinin her biri için **bağımsız elle**
(kodun kendi çıktısına karşı DEĞİL, bilinen log10 sabitleriyle —
log₁₀2=0.30103, log₁₀3=0.47712, log₁₀5=0.69897 vb.) hesaplanmış birer
LOD-ikameli worked example — log10-ortalama, ortalama moving range ve
I-MR (n=2) formülüyle Cpu'yu ±0.001 tolerans içinde doğrular
(`tests/test_microbiology.py::test_microbiology_reference_csv_matches_pipeline`).
Ayrıca 5 parametrenin `PARAMETER_CONFIG` girişinin (gerekli anahtarlar,
tipler, `is_individual`/`one_sided`/`is_microbio` tutarlılığı) doğru
yüklendiğini doğrulayan bir smoke test seti var. Bu, dış kaynaklı
(Montgomery/ICMSF worked example) bir doğrulama DEĞİLDİR — `cpk_
reference.csv`'deki "dahili matematiksel tutarlılık kontrolü" satırlarıyla
aynı kategoridedir, `validation/README.md`'de böyle etiketlenmiştir.

## Ürün referans tabloları ve kaynaklar

Her parametredeki "Ürün" seçimi, LSL/USL alanlarını literatür/sektör
kaynaklı gösterge değerleriyle otomatik doldurur (kullanıcı elle
değiştirebilir — override). **Türk Gıda Kodeksi (TGK) çoğu üründe
sayısal limit belirlemez**; bu tablolar TGK uyumluluğu iddiası değil,
kalite kontrol referansıdır — TGK'nin doğrudan sayısal limit verdiği
istisnalar (Bal'ın nem/HMF üst limitleri) ayrıca belirtilmiştir.

| Parametre | Kaynak | Not |
|---|---|---|
| pH | Oklahoma State University Extension (FDA *Bacteriological Analytical Manual*), Dairy Food Safety Victoria | — |
| Brix | 19 CFR 151.91 (ABD federal regülasyonu, resmi ortalama Brix tablosu) + sektör pratiği | Kaynak tek nokta ortalama verir; ±0.5 tolerans eklenerek aralığa çevrildi. Ölçüm refraktometreyle yapılır ve sıcaklığa duyarlıdır (20°C referans, ATC gerekebilir) |
| Aw | DRINC/UC Davis, Virginia Tech Cooperative Extension | FDA 21 CFR 113/114, aw=0.85'i "potansiyel olarak tehlikeli gıda" eşiği olarak kullanır; sadece USL anlamlıdır |
| Nem/Rutubet, Tuz/NaCl, Titrasyon Asitliği | Sektör pratiği | Bal'ın nem üst limiti (≤20) TGK Bal Tebliği'nden — bu üründe tek taraflı Cpu otomatik devreye girer |
| Viskozite | Prime Resins, Sculpture Supply (teknik viskozite tabloları) | **Tiksotropi uyarısı:** Ketçap, hardal gibi ürünler karıştırma/basınç arttıkça viskozite kaybeder; standardize edilmemiş ölçüm koşulları tutarsız sonuç verebilir |
| Peroksit Değeri | Codex Alimentarius / IOC (International Olive Council) | Natürel sızma zeytinyağı için ≤20 meq O2/kg; sadece USL anlamlıdır |
| HMF | TGK Bal Tebliği (≤40 mg/kg), TGK Üzüm Pekmezi Tebliği (sıvı ≤75, katı ≤100 mg/kg), sektör pratiği (meyve suyu konsantresi ≤20 mg/kg) | Sadece USL anlamlıdır |
| TPC/TMAB, Küf-Maya, Koliform, Enterobacteriaceae, Kantitatif S. aureus | ICMSF genel gıda kategorisi pratiğinden esinlenen GÖSTERGE değerleri (Kantitatif S. aureus için ayrıca ISO 6888-1 yöntem notu) | Sadece USL anlamlıdır, resmi/zorunlu bir TGK limiti DEĞİLDİR. LSL/USL ham KOB/g olarak girilir/gösterilir, Cpk'den önce log10'a çevrilir (bkz. "Mikrobiyoloji (log10-CFU, v1.3)" doğrulama bölümü) |
| Protein (v1.4 Faz 1) | TGK Buğday Unu Tebliği (No: 99/1) Madde 5/d — tam metin doğrulandı | Sadece LSL (minimum) tanımlıdır; USL=100.0 mevzuattan değil, yüzdenin matematiksel üst sınırıdır (Tuz/NaCl'deki aynı desen) |
| Yağ (v1.4 Faz 1) | TGK Tereyağı, Diğer Süt Yağı Esaslı Sürülebilir Ürünler ve Sadeyağ Tebliği (No: 2005/19), Ek tablosu — tam metin doğrulandı | Tereyağı/Yarım yağlı tereyağı iki taraflıdır (mevzuattan); Sadeyağ'da sadece LSL (%99) tanımlı, USL=100.0 matematiksel tavan |
| Kül (v1.4 Faz 1) | TGK Buğday Unu Tebliği (No: 99/1) Madde 5/c — tam metin doğrulandı | Sadece USL anlamlıdır (kül her zaman bir üst limit spesifikasyonudur) |
| Kuru Madde (v1.4 Faz 1) | TGK Reçel, Jöle, Marmelat ve Tatlandırılmış Kestane Püresi Tebliği (No: 2006/55) Madde 5 — tam metin doğrulandı | Sadece LSL (minimum çözünebilir kuru madde) tanımlıdır; USL=100.0 matematiksel tavan |
| Yoğunluk (v1.5 Faz 2) | TGK Yemeklik Zeytinyağı ve Yemeklik Prina Yağı Tebliği (No: 98/7), Ek-1 Madde 2.1 — tam metin doğrulandı | İki taraflıdır (0.910–0.916, 20°C/20°C su); sadece zeytinyağı için, diğer ürünler "Özel/Manuel gir" |
| Refraktif İndeks (v1.5 Faz 2) | Aynı tebliğ, Ek-1 Madde 2.2 — tam metin doğrulandı | İki taraflıdır; naturel/rafine/riviera zeytinyağı (1.4677–1.4700) ile karma prina yağı (1.4680–1.4707) FARKLI aralıklara sahiptir, tebliğ bu ayrımı açıkça yapar. Fiziksel alt sınır nD≥1.333 (su) |

> **Not:** Yukarıdaki 99/1 (Buğday Unu Tebliği), sonraki 2013/9 sürümüyle güncellenmiş olabilir — 2013/9'un TAM METNİ doğrulanamadığı için kaynak olarak 99/1 belirtilir (bu, `RAW_MATERIAL_QC_REFERENCE`'daki "Buğday unu" notuyla AYNI durumdur, bkz. aşağıdaki "Hammadde Kütüphanesi Genişletmesi"). Detaylı worked example ve doğrulama: `validation/chemistry/` ve `validation/physical/` (bkz. `validation/README.md`).

## Hammadde Kütüphanesi Genişletmesi (v1.1.1)

Yukarıdaki "Ürün referans tabloları" **bitmiş ürünler** içindir. v1.1.1
ile 16 hammadde, mevcut 9 parametrenin ilgili olanlarına ("Ürün / Hammadde"
seçim listesine 🌾 önekiyle, `src/constants.py`
`RAW_MATERIAL_QC_REFERENCE`) eklendi — **yeni bir istatistik motoru veya
seçim akışı eklenmedi**, X-bar/R, I-MR ve Cpk/Cpu hesaplama mantığı
(`spc_core.py`) bu değişiklikte hiç dokunulmadı.

**Kritik ayrım:** bu tablo **"Hammadde QC Referansı"**dır, bitmiş ürün
TGK uyumluluğu iddiasını hammaddelere GENİŞLETMEZ. Bir hammadde-parametre
kombinasyonu için güvenilir kaynak (TGK tebliği, Codex/JECFA monografı)
bulunamadığında **rastgele/varsayılan bir sayı konulmadı** — kullanıcı
"Özel/Manuel gir" davranışıyla kendi değerini girer.

### Sonuç özeti

- Toplam hammadde-parametre kombinasyonu: **61**
- Tam kaynaklı (tebliğ/monograf numarası + sayı doğrulandı): **3**
- Kısmi kaynaklı (tebliğ doğru tespit edildi, sayı arama motoru
  snippet'i ile doğrulandı — tam metin taranmış/OCR'siz PDF olduğu için
  doğrudan okunamadı, kritik kullanımdan önce orijinal metinle çapraz
  kontrol önerilir): **1**
- Kaynak bulunamadı → manuel giriş: **57**

### Tam/kısmi kaynaklı 4 çift

| Hammadde | Parametre | Limit | Kaynak | Durum |
|---|---|---|---|---|
| Buğday unu | Nem/Rutubet | USL ≈ %14,5 | TGK Buğday Unu Tebliği (No: 2013/9) | Kısmi — arama snippet'i, tam metin doğrulanmadı |
| Peynir altı suyu tozu | Nem/Rutubet | USL = %5 | TGK Peynir Tebliği (No: 2015/6) | Doğrulandı |
| Kakao tozu | Nem/Rutubet | USL = %9 | TGK Kakao ve Çikolata Ürünleri Tebliği (No: 2017/29) | Doğrulandı |
| Tuz | Tuz/NaCl | LSL = %98 (diğer tuzlar) / %97 (kayatuzu); USL=100 matematiksel tavan | TGK Tuz Tebliği (No: 2013/48) | Doğrulandı (USL mevzuattan değil, yüzdenin matematiksel üst sınırı) |

### Kaynak bulunamayan / manuel giriş gereken hammadde-parametre çiftleri (57)

| Hammadde | Parametreler (manuel giriş) | Not |
|---|---|---|
| Buğday unu | Aw, pH | — |
| Süt tozu | Nem/Rutubet, Aw, pH, Tuz/NaCl (opsiyonel), Titrasyon Asitliği (opsiyonel) | Nem için TGK Fermente Süt Ürünleri Tebliği (2022/44) bulundu ama yanlış ürün kategorisinden (fermente süt tozu) geldiği için sayı KULLANILMADI |
| Glikoz şurubu | Brix, Viskozite, pH, Aw, Nem/Rutubet, Titrasyon Asitliği (opsiyonel) | Brix çözelti bazlı ölçümdür (toz değil, zaten sıvı ürün) |
| Maltodekstrin | Nem/Rutubet, Aw, Brix (opsiyonel), Viskozite (opsiyonel) | Brix/Viskozite toz üründe **çözelti hazırlanarak** ölçülür — metodoloji notu UI'da gösterilir |
| Maltitol | Nem/Rutubet, Aw, Brix (opsiyonel), Viskozite (opsiyonel) | Aynı çözelti-bazlı not |
| Nişasta | Nem/Rutubet, Aw, pH (opsiyonel) | Ayrı bir TGK Nişasta Tebliği tespit edilemedi |
| Bitkisel yağ | Peroksit Değeri, Viskozite | Peroksit için doğru tebliğ (2012/29, değişiklik 2026/14) bulundu ama sayı doğrulanamadı; viskozite genelde mevzuat değil, işletme içi QC parametresi |
| Peynir altı suyu tozu | Aw, pH, Tuz/NaCl (opsiyonel), Titrasyon Asitliği (opsiyonel) | — |
| Kakao tozu | Aw, pH (opsiyonel) | — |
| Toz şeker | Nem/Rutubet, Brix (opsiyonel), Aw (opsiyonel) | Brix çözelti hazırlanarak ölçülür |
| Fruktoz | Nem/Rutubet, Brix (opsiyonel), Aw (opsiyonel) | Brix çözelti hazırlanarak ölçülür |
| Pektin | Nem/Rutubet, Aw, Viskozite, pH (opsiyonel) | Viskozite standart çözelti/jel sisteminde ölçülür, koşullar tesise göre değişir |
| Jelatin | Nem/Rutubet, Aw, Viskozite, pH (opsiyonel) | Aynı çözelti/jel notu |
| Konsantre meyve suyu | Brix, pH, Viskozite, Titrasyon Asitliği, HMF | **HMF için ürün tipine (elma/üzüm/portakal vb.) bağlı genel bir mevzuat limiti bulunamadı — bal/pekmez HMF limitleri buraya uygulanmaz, farklı ürün kategorileridir** |
| Yumurta tozu | Nem/Rutubet, Aw, Peroksit Değeri, pH (opsiyonel), Titrasyon Asitliği (opsiyonel) | TGK Yumurta Tebliği (2024/7) mevcut ama sayısal tablo taranmış PDF'lerden okunamadı |
| Tuz | Aw (opsiyonel) | — |

Detaylı kaynak notları (her çift için tam metin) `src/constants.py`
`RAW_MATERIAL_QC_REFERENCE` sözlüğünde tutulur — bu tablo onun okunabilir
özetidir.

## Yol Haritası (v1.0 → v3.0)

**Method Validation kuralı:** Her yeni istatistiksel hesaplama veya
kalite parametresi, literatürden bilinen bir worked example ile
karşılaştırılıp `validation/` altına referans dosyası olarak eklenmeden
ve `tests/test_validation_suite.py` üzerinden doğrulanmadan release
edilmez. Bu kural **v1.2'den itibaren zorunludur**; öncesindeki sürümler
(v1.0/v1.1/v1.1.1) bu sürece dahil edilmemiştir — onların doğrulaması
yukarıdaki "Doğrulama" bölümünde ayrı şekilde (elle çözülmüş literatür
örnekleriyle) ele alınmıştır.

v1.0/v1.1/v1.1.1, aşağıdaki sürümlerin hiçbiri olmadan da kendi başına
tamamlanmış ve kullanılabilir kabul edilir. Aşağıdakiler bilinçli olarak
bu kapsamın DIŞINDA tutulan, gelecekteki iterasyonlar için notlardır —
her sürüm bir öncekinin üzerine **tek bir net kavramsal eksen**
ekleyecek şekilde sıralanmıştır (özellik listesi değil): sağlamlaştırma
→ istatistiksel derinlik → yeni veri tipi (mikrobiyoloji) → yeni
parametre ailesi (fizikokimyasal) → laboratuvar araçları → mimari
(kalıcılık) → sistem tasarımı.

Liste üç katmana ayrılmıştır:
- **Omurga** — yapılması planlanan, sürüm sırasını taşıyan, taahhüt
  edilen.
- **Extended Roadmap** — versiyon numarası taşır (gelecekte nereye
  oturacağının bir işareti) ama Omurga gibi taahhüt DEĞİLDİR — SPC'nin
  istatistiksel omurgasından (X-bar/R, I-MR, Cpk/Cpu) mimari olarak
  FARKLI ayrı disiplinlerdir.
- **Stretch** — iyi fikir, zaman/ilgi kalırsa değerlendirilecek, taahhüt
  değil, versiyon numarası bile taşımaz.

### Omurga

**v1.0 — Core SPC Platform ✅ Tamamlandı**
- X-bar/R & I-MR kontrol şemaları, Cpk/Cpu hesaplama
- 9 kalite parametresi (pH, Brix, Aw, Viskozite, Nem/Rutubet, Tuz/NaCl,
  Titrasyon Asitliği, Peroksit Değeri, HMF)
- PDF/PNG export, CSV import/export, demo veri, Totox hesaplayıcı
- Güncel test sayısı için bkz. yukarıdaki "Doğrulama" bölümü (sabit bir
  rakam burada verilmiyor — sürekli büyüyen bir sayı, dokümanda
  bayatlamasın diye)

**v1.1 — Sağlamlaştırma ✅ Tamamlandı** (yeni özellik yok, sadece mevcut
iddiaların gerçekten tutulduğunun kanıtı)
- CSV schema validation: sütun sayısı/adı uyuşmazlığı, sayısal olmayan
  değer (virgüllü ondalık, boş hücre, metin) satır numarasıyla birlikte
  Türkçe hata mesajına çevrilir (`src/csv_io.py`)
- Minimum veri sayısı uyarısı: baseline dondurulduktan SONRA da (önceden
  sadece dondurulmadan önce gösteriliyordu) örnek sayısı önerilen
  minimumun (20) altındaysa Cpk/UCL-LCL güvenilirliği için uyarı kalıcı
- NaN / duplicate / boş satır temizleme: tamamen boş satırlar otomatik
  atlanır (sayısı raporlanır); tam yinelenen satırlar silinmez ama
  bilgilendirme amaçlı sayılır (aynı ölçümün tekrar edilmesi istatistiksel
  olarak geçerli olabileceği için sessizce veri kaybına yol açılmaz)
- Spesifikasyon limitlerinin mantıksal doğrulanması: LSL/USL girişleri
  artık parametrenin fiziksel aralığına (`min_value`/`max_value`) sınırlı;
  iki taraflı parametrelerde LSL ≥ USL girilirse aşağıdaki tüm sonuçların
  anlamsız olduğunu belirten açık bir uyarı gösterilir
- Export → import round-trip testi: CSV olarak indirilen bir dosyanın
  (ekstra "Ortalama"/"Range" sütunları dahil) aynen geri yüklendiğinde
  orijinal verinin bozulmadığı otomatik test edilir
- PDF export testi: rapor üretiminin gerçekten çalıştığı ve fpdf2'nin
  Latin-1 dışı karakterlerde (∞, x̄̄ vb.) çökmediği otomatik doğrulanır
- Test coverage raporu: `pytest-cov`, her push'ta CI'da çalışır
- Anlamlı rakam / ondalık basamak koruması: her parametrede
  `decimal_places` niteliği (pH=2, Brix=1, Aw=3, Viskozite=0 gibi,
  laboratuvar cihazı hassasiyetine dayanır); tüm KPI kartı, hesaplama
  adımı ve ham veri tablosu buna göre yuvarlanır — CSV export'u ise
  kullanıcının girdiği tam değeri korur (sadece GÖRÜNÜM yuvarlanır)
- **Validation Suite:** `validation/` klasörü (`xbar_r_reference.csv`,
  `imr_reference.csv`, `cpk_reference.csv` + `README.md`) açıldı;
  `tests/test_validation_suite.py` bu CSV'leri okuyup `spc_core`'a karşı
  çalıştırır — yeni bir referans örneği eklemek artık kod değil veri
  eklemek anlamına gelir. Tek seferlik bir teslimat değil — v1.2'de
  Nelson, v1.3'te mikrobiyoloji formülleri eklendikçe kendi referans
  dosyasını buraya ekleyecek, proje boyunca büyüyen bir disiplin.

Mimari not: CSV içe/dışa aktarma mantığı (`src/csv_io.py`) ve PDF rapor
üretimi (`src/pdf_report.py`) `app.py`'den ayrı, Streamlit'e bağımlı
olmayan modüllere çıkarıldı — `spc_core.py`/`result_helpers.py` ile aynı
gerekçe: pytest ile doğrudan test edilebilmeleri için (bkz. yukarıdaki
"Doğrulama" bölümü).

**v1.1.1 — Hammadde Kütüphanesi ✅ Tamamlandı** (yeni özellik: veri
genişletmesi, yeni istatistik motoru yok)
- 16 hammadde, mevcut 9 parametrenin ilgili olanlarına eklendi (bkz.
  yukarıdaki "Hammadde Kütüphanesi Genişletmesi" bölümü) — X-bar/R, I-MR,
  Cpk/Cpu hesaplama mantığı DEĞİŞMEDİ.
- "Hammadde seçilince parametre listesi filtrelenir" gereksinimi, ayrı
  bir filtreleme fonksiyonu yazmadan, hammaddenin sadece ilgili olduğu
  parametrenin ürün sözlüğünde bulunmasıyla (mimari düzeyde) sağlandı.
- Bitmiş ürün (TGK uyumlu) spesifikasyonlarından ayrı, açıkça etiketlenmiş
  "Hammadde QC Referansı" kategorisi: kaynağı doğrulanamayan hiçbir
  kombinasyon için varsayılan sayı konulmadı (61 çiftin 57'si manuel giriş).
- Kapsam dışı bırakıldı (bilinçli): hammadde kabul sistemi, tedarikçi
  yönetimi, COA yükleme/doğrulama, lot/parti yönetimi, veritabanı — bkz.
  aşağıdaki "Bilinçli olarak reddedilenler".

**v1.2 — Advanced Statistical SPC ✅ Tamamlandı** (mevcut sürekli-veri motorunun
genişletilmesi, yeni istatistik ailesi yok — "sadece gerçekten SPC olan
şeyler")
- Excel/pano yapıştırma editörü (veri girişi)
- Canlı girdi doğrulama (fiziksel sınır uyarısı)
- Nelson / Western Electric kuralları: UCL/LCL aşımı dışında örüntü
  tabanlı sinyaller — Test 5 (2/3 nokta 2σ dışı aynı yönde), Test 6 (4/5
  nokta 1σ dışı aynı yönde), Test 2 (**9** ardışık nokta merkez çizginin
  aynı tarafında — bu maddenin uygulama sırasında bir önceki taslakta
  yanlışlıkla "8 ardışık" yazılmıştı; Nelson (1984) Test 2'nin GERÇEK
  tanımı 9 noktadır, Western Electric'in eski 8-nokta kuralının Nelson
  tarafından güncellenmiş hali — "8 ardışık, HER İKİ tarafta da olabilir,
  Zone C'de hiç nokta yok" ise Test 8, farklı bir kural, burada
  UYGULANMADI, bkz. `src/nelson_rules.py` docstring'i).
  Kaynak: Nelson, L.S. (1984), *"The Shewhart Control Chart—Tests for
  Special Causes"*, Journal of Quality Technology, 16(4), 237-239 —
  çapraz kontrol: SAS PROC SHEWHART "Standard Tests for Special Causes"
  (Nelson 1984/1985 numaralandırması).
- **OOS/OOT ayrımı:** Nelson sinyalinin çıktısı doğru endüstriyel
  terimle etiketlenir — limit (USL/LSL) aşımı **OOS** (Out of
  Specification), örüntü/trend sinyali **OOT** (Out of Trend). Sadece
  doğru terminoloji; otomatik düzeltici faaliyet talimatı (karantina,
  DÖF vb.) ÜRETİLMEZ — uygulama kurumsal SOP'u bilmediği için bu tür bir
  öneri kendi yetkisini aşan bir iddia olur.
- Normality / dağılım kontrolü: histogram + **Shapiro-Wilk testi**
  (`scipy.stats.shapiro`) — "capability analizi yaklaşık normal veri
  varsayar" şeklinde bir uyarı olarak sunulur, otomatik "normal değil →
  SPC yapılamaz" kapısı DEĞİL, şeffaflık amaçlı.
- Ppk/Pp hesabı (genel örneklem std sapmasıyla) + Cpk-vs-Ppk yorum
  cümlesi ("kısa vadeli kapasite genel kapasiteden yüksek, süreç zaman
  içinde kayıyor olabilir" gibi) — Ppk eklemenin gerçek faydasını
  gösterir.
- Zone Shading: ±1σ/±2σ/±3σ bölgelerinin grafikte görsel olarak
  ayrıştırılması — Nelson kurallarının hangi bölgeye dayandığını okunur
  kılar.
- Satır düzenle/sil paneli: şu an yalnızca "tüm verileri temizle"
  (topyekûn) var; tek bir alt grup/ölçümü düzenleme veya silme imkanı
  yok — gerçek bir kullanılabilirlik boşluğu.
- Metodolojik SSS (Nelson kuralları, OOS/OOT'a dair).
- Kontrol limiti manuel hesaplayıcı (elle x̄/R̄ girip UCL/LCL üretme —
  Hızlı Hesaplayıcılar sekmesine, Totox'un yanına).
- Demo senaryo galerisi (iyi süreç / kayan ortalama / düşük Cpk / trend)
  — Nelson sinyallerini göstermek için de gerekli, versiyonun en
  sonunda eklenir (kolay kazanç).
- PDF raporuna otomatik yorum cümlesi (trend + Nelson sinyaline dayanan
  kısa özet).

> **v1.2'ye BİLEREK eklenmeyen bir madde:** "Basit ölçüm belirsizliği/
> tekrarlanabilirlik hesaplayıcısı" fikri değerlendirildi ve reddedildi.
> Kastedilen, aynı numunenin tek operatör tarafından art arda
> ölçülmesinin standart sapmasını raporlamaktı (tek kaynak varyans) —
> ama bu Gage R&R DEĞİLDİR; gerçek R&R en az iki operatör × iki tekrar
> gerektirir (operatör-arası + tekrar-içi varyans ayrımı). Gage R&R'ın
> "hafif" bir versiyonu yoktur — ya tam metodolojiyle yapılır (bkz.
> Stretch Goals → MSA/Gage R&R) ya da hiç yapılmaz; yarım yapılmış bir
> R&R, hiç olmamasından KÖTÜdür çünkü yanlış güven verir.

**Totox Modülü İyileştirmeleri** (v1.2 kapsamında, ayrı görsel iş — PV/
AnV/referans aralığı + hesaplama adımları zaten eklendi, bunun üzerine)
- Sonuç tablosu (PV / AnV / Totox / Referans)
- Birleşik gauge + renkli badge (ayrı KPI kartı değil, tek gösterim)
- LaTeX formül gösterimi (`st.latex`)
- Collapsible references (`st.expander`)
- Genişletilmiş yorum metni + duyarlılık cümlesi (tek satır)
- Session history (uyarı etiketiyle: "bu oturuma özel" — v2.0'daki
  kalıcı depolamadan ÖNCE, session_state-only bir liste)

**v1.3 — Mikrobiyoloji (kantitatif) ✅ Tamamlandı**
- Yeni parametre sınıfı: log10-CFU — **TPC/TMAB, Küf-Maya, Koliform,
  Enterobacteriaceae, Kantitatif S. aureus** (5 parametrenin tümü teslim
  edildi) — sayısal, tek taraflı (USL), mevcut I-MR + `one_sided`
  altyapısını değiştirmeden kullanır.
- **Yeni saf mantık modülü** `src/microbiology.py` (Streamlit'ten
  bağımsız, `spc_core.py`/`nelson_rules.py` ile aynı mimari ilke):
  `substitute_below_lod()`, `to_log10()`, `build_subgroup_entry()` — bu
  ÜÇÜNCÜSÜ, TÜM giriş yollarının (form, CSV import, Excel/pano
  yapıştırma, satır düzenleme paneli, demo veri) geçtiği TEK merkezi
  inşa noktasıdır; hiçbir yerde inline ikame/log10 mantığı tekrarlanmaz.
- Log10 dönüşüm katmanı: mikrobiyal sayımlar log-normal dağılır (ICMSF,
  FDA BAM pratiği); ham CFU normal-dağılım varsayan I-MR/Cpk'ya
  DOĞRUDAN sokulmaz — `subgroups["values"]` mikrobiyoloji parametreleri
  için ZATEN log10 değeridir, `spc_core.py`'ye hiçbir değişiklik
  gerekmedi (grafik/Cpk fonksiyonları parametre-tipinden habersizdir).
- **Ham/log10 şeffaflık tablosu:** "Ham verileri görüntüle/düzenle"
  paneli, mikrobiyoloji parametrelerinde Raw (KOB/g) / LOD altı mı /
  LOD / Kullanılan (KOB/g) / log10 sütunlarını gösterir — "uygulama
  veriyi neden değiştirdi?" sorusunu önler, aynı zamanda düzenlenebilir
  (Raw/LOD altı/LOD elle değiştirilir, Kullanılan/log10 türetilmiş
  olduğu için salt-okunurdur).
- **LOD/LOQ metadata'sı:** tespit limiti altı değerler sansürlü veridir;
  ikame kuralı ICMSF/FDA BAM konvensiyonuna göre **LOD/2**'dir, HER ZAMAN
  yukarıdaki tabloda açıkça gösterilir, gizlenmez. Veri giriş formunda
  "Bu değer LOD altında" checkbox'ı işaretlenince ham girdi devre dışı
  kalır; Excel/pano yapıştırmada aynı bilgi `<10` veya `<LOD` metin
  önekiyle taşınır (regex ile ayrıştırılır, UI'da açıkça belirtilir).
- **Parametreye özgü fark (kasıtlı, dokümante edildi):** Kantitatif
  S. aureus'un varsayılan LOD'u (100 KOB/g) diğer 4 parametreden
  (10 KOB/g) yüksektir — ISO 6888-1 doğrudan yüzey ekimi yöntemi, diğer
  3 parametrenin tipik dökme plaka yönteminden daha az duyarlıdır. Limit
  yapısı (tek taraflı/USL) beşinde de AYNIDIR, fark YALNIZCA LOD'dadır.
- Patojen (Salmonella, Listeria — var/yok) parametreleri BU sürüme
  dahil edilmedi: bunlar kantitatif değildir, Cpk kavramı uygulanamaz
  (bkz. Extended Roadmap → v2.2).

**v1.4 → v1.6 — Food Quality Parameters (fazlı)**

11 parametrenin tamamını + tüm ek özellikleri tek sürümde yapmak
gerçekçi değil: her parametre için ayrı bir LSL/USL kaynak araştırması +
worked example gerekiyor (v1.2 Method Validation kuralı — bkz. yukarıda),
bu da Hammadde Kütüphanesi (v1.1.1) ile kıyaslanabilir büyüklükte bir
araştırma yükü. Bu yüzden aynı istatistik motoru (X-bar/R, I-MR, Cpk/Cpu
— yeni motor İCAT EDİLMEZ) üç fazda, üç ayrı sürümde uygulanır. Faz 1
(çekirdek framework + ilk 4 parametre) onaylanıp tamamlanmadan Faz 2'ye
geçilmez.

**v1.4 — Faz 1: Parameter Framework + Kimyasal/Fiziksel Temel ✅ Tamamlandı**

*Framework (config-driven Internal Parameter Registry):* her parametre
tek bir config nesnesiyle tanımlanır — isim, birim, `decimal_places`,
`physical_bounds` (hard_min/hard_max; örn. Kül/Kuru Madde/Yağ ≥ 0),
`recommended_chart: "auto"` + `subgroup_guidance` (serbest metin —
örn. Protein için "genellikle I-MR, alt grup alınabiliyorsa X-bar/R da
uygun"; sabit grafik dayatılmaz), metodoloji kaynağı (AOAC/ISO), kategori
(Kimyasal/Fiziksel/Optik). Sidebar, CSV şablonu, PDF, validation, bilgi
kartı ve export hepsi bu TEK registry'den okur — yeni parametre eklemek
sadece registry'ye kayıt eklemek anlamına gelir, ayrı UI/CSV/PDF kodu
yazılmaz.

*Faz 1 parametreleri (SADECE bunlar implement edilir):*
- Kimyasal: Protein (%), Yağ (%), Kül (%)
- Fiziksel: Kuru Madde (%)

Her biri için: LSL/USL kaynak araştırması → `constants.py` referans
tablosu → worked example → `validation/chemistry/` veya
`validation/physical/` altına pytest. Kaynağı doğrulanamayan
kombinasyonlarda sayı uydurulmaz, "Özel/Manuel gir"e bırakılır (aynı
disiplin — bkz. Hammadde Kütüphanesi).

*UI:* Kategori gruplama (Kimyasal / Fiziksel / Optik başlıkları — Optik
bu fazda boş, sadece placeholder); parametre bilgi kartı (unit, method,
chart, capability, decimal) framework config'inden otomatik üretilir,
elle yazılmaz.

*Validation klasör yeniden yapılanması:*
```
validation/
  chemistry/
  physical/
  optics/       (boş, Faz 3'te dolacak)
  microbiology/ (v1.3'ten mevcut)
  shared/       (parametre-bağımsız: Cp/Cpk/Ppk, Nelson kuralları, Totox)
```

*Ters Cpk hesaplayıcısı — ❌ PLANLANDI, İMPLEMENT EDİLMEDİ:* gereken sigma
hesabı + Δσ% (mevcut sigma → hedef sigma azaltma oranı) + k-faktörü
analizi (sadece merkez kaydırarak hedefe ulaşılabilir mi) planlanmıştı,
ama koda hiç yazılmadı (`src/app.py`'de "Ters Cpk"/"k-faktör"/"Δσ" için
sıfır eşleşme — 2026-08-20 canlı denetiminde bulundu). Bu satır Faz 1'in
"✅ Tamamlandı" başlığı altında kalmaya devam ediyor çünkü Faz 1'in geri
kalanı (framework + 4 parametre + validation) gerçekten tamamlandı; bu
tek alt madde istisna. Yapılacaksa ayrı bir görev olarak ele alınmalı.

*Dinamik CSV şablon üretici — ❌ PLANLANDI, İMPLEMENT EDİLMEDİ:* Faz 1'in
4 parametresi için birim/format uyumlu `st.download_button` şablonu +
"Template Version" damgası planlanmıştı, koda yazılmadı (`src/app.py`'de
"Template Version" için sıfır eşleşme — aynı denetimde bulundu).

*Totox alt öğeleri* (buraya taşındı):
- Yağ tipi preset seçimi (Balık Yağı/Omega-3, Rafine Bitkisel, Sızma
  Zeytinyağı)
- Oksidasyon eğrisi şeması ("About Totox" panelinin parçası)

*Başlangıç sırası:* (1) framework config şema + physical_bounds/
recommended_chart mekanizması — küçük iş, her şeyi unblock eder; (2) UI
entegrasyonu (kategori gruplama + bilgi kartı), mimariyi erken test etmek
için **placeholder/manuel limitlerle** kurulur (henüz doğrulanmış numara
olarak gösterilmez); (3) Faz 1 — 4 parametre için LSL/USL kaynak
araştırması, placeholder'ların gerçek değerlerle değiştirilmesi; (4)
validation (worked example + pytest); (5) Ters Cpk delta/k-faktör + CSV
şablon üretici (framework'ten bağımsız, herhangi bir noktada yapılabilir).

**v1.5 — Faz 2: Yoğunluk, Refraktif İndeks + Tutarlılık Kontrolleri ✅ Tamamlandı**

Framework zaten kurulu olduğu için bu fazda iş sadece config + LSL/USL
araştırması + worked example — ayrı bir mimari çalışması yok.
- Yoğunluk (g/cm³) — LSL/USL kaynak araştırması + worked example
- Refraktif İndeks (nD) — `physical_bounds`: nD ≥ 1.333 (su)
- Çapraz parametre tutarlılık kontrolü (Kuru Madde + Nem ≈ 100 vb.) —
  bu faza alınma nedeni: Nem parametresi bu fazda framework içinde zaten
  tanımlı olduğu için bağımlılık kurulabilir hale gelir. Yağ+Protein+Kül
  toplamının Kuru Madde'yi aşması durumunda BLOKLAMAYAN, bilgilendirici
  bir uyarı gösterilir.
- `validation/physical/` genişletilir.

**v1.6 — Faz 3: Optik Parametreler ✅ Tamamlandı**
- L*, a*, b* — fiziksel sınır: **L* 0–100**, **a*/b* yaklaşık -128/+127**
  (CIELAB standardı — a*/b*, L* ile AYNI 0-100 aralığında DEĞİLDİR;
  framework'te üçü için ayrı `physical_bounds` tanımlanır, aynı bound
  üçüne birden uygulanmaz)
- Bulanıklık (NTU) — `physical_bounds`: ≥ 0, HER ZAMAN tek taraflı (USL)
- İletkenlik (µS/cm) — `physical_bounds`: ≥ 0
- `validation/optics/` ilk kez dolduruldu — **dahili matematiksel
  tutarlılık kontrolü, ürün spesifikasyonu DEĞİL** (aşağıdaki kaynak
  notuna bakınız)
- **ΔE bu fazda eklenmez** (L*/a*/b*'den türetilir, kapsam dışı — bkz.
  "Kalıcı Hariç Tutulanlar")

> **Kaynak araştırması sonucu — dürüst not:** bu 5 parametrenin hiçbiri
> için ürüne özgü, doğrulanmış bir TGK/Codex/JECFA sayısal limiti
> bulunamadı. Renk (L*/a*/b*) çoğu gıda ürününde mevzuat değil,
> işletme-içi/müşteri-spesifik bir kalite hedefidir; Bulanıklık/İletkenlik
> için de ürüne özgü resmi bir tebliğ limiti yok. Araştırılan ama
> **kullanılmayan** bir kaynak: İnsani Tüketim Amaçlı Sular Hakkında
> Yönetmelik'in Ek-1 tablosu bulanıklık/iletkenlik için sayısal limitler
> içeriyor — ama bu içme suyu potabilite standardıdır, gıda ürünü
> spesifikasyonu DEĞİLDİR (Bal/pekmez HMF limitinin konsantre meyve
> suyuna uygulanmaması ile AYNI ilke). Bu yüzden Hammadde Kütüphanesi'ndeki
> AYNI disiplinle (57/61 manuel giriş) tüm 5 parametrenin "Ürün" listesi
> SADECE "Özel/Manuel gir" içerir — kullanıcı kendi spesifikasyonunu girer.

> **Kalıcı hariç tutulanlar (Food Quality Parameters kapsamında, hiçbir
> fazda yok):** ΔE, ağır metal, pestisit, mikotoksin, alerjen, patojen.

> **Not — AQL/numune boyutu hesaplayıcısı:** bu üç fazın hiçbirinde
> iskelet bile kurulmaz; ISO 2859-1 (TSE 2756-1) tam implementasyonu
> doğrudan Extended Roadmap'teki **v2.2 — Sampling & Acceptance
> Quality**'de bir kerede yapılır (bkz. aşağıda).

**v1.7 — QC Veri Dönüştürücüler (fazlı)**

"Laboratory Utilities" adı terk edildi — **"QC Veri Dönüştürücüler
(Data Pre-processors)"** olarak yeniden çerçevelendi. Bu isim değişikliği
kozmetik değil: sidebar'da SPC Analiz'in ALTINDA, ayrı bir "araçlar
sayfası" gibi değil, **veri giriş kapısı** olarak konumlanır — SPC
FoodLab'in kimliğini ("odaklı bir SPC aracı") koruyan mimari karar bu.

**Altın Kural (her modül için zorunlu kabul testi):** *"Bu
dönüştürücünün çıktısı SPC kontrol kartının Y eksenine doğrudan bir
kalite metriği olarak giriyor mu?"* Hayırsa, modül bu kapsama girmez.
pH Buffer ve genel Unit Converter bu testi geçemediği için kalıcı
reddedildi (aşağıya bakınız).

*Validation klasörü:* `validation/process/` açılır — chemistry/
physical/optics/microbiology'den ayrı bir kategori, çünkü bunlar ürün
spesifikasyonu değil, **ölçüm standardizasyon formülü** doğrulamasıdır
(ICUMSA, Mohr, AOAC asit faktörleri, Ball formula gibi).

**Faz 1 — Köprü Altyapısı + 2 modül + Totox bağlantısı 🟡 Kısmen tamamlandı (Brix sıcaklık düzeltmesi kaynak bekliyor — bkz. aşağıdaki not)**

Önce bunlar çünkü: SPC Entegrasyon Köprüsü paylaşılan altyapıdır (v1.4'teki
Parameter Framework'ün rolünü oynar, sonraki tüm moduller buna bağlanacak);
ilk 2 modül en düşük validation riskini taşır (basit matematik, mevcut
parametreye doğrudan bağlanıyor).

- **SPC Entegrasyon Köprüsü:** `append_to_spc_session(param, value, lot)`
  — hesaplayıcı sonucu, mevcut parametrenin session-state veri setine tek
  tıkla eklenir ("SPC Veri Setine Aktar" butonu). Ayrı bir teknik iş
  kalemi, her modülün "ayrıca ekle"si değil. (Gerçekleşen implementasyon:
  `qc_converters.build_bridge_subgroup_entry()` + `app.py`'deki paylaşılan
  `render_bridge_widget()` — isim planlanandan farklı ama işlev aynı.)

  **Davranış kontratı (kullanıcı aktif OLMAYAN bir hedef seçerse):** buton
  hiç render edilmez, aktif parametre otomatik değiştirilmez, ve
  `subgroups`'a hiçbir şey eklenmez — sadece "önce aktif parametreyi X
  yapın" bilgi mesajı gösterilip fonksiyon `append()` çağrısına
  ulaşmadan sessizce çıkar. Kullanıcı aktif parametreyi elle
  değiştirmeden bu ekrandan hiçbir yazma işlemi gerçekleşemez — Faz 1
  final review'ın yakaladığı "sessizce yanlış parametreye yazma" bug'ı
  bu nedenle yapısal olarak tekrar edemez (bkz. `render_bridge_widget()`
  docstring'i, `app.py`).
- **Brix Düzeltmesi** (ICUMSA SPS-4): mevcut Brix parametresine bağlanır.
  Worked example + `validation/process/` altına pytest.
- **Gravimetrik Nem/Kuru Madde:** dara + yaş + kuru ağırlıktan %Nem/%Kuru
  Madde hesabı, mevcut parametrelere bağlanır. Basit matematik, düşük
  validation riski.
- **Totox köprüsü (kesin — bağlanacak):** Totox v1.0'dan beri mevcut,
  PV/AnV'den türeyen tek bir sayısal değer üretiyor — diğer parametreler
  gibi zaman içinde I-MR ile izlenebilir, teknik olarak farksız. Ayrı
  görünümde kalmasının (session history, v1.2) hiçbir mimari gerekçesi
  yok, sadece köprü konsepti o zaman yoktu. Totox'u tam bir SPC
  parametresi (LSL/USL, chart, Cpk) olarak `FOOD_QUALITY_PARAMETER_CONFIG`'e
  sokmak gereksiz iş — zaten kendi referans aralığı (Codex/IOC, ≤20 meq
  O2/kg) ve gösterimi var; köprü sadece ham Totox değerini zaman
  serisine (I-MR) besleyen bir "kayıt" gibi davranır, tam
  parametre-registry üyeliği gerekmez. Bu ayrım Faz 1 implementasyon
  planında netleştirilecek teknik bir detay, roadmap'i etkilemez.

Implementasyon: `src/qc_converters.py` (pure logic — gravimetrik nem,
köprü fonksiyonu), `src/app.py` "Hızlı Hesaplayıcılar" sekmesi
(Gravimetrik Nem/Kuru Madde paneli + Totox köprü butonu),
`validation/process/`.

**Brix Sıcaklık Düzeltmesi bu tamamlanmaya DAHİL DEĞİL** — kaynak
(AOAC 932.14c veya USDA AMS resmi tablosu) bu oturumda erişilemedi
(paywall/bot engelleme, kaynağın güvenilirlik sorunu DEĞİL). Proje
disiplini gereği ("kaynak doğrulanamazsa sayı uydurulmaz") bu tek
madde, kaynağa erişildiğinde ayrı bir mini-implementasyonla
tamamlanacak şekilde bekletiliyor — bkz. implementasyon planı Task 8-9
(`docs/superpowers/plans/2026-08-19-v1.7-faz1-qc-donusturucu-koprusu.md`).

**Faz 2 — Titrimetrik Dönüştürücüler ✅ Tamamlandı**

Implementasyon: `src/qc_converters.py` (`titratable_acidity()`,
`salt_content_mohr()` — katsayılar IUPAC atomik ağırlıklarından
türetilmiş, kaynağı doğrulanamayan bir tablo DEĞİL), `src/app.py`
"Hızlı Hesaplayıcılar" sekmesi (iki yeni panel, n-tekrarlı X-bar/R
köprüsü), `validation/process/titration_reference.csv`.

**Mimari not:** bu faz, Faz 1'in köprü altyapısını (`build_bridge_
subgroup_entry()`, `render_bridge_widget()`) X-bar/R hedefleri
destekleyecek şekilde genişletti — artık bir köprü, hedefin güncel alt
grup büyüklüğü (n) kadar gerçek tekrar ölçümü (aynı numunenin n kez
titre edilmesi) topluyorsa X-bar/R parametrelerine de bağlanabilir.
Faz 1'deki I-MR-only kısıtlaması (final review bulgusu) hâlâ geçerlidir
— sadece tam sayıda değer verildiğinde X-bar/R köprüsü açılır, n=1 alt
grup asla eklenmez.

**Faz 3 — Karmaşık Validasyon Gerektirenler (sadece F₀) ✅ Tamamlandı**

En son bu çünkü: en yüksek validation riski — hem formül (Bigelow/Ball)
hem de LSL kaynağı araştırması gerekiyor (v1.4→v1.6'daki aynı
disiplinle: kaynak doğrulanamazsa "Özel/Manuel gir").

- **Termal Letalite (F₀, Bigelow/Ball formülü):** hesaplama formülü
  standarttır (z=10°C, T_ref=121.1°C). LSL kaynağı doğrulandı: **FDA 21
  CFR 113** (Thermally Processed Low-Acid Foods) — ABD federal
  regülasyonu, düşük asitli konserve gıdalar için minimum F₀ = **3.0
  dakika** (12D konsepti, D₁₂₁.₁≈0.21 dk *C. botulinum* için; sektör
  pratiğinde ek güvenlik payı için genellikle 6-8 dk hedeflenir — bu not
  UI'da açıkça gösterilir, tek bir "doğru" hedef değer gibi sunulmaz).
  Tek taraflı (sadece LSL anlamlıdır, F₀ ne kadar yüksekse o kadar
  güvenli). Worked example zorunlu, `validation/process/` altına.

Implementasyon: `src/qc_converters.py` (`thermal_lethality_f0()` — Bigelow/
Ball formülü), `src/constants.py` (`F0_BRIDGE_PARAMETER_CONFIG` — Totox
köprüsüyle birebir aynı mimari desen, `PARAMETER_CONFIG`'e katılmaz),
`src/app.py` "Hızlı Hesaplayıcılar" sekmesi (yeni panel, herhangi bir
I-MR parametresine köprülenebilir — mevcut Viskozite parametresine özel
DEĞİL), `validation/process/thermal_lethality_reference.csv`.

**v1.7 QC Veri Dönüştürücüler roadmap'i bu fazla TAMAMLANMIŞTIR** (Faz
1: Köprü Altyapısı + Gravimetrik Nem + Totox köprüsü; Faz 2: Titrimetrik
Dönüştürücüler + köprünün X-bar/R'a genişletilmesi; Faz 3: Termal
Letalite). Brix Sıcaklık Düzeltmesi (Faz 1'de kaynak erişimi
bekleniyor olarak bırakılmıştı) ve Bostwick/Viskozite Sıcaklık
Normalizasyonu (Faz 3 planlamasında kalıcı olarak kapsam dışı
bırakıldı) hâlâ askıda/hariç — bkz. ilgili notlar yukarıda.

**Bostwick/Viskozite Sıcaklık Normalizasyonu — v1.7'den KESİN olarak
ÇIKARILDI, kalıcı hariç tutulanlara taşındı** (bkz. aşağıda). Gerekçe:
araştırma sonucu Bostwick'e özgü standart bir düzeltme formülü/katsayı
tablosu BULUNAMADI (literatür sıcaklığın ölçümü etkilediğini doğruluyor
ama kaynaklanabilir bir denklem sunmuyor). Genel viskozite-sıcaklık
ilişkisi için Arrhenius denklemi matematiksel olarak geçerlidir ama bu,
Hammadde Kütüphanesi'ndeki veya asit faktörlerindeki "kaynak
bulunamadı → manuel gir" durumuyla AYNI KATEGORİDE DEĞİLDİR: o
senaryolarda formül/yöntem sabittir, sadece TEK bir ürün-parametre
eşiği kaynaklanamaz. Bostwick'te ise formülün kendisi (Arrhenius'un
aktivasyon enerjisi Ea) hiçbir zaman evrensel bir sabit sunmaz — her
ürün için deneysel olarak ayrıca ölçülmesi gerekir, hiçbir kaynak
taraması bunu değiştirmez. Kullanıcı her seferinde kendi Ea/A değerini
girmek zorunda kalsaydı, bu artık standarda-referanslı bir "QC Veri
Dönüştürücü" (ICUMSA, Mohr gibi) değil, jenerik bir Arrhenius hesap
makinesi olurdu — tam olarak C₁V₁=C₂V₂ ve pH Buffer'ın reddedilme
gerekçesiyle aynı kategori (genel matematik, standarda özgü değil,
Altın Kural'ı geçemiyor).

**Kapsam dışı (bu roadmap'in parçası değil):**
- **ΔE — KESİN, dışarıda.** v1.6'daki "Kalıcı Hariç Tutulanlar" kararı
  KORUNUYOR: L*, a*, b* zaten ayrı ayrı izleniyor, ΔE bunlardan türeyen
  bir metrik, yeni bilgi eklemiyor. Tek gerçek değeri "hedefe göre sapma"
  vermesi ama bunun için bir "referans parti" (hedef L₀a₀b₀) kavramı
  tanımlanması gerekir — mevcut sistemde olmayan yeni bir SPC kullanım
  paterni (her parametre şu an bağımsız limit karşılaştırması yapıyor,
  hedefe-göre-fark izleme yapmıyor). Küçük bir formül değil, yeni bir
  kavramsal eksen açmak demek. Tartışma KAPANMIŞTIR.
- **Bostwick/Viskozite Sıcaklık Normalizasyonu — KESİN, dışarıda.**
  Yukarıdaki gerekçeyle (standart düzeltme katsayısı yok, her kullanımda
  ürüne özgü deneysel Ea gerektiriyor — SPC pre-processor kimliğine
  uymuyor, "kaynak bulunamadı → manuel gir" fallback'inin kapsamına
  GİRMİYOR çünkü mesele kaynak eksikliği değil, yapısal olarak
  standartlaşamamak). Tartışma KAPANMIŞTIR.
- **C₁V₁=C₂V₂, pH Buffer Preparation, genel Unit Converter** — kalıcı
  reddedildi (Altın Kural'ı geçemiyorlar: SPC akışının parçası değiller,
  gıda-lab'a özgü de değiller — "Food Engineering Toolbox"a kayma riski).
- **Toplu/Batch mod** (Excel sütun yükleyip topluca dönüştürme) — Faz
  1-3'ün hiçbirinde yok. Ayrı bir özellik, köprü + tekil dönüştürücüler
  oturduktan sonra ayrıca değerlendirilir (v1.7.1 veya sonrası).

**Validation zorunluluğu (tüm fazlarda geçerli):** her yeni formül
(ICUMSA, Mohr, asit faktörleri, Ball formula) için literatür worked
example + `validation/` altına pytest — v1.2'den beri zorunlu Method
Validation kuralı burada da aynen işler.

**v1.7.1 — Renk (L*a*b*) Paneli (UI birleştirme, ΔE DEĞİL)**

Canlı denetimde gelen kullanıcı geri bildirimi: L*, a*, b* aynı
spektrofotometre okumasından çıkan üç eksen olduğu halde sidebar'da 3
ayrı parametre gibi (ayrı seçim, ayrı giriş, ayrı ekran) davranıyordu.
Bu, **ΔE kararını yeniden AÇMIYOR** (bkz. yukarıdaki "Kapsam dışı — ΔE
KESİN, dışarıda") — L*, a*, b* istatistiksel olarak hâlâ 3 BAĞIMSIZ I-MR
serisi, hiçbir birleşik/türetilmiş metrik hesaplanmıyor. Değişen sadece
UI katmanı: sidebar'da tek bir "Renk (L*a*b*)" girişi, tek bir birleşik
veri giriş formu (üçü aynı satırda girilir — aynı ölçüme ait oldukları
için), ve üç bağımsız I-MR kartının yan yana gösterildiği tek bir sayfa.

*v1 kapsamı (bilinçli olarak dar tutuldu — Faz 1'in 4 parametreyle
başlayıp sonra genişlemesiyle aynı desen):* birleşik giriş formu + 3
I-MR grafiği + Cpk rozeti + `lab_to_hex()` (D65 varsayımlı, SADECE
görsel önizleme swatch'i — LSL/USL/Cpk kararına hiç girmez, yanında
"yaklaşık önizleme, cihaz aydınlatıcı/gözlemci ayarı farklıysa gerçek
rengi yansıtmayabilir" notu bulunur). **v1'de YOK:** CSV import/export,
PDF export, demo veri üretici, baseline dondurma, Nelson kuralları —
bunlar mevcut tab_data/tab_chart'ın ~1500 satırlık, tek-aktif-parametre
varsayımına sıkı bağlı prosedürel koduna derin bağımlı; bu bağımlılığı
çözüp yeniden kullanılabilir hale getirmek ayrı, daha büyük bir refactor
projesi — v1'e dahil değil, ayrıca değerlendirilecek.

**Validation:** `lab_to_hex()` karar verici olmadığı için (sadece görsel
önizleme) LSL/USL kaynak araştırması gerekmez, ama dönüşüm formülünün
matematiksel doğruluğu bilinen bir CIE Lab→sRGB test vektörüyle
`validation/optics/` altına worked example olarak doğrulanır.

**v2.0 — Kalıcılık & süreç tanımı**
- Kalıcı depolama (SQLite) — session-state-only mimarinin gerçek
  anlamda kapatılması.
- Batch/Lot History: geçmiş lotların Cpk'sını karşılaştırma — kalıcı
  depolamanın asıl gerekçesi budur (depolama tek başına amaç değildir).
- Baseline History: geçmiş baseline dondurma kayıtlarının (ne zaman,
  hangi n ile, hangi UCL/LCL) saklanması — Batch/Lot History'nin doğal
  uzantısı.
- Batch/lot kaydına isteğe bağlı **kullanıcı notu** sütunu (örn. "vana
  temizlendi, sıcaklık normale döndü"), PDF'e yansır. Not: bu bir
  "dijital imza" değildir — kriptografik imzalama/kimlik doğrulama
  yapılmaz, sade bir metin alanıdır; öyle sunulmaz.
- Control Plan: kullanıcının "bu parametre nasıl izlenecek" tanımını
  (parametre, frekans, alt grup büyüklüğü, chart tipi, USL/LSL)
  kaydedebilmesi — otomatik veri toplama sistemine ÇEVRİLMEZ, sadece
  izleme niyetinin tanımı.
- Outlier toggle + what-if simülasyonu: belirli bir noktayı ("özel
  neden" ile açıklanabilir) baseline hesabından geçici olarak hariç
  tutup Cpk/UCL-LCL'in nasıl değişeceğini gösterme — nokta-seviyeli
  metadata (excluded flag) gerektirdiği için kalıcı depolamayla birlikte
  gelir.

**v3.0 — Sistem tasarımı**
- Hesaplama mantığını API katmanına ayırma (FastAPI backend + ince
  istemci) — `spc_core.py`/`result_helpers.py` zaten Streamlit'ten
  bağımsız, bu adım o ayrımın doğal sonucu.
- Docker containerization, temel CI/CD (Docker registry + otomatik
  deploy).
- Minimal audit trail: sade bir değişiklik günlüğü (kim/ne zaman/hangi
  parametre/eski-yeni değer). Bilinçli olarak SADE tutulur — tam bir
  uyum/regülasyon sistemine (e-imza, denetim modu vb.) dönüştürülmez;
  bu proje istatistiksel süreç kontrolüne odaklanır.
- Sürüm geçmişi / changelog paneli (UI karşılığı).
- Kapsamlı entegrasyon testleri (API seviyesinde).

### Extended Roadmap (Taahhüt Değil)

SPC'nin istatistiksel omurgasından (X-bar/R, I-MR, Cpk/Cpu) mimari
olarak FARKLI iki ayrı disiplin — versiyon numarası taşırlar (gelecekte
nereye oturacaklarının bir işareti) ama Omurga'daki gibi taahhüt edilmiş
DEĞİLDİR; zaman/ilgi olursa uygulanır. (Bir önceki taslakta bunlar
yanlışlıkla Omurga'ya, sıradan v2.1/v2.2 olarak konulmuştu — düzeltildi.)

**v2.1 — Attribute Quality Control**
- p chart (kusurlu oranı), np chart, c chart (birim başına kusur
  sayısı), u chart.
- Yabancı madde, kırık ürün, paket hatası gibi zaman içinde tekrarlayan,
  trend/özel-neden mantığının geçerli olduğu klasik SPC kullanımı —
  formülü basit (Binom/Poisson) ama yeni `spc_core` fonksiyonu + yeni
  grafik tipi + yeni test gerektirir.

**v2.2 — Sampling & Acceptance Quality**
- ANSI/ASQ Z1.4, ISO 2859.
- AQL Sample Size Calculator (Lot büyüklüğü → Inspection Level → AQL →
  Sample Size Code Letter, Sample Size, Acceptance/Rejection Number).
- Lot Acceptance / n-c tabloları.
- Salmonella, Listeria gibi var/yok testleri buraya girer: bunlar bir
  kontrol şeması DEĞİL, bir kabul örnekleme sorunudur — ICMSF
  iki-sınıflı (n,c) veya EC 2073/2005 üç-sınıflı (n,c,m,M) planları,
  zaman içinde trend izlemez, TEK bir lotu kabul/red kararına bağlar. Bu
  nedenle v2.1'deki attribute chart motorundan kasıtlı olarak AYRI
  tutulur — ikisi de "attribute veri" olsa da farklı disiplinlerdir
  (kontrol şeması vs. kabul örneklemesi), aynı çatı altında sunulmaz.

### Stretch Goals (iyi fikir, taahhüt değil)

1. **MSA / Gage R&R**: "Süreç mi değişken, ölçüm sistemim mi değişken?"
   sorusu — SPC'nin doğal komşusu ama kendi başına ayrı bir istatistik
   disiplini (tekrarlanabilirlik/tekrar üretilebilirlik, ANOVA tabanlı
   tasarım, en az iki operatör × iki tekrar). v1.2'de "hafif" bir
   versiyonu bilinçli olarak denenmedi (bkz. yukarıdaki not) — ya tam
   metodolojiyle burada yapılır, ya da hiç yapılmaz.
2. **i18n**: Arayüz + PDF için TR/EN geçişi. Gerekçesi mühendislik
   pratiği genişliği göstermektir (string dışsallaştırma, locale-aware
   biçimlendirme) — pazar/erişim büyütme gerekçesiyle DEĞİL.
3. Çoklu kullanıcı, Dashboard, Trend Analytics, Çoklu ürün karşılaştırma.
4. Zone shading detayları, vardiya varyasyon karşılaştırması (v1.2'nin
   ötesinde ek detaylar).
5. İstatistiksel sabitler tablosu (interaktif), LaTeX formül sözlüğü
   (tüm proje için), veri akış şeması (workflow diagram).
6. Export (PDF/PNG) — Totox için.
7. pH Buffer Preparation, Genel Unit Converter (bkz. v1.7 notu —
   QC Veri Dönüştürücüler omurgasının DIŞINDA tutuldu, burada düşük
   öncelikli birer stretch fikri olarak dururlar).
8. **Etkileşimli grafikler (hover/click ile değer gösterme) — Plotly'ye
   geçiş**: GELECEK DEĞERLENDİRME, HENÜZ KARAR VERİLMEDİ. Mevcut mimaride
   (`st.pyplot` + matplotlib) bu mümkün DEĞİL — `st.pyplot()` figürü
   sunucu tarafında statik bir PNG'ye render edip tarayıcıya `<img>`
   olarak gönderir; `mplcursors` gibi kütüphanelerin dayandığı etkileşimli
   GUI event-loop tarayıcı tarafında yoktur, bu bir kısıt değil mimari bir
   imkansızlıktır. Gerçek çözüm `st.plotly_chart()` ile Plotly'ye geçmek
   (native hover tooltip; click-select için ayrıca `streamlit-plotly-
   events` paketi gerekir) — I/MR/X-bar/R chart + histogram fonksiyonları
   `plotly.graph_objects` ile yeniden yazılmalı (UCL/LCL çizgileri, OOS
   segment vurgusu, LCL=0 gölge bandı gibi mantık taşınabilir, veri
   hazırlama zaten ayrık). PDF export'a etkisi: Plotly figürleri
   `fig.to_image(format="png")` ile statik PNG'ye çevrilebilir ama bu yeni
   bir bağımlılık (`kaleido`, `requirements.txt`) gerektirir; kurulunca
   PDF akışı (bkz. yukarıdaki "PDF export testi") yapısal olarak
   değişmez — sadece `fig.savefig()` çağrıları `fig.to_image()` ile yer
   değiştirir. Bilinçli olarak ayrı bir adım: PDF export'un R/MR chart +
   histogram eksikliği matplotlib ile önce düzeltildi (v1.1.1), Plotly
   geçişi bunu bir kez daha bozmadan, kendi başına değerlendirilecek.

### Bilinçli olarak reddedilenler

Aşağıdakiler değerlendirilip roadmap'e ALINMADI, gerekçesiyle birlikte:

- **OOS için otomatik kurumsal aksiyon talimatı** ("ürünü bloke edin,
  DÖF başlatın"): uygulamanın kurumsal SOP/yetki bilgisi yok, bunu
  önermek istatistik aracı ile gerçek QMS otoritesi arasındaki sınırı
  bulanıklaştırır.
- **"Audit Mode"** (denetçiye sadece "temiz" veri gösterip taslak
  veriyi gizleme): iyi niyetli bir "sade görünüm" fikri olsa da, tarif
  edildiği haliyle veriyi seçici gösterme/gizleme mantığına dayanıyor —
  bu, gıda denetimlerinin (BRC/IFS) tam olarak tespit etmeye çalıştığı
  davranış türüdür. Bunun yerine nötr bir "kesinleşmiş lotlar" filtresi
  düşünülebilir ama "denetçiden gizleme" çerçevesiyle değil.
- **Hazır spesifikasyon şablon kütüphanesi**: zaten mevcut —
  `PARAMETER_CONFIG`'teki `products` sözlüğü (yukarıdaki "Ürün referans
  tabloları" bölümü) bu işlevi v1'den beri görüyor.
- **Tam bir kurumsal QMS/regülasyon kapsamı**: HACCP yönetim sistemi,
  ISO dokümantasyonu, COA doğrulama, tedarikçi yönetimi, ağır metal
  analizi, pestisit analizi, mikotoksin analizi, alerjen yönetimi, ERP
  entegrasyonu, LIMS yerine geçme, kurumsal CAPA/DÖF yönetimi, otomatik
  düzeltici faaliyet/karantina talimatı — bu proje istatistiksel süreç
  kontrolüne (SPC) odaklanır, bir kalite yönetim sistemi veya LIMS
  yerine geçmeyi hedeflemez.

---

⬅ [README.md'ye dön](README.md)
