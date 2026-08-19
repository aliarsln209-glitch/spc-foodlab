# validation/process/

Bu klasör, chemistry/physical/optics/microbiology'den AYRI bir kategoridir:
buradaki referanslar **ürün spesifikasyonu DEĞİL**, QC Veri Dönüştürücüler
(v1.7 Faz 1) için ölçüm standardizasyon formülü doğrulamasıdır (AOAC
gravimetrik nem; ICUMSA Brix düzeltmesi kaynak doğrulandığında buraya
eklenecek, bkz. plan Task 8-9; ileride Mohr/AOAC titrimetrik faktörler).

**Önemli - `cpk_reference.csv` ne KANITLAMAZ:** Bu dosyadaki tek satır (AOAC
925.10 worked example), `optics/cpk_reference.csv` ile aynı yaklaşımı izler
(bkz. `tests/test_validation_suite.py`'deki `test_optics_cpk_reference_csv_matches_formula`
yorumu): sadece Cpk formülünün genel mekanizmasını dahili olarak sınayan bir
kontrol - bu formül zaten 6 farklı referans CSV'sinde (chemistry, physical,
optics, ppk vb.) ayrıca doğrulanmıştır. Bu satır, `gravimetric_moisture()`
fonksiyonunun kendisinin (AOAC 925.10 nem/kuru madde formülü) literatür
kaynaklı bir doğrulaması DEĞİLDİR. `gravimetric_moisture()` formülünün
kendisi elle hesaplanmış bir örnekle `tests/test_qc_converters.py`'deki
`test_gravimetric_moisture_basic_worked_example` testinde doğrulanır.

Detay: [METHODOLOGY.md](../../METHODOLOGY.md) → "v1.7 — QC Veri Dönüştürücüler".
