"""
Mikrobiyoloji (log10-CFU) parametreleri icin Streamlit'e bagimli olmayan
saf mantik - LOD-alti (Limit of Detection) ikamesi ve log10 donusumu.

spc_core.py'den AYRI tutulmasinin nedeni: spc_core.py normal dagilim
varsayan genel SPC formulleridir (X-bar/R, I-MR, Cpk); mikrobiyal sayimlar
log-normal dagildigindan spc_core'a girmeden ONCE bu modulden gecmelidir.
csv_io.py/nelson_rules.py ile ayni gerekce: pytest ile Streamlit'i
calistirmadan dogrudan test edilebilir (bkz. tests/test_microbiology.py).

LOD-alti ikamesi (substitute_below_lod) ve ardindan log10 donusumu
(to_log10) HER ZAMAN app.py tarafinda kullaniciya "ham/log10 seffaflik
tablosu" ile ACIKCA gosterilir - sessizce uygulanmaz (bkz. METHODOLOGY.md
v1.3 kapsam tanimi).
"""

import math


def substitute_below_lod(raw: float | None, is_below_lod: bool, lod: float | None) -> float:
    """LOD-alti (ornegin '<10 KOB/g') bir olcumu, SPC hesabinda kullanilacak
    sayisal degere cevirir - standart ikame kurali LOD/2'dir (ICMSF/FDA BAM
    konvensiyonu). is_below_lod=False ise ham deger DOGRUDAN kullanilir.

    is_below_lod=True iken lod=None VEYA lod<=0 olmasi cagiran kodda bir
    hata anlamina gelir (UI'da LOD alani bos birakilmis) - sessizce yanlis
    bir sayi (orn. 0) uretmek yerine ACIKCA patlar."""
    if is_below_lod:
        if lod is None or lod <= 0:
            raise ValueError(
                "is_below_lod=True iken gecerli bir LOD (>0) zorunludur - "
                "LOD/2 ikamesi hesaplanamaz."
            )
        return lod / 2
    if raw is None:
        raise ValueError("is_below_lod=False iken ham deger (raw) zorunludur.")
    return raw


def to_log10(value: float) -> float:
    """Bir KOB/g degerini log10 olceğine cevirir. value<=0 mikrobiyolojik
    olarak imkansizdir (0 KOB/g LOD-alti olarak ayrica temsil edilir, asla
    ham deger olarak gecilmez) - bu durumda ValueError firlatilir, log10(0)
    -inf'i sessizce spc_core'a sizdirmak yerine."""
    if value <= 0:
        raise ValueError(f"log10 donusumu icin deger pozitif olmalidir, alinan: {value}")
    return math.log10(value)


def build_subgroup_entry(raw: float | None, is_below_lod: bool, lod: float | None) -> dict:
    """Tek bir mikrobiyoloji olcumunu, subgroup eleman sozlugune cevirir:
    {"raw", "is_below_lod", "lod", "log_value"}. TEK merkezi insa noktasi -
    veri giris formu, CSV import, yapistirma ve duzenleme paneli HEPSI bu
    fonksiyonu cagirir (kopyala-yapistirilmis ikame/log10 mantigi yerine)."""
    used = substitute_below_lod(raw, is_below_lod, lod)
    log_value = to_log10(used)
    return {"raw": raw, "is_below_lod": is_below_lod, "lod": lod, "log_value": log_value}
