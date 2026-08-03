# 📊 SPC FoodLab

Gıda üretiminde pH, Brix, aw (su aktivitesi), viskozite, nem/rutubet,
tuz/NaCl, titrasyon asitliği, peroksit değeri veya HMF ölçümlerinden
**istatistiksel proses kontrolü (SPC)** grafiği ve **süreç yeterlilik
analizi (Cpk)** üreten bir Streamlit uygulaması.

## Ne yapar

Gıda üretim hatlarında laboratuvar analiz sonuçları (pH, Brix, nem, aw,
viskozite vb.) genelde sadece kaydedilir, istatistiksel olarak
yorumlanmaz. Bu araç, seçilen parametreye göre **alt grup bazlı**
(pH/Brix/aw/nem/tuz/asitlik — vardiya başına birden çok ölçüm) veya
**tek tek ölçülen** (viskozite, peroksit, HMF — I-MR chart, bkz.
aşağıda) verilerden otomatik olarak:

- Ortalama, standart sapma, kontrol limitlerini (UCL/LCL),
- X-bar/R veya I-MR kontrol grafiğini,
- Süreç yeterlilik indeksini (Cpk/Cpu),

hesaplar ve spesifikasyon dışı noktaları grafikte görsel olarak işaretler.

**Neden yaptım:** Gıda mühendisliği eğitimimde gördüğüm istatistiksel
proses kontrolü (SPC) / kalite mühendisliği konusunu, gerçek bir araç
olarak uygulamaya döktüğüm bireysel bir proje. Amaç, ders içeriğindeki
formülleri (X-bar/R kontrol grafiği, Cpk) literatür kaynaklarıyla
doğrulayarak çalışan, deploy edilmiş bir ürüne dönüştürmek.

## Kapsam (v1 / MVP)

**Dahil:**
- Dokuz parametre: pH, Brix, Aw, Viskozite, Nem/Rutubet, Tuz/NaCl,
  Titrasyon Asitliği, Peroksit Değeri, HMF (sidebar'dan seçilir, aynı
  anda tek parametre aktif)
- X-bar/R altyapısı: pH, Brix, Aw, Nem/Rutubet, Tuz/NaCl, Titrasyon
  Asitliği — yapılandırılmış form ile alt grup veri girişi (vardiya
  başına 4 ölçüm)
- I-MR altyapısı: Viskozite, Peroksit Değeri, HMF — tek tek ölçüm
  girişi (alt grup yok, bkz. aşağıda)
- Tek/iki taraflı Cpk seçimi **ürün bazında** otomatik belirlenir
  (örn. Nem/Rutubet'te "Bal" tek taraflı, diğer ürünler iki taraflı)
- Otomatik ortalama, standart sapma, UCL/LCL hesaplama
- X-bar/R kontrol grafiği veya I-MR kontrol grafiği (parametreye göre)
- Cpk / Cpu (süreç yeterlilik indeksi), sıfır-varyasyon edge case'i
  (∞/-∞) dahil
- Spesifikasyon dışı noktaların görsel işaretlenmesi (tek taraflı
  durumlarda LSL/LCL çizgisi gizlenir)
- Totox hesaplayıcı (izole, tek seferlik — "Hızlı Hesaplayıcılar" sekmesi)

**Kapsam dışı (v1'de yok):**
- Çoklu parametre karşılaştırma
- Western Electric kuralları
- Kullanıcı hesabı / çoklu kullanıcı sistemi
- Veritabanı entegrasyonu (session-state + CSV export yeterli)
- Değişken alt grup büyüklüğü (n v1'de sabit kod içinde tutuluyor;
  kullanıcı tarafından değiştirilemiyor — ileride genişletme fikri)

## Kullanılan formüller ve kaynaklar

### X-bar kontrol grafiği
```
UCL = x̄̄ + A2 · R̄
LCL = x̄̄ - A2 · R̄
```

### R kontrol grafiği
```
UCL_R = D4 · R̄
LCL_R = D3 · R̄
```

A2, D3, D4 alt grup büyüklüğüne (n) bağlı standart tablo sabitleridir.
**Kaynak:** Montgomery, D.C., *Introduction to Statistical Quality
Control* — standart SPC sabit tablosu.

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

### Cpk (Süreç Yeterlilik İndeksi)
```
σ̂  = R̄ / d2
Cpk = min[ (USL - x̄̄) / (3σ̂),  (x̄̄ - LSL) / (3σ̂) ]
```
σ̂, subgrup-içi (kısa vadeli) varyasyondan R̄/d2 ile tahmin edilir —
ham veri standart sapmasından değil, çünkü subgrup-arası kayma Cpk'yi
yanlış yönde etkilemesin diye SPC'de standart yaklaşım budur.

**Kaynak:** NIST/SEMATECH e-Handbook of Statistical Methods, Ch. 2 —
[Process Capability (Cpk)](https://itl.nist.gov/div898/software/dataplot/refman2/ch2/cpk.pdf);
standart referans: Montgomery, *Introduction to Statistical Quality Control*.

## Doğrulama

Formüllerin doğruluğu, kodlamadan önce elle çözülmüş bir literatür
örneğiyle test edildi.

**Kaynak:** LibreTexts Engineering, *Chemical Process Dynamics and
Controls* (Woolf), [13.2: SPC - Basic Control Charts](https://eng.libretexts.org/Bookshelves/Industrial_and_Systems_Engineering/Chemical_Process_Dynamics_and_Controls_(Woolf)/13:_Statistics_and_Probability_Background/13.02:_SPC-_Basic_Control_Charts-_Theory_and_Construction_Sample_Size_X-Bar_R_charts_S_charts)
— pH X-bar/R örneği (n=4, k=24 alt grup).

Test girdisi: x̄̄ = 7.01, R̄ = 0.12, A2 = 0.729 (n=4).

| | Hesaplanan | Kaynaktaki beklenen | Fark |
|---|---|---|---|
| UCL | 7.0975 | 7.0982 | 0.00072 |
| LCL | 6.9225 | 6.9251 | 0.00258 |

**Tolerans ve LCL kararı:** Kaynakta gösterilen x̄̄ (7.01) ve R̄ (0.12)
değerleri 2 ondalığa yuvarlanmış görüntü değerleridir; kaynağın kendi
UCL/LCL sonuçları orijinal 24 alt grubun tam hassasiyetli (yuvarlanmamış)
verisinden hesaplanmıştır. Bu yüzden tam eşitlik yerine **±0.001
tolerans** ile test edildi ve UCL bu toleransın içinde kaldı.

LCL için ayrıca bir tutarsızlık bulundu: kaynaktaki UCL (7.0982) ve LCL
(6.9251) değerleri x̄̄=7.01 etrafında **simetrik değil** (UCL ofseti
0.0882, LCL ofseti 0.0849 — birbirine eşit olması gerekirken farklı).
Formül gereği UCL ve LCL matematiksel olarak simetrik olmak zorunda
olduğundan (ikisi de x̄̄ ± A2·R̄), bu kaynaktaki bir transkripsiyon/yuvarlama
hatası olarak değerlendirildi. Bu nedenle test, LCL'i kaynaktaki rakamla
değil, **UCL ile matematiksel simetrisiyle** doğruluyor
(`tests/test_validation.py`).

Test çalıştırmak için:
```bash
pytest tests/
```

## Ürün pH referans tablosu

Arayüzdeki "Ürün" seçimi, LSL/USL alanlarını literatürden alınan
gösterge pH aralıklarıyla otomatik doldurur (kullanıcı bu değerleri
elle değiştirebilir — override).

**Önemli:** Türk Gıda Kodeksi (TGK), çoğu gıda ürünü için sayısal bir
pH limiti belirlemez. Bu yüzden tablo, TGK uyumluluğu iddiasıyla değil,
**kalite kontrol referansı** olarak uluslararası literatürden derlendi:

- **Oklahoma State University Extension** — FDA *Bacteriological
  Analytical Manual* verilerine dayanan gıda pH değerleri derlemesi
- **Dairy Food Safety Victoria** — süt ürünleri (süt, yoğurt, peynir,
  tereyağı) için teknik bilgi notu

Kullanıcı, kendi ürününün gerçek spesifikasyonuna sahipse LSL/USL
alanlarını doğrudan elle güncelleyebilir; tablo sadece başlangıç
noktası sağlar.

## Brix referans tablosu

pH'a ek olarak, ikinci parametre olarak **Brix (°Bx)** desteklenir.
Sidebar'daki "Parametre" seçiciyle pH/Brix arasında geçiş yapılabilir;
X-bar/R ve Cpk formülleri parametreden bağımsız olduğu için
(`spc_core.py` değişmedi) aynı matematiksel çekirdek kullanılır — değişen
sadece ölçüm birimi ve ürün spesifikasyon tablosudur.

**Kaynak:** 19 CFR 151.91 — ABD federal regülasyonu, meyve suyu
ithalatı için resmi ortalama Brix değerleri tablosu, + sektör pratiği.
19 CFR 151.91 her ürün için **tek nokta ortalama değer** verir (aralık
değil); LSL/USL için bir aralık gerektiğinden, bu ortalamaya **±0.5
tolerans** eklenerek aralık haline getirildi.

**Ölçüm notu:** Brix ölçümü genellikle **refraktometre** ile yapılır ve
**sıcaklığa duyarlıdır** — çoğu refraktometre 20°C referans sıcaklığına
göre kalibre edilmiştir; farklı sıcaklıkta ölçüm yapılıyorsa sonuçlar
sıcaklık kompanzasyonu (ATC — Automatic Temperature Compensation) olan
bir cihazla veya manuel düzeltme tablosuyla doğrulanmalıdır.

**Önemli:** pH tablosunda olduğu gibi, bu değerler de Türk Gıda
Kodeksi'nin yerini tutmaz — TGK bu konuda sayısal bir limit
belirlemediği için uluslararası literatür kaynağı kullanıldı. Tablo
kalite kontrol referansıdır, zorunlu bir uyumluluk şartı değildir.

**Parametre değişimi ve veri izolasyonu:** pH ve Brix verileri aynı
oturumda karışmasın diye, sidebar'dan parametre değiştirmek mevcut
alt grup verisini ve baseline'ı siler — bu işlem geri alınamaz olduğu
için onay istenir.

## Aw (su aktivitesi) referans tablosu ve tek taraflı Cpk

Üçüncü parametre olarak **aw (su aktivitesi, birimsiz, 0–1 arası)**
desteklenir. X-bar/R formülleri ve A2/D3/D4/d2 sabit tablosu burada da
değişmez; değişen, Cpk hesabının **tek taraflı** yapılmasıdır (aşağıya
bakınız).

**Kaynak:** DRINC (Davis Region Innovation Corridor) / UC Davis ve
Virginia Tech Cooperative Extension aw referans tabloları. Ayrıca FDA,
düşük asitli/asitlendirilmiş konserve gıda regülasyonunda (21 CFR
113/114) **aw = 0.85 eşiğini** "potansiyel olarak tehlikeli gıda"
sınırı olarak kullanır — bu, aw'nin gıda güvenliğinde neden tek yönlü
bir risk eşiği olarak ele alındığının regülasyon örneğidir.

**Neden tek taraflı Cpk (Cpu):** aw'de yalnızca **üst limit (USL)**
mikrobiyal güvenlik açısından anlamlıdır — "aw belirli bir değeri
geçmesin" (düşük aw'de bakteri/küf üremesi durur, dolayısıyla "aşağıda
kalmak" bir risk değil, hedeftir). Alt limit çoğu ürün için
tanımsızdır/anlamsızdır. Standart iki taraflı Cpk formülü
`min(Cpu, Cpl)` kullanılırsa, anlamsız bir LSL için hesaplanan Cpl,
gerçek süreç yeterliliğini yanlış yansıtabilir (örn. yapay olarak
düşük bir Cpk göstererek süreci olduğundan daha kötü gösterebilir).
Bu yüzden aw seçildiğinde arayüz LSL alanını devre dışı bırakır ve
sadece `Cpu = (USL - x̄̄) / (3σ̂)` hesaplanıp gösterilir.

`compute_cpk()` fonksiyonu bunun için opsiyonel bir `one_sided`
parametresi alır; `False` (varsayılan) durumda pH/Brix için mevcut iki
taraflı davranış aynen korunur — bu değişiklik pH/Brix hesaplamalarını
etkilemez (bkz. `tests/test_validation.py`, hâlâ geçiyor).

## Ürün bazında tek/iki taraflı Cpk

Başlangıçta tek/iki taraflı Cpk seçimi **parametre** düzeyinde sabitti
(örn. tüm aw her zaman tek taraflı). Nem/Rutubet parametresiyle birlikte
bu esnekleştirildi: artık seçim **ürün** düzeyinde de değişebilir. Örnek:
Nem/Rutubet parametresinde çoğu ürün (Ekmek, Kaşar peyniri, Makarna vb.)
iki taraflıyken, **Bal** ürünü seçildiğinde otomatik olarak tek taraflı
Cpu'ya geçilir — çünkü TGK Bal Tebliği'nde nem için sadece bir üst limit
tanımlıdır, alt limit yoktur.

Bu, ürün referans tablolarındaki `(LSL, USL)` ikilisinde `LSL = None`
olan girdilerle ifade edilir (aynı `AW_PRODUCT_RANGES`'te kullanılan
`(None, USL)` deseni). Uygulama, seçilen ürünün LSL'i `None` ise o ürün
için tek taraflı Cpu hesaplar; "Özel/Manuel gir" seçildiğinde ise
parametrenin kendi varsayılanına (`PARAMETER_CONFIG["one_sided"]`)
geri döner. Bu sayede aynı parametre içinde bazı ürünler iki taraflı,
bazıları tek taraflı olabilir.

**Grafik sadeleştirmesi:** Tek taraflı analiz aktifken (parametre veya
ürün kaynaklı fark etmez) X-bar/I chart'ta **LSL/LCL çizgisi ve etiketi
çizilmez** — sadece USL/UCL gösterilir. Bu, önceki oturumda yalnızca
Aw için değil, artık tüm tek taraflı durumlar için tutarlı şekilde
uygulanır (istatistiksel kontrol-dışı tespiti, yani bir noktanın LCL
altında kalıp kalmadığı kontrolü, buna rağmen aynen çalışmaya devam
eder — sadece çizgi görsel olarak gizlenir).

## Sıfıra bölme koruması (Cpk/Cpu edge case)

Eğer bir seri/alt grupta hiç varyasyon yoksa (R̄ veya MR̄ tam 0 — örn.
Peroksit/HMF'de ardışık ölçümler birebir aynıysa), `σ̂ = R̄/d2` formülü
de 0 çıkar ve normal Cpk formülü sıfıra bölme hatası verirdi.
`compute_cpk()` artık bu durumu özel olarak ele alır:

- Varyasyon yok VE ortalama spesifikasyon içindeyse → Cpk/Cpu = **∞**
  (süreç kusursuz)
- Varyasyon yok AMA ortalama zaten spesifikasyon dışındaysa → Cpk/Cpu =
  **-∞** (varyasyon olmasa da süreç yetersiz)

Bu davranış hem X-bar/R hem I-MR yolları için geçerlidir (ikisi de aynı
`compute_cpk()` fonksiyonunu kullanır) ve `tests/test_cpk_edge_cases.py`
ile doğrulanmıştır — mevcut pH/Brix/Aw/Viskozite testlerinden bağımsız,
onları etkilemez.

## I-MR (Individual-Moving Range) Chart — Viskozite

Dördüncü parametre olan **Viskozite (cP)**, X-bar/R yerine **I-MR
(Individual-Moving Range) chart** kullanır. Bu, yapısal olarak farklı
bir chart tipidir — X-bar/R değil.

### Neden farklı: alt grup yok

X-bar/R'de bir **alt grup** kavramı vardır (örn. vardiya başına 4
ölçüm) — kontrol limitleri alt grup *ortalamalarının* ve alt grup
*aralıklarının* (range) varyasyonuna dayanır. Viskozite gibi bazı
parametreler pratikte her seferinde **tek bir değer** olarak ölçülür;
"vardiya başına 4 ölçüm" gibi bir yapı gıda mühendisliği pratiğinde
zorlama olur. I-MR'de bu yüzden alt grup yoktur: **her ölçüm kendi
başına bir nokta**dır, ve "range" yerine **ardışık iki ölçüm arasındaki
fark (moving range)** kullanılır:

```
MR_i = |x_i - x_(i-1)|
MR̄   = ortalama moving range
```

### Formüller

```
σ̂ = MR̄ / d2                    (d2 = 1.128, n=2 sabiti)
I chart:  UCL/LCL = x̄ ± 2.66 × MR̄
MR chart: UCL = 3.267 × MR̄, LCL = 0
```

**Önemli:** I chart'ın merkez sabiti (**2.66**) X-bar chart'ın A2
sabitinden (n=2 için 1.880) **farklıdır** — bunlar karıştırılmamalıdır.
A2, alt grup *ortalamalarının* varyasyonundan türetilir; 2.66 ise
ardışık *bireysel* değerler arasındaki farktan türetilir (yaklaşık
3/d2). Farklı bir varyasyon kaynağını modelledikleri için farklı
sabitlerdir. MR chart'ın D4 sabiti (3.267) ise X-bar/R'nin n=2 için D4
sabitiyle aynıdır, bu bir tesadüf değil — MR de aslında n=2'lik bir
"alt grubun" range'i olarak yorumlanabilir (iki ardışık nokta).

### Doğrulama

**Kaynak:** 6Sigma Toolkit, I-MR Chart örneği (kahve sıcaklığı verisi).

Test girdisi: x̄ = 87.2, MR̄ = 2.889, d2 = 1.128.

| | Hesaplanan | Kaynaktaki beklenen | Fark |
|---|---|---|---|
| UCL | 94.88474 | 94.88 | 0.00474 |
| LCL | 79.51526 | 79.52 | 0.00474 |

±0.01 tolerans ile test edildi (bkz. `tests/test_imr_validation.py` —
mevcut pH/Brix/Aw doğrulama testinden (`test_validation.py`) tamamen
ayrı, birbirini etkilemez).

### Arayüz farkları (Viskozite seçildiğinde)

- Veri girişi formu **tek ölçüm** alır (vardiya/alt grup seçimi yok);
  ölçümlerin girildiği **sıra** korunur ve moving range hesabında
  kullanılır.
- Grafik sekmesinde X-bar/R yerine **I chart** (üstte) ve **MR chart**
  (altta) gösterilir.
- Cpk hesaplaması `compute_cpk(x̄, MR̄, n=2, ...)` ile yapılır — n=2
  sabit tablosundaki d2=1.128 değeri I-MR'nin kendi σ̂ formülüyle
  birebir örtüştüğü için `compute_cpk()`'ye dokunmadan yeniden
  kullanılabildi.
- Sayı girişi aralığı 0–300.000 cP olarak genişletildi (viskozite
  ürüne göre çok geniş bir aralıkta olabilir — sütten fıstık ezmesine
  kadar). Logaritmik ölçekli bir giriş arayüzü değerlendirildi ancak
  v1 kapsamında karmaşıklığı gerekçelendirmediği için doğrusal (linear)
  bir sayı girişiyle bırakıldı; kullanıcı değeri doğrudan yazabilir.

## Viskozite referans tablosu

**Kaynak:** Prime Resins ve Sculpture Supply teknik viskozite tabloları
— gerçek marka ölçümlerine dayanan sektör referansları, resmi/zorunlu
bir standart değildir.

**Tiksotropi uyarısı:** Ketçap, hardal gibi ürünler **tiksotropiktir**
— karıştırma/basınç arttıkça viskoziteleri azalır. Ölçüm koşulları
(karıştırma hızı, bekleme süresi) standardize edilmeden yapılan
ölçümler tutarsız olabilir; bu tablodaki değerler yalnızca gösterge
niteliğindedir, hassas kalite kontrol kararları için ölçüm protokolü
sabitlenmelidir.

## Nem/Rutubet, Tuz/NaCl ve Titrasyon Asitliği referans tabloları

Bu üç parametre, X-bar/R altyapısını (pH/Brix ile aynı) kullanır —
yapılandırılmış alt grup veri girişi, iki taraflı Cpk (Bal istisnası
hariç, bkz. yukarıda). Değerler sektör pratiğine dayanan gösterge
değerleridir, TGK'nin yerini tutmaz (Bal'ın nem üst limiti hariç — o
doğrudan TGK Bal Tebliği'nden alınmıştır).

| Parametre | Birim | Örnek ürün aralığı |
|---|---|---|
| Nem/Rutubet | % | Ekmek: 35-40, Bal: ≤20 (TGK Bal Tebliği, tek taraflı) |
| Tuz/NaCl | % | Ekmek: 1.5-2.0, Turşu salamurası: 5.0-10.0 |
| Titrasyon Asitliği | % | Süt (taze): 0.14-0.16, Yoğurt: 0.6-1.0 |

## Peroksit Değeri ve HMF referans tabloları (I-MR + tek taraflı)

Bu iki parametre, Viskozite gibi **I-MR chart** kullanır (her ölçüm tek
bir parti/batch sonucu olduğundan alt grup kavramı pratik değildir) ve
aw gibi **tek taraflı Cpu** hesaplar (sadece üst limit anlamlıdır).

**Peroksit Değeri (meq O2/kg):** Yağlarda oksidasyon derecesinin
göstergesi. **Kaynak:** Codex Alimentarius / IOC (International Olive
Council) standardı — natürel sızma zeytinyağı için ≤20 meq O2/kg.

**HMF — Hidroksimetilfurfural (mg/kg):** Isıl işlem/depolama sırasında
şekerlerin bozunmasının göstergesi. **Kaynak:** TGK Bal Tebliği (bal,
≤40 mg/kg), TGK Üzüm Pekmezi Tebliği (pekmez sıvı ≤75, katı ≤100
mg/kg), genel sektör pratiği (meyve suyu konsantresi, ≤20 mg/kg).

Her iki parametre de `PARAMETER_CONFIG` içinde `is_individual: True` ve
`one_sided: True` bayraklarını birlikte taşır — bu, I-MR ve tek taraflı
Cpk mekanizmalarının birbirinden bağımsız olarak tasarlandığını ve
istenildiği gibi birleştirilebildiğini gösterir.

## Hızlı Hesaplayıcılar — Totox

Ayrı bir sekmede ("🧮 Hızlı Hesaplayıcılar"), SPC kontrol grafiği
akışından tamamen izole, tek seferlik bir **Totox hesaplayıcısı**
bulunur:

```
Totox = 2 × Peroksit Değeri + Anisidin Değeri
```

Bu bir kontrol grafiği değildir — kullanıcı iki değeri elle girer,
sonuç anında hesaplanır. `session_state.subgroups` veya baseline
mekanizmasına hiçbir şekilde dokunmaz.

## Nasıl çalıştırılır (local)

```bash
pip install -r requirements.txt
cd src
streamlit run app.py
```

Uygulama varsayılan olarak `http://localhost:8501` üzerinde açılır.

## Demo

🔗 [spc-foodlab-4qhdg4ozkknrpnhwj5pxxm.streamlit.app](https://spc-foodlab-4qhdg4ozkknrpnhwj5pxxm.streamlit.app/)

## Teknik yığın

- **Streamlit** (Python) — form, hesaplama ve grafik tek pakette
- **Deploy:** Streamlit Community Cloud
- Veri kalıcılığı: session-state (uygulama içi) + CSV export — v1'de
  veritabanı entegrasyonu yok

## Proje yapısı

```
spc-foodlab/
├── src/
│   ├── app.py          # Streamlit arayüzü (4 sekme)
│   ├── spc_core.py     # X-bar/R, I-MR ve Cpk hesaplama çekirdeği
│   ├── demo_data.py    # Kontrollü simülasyon veri üreteci (alt grup + bireysel)
│   └── constants.py    # Sabit yapılandırma (n=4, parametre/ürün tablolari)
├── tests/
│   ├── test_validation.py      # pH/Brix/Aw/Nem/Tuz/Asitlik (X-bar/R) formül doğrulama testi
│   ├── test_imr_validation.py  # Viskozite/Peroksit/HMF (I-MR) formül doğrulama testi
│   └── test_cpk_edge_cases.py  # Sıfır-varyasyon (R̄/MR̄=0) edge case testleri
└── requirements.txt
```
