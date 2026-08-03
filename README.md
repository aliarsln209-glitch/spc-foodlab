# 📊 SPC FoodLab

Gıda üretiminde pH, Brix, aw (su aktivitesi), viskozite, nem/rutubet,
tuz/NaCl, titrasyon asitliği, peroksit değeri veya HMF ölçümlerinden
**istatistiksel proses kontrolü (SPC)** grafiği ve **süreç yeterlilik
analizi (Cpk/Cpu)** üreten bir Streamlit uygulaması.

🔗 **Demo:** [spc-foodlab-4qhdg4ozkknrpnhwj5pxxm.streamlit.app](https://spc-foodlab-4qhdg4ozkknrpnhwj5pxxm.streamlit.app/)

## English summary

SPC FoodLab turns routine food-quality lab measurements into proper
**Statistical Process Control (SPC)** charts and **process capability
(Cpk/Cpu)** analysis, instead of just logging numbers.

- **Two chart engines:** X-bar/R for subgroup-based parameters (pH,
  Brix, aw, moisture, salt, titratable acidity), and Individual-Moving
  Range (I-MR) for parameters measured one value at a time (viscosity,
  peroxide value, HMF).
- **One- or two-sided Cpk**, resolved automatically per *product* —
  e.g. honey's moisture spec only has an upper limit (per Turkish Food
  Codex), so it gets a one-sided Cpu automatically while other products
  under the same parameter stay two-sided.
- Every formula and constant (A2/D3/D4/d2, the I-chart's 2.66 constant,
  Cpk/Cpu, including the R̄=0 edge case) is validated against a
  textbook or industry worked example before being trusted — see
  `tests/` (10 automated tests across 3 files).
- Built with Python + Streamlit, deployed on Streamlit Community
  Cloud. Independent, individually-developed project (built to apply
  SPC/quality-engineering coursework to a real, deployed tool).

## Ne yapar ve neden yaptım

Gıda üretim hatlarında laboratuvar analiz sonuçları (pH, Brix, nem, aw,
viskozite vb.) genelde sadece kaydedilir, istatistiksel olarak
yorumlanmaz. Bu araç, seçilen parametreye göre **alt grup bazlı**
(vardiya başına birden çok ölçüm) veya **tek tek ölçülen** (I-MR
chart, bkz. aşağıda) verilerden otomatik olarak ortalama, standart
sapma, kontrol limitlerini (UCL/LCL) ve süreç yeterlilik indeksini
(Cpk/Cpu) hesaplar; spesifikasyon dışı noktaları grafikte işaretler.

Gıda mühendisliği eğitimimde gördüğüm istatistiksel proses kontrolü
(SPC) / kalite mühendisliği konusunu, gerçek bir araç olarak
uygulamaya döktüğüm bireysel bir projedir. Amaç, ders içeriğindeki
formülleri literatür/sektör kaynaklarıyla doğrulayarak çalışan, deploy
edilmiş bir ürüne dönüştürmek.

## Desteklenen parametreler

| Parametre | Chart | Taraflılık | Birim |
|---|---|---|---|
| pH | X-bar/R | İki taraflı | pH |
| Brix | X-bar/R | İki taraflı | °Bx |
| Aw (su aktivitesi) | X-bar/R | Tek taraflı (Cpu) | aw (0–1) |
| Nem/Rutubet | X-bar/R | Ürüne göre (Bal: tek taraflı) | % |
| Tuz/NaCl | X-bar/R | İki taraflı | % |
| Titrasyon Asitliği | X-bar/R | İki taraflı | % |
| Viskozite | I-MR | İki taraflı | cP |
| Peroksit Değeri | I-MR | Tek taraflı (Cpu) | meq O2/kg |
| HMF | I-MR | Tek taraflı (Cpu) | mg/kg |

Sidebar'dan tek bir parametre aktif olacak şekilde seçilir; parametre
değiştirmek mevcut veriyi ve baseline'ı siler (onay istenir) — farklı
parametrelerin verisi aynı oturumda karışmasın diye.

**Kapsam dışı (v1'de yok):** çoklu parametre karşılaştırma, Western
Electric kuralları, kullanıcı hesabı/çoklu kullanıcı sistemi, veritabanı
entegrasyonu (session-state + CSV export yeterli), değişken alt grup
büyüklüğü (n=4 sabit).

## Yöntem ve formüller

### X-bar/R (alt grup bazlı parametreler)

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
arasındaki farktan türetilir (≈3/d2). MR chart'ın D4 sabiti (3.267)
X-bar/R'nin n=2 D4'üyle aynıdır — bu tesadüf değil, MR de n=2'lik bir
"alt grubun" range'i olarak yorumlanabilir.

### Cpk / Cpu (süreç yeterlilik indeksi)

```
İki taraflı:  Cpk = min[ (USL - x̄̄)/(3σ̂), (x̄̄ - LSL)/(3σ̂) ]
Tek taraflı:  Cpu = (USL - x̄̄)/(3σ̂)                          (LSL yok sayılır)
```

**Kaynak:** NIST/SEMATECH e-Handbook of Statistical Methods, Ch. 2 —
[Process Capability (Cpk)](https://itl.nist.gov/div898/software/dataplot/refman2/ch2/cpk.pdf).
σ̂, X-bar/R'de R̄/d2, I-MR'de MR̄/d2 ile tahmin edilir — `compute_cpk(n, ...)`
fonksiyonu n=4 (X-bar/R) veya n=2 (I-MR) ile çağrılarak aynı formül
her iki chart tipi için de yeniden kullanılır.

**Tek/iki taraflı seçimi ürün bazındadır**, parametre bazında değil:
ürün referans tablosundaki `(LSL, USL)` çiftinde `LSL = None` ise o
ürün için Cpu hesaplanır (örn. Nem/Rutubet'te "Bal" — TGK Bal
Tebliği'nde nem için sadece üst limit tanımlı); "Özel/Manuel gir"
seçildiğinde parametrenin kendi varsayılanına dönülür. Tek taraflı
analizde arayüz LSL alanını devre dışı bırakır ve X-bar/I chart'ta
LSL/LCL çizgisini çizmez (sadece USL/UCL gösterilir) — istatistiksel
kontrol-dışı tespiti (bir noktanın LCL altında kalması) buna rağmen
aynen çalışmaya devam eder, sadece çizgi görsel olarak gizlenir.

**Sıfıra bölme koruması:** Bir seri/alt grupta hiç varyasyon yoksa
(R̄ veya MR̄ = 0 — örn. Peroksit/HMF'de ardışık ölçümler birebir
aynıysa), `σ̂ = R̄/d2` de 0 çıkar. `compute_cpk()` bu durumu
ZeroDivisionError yerine matematiksel olarak anlamlı bir sonuçla ele
alır: ortalama spesifikasyon içindeyse Cpk/Cpu = **∞** (süreç
kusursuz), dışındaysa **-∞** (varyasyon olmasa da yetersiz).

### Doğrulama

Her formül, kodlamadan önce elle çözülmüş literatür örnekleriyle test
edildi (`pytest tests/` — 10 test, 3 dosya).

**X-bar/R** — Kaynak: LibreTexts Engineering, *Chemical Process
Dynamics and Controls* (Woolf), [13.2: SPC Basic Control Charts](https://eng.libretexts.org/Bookshelves/Industrial_and_Systems_Engineering/Chemical_Process_Dynamics_and_Controls_(Woolf)/13:_Statistics_and_Probability_Background/13.02:_SPC-_Basic_Control_Charts-_Theory_and_Construction_Sample_Size_X-Bar_R_charts_S_charts)
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

**I-MR** — Kaynak: 6Sigma Toolkit, I-MR Chart örneği (kahve sıcaklığı
verisi, x̄=87.2, MR̄=2.889).

| | Hesaplanan | Kaynak | Fark |
|---|---|---|---|
| UCL | 94.88474 | 94.88 | 0.00474 |
| LCL | 79.51526 | 79.52 | 0.00474 |

±0.01 tolerans ile test edildi (`tests/test_imr_validation.py`) —
X-bar/R testinden tamamen bağımsız.

**Cpk edge case'leri** (R̄/MR̄=0 → ∞/-∞) `tests/test_cpk_edge_cases.py`
ile ayrıca doğrulandı.

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
| Aw | DRINC/UC Davis, Virginia Tech Cooperative Extension | FDA 21 CFR 113/114, aw=0.85'i "potansiyel olarak tehlikeli gıda" eşiği olarak kullanır |
| Nem/Rutubet, Tuz/NaCl, Titrasyon Asitliği | Sektör pratiği | Bal'ın nem üst limiti (≤20) TGK Bal Tebliği'nden |
| Viskozite | Prime Resins, Sculpture Supply (teknik viskozite tabloları) | **Tiksotropi uyarısı:** Ketçap, hardal gibi ürünler karıştırma/basınç arttıkça viskozite kaybeder; standardize edilmemiş ölçüm koşulları tutarsız sonuç verebilir |
| Peroksit Değeri | Codex Alimentarius / IOC (International Olive Council) | Natürel sızma zeytinyağı için ≤20 meq O2/kg |
| HMF | TGK Bal Tebliği (≤40 mg/kg), TGK Üzüm Pekmezi Tebliği (sıvı ≤75, katı ≤100 mg/kg), sektör pratiği (meyve suyu konsantresi ≤20 mg/kg) | — |

## Hızlı Hesaplayıcılar — Totox

Ayrı bir sekmede ("🧮 Hızlı Hesaplayıcılar"), SPC kontrol grafiği
akışından tamamen izole, tek seferlik bir hesaplayıcı:

```
Totox = 2 × Peroksit Değeri + Anisidin Değeri
```

Kullanıcı iki değeri elle girer, sonuç anında hesaplanır;
`session_state.subgroups` veya baseline mekanizmasına dokunmaz.

## Nasıl çalıştırılır (local)

```bash
pip install -r requirements.txt
cd src
streamlit run app.py
```

Uygulama varsayılan olarak `http://localhost:8501` üzerinde açılır.

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
│   └── constants.py    # Sabit yapılandırma (n=4, parametre/ürün tabloları)
├── tests/
│   ├── test_validation.py      # X-bar/R formül doğrulama testi (pH örneği)
│   ├── test_imr_validation.py  # I-MR formül doğrulama testi (kahve sıcaklığı örneği)
│   └── test_cpk_edge_cases.py  # Sıfır-varyasyon (R̄/MR̄=0) edge case testleri
└── requirements.txt
```
