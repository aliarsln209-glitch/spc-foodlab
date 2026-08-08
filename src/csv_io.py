"""
CSV ice/disa aktarma icin Streamlit'e bagimli olmayan saf mantik.

app.py'nin CSV yukleme/indirme UI kodu (dosya secici, hata kutulari,
onay mesajlari) burada degil - sadece "veriyi ayristir/dogrula/donustur"
katmani burada, boylece pytest ile Streamlit'i calistirmadan dogrudan
test edilebilir (bkz. tests/test_csv_io.py). Ayni ayrim spc_core.py ve
result_helpers.py icin de gecerlidir.
"""

import re

import pandas as pd

_DECIMAL_COMMA_RE = re.compile(r"^-?\d+,\d+$")


def _find_first_bad_value(raw_series: pd.Series, numeric_series: pd.Series) -> tuple[int, str] | None:
    """numeric_series icinde NaN olan ilk satirin (1-index CSV satir no,
    bastaki baslik satiri haric) ve ham metin degerini dondurur. Kullaniciya
    'hangi satirda ne yanlis' sorusuna somut cevap vermek icin - bare
    'CSV okunamadi' yerine."""
    for i, (raw, num) in enumerate(zip(raw_series, numeric_series), start=1):
        if pd.isna(num):
            return i, ("" if pd.isna(raw) else str(raw))
    return None


def friendly_numeric_error(raw_series: pd.Series, numeric_series: pd.Series, unit: str) -> str:
    """Sayisal donusturme hatasini somut Turkce mesaja cevirir. En yaygin uc
    durumu (ondalik ayiraci olarak virgul kullanilmasi, orn. Excel'in TR
    yerel ayarlarindan kaynaklanan '1,25') ozel olarak yakalayip cozumu
    soyler; digerlerinde bos hucre / sayisal olmayan metin ayrimi yapar."""
    found = _find_first_bad_value(raw_series, numeric_series)
    if found is None:
        return "CSV'de sayisal olmayan veya eksik bir deger bulundu. Lutfen dosyayi kontrol edin."
    row_no, raw_value = found
    stripped = raw_value.strip()
    if stripped == "" or stripped.lower() == "nan":
        return f"{row_no}. satirda bos bir hucre bulundu. Her olcum hucresi bir sayi icermelidir."
    if _DECIMAL_COMMA_RE.match(stripped):
        return (
            f"{row_no}. satirda '{stripped}' bulundu - ondalik ayiraci nokta olmalidir "
            f"(virgul yerine '{stripped.replace(',', '.')}' yazin)."
        )
    return (
        f"{row_no}. satirda sayisal olmayan bir deger bulundu: '{stripped}'. "
        f"Bu sutun yalnizca sayisal {unit} olcumleri icermelidir."
    )


def friendly_csv_read_error(exc: Exception) -> str:
    """CSV'nin kendisi (pandas.read_csv) parse edilemediginde gosterilecek
    somut Turkce mesaj. Ham exception metni kullaniciya DOGRUDAN gosterilmez
    (teknik/Ingilizce ve cogu kullanici icin anlamsizdir) - sadece bir
    'Teknik detay' expander'inda saklanir (bkz. cagiran kod)."""
    if isinstance(exc, pd.errors.EmptyDataError):
        return "CSV dosyasi bos gorunuyor. Lutfen en az bir satir olcum verisi iceren bir dosya yukleyin."
    if isinstance(exc, pd.errors.ParserError):
        return (
            "CSV dosyasi ayristirilamadi - satirlardaki sutun sayisi tutarsiz olabilir "
            "veya dosya virgulden farkli bir ayrac kullaniyor olabilir."
        )
    if isinstance(exc, UnicodeDecodeError):
        return "Dosyanin karakter kodlamasi okunamadi. Dosyayi UTF-8 formatinda kaydedip tekrar deneyin."
    return "CSV dosyasi okunamadi. Dosyanin bozuk olmadigindan ve .csv uzantili oldugundan emin olun."


def drop_blank_rows(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Tum sutunlari bos/NaN olan satirlari cikarir (orn. Excel'den
    export edilen dosyalarda kalan bos satirlar). (temizlenmis_df,
    cikarilan_satir_sayisi) dondurur - cagiran kod kullaniciya kac
    satirin sessizce atlandigini bildirebilsin diye sayim da donuyor."""
    cleaned = df.dropna(how="all").reset_index(drop=True)
    return cleaned, len(df) - len(cleaned)


def count_duplicate_rows(df: pd.DataFrame) -> int:
    """Tum sutunlari birebir ayni olan satir sayisini dondurur. Bunlar
    OTOMATIK SILINMEZ - gida kalite kontrolde ardisik iki olcumun birebir
    ayni cikmasi gecerli bir sonuc olabilir (orn. cok kararli bir surec);
    sessizce veri silmek yanlis olur. Sadece bilgilendirme icin sayilir."""
    return int(df.duplicated().sum())


def subgroups_to_records(subgroups: list[dict], is_individual: bool) -> list[dict]:
    """Session state formatindaki subgroups listesini CSV/tablo satirlarina
    cevirir - hem 'Ham verileri goruntule' tablosunda hem CSV export'ta
    kullanilan TEK ortak fonksiyon (onceden ikisi de app.py icinde ayri
    ayri elle olusturuluyordu)."""
    rows = []
    for i, sg in enumerate(subgroups, start=1):
        vals = sg["values"]
        if is_individual:
            rows.append({
                "Sira": i,
                **{f"Olcum {j + 1}": v for j, v in enumerate(vals)},
            })
        else:
            rows.append({
                "Grup": i,
                "Vardiya": sg["shift"],
                **{f"Olcum {j + 1}": v for j, v in enumerate(vals)},
                "Ortalama": sum(vals) / len(vals),
                "Range": max(vals) - min(vals),
            })
    return rows


def parse_uploaded_dataframe(
    df: pd.DataFrame, is_individual: bool, subgroup_n: int, shift_options: list[str], unit: str = ""
) -> tuple[list[dict] | None, str | None]:
    """CSV'den okunan DataFrame'i subgroups formatina (session_state.subgroups
    ile ayni sekil) cevirir. Basarili olursa (subgroups, None), basarisiz
    olursa (None, kullaniciya gosterilecek Turkce hata mesaji) dondurur.
    'Ortalama'/'Range' gibi export'ta bulunan ama 'Olcum' ile baslamayan
    ekstra sutunlar yok sayilir - export edilen bir dosyanin aynen geri
    yuklenebilmesi (round-trip) bu yuzden calisir, bkz. tests/test_csv_io.py."""
    measurement_cols = [c for c in df.columns if c.startswith("Olcum")]
    expected_count = 1 if is_individual else subgroup_n

    if len(measurement_cols) != expected_count:
        chart_name = "I-MR" if is_individual else f"X-bar/R (n={subgroup_n})"
        return None, (
            f"Beklenen sutun bulunamadi: {chart_name} icin {expected_count} 'Olcum' "
            f"sutunu bekleniyor, {len(measurement_cols)} bulundu. CSV'deki sutunlar: "
            f"{', '.join(df.columns) or '(sutun yok)'}. 'Bos sablon indir' butonuyla "
            "dogru formati indirebilirsiniz."
        )

    if is_individual:
        raw_series = df[measurement_cols[0]]
        numeric_vals = pd.to_numeric(raw_series, errors="coerce")
        if numeric_vals.isna().any():
            return None, friendly_numeric_error(raw_series, numeric_vals, unit)
        subgroups = [{"shift": "-", "values": [float(v)]} for v in numeric_vals]
        return subgroups, None

    numeric_block = df[measurement_cols].apply(pd.to_numeric, errors="coerce")
    if numeric_block.isna().any().any():
        bad_col = next(c for c in measurement_cols if numeric_block[c].isna().any())
        return None, friendly_numeric_error(df[bad_col], numeric_block[bad_col], unit)

    shift_col = df["Vardiya"] if "Vardiya" in df.columns else None
    subgroups = []
    for i in range(len(df)):
        vals = [float(numeric_block.iloc[i][c]) for c in measurement_cols]
        shift_val = str(shift_col.iloc[i]) if shift_col is not None else shift_options[0]
        if shift_val not in shift_options:
            shift_val = shift_options[0]
        subgroups.append({"shift": shift_val, "values": vals})
    return subgroups, None
