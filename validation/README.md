# Validation Suite

Bu klasör, `src/spc_core.py`'deki formüllerin literatür/elle çözülmüş
referans örneklerine karşı doğrulandığının **veri dosyası olarak**
kanıtıdır — `tests/test_validation.py`, `tests/test_imr_validation.py`
ve `tests/test_cpk_edge_cases.py` dosyalarındaki hardcoded karşılaştırmalarla
*aynı* değerleri içerir, ama burada tablo/CSV formatında, kaynak ve
tolerans sütunlarıyla ayrı ayrı okunabilir ve `tests/test_validation_suite.py`
tarafından programatik olarak da çalıştırılır.

## Neden ayrı bir klasör (test dosyalarının içine gömmek yerine)?

- **İncelenebilirlik:** Bir kaynağı doğrulamak için Python test kodunu
  okumaya gerek kalmadan, hangi girdi/çıktı/kaynak/tolerans kombinasyonunun
  test edildiği tek bakışta görülür.
- **Büyüyen disiplin:** Bu tek seferlik bir teslimat değil — v1.2'de
  Nelson kuralları, v1.3'te mikrobiyoloji (log10-CFU) formülleri
  eklendikçe, her biri kendi referans dosyasını buraya ekler
  (`nelson_reference.csv`, `microbiology_reference.csv` vb.).

## Klasör yapısı (v1.4 itibariyle)

```
validation/
  shared/        - parametre-bagimsiz formul dogrulamasi (X-bar/R, I-MR, Cpk/Ppk)
  microbiology/  - v1.3 log10-CFU referanslari
  chemistry/     - v1.4 Faz 1: Protein, Kul
  physical/      - v1.4 Faz 1: Kuru Madde
  optics/        - bos, v1.6 Faz 3'te (L*/a*/b*/Bulaniklik/Iletkenlik) dolacak
```

`chemistry/` ve `physical/` altındaki referanslar **YENI bir formul
DEGIL** - Protein/Kul/Kuru Madde, mevcut I-MR + Cpk/Cpu formulunu (zaten
`shared/imr_reference.csv` ve `shared/cpk_reference.csv` ile dogrulanmis)
YENIDEN KULLANIR. Buradaki dosyalar, o formulun bu YENI parametrelere de
dogru uygulandigini kanitlar - dis kaynakli bir worked example DEGIL
(Protein/Kul icin literatur worked example bulunamadi), `shared/
cpk_reference.csv`'deki "dahili matematiksel tutarlilik kontrolu"
satirlarinin AYNI kategorisi (bkz. asagidaki tablo, kaynak sutunu).

## Dosyalar

| Dosya | Kapsam | Kaynak |
|---|---|---|
| `shared/xbar_r_reference.csv` | X-bar/R kontrol limitleri (UCL) | LibreTexts Engineering, *Chemical Process Dynamics and Controls* (Woolf), 13.2 |
| `shared/imr_reference.csv` | I-MR kontrol limitleri (UCL/LCL) | 6Sigma Toolkit, I-MR Chart örneği |
| `shared/cpk_reference.csv` | Cpk/Cpu (normal durum + sıfır-varyans uç durumları) | LibreTexts pH örneğinin devamı (normal durum) + dahili matematiksel tutarlılık kontrolü (uç durumlar) |
| `shared/ppk_reference.csv` | Ppk/Pp (genel/uzun vadeli süreç yeterliliği) | NIST/SEMATECH e-Handbook Ch. 2 — Cpk'nin genel s-tabanlı formülünün worked example'i (USL=20, LSL=8, x̄=16, s=2), elle inşa edilmiş bir değer listesiyle üretildi |
| `microbiology/microbiology_reference.csv` | log10-CFU + I-MR + Cpu (v1.3) | Bilinen log10 sabitleri (log₁₀2, log₁₀3, log₁₀5) ile elle hesaplanmış LOD-ikameli örnekler |
| `chemistry/cpk_reference.csv` | Protein, Kül — I-MR + Cpk/Cpu (v1.4 Faz 1) | Dahili matematiksel tutarlılık kontrolü (5 elle seçilmiş ölçüm, formül elle uygulanmış) |
| `physical/cpk_reference.csv` | Kuru Madde — I-MR + Cpk (v1.4 Faz 1) | Dahili matematiksel tutarlılık kontrolü |
| `physical/yogunluk_refraktif_cpk_reference.csv` | Yoğunluk, Refraktif İndeks — I-MR + Cpk (v1.5 Faz 2) | Dahili matematiksel tutarlılık kontrolü |

### Nelson kuralları (v1.2) — CSV formatında DEĞİL, neden

`src/nelson_rules.py`, `tests/test_nelson_rules.py` içinde doğrulanır —
buradaki CSV+tolerans şemasına DAHİL EDİLMEDİ, bilinçli bir karar: Nelson
kuralları sayısal bir formül değil, bir **örüntü tanıma** algoritmasıdır
(girdi: bir sayı dizisi, çıktı: ihlal eden indekslerin kümesi) — yukarıdaki
`expected_ucl,tolerance` şeması "tek bir sayıyı kaynakla karşılaştır" için
tasarlandı, bir indeks kümesini temsil etmeye uygun değil. Bunun yerine
her kural, Nelson (1984)'ün tanımına göre ELLE hazırlanmış ve ELLE
doğrulanmış sentetik senaryolarla (tetikleyen + tetiklemeyen "yakın ıskalama"
durumları dahil) test edilir — `test_cpk_edge_cases.py`'nin sıfır-varyans
uç durumlarını doğrulama yöntemiyle aynı rigor, farklı format.

## Nasıl çalıştırılır

```
pytest tests/test_validation_suite.py -v
```

Bu, her CSV satırını okuyup ilgili `spc_core` fonksiyonunu çağırır ve
sonucu `tolerance` sütunundaki payla karşılaştırır — CSV'ye yeni bir
satır eklemek, kod değiştirmeden yeni bir referans örneği eklemek
anlamına gelir.
