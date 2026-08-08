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

## Dosyalar

| Dosya | Kapsam | Kaynak |
|---|---|---|
| `xbar_r_reference.csv` | X-bar/R kontrol limitleri (UCL) | LibreTexts Engineering, *Chemical Process Dynamics and Controls* (Woolf), 13.2 |
| `imr_reference.csv` | I-MR kontrol limitleri (UCL/LCL) | 6Sigma Toolkit, I-MR Chart örneği |
| `cpk_reference.csv` | Cpk/Cpu (normal durum + sıfır-varyans uç durumları) | LibreTexts pH örneğinin devamı (normal durum) + dahili matematiksel tutarlılık kontrolü (uç durumlar) |

## Nasıl çalıştırılır

```
pytest tests/test_validation_suite.py -v
```

Bu, her CSV satırını okuyup ilgili `spc_core` fonksiyonunu çağırır ve
sonucu `tolerance` sütunundaki payla karşılaştırır — CSV'ye yeni bir
satır eklemek, kod değiştirmeden yeni bir referans örneği eklemek
anlamına gelir.
