# 📊 SPC FoodLab

[![Tests](https://github.com/aliarsln209-glitch/spc-foodlab/actions/workflows/tests.yml/badge.svg)](https://github.com/aliarsln209-glitch/spc-foodlab/actions/workflows/tests.yml)

Gıda üretiminde pH, Brix, aw (su aktivitesi), viskozite, nem/rutubet,
tuz/NaCl, titrasyon asitliği, peroksit değeri veya HMF ölçümlerinden
**istatistiksel proses kontrolü (SPC)** grafiği ve **süreç yeterlilik
analizi (Cpk/Cpu/Ppk/Pp)** üreten bir Streamlit uygulaması. Bitmiş
ürünlerin yanı sıra 16 hammadde (buğday unu, süt tozu, kakao tozu, tuz
vb.) için ayrı bir **Hammadde QC Referansı** kütüphanesi de içerir (bkz.
[METHODOLOGY.md](METHODOLOGY.md) "Hammadde Kütüphanesi Genişletmesi").
v1.2 ile **Nelson kuralları** (örüntü tabanlı sinyaller), **OOS/OOT
ayrımı**, **Shapiro-Wilk normallik testi** ve daha fazlası eklendi (bkz.
"v1.2 — Advanced Statistical SPC" bölümü aşağıda).

🔗 **Demo:** [spc-foodlab.streamlit.app](https://spc-foodlab.streamlit.app/)

## English summary

SPC FoodLab turns routine food-quality lab measurements into proper
**Statistical Process Control (SPC)** charts and **process capability
(Cpk/Cpu/Ppk/Pp)** analysis, instead of just logging numbers.

- **Two chart engines:** X-bar/R for subgroup-based parameters (pH,
  Brix, aw, moisture, salt, titratable acidity), and Individual-Moving
  Range (I-MR) for parameters measured one value at a time (viscosity,
  peroxide value, HMF).
- **One- or two-sided Cpk**, resolved automatically per *product* —
  e.g. honey's moisture spec only has an upper limit (per Turkish Food
  Codex), so it gets a one-sided Cpu automatically while other products
  under the same parameter stay two-sided.
- **Nelson (Western Electric) rules**, on top of classic UCL/LCL
  breach: 2-of-3 beyond 2σ, 4-of-5 beyond 1σ, and 9-consecutive-same-side
  — pattern-based signals that catch a process drifting *before* it
  ever crosses a control limit. Paired with an explicit **OOS/OOT split**
  (Out of Specification vs. Out of Trend — independent concepts,
  reported separately, never merged into one count).
- **Ppk/Pp** (long-term capability, overall sample std-dev) alongside
  Cpk/Cpu (short-term, subgroup-based) — with an interpretive comment
  when they diverge — plus a non-blocking **Shapiro-Wilk normality
  check** on the underlying data.
- Every formula and constant (A2/D3/D4/d2, the I-chart's 2.66 constant,
  Cpk/Cpu/Ppk/Pp, including the R̄=0 edge case) is validated against a
  textbook or industry worked example before being trusted — see
  `tests/` (164 automated tests across 13 files, plus a data-driven
  `validation/` folder of reference CSVs, run on every push with
  coverage reporting via GitHub Actions — see badge above).
- **Raw material (hammadde) library:** 16 raw materials mapped to the
  relevant subset of the 9 parameters, kept as a clearly separate
  "Raw Material QC Reference" category from finished-product specs — no
  fabricated limits; combinations without a verified regulatory/technical
  source are left as manual entry (see `METHODOLOGY.md`).
- Result dashboard with a Cpk/Cpu level badge, an auto-generated plain-text
  summary, a shift-by-shift comparison table, and a one-page PDF report
  export — on top of the existing PNG chart export and CSV import/export.
- Built with Python + Streamlit, deployed on Streamlit Community
  Cloud. Independent, individually-developed project (built to apply
  SPC/quality-engineering coursework to a real, deployed tool).

## Ekran görüntüleri

| | |
|---|---|
| ![Veri girişi](screenshots/01_veri_girisi.png) | ![KPI paneli ve X-bar chart](screenshots/02_kpi_ve_xbar_chart.png) |
| Veri girişi + CSV import | KPI paneli ve X-bar/R chart |
| ![Kapasite histogramı](screenshots/03_capability_histogram.png) | ![Hesaplama adımları](screenshots/04_hesaplama_adimlari.png) |
| Süreç yeterlilik histogramı | Formül hesaplama adımları (şeffaflık) |
| ![I-MR chart](screenshots/05_imr_chart.png) | |
| I-MR chart (Viskozite) | |

## Desteklenen parametreler

| Parametre | Chart | Birim |
|---|---|---|
| pH | X-bar/R | pH |
| Brix | X-bar/R | °Bx |
| Aw (su aktivitesi) | X-bar/R | aw (0–1) |
| Nem/Rutubet | X-bar/R | % |
| Tuz/NaCl | X-bar/R | % |
| Titrasyon Asitliği | X-bar/R | % |
| Viskozite | I-MR | cP |
| Peroksit Değeri | I-MR | meq O2/kg |
| HMF | I-MR | mg/kg |

Tek/iki taraflı Cpk mantığı **ürün bazında** otomatik belirlenir (örn.
Bal'ın nem spesifikasyonunda sadece üst limit vardır); alt grup büyüklüğü
(n) sidebar'dan seçilebilir (varsayılan n=4, aralık n=2–10) — detaylı
mantık ve kaynaklar için [METHODOLOGY.md](METHODOLOGY.md).

"Ürün / Hammadde" seçim listesinde bitmiş ürünlerin yanında 🌾 önekiyle
16 hammadde de yer alır (her biri sadece ilgili olduğu parametrede
görünür); bitmiş ürün (TGK uyumlu) spesifikasyonlarından ayrı, açıkça
etiketlenmiş bir "Hammadde QC Referansı" kategorisidir — kaynağı
doğrulanamayan kombinasyonlarda varsayılan sayı KONULMAZ, kullanıcı
manuel girer (detay ve kaynak tablosu: [METHODOLOGY.md](METHODOLOGY.md)).

**Kapsam dışı (henüz yok):** çoklu parametre karşılaştırma, kullanıcı
hesabı/çoklu kullanıcı sistemi, veritabanı entegrasyonu (session-state +
CSV import/export yeterli) — Nelson/Western Electric kuralları artık
kapsam dışı DEĞİL, v1.2 ile eklendi (bkz. aşağıdaki bölüm).

## v1.2 — Advanced Statistical SPC

Sürekli-veri SPC motorunun istatistiksel derinliği artırıldı (yeni bir
istatistik ailesi değil — mevcut kontrol grafiği/Cpk motorunun üzerine):

- **Nelson kuralları** — UCL/LCL aşımı dışında 3 örüntü sinyali (2/3
  nokta 2σ dışı, 4/5 nokta 1σ dışı, 9 ardışık nokta merkezin aynı
  tarafında), grafikte **Zone Shading** (±1σ/±2σ/±3σ bantları) ile
  görselleştirilir.
- **OOS/OOT ayrımı** — spesifikasyon dışı ham ölçüm (OOS) ile
  istatistiksel sapma sinyali (OOT: limit aşımı veya Nelson kuralı)
  artık iki bağımsız sayı olarak ayrı raporlanır.
- **Ppk/Pp** (uzun vadeli, genel örneklem std sapmasıyla) + Cpk-vs-Ppk
  yorum cümlesi, ve **Shapiro-Wilk normallik testi** (engelleyici değil,
  şeffaflık amaçlı).
- **Veri girişi iyileştirmeleri:** Excel/pano'dan yapıştırarak toplu
  veri girişi, tek tek alt grup/ölçüm düzenleme-silme
  (`st.data_editor`), kayıt sonrası spesifikasyon-dışı uyarısı.
- **Manuel kontrol limiti hesaplayıcı** (elle x̿/R̄ veya x̄/MR̄ girip
  UCL/LCL üretir) ve **metodolojik SSS** (Nelson/OOS-OOT/normallik/Ppk
  kavramlarını açıklayan 4 soru-cevap).
- **PDF raporuna otomatik yorum cümlesi** — trend yönü ve/veya Nelson
  sinyali varsa özet metnine otomatik eklenir.
- **Demo senaryo galerisi** — İyi süreç / Kayan ortalama / Düşük Cpk /
  Trend, Nelson sinyallerini örneklerle göstermek için.

Detaylı madde listesi ve doğrulama notları: [METHODOLOGY.md](METHODOLOGY.md).

## Hızlı Hesaplayıcılar — Totox

Ayrı bir sekmede, SPC akışından izole, tek seferlik bir hesaplayıcı:
`Totox = 2 × Peroksit Değeri + Anisidin Değeri`. Kullanıcı iki değeri
elle girer; sonuç birleşik bir gauge + renkli badge ile gösterilir,
limite ne kadar yakın/uzak olunduğunu belirten bir duyarlılık cümlesi
eşlik eder (örn. "%50 altında, 13.00 birim pay var"), ve sonuçlar bu
oturuma özel bir geçmiş listesine eklenebilir.

## Nasıl çalıştırılır

**Local:**
```bash
pip install -r requirements.txt
cd src
streamlit run app.py
```
Uygulama varsayılan olarak `http://localhost:8501` üzerinde açılır.

**Demo:** [spc-foodlab.streamlit.app](https://spc-foodlab.streamlit.app/)

## Teknik yığın

- **Streamlit** (Python) — form, hesaplama ve grafik tek pakette
- **matplotlib + scipy** — kontrol grafikleri ve kapasite histogramı
- **fpdf2** — tek sayfalık PDF analiz raporu export'u
- Hafif CSS geçişleri/animasyonları (buton hover, kart hover gölgesi,
  uyarı kutularında fade-in) — arayüzü canlandırır, dikkat dağıtmaz
- **Deploy:** Streamlit Community Cloud
- Veri kalıcılığı: session-state (uygulama içi) + CSV import/export —
  v1'de veritabanı entegrasyonu yok

## Proje yapısı

```
spc-foodlab/
├── .github/workflows/
│   └── tests.yml        # Her push'ta pytest calistiran GitHub Actions CI
├── src/
│   ├── app.py             # Streamlit arayüzü (4 sekme)
│   ├── spc_core.py        # X-bar/R, I-MR, Cpk/Cpu ve Ppk/Pp hesaplama çekirdeği
│   ├── nelson_rules.py    # Nelson (Western Electric) örüntü kuralları (2/3-2σ, 4/5-1σ, 9-ardışık)
│   ├── normality.py       # Shapiro-Wilk normallik testi ince sarmalayıcısı
│   ├── result_helpers.py  # Cpk rozeti, trend göstergesi, quick summary, Totox yorumu, demo senaryosu hedefleri
│   ├── csv_io.py          # CSV/Excel-yapıştırma içe/dışa aktarma: şema doğrulama, hata mesajları, round-trip
│   ├── pdf_report.py      # Tek sayfalık PDF analiz raporu üretimi
│   ├── demo_data.py       # Kontrollü simülasyon veri üreteci (5 davranış deseni: iyi/kayan/değişken/trend/nokta-sıçrama)
│   └── constants.py       # Sabit yapılandırma (varsayılan n=4, parametre/ürün/kaynak tabloları)
├── tests/
│   ├── test_validation.py        # X-bar/R formül doğrulama testi (pH örneği)
│   ├── test_imr_validation.py    # I-MR formül doğrulama testi (kahve sıcaklığı örneği)
│   ├── test_cpk_edge_cases.py    # Sıfır-varyasyon (R̄/MR̄=0) + geçersiz spesifikasyon (LSL≥USL) testleri
│   ├── test_ppk.py               # Ppk/Pp formül doğrulama testi (NIST Cpk örneği)
│   ├── test_nelson_rules.py      # Nelson kuralları: hand-verified sentetik senaryolar
│   ├── test_normality.py         # Shapiro-Wilk testi (scipy doküman örneğiyle doğrulama)
│   ├── test_demo_data.py         # Demo veri üreteci: davranış deseni garantileri + geriye uyumluluk
│   ├── test_chart_label_formatting.py  # Grafik etiketi decimal_places testi (statik kaynak taraması)
│   ├── test_raw_materials.py     # Hammadde kütüphanesi: ürün→parametre filtreleme, kaynak dürüstlüğü
│   ├── test_result_helpers.py    # Rozet/trend/özet/Totox-yorumu/demo-senaryosu testleri (result_helpers.py)
│   ├── test_csv_io.py            # CSV/yapıştırma şema/hata/temizleme + export→import round-trip testleri
│   ├── test_pdf_report.py        # PDF rapor üretiminin otomatik doğrulanması
│   └── test_validation_suite.py  # validation/*.csv referans dosyalarını çalıştıran testler
├── validation/           # Formül doğrulama referans veri seti (bkz. validation/README.md)
├── screenshots/         # README ekran görüntüleri
├── METHODOLOGY.md       # Formüller, doğrulama, ürün referans kaynakları, sürüm yol haritası
└── requirements.txt
```

---

📖 Detaylı formüller ve doğrulama metodolojisi için: [METHODOLOGY.md](METHODOLOGY.md)
