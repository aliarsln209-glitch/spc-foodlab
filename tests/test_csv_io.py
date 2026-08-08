"""
src/csv_io.py testleri: CSV schema dogrulama, hata mesaji uretimi, bos/
yinelenen satir temizleme ve en onemlisi export->import round-trip -
CSV olarak indirilen bir dosyanin aynen geri yuklenebildiginin kaniti
(bkz. METHODOLOGY.md v1.1 "Export -> import round-trip testi" maddesi).
"""

import io
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pandas as pd

from csv_io import (
    count_duplicate_rows,
    drop_blank_rows,
    friendly_csv_read_error,
    friendly_numeric_error,
    parse_uploaded_dataframe,
    subgroups_to_records,
)


# --- friendly_numeric_error --------------------------------------------

def test_numeric_error_detects_decimal_comma():
    raw = pd.Series(["7.01", "1,25", "7.03"])
    numeric = pd.to_numeric(raw, errors="coerce")
    msg = friendly_numeric_error(raw, numeric, "pH")
    assert "1,25" in msg
    assert "1.25" in msg
    assert "2." in msg  # 2. satir


def test_numeric_error_detects_blank_cell():
    raw = pd.Series(["7.01", "", "7.03"])
    numeric = pd.to_numeric(raw, errors="coerce")
    msg = friendly_numeric_error(raw, numeric, "pH")
    assert "bos" in msg.lower()


def test_numeric_error_detects_non_numeric_text():
    raw = pd.Series(["7.01", "abc", "7.03"])
    numeric = pd.to_numeric(raw, errors="coerce")
    msg = friendly_numeric_error(raw, numeric, "pH")
    assert "abc" in msg
    assert "pH" in msg


# --- friendly_csv_read_error --------------------------------------------

def test_csv_read_error_empty_data():
    exc = pd.errors.EmptyDataError("No columns to parse from file")
    assert "bos" in friendly_csv_read_error(exc).lower()


def test_csv_read_error_parser_error():
    exc = pd.errors.ParserError("Error tokenizing data")
    assert "ayristirilamadi" in friendly_csv_read_error(exc).lower()


def test_csv_read_error_unicode_decode():
    exc = UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")
    assert "kodlamasi" in friendly_csv_read_error(exc).lower()


def test_csv_read_error_generic_fallback():
    exc = ValueError("something else")
    assert "CSV dosyasi okunamadi" in friendly_csv_read_error(exc)


# --- drop_blank_rows / count_duplicate_rows ------------------------------

def test_drop_blank_rows_removes_fully_empty_rows():
    df = pd.DataFrame({
        "Grup": [1, None, 3],
        "Vardiya": ["Sabah", None, "Gece"],
        "Olcum 1": [7.0, None, 7.2],
    })
    cleaned, dropped = drop_blank_rows(df)
    assert dropped == 1
    assert len(cleaned) == 2


def test_drop_blank_rows_keeps_partially_filled_rows():
    # Ikinci satirda "Olcum 1" bos ama "Grup" dolu - satir TAMAMEN bos
    # degil, bu yuzden silinmemeli (sadece TUM sutunlari bos olanlar silinir).
    df = pd.DataFrame({"Grup": [1, 2, 3], "Olcum 1": [7.0, None, 7.2]})
    cleaned, dropped = drop_blank_rows(df)
    assert dropped == 0
    assert len(cleaned) == 3


def test_count_duplicate_rows_detects_exact_duplicates():
    # 0. ve 1. satir TUM sutunlarda birebir ayni (Grup dahil) - gercek
    # bir yinelenen satir senaryosu (orn. CSV yanlislikla iki kez eklenmis).
    df = pd.DataFrame({
        "Grup": [1, 1, 3],
        "Vardiya": ["Sabah", "Sabah", "Gece"],
        "Olcum 1": [7.0, 7.0, 7.2],
    })
    assert count_duplicate_rows(df) == 1


def test_count_duplicate_rows_zero_when_all_unique():
    df = pd.DataFrame({"Olcum 1": [7.0, 7.1, 7.2]})
    assert count_duplicate_rows(df) == 0


# --- parse_uploaded_dataframe: hata durumlari -----------------------------

def test_parse_individual_wrong_column_count():
    df = pd.DataFrame({"Sira": [1, 2], "Olcum 1": [7.0, 7.1], "Olcum 2": [7.2, 7.3]})
    subgroups, err = parse_uploaded_dataframe(df, is_individual=True, subgroup_n=4, shift_options=["Sabah"])
    assert subgroups is None
    assert "1 'Olcum'" in err


def test_parse_subgroup_wrong_column_count():
    df = pd.DataFrame({"Grup": [1], "Olcum 1": [7.0], "Olcum 2": [7.1]})
    subgroups, err = parse_uploaded_dataframe(df, is_individual=False, subgroup_n=4, shift_options=["Sabah"])
    assert subgroups is None
    assert "4 'Olcum'" in err


def test_parse_individual_non_numeric_value_returns_friendly_error():
    df = pd.DataFrame({"Sira": [1, 2], "Olcum 1": ["7.0", "abc"]})
    subgroups, err = parse_uploaded_dataframe(df, is_individual=True, subgroup_n=4, shift_options=["Sabah"])
    assert subgroups is None
    assert "abc" in err


# --- parse_uploaded_dataframe: basarili durumlar --------------------------

def test_parse_individual_success():
    df = pd.DataFrame({"Sira": [1, 2, 3], "Olcum 1": [7.0, 7.1, 7.2]})
    subgroups, err = parse_uploaded_dataframe(df, is_individual=True, subgroup_n=4, shift_options=["Sabah"])
    assert err is None
    assert subgroups == [
        {"shift": "-", "values": [7.0]},
        {"shift": "-", "values": [7.1]},
        {"shift": "-", "values": [7.2]},
    ]


def test_parse_subgroup_success_with_valid_shift():
    df = pd.DataFrame({
        "Grup": [1, 2],
        "Vardiya": ["Sabah", "Gece"],
        "Olcum 1": [7.0, 7.1],
        "Olcum 2": [7.05, 7.15],
    })
    subgroups, err = parse_uploaded_dataframe(
        df, is_individual=False, subgroup_n=2, shift_options=["Sabah", "Ogle", "Gece"]
    )
    assert err is None
    assert subgroups[0] == {"shift": "Sabah", "values": [7.0, 7.05]}
    assert subgroups[1] == {"shift": "Gece", "values": [7.1, 7.15]}


def test_parse_subgroup_missing_shift_column_falls_back_to_first_option():
    df = pd.DataFrame({"Grup": [1], "Olcum 1": [7.0], "Olcum 2": [7.1]})
    subgroups, err = parse_uploaded_dataframe(
        df, is_individual=False, subgroup_n=2, shift_options=["Sabah", "Ogle", "Gece"]
    )
    assert err is None
    assert subgroups[0]["shift"] == "Sabah"


def test_parse_subgroup_invalid_shift_value_falls_back_to_first_option():
    df = pd.DataFrame({
        "Grup": [1], "Vardiya": ["Gundoner-Vardiyasi"],
        "Olcum 1": [7.0], "Olcum 2": [7.1],
    })
    subgroups, err = parse_uploaded_dataframe(
        df, is_individual=False, subgroup_n=2, shift_options=["Sabah", "Ogle", "Gece"]
    )
    assert err is None
    assert subgroups[0]["shift"] == "Sabah"


# --- Export -> import round-trip -------------------------------------------

def test_round_trip_individual_preserves_values():
    original = [{"shift": "-", "values": [7.01]}, {"shift": "-", "values": [7.03]}, {"shift": "-", "values": [6.98]}]

    records = subgroups_to_records(original, is_individual=True)
    csv_text = pd.DataFrame(records).to_csv(index=False)
    reloaded_df = pd.read_csv(io.StringIO(csv_text))

    round_tripped, err = parse_uploaded_dataframe(
        reloaded_df, is_individual=True, subgroup_n=4, shift_options=["-"]
    )

    assert err is None
    assert round_tripped == original


def test_round_trip_subgroup_preserves_values_despite_extra_export_columns():
    # subgroups_to_records X-bar/R export'unda "Ortalama"/"Range" gibi
    # sadece goruntuleme amacli EKSTRA sutunlar da uretir (bkz. app.py'deki
    # gercek export/goruntuleme kodu) - bu sutunlar "Olcum" ile baslamadigi
    # icin parse_uploaded_dataframe tarafindan yok sayilmali ve round-trip
    # yine de tam calismali.
    original = [
        {"shift": "Sabah", "values": [7.0, 7.05, 6.98, 7.02]},
        {"shift": "Gece", "values": [7.1, 7.12, 7.08, 7.09]},
    ]

    records = subgroups_to_records(original, is_individual=False)
    assert "Ortalama" in records[0]  # export gercekten ekstra sutun icermeli (regresyon kontrolu)

    csv_text = pd.DataFrame(records).to_csv(index=False)
    reloaded_df = pd.read_csv(io.StringIO(csv_text))

    round_tripped, err = parse_uploaded_dataframe(
        reloaded_df, is_individual=False, subgroup_n=4, shift_options=["Sabah", "Ogle", "Gece"]
    )

    assert err is None
    assert round_tripped == original


if __name__ == "__main__":
    test_numeric_error_detects_decimal_comma()
    test_numeric_error_detects_blank_cell()
    test_numeric_error_detects_non_numeric_text()
    test_csv_read_error_empty_data()
    test_csv_read_error_parser_error()
    test_csv_read_error_unicode_decode()
    test_csv_read_error_generic_fallback()
    test_drop_blank_rows_removes_fully_empty_rows()
    test_drop_blank_rows_keeps_partially_filled_rows()
    test_count_duplicate_rows_detects_exact_duplicates()
    test_count_duplicate_rows_zero_when_all_unique()
    test_parse_individual_wrong_column_count()
    test_parse_subgroup_wrong_column_count()
    test_parse_individual_non_numeric_value_returns_friendly_error()
    test_parse_individual_success()
    test_parse_subgroup_success_with_valid_shift()
    test_parse_subgroup_missing_shift_column_falls_back_to_first_option()
    test_parse_subgroup_invalid_shift_value_falls_back_to_first_option()
    test_round_trip_individual_preserves_values()
    test_round_trip_subgroup_preserves_values_despite_extra_export_columns()
    print("CSV_IO TESTLERI GECTI")
