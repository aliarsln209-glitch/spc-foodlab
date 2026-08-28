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

    'products' HER ZAMAN sadece {'Ozel/Manuel gir': None} icerir: custom
    parametrelerde urun-bazli LSL/USL yok, tek bir genel LSL/USL var -
    resolve_current_spec_hint() ve demo_scenario_targets() gibi built-in
    tuketiciler zaten product_range=None durumunu genel varsayilana
    (default_lsl/default_usl) duserek ele aliyor, bu yuzden custom
    parametreler icin ekstra bir dallanma GEREKMEZ. 'Ozel/Manuel gir'
    anahtari, app.py'nin urun secim listesinde bu degeri VARSAYILAN
    OLARAK bulup .index() ile secebilmesi icin ZORUNLUdur (bkz. app.py
    ~2579-2617).

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
        "default_measurement": 0.0,
        "products": {"Ozel/Manuel gir": None},
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
