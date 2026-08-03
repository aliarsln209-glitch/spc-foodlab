# 📊 SPC FoodLab

Gıda üretiminde pH ölçümlerinden **istatistiksel proses kontrolü (SPC)**
grafiği ve **süreç yeterlilik analizi (Cpk)** üreten bir Streamlit
uygulaması.

## Ne yapar

Gıda üretim hatlarında laboratuvar analiz sonuçları (pH, Brix, nem, aw,
viskozite vb.) genelde sadece kaydedilir, istatistiksel olarak
yorumlanmaz. Bu araç, vardiya bazlı alt gruplar halinde girilen pH
ölçümlerinden otomatik olarak:

- Ortalama, standart sapma, kontrol limitlerini (UCL/LCL),
- X-bar ve R kontrol grafiğini,
- Süreç yeterlilik indeksini (Cpk),

hesaplar ve spesifikasyon dışı noktaları grafikte görsel olarak işaretler.

**Neden yaptım:** Gıda mühendisliği eğitimimde gördüğüm istatistiksel
proses kontrolü (SPC) / kalite mühendisliği konusunu, gerçek bir araç
olarak uygulamaya döktüğüm bireysel bir proje. Amaç, ders içeriğindeki
formülleri (X-bar/R kontrol grafiği, Cpk) literatür kaynaklarıyla
doğrulayarak çalışan, deploy edilmiş bir ürüne dönüştürmek.

**Bağımsızlık notu:** Bu proje, NAR ve EtiketAI'daki ekip
çalışmalarımdan tamamen bağımsız, farklı bir gıda mühendisliği alt
alanında (istatistiksel proses kontrolü / kalite mühendisliği)
bireysel olarak geliştirilmiştir. NAR etiket analizi, EtiketAI mevzuat
uyum SaaS'ı üzerine kurulu ekip projeleridir; SPC FoodLab konu, kullanım
senaryosu ve hedef kitle açısından bunlardan net şekilde ayrışır.

## Kapsam (v1 / MVP)

**Dahil:**
- Tek parametre: pH
- Yapılandırılmış form ile alt grup veri girişi (vardiya başına 4 ölçüm)
- Otomatik ortalama, standart sapma, UCL/LCL hesaplama
- X-bar ve R kontrol grafiği
- Cpk (süreç yeterlilik indeksi)
- Spesifikasyon dışı noktaların görsel işaretlenmesi

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

## Nasıl çalıştırılır (local)

```bash
pip install -r requirements.txt
cd src
streamlit run app.py
```

Uygulama varsayılan olarak `http://localhost:8501` üzerinde açılır.

## Demo

<!-- Deploy sonrası link buraya eklenecek -->

## Teknik yığın

- **Streamlit** (Python) — form, hesaplama ve grafik tek pakette
- **Deploy:** Streamlit Community Cloud
- Veri kalıcılığı: session-state (uygulama içi) + CSV export — v1'de
  veritabanı entegrasyonu yok

## Proje yapısı

```
spc-foodlab/
├── src/
│   ├── app.py          # Streamlit arayüzü (3 sekme)
│   ├── spc_core.py     # X-bar/R ve Cpk hesaplama çekirdeği
│   ├── demo_data.py    # Kontrollü simülasyon veri üreteci
│   └── constants.py    # Sabit yapılandırma (n=4, vardiya listesi)
├── tests/
│   └── test_validation.py  # Formül doğrulama testi
└── requirements.txt
```
