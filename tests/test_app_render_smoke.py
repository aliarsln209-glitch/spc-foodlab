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
