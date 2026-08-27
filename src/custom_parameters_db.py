"""Kullanici tanimli ozel analiz parametreleri icin SQLite katmani - saf
mantik, Streamlit'e HIC bagimli degil (qc_converters.py/spc_core.py ile
ayni mimari ilke). Streamlit/session_state entegrasyonu app.py'de
(parameter_registry.py uzerinden) yapilir.

Kalicilik notu: Streamlit Community Cloud'da dosya sistemi redeploy/
uyku-sonrasi uyanmada sifirlanabilir - bu MVP icin bilinen, kabul edilmis
bir kisit (bkz. plan Global Constraints). Yerel/kendi makinede calisirken
bu sinirlama gecerli degildir.
"""

import json
import os
import sqlite3
from datetime import datetime

DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "custom_parameters.db")


def get_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Baglanti acar, dizin yoksa olusturur, semayi (yoksa) kurar. Her
    cagrida CREATE TABLE IF NOT EXISTS calistigi icin idempotenttir -
    var olan bir DB'ye tekrar baglanmak semayi bozmaz."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    _ensure_schema(conn)
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS custom_parameters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            unit TEXT NOT NULL,
            chart_type TEXT NOT NULL CHECK(chart_type IN ('I-MR', 'Xbar-R')),
            subgroup_size INTEGER,
            data_type TEXT NOT NULL CHECK(data_type IN ('continuous', 'count')),
            lsl REAL,
            usl REAL,
            has_specification INTEGER NOT NULL,
            one_sided INTEGER NOT NULL DEFAULT 0,
            log_scale INTEGER NOT NULL DEFAULT 0,
            decimal_places INTEGER NOT NULL DEFAULT 2,
            min_value REAL,
            max_value REAL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS custom_measurements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parameter_id INTEGER NOT NULL REFERENCES custom_parameters(id),
            shift TEXT,
            values_json TEXT NOT NULL,
            notes TEXT,
            urun TEXT,
            timestamp TEXT NOT NULL,
            lot_no TEXT
        )
        """
    )
    conn.commit()


def insert_custom_parameter(
    conn: sqlite3.Connection, *, name: str, unit: str, chart_type: str,
    subgroup_size: int | None, data_type: str, lsl: float | None, usl: float | None,
    has_specification: bool, one_sided: bool, log_scale: bool, decimal_places: int,
    min_value: float | None, max_value: float | None,
) -> int:
    """Yeni bir ozel parametre tanimi ekler. Ad benzersizligi burada
    (uygulama katmaninda, veritabani UNIQUE kisitindan ONCE) kontrol
    edilir - boylece sqlite3.IntegrityError yerine acik/anlasilir bir
    ValueError alinir (built-in parametre isimleriyle carpisma kontrolu
    parameter_registry.py'de, bu fonksiyonun CAGIRANI tarafindan yapilir)."""
    existing = {row["name"] for row in conn.execute("SELECT name FROM custom_parameters")}
    if name in existing:
        raise ValueError(f"'{name}' adinda bir ozel parametre zaten mevcut")
    cur = conn.execute(
        """
        INSERT INTO custom_parameters
            (name, unit, chart_type, subgroup_size, data_type, lsl, usl,
             has_specification, one_sided, log_scale, decimal_places,
             min_value, max_value, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            name, unit, chart_type, subgroup_size, data_type, lsl, usl,
            int(has_specification), int(one_sided), int(log_scale), decimal_places,
            min_value, max_value, datetime.now().isoformat(timespec="seconds"),
        ),
    )
    conn.commit()
    return cur.lastrowid


def list_custom_parameters(conn: sqlite3.Connection) -> list[dict]:
    rows = conn.execute("SELECT * FROM custom_parameters ORDER BY id").fetchall()
    return [dict(r) for r in rows]


def insert_custom_measurement(
    conn: sqlite3.Connection, *, parameter_id: int, shift: str, values: list[float],
    notes: str, urun: str, timestamp: str, lot_no: str,
) -> None:
    conn.execute(
        """
        INSERT INTO custom_measurements
            (parameter_id, shift, values_json, notes, urun, timestamp, lot_no)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (parameter_id, shift, json.dumps(values), notes, urun, timestamp, lot_no),
    )
    conn.commit()


def list_custom_measurements(conn: sqlite3.Connection, parameter_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM custom_measurements WHERE parameter_id = ? ORDER BY id",
        (parameter_id,),
    ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["values"] = json.loads(d.pop("values_json"))
        out.append(d)
    return out
