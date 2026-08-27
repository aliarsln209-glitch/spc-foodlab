# Kullanıcı Tanımlı Özel Analiz Parametresi Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Kullanıcının kodda önceden tanımlanmamış bir analiz parametresini ("Ekstraksiyon Verimi" gibi) runtime'da tanımlayıp, mevcut I-MR/X-bar/R + Cpk motorunu hiç değiştirmeden bu parametre için veri toplayıp SPC takibi yapabilmesini sağlar.

**Architecture:** Senaryo B (Registry Abstraction + Merkezi Getter). `constants.PARAMETER_CONFIG` hiç mutasyona uğramaz — yeni bir `parameter_registry.py` (saf mantık) custom parametreleri SQLite'tan (`custom_parameters_db.py`, saf mantık) okuyup built-in registry ile session-scope'lu bir kopya üzerinde birleştirir. `app.py`'deki tüm `PARAMETER_CONFIG[...]` erişimleri bu session-cache'li getter'a yönlendirilir; `spc_core.py`/`pdf_report.py`/`qc_converters.py` hiç değişmez (zaten parametreyi argüman olarak alan saf fonksiyonlar).

**Tech Stack:** Python stdlib `sqlite3`, Streamlit `st.session_state`, pytest.

**Spec:** Bu plan, konuşma içinde kullanıcı tarafından verilen ve gözden geçirilen "kullanıcı tanımlı özel analiz parametresi" spesifikasyonuna dayanır (ayrı bir spec dosyası yok — spec bu konuşmanın kendisidir). Aşağıdaki "Global Constraints" spesifikasyonun tam metnidir.

## Global Constraints

- `constants.PARAMETER_CONFIG`'e runtime'da **asla** `.update()` ile doğrudan mutasyon uygulanmaz (Senaryo A reddedildi — çoklu kullanıcı veri sızıntısı riski, bkz. Streamlit Community Cloud tek-process mimarisi).
- EAV (entity-attribute-value) deseni kullanılmaz.
- Built-in ve custom parametreler için ayrı/paralel if-else akışları yazılmaz (Senaryo C reddedildi) — custom parametreler built-in'lerle **aynı** `PARAMETER_CONFIG`-şekilli sözlük girdisi üretip aynı motoru kullanır.
- `spc_core.py`, `pdf_report.py`, `qc_converters.py`'ye dokunulmaz.
- `demo_target_mean` vb. demo veri üretim alanları custom parametrelere taşınmaz — custom parametreler için demo veri bölümü tamamen gizlenir.
- `is_microbio` alanı şemaya **eklenmez** (LOD/2 ikamesi/log10 pipeline'ı kapsam dışı) — sadece görsel eksen etkisi olan `log_scale` (bool) kullanılır.
- "Sayım" veri tipi seçilince ondalık hane alanı gizlenir ve değer otomatik `0`'a sabitlenir.
- `min_value`/`max_value` (widget fiziksel sınırı) ile `lsl`/`usl` (spesifikasyon limiti) kesinlikle ayrı alanlardır, birbirine map edilmez. **Not:** orijinal spec'in `custom_parameters` şemasında bu iki alan unutulmuştu (form "Fiziksel min/max sınır" topluyor ama şemada sütun yoktu) — bu plan `min_value REAL`, `max_value REAL` sütunlarını (nullable, `NULL` = sınırsız) şemaya ekleyerek bu boşluğu kapatır.
- SQLite dosyası Streamlit Community Cloud'da redeploy/uyanmada sıfırlanabilir — bu MVP için kabul edildi; UI'da kullanıcıya bunu belirten bir not gösterilir, ayrıca kapsam büyütülmez (kalıcı disk/harici DB araştırması bu plana dahil değil).
- `one_sided`, forma ayrı sorulmaz: `has_specification=True` ve LSL/USL'den sadece biri girilmişse `one_sided=True`, ikisi de girilmişse `False`. `has_specification=False` ise Cpk/Cpu/Cpl hiç hesaplanmaz, UI'da "Spesifikasyon limiti tanımlanmamış, yalnızca UCL/LCL proses kontrol limitleri geçerlidir" notu gösterilir.

---

## File Structure

- **Create** `src/custom_parameters_db.py` — SQLite şema + CRUD, Streamlit'ten bağımsız saf fonksiyonlar (qc_converters.py ile aynı mimari ilke).
- **Create** `src/parameter_registry.py` — custom SQLite satırlarını `PARAMETER_CONFIG`-şekilli sözlüğe çeviren ve built-in registry ile birleştiren saf mantık (SQLite/Streamlit'e dokunmaz, sadece veri alır/döndürür).
- **Modify** `src/app.py` — session-cache'li getter fonksiyonları, 5 doğrudan `PARAMETER_CONFIG` erişim noktası, `PARAMETER_CATEGORIES` iterasyon noktaları, custom-parameter crash guard'ları (demo bölümü, mikrobiyoloji-özel bilgi kartı else dalı), "Yeni Analiz Ekle" formu, custom parametre veri girişi/persistans köprüsü.
- **Modify** `.gitignore` — `*.db` eklenir (yerel SQLite dosyası commit'lenmesin diye).
- **Test** `tests/test_custom_parameters_db.py`, `tests/test_parameter_registry.py`, `tests/test_app_render_smoke.py` (genişletme).

---

### Task 1: SQLite katmanı — `custom_parameters_db.py`

**Files:**
- Create: `src/custom_parameters_db.py`
- Modify: `.gitignore`
- Test: `tests/test_custom_parameters_db.py`

**Interfaces:**
- Produces: `get_connection(db_path: str) -> sqlite3.Connection`, `insert_custom_parameter(conn, **kwargs) -> int`, `list_custom_parameters(conn) -> list[dict]`, `insert_custom_measurement(conn, **kwargs) -> None`, `list_custom_measurements(conn, parameter_id: int) -> list[dict]`, `DEFAULT_DB_PATH: str`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_custom_parameters_db.py
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


def test_reopening_connection_preserves_schema(tmp_path):
    db_path = str(tmp_path / "reopen.db")
    conn1 = get_connection(db_path)
    insert_custom_parameter(conn1, **_base_kwargs())
    conn1.close()

    conn2 = get_connection(db_path)
    rows = list_custom_parameters(conn2)
    conn2.close()
    assert len(rows) == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_custom_parameters_db.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'custom_parameters_db'`

- [ ] **Step 3: Implement `src/custom_parameters_db.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_custom_parameters_db.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: `.gitignore`'a `*.db` ekle**

```
__pycache__/
*.pyc
.venv/
venv/
*.db
```

- [ ] **Step 6: Commit**

```bash
git add src/custom_parameters_db.py tests/test_custom_parameters_db.py .gitignore
git commit -m "feat: custom parameter SQLite layer (custom_parameters_db.py)"
```

---

### Task 2: Saf birleştirme mantığı — `parameter_registry.py`

**Files:**
- Create: `src/parameter_registry.py`
- Test: `tests/test_parameter_registry.py`

**Interfaces:**
- Consumes: `custom_parameters_db.list_custom_parameters()`'ın döndürdüğü şekilde `dict` satırları (Task 1).
- Produces: `custom_parameter_to_config_entry(row: dict) -> dict`, `merge_parameter_config(builtin_config: dict, custom_rows: list[dict]) -> dict`, `merge_parameter_categories(builtin_categories: list[tuple], custom_rows: list[dict]) -> list[tuple]`, `CUSTOM_CATEGORY_ID = "ozel"`, `CUSTOM_CATEGORY_LABEL = "Özel Parametreler"`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_parameter_registry.py
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from parameter_registry import (
    custom_parameter_to_config_entry,
    merge_parameter_config,
    merge_parameter_categories,
    CUSTOM_CATEGORY_ID,
    CUSTOM_CATEGORY_LABEL,
)


def _row(**overrides):
    row = dict(
        id=1, name="Ekstraksiyon Verimi", unit="%", chart_type="I-MR",
        subgroup_size=None, data_type="continuous", lsl=None, usl=85.0,
        has_specification=1, one_sided=1, log_scale=0, decimal_places=2,
        min_value=None, max_value=None, created_at="2026-08-27T10:00:00",
    )
    row.update(overrides)
    return row


def test_custom_parameter_to_config_entry_one_sided_usl_only():
    entry = custom_parameter_to_config_entry(_row())
    assert entry["unit"] == "%"
    assert entry["is_individual"] is True
    assert entry["one_sided"] is True
    assert entry["default_usl"] == 85.0
    assert entry["default_lsl"] == 0.0
    assert entry["has_specification"] is True
    assert entry["is_custom"] is True
    assert entry["products"] == {}
    assert entry["category"] == CUSTOM_CATEGORY_LABEL
    assert entry["custom_parameter_id"] == 1


def test_custom_parameter_to_config_entry_no_specification():
    entry = custom_parameter_to_config_entry(
        _row(has_specification=0, one_sided=0, lsl=None, usl=None)
    )
    assert entry["has_specification"] is False
    assert entry["default_lsl"] == 0.0
    assert entry["default_usl"] == 0.0


def test_custom_parameter_to_config_entry_xbar_r_carries_subgroup_size():
    entry = custom_parameter_to_config_entry(
        _row(chart_type="Xbar-R", subgroup_size=4, is_individual=False)
    )
    assert entry["is_individual"] is False
    assert entry["custom_subgroup_size"] == 4


def test_custom_parameter_to_config_entry_count_forces_zero_decimals():
    entry = custom_parameter_to_config_entry(_row(data_type="count", decimal_places=2))
    assert entry["decimal_places"] == 0


def test_custom_parameter_to_config_entry_carries_min_max_and_log_scale():
    entry = custom_parameter_to_config_entry(
        _row(min_value=0.0, max_value=100.0, log_scale=1)
    )
    assert entry["min_value"] == 0.0
    assert entry["max_value"] == 100.0
    assert entry["log_scale"] is True


def test_merge_parameter_config_does_not_mutate_builtin():
    builtin = {"pH": {"unit": "-", "min_value": 0.0}}
    merged = merge_parameter_config(builtin, [_row()])
    assert "Ekstraksiyon Verimi" in merged
    assert "Ekstraksiyon Verimi" not in builtin
    assert merged["pH"] == builtin["pH"]


def test_merge_parameter_config_empty_custom_rows_returns_copy():
    builtin = {"pH": {"unit": "-"}}
    merged = merge_parameter_config(builtin, [])
    assert merged == builtin
    assert merged is not builtin


def test_merge_parameter_categories_adds_custom_category_when_rows_exist():
    builtin_categories = [("fiziksel", "Fiziksel", ["pH"])]
    merged = merge_parameter_categories(builtin_categories, [_row()])
    assert merged[0] == builtin_categories[0]
    assert merged[-1] == (CUSTOM_CATEGORY_ID, CUSTOM_CATEGORY_LABEL, ["Ekstraksiyon Verimi"])


def test_merge_parameter_categories_no_custom_category_when_no_rows():
    builtin_categories = [("fiziksel", "Fiziksel", ["pH"])]
    merged = merge_parameter_categories(builtin_categories, [])
    assert merged == builtin_categories
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_parameter_registry.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'parameter_registry'`

- [ ] **Step 3: Implement `src/parameter_registry.py`**

```python
"""Kullanici tanimli ozel parametreleri, constants.PARAMETER_CONFIG'teki
built-in kayitlarla AYNI sekle donusturup birlestiren SAF mantik -
qc_converters.py/spc_core.py ile ayni mimari ilke: hicbir fonksiyon
st.session_state'e veya SQLite baglantisina dokunmaz, sadece veri alir/
dondurur. Streamlit/SQLite entegrasyonu (session-scope cache) app.py'de
yapilir - bkz. get_combined_parameter_config() orada.

KRITIK mimari karar (Senaryo B): merge_parameter_config() ASLA girdi
sozlugunu (builtin_config) mutasyona UGRATMAZ, her zaman YENI bir dict
dondurur (deepcopy). constants.PARAMETER_CONFIG'in kendisi boylece hicbir
zaman degismez - Senaryo A'nin coklu-kullanici (Streamlit Community
Cloud tek-process) veri sizintisi riski, bu fonksiyonun kendisi tarafindan
yapisal olarak imkansiz kilinir."""

from copy import deepcopy

CUSTOM_CATEGORY_ID = "ozel"
CUSTOM_CATEGORY_LABEL = "Özel Parametreler"


def custom_parameter_to_config_entry(row: dict) -> dict:
    """Bir custom_parameters SQLite satirini (dict), PARAMETER_CONFIG'teki
    built-in kayitlarla AYNI sekle cevirir - app.py'deki mevcut TUM okuma
    noktalari (param_config['unit'], ['min_value'], ['is_individual'] vb.)
    built-in/custom ayrimi yapmadan calisabilsin diye.

    'products' HER ZAMAN bos sozluk: custom parametrelerde urun-bazli
    LSL/USL yok, tek bir genel LSL/USL var - resolve_current_spec_hint()
    ve demo_scenario_targets() gibi built-in tuketiciler zaten
    product_range=None durumunu genel varsayilana (default_lsl/default_usl)
    duserek ele aliyor, bu yuzden custom parametreler icin ekstra bir
    dallanma GEREKMEZ.

    has_specification=False ise default_lsl/default_usl 0.0'a sabitlenir
    (spc_core.is_spec_valid ve Cpk hesabi cagrilirken has_specification
    bayragina bakip HIC cagrilmamalari gerekir - bu deger sadece
    'kullanilmayacak' bir placeholder'dir, YOK SAYILIR).

    is_microbio HER ZAMAN False: LOD/2 ikamesi/log10 depolama pipeline'i
    custom parametreler icin kapsam disi (bkz. plan Global Constraints).
    log_scale ise SADECE grafik ekseninin gorsel olcegini etkileyen,
    is_microbio'dan tamamen bagimsiz bir alandir."""
    has_spec = bool(row["has_specification"])
    lsl = row["lsl"] if has_spec and row["lsl"] is not None else 0.0
    usl = row["usl"] if has_spec and row["usl"] is not None else 0.0
    decimal_places = 0 if row["data_type"] == "count" else row["decimal_places"]
    return {
        "unit": row["unit"],
        "min_value": row["min_value"],
        "max_value": row["max_value"],
        "decimal_places": decimal_places,
        "products": {},
        "default_lsl": lsl,
        "default_usl": usl,
        "one_sided": bool(row["one_sided"]),
        "is_individual": row["chart_type"] == "I-MR",
        "is_microbio": False,
        "category": CUSTOM_CATEGORY_LABEL,
        "method_source": "Kullanıcı tanımlı özel parametre",
        "is_custom": True,
        "has_specification": has_spec,
        "log_scale": bool(row["log_scale"]),
        "custom_parameter_id": row["id"],
        "custom_subgroup_size": row["subgroup_size"],
    }


def merge_parameter_config(builtin_config: dict, custom_rows: list[dict]) -> dict:
    """builtin_config'in deepcopy'sini custom_rows ile genisletir. deepcopy
    ZORUNLU: sadece ust seviye dict'i degil, her bir parametrenin ic
    sozlugunu (orn. 'products') de kopyalar - aksi halde donen sozlukteki
    bir ic degeri degistirmek (orn. gelecekte eklenecek bir 'products'
    guncellemesi) builtin_config'i de mutasyona ugratirdi."""
    merged = deepcopy(builtin_config)
    for row in custom_rows:
        merged[row["name"]] = custom_parameter_to_config_entry(row)
    return merged


def merge_parameter_categories(builtin_categories: list[tuple], custom_rows: list[dict]) -> list[tuple]:
    """builtin_categories'in (cat_id, cat_label, cat_params) formatindaki
    listesine, custom_rows varsa sona bir 'Özel Parametreler' kategorisi
    ekler. custom_rows bossa hicbir sey eklenmez - bos bir kategori
    sidebar'da anlamsiz bir bolum acardi."""
    merged = list(builtin_categories)
    if custom_rows:
        merged.append((CUSTOM_CATEGORY_ID, CUSTOM_CATEGORY_LABEL, [row["name"] for row in custom_rows]))
    return merged
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_parameter_registry.py -v`
Expected: PASS (9 tests)

- [ ] **Step 5: Commit**

```bash
git add src/parameter_registry.py tests/test_parameter_registry.py
git commit -m "feat: pure merge logic for custom + builtin parameter registry"
```

---

### Task 3: `app.py` — session-cache'li getter + 5 call-site + kategori değişikliği

**Files:**
- Modify: `src/app.py:1-47` (import bloğu), `:182`, `:242-247`, `:295-311`, `:367`, `:3367`, `:3617`, `:3758`
- Test: `tests/test_app_render_smoke.py` (genişletme)

**Interfaces:**
- Consumes: `parameter_registry.merge_parameter_config`, `merge_parameter_categories` (Task 2); `custom_parameters_db.get_connection`, `list_custom_parameters` (Task 1).
- Produces: `get_combined_parameter_config() -> dict`, `get_combined_parameter_categories() -> list[tuple]`, `invalidate_parameter_registry_cache() -> None` (app.py içinde, sonraki task'ların kullanacağı).

- [ ] **Step 1: İmportları ekle**

`src/app.py` satır 35-36 civarına (mevcut `qc_converters`/`color_lab` importlarının yanına) ekle:

```python
from custom_parameters_db import get_connection as get_custom_param_connection, list_custom_parameters, insert_custom_parameter, insert_custom_measurement, list_custom_measurements
from parameter_registry import merge_parameter_config, merge_parameter_categories, CUSTOM_CATEGORY_ID
```

- [ ] **Step 2: Getter fonksiyonlarını ekle**

`src/app.py` satır 114'ten (session_state init bloğunun bittiği yer) hemen sonra ekle:

```python
def get_combined_parameter_config() -> dict:
    """PARAMETER_CONFIG'i (built-in) SQLite'taki custom_parameters ile
    birlestirir - SADECE bu session'a ait bir kopya uzerinde (st.session_
    state icinde cache'lenir). constants.PARAMETER_CONFIG'in KENDISI ASLA
    mutasyona ugramaz (Senaryo A'nin coklu-kullanici veri sizintisi riski
    boylece yapisal olarak imkansiz - bkz. parameter_registry.merge_
    parameter_config docstring'i). Cache, yeni bir custom parametre
    eklendiginde invalidate_parameter_registry_cache() ile temizlenir."""
    if "_param_registry_cache" not in st.session_state:
        conn = get_custom_param_connection()
        try:
            custom_rows = list_custom_parameters(conn)
        finally:
            conn.close()
        st.session_state._param_registry_cache = merge_parameter_config(PARAMETER_CONFIG, custom_rows)
        st.session_state._param_categories_cache = merge_parameter_categories(PARAMETER_CATEGORIES, custom_rows)
    return st.session_state._param_registry_cache


def get_combined_parameter_categories() -> list:
    """bkz. get_combined_parameter_config() - iki cache birlikte doldurulur,
    bu fonksiyon sadece kategori tarafini dondurur."""
    get_combined_parameter_config()
    return st.session_state._param_categories_cache


def invalidate_parameter_registry_cache() -> None:
    """Yeni bir custom parametre SQLite'a eklendikten HEMEN sonra
    cagrilmali - aksi halde ekleyen kullanicinin kendi session'i bile
    az once ekledigi parametreyi goremez (cache bayat kalir)."""
    st.session_state.pop("_param_registry_cache", None)
    st.session_state.pop("_param_categories_cache", None)
```

- [ ] **Step 3: 5 doğrudan `PARAMETER_CONFIG` erişimini değiştir**

`src/app.py` satır 182:
```python
    param_cfg = PARAMETER_CONFIG[active_param]
```
→
```python
    param_cfg = get_combined_parameter_config()[active_param]
```

`src/app.py` satır 367:
```python
param_config = PARAMETER_CONFIG[st.session_state.active_parameter]
```
→
```python
param_config = get_combined_parameter_config()[st.session_state.active_parameter]
```

`src/app.py` satır 3367:
```python
    target_config = PARAMETER_CONFIG.get(target, {})
```
→
```python
    target_config = get_combined_parameter_config().get(target, {})
```

`src/app.py` satır 3617:
```python
        _f0_individual_params = sorted(
            p for p, cfg in PARAMETER_CONFIG.items()
            if cfg.get("is_individual", False) and p not in ("L*", "a*", "b*")
        )
```
→
```python
        _f0_individual_params = sorted(
            p for p, cfg in get_combined_parameter_config().items()
            if cfg.get("is_individual", False) and p not in ("L*", "a*", "b*")
        )
```

`src/app.py` satır 3758 (Totox köprüsü, aynı desen):
```python
        _totox_individual_params = sorted(
            p for p, cfg in PARAMETER_CONFIG.items()
            if cfg.get("is_individual", False) and p not in ("L*", "a*", "b*")
        )
```
→
```python
        _totox_individual_params = sorted(
            p for p, cfg in get_combined_parameter_config().items()
            if cfg.get("is_individual", False) and p not in ("L*", "a*", "b*")
        )
```

- [ ] **Step 4: `PARAMETER_CATEGORIES` iterasyon noktalarını değiştir**

`src/app.py` satır 241-247:
```python
if st.session_state.pop("_reset_parameter_radio", False):
    for _cat_id, _cat_label, _cat_params in PARAMETER_CATEGORIES:
        st.session_state[f"parameter_radio_{_cat_id}"] = (
            st.session_state.active_parameter
            if st.session_state.active_parameter in _cat_params
            else None
        )
```
→
```python
if st.session_state.pop("_reset_parameter_radio", False):
    for _cat_id, _cat_label, _cat_params in get_combined_parameter_categories():
        st.session_state[f"parameter_radio_{_cat_id}"] = (
            st.session_state.active_parameter
            if st.session_state.active_parameter in _cat_params
            else None
        )
```

`src/app.py` satır 295 (`for _cat_id, _cat_label, _cat_params in PARAMETER_CATEGORIES:`) → `for _cat_id, _cat_label, _cat_params in get_combined_parameter_categories():`

- [ ] **Step 5: Statik regresyon testi ekle (aynı desen `test_app_render_smoke.py`'de zaten var)**

`tests/test_app_render_smoke.py`'ye ekle:

```python
def test_no_bare_parameter_config_reads_remain_in_app():
    with open(APP_PATH, encoding="utf-8") as f:
        source = f.read()
    # get_combined_parameter_config()[...]/.get(...) icindeki "PARAMETER_CONFIG"
    # alt-string'ini YANLISLIKLA yakalamamak icin, fonksiyon TANIMLARINI
    # (def get_combined_parameter_config...) ve import satirlarini haric
    # tutuyoruz - geriye sadece dogrudan "PARAMETER_CONFIG[" / ".get(" gibi
    # eski-desen cagrilar kalmali, hicbiri kalmamalidir.
    forbidden = re.findall(r"(?<!get_combined_)PARAMETER_CONFIG\[|(?<!get_combined_)PARAMETER_CONFIG\.get\(|(?<!get_combined_)PARAMETER_CONFIG\.items\(\)", source)
    assert not forbidden, (
        "app.py'de hala dogrudan PARAMETER_CONFIG erisimi var - Senaryo B "
        "geregi hepsi get_combined_parameter_config() uzerinden gecmeli "
        f"(bulunanlar: {forbidden})"
    )
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/test_app_render_smoke.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/app.py tests/test_app_render_smoke.py
git commit -m "refactor: route all PARAMETER_CONFIG reads through get_combined_parameter_config()"
```

---

### Task 4: Custom parametreler için çökme koruması (demo bölümü + mikrobiyoloji bilgi kartı)

**Files:**
- Modify: `src/app.py:1866-2027` (demo veri bölümü), `src/app.py:2543-2589` (bilgi kartı if/elif zinciri)
- Test: `tests/test_app_render_smoke.py` (genişletme)

**Rationale:** `demo_scenario_targets()` (`result_helpers.py:157,160`) `param_config["products"]` ve `param_config["demo_target_mean"]` anahtarlarına **koşulsuz** erişiyor — custom parametrelerin bu anahtarları yok, çağrılırsa `KeyError` verir. Aynı şekilde bilgi kartı if/elif zinciri (satır 2466-2589), custom parametreler için hiçbir dal içermediğinden mikrobiyoloji-özel `else` dalına düşer ve `param_config["default_usl"]` (satır 2582) `KeyError` ile çöker — tam olarak `test_app_render_smoke.py`'deki mevcut 1.1 regresyon testinin yakaladığı hata sınıfı, custom parametreler için tekrarlanıyor.

- [ ] **Step 1: Demo bölümünü koru**

`src/app.py` satır 1866 öncesine (demo_scenario_options tanımından hemen önce) ekle, ve mevcut `demo_scenario_options = ...`'tan `st.rerun()` (satır 2027, `col_a` bloğunun sonu) içeren kısmı bir `else` dalına indirge:

```python
        if param_config.get("is_custom", False):
            st.caption(
                "ℹ️ Bu özel parametre için demo veri üretimi desteklenmiyor "
                "(demo veri built-in parametrelerin literatür kaynaklı "
                "hedef değerlerine dayanır, özel parametrelerde bu değerler "
                "tanımlı değildir)."
            )
        else:
            demo_scenario_options = ["Genel (varsayilan)"] + [
                p for p in param_config["products"] if p != "Ozel/Manuel gir"
            ]
            # ... (mevcut demo_scenario, demo_pattern_choice, col_a/col_b
            # icindeki "Demo veri yukle" butonu ve mantigi BURAYA, ayni
            # girinti seviyesiyle tasinir - icerik degismez, sadece bu
            # else dalinin altina bir girinti seviyesi eklenir)
```

`col_b` (satır 2028, "Tüm verileri temizle") bloğu **bu `if/else`'in dışında, koşulsuz** kalmalı — custom parametreler için de veri temizleme çalışmalı. Bunu sağlamak için `col_a, col_b = st.columns(2)` satırını (mevcut 1921) `if/else` bloğunun DIŞINA, her iki dalın da erişebileceği şekilde taşı: `demo_scenario`/`demo_pattern_choice`/buton mantığı `else` dalında `with col_a:` içine, `is_custom` dalında da boş bir `with col_a: st.caption(...)` olarak kalsın, `with col_b:` (temizleme) her iki durumda da aynı, koşulsuz kod olarak en dışarıda kalsın.

- [ ] **Step 2: Bilgi kartı zincirine custom dalı ekle**

`src/app.py` satır 2543 öncesine (mevcut `elif active_param in FOOD_QUALITY_PARAMETER_CONFIG:` dalından önce) ekle:

```python
            elif param_config.get("is_custom", False):
                st.caption(
                    "Bu, kullanıcı tarafından tanımlanmış özel bir "
                    "parametredir — LSL/USL değerleri (varsa) kullanıcı "
                    "tarafından elle girilmiştir, literatür/regülasyon "
                    "kaynağı yoktur."
                )
```

Bu dal, mevcut `elif active_param in FOOD_QUALITY_PARAMETER_CONFIG:` dalından **önce** olmalı ki custom parametreler oraya değil buraya düşsün (custom parametre adları zaten `FOOD_QUALITY_PARAMETER_CONFIG`'te olamaz, ama açıklık için sıralama önemli — mikrobiyoloji `else` dalından önce olması zorunlu).

Ayrıca satır 2582 (`ic2.markdown(f"**Default LOD**  \n{param_config.get('default_lod', '-'):g} {unit}")`) zaten `.get('default_lod', '-')` kullanıyor ama `:g` format spesifikasyonu string `'-'` üzerinde çöker (bu, dosyanın kendi 1.1 regresyon notunda belgelenen bilinen hata sınıfı) — custom parametreler bu `else` dalına hiç düşmeyeceği için (Step 2 sayesinde) bu satıra custom parametrelerle ilgili ek bir değişiklik GEREKMEZ.

- [ ] **Step 3: Statik regresyon testi ekle**

`tests/test_app_render_smoke.py`'ye ekle:

```python
def test_custom_parameter_branch_exists_before_microbio_else():
    chain = _read_info_card_chain()
    custom_pos = chain.index('elif param_config.get("is_custom", False):')
    else_pos = chain.index("else:  # is_microbio")
    assert custom_pos < else_pos, (
        "Custom parametre yakalama dali, mikrobiyoloji-ozel 'else' "
        "dalindan ONCE olmali - aksi halde custom parametreler "
        "param_config['default_usl'] KeyError'iyla cokme riski tasir "
        "(ayni sinif hata, bkz. dosyanin en ustundeki 1.1 bulgusu)."
    )


def test_demo_section_guards_custom_parameters():
    with open(APP_PATH, encoding="utf-8") as f:
        source = f.read()
    demo_guard_pos = source.index('if param_config.get("is_custom", False):')
    products_read_pos = source.index('demo_scenario_options = ["Genel (varsayilan)"]')
    assert demo_guard_pos < products_read_pos, (
        "Demo bolumu, param_config['products'] okumadan ONCE is_custom "
        "kontrolu yapmali - aksi halde custom parametrelerde KeyError."
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_app_render_smoke.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/app.py tests/test_app_render_smoke.py
git commit -m "fix: guard demo section and info-card chain against custom parameters"
```

---

### Task 5: "Yeni Analiz Ekle" formu

**Files:**
- Modify: `src/app.py:347-353` (sidebar, "Görünüm Ayarları" başlığından önce/sonra uygun bir yere)
- Test: `tests/test_app_render_smoke.py` (genişletme, form varlığı için statik kontrol) + manuel QA (Streamlit formu, otomatik test edilemez — bkz. Task 3 Adım 5'teki mevcut testin gerekçe notu)

**Interfaces:**
- Consumes: `custom_parameters_db.insert_custom_parameter`, Task 3'ün `invalidate_parameter_registry_cache()`.

- [ ] **Step 1: Formu ekle**

`src/app.py` satır 347 (`st.divider()`, "Görünüm Ayarları"ndan hemen önce) civarına ekle:

```python
    st.divider()
    with st.expander("➕ Yeni Analiz Ekle", expanded=False):
        st.caption(
            "Listede olmayan bir analiz mi takip ediyorsunuz? Buradan "
            "kendi parametrenizi tanımlayıp aynı SPC motoruyla (kontrol "
            "grafiği + Cpk) takip edebilirsiniz. ℹ️ Bu kayıtlar yerel "
            "SQLite dosyasında tutulur; uygulama yeniden başlatılırsa "
            "(örn. Streamlit Cloud'da uzun süreli inaktivite sonrası) "
            "kaybolabilir."
        )
        with st.form("new_custom_parameter_form", clear_on_submit=True):
            new_name = st.text_input("Analiz adı")
            new_unit = st.text_input("Birim")
            new_data_type_label = st.radio(
                "Veri tipi", ["Sürekli", "Sayım"], index=0, horizontal=True,
                key="new_param_data_type",
            )
            new_spec_mode = st.radio(
                "Spesifikasyon", ["LSL/USL gir", "Belirtilmiyor"], index=0,
                key="new_param_spec_mode",
            )
            _spec_disabled = new_spec_mode == "Belirtilmiyor"
            sc1, sc2 = st.columns(2)
            with sc1:
                new_lsl_enabled = st.checkbox("LSL kullan", value=True, key="new_param_lsl_enabled", disabled=_spec_disabled)
                new_lsl = st.number_input("LSL", value=0.0, key="new_param_lsl", disabled=_spec_disabled or not new_lsl_enabled)
            with sc2:
                new_usl_enabled = st.checkbox("USL kullan", value=True, key="new_param_usl_enabled", disabled=_spec_disabled)
                new_usl = st.number_input("USL", value=0.0, key="new_param_usl", disabled=_spec_disabled or not new_usl_enabled)
            new_structure = st.radio(
                "Ölçüm yapısı", ["Bireysel (I-MR)", "Alt Grup (X-bar/R)"], index=0,
                key="new_param_structure",
            )
            new_subgroup_n = None
            if new_structure == "Alt Grup (X-bar/R)":
                new_subgroup_n = st.number_input(
                    "Alt grup büyüklüğü (n)", min_value=MIN_SUBGROUP_SIZE,
                    max_value=MAX_SUBGROUP_SIZE, value=DEFAULT_SUBGROUP_SIZE,
                    key="new_param_subgroup_n",
                )
            with st.expander("Gelişmiş ayarlar", expanded=False):
                new_is_count = new_data_type_label == "Sayım"
                new_decimal_places = 0
                if not new_is_count:
                    new_decimal_places = st.number_input(
                        "Ondalık hane", min_value=0, max_value=6, value=2,
                        key="new_param_decimal_places",
                    )
                else:
                    st.caption("Sayım verisi için ondalık hane 0'a sabitlenir.")
                new_log_scale = st.checkbox(
                    "Veriler log ölçekte mi gösterilsin?", value=False,
                    key="new_param_log_scale",
                )
                mc1, mc2 = st.columns(2)
                with mc1:
                    new_min_enabled = st.checkbox("Fiziksel min sınır", value=False, key="new_param_min_enabled")
                    new_min_value = st.number_input("Min", value=0.0, key="new_param_min_value", disabled=not new_min_enabled)
                with mc2:
                    new_max_enabled = st.checkbox("Fiziksel max sınır", value=False, key="new_param_max_enabled")
                    new_max_value = st.number_input("Max", value=100.0, key="new_param_max_value", disabled=not new_max_enabled)

            new_submitted = st.form_submit_button("Parametreyi oluştur")

        if new_submitted:
            _combined = get_combined_parameter_config()
            _name_clean = new_name.strip()
            if not _name_clean:
                st.error("Analiz adı boş olamaz.")
            elif not new_unit.strip():
                st.error("Birim boş olamaz.")
            elif _name_clean in _combined:
                st.error(f"'{_name_clean}' adında bir parametre zaten mevcut (built-in veya özel).")
            else:
                _has_spec = not _spec_disabled and (new_lsl_enabled or new_usl_enabled)
                _lsl = new_lsl if (_has_spec and new_lsl_enabled) else None
                _usl = new_usl if (_has_spec and new_usl_enabled) else None
                _one_sided = _has_spec and (_lsl is None or _usl is None)
                if _has_spec and _lsl is not None and _usl is not None and _lsl >= _usl:
                    st.error("LSL, USL'den küçük olmalıdır.")
                else:
                    conn = get_custom_param_connection()
                    try:
                        insert_custom_parameter(
                            conn, name=_name_clean, unit=new_unit.strip(),
                            chart_type="I-MR" if new_structure == "Bireysel (I-MR)" else "Xbar-R",
                            subgroup_size=new_subgroup_n,
                            data_type="count" if new_is_count else "continuous",
                            lsl=_lsl, usl=_usl, has_specification=_has_spec,
                            one_sided=_one_sided, log_scale=new_log_scale,
                            decimal_places=new_decimal_places,
                            min_value=new_min_value if new_min_enabled else None,
                            max_value=new_max_value if new_max_enabled else None,
                        )
                    except ValueError as exc:
                        st.error(str(exc))
                    else:
                        conn.close()
                        invalidate_parameter_registry_cache()
                        st.success(f"'{_name_clean}' eklendi. Sol menüden 'Özel Parametreler' altında bulabilirsiniz.")
                        st.rerun()
```

**Not:** `_name_clean in _combined` kontrolü hem built-in hem custom isimleri kapsar (çünkü `_combined` zaten `get_combined_parameter_config()`'in birleştirilmiş sonucu) — Task 1'deki DB-seviyesi `ValueError` (aynı isimde custom parametre) bu kontrolün **arkasında ikinci bir güvenlik ağı** olarak kalır (örn. iki farklı session'ın aynı anda aynı adı eklemeye çalışması gibi bir yarış durumunda).

- [ ] **Step 2: Statik varlık testi**

`tests/test_app_render_smoke.py`'ye ekle:

```python
def test_new_custom_parameter_form_exists():
    with open(APP_PATH, encoding="utf-8") as f:
        source = f.read()
    assert 'st.form("new_custom_parameter_form"' in source
    assert "insert_custom_parameter(" in source
    assert "invalidate_parameter_registry_cache()" in source
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `pytest tests/test_app_render_smoke.py -v`
Expected: PASS

- [ ] **Step 4: Manuel QA (Streamlit formu otomatik test edilemiyor, bkz. dosyanın kendi notu)**

`streamlit run src/app.py` çalıştır:
1. Sidebar'da "➕ Yeni Analiz Ekle" genişlet, "Ekstraksiyon Verimi" / birim "%" / Sürekli / USL=85 / Bireysel (I-MR) ile oluştur.
2. "Özel Parametreler" kategorisinin sidebar'da göründüğünü, yeni parametrenin seçilebildiğini doğrula.
3. Aynı adı tekrar eklemeyi dene → "zaten mevcut" hatası görünmeli.
4. Built-in bir isim ("pH") ile eklemeyi dene → aynı hata.

- [ ] **Step 5: Commit**

```bash
git add src/app.py tests/test_app_render_smoke.py
git commit -m "feat: add 'Yeni Analiz Ekle' custom parameter creation form"
```

---

### Task 6: Custom parametre veri girişi — persistans köprüsü + `subgroup_size` senkronizasyonu

**Files:**
- Modify: `src/app.py:373-464` (parametre-özel sidebar mantığının olduğu blok, Nem/Kuru Madde deseniyle aynı yere)
- Modify: `src/app.py` içindeki `submitted` blokları (satır ~1817-1864, ölçüm kaydı) — custom parametre ise SQLite'a da yazılmalı.

**Rationale:** Built-in parametrelerde veri sadece `st.session_state.subgroups`'ta tutulur (kalıcı değil, kasıtlı). Custom parametrelerde ise `custom_measurements` tablosu var — bu, verinin session kapanınca kaybolmaması için. Yani custom parametre aktifken: (a) parametre değişince/uygulama açılışında SQLite'tan mevcut ölçümler `st.session_state.subgroups`'a hydrate edilir, (b) yeni ölçüm kaydedilince hem `st.session_state.subgroups`'a (anlık UI için, mevcut davranış) hem SQLite'a (kalıcılık için) yazılır.

- [ ] **Step 1: `subgroup_size` senkronizasyonu — parametre değişiminde**

`src/app.py` satır 373 civarına (Nem/Kuru Madde özel bloğunun yanına, aynı if-chain'e) ekle:

```python
if param_config.get("is_custom", False) and not param_config["is_individual"]:
    # Custom X-bar/R parametrenin SQLite'a kaydedilmis subgroup_size'i,
    # global st.session_state.subgroup_size'a senkronize edilir - Nem/Kuru
    # Madde panelinin is_individual'i runtime'da set etmesiyle (yukaridaki
    # blok) AYNI desen. Sadece parametre YENI aktif oldugunda (henuz veri
    # girilmemisken) senkronize edilir - kullanici sidebar'daki "Alt grup
    # buyuklugu" widget'iyla ELLE degistirdiyse (asagida) o tercih ezilmez.
    if not st.session_state.subgroups and param_config.get("custom_subgroup_size"):
        st.session_state.subgroup_size = param_config["custom_subgroup_size"]
```

Bu blok, mevcut `if st.session_state.active_parameter == "Nem / Kuru Madde":` (satır 373) ile `is_individual = param_config.get("is_individual", False)` (satır 422) arasına, o if/elif zincirinin bir parçası olarak eklenir.

- [ ] **Step 2: Parametre aktif olunca SQLite'tan hydrate et**

`src/app.py` satır 373 öncesine (parametre-özel bloklardan önce, `param_config` tanımlandıktan hemen sonra — satır 367-368 civarı) ekle:

```python
if param_config.get("is_custom", False) and "_custom_hydrated_for" not in st.session_state:
    st.session_state._custom_hydrated_for = None
if (
    param_config.get("is_custom", False)
    and st.session_state.get("_custom_hydrated_for") != st.session_state.active_parameter
    and not st.session_state.subgroups
):
    # Custom parametre ilk kez aktif oldugunda (bu session'da), SQLite'taki
    # gecmis olcumleri session_state.subgroups'a yukler - custom parametreler
    # ARTIK sadece session-state-only degil, kalici (bkz. custom_measurements
    # tablosu). "not st.session_state.subgroups" korumasi: kullanici ayni
    # parametrede zaten veri girmisse (submitted blogu subgroups'a EKLEMIS
    # olabilir bu run'dan once) hydrate ETMEZ - cift kayit onlenir.
    _conn = get_custom_param_connection()
    try:
        _hydrated = list_custom_measurements(_conn, param_config["custom_parameter_id"])
    finally:
        _conn.close()
    st.session_state.subgroups = [
        {"shift": r["shift"], "values": r["values"], "notes": r["notes"] or "",
         "urun": r["urun"] or "", "timestamp": r["timestamp"], "lot_no": r["lot_no"] or ""}
        for r in _hydrated
    ]
    st.session_state._custom_hydrated_for = st.session_state.active_parameter
```

- [ ] **Step 3: Ölçüm kaydedilirken SQLite'a da yaz**

`src/app.py` satır 1844-1850 (is_individual olmayan, X-bar/R submit bloğu):

```python
            elif submitted:
                st.session_state.subgroups.append({
                    "shift": shift, "values": measurements,
                    "lot_no": lot_no, "notes": notes,
                    "urun": st.session_state.get("product_select", ""),
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                })
```
→
```python
            elif submitted:
                _new_entry = {
                    "shift": shift, "values": measurements,
                    "lot_no": lot_no, "notes": notes,
                    "urun": st.session_state.get("product_select", ""),
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                }
                st.session_state.subgroups.append(_new_entry)
                if param_config.get("is_custom", False):
                    _conn = get_custom_param_connection()
                    try:
                        insert_custom_measurement(
                            _conn, parameter_id=param_config["custom_parameter_id"],
                            shift=_new_entry["shift"], values=_new_entry["values"],
                            notes=_new_entry["notes"], urun=_new_entry["urun"],
                            timestamp=_new_entry["timestamp"], lot_no=_new_entry["lot_no"],
                        )
                    finally:
                        _conn.close()
```

Aynı desen, `is_individual` (mikrobiyoloji olmayan) submit bloğu için de uygulanır — satır ~1826 civarındaki `st.session_state.subgroups.append({...})` çağrısı, custom parametreler `is_microbio=False` sabit olduğu için (Global Constraints) bu ikinci noktaya (mikrobiyoloji submit bloğu, satır 1818-1832) **hiç girmez** — custom I-MR ölçümleri her zaman satır 1775-1788'deki (`elif is_individual:`) genel I-MR giriş yoluna düşer. O yoldaki submit bloğu, yukarıdaki `elif submitted:` (satır 1844) ile **aynı bloktur** (kod, `is_individual` olsun olmasın tek bir `submitted` bloğunda birleşiyor — satır 1844'teki değişiklik hem I-MR hem X-bar/R custom kayıtlarını kapsar). Bunu doğrulamak için Adım 4'teki teste bakın.

- [ ] **Step 4: Test — hydrate + persist döngüsü**

Bu akış Streamlit widget etkileşimi gerektirdiği için (form submit, session_state) `tests/test_app_render_smoke.py`'deki mevcut yaklaşımla aynı şekilde **statik kaynak kontrolü** ile test edilir:

```python
def test_custom_measurement_persisted_on_submit():
    with open(APP_PATH, encoding="utf-8") as f:
        source = f.read()
    assert "insert_custom_measurement(" in source
    assert '"_custom_hydrated_for"' in source
```

Fonksiyonel doğrulama (gerçek SQLite döngüsü) zaten Task 1'in `test_insert_and_list_custom_measurements` testinde saf mantık seviyesinde kapsanıyor; app.py entegrasyonu manuel QA ile doğrulanır (Adım 5).

- [ ] **Step 5: Manuel QA**

`streamlit run src/app.py`:
1. Bir custom I-MR parametre oluştur, 3 ölçüm gir.
2. Başka bir parametreye geçip geri dön → 3 ölçümün hala göründüğünü doğrula (session-state hydrate).
3. Uygulamayı tamamen yeniden başlat (`Ctrl+C` + tekrar `streamlit run`) → aynı 3 ölçümün SQLite'tan geri yüklendiğini doğrula (kalıcılık).

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/test_app_render_smoke.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add src/app.py tests/test_app_render_smoke.py
git commit -m "feat: persist and hydrate custom parameter measurements via SQLite"
```

---

### Task 7: `has_specification=False` — Cpk/Cpu gizleme

**Files:**
- Modify: `src/app.py:159-233` (`compute_active_parameter_status`), ilgili Cpk gösterim noktaları (Chart sekmesi — KPI kartı).
- Test: `tests/test_app_render_smoke.py` (genişletme)

**Rationale:** `is_spec_valid(one_sided, lsl, usl)` (spc_core.py) `lsl < usl` kontrolü yapar — `has_specification=False` durumunda `lsl=0.0, usl=0.0` gönderilirse `0.0 < 0.0` `False` döner, yani `is_spec_valid` zaten `False` döndürüp Cpk hesaplanmasını **otomatik olarak engeller** (spc_core.py'ye dokunmadan, sadece 0.0/0.0 verisiyle doğal olarak "geçersiz spec" sayılıyor). Bu, `spc_core.py`'ye dokunmama kısıtını ihlal etmeden hedefe ulaşmanın yolu — ekstra bir `has_specification` kontrolü sadece **mesaj metninde** gerekli (kullanıcıya "geçersiz spesifikasyon" yerine "spesifikasyon tanımlanmadı" demek için).

- [ ] **Step 1: KPI/uyarı metnini `has_specification`'a göre özelleştir**

`src/app.py`'de `is_spec_valid(...)` `False` döndüğünde gösterilen mevcut uyarı metninin bulunduğu yeri (Chart sekmesi, KPI kartı civarı — `resolve_current_spec_hint`'in tüketildiği yer) bul ve şu deseni uygula:

```python
if not is_spec_valid(one_sided, lsl, usl):
    if param_config.get("is_custom", False) and not param_config.get("has_specification", True):
        st.info(
            "ℹ️ Bu özel parametre için spesifikasyon limiti (LSL/USL) "
            "tanımlanmamış — yalnızca UCL/LCL proses kontrol limitleri "
            "geçerlidir, Cpk/Cpu/Ppk/Pp hesaplanmaz."
        )
    else:
        st.warning("LSL/USL gecersiz (LSL >= USL) - Cpk hesaplanamiyor.")
```

Bu, mevcut `is_spec_valid` kontrolünün olduğu **her** gösterim noktasında (KPI kartı, PDF export öncesi, sidebar durum noktası) tekrarlanan bir örüntüdür — `compute_active_parameter_status()` (satır 187-188) zaten `if not is_spec_valid(...): return "gray", None` ile bunu otomatik "nötr" gösteriyor, oraya ek değişiklik gerekmez (zaten doğru davranıyor). Sadece **kullanıcının gördüğü metin** güncellenir.

- [ ] **Step 2: Test**

```python
def test_has_specification_message_branch_exists():
    with open(APP_PATH, encoding="utf-8") as f:
        source = f.read()
    assert 'param_config.get("has_specification", True)' in source
    assert "yalnızca UCL/LCL proses kontrol limitleri" in source
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `pytest tests/test_app_render_smoke.py -v`
Expected: PASS

- [ ] **Step 4: Manuel QA**

Spesifikasyonsuz bir custom I-MR parametre oluştur (Spesifikasyon: "Belirtilmiyor"), birkaç ölçüm gir, Chart sekmesinde Cpk kartının **görünmediğini**, bunun yerine bilgi notunun göründüğünü doğrula. Kontrol grafiğinin (UCL/LCL) yine de çizildiğini doğrula.

- [ ] **Step 5: Commit**

```bash
git add src/app.py tests/test_app_render_smoke.py
git commit -m "feat: hide Cpk/Cpu for custom parameters without specification limits"
```

---

## Self-Review Notu (plan yazarı tarafından, spec'e karşı)

- **Spec kapsaması:** Mimari (getter+cache, 5 call-site, kategori genişletme) → Task 3; SQLite şeması → Task 1 (+ eksik `min_value`/`max_value` düzeltmesi not edildi); form alanları (zorunlu+gelişmiş, "Sayım"→0 ondalık) → Task 5; `has_specification` türetme ve Cpk gizleme → Task 2 + Task 7; kaçınılacaklar (Senaryo A/C, EAV, `is_microbio`, demo alanları) → Global Constraints + Task 4 (crash guard'lar bu kaçınmaların doğal sonucu olarak gerekti). Kalıcılık uyarısı → Task 5 form metni.
- **Placeholder taraması:** Her adımda çalıştırılabilir kod var; "TODO"/"benzer şekilde" yerine somut satır/blok verildi (Task 6 Adım 3'teki I-MR/X-bar/R birleşik `submitted` bloğu istisnası açıkça gerekçelendirildi).
- **Tip tutarlılığı:** `custom_parameter_id`, `custom_subgroup_size`, `is_custom`, `has_specification`, `log_scale` alan adları Task 2 (üretici) ve Task 3/5/6/7 (tüketici) arasında birebir aynı kullanıldı.
