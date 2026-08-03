# 📊 SPC FoodLab

Gıda üretiminde pH veya Brix ölçümlerinden **istatistiksel proses
kontrolü (SPC)** grafiği ve **süreç yeterlilik analizi (Cpk)** üreten
bir Streamlit uygulaması.

## Ne yapar

Gıda üretim hatlarında laboratuvar analiz sonuçları (pH, Brix, nem, aw,
viskozite vb.) genelde sadece kaydedilir, istatistiksel olarak
yorumlanmaz. Bu araç, vardiya bazlı alt gruplar halinde girilen pH veya
Brix ölçümlerinden otomatik olarak:

- Ortalama, standart sapma, kontrol limitlerini (UCL/LCL),
- X-bar ve R kontrol grafiğini,
- Süreç yeterlilik indeksini (Cpk),

hesaplar ve spesifikasyon dışı noktaları grafikte görsel olarak işaretler.

**Neden yaptım:** Gıda mühendisliği eğitimimde gördüğüm istatistiksel
proses kontrolü (SPC) / kalite mühendisliği konusunu, gerçek bir araç
olarak uygulamaya döktüğüm bireysel bir proje. Amaç, ders içeriğindeki
formülleri (X-bar/R kontrol grafiği, Cpk) literatür kaynaklarıyla
doğrulayarak çalışan, deploy edilmiş bir ürüne dönüştürmek.

## Kapsam (v1 / MVP)

**Dahil:**
- Üç parametre: pH, Brix ve Aw (sidebar'dan seçilir, aynı anda tek parametre aktif)
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
│   ├── app.py          # Streamlit arayüzü (3 sekme)
│   ├── spc_core.py     # X-bar/R ve Cpk hesaplama çekirdeği
│   ├── demo_data.py    # Kontrollü simülasyon veri üreteci
│   └── constants.py    # Sabit yapılandırma (n=4, vardiya listesi)
├── tests/
│   └── test_validation.py  # Formül doğrulama testi
└── requirements.txt
```
