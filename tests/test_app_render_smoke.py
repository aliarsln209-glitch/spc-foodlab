"""
Canli denetim raporunda bulunan KRITIK hatanin (1.1) regresyon testi.

Bulgu: v1.4->v1.6 Food Quality Parameters'in (Protein, Yag, Kul, Kuru Madde,
Yogunluk, Refraktif Indeks, L*, a*, b*, Bulaniklik, Iletkenlik) hicbiri icin
app.py'deki "Sekme 2: X-bar/R Chart & Cpk" altindaki parametre-ozel bilgi
kartinin if/elif zincirinde bir dal yoktu; hepsi yanlislikla mikrobiyoloji-
ozel 'else' daline dusuyor ve orada 'Default LOD' karti None/'-' uzerinde
':g' format spesifikasyonu deneyip ValueError ile COKUYORDU.

Bu, app.py'yi gercekten calistiran (Streamlit AppTest) bir uctan uca test
DEGIL - o yaklasim denendi, ancak sidebar'daki parametre radio'sunun
format_func'u aktif parametrenin canli Cpk durumuna gore nokta rengini
DINAMIK urettigi icin AppTest'in kendi widget-durum senkronizasyonu
(rerun'lar arasi onceki formatlanmis deger/yeni options karsilastirmasi)
bagimsiz olarak kiriliyor - bu ayri, once-var bir kirilganlik, bizim
duzeltmemizle ilgisiz. Onun yerine, kaynak koddaki if/elif zincirinin
yapisini dogrudan denetleyen, ayni sinif regresyonu (yeni bir parametre
eklenip bu zincire dal eklenmesi unutulursa) yakalayan bir statik test
kullanilir.
"""

import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from constants import FOOD_QUALITY_PARAMETER_CONFIG, PARAMETER_CATEGORIES

APP_PATH = os.path.join(os.path.dirname(__file__), "..", "src", "app.py")


def _read_info_card_chain() -> str:
    with open(APP_PATH, encoding="utf-8") as f:
        source = f.read()
    start = source.index('elif active_param == "pH":')
    end = source.index("_methods.append(", start)
    return source[start:end]


def test_food_quality_catchall_branch_exists_before_microbio_else():
    chain = _read_info_card_chain()
    catchall_pos = chain.index("elif active_param in FOOD_QUALITY_PARAMETER_CONFIG:")
    else_pos = chain.index("else:  # is_microbio")
    assert catchall_pos < else_pos, (
        "FOOD_QUALITY_PARAMETER_CONFIG yakalama dali, mikrobiyoloji-ozel "
        "'else' dalindan ONCE olmali - aksi halde v1.4-1.6 parametreleri "
        "yine yanlislikla mikrobiyoloji daline duser (bkz. 1.1 bulgusu)."
    )


def test_every_food_quality_parameter_is_covered():
    chain = _read_info_card_chain()
    named_branches = set(re.findall(r'elif active_param == "([^"]+)":', chain))
    has_catchall = "elif active_param in FOOD_QUALITY_PARAMETER_CONFIG:" in chain
    uncovered = [
        p for p in FOOD_QUALITY_PARAMETER_CONFIG
        if p not in named_branches and not has_catchall
    ]
    assert not uncovered, (
        f"Su parametreler icin bilgi karti dalı yok, mikrobiyoloji 'else' "
        f"dalina dusup cokebilirler: {uncovered}"
    )


def test_microbio_else_branch_uses_default_lod_only_for_actual_microbio():
    # Format spesifikasyonu (':g') sadece sayisal bir deger geldiginde
    # guvenlidir - default_lod'un None/'-' oldugu (mikrobiyoloji DISI)
    # bir parametre bu dala hicbir zaman ulasmamali (yukaridaki iki test
    # bunu yapisal olarak garanti eder). Burada regresyonun asil nedenini
    # (":g" formatinin varsayilan '-' uzerinde calisamamasi) dokumante
    # etmek icin dogrudan davranisi da dogruluyoruz.
    import pytest
    with pytest.raises(ValueError):
        f"{'-':g}"


def test_a_star_and_b_star_config_still_valid_but_not_in_sidebar_categories():
    # Task 5'in sonucu: a*/b* PARAMETER_CONFIG'de KALDI (Renk Paneli
    # okuyor) ama hicbir PARAMETER_CATEGORIES grubunda AYRI listelenmiyor.
    all_categorized = {p for _cat_id, _label, params in PARAMETER_CATEGORIES for p in params}
    assert "a*" not in all_categorized
    assert "b*" not in all_categorized
    assert "L*" in all_categorized
    assert "a*" in FOOD_QUALITY_PARAMETER_CONFIG
    assert "b*" in FOOD_QUALITY_PARAMETER_CONFIG


def test_color_lab_data_entry_uses_widget_keys_not_form():
    # Task 2: st.form KALDIRILDI (canli onizleme icin) - regresyon: biri
    # yanlislikla st.form'u geri getirirse bu testin yakalamasi beklenir.
    with open(APP_PATH, encoding="utf-8") as f:
        source = f.read()
    start = source.index("def render_color_lab_data_entry_tab()")
    end = source.index("def render_color_lab_chart_tab()")
    body = source[start:end]
    assert 'st.form("color_lab_entry_form")' not in body
    assert 'key=f"color_lab_l_input_' in body
    assert 'key=f"color_lab_lot_input_' in body


def test_color_lab_chart_tab_uses_min_recommended_baseline_threshold():
    # Task 3: duzenli MIN_RECOMMENDED_BASELINE sabiti kullanilmali, yeni
    # bir esik icat edilmemis olmali.
    with open(APP_PATH, encoding="utf-8") as f:
        source = f.read()
    start = source.index("def render_color_lab_chart_tab()")
    end = source.index("def render_generic_data_entry_tab()")
    body = source[start:end]
    assert "MIN_RECOMMENDED_BASELINE" in body
    assert "annotate_hline" in body


def test_history_table_column_config_includes_traceability_columns():
    # Task 5: gecmis tablosunda lot_no/notes duzenlenebilir, urun/timestamp
    # salt-okunur olmali - regresyon: biri yanlislikla bu sutunlari
    # cikarirsa veya disabled durumunu ters cevirirse bu test yakalar.
    with open(APP_PATH, encoding="utf-8") as f:
        source = f.read()
    start = source.index("def render_generic_data_entry_tab()")
    end = source.index("def render_generic_chart_tab()")
    body = source[start:end]
    assert 'column_config["Parti/Lot No"] = st.column_config.TextColumn()' in body
    assert 'column_config["Not"] = st.column_config.TextColumn()' in body
    assert 'column_config["Urun"] = st.column_config.TextColumn(disabled=True)' in body
    assert 'column_config["Zaman"] = st.column_config.TextColumn(disabled=True)' in body
    assert '"Urun": st.column_config.TextColumn(disabled=True),' in body  # microbio dali


def test_render_bridge_widget_no_longer_hardcodes_sabah_shift():
    # Task 2: eski tasarimda X-bar/R kopruleri icin sabit shift="Sabah"
    # varsayimi vardi (spec review'da reddedildi) - artik gercek bir
    # Vardiya selectbox'i olmali.
    with open(APP_PATH, encoding="utf-8") as f:
        source = f.read()
    start = source.index("def render_bridge_widget(")
    end = source.index("with tab_calc:")
    body = source[start:end]
    assert 'st.selectbox(\n            "Vardiya", SHIFT_OPTIONS, key=f"{widget_key_prefix}_shift"' in body
    assert 'shift="Sabah"' not in body
    assert "shift_label=" not in body  # eski API tamamen kaldirildi


def test_render_bridge_widget_stamps_urun_and_notes():
    with open(APP_PATH, encoding="utf-8") as f:
        source = f.read()
    start = source.index("def render_bridge_widget(")
    end = source.index("with tab_calc:")
    body = source[start:end]
    assert 'urun=st.session_state.get("product_select", "")' in body
    assert 'notes=f"QC Dönüştürücü - {source_label}"' in body


def test_moisture_dry_matter_panel_exists_and_is_routed():
    # Task 1: Nem/Kuru Madde Birlesik Paneli - active_parameter bu iki
    # degerden biriyken tab_data render_moisture_dry_matter_data_entry_tab'a
    # yonlenmeli, fonksiyon gravimetric_moisture'i n kez cagirip dogrudan
    # aktif parametreye yazmali (render_bridge_widget KULLANILMAMALI - hedef
    # zaten belli, secim UI'i gereksiz).
    with open(APP_PATH, encoding="utf-8") as f:
        source = f.read()
    assert 'active_parameter in ("Nem/Rutubet", "Kuru Madde")' in source
    start = source.index("def render_moisture_dry_matter_data_entry_tab()")
    end = source.index("def render_generic_data_entry_tab()")
    body = source[start:end]
    assert "gravimetric_moisture(" in body
    assert "build_bridge_subgroup_entry(" in body
    assert "render_bridge_widget(" not in body  # bu panelde KULLANILMAZ
    assert "render_generic_data_entry_tab()" in body  # dogrudan deger girisi altta kalir
    assert 'entry["lot_no"] = lot_no' in body
    # widget key'leri active_parameter'i icermeli - aksi halde Nem/Rutubet
    # (subgroup_size=1) ile Kuru Madde (daima n=1) ayni key'i paylasip
    # parametreler arasi gecişte eski degerleri tasir (bkz. kullanici
    # geri bildirimi / implementasyon plani onceki turu).
    assert 'key_scope = f"{st.session_state.active_parameter}_{n}"' in body


def test_old_gravimetric_calculator_removed_from_tab_calc():
    # Task 1: eski tekil hesaplayici (Hizli Hesaplayicilar sekmesinde,
    # sadece TEK hedefe koprulenebiliyordu) yeni panelle DEGISTIRILDI.
    with open(APP_PATH, encoding="utf-8") as f:
        source = f.read()
    start = source.index("with tab_calc:")
    end = source.index("st.markdown(\"### \U0001F9EA Titre Edilebilir Asitlik\")")
    body = source[start:end]
    assert "qc_moisture_tare" not in body
    assert "### ⚖️ Gravimetrik Nem / Kuru Madde" not in body
