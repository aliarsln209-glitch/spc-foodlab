# SPC FoodLab — Metodoloji ve Doğrulama

Bu doküman, [README.md](README.md)'de kısaca değinilen SPC FoodLab'in
kullandığı formülleri, sabit tablolarını, doğrulama testlerini ve ürün
referans tablolarının kaynaklarını detaylı şekilde açıklar. README hızlı
bir genel bakış içindir; burada projenin "neden doğru" olduğunun kanıtı var.

## İçindekiler

1. [Yöntem ve formüller](#yöntem-ve-formüller)
2. [Doğrulama](#doğrulama)
3. [Ürün referans tabloları ve kaynaklar](#ürün-referans-tabloları-ve-kaynaklar)

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
fonksiyonundaki (`src/app.py`) şu eşiklere dayanır — bu, hesaplamayı
etkilemeyen, salt görsel bir sınıflandırmadır:

| Cpk/Cpu | Rozet |
|---|---|
| ≥ 1.67 | 🟢 Excellent |
| 1.33 – 1.67 | 🟢 Capable |
| 1.0 – 1.33 | 🟡 Marginal |
| < 1.0 | 🔴 Not Capable |

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
edildi (`pytest tests/` — 27 test, 4 dosya; her push'ta GitHub Actions
ile otomatik çalışır). İlk 3 dosya (17 test) aşağıda anlatılan formül
doğrulamalarını kapsar; 4. dosya (`test_result_helpers.py`, 10 test)
`src/result_helpers.py`'daki hesaplama-DIŞI sunum yardımcılarını
(Cpk rozet eşikleri, trend göstergesi, quick summary metni, demo
senaryosu hedef hesaplaması) test eder — bunlar doğrulanacak
istatistiksel formüller değil, mevcut sonuçların doğru sınıflandırılıp
metne çevrildiğinin kontrolüdür.

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

---

⬅ [README.md'ye dön](README.md)
