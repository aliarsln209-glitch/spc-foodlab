import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest

from custom_parameters_db import (
    get_connection,
    insert_custom_parameter,
    list_custom_parameters,
    insert_custom_measurement,
    list_custom_measurements,
    delete_custom_measurements,
)


@pytest.fixture
def conn(tmp_path):
    c = get_connection(str(tmp_path / "test_custom.db"))
    yield c
    c.close()


def _base_kwargs(**overrides):
    kwargs = dict(
        name="Ekstraksiyon Verimi", unit="%", chart_type="I-MR", subgroup_size=None,
        data_type="continuous", lsl=None, usl=85.0, has_specification=True,
        one_sided=True, log_scale=False, decimal_places=2,
        min_value=None, max_value=None,
    )
    kwargs.update(overrides)
    return kwargs


def test_insert_and_list_custom_parameter(conn):
    pid = insert_custom_parameter(conn, **_base_kwargs())
    rows = list_custom_parameters(conn)
    assert len(rows) == 1
    assert rows[0]["id"] == pid
    assert rows[0]["name"] == "Ekstraksiyon Verimi"
    assert rows[0]["unit"] == "%"
    assert rows[0]["usl"] == 85.0
    assert rows[0]["lsl"] is None
    assert rows[0]["has_specification"] == 1
    assert rows[0]["log_scale"] == 0


def test_insert_duplicate_name_raises(conn):
    insert_custom_parameter(conn, **_base_kwargs())
    with pytest.raises(ValueError, match="zaten mevcut"):
        insert_custom_parameter(conn, **_base_kwargs())


def test_insert_and_list_custom_measurements(conn):
    pid = insert_custom_parameter(conn, **_base_kwargs())
    insert_custom_measurement(
        conn, parameter_id=pid, shift="-", values=[82.5], notes="", urun="",
        timestamp="2026-08-27T10:00:00", lot_no="L1",
    )
    insert_custom_measurement(
        conn, parameter_id=pid, shift="-", values=[83.1], notes="not", urun="Urun A",
        timestamp="2026-08-27T11:00:00", lot_no="L2",
    )
    rows = list_custom_measurements(conn, pid)
    assert len(rows) == 2
    assert rows[0]["values"] == [82.5]
    assert rows[1]["values"] == [83.1]
    assert rows[1]["lot_no"] == "L2"


def test_list_custom_measurements_empty_for_unknown_parameter(conn):
    assert list_custom_measurements(conn, 999) == []


def test_delete_custom_measurements_clears_only_that_parameter(conn):
    pid1 = insert_custom_parameter(conn, **_base_kwargs())
    pid2 = insert_custom_parameter(conn, **_base_kwargs(name="Diger Analiz"))
    insert_custom_measurement(
        conn, parameter_id=pid1, shift="-", values=[82.5], notes="", urun="",
        timestamp="2026-08-27T10:00:00", lot_no="L1",
    )
    insert_custom_measurement(
        conn, parameter_id=pid1, shift="-", values=[83.1], notes="", urun="",
        timestamp="2026-08-27T11:00:00", lot_no="L2",
    )
    insert_custom_measurement(
        conn, parameter_id=pid2, shift="-", values=[10.0], notes="", urun="",
        timestamp="2026-08-27T12:00:00", lot_no="L3",
    )

    delete_custom_measurements(conn, pid1)

    assert list_custom_measurements(conn, pid1) == []
    assert len(list_custom_measurements(conn, pid2)) == 1


def test_delete_custom_measurements_unknown_parameter_is_noop(conn):
    pid = insert_custom_parameter(conn, **_base_kwargs())
    insert_custom_measurement(
        conn, parameter_id=pid, shift="-", values=[82.5], notes="", urun="",
        timestamp="2026-08-27T10:00:00", lot_no="L1",
    )
    delete_custom_measurements(conn, 999)
    assert len(list_custom_measurements(conn, pid)) == 1


def test_get_connection_with_bare_filename_no_directory(tmp_path, monkeypatch):
    # Fix 8: db_path'in dizin bileseni yoksa ("" doner) os.makedirs("")
    # FileNotFoundError firlatmamali.
    monkeypatch.chdir(tmp_path)
    c = get_connection("bare_no_dir.db")
    try:
        insert_custom_parameter(c, **_base_kwargs())
        assert len(list_custom_parameters(c)) == 1
    finally:
        c.close()


def test_reopening_connection_preserves_schema(tmp_path):
    db_path = str(tmp_path / "reopen.db")
    conn1 = get_connection(db_path)
    insert_custom_parameter(conn1, **_base_kwargs())
    conn1.close()

    conn2 = get_connection(db_path)
    rows = list_custom_parameters(conn2)
    conn2.close()
    assert len(rows) == 1
