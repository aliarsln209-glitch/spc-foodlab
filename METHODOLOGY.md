# SPC FoodLab — Metodoloji ve Doğrulama

Bu doküman, [README.md](README.md)'de kısaca değinilen SPC FoodLab'in
kullandığı formülleri, sabit tablolarını, doğrulama testlerini ve ürün
referans tablolarının kaynaklarını detaylı şekilde açıklar. README hızlı
bir genel bakış içindir; burada projenin "neden doğru" olduğunun kanıtı var.

## İçindekiler

1. [Yöntem ve formüller](#yöntem-ve-formüller)
2. [Doğrulama](#doğrulama)
3. [Ürün referans tabloları ve kaynaklar](#ürün-referans-tabloları-ve-kaynaklar)
4. [Yol haritası (v1.1 → v3)](#yol-haritası-v11--v3)

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
edildi (`pytest tests/` — 56 test, 7 dosya; her push'ta GitHub Actions
ile otomatik çalışır, `pytest-cov` ile kapsam raporu üretir). İlk 3 dosya
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

## Yol Haritası (v1.1 → v3)

v1, aşağıdaki sürümlerin hiçbiri olmadan da kendi başına tamamlanmış ve
kullanılabilir kabul edilir. Aşağıdakiler bilinçli olarak v1 kapsamı
DIŞINDA tutulan, gelecekteki iterasyonlar için notlardır — her sürüm bir
öncekinin üzerine **tek bir net kavramsal eksen** ekleyecek şekilde
sıralanmıştır (özellik listesi değil): sağlamlaştırma → istatistiksel
derinlik → yeni veri tipi (mikrobiyoloji) → mimari (kalıcılık) → sistem
tasarımı.

Liste **omurga** (yapılması planlanan, sürüm sırasını taşıyan) ve
**stretch** (iyi fikir, zaman/ilgi kalırsa değerlendirilecek, taahhüt
değil) olarak ikiye ayrılmıştır.

### Omurga

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

**v1.2 — İstatistiksel derinlik** (mevcut sürekli-veri motorunun
genişletilmesi, yeni istatistik ailesi yok)
- Nelson / Western Electric kuralları: UCL/LCL aşımı dışında örüntü
  tabanlı sinyaller (örn. 2/3 nokta 2σ dışı aynı yönde, 4/5 nokta 1σ
  dışı aynı yönde, 8 ardışık nokta merkez çizginin aynı tarafında).
  Kaynak: Nelson, L.S. (1984), *"The Shewhart Control Chart—Tests for
  Special Causes"*, Journal of Quality Technology.
- **OOS/OOT ayrımı:** Nelson sinyalinin çıktısı doğru endüstriyel
  terimle etiketlenir — limit (USL/LSL) aşımı **OOS** (Out of
  Specification), örüntü/trend sinyali **OOT** (Out of Trend). Sadece
  doğru terminoloji; otomatik düzeltici faaliyet talimatı (karantina,
  DÖF vb.) ÜRETİLMEZ — uygulama kurumsal SOP'u bilmediği için bu tür bir
  öneri kendi yetkisini aşan bir iddia olur.
- Normality / dağılım kontrolü: histogram + basit normal dağılım
  karşılaştırması, "capability analizi yaklaşık normal veri varsayar"
  şeklinde bir uyarı olarak sunulur — otomatik "normal değil → SPC
  yapılamaz" kapısı DEĞİL, şeffaflık amaçlı.
- Ppk/Pp hesabı (genel örneklem std sapmasıyla) + Cpk-vs-Ppk yorum
  cümlesi ("kısa vadeli kapasite genel kapasiteden yüksek, süreç zaman
  içinde kayıyor olabilir" gibi) — Ppk eklemenin gerçek faydasını
  gösterir.
- Demo senaryo galerisi (iyi süreç / kayan ortalama / düşük Cpk / trend)
  — Nelson sinyallerini göstermek için de gerekli.
- PDF raporuna otomatik yorum cümlesi (trend + Nelson sinyaline dayanan
  kısa özet).

**v1.3 — Mikrobiyoloji (kantitatif)**
- Yeni parametre sınıfı: log10-CFU (TPC/TMAB, Küf-Maya, Koliform,
  Enterobacteriaceae, kantitatif S. aureus) — sayısal, tek taraflı
  (USL), mevcut I-MR + one_sided altyapısını kullanır.
- Log10 dönüşüm katmanı: mikrobiyal sayımlar log-normal dağılır
  (ICMSF, FDA BAM pratiği); ham CFU normal-dağılım varsayan I-MR/Cpk'ya
  DOĞRUDAN sokulmaz.
- **Ham/log10 şeffaflık tablosu:** kullanıcıya hem ham CFU hem
  log10-dönüştürülmüş değer birlikte gösterilir (Batch / Raw CFU/g /
  log₁₀ CFU/g) — "uygulama veriyi neden değiştirdi?" sorusunu önler.
- **LOD/LOQ metadata'sı:** tespit limiti altı değerler ("<10 CFU/g")
  sansürlü veridir; ikame kuralı (örn. LOD/2) kullanıcıya açıkça
  gösterilir (`LOD = 10 CFU/g, Substitution = LOD/2, Used value = 5`),
  gizlenmez.
- Patojen (Salmonella, Listeria — var/yok) parametreleri BU sürüme
  dahil edilmez: bunlar kantitatif değildir, Cpk kavramı uygulanamaz
  (bkz. v2.2).

**v2.0 — Kalıcılık & süreç tanımı**
- Kalıcı depolama (SQLite) — session-state-only mimarinin gerçek
  anlamda kapatılması.
- Batch/Lot History: geçmiş lotların Cpk'sını karşılaştırma — kalıcı
  depolamanın asıl gerekçesi budur (depolama tek başına amaç değildir).
- Batch/lot kaydına isteğe bağlı **kullanıcı notu** sütunu (örn. "vana
  temizlendi, sıcaklık normale döndü"), PDF'e yansır. Not: bu bir
  "dijital imza" değildir — kriptografik imzalama/kimlik doğrulama
  yapılmaz, sade bir metin alanıdır; öyle sunulmaz.
- Control Plan: kullanıcının "bu parametre nasıl izlenecek" tanımını
  (parametre, frekans, alt grup büyüklüğü, chart tipi, USL/LSL)
  kaydedebilmesi — otomatik veri toplama sistemine ÇEVRİLMEZ, sadece
  izleme niyetinin tanımı.

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
- Kapsamlı entegrasyon testleri (API seviyesinde).

### Stretch (iyi fikir, taahhüt değil — ilk kesilecekler sırasıyla)

1. **MSA / Gage R&R** (v2.3): "Süreç mi değişken, ölçüm sistemim mi
   değişken?" sorusu — SPC'nin doğal komşusu ama kendi başına ayrı bir
   istatistik disiplini (tekrarlanabilirlik/tekrar üretilebilirlik,
   ANOVA tabanlı tasarım). En yüksek kesilme adayı.
2. **Lot Kabul Örneklemesi — patojen var/yok** (v2.2): Salmonella/
   Listeria gibi parametreler bir kontrol şeması DEĞİL, bir kabul
   örnekleme sorunudur — ICMSF iki-sınıflı (n,c) veya EC 2073/2005 üç-
   sınıflı (n,c,m,M) planları, zaman içinde trend izlemez, TEK bir lotu
   kabul/red kararına bağlar. Bu nedenle aşağıdaki attribute chart
   motorundan (v2.1) kasıtlı olarak AYRI tutulur — ikisi de "attribute
   veri" olsa da farklı disiplinlerdir (kontrol şeması vs. kabul
   örneklemesi), aynı çatı altında sunulmaz.
3. **Attribute charts — fiziksel kusur** (v2.1): p-chart (kusurlu
   oranı) / c-chart (birim başına kusur sayısı) — hatalı kapak, bombajlı
   kutu, baskı hatası gibi zaman içinde tekrarlayan, trend/özel-neden
   mantığının geçerli olduğu klasik SPC kullanımı. Formülü basit (Binom/
   Poisson) ama yeni `spc_core` fonksiyonu + yeni grafik tipi + yeni
   test gerektirir.
4. **i18n** (v3.1): Arayüz + PDF için TR/EN geçişi. Gerekçesi mühendislik
   pratiği genişliği göstermektir (string dışsallaştırma, locale-aware
   biçimlendirme) — pazar/erişim büyütme gerekçesiyle DEĞİL.
5. **Etkileşimli grafikler (hover/click ile değer gösterme) — Plotly'ye
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

---

⬅ [README.md'ye dön](README.md)
