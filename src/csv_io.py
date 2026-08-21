"""
CSV ice/disa aktarma icin Streamlit'e bagimli olmayan saf mantik.

app.py'nin CSV yukleme/indirme UI kodu (dosya secici, hata kutulari,
onay mesajlari) burada degil - sadece "veriyi ayristir/dogrula/donustur"
katmani burada, boylece pytest ile Streamlit'i calistirmadan dogrudan
test edilebilir (bkz. tests/test_csv_io.py). Ayni ayrim spc_core.py ve
result_helpers.py icin de gecerlidir.
"""

import re
from datetime import datetime

import pandas as pd

from microbiology import build_subgroup_entry

_DECIMAL_COMMA_RE = re.compile(r"^-?\d+,\d+$")
_BELOW_LOD_PASTE_RE = re.compile(r"^<\s*(LOD|[\d.,]+)$", re.IGNORECASE)


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


def subgroups_to_records(subgroups: list[dict], is_individual: bool, is_microbio: bool = False) -> list[dict]:
    """Session state formatindaki subgroups listesini CSV/tablo satirlarina
    cevirir - hem 'Ham verileri goruntule' tablosunda hem CSV export'ta
    kullanilan TEK ortak fonksiyon (onceden ikisi de app.py icinde ayri
    ayri elle olusturuluyordu).

    is_microbio=True (yalnizca is_individual=True ile birlikte anlamlidir):
    'Olcum 1' yerine Raw/LOD altimi/LOD/log10 sutunlari uretilir - "values"
    icindeki tek eleman ZATEN log10 degeridir (bkz. app.py'nin subgroup
    dict'e ek olarak tuttugu 'raw'/'is_below_lod'/'lod' anahtarlari),
    kullaniciya HAM KOB/g ve log10'u YAN YANA gosterip seffafligi korur."""
    rows = []
    for i, sg in enumerate(subgroups, start=1):
        vals = sg["values"]
        trace = {
            "Parti/Lot No": sg.get("lot_no", ""),
            "Not": sg.get("notes", ""),
            "Urun": sg.get("urun", ""),
            "Zaman": sg.get("timestamp", ""),
        }
        if is_individual and is_microbio:
            is_below = sg.get("is_below_lod", False)
            lod = sg.get("lod")
            used_value = (lod / 2) if (is_below and lod is not None) else sg.get("raw")
            rows.append({
                "Sira": i,
                "Raw (KOB/g)": sg.get("raw"),
                "LOD altimi": is_below,
                "LOD": lod,
                "Kullanilan (KOB/g)": used_value,
                "log10": vals[0],
                **trace,
            })
        elif is_individual:
            rows.append({
                "Sira": i,
                **{f"Olcum {j + 1}": v for j, v in enumerate(vals)},
                **trace,
            })
        else:
            rows.append({
                "Grup": i,
                "Vardiya": sg["shift"],
                **{f"Olcum {j + 1}": v for j, v in enumerate(vals)},
                "Ortalama": sum(vals) / len(vals),
                "Range": max(vals) - min(vals),
                **trace,
            })
    return rows


def _parse_microbio_dataframe(
    df: pd.DataFrame, unit: str, default_lod: float | None, default_urun: str = "",
) -> tuple[list[dict] | None, str | None]:
    """parse_uploaded_dataframe'in is_microbio=True dali - 'Raw (KOB/g)'
    sutununu (yoksa 'Olcum 1'i HAM KOB/g olarak) okur, opsiyonel 'LOD altimi'
    (bool-benzeri: True/False, Evet/Hayir) ve 'LOD' sutunlarini kullanir.
    Sutun yoksa is_below_lod=False / lod=default_lod varsayilir. Asil
    ikame/log10 mantigi burada YAZILMAZ - microbiology.build_subgroup_entry
    cagrilir (TEK merkezi insa noktasi). v2: lot_no/notes/urun/timestamp
    sutunlari df'de VARSA korunur, YOKSA sirasiyla ""/""/default_urun/
    simdiki-zamana duser (bkz. docs/superpowers/specs/2026-08-21-
    paylasilan-subgroups-izlenebilirlik-design.md)."""
    raw_col = "Raw (KOB/g)" if "Raw (KOB/g)" in df.columns else "Olcum 1"
    if raw_col not in df.columns:
        return None, (
            "Beklenen sutun bulunamadi: mikrobiyoloji parametreleri icin 'Raw (KOB/g)' "
            "(veya 'Olcum 1') sutunu gereklidir. CSV'deki sutunlar: "
            f"{', '.join(df.columns) or '(sutun yok)'}."
        )

    below_col = next((c for c in df.columns if c.lower() in ("lod altimi", "is_below_lod")), None)
    lod_col = next((c for c in df.columns if c.lower() == "lod"), None)
    lot_no_col = "lot_no" if "lot_no" in df.columns else None
    notes_col = "notes" if "notes" in df.columns else None
    urun_col = "urun" if "urun" in df.columns else None
    timestamp_col = "timestamp" if "timestamp" in df.columns else None

    subgroups = []
    for i in range(len(df)):
        raw_cell = df[raw_col].iloc[i]
        is_below = False
        if below_col is not None:
            below_cell = df[below_col].iloc[i]
            is_below = str(below_cell).strip().lower() in ("true", "1", "evet", "yes")
        lod = default_lod
        if lod_col is not None and pd.notna(df[lod_col].iloc[i]):
            lod = float(df[lod_col].iloc[i])

        raw_val = None if (is_below or pd.isna(raw_cell)) else float(raw_cell)
        try:
            entry = build_subgroup_entry(raw=raw_val, is_below_lod=is_below, lod=lod)
        except ValueError as exc:
            return None, f"{i + 1}. satir: {exc}"
        subgroups.append({
            "shift": "-", "values": [entry["log_value"]],
            "raw": entry["raw"], "is_below_lod": entry["is_below_lod"], "lod": entry["lod"],
            "lot_no": str(df[lot_no_col].iloc[i]) if lot_no_col and pd.notna(df[lot_no_col].iloc[i]) else "",
            "notes": str(df[notes_col].iloc[i]) if notes_col and pd.notna(df[notes_col].iloc[i]) else "",
            "urun": str(df[urun_col].iloc[i]) if urun_col and pd.notna(df[urun_col].iloc[i]) else default_urun,
            "timestamp": (
                str(df[timestamp_col].iloc[i]) if timestamp_col and pd.notna(df[timestamp_col].iloc[i])
                else datetime.now().isoformat(timespec="seconds")
            ),
        })
    return subgroups, None


def parse_uploaded_dataframe(
    df: pd.DataFrame, is_individual: bool, subgroup_n: int, shift_options: list[str], unit: str = "",
    is_microbio: bool = False, default_lod: float | None = None, default_urun: str = "",
) -> tuple[list[dict] | None, str | None]:
    """CSV'den okunan DataFrame'i subgroups formatina (session_state.subgroups
    ile ayni sekil) cevirir. Basarili olursa (subgroups, None), basarisiz
    olursa (None, kullaniciya gosterilecek Turkce hata mesaji) dondurur.
    'Ortalama'/'Range' gibi export'ta bulunan ama 'Olcum' ile baslamayan
    ekstra sutunlar yok sayilir - export edilen bir dosyanin aynen geri
    yuklenebilmesi (round-trip) bu yuzden calisir, bkz. tests/test_csv_io.py.

    is_microbio=True (sadece is_individual=True ile birlikte kullanilir):
    HAM KOB/g + opsiyonel LOD-altmi/LOD sutunlarini okuyup
    microbiology.build_subgroup_entry uzerinden gecirir - bkz.
    _parse_microbio_dataframe.

    v2: lot_no/notes/urun/timestamp sutunlari df'de VARSA korunur (round-trip
    icin gerekli - "Degisiklikleri kaydet" bu fonksiyonu kullanir), YOKSA
    sirasiyla ""/""/default_urun/simdiki-zamana duser."""
    if is_individual and is_microbio:
        return _parse_microbio_dataframe(df, unit, default_lod, default_urun)

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

    lot_no_col = "lot_no" if "lot_no" in df.columns else None
    notes_col = "notes" if "notes" in df.columns else None
    urun_col = "urun" if "urun" in df.columns else None
    timestamp_col = "timestamp" if "timestamp" in df.columns else None

    def _trace_fields(i: int) -> dict:
        return {
            "lot_no": str(df[lot_no_col].iloc[i]) if lot_no_col and pd.notna(df[lot_no_col].iloc[i]) else "",
            "notes": str(df[notes_col].iloc[i]) if notes_col and pd.notna(df[notes_col].iloc[i]) else "",
            "urun": str(df[urun_col].iloc[i]) if urun_col and pd.notna(df[urun_col].iloc[i]) else default_urun,
            "timestamp": (
                str(df[timestamp_col].iloc[i]) if timestamp_col and pd.notna(df[timestamp_col].iloc[i])
                else datetime.now().isoformat(timespec="seconds")
            ),
        }

    if is_individual:
        raw_series = df[measurement_cols[0]]
        numeric_vals = pd.to_numeric(raw_series, errors="coerce")
        if numeric_vals.isna().any():
            return None, friendly_numeric_error(raw_series, numeric_vals, unit)
        subgroups = [
            {"shift": "-", "values": [float(v)], **_trace_fields(i)}
            for i, v in enumerate(numeric_vals)
        ]
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
        subgroups.append({"shift": shift_val, "values": vals, **_trace_fields(i)})
    return subgroups, None


def _parse_pasted_float(raw: str, unit: str, line_no: int, col_no: int) -> tuple[float | None, str | None]:
    """Yapistirilan metindeki TEK bir hucreyi sayiya cevirir. parse_uploaded_
    dataframe'deki friendly_numeric_error ile AYNI virgul-ondalik toleransini
    saglar, ama pandas Series yerine DUZ METIN uzerinde calisir (yapistirma
    akisi pandas'a hic girmez - satir/sutun bazinda dogrudan string split)."""
    stripped = raw.strip()
    if stripped == "":
        return None, (
            f"{line_no}. satir, {col_no}. sutun: hucre bos - her hucre bir "
            f"{unit} sayisi icermelidir."
        )
    candidate = stripped.replace(",", ".") if _DECIMAL_COMMA_RE.match(stripped) else stripped
    try:
        return float(candidate), None
    except ValueError:
        return None, (
            f"{line_no}. satir, {col_no}. sutun: '{stripped}' sayiya cevrilemedi - "
            f"bu hucre yalnizca sayisal bir {unit} olcumu icermelidir."
        )


def parse_pasted_text(
    text: str, is_individual: bool, subgroup_n: int, shift_options: list[str], unit: str = "",
    is_microbio: bool = False, default_lod: float | None = None,
) -> tuple[list[dict] | None, str | None]:
    """Excel/pano'dan kopyalanan HAM (basliksiz) veriyi subgroups formatina
    cevirir - parse_uploaded_dataframe'in aksine "Olcum N" basligi ARANMAZ:
    kullanici Excel'de bir hucre araligini secip dogrudan kopyala-yapistir
    yapar (Excel'in varsayilan kopyalama formati SEKME-ayrilmis satirlardir).
    Satir basina bir alt grup/olcum, sutunlar HAM sayilardir.

    I-MR: her satirda TAM 1 deger beklenir.
    X-bar/R: her satirda TAM subgroup_n deger (vardiya varsayilan ilk
    secenek olur) VEYA basinda bir vardiya adiyla subgroup_n+1 deger -
    ilk hucre shift_options'taki bir degerle (buyuk/kucuk harf, bosluk
    toleransli) eslesirse vardiya olarak alinir, aksi halde sutun sayisi
    hatasi verilir (sessizce yanlis yorumlanmaz).

    Basarili olursa (subgroups, None), basarisiz olursa (None, kullaniciya
    gosterilecek Turkce hata mesaji) dondurur - parse_uploaded_dataframe ile
    AYNI sozlesme, boylece cagiran taraf (app.py) ayni hata gosterme
    desenini kullanabilir."""
    lines = [ln for ln in text.strip().splitlines() if ln.strip()]
    if not lines:
        return None, "Yapistirilan metin bos gorunuyor. Excel'den bir hucre araligi kopyalayip yapistirin."

    subgroups = []
    for line_no, line in enumerate(lines, start=1):
        fields = line.split("\t")
        # Virgul, HEM sutun ayraci (elle CSV-tarzi yapistirma) HEM ondalik
        # ayiraci (TR yerel ayari, orn. "7,01") olabilir - bu ikisi AYNI
        # karakterle CAKISABILIR. Tum satir TEK bir ondalik-virgullu sayi
        # deseniyle (^-?\d+,\d+$) eslesiyorsa virgulu ondalik ayiraci say,
        # sutun ayraci olarak BOLME (aksi halde "7,01" yanlislikla ["7","01"]
        # gibi iki sahte sutuna bolunurdu). Bu, TEK sutunlu (I-MR) satirlar
        # icin tam cozer; birden fazla ondalik-virgullu sayinin virgulle
        # birlestirildigi (orn. "7,01,8,02") pathological durumlar BILEREK
        # cozulmedi - Excel'in gercek kopyalama formati zaten SEKME kullanir.
        if len(fields) == 1 and "," in line and not _DECIMAL_COMMA_RE.match(line.strip()):
            fields = line.split(",")
        fields = [f.strip() for f in fields]

        if is_individual and is_microbio:
            if len(fields) != 1:
                return None, (
                    f"{line_no}. satirda {len(fields)} deger bulundu, 1 bekleniyor "
                    f"(her satir tek bir {unit} olcumudur - LOD altindaki degerler icin "
                    "'<10' veya '<LOD' yazin)."
                )
            token = fields[0]
            below_match = _BELOW_LOD_PASTE_RE.match(token)
            if below_match:
                captured = below_match.group(1)
                lod = default_lod if captured.upper() == "LOD" else float(captured.replace(",", "."))
                raw_val, is_below = None, True
            else:
                num_val, err = _parse_pasted_float(token, unit, line_no, 1)
                if err:
                    return None, err
                raw_val, is_below, lod = num_val, False, default_lod
            try:
                entry = build_subgroup_entry(raw=raw_val, is_below_lod=is_below, lod=lod)
            except ValueError as exc:
                return None, f"{line_no}. satir: {exc}"
            subgroups.append({
                "shift": "-", "values": [entry["log_value"]],
                "raw": entry["raw"], "is_below_lod": entry["is_below_lod"], "lod": entry["lod"],
            })
            continue

        if is_individual:
            if len(fields) != 1:
                return None, (
                    f"{line_no}. satirda {len(fields)} deger bulundu, 1 bekleniyor "
                    f"(bu parametre icin her satir tek bir {unit} olcumudur)."
                )
            value, err = _parse_pasted_float(fields[0], unit, line_no, 1)
            if err:
                return None, err
            subgroups.append({"shift": "-", "values": [value]})
            continue

        shift = shift_options[0]
        measurement_fields = fields
        if len(fields) == subgroup_n + 1:
            candidate_shift = fields[0].strip().lower()
            matched = next((s for s in shift_options if s.lower() == candidate_shift), None)
            if matched:
                shift = matched
                measurement_fields = fields[1:]
        if len(measurement_fields) != subgroup_n:
            return None, (
                f"{line_no}. satirda {len(fields)} deger bulundu - {subgroup_n} "
                f"(alt grup buyuklugu n={subgroup_n}) veya basinda bir vardiya adiyla "
                f"{subgroup_n + 1} deger bekleniyor. Vardiya secenekleri: {', '.join(shift_options)}."
            )
        values = []
        for col_no, raw in enumerate(measurement_fields, start=1):
            value, err = _parse_pasted_float(raw, unit, line_no, col_no)
            if err:
                return None, err
            values.append(value)
        subgroups.append({"shift": shift, "values": values})

    return subgroups, None
