"""SPC FoodLab - pH/Brix/Aw/Viskozite/Mikrobiyoloji (log10-CFU) Istatistiksel Proses Kontrolu (Streamlit MVP)."""

import io
import textwrap
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
from fpdf import FPDF
from scipy import stats

import csv_io
from constants import (
    DEFAULT_SUBGROUP_SIZE,
    F0_BRIDGE_PARAMETER_CONFIG,
    FOOD_QUALITY_PARAMETER_CONFIG,
    MAX_SUBGROUP_SIZE,
    MIN_SUBGROUP_SIZE,
    PARAMETER_CATEGORIES,
    PARAMETER_CONFIG,
    PARAMETER_DESCRIPTIONS,
    PARAMETER_INFO,
    PARAMETER_SOURCES,
    RAW_MATERIAL_PREFIX,
    RAW_MATERIAL_QC_REFERENCE,
    SHIFT_OPTIONS,
    TITRATABLE_ACID_MEQ_FACTORS,
    TOTOX_BRIDGE_PARAMETER_CONFIG,
)
from demo_data import generate_demo_individual, generate_demo_subgroups
from microbiology import build_subgroup_entry, to_log10
from pdf_report import build_pdf_report
from qc_converters import build_bridge_subgroup_entry, bridge_value_count_matches, bridge_value_is_single, gravimetric_moisture, salt_content_mohr, thermal_lethality_f0, titratable_acidity
from result_helpers import (
    build_dry_matter_moisture_consistency_note,
    build_parameter_info_card,
    build_quick_summary,
    build_totox_comment,
    build_trend_nelson_comment,
    compute_trend,
    demo_scenario_targets,
    format_cpk,
    get_cpk_level,
    measurement_plausibility_warnings,
)


def get_parameter_info_text(param_name: str) -> str:
    """Parametre bilgi karti icin gosterilecek metni dondurur - Food Quality
    Parameters (Protein/Yag/Kul/Kuru Madde, v1.4 Faz 1) FOOD_QUALITY_
    PARAMETER_CONFIG'de tanimliysa framework'un OTOMATIK urettigi karti
    (bkz. result_helpers.build_parameter_info_card) kullanir; legacy
    parametreler (pH..Kantitatif S. aureus) icin elle yazilmis PARAMETER_INFO
    metnine geri doner - iki farkli yazim tarzi ayni fonksiyondan cikmasin
    diye burada ayristirilir."""
    if param_name in FOOD_QUALITY_PARAMETER_CONFIG:
        return build_parameter_info_card(FOOD_QUALITY_PARAMETER_CONFIG[param_name])
    return PARAMETER_INFO.get(param_name, "")
from spc_core import (
    CONTROL_CHART_CONSTANTS,
    I_CHART_CONSTANT,
    MR_CHART_D2,
    MR_CHART_D4,
    compute_cpk,
    compute_imr_limits,
    compute_moving_ranges,
    compute_pp,
    compute_ppk,
    compute_xbar_r_limits,
    is_spec_valid,
)
from nelson_rules import (
    check_rule_2of3_beyond_2sigma,
    check_rule_4of5_beyond_1sigma,
    check_rule_9_same_side,
)
from normality import MIN_SAMPLE_SIZE_FOR_SHAPIRO, check_normality, interpret_normality

GITHUB_URL = "https://github.com/aliarsln209-glitch/spc-foodlab"


def raw_material_name(product_name: str) -> str | None:
    """Urun secim listesindeki bir girdi hammadde ise (RAW_MATERIAL_PREFIX ile
    baslar) duz hammadde adini dondurur, degilse (bitmis urun/'Ozel/Manuel
    gir') None dondurur - Cpk/istatistik motorunu etkilemez, sadece hammadde
    icin ayri 'Hammadde QC Referansi' notunun gosterilip gosterilmeyecegine
    karar vermek icin kullanilir."""
    if product_name.startswith(RAW_MATERIAL_PREFIX):
        return product_name[len(RAW_MATERIAL_PREFIX):]
    return None


MIN_RECOMMENDED_BASELINE = 20
CPK_SANITY_THRESHOLD = 10  # |Cpk| bu esigi asarsa LSL/USL-veri uyumsuzlugu uyarisi goster

st.set_page_config(page_title="SPC FoodLab", page_icon="\U0001F4CA", layout="wide")

if "subgroups" not in st.session_state:
    st.session_state.subgroups = []  # list of dict: {"shift": str, "values": list[float]}
if "baseline" not in st.session_state:
    st.session_state.baseline = None  # dict: {"x_double_bar", "r_bar", "n_baseline"}
if "active_parameter" not in st.session_state:
    st.session_state.active_parameter = "pH"
if "subgroup_size" not in st.session_state:
    st.session_state.subgroup_size = DEFAULT_SUBGROUP_SIZE
for _flag in ("confirm_clear", "confirm_freeze", "confirm_reset_baseline", "confirm_param_switch"):
    if _flag not in st.session_state:
        st.session_state[_flag] = False


def compute_stats(subgroups):
    """Alt gruplardan ortalama/range listelerini ve genel ortalama/R-bar'i hesaplar.
    Her kullanim yerinde taze cagrilir, boylece ayni script run'i icindeki veri
    mutasyonlarindan hemen sonra dogru sonuc verir."""
    means = [sum(sg["values"]) / len(sg["values"]) for sg in subgroups]
    ranges = [max(sg["values"]) - min(sg["values"]) for sg in subgroups]
    x_double_bar = sum(means) / len(means) if means else None
    r_bar = sum(ranges) / len(ranges) if ranges else None
    return means, ranges, x_double_bar, r_bar


def compute_individual_stats(subgroups):
    """I-MR (alt grup olmayan) parametreler icin: her 'subgroup' tek bir olcum
    degeri icerir (values listesi uzunlugu 1). Ardisik degerler arasindaki
    moving range'i ve ozet istatistikleri hesaplar. compute_stats'a benzer
    sekilde her kullanim yerinde taze cagrilir."""
    values = [sg["values"][0] for sg in subgroups]
    moving_ranges = compute_moving_ranges(values)
    x_bar = sum(values) / len(values) if values else None
    mr_bar = sum(moving_ranges) / len(moving_ranges) if moving_ranges else None
    return values, moving_ranges, x_bar, mr_bar


def resolve_current_spec_hint(param_cfg: dict) -> tuple[float, float, bool]:
    """su anki (lsl, usl, one_sided) 'tahminini' session_state'ten okur -
    henuz tab_chart'a hic gidilmemisse veya widget'lar bu run'da render
    edilmemisse param_cfg'nin varsayilanlarina duser. compute_active_
    parameter_status() VE render_measurement_plausibility_warning() (Madde
    8, canli girdi dogrulama) TARAFINDAN AYNI sekilde kullanilir - onceden
    bu mantik sadece birincisinde tekrarsizdi, ikinci kullanim yeri
    eklenince ortak fonksiyona cikarildi."""
    lsl = st.session_state.get("lsl_input", param_cfg["default_lsl"])
    usl = st.session_state.get("usl_input", param_cfg["default_usl"])
    selected_product = st.session_state.get("product_select")
    product_range = param_cfg["products"].get(selected_product)
    if product_range is not None:
        one_sided = product_range[0] is None
    else:
        one_sided = param_cfg.get("one_sided", False)
    return lsl, usl, one_sided


def compute_active_parameter_status() -> tuple[str, float | None]:
    """Sidebar'daki parametre secici icin: SADECE su an aktif olan parametrenin
    guncel Cpk/Cpu'suna gore ('green'/'red'/'gray') basit bir durum dondurur.

    ADIM 2 kapsam karari (kullanici ile teyit edildi): session_state.subgroups
    tek parametreye ozgu (parametre degisince veri silinir) - bu yuzden diger
    8 parametre icin ANLAMLI bir durum hesaplanamaz, sadece aktif parametre
    icin gosterilir. Tum 9 parametrenin es zamanli takibi (veri modelini
    {parametre: veri} sozlugune cevirmeyi gerektiren daha buyuk bir refactor)
    kasitli olarak ayri bir goreve birakildi.

    'gray': durum HESAPLANAMIYOR (yetersiz veri VEYA LSL>=USL gecersiz
    spesifikasyon VEYA anlamsiz Cpk) - iyi/kotu degil, notr.
    Esik (yesil: Cpk>=1.33) kullanici ile teyit edildi - render_cpk_message'daki
    ayni "Yeterli" esigiyle tutarlidir."""
    if len(st.session_state.subgroups) < 2:
        return "gray", None

    active_param = st.session_state.active_parameter
    param_cfg = PARAMETER_CONFIG[active_param]
    is_indiv = param_cfg.get("is_individual", False)

    lsl, usl, one_sided = resolve_current_spec_hint(param_cfg)

    if not is_spec_valid(one_sided, lsl, usl):
        return "gray", None

    if param_cfg.get("is_microbio", False):
        # LSL/USL widget'lari HAM KOB/g olceginde tutulur (bkz. resolve_current_
        # spec_hint) ama compute_individual_stats() ASAGIDA zaten log10 degerler
        # dondurur (subgroups["values"] mikrobiyoloji icin log10'dur) - Cpk'ye
        # girmeden ONCE usl/lsl'i AYNI olcege (log10) cevirmek gerekir, aksi
        # halde ham/log olcek karisir ve anlamsiz bir Cpk uretilir.
        usl = to_log10(usl) if usl > 0 else usl

    if is_indiv:
        _, _, center, spread = compute_individual_stats(st.session_state.subgroups)
        n_val = 2
    else:
        _, _, center, spread = compute_stats(st.session_state.subgroups)
        n_val = st.session_state.subgroup_size

    cpk = compute_cpk(center, spread, n_val, lsl, usl, one_sided=one_sided)
    if cpk == float("inf"):
        return "green", cpk
    if cpk == float("-inf"):
        return "red", cpk
    if cpk != cpk or abs(cpk) > CPK_SANITY_THRESHOLD:  # NaN veya anlamsiz deger
        return "gray", cpk
    return ("green" if cpk >= 1.33 else "red"), cpk


def reset_parameter_scoped_state() -> None:
    """Parametre degistiginde (pH<->Brix) urun/limit widget'larini temizler.
    Degeri direkt yeni parametrenin varsayilanina ATAMAK yerine SILMEK tercih
    edildi: bu widget'lar hemen sonra render EDILMEYECEKSE (ornegin script
    sirasi geregi baska bir yerde rerun tetiklenirse), Streamlit render
    edilmeyen widget state'ini otomatik temizliyor - onceden yasanan ve kok
    nedeni bulunan bir hata. Silinen anahtarlar bir sonraki render'da
    tab_chart'taki init mantigiyla dogru parametre varsayilanlarindan yeniden
    olusturulur."""
    for key in ("product_select", "prev_product", "prev_parameter", "lsl_input", "usl_input"):
        st.session_state.pop(key, None)


# "Vazgec" ile parametre secici radyo'lari eski durumuna dondurmek icin: bu,
# radio widget'lari BU RUN'DA ZATEN olusturulmadan once yapilmali (Streamlit,
# bir widget'in session_state degerini o widget instantiate edildikten sonra
# degistirmeye izin vermiyor). Bu yuzden reset islemini bir onceki run'da
# birakilan bayrakla, widget'lardan once burada uyguluyoruz.
#
# Parametre secici artik TEK bir radio degil, PARAMETER_CATEGORIES'e gore
# gruplanmis (st.expander icinde) AYRI radio'lar - her biri KENDI key'ine
# ("parameter_radio_<kategori id>") sahip. Bu yuzden reset, aktif parametreyi
# ICEREN kategorinin radio'sunu aktif parametreye, DIGER TUM kategorilerin
# radio'larini None'a (secim yok) esitler - aksi halde onceden baska bir
# kategoride tiklanmis ama iptal edilmis/degistirilmis bir secim, o kategori
# artik aktif degilken bile "secili" gorunmeye devam ederdi (hayalet secim).
if st.session_state.pop("_reset_parameter_radio", False):
    for _cat_id, _cat_label, _cat_params in PARAMETER_CATEGORIES:
        st.session_state[f"parameter_radio_{_cat_id}"] = (
            st.session_state.active_parameter
            if st.session_state.active_parameter in _cat_params
            else None
        )
# Ayni sekilde n secici icin: iptal edildiginde widget'i eski degere dondurur
# (widget instantiate edilmeden ONCE yapilmali - bkz. yukaridaki aciklama).
if st.session_state.pop("_reset_subgroup_n_input", False):
    st.session_state.subgroup_size_input = st.session_state.subgroup_size

with st.sidebar:
    # "Ayarlar" basligi eskiden burada, parametre secicisinin USTUNDE
    # duruyordu - hicbir etkilesimi olmayan, tiklanabilir gibi gorunen bir
    # baslikti ve altindaki parametre secicisiyle degil, DIVIDER'dan sonraki
    # gercek ayarlarla (tema/renk) ilgiliydi (canli denetimde bulundu).
    # Asagida, gercek ayarlarin hemen ustune tasindi.

    # Durum noktasi: SADECE aktif parametre icin guncel Cpk'ye gore yesil/kirmizi,
    # digerleri notr gri ('bu parametre icin henuz veri yok/gosterilmiyor' -
    # veri modeli tek seferde tek parametreyi tuttugu icin, bkz.
    # compute_active_parameter_status() docstring'i). Esik: Cpk >= 1.33 yesil.
    _status, _status_cpk = compute_active_parameter_status()
    _status_dot = {"green": "\U0001F7E2", "red": "\U0001F534", "gray": "\U000026AA"}[_status]

    def _param_radio_label(p: str) -> str:
        # Sadece AKTIF parametre icin durum noktasi gosterilir (Cpk'ye gore
        # yesil/kirmizi/gri anlam tasir); digerlerinde hicbir zaman anlamli
        # bir renk olmadigi icin (hep notr beyaz) - bu, secim isaretinin
        # yaninda anlamsiz/isik gibi yanan bir ikinci nokta gorunumu
        # yaratiyordu (canli denetimde bulundu) - onlarda nokta hic
        # gosterilmez, sadece isim yazilir.
        if p == st.session_state.active_parameter:
            return f"{_status_dot} {p}"
        return p

    st.caption("Parametre")
    # 9 parametre 3 kategoriye (Fiziksel/Duyusal, Kimyasal Kompozisyon,
    # Oksidasyon/Bozulma) gruplandi - sadece AKTIF parametreyi iceren kategori
    # varsayilan olarak acik baslar, digerleri kapali (sidebar'in daha kisa/
    # taranabilir kalmasi icin); kullanici istedigi kategoriyi elle acabilir.
    selected_param_radio = st.session_state.active_parameter
    for _cat_id, _cat_label, _cat_params in PARAMETER_CATEGORIES:
        _is_active_category = st.session_state.active_parameter in _cat_params
        with st.expander(_cat_label, expanded=_is_active_category):
            _default_index = _cat_params.index(st.session_state.active_parameter) if _is_active_category else None
            _picked = st.radio(
                f"Parametre - {_cat_label}", _cat_params,
                index=_default_index,
                key=f"parameter_radio_{_cat_id}",
                format_func=_param_radio_label,
                captions=[PARAMETER_DESCRIPTIONS.get(p, "") for p in _cat_params],
                label_visibility="collapsed",
            )
        # SADECE farkli bir kategoride, aktif parametreden BASKA bir secim
        # yapildiysa gecerli sayilir - kendi kategorisinde None donen (henuz
        # tiklanmamis) diger radio'lar goz ardi edilir.
        if _picked is not None and _picked != st.session_state.active_parameter:
            selected_param_radio = _picked

    if selected_param_radio != st.session_state.active_parameter:
        if st.session_state.subgroups:
            st.warning(
                f"Mevcut veri ({st.session_state.active_parameter}) silinecek. "
                "Emin misiniz?"
            )
            pc1, pc2 = st.columns(2)
            with pc1:
                if st.button("Evet, degistir", type="primary", key="param_switch_yes"):
                    st.session_state.active_parameter = selected_param_radio
                    st.session_state.subgroups = []
                    st.session_state.baseline = None
                    reset_parameter_scoped_state()
                    # Yeni aktif parametreyi ICEREN kategorinin radio'su zaten
                    # dogru degeri gosteriyor (tiklanan bu oldugu icin), ama
                    # ONCEKI aktif parametrenin kategorisindeki radio hala eski
                    # degeri (session_state'te) tutuyor - bayrak olmadan bu,
                    # artik aktif OLMAYAN bir kategoride "hayalet" secili
                    # goruntu birakir (Playwright ile kanitlandi).
                    st.session_state._reset_parameter_radio = True
                    st.rerun()
            with pc2:
                if st.button("Vazgec", key="param_switch_no"):
                    st.session_state._reset_parameter_radio = True
                    st.rerun()
        else:
            st.session_state.active_parameter = selected_param_radio
            reset_parameter_scoped_state()
            # Ayni hayalet-secim nedeniyle (bkz. "Evet, degistir" yorumu) -
            # veri olmadigi icin onay istenmeden dogrudan gecilen bu durumda
            # da onceki aktif kategorinin radio'sunu temizlemek gerekir.
            st.session_state._reset_parameter_radio = True
            st.rerun()

    st.divider()
    st.subheader("Gorunum Ayarlari")
    chart_theme = st.selectbox("Tema (grafik + arayuz)", ["Acik", "Koyu"], key="chart_theme")
    accent_color = st.color_picker(
        "Vurgu rengi", value=st.session_state.get("accent_color", "#4c6ef5"),
        key="accent_color",
        help="Butonlar ve KPI kartlarindaki vurgu rengini degistirir (basari/uyari/hata renkleri sabit kalir).",
    )
    sidebar_color = st.color_picker(
        "Sidebar rengi", value=st.session_state.get("sidebar_color", "#0F172A"),
        key="sidebar_color",
        help=(
            "Bu sidebar'in (sol panel) zemin rengini degistirir - 'Tema "
            "(grafik + arayuz)' secimden (Acik/Koyu) BAGIMSIZDIR, uygulamanin "
            "sabit kimligi olarak kalir. Ana icerikteki widget renklerini "
            "etkilemez."
        ),
    )

dark = chart_theme == "Koyu"
param_config = PARAMETER_CONFIG[st.session_state.active_parameter]
unit = param_config["unit"]
# Laboratuvar cihazinin gercek olcum hassasiyetini yansitir (orn. pH metre
# 2 basamak verirken ekranda 4.5512344 gostermek sahte kesinlik olur) -
# tum grafik etiketi/tablo/Cpk-adim gosterimi buna gore yuvarlanir.
decimal_places = param_config["decimal_places"]
is_individual = param_config.get("is_individual", False)  # True: I-MR (alt grup yok), False: X-bar/R
is_microbio = param_config.get("is_microbio", False)  # True: log10-CFU (TPC/TMAB) - bkz. microbiology.py

if not is_individual:
    with st.sidebar:
        st.divider()
        selected_n = st.number_input(
            "Alt grup buyuklugu (n)",
            min_value=MIN_SUBGROUP_SIZE, max_value=MAX_SUBGROUP_SIZE,
            value=st.session_state.subgroup_size, step=1,
            key="subgroup_size_input",
            help=(
                f"Her alt grupta kac {unit} olcumu olacagini belirler. n=1 icin "
                "X-bar/R anlamsizdir (range her zaman 0 olur) - bu yuzden alt "
                f"sinir n={MIN_SUBGROUP_SIZE}'dir; tek tek olculen parametreler "
                "(Viskozite, Peroksit, HMF) zaten ayri bir chart turu olan I-MR "
                "kullanir. Ust sinir, standart Montgomery SPC sabit tablosunun "
                f"kapsadigi n={MAX_SUBGROUP_SIZE}'dur. Pratikte n=4-5 yaygindir."
            ),
        )
        if selected_n != st.session_state.subgroup_size:
            if st.session_state.subgroups:
                st.warning(
                    f"n degeri {st.session_state.subgroup_size} -> {selected_n} olarak "
                    "degistirilirse mevcut alt gruplar ve baseline silinecek "
                    "(mevcut veri eski n'e gore girildi). Emin misiniz?"
                )
                nc1, nc2 = st.columns(2)
                with nc1:
                    if st.button("Evet, degistir", type="primary", key="n_change_yes"):
                        st.session_state.subgroup_size = selected_n
                        st.session_state.subgroups = []
                        st.session_state.baseline = None
                        st.rerun()
                with nc2:
                    if st.button("Vazgec", key="n_change_no"):
                        st.session_state._reset_subgroup_n_input = True
                        st.rerun()
            else:
                st.session_state.subgroup_size = selected_n
                st.rerun()

subgroup_n = st.session_state.subgroup_size


def contrasting_sidebar_text_colors(hex_color: str) -> tuple[str, str, str]:
    """Sidebar rengi SERBESTCE secilebildigi icin (acik tonlar dahil), metin
    rengini SABIT acik birakmak kullanici acik bir sidebar rengi sectiginde
    yaziyi okunmaz hale getiriyordu. Bunun yerine secilen zeminin
    parlakligina gore (YIQ formulu - bkz. https://24ways.org/2010/calculating-color-contrast)
    ana metin + soluk caption + renk-secici-swatch cercevesi rengi otomatik
    hesaplanir; boylece renk secici kisitlanmadan (herhangi bir ton
    secilebilir) her zaman okunakli kalir. Gecersiz/eksik hex girisinde
    (ör. renk secici henuz tam yazilmamisken) guvenli varsayilan olarak
    koyu-zemin varsayimiyla acik metin dondurulur."""
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return "#E8EAF0", "#A8B0C3", "rgba(232,234,240,0.35)"
    try:
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    except ValueError:
        return "#E8EAF0", "#A8B0C3", "rgba(232,234,240,0.35)"
    yiq = (r * 299 + g * 587 + b * 114) / 1000
    if yiq >= 150:
        # acik zemin -> koyu metin + soluk koyu gri caption + koyu swatch cercevesi
        return "#1A1D29", "#5A6072", "rgba(26,29,41,0.35)"
    # koyu zemin -> acik metin + soluk acik gri caption + acik swatch cercevesi
    return "#E8EAF0", "#A8B0C3", "rgba(232,234,240,0.35)"


def inject_theme_css(dark: bool, accent: str, sidebar_color: str) -> None:
    """Secilen acik/koyu temayi + vurgu rengini grafiklerin otesinde tum
    arayuze (sidebar, kartlar, metrikler, uyari kutulari) uygular. Streamlit'in
    kendi config.toml temasi Community Cloud'da calisma anindan
    degistirilemedigi icin bu, custom CSS injection ile yapiliyor.

    Ayrica hafif (agir olmayan) hover/gecis animasyonlari icerir - buton
    hover'da kucuk buyume, karti gecisi, uyari kutularinda fade-in. Amac
    sadece arayuzu biraz daha 'canli' hissettirmek, dikkat dagitmamak."""
    sidebar_text, sidebar_caption, sidebar_swatch_border = contrasting_sidebar_text_colors(sidebar_color)
    # "Vazgec" gibi ikincil butonlar icin ayri bir zemin/metin cifti: sidebar
    # zemini KOYUYSA (sidebar_text acik -> "#E8EAF0") buton acik gri zeminde
    # koyu metin alir, sidebar zemini ACIKSA bunun tersi - boylece buton her
    # zaman sidebar zemininden ayrisan, kendi icinde okunakli bir "kart" gibi
    # gorunur (canli denetimde bulunan beyaz-zeminde-beyaz-yazi hatasinin fix'i).
    if sidebar_text == "#E8EAF0":
        sidebar_button_bg, sidebar_button_text = "#2A3142", "#E8EAF0"
    else:
        sidebar_button_bg, sidebar_button_text = "#E4E7EC", "#1A1D29"
    # KART SECICI NOTU: Streamlit >=1.5x'te st.container(border=True) artik
    # sabit bir data-testid ("stVerticalBlockBorderWrapper") ILE ISARETLENMIYOR -
    # bordered/border'siz tum bloklar ayni data-testid="stVerticalBlock"'u
    # paylasiyor, aralarindaki tek fark, build'e gore degisebilen rastgele bir
    # emotion-cache class hash'i (CSS'te guvenle hedeflenemez, Streamlit
    # surum guncellemesinde sessizce kirilir - dogrulama: bkz. PR/commit notu).
    # Bunun yerine Streamlit'in RESMI/STABIL API'si kullanildi: her
    # st.container(border=True, key=...) cagrisina "card-" ile baslayan bir
    # key verildi (bkz. asagidaki with bloklari), bu da tarayicida
    # class="... st-key-<key> ..." sabit bir CSS sinifi uretir. Asagidaki
    # [class*="st-key-card-"] secici, Streamlit surumunden BAGIMSIZ calisir.
    if dark:
        theme_css = """
        .stApp { background-color: #0e1117 !important; }
        .stApp, .stApp p, .stApp span, .stApp label,
        h1, h2, h3, h4, h5, h6 { color: #fafafa; }
        [data-testid="stMetricValue"], [data-testid="stMetricLabel"] { color: #fafafa; }
        [class*="st-key-card-"] {
            background-color: #161a23 !important;
            border-color: #333c4a !important;
        }
        [data-testid="stNumberInput"] input,
        [data-testid="stTextInput"] input,
        [data-testid="stSelectbox"] div[data-baseweb="select"] > div {
            background-color: #262d3d;
            color: #fafafa;
        }
        [data-testid="stDataFrame"] { color-scheme: dark; }
        .stAlert { background-color: #1c2230; }
        button[kind="secondary"], [data-testid="stFormSubmitButton"] button {
            background-color: #262d3d;
            color: #fafafa !important;
            border-color: #333c4a;
        }
        """
    else:
        # Icerik zeminini duz beyaz yerine cok hafif gri-mavi (#F7F8FA) yapiyoruz
        # ki icindeki beyaz kartlar (st.container(border=True)) kontrastla
        # "kart" gibi ayrissin - config.toml'daki backgroundColor (#FFFFFF)
        # bilerek farkli: o, Streamlit'in kendi bilesenlerinin (ör. dialog,
        # menu) varsayilan zemini icin, burasi ise ana govde zemini icin.
        # !important sarttir: Streamlit'in kendi <head> icindeki emotion
        # CSS'i, ayni ozgullukte (0,1,0) bir .stApp kurali icerebiliyor ve
        # DOM sirasina gore bizimkini ezebiliyor (Playwright ile dogrulandi).
        theme_css = """
        .stApp { background-color: #F7F8FA !important; }
        [class*="st-key-card-"] {
            background-color: #ffffff !important;
            border-color: #E4E7EC !important;
        }
        """

    css = f"""
    <style>
    /* Tipografi: sistem fontu yerine Inter (web font) - @import CSS
       spesifikasyonu geregi stylesheet'in EN BASINDA olmak ZORUNDA
       (@charset disinda baska herhangi bir kuraldan ONCE gelmezse
       tarayici tarafindan yok sayilir), bu yuzden {{theme_css}}'den bile
       once, <style>'den hemen sonra yerlestirildi. Google Fonts CDN'i
       kullanir - tarayici (kullanicinin cihazi) bu istegi yapar, sunucu
       tarafinda internet erisimi gerektirmez. Font yuklenene kadar (veya
       CDN engelliyse) tarayici otomatik olarak sans-serif yedegine
       (sistem fontu) duser - bkz. font-family zincirindeki fallback'ler. */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    /* .stApp * KULLANILMADI: font-family zaten miras alinan (inherited) bir
       ozellik - tum alt elemanlar bunu otomatik devralir. "*" ile HER
       elemani (SVG/ikon elemanlari dahil) zorla ezmek, Streamlit'in olasi
       font-tabanli ikonlarini (checkmark/chevron/help sembolleri gibi)
       bozma riski tasirdi - inheritance ile bu risk yok, cunku bir ikonun
       KENDI font-family kurali (varsa) her zaman miras alinan degerden
       oncelikli olur. */
    html, body,
    .stApp,
    .stApp[data-testid="stApp"],
    [data-testid="stAppViewContainer"] {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
    }}
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6 {{
        font-weight: 700 !important;
        letter-spacing: -0.01em;
    }}

    {theme_css}

    /* Vurgu rengi (kullanici secimi) - primary butonlar + slider */
    button[kind="primary"] {{
        background-color: {accent} !important;
        border-color: {accent} !important;
    }}
    [data-testid="stSlider"] div[role="slider"] {{ background-color: {accent} !important; }}
    a {{ color: {accent}; }}

    /* Sidebar rengi (kullanici secimi, "Sidebar rengi" renk secici) - Tema
       (Acik/Koyu) anahtarindan BILEREK BAGIMSIZ: uygulamanin sabit kimligi
       olarak her iki modda da ayni kalir. SADECE [data-testid="stSidebar"]
       hedeflenir - config.toml'daki secondaryBackgroundColor (ana icerikteki
       number_input/selectbox zeminiyle PAYLASILIR) burada KULLANILMIYOR,
       tam da bu yuzden ADIM 1'de erteenmisti (secondaryBackgroundColor'i
       koyulastirmak ana icerikteki input kutularini da koyultup, Acik
       temadaki beyaz kartlarla cakisirdi). Metin renkleri SABIT DEGIL -
       sidebar_text/sidebar_caption, secilen zeminin parlakligina gore
       (contrasting_sidebar_text_colors) OTOMATIK hesaplanir: kullanici acik
       bir sidebar rengi secerse yazi da otomatik koyulasir, boylece renk
       secici kisitlanmadan (herhangi bir ton secilebilir) her zaman
       okunakli kalir - bkz. kullanici geri bildirimi (acik renkte yazi
       gorunmuyordu). */
    [data-testid="stSidebar"] {{
        background-color: {sidebar_color} !important;
    }}
    [data-testid="stSidebar"],
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] h4,
    [data-testid="stSidebar"] h5,
    [data-testid="stSidebar"] h6 {{
        color: {sidebar_text} !important;
    }}
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"],
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] * {{
        color: {sidebar_caption} !important;
    }}
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {{
        color: {sidebar_text} !important;
    }}
    /* Renk secici swatch'i, sectigi renk zeminle (ozellikle "Sidebar rengi"
       kendi rengini secip zeminle ayni tona geldiginde) karisip GORUNMEZ
       olmasin diye her zaman ince bir cerceve alir. */
    [data-testid="stSidebar"] [data-testid="stColorPickerBlock"] {{
        border: 1.5px solid {sidebar_swatch_border} !important;
        border-radius: 6px !important;
    }}

    /* Fix: "Vazgec" gibi ikincil (kind="secondary") butonlar sidebar icinde
       kendi varsayilan (acik temada beyaz) zeminini korurken, yukaridaki
       genel "p/span/label" kurali buton METNINI de sidebar_text'e (koyu
       sidebar zeminine gore secilen, genelde ACIK bir renk) boyuyordu -
       sonuc beyaz zeminde beyaz yazi, buton GORUNMEZ oluyordu (canli
       denetimde bulundu - parametre degistirme onay dialogundaki "Vazgec").
       Butonun kendi zeminini de sidebar_swatch_border ile ayni mantikla
       (sidebar rengine gore kontrastli) veriyoruz. */
    [data-testid="stSidebar"] button[kind="secondary"] {{
        background-color: {sidebar_button_bg} !important;
        color: {sidebar_button_text} !important;
        border-color: {sidebar_button_bg} !important;
    }}
    [data-testid="stSidebar"] button[kind="secondary"] p {{
        color: {sidebar_button_text} !important;
    }}

    /* Fix: parametre kategori basliklarinin (st.expander "summary" elementi)
       varsayilan arka plani Streamlit'in KENDI emotion CSS'inden gelen
       neredeyse-beyaz bir renk (#F8F9FC) - sidebar'in dark/custom rengiyle
       HIC ilgisi yok, cunku Streamlit temasi (config.toml) hala "light" ve
       BaseWeb bilesenleri buna gore render ediliyor. Bunun uzerine bizim
       acik renkli (sidebar_text) metnimiz binince dusuk kontrast/okunmaz
       yazi olusuyordu - ozellikle hover'da (varsayilan hover, bu beyaz
       zemini ayrica bir mavi-gri overlay ile daha da belirginlestiriyordu)
       kullanici tarafindan yakalandi. Zemin transparent yapilip, hover'a
       diger sidebar bilesenleriyle (Ince ayar 1 pill) AYNI desende ince bir
       Vurgu rengi tonu verildi. */
    [data-testid="stSidebar"] [data-testid="stExpander"] summary {{
        background-color: transparent !important;
    }}
    [data-testid="stSidebar"] [data-testid="stExpander"] summary:hover {{
        background-color: {accent}26 !important;
    }}

    /* Ince ayar 1: Aktif sidebar satirina arka plan pill'i - data-selected
       Streamlit'in KENDI semantik attribute'u (Playwright ile DOM'dan
       dogrulandi), emotion-cache hash'i degil - surum guncellemesinde
       kirilma riski dusuk. */
    [data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] {{
        background-color: {accent}26 !important;
        border-radius: 8px !important;
    }}

    /* Ince ayar 2: Aktif sekme gostergesi - Streamlit'in kendi
       react-aria-SelectionIndicator elemani (react-aria kutuphanesine ait,
       Streamlit build'inden bagimsiz stabil bir sinif) Vurgu rengiyle
       renklendirilir + kalinlastirilir; secili sekme metni de vurgu
       rengine + kalin agirliga gecer. */
    [data-testid="stTab"] .react-aria-SelectionIndicator {{
        background-color: {accent} !important;
        height: 3px !important;
    }}
    [data-testid="stTab"][data-selected="true"] p {{
        color: {accent} !important;
        font-weight: 700 !important;
    }}

    /* Ince ayar 3: Odak (focus) halkasi Vurgu rengiyle - klavye ile gezinme
       (Tab tusu) sirasinda tarayici varsayilani yerine. :focus-visible
       SADECE klavye odaklamada tetiklenir (fare tiklamasinda degil), bu
       yuzden mouse kullaniminda gereksiz halka gorunmez. */
    .stApp *:focus-visible {{
        outline: 2px solid {accent} !important;
        outline-offset: 2px !important;
    }}

    /* Ince ayar 4: Ince/ozel scrollbar - tarayicinin kalin varsayilanindan,
       sidebar rengiyle uyumlu ince bir cubuga. Firefox (scrollbar-width) +
       WebKit/Chromium (::-webkit-scrollbar) ayri ayri hedeflenir. */
    * {{
        scrollbar-width: thin;
        scrollbar-color: {sidebar_color}99 transparent;
    }}
    ::-webkit-scrollbar {{
        width: 8px;
        height: 8px;
    }}
    ::-webkit-scrollbar-track {{
        background: transparent;
    }}
    ::-webkit-scrollbar-thumb {{
        background-color: {sidebar_color}99;
        border-radius: 4px;
    }}

    /* Hafif hover/gecis animasyonlari - agir hareket yok, sadece kucuk
       buyume/golge/fade. */
    button {{ transition: transform 0.12s ease, box-shadow 0.12s ease; }}
    button:hover {{ transform: translateY(-1px) scale(1.01); }}

    /* Kart gorunumu: st.container(border=True, key="card-...") ile
       olusturulan tum bloklar (Ozet, Vardiya Karsilastirmasi, Hesaplama
       Adimlari vb.) yuvarlatilmis kose + hafif golge alir - Streamlit'in
       varsayilan ince-cizgili kutusundan, referans taslaktaki yumusak
       "card" hissine gecis. [class*="st-key-card-"] Streamlit'in resmi
       key= API'siyle uretilen SABIT bir sinif - surum guncellemesinde
       kirilmaz (bkz. yukaridaki KART SECICI NOTU). */
    [class*="st-key-card-"] {{
        border-radius: 12px !important;
        box-shadow: 0 1px 2px rgba(15,23,42,0.06), 0 2px 10px rgba(15,23,42,0.09);
        transition: box-shadow 0.2s ease;
    }}
    [class*="st-key-card-"]:hover {{
        box-shadow: 0 2px 12px rgba(0,0,0,0.10);
    }}

    .kpi-card {{ transition: transform 0.15s ease, box-shadow 0.15s ease; }}
    .kpi-card:hover {{ transform: translateY(-2px); box-shadow: 0 3px 10px rgba(0,0,0,0.12); }}

    /* Spacing/whitespace ferahligi: Streamlit'in varsayilan yogunlugu
       kullanici geri bildirimiyle "sikisik" bulundu. Kart ic dolgusu
       artirildi (nefes alan bir his icin); dikey blok elemanlari arasi
       bosluk (Streamlit'in kendi flex "gap"i) hafifce artirildi - ANCAK
       mevcut kodda kartlar arasinda zaten manuel st.write("") bosluklari
       var, bu yuzden gap COK buyutulmedi (aksi halde bosluklar ikiye
       katlanip asiri "havadar" gorunurdu). Sidebar'da biraz daha fazla
       (ayarlar bölümleri birbirinden daha net ayrilsin diye). */
    [class*="st-key-card-"] {{
        padding: 1.6rem 1.8rem !important;
    }}
    [data-testid="stVerticalBlock"] {{
        gap: 1.1rem;
    }}
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {{
        gap: 1.3rem;
    }}
    [data-testid="stSidebar"] hr {{
        margin: 1.3rem 0 !important;
    }}

    @keyframes spcFadeIn {{
        from {{ opacity: 0; transform: translateY(-4px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}
    .stAlert {{ animation: spcFadeIn 0.35s ease; }}
    </style>
    """
    # KRITIK: css f-string'i fonksiyonun kendi Python girinti seviyesini (4
    # bosluk) miras alir - dedent olmadan st.markdown() bunu CommonMark'in
    # "4+ bosluk girintili satir = kod bloğu" kuraliyla yorumlar ve '<style>'
    # etiketini kacis karakterli duz metin olarak basar (CSS hic uygulanmaz).
    # Daha once tam bu sorun yasanip duzeltilmis, sonra "Faz 2" toplu geri
    # alinirken duzeltme de kaybolmustu - bkz. gecmis commit f2173d1.
    st.markdown(textwrap.dedent(css).strip(), unsafe_allow_html=True)


inject_theme_css(dark, accent_color, sidebar_color)


def render_empty_state(icon: str, message: str) -> None:
    """Ince ayar 5: duz st.info() yerine, ilk acilista veya yetersiz veri
    durumunda kullaniciyi karsilayan bosluklarda (henuz veri yok, grafik
    icin yetersiz veri) biraz daha davetkar/yumusak bir gorsel - buyuk bir
    ikon + ortalanmis, soluk tonlu metin. Renk sabit notr gridir (tema/
    Vurgu rengine bagli degil) - hem Acik hem Koyu temada okunakli kalsin
    diye asiri koyu/acik uc degerlerden kacinildi."""
    st.markdown(
        f"""
        <div style="text-align:center; padding:2.4rem 1rem; color:#8a94a6;">
            <div style="font-size:2.4rem; margin-bottom:0.6rem; opacity:0.7;">{icon}</div>
            <div style="font-size:0.95rem;">{message}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_last_analysis_card(parameter: str, product: str, chart_type_label: str,
                               n_samples: int, cpk: float, cpk_label: str,
                               cpk_valid: bool = True) -> None:
    """Tek yerde ozet: Parametre, Urun, Ornek Sayisi, Chart Tipi, Sonuc + zaman damgasi.
    cpk_valid=False (LSL>=USL gecersiz spesifikasyon) durumunda gercek Cpk
    degeri/rozeti YERINE somut bir 'gecersiz' notu gosterir - get_cpk_level()
    gecersiz bir sayiyi (orn. -6.998) yine de bir renk/etikete siniflandirip
    yaniltici bir sonuc gostermis olurdu."""
    st.caption(f"\U0001F553 Son analiz: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    la1, la2, la3, la4, la5 = st.columns(5)
    la1.markdown(f"**Parametre**  \n{parameter}")
    la2.markdown(f"**Urun**  \n{product}")
    la3.markdown(f"**Ornek Sayisi**  \n{n_samples}")
    la4.markdown(f"**Chart Tipi**  \n{chart_type_label}")
    if cpk_valid:
        emoji, level_label, _ = get_cpk_level(cpk)
        la5.markdown(f"**Sonuc**  \n{emoji} {cpk_label}={format_cpk(cpk)} ({level_label})")
    else:
        la5.markdown(f"**Sonuc**  \n⚠️ {cpk_label}=Gecersiz (LSL≥USL)")


def render_formula_method_card(chart_type_label: str, n_val: int) -> None:
    """Hangi chart tipinin/formulun kullanildigini ozetleyen kucuk kart,
    detay icin METHODOLOGY.md'ye link verir."""
    if chart_type_label == "I-MR":
        formula_line = f"I chart: x̄ ± {I_CHART_CONSTANT}×MR̄  ·  σ̂ = MR̄/d2 (d2={MR_CHART_D2}, n=2)"
    else:
        formula_line = f"X-bar/R: x̄̄ ± A2×R̄ (n={n_val})  ·  σ̂ = R̄/d2"
    st.caption(
        f"\U0001F4D0 Yontem: **{chart_type_label}** · {formula_line} · "
        f"Detay ve dogrulama: [METHODOLOGY.md]({GITHUB_URL}/blob/main/METHODOLOGY.md)"
    )


def render_pdf_download(parameter: str, product: str, chart_type_label: str,
                         n_samples: int, n_out_of_control: int, cpk: float,
                         cpk_label: str, quick_summary_text: str,
                         chart_images: list[tuple[str, bytes]], key: str) -> None:
    """'PDF olarak indir' butonu - build_pdf_report() ile ayni verilerden
    (ana kontrol grafigi + range/MR grafigi + histogram, hepsi dahil) bir
    rapor uretir."""
    pdf_bytes = build_pdf_report(
        parameter, product, chart_type_label, n_samples, n_out_of_control,
        cpk, cpk_label, quick_summary_text, chart_images,
    )
    st.download_button(
        "\U0001F4C4 PDF rapor olarak indir", pdf_bytes,
        f"{parameter.lower()}_spc_raporu.pdf", "application/pdf", key=key,
    )


def render_shift_comparison(subgroups: list[dict], n_val: int, lsl: float, usl: float,
                             one_sided: bool, cpk_label: str, unit: str) -> None:
    """Ayni parametre icin vardiyalara gore (Sabah/Ogle/Gece) ortalama ve
    Cpk/Cpu'yu yan yana gosteren basit bir tablo - tam bir batch comparison
    dashboard degil, mevcut veri uzerinde vardiya etiketine gore gruplama."""
    rows = []
    for shift in SHIFT_OPTIONS:
        shift_groups = [sg for sg in subgroups if sg["shift"] == shift]
        if not shift_groups:
            continue
        _, _, shift_mean, shift_r_bar = compute_stats(shift_groups)
        shift_cpk = compute_cpk(shift_mean, shift_r_bar, n_val, lsl, usl, one_sided=one_sided)
        rows.append({
            "Vardiya": shift,
            "Alt Grup Sayisi": len(shift_groups),
            f"Ortalama ({unit})": round(shift_mean, 4),
            cpk_label: format_cpk(shift_cpk),
        })

    with st.container(border=True, key="card-01"):
        st.subheader("Vardiya Karsilastirmasi")
        if len(rows) < 2:
            st.info(
                "Vardiya karsilastirmasi icin en az 2 farkli vardiyada veri olmali "
                "(su an tum veri ayni vardiyada veya vardiya cesitliligi yetersiz)."
            )
        else:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def fig_to_png_bytes(fig) -> bytes:
    """Matplotlib figurunu PNG bayt dizisine cevirir (indirme butonlari icin)."""
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    buf.seek(0)
    return buf.getvalue()


def render_png_download(fig, filename: str, key: str) -> None:
    """Verilen figur icin 'PNG olarak indir' butonu gosterir. plt.close(fig)
    cagrilmadan ONCE (byte'lar alinip kapatildiktan sonra da kullanilabilir,
    cunku fig_to_png_bytes zaten byte'lari kapatmadan once cikarir) cagrilmalidir."""
    png_bytes = fig_to_png_bytes(fig)
    st.download_button(
        "\U0001F5BC️ PNG olarak indir", png_bytes, filename, "image/png", key=key
    )


# CSV ayristirma/dogrulama mantigi src/csv_io.py'de (Streamlit'ten bagimsiz,
# pytest ile test edilebilir - bkz. tests/test_csv_io.py). Burada sadece
# csv_io.* fonksiyonlari cagrilir.


def cpk_capability_badge(cpk: float, cpk_valid: bool) -> tuple[str, str, str]:
    """ADIM 4: 'Surec Yeterliligi' karti icin basit UC RENKLI (yesil/sari/
    kirmizi) rozet - get_cpk_level()'in DORT seviyeli mavi/mor/kirmizi
    paletinden (result_helpers.py) BILEREK AYRI: o palet, kullanicinin
    serbestce sectigi 'Vurgu rengi' ile KPI kartlarindaki sonuc rengi
    arasindaki olasi karisikligi onlemek icin ozellikle yesil/kirmizi
    DISINDA secilmisti (bkz. get_cpk_level docstring'i). Burada (referans
    taslaktaki 'Capable' rozetine karsilik gelen, sidebar durum
    noktalarindaki ile AYNI ruhta bir gosterge) klasik yesil/sari/kirmizi
    kullanildi - ayni esikler (>=1.33 yesil, 1.0-1.33 sari, <1.0 kirmizi),
    compute_active_parameter_status() ile tutarli."""
    if not cpk_valid:
        return "⚪", "Gecersiz", "#868e96"
    if cpk == float("-inf"):
        return "\U0001F534", "Yetersiz", "#e03131"
    if cpk == float("inf") or cpk >= 1.33:
        return "\U0001F7E2", "Yeterli", "#2f9e44"
    if cpk >= 1.0:
        return "\U0001F7E1", "Sinirda", "#f08c00"
    return "\U0001F534", "Yetersiz", "#e03131"


def render_capability_card(cpk: float, cpk_label: str, cpk_valid: bool) -> None:
    """ADIM 4 'Process Capability' karti: buyuk Cpk/Cpu degeri + uc renkli
    rozet (bkz. cpk_capability_badge). X-bar/R ve I-MR'de AYNI - farklari
    (etiket, gecerlilik) zaten parametre olarak aliniyor."""
    emoji, level_label, color = cpk_capability_badge(cpk, cpk_valid)
    st.markdown(f"##### \U0001F3AF Surec Yeterliligi")
    if cpk_valid:
        st.markdown(
            f"<div style='font-size:2rem; font-weight:700;'>{format_cpk(cpk)}</div>"
            f"<div style='color:{color}; font-weight:600;'>{emoji} {level_label}</div>",
            unsafe_allow_html=True,
        )
        st.caption(f"{cpk_label} - genel kabul: >=1.33 yeterli, 1.0-1.33 sinirda, <1.0 yetersiz.")
        if abs(cpk) > CPK_SANITY_THRESHOLD:
            # render_cpk_message()'daki AYNI kontrol (o fonksiyon artik burada
            # cagrilmiyor - rozet zaten Yeterli/Sinirda/Yetersiz'i gosteriyor,
            # ayni bilgiyi tekrarlayan buyuk bir st.success/error/warning kutusu
            # kompakt kartta fazla yer kaplardi) - ama bu SPESIFIK uyari
            # (LSL/USL-veri uyumsuzlugu ihtimali) korunmali, veri kalitesi
            # acisindan onemli bir sinyal.
            st.warning(
                f"{cpk_label} anlamsiz derecede yuksek/dusuk cikti. Sectigin "
                "urunun spesifikasyon araligi, girdigin verilerle ortusmuyor "
                "olabilir - LSL/USL degerlerini kontrol et."
            )
    else:
        st.markdown(
            f"<div style='font-size:2rem; font-weight:700; color:#868e96;'>—</div>"
            f"<div style='color:{color}; font-weight:600;'>{emoji} {level_label}</div>",
            unsafe_allow_html=True,
        )
        st.caption(f"{cpk_label} hesaplanamadi: spesifikasyon gecersiz (LSL >= USL).")


def build_cpk_vs_ppk_comment(cpk: float, ppk: float) -> str:
    """Cpk (kisa vadeli, alt grup ICI) ile Ppk (genel/uzun vadeli, TUM ham
    veri) arasindaki farka gore kisa bir yorum cumlesi uretir - Ppk eklemenin
    GERCEK faydasini gosterir: ikisi yakinsa surec zaman icinde ISTIKRARLI
    (Cpk'nin gormedigi ek bir kayma yok); Ppk belirgin sekilde dusukse, Cpk'nin
    YAKALAYAMADIGI bir alt-gruplar-arasi kayma/trend olabilecegine isaret eder.

    0.2'lik esik KESIN bir istatistiksel test DEGIL - sadece "dikkate deger
    bir fark" icin basit, yorumlanabilir bir esik (SPC pratiginde yaygin
    kullanilan bir kural-of-thumb)."""
    if cpk in (float("inf"), float("-inf")) or ppk in (float("inf"), float("-inf")):
        return (
            "Kisa vadeli (Cpk) ve genel (Ppk) yeterlilik karsilastirmasi, "
            "sifir varyasyonlu uc durumlarda anlamli degildir."
        )
    if cpk - ppk > 0.2:
        return (
            f"Ppk ({format_cpk(ppk)}), Cpk'den ({format_cpk(cpk)}) belirgin sekilde dusuk - "
            "bu, alt gruplar ARASINDA (zaman icinde) Cpk'nin YAKALAYAMADIGI bir kayma/trend "
            "olabilecegine isaret eder."
        )
    return (
        f"Ppk ({format_cpk(ppk)}) ile Cpk ({format_cpk(cpk)}) birbirine yakin - "
        "surec zaman icinde nispeten ISTIKRARLI, alt gruplar arasinda belirgin bir kayma "
        "gorunmuyor."
    )


def render_ppk_pp_expander(cpk: float, ppk: float, pp: float | None, one_sided: bool) -> None:
    """'Süreç Yeterliliği' kartina eklenen, katlanabilir Ppk/Pp bolumu -
    Cpk'nin YANINDA, onu degistirmeden ek bir 'genel yeterlilik' bakis
    acisi sunar (bkz. build_cpk_vs_ppk_comment)."""
    with st.expander("\U0001F4C8 Ppk/Pp (genel yeterlilik)"):
        st.caption(
            "Cpk, alt grup ICI (kisa vadeli) varyasyona dayanir (σ̂=R̄/d2). "
            "Ppk/Pp ise TUM ham olculerin GENEL (uzun vadeli) ornek standart "
            "sapmasini kullanir - alt gruplar ARASINDAKI kaymalari/trendleri "
            "de yansitir."
        )
        # NOT: st.columns(2) ile yan yana denendi ama kart zaten dar (sayfa
        # genisliginin ~1/3'u) oldugu icin st.metric()'in buyuk fontu
        # "0.9..." gibi kirpiliyordu (Playwright ile canli DOM'da gozlendi) -
        # bu yuzden metrikler ALT ALTA, kartin TAM genisligini kullanacak
        # sekilde gosteriliyor.
        ppk_label = "Ppu (tek tarafli)" if one_sided else "Ppk"
        st.metric(ppk_label, format_cpk(ppk))
        if not one_sided:
            st.metric("Pp", format_cpk(pp) if pp is not None else "—")
        st.markdown(build_cpk_vs_ppk_comment(cpk, ppk))


def _oos_oot_status_row(label: str, count: int, color: str, soft_bg: str) -> str:
    """OOS/OOT satirlarinin HTML'ini uretir - render_data_summary_card
    icinde iki kez (OOS, OOT) cagrilir, kopyala-yapistir onlemek icin."""
    if count:
        return (
            f"<div style='background:{soft_bg}; color:{color}; font-weight:600; "
            f"border-radius:6px; padding:0.4rem 0.6rem; margin-top:0.4rem;'>"
            f"⚠️ {label}: {count}</div>"
        )
    return (
        f"<div style='background:#ebfbee; color:#2f9e44; font-weight:600; "
        f"border-radius:6px; padding:0.4rem 0.6rem; margin-top:0.4rem;'>"
        f"✅ {label}: 0</div>"
    )


def render_data_summary_card(mean_label: str, mean_value: float, spread_label: str,
                              spread_value: float, n_label: str, n_value: int,
                              n_oos: int, n_oot: int, decimal_places: int) -> None:
    """'Veri Ozeti' karti: ortalama/yayilim/ornek sayisi + AYRI AYRI iki satir
    - OOS (Out of Specification, mor - LSL/USL disina cikan HAM olcum sayisi)
    ve OOT (Out of Trend, kirmizi - UCL/LCL asimi VEYA Nelson oruntu sinyali
    veren nokta sayisi). Bu ikisi BAGIMSIZDIR: bir nokta OOT olabilir ama
    yine de spesifikasyon icinde kalabilir, ya da tersi - bkz. METHODOLOGY.md
    v1.2 'OOS/OOT ayrimi' maddesi. ONCEDEN (v1.1.1 ve oncesi) tek bir
    'Kontrol Disi' satiri vardi ve bu aslinda SADECE UCL/LCL asimini
    gosteriyordu, LSL/USL'i hic yansitmiyordu - bu karti cagiran taraf artik
    iki sayiyi AYRI hesaplayip geciriyor (bkz. compute_oos_flags,
    compute_nelson_oot_indices)."""
    st.markdown("##### \U0001F4CB Veri Ozeti")
    st.markdown(
        f"**{mean_label}**  \n{mean_value:.{decimal_places}f}  \n\n"
        f"**{spread_label}**  \n{spread_value:.{decimal_places}f}  \n\n"
        f"**{n_label}**  \n{n_value}"
    )
    st.markdown(_oos_oot_status_row("OOS (spesifikasyon disi)", n_oos, "#9c36b5", "#f6ecfb"), unsafe_allow_html=True)
    st.markdown(_oos_oot_status_row("OOT (kontrol disi)", n_oot, "#e03131", "#fff0f0"), unsafe_allow_html=True)


def render_capability_histogram(values: list[float], lsl: float, usl: float,
                                 one_sided: bool, dark: bool, unit: str,
                                 accent: str = "steelblue"):
    """Mevcut olcumlerden histogram + normal dagilim egrisi (scipy.stats.norm),
    LSL/USL dikey cizgileri ve (iki tarafliysa) Target (LSL/USL ortalamasi)
    cizgisi ile bir 'surec yeterlilik' gorseli olusturur. Figur objesini
    dondurur - cagiran taraf st.pyplot + PNG export + plt.close yapar.
    accent: Ince ayar 6 - histogram cubuklari, arayuzdeki "Vurgu rengi" ile
    tutarli olsun diye sabit "steelblue" yerine cagiran tarafin gecirdigi
    renk kullanilir (varsayilan "steelblue" - fonksiyon bagimsiz/testte
    accent verilmeden de calisabilsin diye)."""
    values_arr = np.array(values, dtype=float)
    mu = float(values_arr.mean())
    sigma = float(values_arr.std(ddof=1)) if len(values_arr) > 1 else 0.0

    fig, ax = plt.subplots(figsize=(8, 3.5), constrained_layout=True)

    bins = min(15, max(5, len(values_arr) // 2))
    ax.hist(
        values_arr, bins=bins, density=True, color=accent, alpha=0.6,
        edgecolor="white", label="Olcum dagilimi",
    )

    data_min, data_max = float(values_arr.min()), float(values_arr.max())
    lower_bound = data_min if one_sided else min(data_min, lsl)
    upper_bound = max(data_max, usl)
    span = upper_bound - lower_bound
    pad = span * 0.15 if span > 0 else (sigma * 3 if sigma > 0 else 1.0)
    x_curve = np.linspace(lower_bound - pad, upper_bound + pad, 200)

    if sigma > 0:
        y_curve = stats.norm.pdf(x_curve, mu, sigma)
        ax.plot(x_curve, y_curve, color="darkorange", linewidth=2, label="Normal dagilim")

    ax.axvline(usl, color="red", linestyle="--", linewidth=1.5, label="USL")
    if not one_sided:
        ax.axvline(lsl, color="red", linestyle="--", linewidth=1.5, label="LSL")
        target = (lsl + usl) / 2
        ax.axvline(target, color="seagreen", linestyle=":", linewidth=1.5, label="Target")

    ax.set_xlabel(unit)
    ax.set_ylabel("Yogunluk")
    ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1), fontsize=8)
    style_chart(fig, ax, dark)
    return fig


def render_normality_check(values: list[float]) -> None:
    """Shapiro-Wilk normallik testi sonucunu histogramin ALTINDA gosterir -
    METHODOLOGY.md v1.2 'Normality / dagilim kontrolu' maddesi: seffaflik
    amacli bir uyari/bilgi kutusu, otomatik bir 'normal degil -> SPC
    yapilamaz' KAPISI DEGIL - Cpk/Ppk HER ZAMAN hesaplanip gosterilmeye
    devam eder, bu sadece o hesaplarin dayandigi varsayimi acikca belirtir.

    len(values) < MIN_SAMPLE_SIZE_FOR_SHAPIRO (scipy'nin kendi kisiti,
    3) ise testi hic CALISTIRMAZ - o kadar az veriyle normallik testi
    zaten guvenilir/anlamli degildir, sessizce atlanir (hata gosterilmez)."""
    if len(values) < MIN_SAMPLE_SIZE_FOR_SHAPIRO:
        return
    w, p = check_normality(values)
    message, level = interpret_normality(w, p)
    if level == "info":
        st.info(message)
    else:
        st.warning(message)


def annotate_hline(ax, x_pos: float, y_value: float, text: str, color: str) -> None:
    """Bir yatay kontrol/spesifikasyon cizgisinin sag ucuna kucuk bir deger
    etiketi ekler (orn. 'UCL=7.098'), grafigi okumayi kolaylastirir."""
    ax.annotate(
        text, xy=(x_pos, y_value), xytext=(3, 0), textcoords="offset points",
        color=color, fontsize=7, va="center", ha="left", annotation_clip=False,
    )


OOT_LINE_COLOR = "#e03131"  # KPI panelindeki "OOT (Kontrol Disi)" ile ayni kirmizi
# ADIM v1.2 Madde 2 (OOS/OOT ayrimi) ONCESI bu renk/fonksiyon "OOS_LINE_COLOR"/
# "highlight_oos_segments" adiyla anilirdi - ama isaretledigi sey aslinda HEP
# UCL/LCL (kontrol limiti) asimiydi, spesifikasyon (LSL/USL) asimi DEGIL. Bu,
# tam da OOS/OOT ayriminin duzeltmek istedigi terminoloji hatasiydi - bkz.
# METHODOLOGY.md v1.2 "OOS/OOT ayrimi" maddesi. Asagidaki OOS_MARKER_COLOR,
# GERCEK spesifikasyon (LSL/USL) asimi icin AYRI ve BILEREK farkli bir renk.
OOS_MARKER_COLOR = "#9c36b5"  # LSL/USL disi (gercek OOS) icin mor - OOT'un kirmizisindan bilerek farkli


def highlight_oot_segments(ax, x: list[float], y: list[float], oot_indices) -> None:
    """OOT (Out of Trend - UCL/LCL asimi VEYA Nelson oruntu sinyali) olan bir
    noktaya BAGLANAN cizgi segmentini kirmizi ile ustten yeniden cizer -
    boylece sadece nokta degil, sinira/oruntuye GECISI gosteren segment de
    gorsel olarak isaretlenir. x/y, ana seriyle (indices/values, indices/
    means, vb.) AYNI sirada ve 0-tabanli olmali; oot_indices, out_of_control_
    i/x/r/mr VE Nelson kurallarinin birlesimiyle (0-tabanli liste pozisyonu)
    ayni formatta beklenir."""
    oot_set = set(oot_indices)
    for i in range(len(x) - 1):
        if i in oot_set or (i + 1) in oot_set:
            ax.plot([x[i], x[i + 1]], [y[i], y[i + 1]], color=OOT_LINE_COLOR, linewidth=1.5, zorder=4)


def shade_lcl_zero_zone(ax, lcl: float) -> None:
    """R/MR (range-tabanli) grafiklerde LCL=0 oldugunda (kucuk n icin D3=0
    - Montgomery SPC sabit tablosu - pratikte COK yaygin), alt bolgeye hafif
    kirmizi bir 'bu sinirin altina inilemez/inilirse anlamli degildir' golge
    bandı ekler. Sadece gorsel: LCL zaten dashed cizgi + etiketle cizili,
    bu golge onu vurgulayan ek bir ipucu. lcl, compute_xbar_r_limits/
    compute_imr_limits'ten gelen GERCEK LCL degeridir (ax.get_ylim()'den
    TAHMIN EDILMEZ - Range degerleri LCL=0 olmasa bile 0'a yakin
    baslayabilir, bu yanlis pozitife yol acardi). axhline/plot
    cagrilarindan SONRA, style_chart'tan ONCE cagrilmalidir."""
    if abs(lcl) > 1e-9:
        return  # LCL=0 degil - golge gereksiz
    ymin, ymax = ax.get_ylim()
    band_bottom = ymin - 0.12 * (ymax - ymin if ymax > ymin else 1.0)
    ax.set_ylim(band_bottom, ymax)
    ax.axhspan(band_bottom, 0, color=OOT_LINE_COLOR, alpha=0.08, zorder=0)


def draw_zone_shading(ax, center: float, sigma: float, dark: bool) -> None:
    """Nelson kurallarinin dayandigi Zone C/B/A bolgelerini (merkez cizgiden
    +-1/+-2/+-3 sigma) grafikte hafif renkli yatay bantlar olarak
    gorsellestirir - boylece kullanici bir Nelson sinyalinin HANGI bolgeye
    dayandigini (2/3-2sigma kurali Zone A'yi, 4/5-1sigma kurali Zone B/A'yi,
    9-ayni-taraf kurali sadece merkezin hangi tarafinda oldugunu kullanir)
    grafikte gorebilir - salt sayisal bir OOT etiketinden farkli olarak
    GORSEL bir sezgi saglar.

    Zone C (merkeze en yakin) EN SOLUK, Zone A (kontrol limitine en yakin)
    EN BELIRGIN bant olacak sekilde kademeli artan opaklik kullanilir - her
    bant KENDI araligini (onceki sinirdan bir sonraki sinira) kapladigi
    icin bantlar UST USTE binmez, her birinin opakligi dogrudan o bandin
    gorunurlugunu belirler.

    sigma<=0 (varyasyon yok) durumunda bolgeler ANLAMSIZDIR - hicbir sey
    cizilmez. axhline/plot cagrilarindan SONRA, style_chart'tan ONCE
    cagrilmalidir (shade_lcl_zero_zone ile ayni sira kurali) - ZORDER=0 ile
    veri cizgisinin/UCL-LCL/merkez cizgisinin ARKASINDA kalir."""
    if sigma <= 0:
        return
    band_color = "#ffffff" if dark else "#000000"
    zone_alphas = [(1, 0.05), (2, 0.09), (3, 0.13)]  # (sigma kati, opaklik) - Zone C, B, A
    prev_multiplier = 0.0
    for multiplier, alpha in zone_alphas:
        ax.axhspan(
            center + prev_multiplier * sigma, center + multiplier * sigma,
            color=band_color, alpha=alpha, zorder=0, linewidth=0,
        )
        ax.axhspan(
            center - multiplier * sigma, center - prev_multiplier * sigma,
            color=band_color, alpha=alpha, zorder=0, linewidth=0,
        )
        prev_multiplier = multiplier


def compute_oos_flags(
    raw_value_groups: list[list[float]], lsl: float, usl: float, one_sided: bool
) -> tuple[set[int], int]:
    """OOS (Out of Specification): bir HAM olcumun LSL/USL DISINA cikmasi -
    UCL/LCL (kontrol limiti) ile HICBIR ilgisi yoktur, tamamen spesifikasyona
    gore degerlendirilir. raw_value_groups, I-MR'de her biri TEK elemanli
    ([[v1], [v2], ...] - grup indeksi = olcum indeksi), X-bar/R'de ise bir alt
    grubun TUM ham olculerini (birden fazla elemanli) tasir.

    Doner: (oos_group_indices, oos_raw_count) - ilki grafikte/UI'da HANGI
    grubun (X-bar/R'de alt grup, I-MR'de olcumun kendisi) en az bir OOS ham
    olcum icerdigini isaretlemek icin (0-tabanli, means/values ile AYNI
    indeks uzayinda); ikincisi Veri Ozeti sayacinda gosterilen GERCEK ham
    OOS olcum sayisidir - bir alt grup icinde BIRDEN FAZLA OOS olcum
    olabilecegi icin grup sayisiyla KARISTIRILMAMALIDIR."""
    oos_group_indices: set[int] = set()
    oos_raw_count = 0
    for g, group in enumerate(raw_value_groups):
        group_has_oos = False
        for v in group:
            if v > usl or (not one_sided and v < lsl):
                oos_raw_count += 1
                group_has_oos = True
        if group_has_oos:
            oos_group_indices.add(g)
    return oos_group_indices, oos_raw_count


def compute_nelson_oot_indices(series: list[float], center: float, sigma: float) -> set[int]:
    """OOT (Out of Trend) - oruntu/sinyal tabanli 3 Nelson kuralinin (2/3
    2-sigma, 4/5 1-sigma, 9 ayni-taraf) BIRLESIMI. Cagiran taraf bunu HER
    ZAMAN mevcut UCL/LCL asim listesiyle (out_of_control_x/i) BIRLESTIRIR -
    OOT'un tam tanimi 'kontrol limiti asimi VEYA Nelson sinyali'dir, bu
    fonksiyon sadece Nelson kismini uretir."""
    return (
        check_rule_2of3_beyond_2sigma(series, center, sigma)
        | check_rule_4of5_beyond_1sigma(series, center, sigma)
        | check_rule_9_same_side(series, center)
    )


def _cpu_cpl_for_display(center: float, sigma_hat: float, lsl: float, usl: float) -> tuple[float, float]:
    """Cpu/Cpl'yi 'Hesaplama adimlari' panelinde gostermek icin hesaplar.

    compute_cpk() (spc_core.py) ile AYNI sigma_hat=0 kuralini taraf taraf
    uygular: sigma_hat=0 ise Cpu, merkez USL'nin altinda/esitse +inf,
    ustundeyse -inf; Cpl de ayni sekilde LSL'ye gore. Bu, iki tarafin da
    kosulsuz +inf donduren eski davranisin aksine, compute_cpk()'in
    min(Cpu, Cpl) sonucuyla HER ZAMAN tutarlidir (bkz. tests/test_cpk_edge_cases.py
    - onceki halde merkez spesifikasyon disindayken bile panel Cpu=Cpl=inf
    gosterebiliyordu, KPI kartindaki gercek Cpk=-inf ile celisiyordu)."""
    if sigma_hat == 0:
        cpu = float("inf") if center <= usl else float("-inf")
        cpl = float("inf") if center >= lsl else float("-inf")
        return cpu, cpl
    cpu = (usl - center) / (3 * sigma_hat)
    cpl = (center - lsl) / (3 * sigma_hat)
    return cpu, cpl


def render_calculation_steps_xbar(x_double_bar: float, r_bar: float, limits,
                                   cpk: float, cpk_label: str, lsl: float, usl: float,
                                   one_sided: bool, unit: str, decimal_places: int) -> None:
    """X-bar/R icin formul-adim-adim dokumu: bu sonuca nasil ulasildigini
    rakamlarla gosterir (egitim amacli + guven verici seffaflik). decimal_places,
    olcumun laboratuvar hassasiyetiyle tutarli basamak sayisi icindir - Cpu/Cpl/Cpk
    (format_cpk ile ayri formatlanir) buna dahil degildir, cunku onlar boyutsuz
    bir oran, olcum biriminde bir deger degildir."""
    d = decimal_places
    sigma_hat = r_bar / limits.d2 if limits.d2 else 0.0
    lines = [
        f"x̄̄ = alt grup ortalamalarinin ortalamasi = **{x_double_bar:.{d}f} {unit}**",
        f"R̄ = alt grup range'lerinin ortalamasi = **{r_bar:.{d}f} {unit}**",
        f"A2 (n={subgroup_n}) = {limits.a2}, D3 = {limits.d3}, D4 = {limits.d4}, d2 = {limits.d2}  *(Montgomery SPC sabit tablosu)*",
        "",
        f"UCL = x̄̄ + A2·R̄ = {x_double_bar:.{d}f} + {limits.a2}×{r_bar:.{d}f} = **{limits.ucl_x:.{d}f}**",
        f"LCL = x̄̄ - A2·R̄ = {x_double_bar:.{d}f} - {limits.a2}×{r_bar:.{d}f} = **{limits.lcl_x:.{d}f}**",
        "",
        f"σ̂ = R̄ / d2 = {r_bar:.{d}f} / {limits.d2} = **{sigma_hat:.{d}f}**",
    ]
    if one_sided:
        lines.append(f"{cpk_label} = (USL - x̄̄) / (3σ̂) = ({usl:.{d}f} - {x_double_bar:.{d}f}) / (3×{sigma_hat:.{d}f}) = **{format_cpk(cpk)}**")
    else:
        cpu, cpl = _cpu_cpl_for_display(x_double_bar, sigma_hat, lsl, usl)
        lines.append(f"Cpu = (USL - x̄̄) / (3σ̂) = ({usl:.{d}f} - {x_double_bar:.{d}f}) / (3×{sigma_hat:.{d}f}) = {format_cpk(cpu)}")
        lines.append(f"Cpl = (x̄̄ - LSL) / (3σ̂) = ({x_double_bar:.{d}f} - {lsl:.{d}f}) / (3×{sigma_hat:.{d}f}) = {format_cpk(cpl)}")
        lines.append(f"{cpk_label} = min(Cpu, Cpl) = **{format_cpk(cpk)}**")
    st.markdown("  \n".join(lines))


def render_calculation_steps_imr(x_bar: float, mr_bar: float, limits,
                                  cpk: float, cpk_label: str, lsl: float, usl: float,
                                  one_sided: bool, unit: str, decimal_places: int) -> None:
    """I-MR icin formul-adim-adim dokumu - X-bar/R'ye benzer ama I-MR'ye ozgu
    sabitlerle (2.66, D4=3.267, d2=1.128, n=2)."""
    d = decimal_places
    sigma_hat = mr_bar / MR_CHART_D2 if MR_CHART_D2 else 0.0
    lines = [
        f"x̄ = tum olcumlerin ortalamasi = **{x_bar:.{d}f} {unit}**",
        f"MR̄ = ardisik olcumler arasi ortalama fark = **{mr_bar:.{d}f} {unit}**",
        f"I chart sabiti = {I_CHART_CONSTANT}, MR chart D4 = {MR_CHART_D4}, d2 = {MR_CHART_D2}  *(n=2, Montgomery SPC sabit tablosu)*",
        "",
        f"UCL = x̄ + 2.66×MR̄ = {x_bar:.{d}f} + {I_CHART_CONSTANT}×{mr_bar:.{d}f} = **{limits.ucl_i:.{d}f}**",
        f"LCL = x̄ - 2.66×MR̄ = {x_bar:.{d}f} - {I_CHART_CONSTANT}×{mr_bar:.{d}f} = **{limits.lcl_i:.{d}f}**",
        "",
        f"σ̂ = MR̄ / d2 = {mr_bar:.{d}f} / {MR_CHART_D2} = **{sigma_hat:.{d}f}**",
    ]
    if one_sided:
        lines.append(f"{cpk_label} = (USL - x̄) / (3σ̂) = ({usl:.{d}f} - {x_bar:.{d}f}) / (3×{sigma_hat:.{d}f}) = **{format_cpk(cpk)}**")
    else:
        cpu, cpl = _cpu_cpl_for_display(x_bar, sigma_hat, lsl, usl)
        lines.append(f"Cpu = (USL - x̄) / (3σ̂) = ({usl:.{d}f} - {x_bar:.{d}f}) / (3×{sigma_hat:.{d}f}) = {format_cpk(cpu)}")
        lines.append(f"Cpl = (x̄ - LSL) / (3σ̂) = ({x_bar:.{d}f} - {lsl:.{d}f}) / (3×{sigma_hat:.{d}f}) = {format_cpk(cpl)}")
        lines.append(f"{cpk_label} = min(Cpu, Cpl) = **{format_cpk(cpk)}**")
    st.markdown("  \n".join(lines))


def style_chart(fig, ax, dark: bool) -> None:
    """Grafigi secilen acik/koyu temaya uyarlar (arka plan, yazi, izgara, legend renkleri)."""
    bg = "#0e1117" if dark else "#ffffff"
    fg = "#fafafa" if dark else "#31333f"
    grid = "#333c4a" if dark else "#d3d3d3"

    fig.patch.set_facecolor(bg)
    ax.set_facecolor(bg)
    ax.tick_params(colors=fg)
    ax.xaxis.label.set_color(fg)
    ax.yaxis.label.set_color(fg)
    ax.title.set_color(fg)
    for spine in ax.spines.values():
        spine.set_color(fg)
    ax.grid(True, color=grid, alpha=0.3)

    legend = ax.get_legend()
    if legend is not None:
        legend.get_frame().set_facecolor(bg)
        legend.get_frame().set_edgecolor(fg)
        for text in legend.get_texts():
            text.set_color(fg)


st.title("\U0001F4CA SPC FoodLab")
st.caption("Gida uretiminde pH/Brix/Aw/Viskozite olcumlerinden istatistiksel proses kontrolu (SPC)")

chart_tab_label = "\U0001F4C8 I-MR Chart & Cpk" if is_individual else "\U0001F4C8 X-bar/R Chart & Cpk"
tab_data, tab_chart, tab_calc, tab_about = st.tabs([
    "\U0001F4DD Veri Girisi", chart_tab_label,
    "\U0001F9EE Hizli Hesaplayicilar", "ℹ️ Hakkinda",
])

# NOT: SEKME 1 (tab_data) kodu bilerek SEKME 2'den (tab_chart) ONCE yaziliyor.
# Sekme gecisi Streamlit'te bir rerun TETIKLEMEZ (sadece client-side gorunurluk
# degisir) - yani tab_chart, tab_data'daki bir mutasyonla (ornegin demo veri
# yukleme) AYNI script run'inda calisir. tab_chart, tab_data'dan ONCE calissaydi
# (daha once denenmis bir yaklasim), bu mutasyonlardan hemen sonra sekme
# degistirildiginde tab_chart hala ESKI veriyi kullanarak render edilmis
# DOM'u gostermeye devam ederdi (bir sonraki gercek rerun'a kadar) - bu da
# "demo veri yukledim ama grafik hala 'yetersiz veri' diyor" seklinde gozlemlenen
# bir hataya yol acmisti. Dogru sira budur; lsl_input/usl_input widget'larinin
# ara run'larda (orn. onay akislarindaki rerun'lar) render edilmeyip Streamlit
# tarafindan temizlenmesi ihtimaline karsi asagida setdefault() kullaniliyor -
# bu, sirlamaya bagli olmadan 0.0'a dusmeyi onluyor.

# ---------------------------------------------------------------------------
# SEKME 1: Veri Girisi / Goruntuleme
# ---------------------------------------------------------------------------
with tab_data:
    with st.container(border=True, key="card-02"):
        if is_individual:
            st.subheader("Yeni olcum ekle")
            st.write(
                f"I-MR chart icin alt grup/vardiya kavrami yok - her satir tek bir {unit} "
                f"olcumudur. Olcum SIRASI onemlidir (ardisik olcumler arasindaki fark - "
                f"moving range - hesaba katilir). (Parametre: {st.session_state.active_parameter})"
            )
        else:
            st.subheader("Yeni alt grup ekle")
            st.write(f"Her alt grup icin {subgroup_n} {unit} olcumu girilir. (Parametre: {st.session_state.active_parameter})")

        with st.form("subgroup_form", clear_on_submit=True):
            default_measurement = param_config["default_measurement"]
            # Canli girdi dogrulama (v1.2 Madde 8): number_input'un min/max'i
            # sadece FIZIKSEL siniri (orn. pH 0-14) uygular - urunun kendi
            # spesifikasyonuna (orn. secili urun icin LSL=6.8/USL=7.2) gore
            # olagan disi bir deger (orn. yanlislikla 70.1 yazmak) BUNU
            # yakalayamaz. st.form ICINDEKI widget'lar TUS BASINA rerun
            # TETIKLEMEDIGI icin (formun butun amaci budur) gercek anlamda
            # "yazarken" canli bir uyari gosterilemez - bunun yerine (1)
            # mevcut spesifikasyon araligi burada bir REFERANS olarak
            # gosterilir, (2) kaydettikten SONRA (asagida) deger(ler)
            # bu araligin disindaysa engelleyici olmayan bir uyari cikar.
            _hint_lsl, _hint_usl, _hint_one_sided = resolve_current_spec_hint(param_config)
            if is_spec_valid(_hint_one_sided, _hint_lsl, _hint_usl):
                _range_text = f"USL={_hint_usl:g}" if _hint_one_sided else f"{_hint_lsl:g}–{_hint_usl:g}"
                st.caption(
                    f"\U00002139️ Mevcut spesifikasyon araligi: {_range_text} {unit} - "
                    "bu araligin disindaki degerler yine de kaydedilir, sadece uyari gosterilir."
                )
            if is_individual and is_microbio:
                # Mikrobiyoloji: ham KOB/g + "LOD altinda" checkbox + LOD alani.
                # Checkbox isaretliyken ham input DEVRE DISI kalir (deger LOD/2
                # ile otomatik ikame edilir, kullanici bir sayi girmek zorunda
                # DEGILDIR) - substitute_below_lod/to_log10 mantigi burada
                # YAZILMAZ, kaydederken build_subgroup_entry() cagrilir (bkz.
                # asagidaki submitted bloğu).
                below_lod = st.checkbox(
                    "Bu deger LOD altinda", key=f"below_lod_{st.session_state.active_parameter}",
                    help="Isaretlenirse ham deger yerine LOD/2 (asagidaki LOD'a gore) kullanilir.",
                )
                mcol1, mcol2 = st.columns(2)
                with mcol1:
                    raw_val = st.number_input(
                        f"Olcum ({unit})", min_value=param_config["min_value"],
                        max_value=param_config["max_value"],
                        value=default_measurement, step=1.0, format="%.0f",
                        key=f"m_0_{st.session_state.active_parameter}",
                        disabled=below_lod,
                    )
                with mcol2:
                    lod_val = st.number_input(
                        f"LOD ({unit})", min_value=0.01,
                        value=param_config.get("default_lod", 10.0), step=1.0, format="%.2f",
                        key=f"lod_{st.session_state.active_parameter}",
                        help="Tespit limiti - LOD altinda isaretlenirse LOD/2 ikame edilir.",
                    )
                measurements = None  # asagida submitted bloğunda build_subgroup_entry ile olusturulur
                shift = "-"
            elif is_individual:
                # key'e parametre adi dahil edildi: Streamlit, ayni key'e sahip bir
                # number_input'un onceki gosterilen degerini frontend'de tutar - session_state
                # taraftan silinse bile "value=" ile verilen yeni varsayilani yoksayip eski
                # degeri gostermeye devam eder. Parametre degisince key de degisince widget
                # gercekten yeniden olusturulur ve dogru varsayilanla baslar.
                val = st.number_input(
                    f"Olcum ({unit})", min_value=param_config["min_value"],
                    max_value=param_config["max_value"],
                    value=default_measurement, step=1.0, format="%.1f",
                    key=f"m_0_{st.session_state.active_parameter}",
                )
                measurements = [val]
                shift = "-"
            else:
                shift = st.selectbox(
                    "Vardiya", SHIFT_OPTIONS,
                    help=(
                        "Bu alt grubun hangi vardiyada olculdugunu etiketler - "
                        "hesaplamayi (UCL/LCL/Cpk) ETKILEMEZ, sadece 'X-bar/R "
                        "Chart & Cpk' sekmesindeki 'Vardiya Karsilastirmasi' "
                        "tablosunda vardiyalara gore gruplama yapabilmek icin "
                        "kaydedilir (en az 2 farkli vardiyada veri olmasi gerekir)."
                    ),
                )
                cols = st.columns(subgroup_n)
                measurements = []
                for i, col in enumerate(cols):
                    with col:
                        val = st.number_input(
                            f"Olcum {i + 1} ({unit})", min_value=param_config["min_value"],
                            max_value=param_config["max_value"],
                            value=default_measurement, step=0.01, format="%.2f",
                            key=f"m_{i}_{st.session_state.active_parameter}",
                        )
                        measurements.append(val)
            submitted = st.form_submit_button("Olcumu kaydet" if is_individual else "Alt grubu kaydet")
            if submitted and is_individual and is_microbio:
                try:
                    entry = build_subgroup_entry(
                        raw=None if below_lod else raw_val, is_below_lod=below_lod, lod=lod_val,
                    )
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.session_state.subgroups.append({
                        "shift": shift, "values": [entry["log_value"]],
                        "raw": entry["raw"], "is_below_lod": entry["is_below_lod"], "lod": entry["lod"],
                    })
                    st.success("Olcum eklendi.")
                    if not below_lod:
                        plausibility_warnings = measurement_plausibility_warnings(
                            [("Olcum", raw_val)], _hint_lsl, _hint_usl, _hint_one_sided,
                        )
                        if plausibility_warnings:
                            st.warning(
                                "Girilen deger mevcut spesifikasyon araliginin disinda "
                                "gorunuyor - KAYDEDILDI, yazim hatasi olup olmadigini kontrol edin:  \n"
                                + "  \n".join(f"- {w}" for w in plausibility_warnings)
                            )
            elif submitted:
                st.session_state.subgroups.append({"shift": shift, "values": measurements})
                st.success("Olcum eklendi." if is_individual else "Alt grup eklendi.")
                labeled_values = (
                    [("Olcum", measurements[0])] if is_individual
                    else [(f"Olcum {i + 1}", v) for i, v in enumerate(measurements)]
                )
                plausibility_warnings = measurement_plausibility_warnings(
                    labeled_values, _hint_lsl, _hint_usl, _hint_one_sided
                )
                if plausibility_warnings:
                    st.warning(
                        "Girilen deger(ler) mevcut spesifikasyon araliginin disinda "
                        "gorunuyor - KAYDEDILDI, yazim hatasi olup olmadigini kontrol edin:  \n"
                        + "  \n".join(f"- {w}" for w in plausibility_warnings)
                    )

        demo_scenario_options = ["Genel (varsayilan)"] + [
            p for p in param_config["products"] if p != "Ozel/Manuel gir"
        ]
        demo_scenario = st.selectbox(
            "Demo senaryosu", demo_scenario_options,
            key=f"demo_scenario_{st.session_state.active_parameter}",
            help=(
                "'Genel (varsayilan)' parametrenin standart demo verisini uretir. "
                "Bir urun secersen, demo veri o urunun LSL/USL araligina gore "
                "ortalanmis olarak uretilir (orn. 'Bal' secilirse nem verisi "
                "Bal'in nem spesifikasyonu civarinda olusturulur)."
            ),
        )

        # v1.2 Madde 12: Demo senaryo galerisi - "Demo senaryosu" (yukarida,
        # HANGI URUNE gore ortalanacagini secer) ile BAGIMSIZ bir eksen: bu
        # secim surecin NASIL DAVRANDIGINI (iyi/kayan/degisken/trend) belirler.
        # Ikisi carpilarak (urun x davranis) kullanilabilir - orn. "Bal" +
        # "Kayan ortalama" -> Bal'in spesifikasyonu civarinda kalici kayan veri.
        demo_pattern_labels = {
            "Ani sicrama (tek nokta)": "point_shift",
            "Iyi surec (kontrol altinda)": "none",
            "Kayan ortalama (kalici kayma)": "persistent_shift",
            "Dusuk Cpk (yuksek degiskenlik)": "high_variation",
            "Trend (dogrusal kayma)": "trend",
        }
        demo_pattern_choice = st.selectbox(
            "Demo davranis deseni", list(demo_pattern_labels.keys()),
            key=f"demo_pattern_{st.session_state.active_parameter}",
            help=(
                "Surecin demo verisinde NASIL davranacagini secer - Nelson "
                "kurallarini/dusuk Cpk'yi/trendi gormek icin farkli desenler "
                "dener. 'Ani sicrama' onceki surumlerin varsayilan demosudur."
            ),
        )
        demo_pattern = demo_pattern_labels[demo_pattern_choice]

        if is_microbio:
            # Ayri bir "Normal SPC Demo / Microbiology Demo" secici EKLENMEDI -
            # is_microbio zaten parametre secimiyle otomatik belirlendigi icin
            # (bu parametre TPC/TMAB ise demo HER ZAMAN log-normal uretilir,
            # baska turlusu anlamsiz olurdu) boyle bir secici sadece TEK gecerli
            # cevabi olan bir soru sorar - kafa karistirir. Bunun yerine burada
            # NEDEN log-normal uretildigi aciklanir (bkz. asagidaki demo yukleme
            # kodu: generate_demo_individual log10 uzayinda cagrilir, sonra
            # 10**log_deger ile ham KOB/g'ye cevrilip build_subgroup_entry()'den
            # gecirilir).
            st.caption(
                "\U0001F9EA Bu parametre icin demo veri **log-normal dagilimdan** "
                "uretilir (once log10 olceginde normal dagilim uretilir, sonra ham "
                "KOB/g'ye cevrilir) - mikrobiyal sayimlarin gercek dagilimini "
                "yansitir, bu yuzden neden log10 donusumu kullanildigini gorsel "
                "olarak da gosterir."
            )

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("\U0001F9EA Demo veri yukle (24 olcum)" if is_individual else "\U0001F9EA Demo veri yukle (24 alt grup)", type="primary"):
                scenario_product = None if demo_scenario == "Genel (varsayilan)" else demo_scenario
                demo_mean, demo_spread, demo_shift_amount = demo_scenario_targets(param_config, scenario_product)
                # "point_shift" (mevcut varsayilan) TEK bir noktayi carpici
                # sekilde disari cikarmak icin buyuk bir shift_amount kullanir
                # (orn. pH icin 0.35 - 3sigma'nin cok uzerinde). "persistent_shift"/
                # "trend" ise KALICI bir kayma oldugu icin AYNI buyuklukte
                # kullanilirsa TUM noktalar asiri sekilde disari cikar (manuel
                # QA'da once denendi: 24/24 nokta hem UCL/LCL hem Nelson ile
                # isaretleniyordu, Nelson Test 2'nin (9 ardisik) inceligi
                # kayboluyordu - amac SADECE limit asimini degil, "henuz limit
                # asmayan ama oruntusel sapma gosteren" durumu da gosterebilmek).
                # Asagidaki carpanlar/index'ler seed=42 ile deneysel olarak
                # ayarlandi - cogunlukla Nelson-only bir sinyal, minimal/hic
                # UCL asimi hedeflenir (bkz. tests/test_demo_data.py, bu
                # DAVRANIS testlerinde degil sadece yon/genislik kontrol
                # edilir - kesin sayilar seed'e bagli oldugu icin BURADA
                # sadece manuel QA ile dogrulanmistir).
                demo_kwargs = {}
                if demo_pattern == "persistent_shift":
                    demo_pattern_shift = demo_spread * (1.8 if is_individual else 0.5)
                    demo_kwargs["shift_index" if is_individual else "shift_subgroup_index"] = 15 if is_individual else 12
                elif demo_pattern == "trend":
                    demo_pattern_shift = demo_spread * (3.0 if is_individual else 1.0)
                else:
                    demo_pattern_shift = demo_shift_amount
                if is_individual and is_microbio:
                    # demo_mean HAM KOB/g'dir (digerleriyle ayni kaynak: demo_
                    # scenario_targets) - generate_demo_individual'a vermeden
                    # ONCE log10'a cevrilir; demo_spread (RAW olcekte, urun
                    # araligina bagli) burada KULLANILMAZ, sabit log10_sigma
                    # (PARAMETER_CONFIG["demo_target_sigma"]) tercih edilir
                    # (bkz. constants.py notu). Uretilen log10 seri, HER
                    # DEGER icin build_subgroup_entry() uzerinden gecirilir
                    # (raw=10**log_deger, is_below_lod=False) - ayri bir mock
                    # ikame/log10 mantigi YAZILMAZ.
                    log_mean = to_log10(demo_mean)
                    log_sigma = param_config["demo_target_sigma"]
                    demo_log_values = generate_demo_individual(
                        target_mean=log_mean,
                        target_sigma=log_sigma,
                        shift_amount=demo_pattern_shift / demo_spread * log_sigma if demo_spread else None,
                        pattern=demo_pattern,
                        **demo_kwargs,
                    )
                    new_subgroups = []
                    for log_v in demo_log_values:
                        raw_cfu = max(10 ** log_v, param_config["min_value"])
                        entry = build_subgroup_entry(raw=raw_cfu, is_below_lod=False, lod=param_config.get("default_lod"))
                        new_subgroups.append({
                            "shift": "-", "values": [entry["log_value"]],
                            "raw": entry["raw"], "is_below_lod": False, "lod": entry["lod"],
                        })
                    st.session_state.subgroups = new_subgroups
                elif is_individual:
                    demo_values = generate_demo_individual(
                        target_mean=demo_mean,
                        target_sigma=demo_spread,
                        shift_amount=demo_pattern_shift,
                        pattern=demo_pattern,
                        **demo_kwargs,
                    )
                    st.session_state.subgroups = [{"shift": "-", "values": [v]} for v in demo_values]
                else:
                    demo = generate_demo_subgroups(
                        subgroup_size=subgroup_n,
                        target_mean=demo_mean,
                        target_r_bar=demo_spread,
                        shift_amount=demo_pattern_shift,
                        pattern=demo_pattern,
                        clip_min=param_config["min_value"],
                        clip_max=param_config["max_value"],
                        **demo_kwargs,
                    )
                    st.session_state.subgroups = [
                        {"shift": SHIFT_OPTIONS[i % len(SHIFT_OPTIONS)], "values": vals}
                        for i, vals in enumerate(demo)
                    ]
                st.session_state.baseline = None
                st.session_state.confirm_clear = False
                # KRITIK: burada aciktan st.rerun() cagirmadan onceki halde,
                # bu mutasyon script'in bu run'inda GEC gerceklesiyordu -
                # sidebar (dosyanin EN USTUNDE, tab_data'dan ONCE calisir)
                # zaten ESKI (bos) subgroups ile render edilmis oluyordu.
                # Sekme degistirmek bunu DUZELTMIYOR (Streamlit'te sekme
                # gecisi bir rerun TETIKLEMEZ - bkz. asagidaki NOT), yani
                # sidebar durum noktasi kalici olarak "veri yok" gorunumunde
                # takili kalabiliyordu.
                #
                # _reset_parameter_radio bayragi (asagida, sidebar'dan ONCE
                # islenir) burada BILEREK yeniden kullanildi: bu rerun,
                # "parameter_radio" widget'i BU RUN'DA ZATEN (eski/gri durum
                # etiketiyle) render edildikten SONRA tetikleniyor -
                # format_func'un urettigi etiket metni (nokta rengi) rerun
                # oncesi/sonrasi FARKLI oldugu icin (gri->kirmizi/yesil),
                # React/BaseWeb bu ani ard-arda render'da secili radio'nun
                # checked gorunumunu kaybediyor (Playwright ile dogrulandi:
                # input.checked=false kaliyor). session_state.parameter_radio'yu
                # DOGRUDAN burada atamak DENENDI ama StreamlitAPIException
                # verdi ("... cannot be modified after the widget ... is
                # instantiated") - widget bu run'da zaten olusturuldu. Bayrak
                # deseni bu kisitlamayi dogru sekilde asiyor: gercek atama bir
                # SONRAKI run'da, widget olusturulmadan ONCE yapilir.
                st.session_state._reset_parameter_radio = True
                st.rerun()
        with col_b:
            if not st.session_state.confirm_clear:
                if st.button("\U0001F5D1️ Tum verileri temizle", type="secondary"):
                    st.session_state.confirm_clear = True
                    st.rerun()
            else:
                st.warning("Emin misiniz? Tum alt gruplar ve baseline silinecek, bu islem geri alinamaz.")
                cc1, cc2 = st.columns(2)
                with cc1:
                    if st.button("Evet, sil", type="primary", key="confirm_clear_yes"):
                        st.session_state.subgroups = []
                        st.session_state.baseline = None
                        st.session_state.confirm_clear = False
                        st.rerun()
                with cc2:
                    if st.button("Vazgec", key="confirm_clear_no"):
                        st.session_state.confirm_clear = False
                        st.rerun()

    st.write("")

    with st.container(border=True, key="card-03"):
        with st.expander("\U0001F4E4 CSV'den veri yukle", expanded=False):
            if is_microbio:
                expected_cols = "Sira, Raw (KOB/g), LOD altimi (istege bagli), LOD (istege bagli)"
            elif is_individual:
                expected_cols = "Sira, Olcum 1"
            else:
                expected_cols = f"Grup, Vardiya, Olcum 1..{subgroup_n}"
            st.caption(
                f"Uygulamanin kendi 'CSV olarak indir' formatiyla uyumlu olmalidir - "
                f"beklenen sutunlar: **{expected_cols}** (birim: {unit}). "
                "Yuklenen veri MEVCUT VERININ YERINI ALIR (baseline da sifirlanir)."
            )

            if is_microbio:
                template_cols = ["Sira", "Raw (KOB/g)", "LOD altimi", "LOD"]
            elif is_individual:
                template_cols = ["Sira", "Olcum 1"]
            else:
                template_cols = ["Grup", "Vardiya"] + [f"Olcum {i + 1}" for i in range(subgroup_n)]
            template_csv = (",".join(template_cols) + "\n").encode("utf-8")
            st.download_button(
                "\U0001F4C4 Bos sablon indir", template_csv,
                f"{st.session_state.active_parameter.lower()}_sablon.csv", "text/csv",
                key=f"csv_template_{st.session_state.active_parameter}",
            )

            uploaded_file = st.file_uploader(
                "CSV dosyasi sec", type="csv",
                key=f"csv_upload_{st.session_state.active_parameter}",
            )
            if uploaded_file is not None:
                try:
                    import_df = pd.read_csv(uploaded_file)
                except Exception as exc:
                    st.error(csv_io.friendly_csv_read_error(exc))
                    with st.expander("Teknik detay"):
                        st.code(f"{type(exc).__name__}: {exc}")
                    import_df = None

                if import_df is not None:
                    import_df, dropped_blank = csv_io.drop_blank_rows(import_df)
                    if dropped_blank:
                        st.info(f"{dropped_blank} tamamen bos satir bulundu ve atlandi.")

                    if len(import_df) == 0:
                        st.error("CSV'de veri satiri bulunamadi (sadece baslik satiri var gibi gorunuyor).")
                    else:
                        dup_count = csv_io.count_duplicate_rows(import_df)
                        if dup_count:
                            st.info(
                                f"{dup_count} yinelenen satir tespit edildi (tum sutunlarda ayni "
                                "deger) - veri oldugu gibi ice aktarildi; ardisik olcumlerin "
                                "birebir ayni cikmasi (orn. cok kararli bir surecte) gecerli bir "
                                "sonuc olabilecegi icin otomatik silinmedi."
                            )

                        new_subgroups, err = csv_io.parse_uploaded_dataframe(
                            import_df, is_individual, subgroup_n, SHIFT_OPTIONS, unit,
                            is_microbio=is_microbio, default_lod=param_config.get("default_lod"),
                        )
                        if err:
                            st.error(err)
                        else:
                            st.session_state.subgroups = new_subgroups
                            st.session_state.baseline = None
                            label = "olcum" if is_individual else "alt grup"
                            st.success(f"{len(new_subgroups)} {label} CSV'den yuklendi.")

        with st.expander("\U0001F4CB Excel/pano yapistir", expanded=False):
            paste_format_hint = (
                "her satirda tek bir deger"
                if is_individual
                else f"her satirda {subgroup_n} deger, istege bagli basinda bir vardiya adi"
            )
            st.caption(
                f"Excel'de bir hucre araligi secip kopyalayin (Ctrl+C), asagiya "
                f"yapistirin (Ctrl+V) - BASLIK SATIRI OLMAMALIDIR, dogrudan sayilar "
                f"({paste_format_hint}, birim: {unit}). CSV yuklemenin AKSINE mevcut "
                "veriyi SILMEZ - yapistirilan satirlar mevcut verinin SONUNA EKLENIR."
                + (
                    "  \nLOD altindaki bir olcum icin sayi yerine **'<10'** (LOD degeri, "
                    "orn. 10) veya **'<LOD'** yazin - otomatik olarak LOD/2 ile ikame edilir."
                    if is_microbio else ""
                )
            )
            paste_placeholder = (
                "7.01\n7.02\n6.99"
                if is_individual
                else "\t".join(["7.01"] * subgroup_n) + "\n" + "\t".join(["6.98"] * subgroup_n)
            )
            with st.form(f"paste_form_{st.session_state.active_parameter}", clear_on_submit=True):
                pasted_text = st.text_area(
                    "Yapistirilan veri", height=120, placeholder=paste_placeholder,
                    label_visibility="collapsed",
                )
                paste_submitted = st.form_submit_button("\U00002795 Yapistirilan veriyi ekle")

            if paste_submitted:
                if not pasted_text.strip():
                    st.error("Once Excel'den kopyaladiginiz veriyi yukaridaki alana yapistirin.")
                else:
                    new_rows, err = csv_io.parse_pasted_text(
                        pasted_text, is_individual, subgroup_n, SHIFT_OPTIONS, unit,
                        is_microbio=is_microbio, default_lod=param_config.get("default_lod"),
                    )
                    if err:
                        st.error(err)
                    else:
                        st.session_state.subgroups.extend(new_rows)
                        st.session_state.baseline = None
                        label = "olcum" if is_individual else "alt grup"
                        st.success(f"{len(new_rows)} {label} eklendi (baseline sifirlandi).")

    st.write("")

    with st.container(border=True, key="card-04"):
        st.subheader("Kayitli olculer" if is_individual else "Kayitli alt gruplar")

        if not st.session_state.subgroups:
            render_empty_state("\U0001F4CB", "Henuz veri yok. Yukaridan manuel ekleyin veya demo veri yukleyin.")
        else:
            if is_individual:
                _, _, summary_x_bar, summary_mr_bar = compute_individual_stats(st.session_state.subgroups)
                sm1, sm2 = st.columns(2)
                sm1.metric(f"Genel Ortalama (x̄, {unit})", f"{summary_x_bar:.{decimal_places}f}")
                sm2.metric(
                    f"Ortalama Moving Range (MR̄, {unit})",
                    f"{summary_mr_bar:.{decimal_places}f}" if summary_mr_bar is not None else "—",
                )
            else:
                _, _, summary_x_double_bar, summary_r_bar = compute_stats(st.session_state.subgroups)
                sm1, sm2 = st.columns(2)
                sm1.metric(f"Genel Ortalama (x̄̄, {unit})", f"{summary_x_double_bar:.{decimal_places}f}")
                sm2.metric(f"Ortalama Range (R̄, {unit})", f"{summary_r_bar:.{decimal_places}f}")

            st.divider()

            with st.expander(
                "\U0001F4CB Ham/log10 seffaflik tablosu - goruntule / duzenle" if is_microbio
                else "\U0001F4CB Ham verileri goruntule / duzenle", expanded=False,
            ):
                rows = csv_io.subgroups_to_records(st.session_state.subgroups, is_individual, is_microbio=is_microbio)
                df = pd.DataFrame(rows)
                index_col = "Sira" if is_individual else "Grup"
                if is_microbio:
                    # "Kullanilan (KOB/g)" ve "log10" TURETILMIS (LOD ikamesi +
                    # log10 donusumunun sonucu) - elle DUZENLENEMEZ, sadece
                    # seffaflik icin gosterilir. Duzenlenebilir tek alanlar
                    # Raw/LOD altimi/LOD'dir - kaydedince ayni build_subgroup_
                    # entry() zinciri (parse_uploaded_dataframe) yeniden calisir.
                    derived_cols = {"Kullanilan (KOB/g)", "log10"}
                    column_config = {
                        "Raw (KOB/g)": st.column_config.NumberColumn(format="%.0f"),
                        "LOD altimi": st.column_config.CheckboxColumn(),
                        "LOD": st.column_config.NumberColumn(format="%.2f"),
                        "Kullanilan (KOB/g)": st.column_config.NumberColumn(format="%.2f", disabled=True),
                        "log10": st.column_config.NumberColumn(format="%.3f", disabled=True),
                        index_col: st.column_config.NumberColumn(disabled=True),
                    }
                    st.caption(
                        "**Kullanilan (KOB/g)** ve **log10**, LOD ikamesi/log10 donusumunun "
                        "SONUCUDUR - dogrudan duzenlenemez; degistirmek icin Raw/LOD "
                        "altimi/LOD sutunlarini duzenleyip kaydedin."
                    )
                else:
                    # Sadece GORUNUMU laboratuvar hassasiyetine yuvarlar - alttaki veri
                    # (ve CSV export'u) kullanicinin girdigi tam degerleri korur.
                    numeric_cols = [c for c in df.columns if c not in ("Sira", "Grup", "Vardiya")]
                    derived_cols = {"Ortalama", "Range"} & set(df.columns)  # turetilmis, elle DUZENLENEMEZ
                    column_config = {
                        c: st.column_config.NumberColumn(
                            format=f"%.{decimal_places}f", disabled=(c in derived_cols)
                        )
                        for c in numeric_cols
                    }
                    column_config[index_col] = st.column_config.NumberColumn(disabled=True)
                    if not is_individual:
                        column_config["Vardiya"] = st.column_config.SelectboxColumn(
                            options=SHIFT_OPTIONS, required=True
                        )

                st.caption(
                    "Hucreleri duzenleyebilir, bir satiri SILEBILIR (satiri secip "
                    "klavyeden Delete) veya tablonun altindaki '+' ile YENI satir "
                    "ekleyebilirsiniz - degisiklikler asagidaki 'Degisiklikleri "
                    "kaydet' butonuna basana kadar UYGULANMAZ (baseline, "
                    "kaydedilince sifirlanir - veri degistigi icin eski limitler "
                    "artik gecerli degildir)."
                )
                edited_df = st.data_editor(
                    df, use_container_width=True, hide_index=True, num_rows="dynamic",
                    column_config=column_config,
                    key=f"data_editor_{st.session_state.active_parameter}",
                )

                ec1, ec2 = st.columns(2)
                with ec1:
                    if st.button("\U0001F4BE Degisiklikleri kaydet", type="primary", key="save_edited_data"):
                        # Turetilmis sutunlar (Ortalama/Range) parse_uploaded_
                        # dataframe tarafindan zaten yok sayilir, ama satir
                        # silme/ekleme sonrasi ESKI (guncel olmayan) degerler
                        # tasiyabilecekleri icin kafa karistirmasin diye
                        # onceden cikariliyor.
                        clean_df = edited_df.drop(columns=[c for c in derived_cols if c in edited_df.columns])
                        if len(clean_df) == 0:
                            st.error(
                                "En az bir satir kalmalidir - tumunu silmek icin "
                                "yukaridaki 'Tum verileri temizle' butonunu kullanin."
                            )
                        else:
                            new_subgroups, err = csv_io.parse_uploaded_dataframe(
                                clean_df, is_individual, subgroup_n, SHIFT_OPTIONS, unit,
                                is_microbio=is_microbio, default_lod=param_config.get("default_lod"),
                            )
                            if err:
                                st.error(err)
                            else:
                                st.session_state.subgroups = new_subgroups
                                st.session_state.baseline = None
                                st.success("Degisiklikler kaydedildi (baseline sifirlandi).")
                                st.rerun()
                with ec2:
                    csv = df.to_csv(index=False).encode("utf-8")
                    st.download_button(
                        "CSV olarak indir", csv,
                        f"{st.session_state.active_parameter.lower()}_olcumleri.csv", "text/csv",
                    )

# ---------------------------------------------------------------------------
# SEKME 2: X-bar/R Chart & Cpk
# ---------------------------------------------------------------------------
with tab_chart:
    if len(st.session_state.subgroups) < 2:
        render_empty_state("\U0001F4C8", "Grafik icin en az 2 alt grup gerekli. Once veri girisi sekmesinden veri ekleyin.")
    else:
        with st.container(border=True, key="card-05"):
            info_col, clear_col = st.columns([5, 1])
            with info_col:
                st.caption(
                    f"ℹ️ **{st.session_state.active_parameter}** — "
                    f"{get_parameter_info_text(st.session_state.active_parameter)}"
                )
            with clear_col:
                if st.button(
                    "\U0001F504 Analizi Temizle", key="clear_analysis_btn",
                    help="Baseline'i ve urun/limit secimini sifirlar; olculen veriler korunur.",
                ):
                    st.session_state.baseline = None
                    reset_parameter_scoped_state()
                    st.session_state.confirm_freeze = False
                    st.session_state.confirm_reset_baseline = False
                    st.success("Analiz sifirlandi (olculen veriler korundu).")
                    st.rerun()

        if st.session_state.active_parameter == "Kuru Madde":
            # v1.5 Faz 2: Kuru Madde + Nem capraz tutarlilik kontrolu -
            # BLOKLAMAYAN, bilgilendirici (bkz. METHODOLOGY.md v1.5 Faz 2 ve
            # result_helpers.build_dry_matter_moisture_consistency_note
            # docstring'i - neden GERCEK bir ikinci parametre yerine elle
            # girilen bir referans Nem % kullanildigini acikliyor).
            with st.expander("\U0001F50D Capraz kontrol: Kuru Madde + Nem"):
                _dm_values, _dm_mr, _dm_xbar, _ = compute_individual_stats(st.session_state.subgroups)
                _nem_ref = st.number_input(
                    "Referans Nem % (aynı numune icin, elle girilir)",
                    min_value=0.0, max_value=100.0, value=10.0, step=0.1,
                    key="kuru_madde_nem_check_input",
                )
                st.caption(build_dry_matter_moisture_consistency_note(_dm_xbar, _nem_ref))

        products = list(param_config["products"].keys())
        default_index = products.index("Ozel/Manuel gir")

        def _resolve_one_sided(product_name: str) -> bool:
            """Tek/iki tarafli Cpk secimi PARAMETRE degil URUN bazindadir:
            secilen urunun LSL'i None ise (orn. Nem/Rutubet'te 'Bal') o urun
            icin tek tarafli Cpu hesaplanir; 'Ozel/Manuel gir' secildiginde
            parametrenin kendi varsayilanina (PARAMETER_CONFIG['one_sided'])
            geri donulur."""
            product_range = param_config["products"].get(product_name)
            if product_range is None:
                return param_config.get("one_sided", False)
            range_lsl, _ = product_range
            return range_lsl is None

        # Selectbox olusturulmadan once mevcut secimi (varsa) tahmin ederek
        # basliktaki Cpk/Cpu etiketini dogru gostermeye calisiriz; selectbox
        # olusturulduktan sonra ayni deger zaten kesinlesmis olarak asagida
        # yeniden hesaplaniyor (bkz. "one_sided = _resolve_one_sided(...)").
        _guess_product = st.session_state.get("product_select", products[default_index])
        if _guess_product not in param_config["products"]:
            _guess_product = products[default_index]
        one_sided = _resolve_one_sided(_guess_product)
        cpk_label = "Cpu (tek tarafli)" if one_sided else "Cpk"

        with st.container(border=True, key="card-06"):
            st.subheader(f"Spesifikasyon limitleri ({unit}, {cpk_label} icin)")

            selected_product = st.selectbox(
                "Urun / Hammadde", products, index=default_index, key="product_select",
                help=(
                    "Secilen urune gore LSL/USL degerleri asagida otomatik "
                    "doldurulur (elle degistirilebilir). \U0001F33E ile "
                    "baslayan girdiler hammadde QC referanslaridir - bitmis "
                    "urun (TGK uyumlu) spesifikasyonlarindan ayri bir "
                    "kategoridir, listede en altta 'Ozel/Manuel gir' "
                    "oncesinde grupludur."
                ),
            )
            one_sided = _resolve_one_sided(selected_product)
            cpk_label = "Cpu (tek tarafli)" if one_sided else "Cpk"
            raw_name = raw_material_name(selected_product)
            if raw_name is None:
                st.caption(
                    f"\U0001F3F7️ Kaynak: **{PARAMETER_SOURCES.get(st.session_state.active_parameter, '-')}** "
                    f"— detay: [METHODOLOGY.md]({GITHUB_URL}/blob/main/METHODOLOGY.md)"
                )

            if (
                "prev_product" not in st.session_state
                or st.session_state.get("prev_parameter") != st.session_state.active_parameter
            ):
                st.session_state.prev_product = selected_product
                st.session_state.prev_parameter = st.session_state.active_parameter
            # setdefault: widget bir onceki run'da (subgroups gecici olarak <2
            # oldugunda vb.) render edilmeyip Streamlit tarafindan temizlenmis
            # olsa bile makul bir varsayilana geri doner (0.0'a degil).
            st.session_state.setdefault("lsl_input", param_config["default_lsl"])
            st.session_state.setdefault("usl_input", param_config["default_usl"])

            if selected_product != st.session_state.prev_product:
                product_range = param_config["products"][selected_product]
                if product_range is not None:
                    range_lsl, range_usl = product_range
                    if range_lsl is not None:
                        st.session_state.lsl_input = range_lsl
                    st.session_state.usl_input = range_usl
                st.session_state.prev_product = selected_product

            active_param = st.session_state.active_parameter
            if raw_name is not None:
                # Hammadde secildi: bitmis urun (TGK uyumlulugu iddiasi tasiyan)
                # per-parametre notlari yerine, ayri "Hammadde QC Referansi"
                # kategorisini acikca etiketleyen bir not gosterilir - bkz.
                # RAW_MATERIAL_QC_REFERENCE (constants.py) ve METHODOLOGY.md
                # "Hammadde Kutuphanesi Genislemesi".
                _spec = RAW_MATERIAL_QC_REFERENCE.get(raw_name, {}).get(active_param, {})
                _source = _spec.get("source")
                _verified = _spec.get("verified")
                _note = _spec.get("note")
                if _verified is True:
                    st.success(
                        f"\U0001F33E **Hammadde QC Referansi** (bitmis urun TGK "
                        f"uyumlulugu ile ILGILI DEGILDIR, ayri bir kategoridir). "
                        f"Kaynak: {_source}"
                    )
                elif _verified == "kismi":
                    st.warning(
                        f"\U0001F33E **Hammadde QC Referansi** (bitmis urun TGK "
                        f"uyumlulugu ile ILGILI DEGILDIR). Kaynak: {_source} — "
                        "arama motoru sonucuyla dogrulandi, tam metin taranmis "
                        "PDF oldugu icin dogrudan okunamadi; kritik kullanimdan "
                        "once tebligin orijinal metniyle capraz kontrol onerilir."
                    )
                else:
                    st.warning(
                        "\U0001F33E **Hammadde QC Referansi** — bu hammadde/parametre "
                        "kombinasyonu icin guvenilir bir kaynak (TGK tebligi, Codex/"
                        "JECFA monografi) DOGRULANAMADI. Rastgele/varsayilan bir "
                        "limit KONULMADI — LSL/USL alanlarini kendi spesifikasyonuna "
                        "gore elle gir."
                        + (f" (arastirma notu: {_source})" if _source else "")
                    )
                if _note:
                    st.caption(f"ℹ️ {_note}")
            elif active_param == "pH":
                st.caption(
                    "Bu degerler literatur/sektor pratiginden alinan gosterge "
                    "degerlerdir. Turk Gida Kodeksi cogu urunde sayisal bir pH "
                    "limiti belirlemez; bu tablo TGK uyumlulugu icin degil, kalite "
                    "kontrol referansi olarak kullanilir. LSL/USL degerlerini "
                    "kendi urun/spesifikasyonuna gore elle degistirebilirsin."
                )
            elif active_param == "Brix":
                st.caption(
                    "Bu degerler 19 CFR 151.91 (ABD federal regulasyonu, meyve "
                    "sulari icin resmi ortalama Brix tablosu) ve sektor pratigine "
                    "dayanir; resmi tek nokta ortalamaya ±0.5 tolerans eklenerek "
                    "aralik haline getirildi. Turk Gida Kodeksi'nin yerini tutmaz - "
                    "kalite kontrol referansidir. LSL/USL degerlerini kendi "
                    "urun/spesifikasyonuna gore elle degistirebilirsin."
                )
            elif active_param == "Viskozite":
                st.caption(
                    "Bu degerler Prime Resins ve Sculpture Supply teknik "
                    "viskozite tablolarina (gercek marka olcumlerine dayanan "
                    "sektor referanslari) dayanir - resmi bir standart degil, "
                    "kalite kontrol referansidir. **Ketcap, hardal gibi bazi "
                    "urunler tiksotropiktir** - karistirma/basinc arttikca "
                    "viskoziteleri azalir; olcum kosullari (karistirma hizi, "
                    "bekleme suresi) standardize edilmeden yapilan olcumler "
                    "tutarsiz olabilir."
                )
            elif active_param == "Aw":
                st.caption(
                    "Bu degerler DRINC/UC Davis ve Virginia Tech Cooperative "
                    "Extension aw referans tablolarina dayanir - kalite kontrol "
                    "referansidir, zorunlu bir limit degil. **aw'de sadece USL "
                    "(ust limit) anlamlidir**: aw belirli bir degerin ustune "
                    "cikarsa mikrobiyal ureme riski artar; alt limit cogu urun "
                    "icin tanimsiz oldugundan LSL bu parametrede kullanilmaz."
                )
            elif active_param == "Nem/Rutubet":
                st.caption(
                    "Bu degerler sektor pratigine dayanan gosterge degerlerdir, "
                    "kalite kontrol referansidir. **Bal urunu icin sadece USL "
                    "anlamlidir** (TGK Bal Tebligi'nde nem icin tek tarafli ust "
                    "limit tanimlanmistir) - bu urun secildiginde LSL otomatik "
                    "devre disi kalir ve Cpu hesaplanir; diger urunler iki "
                    "tarafli kalir."
                )
            elif active_param == "Tuz/NaCl":
                st.caption(
                    "Bu degerler sektor pratigine dayanan gosterge degerlerdir, "
                    "kalite kontrol referansidir, TGK'nin yerini tutmaz. LSL/USL "
                    "degerlerini kendi urun/spesifikasyonuna gore elle "
                    "degistirebilirsin."
                )
            elif active_param == "Titrasyon Asitligi":
                st.caption(
                    "Bu degerler sektor pratigine dayanan gosterge degerlerdir, "
                    "kalite kontrol referansidir. Titrasyon asitligi, urunun "
                    "toplam asit icerigini (pH'tan farkli olarak) yansitir; "
                    "LSL/USL degerlerini kendi urun/spesifikasyonuna gore elle "
                    "degistirebilirsin."
                )
            elif active_param == "Peroksit Degeri":
                st.caption(
                    "Bu deger Codex Alimentarius / IOC (International Olive "
                    "Council) standardina dayanir (zeytinyagi icin) - kalite "
                    "kontrol referansidir. **Sadece USL anlamlidir**: peroksit "
                    "degeri yaglarda oksidasyon derecesini gosterir, ne kadar "
                    "dusukse o kadar iyidir; alt limit kavrami yoktur."
                )
            elif active_param == "HMF":
                st.caption(
                    "Bu degerler TGK Bal Tebligi, TGK Uzum Pekmezi Tebligi ve "
                    "genel sektor pratigine dayanir. **Sadece USL anlamlidir**: "
                    "HMF, isil islem/depolama sirasinda sekerlerin bozunmasinin "
                    "gostergesidir; alt limit kavrami yoktur."
                )
            elif active_param in FOOD_QUALITY_PARAMETER_CONFIG:
                # v1.4->v1.6 Food Quality Parameters (Protein, Yag, Kul, Kuru
                # Madde, Yogunluk, Refraktif Indeks, L*, a*, b*, Bulaniklik,
                # Iletkenlik): bu parametreler mikrobiyoloji DEGIL, asagidaki
                # 'is_microbio' else dalina hicbir zaman ait olmamaliydi -
                # oraya dusunce 'Default LOD' kartinin ':g' format spesi
                # None/'-' uzerinde ValueError ile COKUYORDU (canli denetimde
                # bulundu). Bilgi metni zaten framework'ten otomatik uretilir
                # (bkz. get_parameter_info_text/build_parameter_info_card,
                # ust taraftaki "SEKME 2" basligindaki karta da ayni metin
                # basiliyor) - burada ayrica kopyalanmaz, sadece kaynak atfi
                # gosterilir.
                st.caption(
                    f"Bu deger {PARAMETER_SOURCES.get(active_param, '-')} "
                    "kaynagina dayanan gosterge degeridir - resmi/zorunlu bir "
                    "TGK limiti degildir. LSL/USL degerlerini kendi urun/"
                    "spesifikasyonuna gore elle degistirebilirsin."
                )
            else:  # is_microbio (TPC/TMAB, Kuf-Maya, Koliform, Enterobacteriaceae, Kantitatif S. aureus)
                # v1.3 Madde 3 (kalan mikrobiyoloji parametreleri) ONCESI bu else
                # dali sadece HMF'i kapsiyordu - 5 yeni mikrobiyoloji parametresi
                # eklenince YANLISLIKLA HMF'e ozgu metni (TGK Bal Tebligi vb.)
                # gosteriyordu (gercek bir hata, yukaridaki elif active_param ==
                # "HMF" ile duzeltildi). Method referanslari PARAMETER_SOURCES'tan
                # (constants.py) okunur - ayri bir kopya metin YAZILMAZ.
                st.caption(
                    f"Bu deger {PARAMETER_SOURCES.get(active_param, '-')} kaynagina "
                    "dayanan GOSTERGE degeridir, resmi/zorunlu bir TGK limiti "
                    "DEGILDIR. **Sadece USL anlamlidir** (mikrobiyal sayimlarda "
                    "alt limit kavrami yoktur - az bakteri her zaman iyidir); "
                    "grafik/Cpk **log10 olceginde** hesaplanir (bkz. asagidaki "
                    "'Parametre Bilgi Karti')."
                )
                with st.container(border=True):
                    ic1, ic2, ic3 = st.columns(3)
                    ic1.markdown(f"**Unit**  \n{unit}")
                    ic1.markdown(f"**Chart**  \n{'I-MR' if is_individual else 'X-bar/R'}")
                    ic2.markdown(f"**Capability**  \n{'Cpu (tek tarafli)' if one_sided else 'Cpk'}")
                    ic2.markdown(f"**Default LOD**  \n{param_config.get('default_lod', '-'):g} {unit}")
                    _typical_usl = param_config["default_usl"]
                    ic3.markdown(f"**Typical Specification**  \n≤ {_typical_usl:g} {unit}")
                    ic3.markdown(f"**Transformation**  \n{param_config.get('log_axis_label', 'log10')}")
                    _methods = ["ICMSF", "FDA BAM (LOD/2 ikamesi)"]
                    if active_param == "Kantitatif S. aureus":
                        _methods.append("ISO 6888-1")
                    st.caption(f"\U0001F4D0 Method: {' · '.join(_methods)}")

            col1, col2 = st.columns(2)
            with col1:
                lsl = st.number_input(
                    f"Alt spesifikasyon limiti (LSL, {unit})", step=0.01, format="%.2f",
                    min_value=param_config["min_value"], max_value=param_config["max_value"],
                    key="lsl_input", disabled=one_sided,
                    help=(
                        "Bu urun/parametrede LSL kullanilmiyor (bkz. yukaridaki not)."
                        if one_sided else
                        "Surecin kabul edilebilir alt siniri - Cpk hesabinda kullanilir."
                    ),
                )
            with col2:
                usl = st.number_input(
                    f"Ust spesifikasyon limiti (USL, {unit})", step=0.01, format="%.2f", key="usl_input",
                    min_value=param_config["min_value"], max_value=param_config["max_value"],
                    help="Surecin kabul edilebilir ust siniri - Cpk/Cpu hesabinda kullanilir.",
                )

            # spec_valid=False iken Cpk/Cpu HESAPLANMAZ VE GOSTERILMEZ (asagidaki
            # KPI karti/mesaj/hesaplama adimlari bunu kontrol eder) - LSL>=USL
            # durumunda formul matematiksel olarak calisir ama anlamsiz bir sayi
            # uretir (orn. Cpk=-6.998), bu da yukaridaki hata mesajiyla celisen
            # yaniltici bir "sonuc" gostermis olurdu.
            spec_valid = is_spec_valid(one_sided, lsl, usl)
            if not spec_valid:
                st.error(
                    f"Gecersiz spesifikasyon: LSL ({lsl:.2f}) >= USL ({usl:.2f}). "
                    "Alt limit ust limitten kucuk olmalidir - asagidaki Cpk/kontrol "
                    "semasi sonuclari bu duzeltilene kadar anlamsizdir."
                )

        if is_microbio:
            # KRITIK: lsl/usl widget'lari (yukarida) HAM KOB/g olceginde
            # girilir/gosterilir, ama subgroups["values"] (compute_individual_
            # stats -> values/x_bar/mr_bar) ZATEN log10'dur (bkz. build_
            # subgroup_entry). Bu blok ASAGIDAKI TUM chart/Cpk/OOS/histogram
            # kodu (satirin sonuna kadar, is_individual dalinin ICINDE) log10
            # olcekte calisir - lsl/usl'i BURADA (widget'in session_state
            # degerini DEGIL, sadece bu run'daki YEREL degiskeni) log10'a
            # ceviriyoruz. st.session_state.lsl_input/usl_input HAM kalir,
            # widget bir sonraki run'da yine HAM KOB/g gosterir.
            usl = to_log10(usl) if usl > 0 else usl
            lsl = to_log10(lsl) if lsl > 0 else lsl  # one_sided=True oldugu icin kullanilmiyor, tutarlilik icin
            unit = param_config.get("log_axis_label", unit)
            decimal_places = param_config.get("log_decimal_places", decimal_places)

        st.write("")

        if is_individual:
            # ADIM 4: Process Capability / Data Summary / Baseline Reference
            # referans taslaktaki hiyerarsiyle ayni sirada yan yana (bkz.
            # sohbet gecmisindeki "1. secenek" onayi). Baseline karti
            # KENDI x_bar/mr_bar'ini urettigi icin (butonlar/onay akislari
            # dahil) mantiksal olarak ILK calismasi gerekiyor - ama
            # st.columns() nesneleri ONCE olusturulup, doldurma sirasi
            # (col_baseline -> col_cap -> col_summary) GORSEL soldan-saga
            # sirayla AYNI OLMAK ZORUNDA DEGIL; Streamlit bu iki seyi
            # ayirir. UCL/LCL (I chart), limits hesaplanmadan once
            # bilinmedigi icin st.empty() placeholder ile baseline
            # kartinin ICINE sonradan yerlestirilir.
            col_cap, col_summary, col_baseline = st.columns(3)

            with col_baseline:
                with st.container(border=True, key="card-07"):
                    st.markdown("##### \U0001F4CC Baseline Referansi")

                    baseline = st.session_state.baseline
                    n_current = len(st.session_state.subgroups)
                    values, moving_ranges, live_x_bar, live_mr_bar = compute_individual_stats(
                        st.session_state.subgroups
                    )

                    if baseline is None:
                        st.info(
                            "Baseline henuz dondurulmadi. Asagidaki UCL/LCL, mevcut TUM "
                            "olculerden canli hesaplaniyor; yeni veri eklendikce degisir. "
                            "Bu, kontrol disi bir noktanin limitleri kendine dogru cekmesine "
                            "yol acabilir (SPC'de 'limitleri kovalamak' olarak bilinen hata)."
                        )
                        if n_current < MIN_RECOMMENDED_BASELINE:
                            st.warning(
                                f"Su an {n_current} olcum var. Guvenilir kontrol limitleri "
                                f"icin en az {MIN_RECOMMENDED_BASELINE} olcum onerilir "
                                "(Montgomery, Introduction to Statistical Quality Control)."
                            )

                        if not st.session_state.confirm_freeze:
                            if st.button("\U0001F4CC Baseline'i hesapla ve dondur"):
                                st.session_state.confirm_freeze = True
                                st.rerun()
                        else:
                            st.warning(
                                "Emin misiniz? Baseline donduruldugunda UCL/LCL sabitlenir; "
                                "yeni eklenen veriler bunlari degistirmez. Geri almak icin "
                                "sonradan 'Baseline'i sifirla' kullanman gerekir."
                            )
                            fc1, fc2 = st.columns(2)
                            with fc1:
                                if st.button("Evet, dondur", type="primary", key="confirm_freeze_yes"):
                                    st.session_state.baseline = {
                                        "x_bar": live_x_bar,
                                        "mr_bar": live_mr_bar,
                                        "n_baseline": n_current,
                                    }
                                    st.session_state.confirm_freeze = False
                                    st.rerun()
                            with fc2:
                                if st.button("Vazgec", key="confirm_freeze_no"):
                                    st.session_state.confirm_freeze = False
                                    st.rerun()

                        x_bar = live_x_bar
                        mr_bar = live_mr_bar
                    else:
                        st.success(
                            f"Baseline donduruldu: ilk {baseline['n_baseline']} olcum ile "
                            "hesaplandi. UCL/LCL artik sabit; yeni eklenen olcumler bu "
                            "limitlerle karsilastirilir, limitleri degistirmez."
                        )
                        if baseline["n_baseline"] < MIN_RECOMMENDED_BASELINE:
                            st.warning(
                                f"Bu baseline yalnizca {baseline['n_baseline']} olcume dayaniyor "
                                f"(onerilen minimum: {MIN_RECOMMENDED_BASELINE}) - UCL/LCL ve Cpk/Cpu "
                                "guvenilirligi sinirlidir, yorumlarken dikkatli olun."
                            )

                        if not st.session_state.confirm_reset_baseline:
                            if st.button("\U0001F513 Baseline'i sifirla"):
                                st.session_state.confirm_reset_baseline = True
                                st.rerun()
                        else:
                            st.warning(
                                "Emin misiniz? Baseline sifirlanirsa UCL/LCL tekrar "
                                "mevcut TUM veriden canli hesaplanmaya baslar."
                            )
                            rc1, rc2 = st.columns(2)
                            with rc1:
                                if st.button("Evet, sifirla", type="primary", key="confirm_reset_yes"):
                                    st.session_state.baseline = None
                                    st.session_state.confirm_reset_baseline = False
                                    st.rerun()
                            with rc2:
                                if st.button("Vazgec", key="confirm_reset_no"):
                                    st.session_state.confirm_reset_baseline = False
                                    st.rerun()

                        x_bar = baseline["x_bar"]
                        mr_bar = baseline["mr_bar"]

                    ucl_lcl_slot = st.empty()

            limits = compute_imr_limits(x_bar, mr_bar)
            cpk = compute_cpk(x_bar, mr_bar, 2, lsl, usl, one_sided=one_sided)
            ucl_lcl_slot.metric(
                "UCL / LCL (I chart)", f"{limits.ucl_i:.{decimal_places}f} / {limits.lcl_i:.{decimal_places}f}",
                help="Istatistiksel kontrol limitleri (Ust/Alt Kontrol Siniri) - surecin dogal varyasyon araligi, spesifikasyon limitleriyle (LSL/USL) karistirilmamalidir.",
            )

            indices_i = list(range(1, len(values) + 1))
            indices_mr = list(range(2, len(values) + 1))
            sigma_hat_imr = mr_bar / MR_CHART_D2 if MR_CHART_D2 else 0.0

            # OOT (Out of Trend): UCL/LCL asimi VEYA Nelson oruntu sinyali (2/3
            # 2-sigma, 4/5 1-sigma, 9 ayni-taraf) - surecin DAVRANIS sinyali,
            # spesifikasyonla dogrudan ilgisi yok. Nelson kurallari x_bar/
            # sigma_hat merkez alinarak 'values' (ham I chart serisi) uzerinde
            # calisir - MR serisi uzerinde CALISTIRILMAZ (Nelson kurallari
            # klasik olarak birincil chart'a uygulanir, range/MR chart'ina degil).
            out_of_control_i = [i for i, v in enumerate(values) if v > limits.ucl_i or v < limits.lcl_i]
            out_of_control_mr = [
                i for i, mr in enumerate(moving_ranges) if mr > limits.ucl_mr or mr < limits.lcl_mr
            ]
            nelson_oot_i = compute_nelson_oot_indices(values, x_bar, sigma_hat_imr)
            oot_indices_i = set(out_of_control_i) | nelson_oot_i
            oot_points = sorted({i + 1 for i in oot_indices_i} | {i + 2 for i in out_of_control_mr})

            # OOS (Out of Specification): HAM olcumun LSL/USL DISINA cikmasi -
            # I-MR'de her 'grup' tek bir olcum oldugu icin oos_indices_i
            # dogrudan values ile AYNI (0-tabanli) indeks uzayindadir.
            oos_indices_i, oos_raw_count_i = compute_oos_flags([[v] for v in values], lsl, usl, one_sided)

            with col_cap:
                with st.container(border=True, key="card-08"):
                    render_capability_card(cpk, cpk_label, spec_valid)
                    if spec_valid:
                        with st.expander("\U0001F9EE Hesaplama adimlarini goster"):
                            render_calculation_steps_imr(x_bar, mr_bar, limits, cpk, cpk_label, lsl, usl, one_sided, unit, decimal_places)
                        ppk_i = compute_ppk(values, lsl, usl, one_sided=one_sided)
                        pp_i = None if one_sided else compute_pp(values, lsl, usl)
                        render_ppk_pp_expander(cpk, ppk_i, pp_i, one_sided)

            with col_summary:
                with st.container(border=True, key="card-09"):
                    render_data_summary_card(
                        f"Genel Ortalama (x̄, {unit})", x_bar,
                        f"Ortalama MR (MR̄, {unit})", mr_bar,
                        "Olcum Sayisi", len(values),
                        oos_raw_count_i, len(oot_points), decimal_places,
                    )

            render_formula_method_card("I-MR", 2)

            st.write("")

            if spec_valid:
                imr_quick_summary = build_quick_summary(
                    "olcum", len(values), len(oot_points), oos_raw_count_i, cpk, cpk_label
                ) + build_trend_nelson_comment(compute_trend(values), bool(nelson_oot_i))
            else:
                oot_text = "OOT (kontrol disi) nokta yok" if not oot_points else f"{len(oot_points)} OOT (kontrol disi) nokta var"
                imr_quick_summary = (
                    f"{len(values)} olcum analiz edildi, {oot_text}, "
                    f"{cpk_label} hesaplanamadi (spesifikasyon gecersiz: LSL >= USL)."
                )
            with st.container(border=True, key="card-10"):
                st.markdown(f"**\U0001F4CB Ozet:** {imr_quick_summary}")
                st.code(imr_quick_summary, language=None)
                render_last_analysis_card(
                    st.session_state.active_parameter, selected_product, "I-MR",
                    len(values), cpk, cpk_label, cpk_valid=spec_valid,
                )

            st.write("")

            with st.container(border=True, key="card-11"):
                st.subheader("I (Individual) Kontrol Grafigi")

                fig, ax = plt.subplots(figsize=(8, 3.5), constrained_layout=True)
                ax.plot(indices_i, values, marker="o", color=accent_color, linewidth=1, label="Olcum")
                ax.axhline(x_bar, color="green", linestyle="-", label="Genel ortalama (x̄)")
                ax.axhline(limits.ucl_i, color="red", linestyle="--", label="UCL")
                annotate_hline(ax, indices_i[-1], limits.ucl_i, f"UCL={limits.ucl_i:.{decimal_places}f}", "red")
                annotate_hline(ax, indices_i[-1], x_bar, f"x̄={x_bar:.{decimal_places}f}", "green")
                if not one_sided:
                    # Tek tarafli (one_sided) analizde LSL/LCL anlamsizdir (bkz.
                    # Spesifikasyon limitleri karti) - grafik sadelestirmesi
                    # olarak bu durumda LCL cizgisi/etiketi cizilmez.
                    ax.axhline(limits.lcl_i, color="red", linestyle="--", label="LCL")
                    annotate_hline(ax, indices_i[-1], limits.lcl_i, f"LCL={limits.lcl_i:.{decimal_places}f}", "red")
                # Spesifikasyon (LSL/USL) cizgileri - UCL/LCL'den BILEREK farkli
                # cizgi rengi/tonu (mor, kesikli-noktali) kullanilir ki "kontrol
                # limiti" (kirmizi, kesikli) ile "spesifikasyon limiti" (mor,
                # kesikli-noktali) gorsel olarak KARISTIRILMASIN - ayni ayrim
                # OOS_MARKER_COLOR/OOT_LINE_COLOR renk cifti icin de gecerli.
                ax.axhline(usl, color=OOS_MARKER_COLOR, linestyle="-.", linewidth=1.2, label="USL")
                annotate_hline(ax, indices_i[-1], usl, f"USL={usl:.{decimal_places}f}", OOS_MARKER_COLOR)
                if not one_sided:
                    ax.axhline(lsl, color=OOS_MARKER_COLOR, linestyle="-.", linewidth=1.2, label="LSL")
                    annotate_hline(ax, indices_i[-1], lsl, f"LSL={lsl:.{decimal_places}f}", OOS_MARKER_COLOR)
                if oot_indices_i:
                    highlight_oot_segments(ax, indices_i, values, oot_indices_i)
                    ax.scatter(
                        [indices_i[i] for i in oot_indices_i],
                        [values[i] for i in oot_indices_i],
                        color="red", s=100, zorder=5, label="OOT (kontrol disi)",
                    )
                if oos_indices_i:
                    ax.scatter(
                        [indices_i[i] for i in oos_indices_i],
                        [values[i] for i in oos_indices_i],
                        marker="D", facecolors="none", edgecolors=OOS_MARKER_COLOR,
                        s=140, linewidths=2, zorder=6, label="OOS (spesifikasyon disi)",
                    )
                ax.set_xlabel("Olcum no")
                ax.set_ylabel(unit)
                ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1), fontsize=8)
                draw_zone_shading(ax, x_bar, sigma_hat_imr, dark)
                style_chart(fig, ax, dark)
                st.pyplot(fig, use_container_width=True)
                render_png_download(fig, f"{st.session_state.active_parameter.lower()}_i_chart.png", key="png_i_chart")
                imr_main_chart_png = fig_to_png_bytes(fig)
                plt.close(fig)

            st.write("")

            with st.container(border=True, key="card-12"):
                st.subheader("Surec Yeterlilik Histogrami")
                st.caption(
                    "Olculen degerlerin dagilimi + normal dagilim egrisi (scipy.stats.norm). "
                    "Bu, kontrol grafiginden farkli bir gorseldir - zaman sirasini degil, "
                    "verinin spesifikasyon limitlerine gore genel dagilimini gosterir."
                )
                hist_fig = render_capability_histogram(values, lsl, usl, one_sided, dark, unit, accent_color)
                st.pyplot(hist_fig, use_container_width=True)
                render_png_download(
                    hist_fig, f"{st.session_state.active_parameter.lower()}_histogram.png", key="png_histogram"
                )
                imr_histogram_png = fig_to_png_bytes(hist_fig)
                plt.close(hist_fig)
                render_normality_check(values)

            st.write("")

            with st.container(border=True, key="card-13"):
                st.subheader("MR (Moving Range) Kontrol Grafigi")

                fig2, ax2 = plt.subplots(figsize=(8, 2.8), constrained_layout=True)
                ax2.plot(
                    indices_mr, moving_ranges, marker="o", color=accent_color, linewidth=1,
                    label="Moving range",
                )
                ax2.axhline(mr_bar, color="green", linestyle="-", label="MR̄")
                ax2.axhline(limits.ucl_mr, color="red", linestyle="--", label="UCL_MR")
                ax2.axhline(limits.lcl_mr, color="red", linestyle="--", label="LCL_MR")
                annotate_hline(ax2, indices_mr[-1], limits.ucl_mr, f"UCL={limits.ucl_mr:.{decimal_places}f}", "red")
                annotate_hline(ax2, indices_mr[-1], mr_bar, f"MR̄={mr_bar:.{decimal_places}f}", "green")
                if out_of_control_mr:
                    highlight_oot_segments(ax2, indices_mr, moving_ranges, out_of_control_mr)
                    ax2.scatter(
                        [indices_mr[i] for i in out_of_control_mr],
                        [moving_ranges[i] for i in out_of_control_mr],
                        color="red", s=100, zorder=5, label="Kontrol disi",
                    )
                ax2.set_xlabel("Olcum no")
                ax2.set_ylabel("Moving Range")
                ax2.legend(loc="upper left", bbox_to_anchor=(1.02, 1), fontsize=8)
                shade_lcl_zero_zone(ax2, limits.lcl_mr)
                style_chart(fig2, ax2, dark)
                st.pyplot(fig2, use_container_width=True)
                render_png_download(fig2, f"{st.session_state.active_parameter.lower()}_mr_chart.png", key="png_mr_chart")
                imr_mr_chart_png = fig_to_png_bytes(fig2)
                plt.close(fig2)

            with st.container(border=True, key="card-14"):
                if spec_valid:
                    render_pdf_download(
                        st.session_state.active_parameter, selected_product, "I-MR",
                        len(values), len(oot_points), cpk, cpk_label, imr_quick_summary,
                        [
                            ("I (Individual) Kontrol Grafigi", imr_main_chart_png),
                            ("MR (Moving Range) Kontrol Grafigi", imr_mr_chart_png),
                            ("Surec Yeterlilik Histogrami", imr_histogram_png),
                        ],
                        key="pdf_imr",
                    )
                else:
                    st.info(
                        "PDF raporu, spesifikasyon (LSL/USL) gecerli hale getirilene "
                        "kadar devre disi - gecersiz bir Cpk iceren rapor uretilmez."
                    )

            if oot_points:
                st.warning(
                    f"OOT (kontrol disi) olcumler: {oot_points} "
                    "- surec bu noktalarda beklenmedik bir davranis (kontrol limiti "
                    "asimi veya Nelson oruntu sinyali) gosteriyor."
                )
            if oos_indices_i:
                oos_measurement_numbers = sorted(i + 1 for i in oos_indices_i)
                st.warning(
                    f"OOS (spesifikasyon disi) olcumler: {oos_measurement_numbers} "
                    "- bu olcumler LSL/USL disina cikiyor."
                )
        else:
            means, ranges, live_x_double_bar, live_r_bar = compute_stats(st.session_state.subgroups)

            # ADIM 4: bkz. I-MR dalindaki ayni desenin aciklamasi (yukarida) -
            # Process Capability / Data Summary / Baseline Reference yan
            # yana, baseline karti mantiksal olarak once doldurulur (x_double_bar/
            # r_bar'i uretir), UCL/LCL ise st.empty() ile sonradan yerlestirilir.
            col_cap, col_summary, col_baseline = st.columns(3)

            with col_baseline:
                with st.container(border=True, key="card-15"):
                    st.markdown("##### \U0001F4CC Baseline Referansi")

                    baseline = st.session_state.baseline
                    n_current = len(st.session_state.subgroups)

                    if baseline is None:
                        st.info(
                            "Baseline henuz dondurulmadi. Asagidaki UCL/LCL, mevcut TUM alt "
                            "gruplardan canli hesaplaniyor; yeni veri eklendikce degisir. "
                            "Bu, kontrol disi bir noktanin limitleri kendine dogru cekmesine "
                            "yol acabilir (SPC'de 'limitleri kovalamak' olarak bilinen hata)."
                        )
                        if n_current < MIN_RECOMMENDED_BASELINE:
                            st.warning(
                                f"Su an {n_current} alt grup var. Guvenilir kontrol limitleri "
                                f"icin en az {MIN_RECOMMENDED_BASELINE} alt grup onerilir "
                                "(Montgomery, Introduction to Statistical Quality Control)."
                            )

                        if not st.session_state.confirm_freeze:
                            if st.button("\U0001F4CC Baseline'i hesapla ve dondur"):
                                st.session_state.confirm_freeze = True
                                st.rerun()
                        else:
                            st.warning(
                                "Emin misiniz? Baseline donduruldugunda UCL/LCL sabitlenir; "
                                "yeni eklenen veriler bunlari degistirmez. Geri almak icin "
                                "sonradan 'Baseline'i sifirla' kullanman gerekir."
                            )
                            fc1, fc2 = st.columns(2)
                            with fc1:
                                if st.button("Evet, dondur", type="primary", key="confirm_freeze_yes"):
                                    st.session_state.baseline = {
                                        "x_double_bar": live_x_double_bar,
                                        "r_bar": live_r_bar,
                                        "n_baseline": n_current,
                                    }
                                    st.session_state.confirm_freeze = False
                                    st.rerun()
                            with fc2:
                                if st.button("Vazgec", key="confirm_freeze_no"):
                                    st.session_state.confirm_freeze = False
                                    st.rerun()

                        x_double_bar = live_x_double_bar
                        r_bar = live_r_bar
                    else:
                        st.success(
                            f"Baseline donduruldu: ilk {baseline['n_baseline']} alt grup ile "
                            "hesaplandi. UCL/LCL artik sabit; yeni eklenen alt gruplar bu "
                            "limitlerle karsilastirilir, limitleri degistirmez."
                        )
                        if baseline["n_baseline"] < MIN_RECOMMENDED_BASELINE:
                            st.warning(
                                f"Bu baseline yalnizca {baseline['n_baseline']} alt gruba dayaniyor "
                                f"(onerilen minimum: {MIN_RECOMMENDED_BASELINE}) - UCL/LCL ve Cpk/Cpu "
                                "guvenilirligi sinirlidir, yorumlarken dikkatli olun."
                            )

                        if not st.session_state.confirm_reset_baseline:
                            if st.button("\U0001F513 Baseline'i sifirla"):
                                st.session_state.confirm_reset_baseline = True
                                st.rerun()
                        else:
                            st.warning(
                                "Emin misiniz? Baseline sifirlanirsa UCL/LCL tekrar "
                                "mevcut TUM veriden canli hesaplanmaya baslar."
                            )
                            rc1, rc2 = st.columns(2)
                            with rc1:
                                if st.button("Evet, sifirla", type="primary", key="confirm_reset_yes"):
                                    st.session_state.baseline = None
                                    st.session_state.confirm_reset_baseline = False
                                    st.rerun()
                            with rc2:
                                if st.button("Vazgec", key="confirm_reset_no"):
                                    st.session_state.confirm_reset_baseline = False
                                    st.rerun()

                        x_double_bar = baseline["x_double_bar"]
                        r_bar = baseline["r_bar"]

                    ucl_lcl_slot = st.empty()

            limits = compute_xbar_r_limits(x_double_bar, r_bar, subgroup_n)
            cpk = compute_cpk(x_double_bar, r_bar, subgroup_n, lsl, usl, one_sided=one_sided)
            ucl_lcl_slot.metric(
                "UCL / LCL (X-bar)", f"{limits.ucl_x:.{decimal_places}f} / {limits.lcl_x:.{decimal_places}f}",
                help="Istatistiksel kontrol limitleri (Ust/Alt Kontrol Siniri) - surecin dogal varyasyon araligi, spesifikasyon limitleriyle (LSL/USL) karistirilmamalidir.",
            )

            indices = list(range(1, len(means) + 1))
            sigma_hat_xbar = r_bar / limits.d2 if limits.d2 else 0.0

            # OOT: bkz. I-MR dalindaki ayni mantigin aciklamasi (yukarida).
            # Nelson kurallari alt grup ORTALAMALARI (means) uzerinde calisir -
            # R chart'ina (araliklara) DEGIL, X-bar/I-MR ile ayni gerekce.
            out_of_control_x = [i for i, m in enumerate(means) if m > limits.ucl_x or m < limits.lcl_x]
            out_of_control_r = [i for i, r in enumerate(ranges) if r > limits.ucl_r or r < limits.lcl_r]
            nelson_oot_x = compute_nelson_oot_indices(means, x_double_bar, sigma_hat_xbar)
            oot_indices_x = set(out_of_control_x) | nelson_oot_x
            oot_groups = sorted({i + 1 for i in oot_indices_x} | {i + 1 for i in out_of_control_r})

            # OOS: X-bar/R'de spesifikasyon HAM olculere (alt grubun icindeki
            # tek tek degerlere) karsi kontrol edilir - alt grup ORTALAMASI
            # spec icinde olsa bile, o ortalamayi olusturan ham olculerden biri
            # spec disina cikmis olabilir (ve bunun tersi de dogrudur, bu yuzden
            # ayrica kontrol edilir, out_of_control_x'ten TURETILMEZ).
            oos_group_indices_x, oos_raw_count_x = compute_oos_flags(
                [sg["values"] for sg in st.session_state.subgroups], lsl, usl, one_sided
            )

            with col_cap:
                with st.container(border=True, key="card-16"):
                    render_capability_card(cpk, cpk_label, spec_valid)
                    if spec_valid:
                        with st.expander("\U0001F9EE Hesaplama adimlarini goster"):
                            render_calculation_steps_xbar(x_double_bar, r_bar, limits, cpk, cpk_label, lsl, usl, one_sided, unit, decimal_places)
                        # Ppk/Pp, X-bar/R'de de TUM HAM olculere (alt grup
                        # ortalamalarina degil) dayanir - ayni gerekce:
                        # Cpk'nin gormedigi alt-gruplar-arasi kaymayi da
                        # yansitsin diye (bkz. compute_ppk docstring'i).
                        all_raw_values_x = [v for sg in st.session_state.subgroups for v in sg["values"]]
                        ppk_x = compute_ppk(all_raw_values_x, lsl, usl, one_sided=one_sided)
                        pp_x = None if one_sided else compute_pp(all_raw_values_x, lsl, usl)
                        render_ppk_pp_expander(cpk, ppk_x, pp_x, one_sided)

            with col_summary:
                with st.container(border=True, key="card-17"):
                    render_data_summary_card(
                        f"Genel Ortalama (x̄̄, {unit})", x_double_bar,
                        f"Ortalama Range (R̄, {unit})", r_bar,
                        "Alt Grup Sayisi", len(means),
                        oos_raw_count_x, len(oot_groups), decimal_places,
                    )

            render_formula_method_card("X-bar/R", subgroup_n)

            st.write("")

            if spec_valid:
                xbar_quick_summary = build_quick_summary(
                    "alt grup", len(means), len(oot_groups), oos_raw_count_x, cpk, cpk_label
                ) + build_trend_nelson_comment(compute_trend(means), bool(nelson_oot_x))
            else:
                oot_text = "OOT (kontrol disi) nokta yok" if not oot_groups else f"{len(oot_groups)} OOT (kontrol disi) nokta var"
                xbar_quick_summary = (
                    f"{len(means)} alt grup analiz edildi, {oot_text}, "
                    f"{cpk_label} hesaplanamadi (spesifikasyon gecersiz: LSL >= USL)."
                )
            with st.container(border=True, key="card-18"):
                st.markdown(f"**\U0001F4CB Ozet:** {xbar_quick_summary}")
                st.code(xbar_quick_summary, language=None)
                render_last_analysis_card(
                    st.session_state.active_parameter, selected_product, "X-bar/R",
                    len(means), cpk, cpk_label, cpk_valid=spec_valid,
                )

            st.write("")

            if spec_valid:
                render_shift_comparison(
                    st.session_state.subgroups, subgroup_n, lsl, usl, one_sided, cpk_label, unit,
                )
            else:
                with st.container(border=True, key="card-19"):
                    st.subheader("Vardiya Karsilastirmasi")
                    st.info(
                        "Spesifikasyon (LSL/USL) gecerli hale getirilene kadar vardiya "
                        "bazinda Cpk/Cpu karsilastirmasi gosterilmiyor."
                    )

            st.write("")

            with st.container(border=True, key="card-20"):
                st.subheader("X-bar Kontrol Grafigi")

                fig, ax = plt.subplots(figsize=(8, 3.5), constrained_layout=True)
                ax.plot(indices, means, marker="o", color=accent_color, linewidth=1, label="Alt grup ortalamasi")
                ax.axhline(x_double_bar, color="green", linestyle="-", label="Genel ortalama (x̄̄)")
                ax.axhline(limits.ucl_x, color="red", linestyle="--", label="UCL")
                annotate_hline(ax, indices[-1], limits.ucl_x, f"UCL={limits.ucl_x:.{decimal_places}f}", "red")
                annotate_hline(ax, indices[-1], x_double_bar, f"x̄̄={x_double_bar:.{decimal_places}f}", "green")
                if not one_sided:
                    # Tek tarafli (one_sided) analizde LSL/LCL anlamsizdir (bkz.
                    # Spesifikasyon limitleri karti) - grafik sadelestirmesi
                    # olarak bu durumda LCL cizgisi/etiketi cizilmez.
                    ax.axhline(limits.lcl_x, color="red", linestyle="--", label="LCL")
                    annotate_hline(ax, indices[-1], limits.lcl_x, f"LCL={limits.lcl_x:.{decimal_places}f}", "red")
                if oot_indices_x:
                    highlight_oot_segments(ax, indices, means, oot_indices_x)
                    ax.scatter(
                        [indices[i] for i in oot_indices_x],
                        [means[i] for i in oot_indices_x],
                        color="red", s=100, zorder=5, label="OOT (kontrol disi)",
                    )
                if oos_group_indices_x:
                    # X-bar chart'i ALT GRUP ORTALAMASINI cizer, ham olcumu
                    # degil - bu yuzden LSL/USL cizgileri BURAYA cizilmez (bir
                    # ortalama spec icinde olsa bile grubu olusturan ham
                    # olculerden biri disarida kalmis olabilir, bkz. yukaridaki
                    # compute_oos_flags cagrisinin yorumu). Bunun yerine, EN AZ
                    # bir OOS ham olcum iceren alt grubun ORTALAMASI, "bu grupta
                    # dikkat edilmesi gereken bir ham olcum var" isareti olarak
                    # OOS markeriyle isaretlenir - etiket bunu acikca belirtir.
                    ax.scatter(
                        [indices[i] for i in oos_group_indices_x],
                        [means[i] for i in oos_group_indices_x],
                        marker="D", facecolors="none", edgecolors=OOS_MARKER_COLOR,
                        s=140, linewidths=2, zorder=6,
                        label="Grup icinde ≥ 1 OOS ham olcum",
                    )
                ax.set_xlabel("Alt grup no")
                ax.set_ylabel(unit)
                ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1), fontsize=8)
                draw_zone_shading(ax, x_double_bar, sigma_hat_xbar, dark)
                style_chart(fig, ax, dark)
                st.pyplot(fig, use_container_width=True)
                render_png_download(fig, f"{st.session_state.active_parameter.lower()}_xbar_chart.png", key="png_xbar_chart")
                xbar_main_chart_png = fig_to_png_bytes(fig)
                plt.close(fig)

            st.write("")

            with st.container(border=True, key="card-21"):
                st.subheader("Surec Yeterlilik Histogrami")
                st.caption(
                    "Tum bireysel olcumlerin (alt gruplar acilarak) dagilimi + normal "
                    "dagilim egrisi (scipy.stats.norm). Bu, kontrol grafiginden farkli "
                    "bir gorseldir - zaman sirasini degil, verinin spesifikasyon "
                    "limitlerine gore genel dagilimini gosterir."
                )
                all_values = [v for sg in st.session_state.subgroups for v in sg["values"]]
                hist_fig = render_capability_histogram(all_values, lsl, usl, one_sided, dark, unit, accent_color)
                st.pyplot(hist_fig, use_container_width=True)
                render_png_download(
                    hist_fig, f"{st.session_state.active_parameter.lower()}_histogram.png", key="png_histogram"
                )
                xbar_histogram_png = fig_to_png_bytes(hist_fig)
                plt.close(hist_fig)
                render_normality_check(all_values)

            st.write("")

            with st.container(border=True, key="card-22"):
                st.subheader("R Kontrol Grafigi")

                fig2, ax2 = plt.subplots(figsize=(8, 2.8), constrained_layout=True)
                ax2.plot(indices, ranges, marker="o", color=accent_color, linewidth=1, label="Alt grup range")
                ax2.axhline(r_bar, color="green", linestyle="-", label="R̄")
                ax2.axhline(limits.ucl_r, color="red", linestyle="--", label="UCL_R")
                ax2.axhline(limits.lcl_r, color="red", linestyle="--", label="LCL_R")
                annotate_hline(ax2, indices[-1], limits.ucl_r, f"UCL={limits.ucl_r:.{decimal_places}f}", "red")
                annotate_hline(ax2, indices[-1], r_bar, f"R̄={r_bar:.{decimal_places}f}", "green")
                if out_of_control_r:
                    highlight_oot_segments(ax2, indices, ranges, out_of_control_r)
                    ax2.scatter(
                        [indices[i] for i in out_of_control_r],
                        [ranges[i] for i in out_of_control_r],
                        color="red", s=100, zorder=5, label="Kontrol disi",
                    )
                ax2.set_xlabel("Alt grup no")
                ax2.set_ylabel("Range")
                ax2.legend(loc="upper left", bbox_to_anchor=(1.02, 1), fontsize=8)
                shade_lcl_zero_zone(ax2, limits.lcl_r)
                style_chart(fig2, ax2, dark)
                st.pyplot(fig2, use_container_width=True)
                render_png_download(fig2, f"{st.session_state.active_parameter.lower()}_r_chart.png", key="png_r_chart")
                xbar_r_chart_png = fig_to_png_bytes(fig2)
                plt.close(fig2)

            with st.container(border=True, key="card-23"):
                if spec_valid:
                    render_pdf_download(
                        st.session_state.active_parameter, selected_product, "X-bar/R",
                        len(means), len(oot_groups), cpk, cpk_label, xbar_quick_summary,
                        [
                            ("X-bar Kontrol Grafigi", xbar_main_chart_png),
                            ("R Kontrol Grafigi", xbar_r_chart_png),
                            ("Surec Yeterlilik Histogrami", xbar_histogram_png),
                        ],
                        key="pdf_xbar",
                    )
                else:
                    st.info(
                        "PDF raporu, spesifikasyon (LSL/USL) gecerli hale getirilene "
                        "kadar devre disi - gecersiz bir Cpk iceren rapor uretilmez."
                    )

            if oot_groups:
                st.warning(
                    f"OOT (kontrol disi) alt gruplar: {oot_groups} "
                    "- surec bu noktalarda beklenmedik bir davranis (kontrol limiti "
                    "asimi veya Nelson oruntu sinyali) gosteriyor."
                )
            if oos_group_indices_x:
                oos_group_numbers = sorted(i + 1 for i in oos_group_indices_x)
                st.warning(
                    f"OOS (spesifikasyon disi) alt gruplar: {oos_group_numbers} "
                    f"({oos_raw_count_x} ham olcum LSL/USL disina cikiyor)."
                )

# ---------------------------------------------------------------------------
# SEKME 3: Hizli Hesaplayicilar
# ---------------------------------------------------------------------------
# NOT: Bu sekme, mevcut SPC chart/veri akisindan BILINCLI OLARAK izole tutuldu.
# Totox ve Gravimetrik Nem tek seferlik hesap makineleridir - session_state.
# subgroups'a normalde dokunmazlar, kontrol grafigi/baseline mantigiyla
# etkilesime girmezler. TEK istisna: kullanicinin acikca tetikledigi, aktif
# parametre + I-MR tipi kontrolune tabi "SPC Veri Setine Aktar" kopru
# butonlari (bkz. asagida) - bilincli, gated bir istisnadir.
TOTOX_ANV_LIMIT = 20.0
TOTOX_LIMIT = 26.0


def render_totox_gauge(totox_value: float, totox_limit: float, dark: bool):
    """v1.2 Madde 13: Totox degerini TEK bir gorselde (ayri KPI karti degil)
    gosteren birlesik gauge + renkli badge. Yesil/kirmizi bolge sinirin
    neresinde oldugunu, siyah kesikli cizgi limitin tam yerini, kalin
    renkli cubuk ise mevcut degeri gosterir - rengi de ayni anda
    uygun/sinir disi durumunu iletir (ayri bir badge'e ihtiyac kalmadan)."""
    max_x = max(totox_limit * 1.4, totox_value * 1.15, 1.0)
    fig, ax = plt.subplots(figsize=(8, 1.1), constrained_layout=True)
    ax.barh(0, totox_limit, height=0.5, color="#2f9e44", alpha=0.18, zorder=1)
    ax.barh(0, max_x - totox_limit, left=totox_limit, height=0.5, color="#e03131", alpha=0.14, zorder=1)
    bar_color = "#2f9e44" if totox_value < totox_limit else "#e03131"
    ax.barh(0, min(totox_value, max_x), height=0.5, color=bar_color, zorder=2)
    ax.axvline(totox_limit, color="#495057", linestyle="--", linewidth=1.2, zorder=3)
    ax.text(totox_limit, 0.34, f"Limit={totox_limit:.0f}", ha="center", fontsize=8, color="#868e96")
    ax.text(
        min(totox_value, max_x), -0.42, f"{totox_value:.2f}", ha="center",
        fontsize=11, fontweight="bold", color=bar_color,
    )
    ax.set_xlim(0, max_x)
    ax.set_ylim(-0.6, 0.55)
    ax.set_yticks([])
    ax.set_xticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    style_chart(fig, ax, dark)
    ax.grid(False)
    for spine in ax.spines.values():
        spine.set_visible(False)
    return fig


def render_bridge_widget(
    values_by_target: dict, source_label: str, widget_key_prefix: str, extra_note: str | None = None,
) -> None:
    """QC donusturucu sonucunu SPC subgroups'a koprulemek icin PAYLASILAN UI
    bileseni - Faz 1 final review bulgusu (X-bar/R aktifken n=1 alt grup
    eklemek Range'i sifirlayip Cpk'yi yapay sisirir) burada TEK yerde
    ele alinir. Her yeni donusturucu (Faz 2/3: Titrasyon Asitligi, Tuz,
    Bostwick, F0) kendi gating mantigini yeniden yazmak yerine bu
    fonksiyonu cagirir - ayni koruma otomatik gelir.

    values_by_target: {parametre_adi: koprulenecek_deger} - secilebilecek
    her hedef parametre icin ayri bir deger (Gravimetrik Nem'de hedefe gore
    farkli deger; Totox gibi tek sayi ureten donusturuculerde tum hedefler
    ayni degeri paylasir).
    source_label: shift etiketinde ve basari mesajinda kullanilan kaynak adi.
    widget_key_prefix: Streamlit widget key benzersizligi icin onek.
    extra_note: basari mesajina eklenecek kaynak-ozel ek not (orn. Totox'un
    kendi referans ustsiniri ile aktif parametrenin spesifikasyonu ARASINDAKI
    farki acikliga kavusturan not).

    Faz 2 guncellemesi: values_by_target'taki bir deger artik list[float] de
    olabilir - bu, hedefin X-bar/R oldugunu ve TAM OLARAK
    st.session_state.subgroup_size kadar elemanla (gercek bir alt grup -
    ayni numunenin n kez olculmesi) koprulenecegini belirtir. Eksik/fazla
    sayida deger reddedilir (buton render edilmez) - bu, Faz 1 final
    review'in yakaladigi "X-bar/R'a n=1 alt grup eklemek Range'i sifirlar"
    bug'inin kalici cozumudur.

    UX karari (kullanicinin hangi I-MR parametresine aktaracagini SECMESI
    gerekir, sadece "su an aktif olan" varsayimina guvenilmez): tek paylasilan
    subgroups listesi mimarisi nedeniyle (ayri parametre-bazli depolama yok)
    hedef HER ZAMAN aktif parametreyle eslesmek ZORUNDADIR - ama kullanici
    niyetini acikca bir selectbox'tan SECER (varsayilani aktif parametre
    olsa bile), boylece "hangi parametreye gittigi" asla sessizce/kazara
    belirlenmez - selectbox + eslesme kontrolu KOMBINASYONU, sadece birinin
    tek basina saglayamayacagi guvenceyi verir.

    Kullanici, aktif OLMAYAN bir hedef secerse TAM OLARAK ne olur (uc
    ihtimalden - buton devre disi / aktif parametre otomatik degisir /
    yine de eklenir - HANGISI): buton hic RENDER EDILMEZ, aktif parametre
    OTOMATIK DEGISTIRILMEZ, ve subgroups'a HICBIR SEY EKLENMEZ - sadece
    st.info() ile "once Veri Girisi/Chart sekmesinden aktif parametreyi
    '{target}' yapin" mesaji gosterilip fonksiyon return ile SESSIZCE
    CIKAR (append() cagrisindan once, kod yolu oraya hic ulasmaz). Kullanici
    aktif parametreyi elle degistirmeden bu ekrandan hicbir yazma islemi
    GERCEKLESEMEZ - Faz 1 final review'in yakaladigi "sessizce yanlis
    parametreye yazma" bug'i bu nedenle yapisal olarak tekrar edemez.
    """
    target_options = list(values_by_target.keys())
    default_index = (
        target_options.index(st.session_state.active_parameter)
        if st.session_state.active_parameter in target_options
        else 0
    )
    target = st.selectbox(
        "Hangi SPC parametresine aktarılsın?",
        target_options,
        index=default_index,
        key=f"{widget_key_prefix}_target_param",
    )
    target_config = PARAMETER_CONFIG.get(target, {})
    target_is_individual = target_config.get("is_individual", False)
    target_is_active = target == st.session_state.active_parameter

    if not target_is_active:
        st.info(
            f"'{target}' şu anda aktif parametre değil. Aktarım yapabilmek için "
            f"önce Veri Girişi/Chart sekmesinden aktif parametreyi '{target}' "
            "olarak değiştirin."
        )
        return
    if not target_is_individual:
        target_values = values_by_target[target]
        if not isinstance(target_values, list):
            target_values = [target_values]
        required_n = st.session_state.subgroup_size
        if not bridge_value_count_matches(target_values, required_n):
            st.warning(
                f"'{target}' bir X-bar/R parametresidir, mevcut alt grup büyüklüğü "
                f"n={required_n}. Bu köprü tam olarak {required_n} ölçüm gerektirir "
                f"({len(target_values)} girildi) - sidebar'dan n'i değiştirin veya "
                "eksik/fazla ölçümü düzeltin."
            )
            return
        st.caption(f"Aktif parametre: {target} (X-bar/R, n={required_n})")
        if st.button(f"📌 SPC Veri Setine Aktar ({source_label})", key=f"{widget_key_prefix}_bridge_button"):
            entry = build_bridge_subgroup_entry(
                value=target_values, shift_label=f"QC Dönüştürücü - {source_label}",
            )
            st.session_state.subgroups.append(entry)
            message = (
                f"{source_label} değeri SPC veri setine eklendi "
                f"({target}, X-bar/R, n={required_n})."
            )
            if extra_note:
                message += " " + extra_note
            st.success(message)
        return

    imr_value = values_by_target[target]
    if not bridge_value_is_single(imr_value):
        st.warning(
            f"'{target}' bir I-MR parametresidir - bu köprü tek bir ölçüm bekler, "
            f"birden fazla değer köprülenemez ({len(imr_value)} değer verildi)."
        )
        return
    if isinstance(imr_value, list):
        imr_value = imr_value[0]

    st.caption(f"Aktif parametre: {target} (I-MR)")
    if st.button(f"📌 SPC Veri Setine Aktar ({source_label})", key=f"{widget_key_prefix}_bridge_button"):
        entry = build_bridge_subgroup_entry(
            value=imr_value, shift_label=f"QC Dönüştürücü - {source_label}",
        )
        st.session_state.subgroups.append(entry)
        message = f"{source_label} değeri SPC veri setine eklendi ({target}, I-MR)."
        if extra_note:
            message += " " + extra_note
        st.success(message)


with tab_calc:
    st.markdown("### ⚖️ Gravimetrik Nem / Kuru Madde")
    st.caption("AOAC 925.10 yöntemi: dara + yaş numune + kuru kalıntı ağırlığından hesaplar.")

    col_g1, col_g2, col_g3 = st.columns(3)
    with col_g1:
        dish_tare = st.number_input("Kap darası (g)", min_value=0.0, value=25.000, step=0.001, format="%.3f", key="qc_moisture_tare")
    with col_g2:
        wet_with_dish = st.number_input("Kap + yaş numune (g)", min_value=0.0, value=30.000, step=0.001, format="%.3f", key="qc_moisture_wet")
    with col_g3:
        dry_with_dish = st.number_input("Kap + kuru kalıntı (g)", min_value=0.0, value=29.400, step=0.001, format="%.3f", key="qc_moisture_dry")

    try:
        moisture_result = gravimetric_moisture(dish_tare, wet_with_dish, dry_with_dish)
        col_r1, col_r2 = st.columns(2)
        col_r1.metric("Nem (%)", f"{moisture_result['moisture_pct']:.2f}")
        col_r2.metric("Kuru Madde (%)", f"{moisture_result['dry_matter_pct']:.2f}")

        render_bridge_widget(
            values_by_target={
                "Nem/Rutubet": moisture_result["moisture_pct"],
                "Kuru Madde": moisture_result["dry_matter_pct"],
            },
            source_label="Gravimetrik Nem/Kuru Madde",
            widget_key_prefix="qc_moisture",
        )
    except ValueError as exc:
        st.error(f"Girdi hatası: {exc}")

    st.divider()

    st.markdown("### 🧪 Titre Edilebilir Asitlik")
    st.caption(
        "AOAC yöntemi: titre hacmi + normalite + asit faktörü + numune "
        "miktarından % asitlik hesaplar. Titrasyon Asitliği X-bar/R "
        "parametresi olduğu için, aktif alt grup büyüklüğü (n) kadar "
        "tekrar ölçüm gerekir - aynı numunenin n kez titre edilmesi gibi."
    )

    col_ta1, col_ta2, col_ta3 = st.columns(3)
    with col_ta1:
        ta_acid_choice = st.selectbox(
            "Baskın asit", list(TITRATABLE_ACID_MEQ_FACTORS.keys()), key="qc_ta_acid_choice",
        )
    ta_acid_factor = TITRATABLE_ACID_MEQ_FACTORS[ta_acid_choice]
    with col_ta2:
        if ta_acid_factor is None:
            ta_acid_factor = st.number_input(
                "Özel asit faktörü (g/meq)", min_value=0.0001, value=0.0640,
                step=0.0001, format="%.4f", key="qc_ta_custom_factor",
            )
        else:
            st.metric("Asit faktörü (g/meq)", f"{ta_acid_factor:.4f}")
    with col_ta3:
        ta_normality = st.number_input(
            "Titrant normalitesi (N)", min_value=0.0001, value=0.1,
            step=0.01, format="%.3f", key="qc_ta_normality",
        )

    ta_sample_size = st.number_input(
        "Numune miktarı (mL)", min_value=0.0001, value=10.0, step=0.1, key="qc_ta_sample_size",
    )

    ta_n = st.session_state.subgroup_size
    st.caption(f"Alt grup büyüklüğü n={ta_n} (sidebar'dan değiştirilebilir) - {ta_n} adet titrasyon tekrarı girin.")

    ta_values = []
    ta_error = None
    ta_cols = st.columns(ta_n)
    for _ta_i, _ta_col in enumerate(ta_cols):
        with _ta_col:
            _ta_vol = st.number_input(
                f"Titre hacmi #{_ta_i + 1} (mL)", min_value=0.0, value=9.2,
                step=0.1, key=f"qc_ta_volume_{_ta_i}",
            )
            try:
                _ta_result = titratable_acidity(_ta_vol, ta_normality, ta_acid_factor, ta_sample_size)
                ta_values.append(_ta_result["acidity_pct"])
            except ValueError as exc:
                ta_error = str(exc)

    if ta_error:
        st.error(f"Girdi hatası: {ta_error}")
    else:
        st.write(
            "Hesaplanan % asitlik değerleri: "
            + ", ".join(f"{v:.3f}" for v in ta_values)
        )
        render_bridge_widget(
            values_by_target={"Titrasyon Asitligi": ta_values},
            source_label="Titre Edilebilir Asitlik",
            widget_key_prefix="qc_ta",
        )

    st.divider()

    st.markdown("### 🧂 Tuz (Mohr Metodu)")
    st.caption(
        "AgNO₃ titrasyonu ile klorür tayini, %NaCl olarak raporlanır. "
        "Tuz/NaCl X-bar/R parametresi olduğu için aktif alt grup büyüklüğü "
        "(n) kadar tekrar ölçüm gerekir."
    )

    col_salt1, col_salt2 = st.columns(2)
    with col_salt1:
        salt_normality = st.number_input(
            "AgNO₃ normalitesi (N)", min_value=0.0001, value=0.1,
            step=0.01, format="%.3f", key="qc_salt_normality",
        )
    with col_salt2:
        salt_sample_size = st.number_input(
            "Numune miktarı (g)", min_value=0.0001, value=10.0, step=0.1, key="qc_salt_sample_size",
        )

    salt_n = st.session_state.subgroup_size
    st.caption(f"Alt grup büyüklüğü n={salt_n} (sidebar'dan değiştirilebilir) - {salt_n} adet titrasyon tekrarı girin.")

    salt_values = []
    salt_error = None
    salt_cols = st.columns(salt_n)
    for _salt_i, _salt_col in enumerate(salt_cols):
        with _salt_col:
            _salt_vol = st.number_input(
                f"AgNO₃ hacmi #{_salt_i + 1} (mL)", min_value=0.0, value=12.0,
                step=0.1, key=f"qc_salt_volume_{_salt_i}",
            )
            try:
                _salt_result = salt_content_mohr(_salt_vol, salt_normality, salt_sample_size)
                salt_values.append(_salt_result["salt_pct"])
            except ValueError as exc:
                salt_error = str(exc)

    if salt_error:
        st.error(f"Girdi hatası: {salt_error}")
    else:
        st.write(
            "Hesaplanan % NaCl değerleri: "
            + ", ".join(f"{v:.3f}" for v in salt_values)
        )
        render_bridge_widget(
            values_by_target={"Tuz/NaCl": salt_values},
            source_label="Tuz (Mohr Metodu)",
            widget_key_prefix="qc_salt",
        )

    st.divider()

    st.markdown("### 🌡️ Termal Letalite (F₀)")
    st.caption(
        "Bigelow/Ball formülü: F₀ = Δt × Σ 10^((T-121.1)/10). Retort/proses "
        "sırasında eşit aralıklarla okunan sıcaklık değerlerinden hesaplar. "
        f"Kaynak (LSL): {F0_BRIDGE_PARAMETER_CONFIG['method_source']} — "
        "sektör pratiğinde genellikle ek güvenlik payı için 6-8 dk hedeflenir "
        "(bu tek bir 'doğru' hedef değil, LSL=3.0 dk resmi minimumdur)."
    )

    col_f0_1, col_f0_2 = st.columns(2)
    with col_f0_1:
        f0_delta_t = st.number_input(
            "Okumalar arası zaman aralığı Δt (dk)", min_value=0.0001, value=1.0,
            step=0.1, key="qc_f0_delta_t",
        )
    with col_f0_2:
        f0_reading_count = st.number_input(
            "Sıcaklık okuma sayısı", min_value=2, max_value=60, value=7,
            step=1, key="qc_f0_reading_count",
        )

    st.caption(f"{f0_reading_count} adet sıcaklık okuması girin (zaman sırasına göre):")
    f0_temps = []
    f0_cols = st.columns(min(f0_reading_count, 10))
    for _f0_i in range(f0_reading_count):
        with f0_cols[_f0_i % len(f0_cols)]:
            _f0_t = st.number_input(
                f"T{_f0_i + 1} (°C)", min_value=0.0, max_value=200.0, value=121.1,
                step=0.1, key=f"qc_f0_temp_{_f0_i}",
            )
            f0_temps.append(_f0_t)

    try:
        f0_result = thermal_lethality_f0(temperatures_c=f0_temps, delta_t_minutes=f0_delta_t)
        f0_value = f0_result["f0_minutes"]
        st.metric("Hesaplanan F₀ (dk)", f"{f0_value:.2f}")
        f0_lsl = F0_BRIDGE_PARAMETER_CONFIG["default_lsl"]
        if f0_value < f0_lsl:
            st.warning(f"F₀={f0_value:.2f} dk, FDA minimum LSL'in ({f0_lsl} dk) ALTINDA.")
        else:
            st.success(f"F₀={f0_value:.2f} dk, FDA minimum LSL'i ({f0_lsl} dk) karşılıyor.")

        # Totox koprusuyle AYNI mimari desen: F0'in kendi ayri bir
        # PARAMETER_CONFIG kaydi olmadigi icin (bkz. F0_BRIDGE_PARAMETER_CONFIG
        # notu, constants.py) hedef, uygulamadaki TUM I-MR parametreleri
        # arasindan acikca secilir - mevcut Viskozite parametresine OZEL
        # olarak baglanmaz (Faz 3 kapsam karari).
        _f0_individual_params = sorted(
            p for p, cfg in PARAMETER_CONFIG.items() if cfg.get("is_individual", False)
        )
        render_bridge_widget(
            values_by_target=dict.fromkeys(_f0_individual_params, f0_value),
            source_label="Termal Letalite (F₀)",
            widget_key_prefix="qc_f0",
            extra_note=(
                "Not: bu köprü sadece I-MR zaman serisine ham değer kaydeder; "
                "grafik/Cpk hesaplaması seçilen parametrenin kendi LSL/USL "
                "spesifikasyonunu kullanır, F₀'ın FDA referans alt sınırı "
                f"({F0_BRIDGE_PARAMETER_CONFIG['default_lsl']} dk) sadece bilgi "
                "amaçlıdır."
            ),
        )
    except ValueError as exc:
        st.error(f"Girdi hatası: {exc}")

    st.divider()

    with st.container(border=True, key="card-24"):
        st.subheader("Totox Hesaplayici")
        st.caption(
            "Bu bir SPC kontrol grafigi degildir - tek seferlik bir hesap "
            "makinesidir, mevcut veri girisi/chart akisindan bagimsizdir ve "
            "onu etkilemez."
        )
        st.latex(r"Totox = 2 \times PV + AnV")

        with st.expander("\U0001F3F7️ Kaynaklar"):
            st.caption(
                "Kaynak: Schaal firin testi standardi (Wan, 1995). "
                f"Referans araligi (AnV<{TOTOX_ANV_LIMIT:.0f}, Totox<{TOTOX_LIMIT:.0f}) "
                "GOED/CRN (Global Organization for EPA and DHA Omega-3s / Council for "
                "Responsible Nutrition) sektor pratigidir - Turk Gida Kodeksi'nin "
                "dogrudan bir hukmu DEGILDIR."
            )

        tc1, tc2 = st.columns(2)
        with tc1:
            totox_peroxide = st.number_input(
                "Peroksit Degeri - PV (meq O2/kg)", min_value=0.0, value=5.0,
                step=0.1, format="%.2f", key="totox_peroxide",
                help=(
                    "Yaglarda BIRINCIL oksidasyon urunlerinin (hidroperoksitler) "
                    "olcusudur - oksidasyonun erken evresini yansitir. Deger ne "
                    "kadar dusukse yag o kadar taze/stabildir."
                ),
            )
        with tc2:
            totox_anisidine = st.number_input(
                "Anisidin Degeri - AnV", min_value=0.0, value=3.0,
                step=0.1, format="%.2f", key="totox_anisidine",
                help=(
                    "IKINCIL oksidasyon urunlerinin (hidroperoksitlerin bozunmasiyla "
                    "olusan aldehitler) olcusudur. PV'nin aksine ISIL ISLEME "
                    "dayaniklidir - bu yuzden kizartma/rafinasyon gibi islemlerden "
                    "sonra bile yagin oksidasyon GECMISINI gostermeye devam eder."
                ),
            )

        totox_value = 2 * totox_peroxide + totox_anisidine
        anv_ok = totox_anisidine < TOTOX_ANV_LIMIT
        totox_ok = totox_value < TOTOX_LIMIT
        totox_in_range = anv_ok and totox_ok

        # Birlesik gauge + renkli badge - ayri bir KPI karti/badge yerine TEK
        # gorsel (bkz. render_totox_gauge docstring'i): renk hem gauge
        # cubugunda hem badge'de AYNI anda uygun/sinir disi durumunu tasir.
        badge_bg, badge_fg, badge_icon, badge_text = (
            ("#ebfbee", "#2f9e44", "✅", "GOED/CRN referans araliginda")
            if totox_in_range else
            ("#fff0f0", "#e03131", "⚠️", "GOED/CRN referans araligi disinda")
        )
        st.markdown(
            f"<div style='background:{badge_bg}; color:{badge_fg}; font-weight:600; "
            f"border-radius:6px; padding:0.5rem 0.7rem;'>{badge_icon} {badge_text}</div>",
            unsafe_allow_html=True,
        )
        gauge_fig = render_totox_gauge(totox_value, TOTOX_LIMIT, dark)
        st.pyplot(gauge_fig, use_container_width=True)
        plt.close(gauge_fig)

        st.caption(build_totox_comment(totox_value, totox_anisidine, TOTOX_LIMIT, TOTOX_ANV_LIMIT))

        st.dataframe(
            {
                "Olcum": ["PV (meq O2/kg)", "AnV", "Totox", "Referans"],
                "Deger": [
                    f"{totox_peroxide:.2f}", f"{totox_anisidine:.2f}", f"{totox_value:.2f}",
                    f"AnV<{TOTOX_ANV_LIMIT:.0f}, Totox<{TOTOX_LIMIT:.0f}",
                ],
            },
            hide_index=True, use_container_width=True,
        )

        with st.expander("\U0001F9EE Hesaplama adimlarini goster"):
            st.markdown(
                f"Totox = 2 × PV + AnV = 2 × {totox_peroxide:.2f} + {totox_anisidine:.2f} "
                f"= **{totox_value:.2f}**  \n"
                f"AnV kontrolu: {totox_anisidine:.2f} {'<' if anv_ok else '≥'} "
                f"{TOTOX_ANV_LIMIT:.0f} → **{'uygun' if anv_ok else 'sinir disi'}**  \n"
                f"Totox kontrolu: {totox_value:.2f} {'<' if totox_ok else '≥'} "
                f"{TOTOX_LIMIT:.0f} → **{'uygun' if totox_ok else 'sinir disi'}**"
            )

        # Session history - v2.0'daki KALICI depolamadan ONCE, sadece bu
        # oturuma ozel gecici bir liste (sayfa yenilenince/kapatilinca
        # silinir) - bu acikca belirtilir, kalici bir kayit sistemi gibi
        # YANLIS bir izlenim verilmez.
        if "totox_history" not in st.session_state:
            st.session_state.totox_history = []
        hist_col1, hist_col2 = st.columns([3, 1])
        with hist_col2:
            if st.button("\U0001F4CC Sonucu gecmise ekle", key="totox_add_history"):
                st.session_state.totox_history.append({
                    "Zaman": datetime.now().strftime("%H:%M:%S"),
                    "PV": round(totox_peroxide, 2),
                    "AnV": round(totox_anisidine, 2),
                    "Totox": round(totox_value, 2),
                    "Durum": "Uygun" if totox_in_range else "Sinir disi",
                })
        if st.session_state.totox_history:
            with hist_col1:
                st.caption(
                    "⚠️ Bu gecmis SADECE bu oturuma ozeldir - sayfa yenilenince/"
                    "kapatilinca silinir (kalici depolama v2.0'da eklenecek)."
                )
            st.dataframe(st.session_state.totox_history, hide_index=True, use_container_width=True)

        # Bilinclı, kullanici tetikli bir istisna: Totox sekmesi normalde
        # session_state.subgroups'a DOKUNMAZ (sekme izolasyon politikasi),
        # ancak kullanici asagidaki paylasilan render_bridge_widget()
        # araciligiyla Totox degerini SPC I-MR veri setine ham deger olarak
        # koprulemeyi acikca talep edebilir. Totox'un kendi ayri bir
        # PARAMETER_CONFIG kaydi olmadigi icin (bkz. yukaridaki
        # TOTOX_BRIDGE_PARAMETER_CONFIG notu) hedef, uygulamadaki TUM I-MR
        # parametreleri arasindan acikca secilir - "su an hangisi aktifse
        # o" varsayimina guvenilmez (Faz 1 final review bulgusu).
        _totox_individual_params = sorted(
            p for p, cfg in PARAMETER_CONFIG.items() if cfg.get("is_individual", False)
        )
        render_bridge_widget(
            values_by_target=dict.fromkeys(_totox_individual_params, totox_value),
            source_label="Totox",
            widget_key_prefix="qc_totox",
            extra_note=(
                "Not: bu köprü sadece I-MR zaman serisine ham değer kaydeder; "
                "grafik/Cpk hesaplaması seçilen parametrenin kendi LSL/USL "
                "spesifikasyonunu kullanır, Totox'un referans üst sınırı "
                f"({TOTOX_BRIDGE_PARAMETER_CONFIG['default_usl']} meq O2/kg) sadece "
                "bilgi amaçlıdır."
            ),
        )

    # v1.2 Madde 9: Kontrol limiti manuel hesaplayici. Totox/Gravimetrik Nem
    # panellerindeki gated kopru butonlarinin aksine, bu hesaplayici
    # session_state.subgroups'a DOKUNMAZ - mevcut compute_xbar_r_limits/
    # compute_imr_limits fonksiyonlarini dogrudan cagirir (YENI bir formul
    # YOK, dolayisiyla Method Validation gerekmez - bkz. METHODOLOGY.md v1.2
    # plani, Madde 9 notu).
    with st.container(border=True, key="card-26"):
        st.subheader("Kontrol Limiti Hesaplayici")
        st.caption(
            "Elinizde zaten hesaplanmis x̿/R̄ (veya x̄/MR̄) varsa, veri girmeden "
            "dogrudan UCL/LCL degerlerini hesaplayin. Bu, uygulamanin kendi "
            "grafik akisiyla AYNI formulleri kullanir - ayri/yeni bir formul "
            "degildir, sadece tek seferlik bir hesap makinesidir."
        )

        limit_mode = st.radio(
            "Grafik turu", ["X-bar / R (alt grup)", "I-MR (tekli olcum)"],
            key="limit_calc_mode", horizontal=True,
        )

        if limit_mode == "X-bar / R (alt grup)":
            lc1, lc2, lc3 = st.columns(3)
            with lc1:
                lc_xbb = st.number_input(
                    "Genel ortalama (x̿)", value=7.0, step=0.01, format="%.4f",
                    key="limit_calc_xbb",
                )
            with lc2:
                lc_rbar = st.number_input(
                    "Ortalama alt grup araligi (R̄)", value=0.1, min_value=0.0,
                    step=0.01, format="%.4f", key="limit_calc_rbar",
                )
            with lc3:
                lc_n = st.selectbox(
                    "Alt grup buyuklugu (n)", sorted(CONTROL_CHART_CONSTANTS.keys()),
                    index=1, key="limit_calc_n",
                )
            limits = compute_xbar_r_limits(lc_xbb, lc_rbar, lc_n)
            res1, res2 = st.columns(2)
            with res1:
                st.metric("X-bar UCL", f"{limits.ucl_x:.4f}")
                st.metric("X-bar LCL", f"{limits.lcl_x:.4f}")
            with res2:
                st.metric("R UCL", f"{limits.ucl_r:.4f}")
                st.metric("R LCL", f"{limits.lcl_r:.4f}")
            with st.expander("\U0001F9EE Hesaplama adimlarini goster"):
                st.markdown(
                    f"A2={limits.a2}, D3={limits.d3}, D4={limits.d4} (n={lc_n})  \n"
                    f"X-bar UCL/LCL = x̿ ± A2 × R̄ = {lc_xbb:.4f} ± {limits.a2} × {lc_rbar:.4f} "
                    f"= **{limits.ucl_x:.4f}** / **{limits.lcl_x:.4f}**  \n"
                    f"R UCL = D4 × R̄ = {limits.d4} × {lc_rbar:.4f} = **{limits.ucl_r:.4f}**  \n"
                    f"R LCL = D3 × R̄ = {limits.d3} × {lc_rbar:.4f} = **{limits.lcl_r:.4f}**"
                )
        else:
            lc1, lc2 = st.columns(2)
            with lc1:
                lc_xbar = st.number_input(
                    "Genel ortalama (x̄)", value=100.0, step=0.01, format="%.4f",
                    key="limit_calc_xbar",
                )
            with lc2:
                lc_mrbar = st.number_input(
                    "Ortalama hareketli aralik (MR̄)", value=2.0, min_value=0.0,
                    step=0.01, format="%.4f", key="limit_calc_mrbar",
                )
            limits = compute_imr_limits(lc_xbar, lc_mrbar)
            res1, res2 = st.columns(2)
            with res1:
                st.metric("I UCL", f"{limits.ucl_i:.4f}")
                st.metric("I LCL", f"{limits.lcl_i:.4f}")
            with res2:
                st.metric("MR UCL", f"{limits.ucl_mr:.4f}")
                st.metric("MR LCL", f"{limits.lcl_mr:.4f}")
            with st.expander("\U0001F9EE Hesaplama adimlarini goster"):
                st.markdown(
                    f"I UCL/LCL = x̄ ± 2.66 × MR̄ = {lc_xbar:.4f} ± {I_CHART_CONSTANT} × "
                    f"{lc_mrbar:.4f} = **{limits.ucl_i:.4f}** / **{limits.lcl_i:.4f}**  \n"
                    f"MR UCL = {MR_CHART_D4} × MR̄ = {MR_CHART_D4} × {lc_mrbar:.4f} "
                    f"= **{limits.ucl_mr:.4f}**  \n"
                    f"MR LCL = 0 (sabit)"
                )

# ---------------------------------------------------------------------------
# SEKME 4: Hakkinda
# ---------------------------------------------------------------------------
with tab_about:
    with st.container(border=True, key="card-25"):
        st.subheader("SPC FoodLab hakkinda")
        st.markdown(
            """
Gida uretim hatlarinda pH, Brix, aw (su aktivitesi) veya viskozite
olcumlerinden **istatistiksel proses kontrolu (SPC)** grafigi ve **surec
yeterlilik analizi (Cpk)** ureten bir arac.

**Kullanilan formuller (X-bar/R - pH, Brix, aw):**
- X-bar UCL/LCL: `x̄̄ ± A2 × R̄`
- R chart UCL/LCL: `D4 × R̄` / `D3 × R̄`
- Cpk (iki tarafli, pH/Brix): `min[(USL - x̄̄)/(3σ̂), (x̄̄ - LSL)/(3σ̂)]`, `σ̂ = R̄/d2`
- Cpu (tek tarafli, aw): `(USL - x̄̄)/(3σ̂)` - LSL yok sayilir

**Kullanilan formuller (I-MR - Viskozite):**
- I chart UCL/LCL: `x̄ ± 2.66 × MR̄`
- MR chart UCL/LCL: `3.267 × MR̄` / `0`
- σ̂ = MR̄/d2 (d2=1.128, n=2 sabiti) - Cpk/Cpu ayni formulle, sadece σ̂ farkli hesaplanir

Bu formuller ve A2/D3/D4/d2 sabit tablosu parametreden bagimsizdir - degisen
sadece olcum birimi, urun spesifikasyon tablosu ve aw icin tek/iki tarafli Cpk
secimidir. Alt grup buyuklugu (n) sidebar'dan secilebilir (varsayilan n=4,
aralik n=2-10); n degistiginde A2/D3/D4/d2 sabitleri de otomatik guncellenir.

**X-bar/R ile I-MR arasindaki temel fark:** X-bar/R'de bir **alt grup**
kavrami vardir (orn. vardiya basina 4 olcum) - kontrol limitleri alt grup
ORTALAMALARININ ve alt grup ARALIKLARININ (range) varyasyonuna dayanir. I-MR'de
alt grup YOKTUR; viskozite gibi bazi parametreler her seferinde tek bir deger
olarak olculur. Bu durumda "range" yerine ardisik iki olcum arasindaki fark
(**moving range**, MR_i = |x_i - x_(i-1)|) kullanilir ve kontrol limitleri
buna gore hesaplanir. I chart'in merkez sabiti (2.66) bu yuzden X-bar
chart'in A2 sabitinden (n=2 icin 1.880) farklidir - farkli bir varyasyon
kaynagini (ardisik fark vs alt grup ortalamasi) modelledigi icin.

**Neden aw'de tek tarafli Cpk:** aw'de yalnizca ust limit (USL) mikrobiyal
guvenlik acisindan anlamlidir ("aw belirli bir degeri gecmesin"); alt limit
cogu urun icin tanimsizdir. Iki tarafli Cpk formulu boyle bir durumda LSL
icin anlamsiz bir Cpl degeri uretip surec yeterliligini yanlis yansitir; bu
yuzden aw secildiginde sadece Cpu hesaplanir.

**Baseline mantigi:** Kontrol limitleri, "Baseline'i hesapla ve dondur"
butonuyla o ana kadar girilen verilerden bir kez hesaplanip sabitlenir.
Bu sayede sonradan eklenen (ozellikle kontrol disi) noktalar limitleri
kendine dogru cekmez - SPC'de limitlerin bir baseline donemden turetilip
sabit tutulmasi gerektigi icin bu mekanizma eklendi.

**Parametre degisimi:** Farkli parametrelerin (pH, Brix, aw, viskozite)
verileri ayni oturumda karismasin diye, sidebar'dan parametre degistirmek
mevcut veriyi siler (onay istenir).

Detayli kaynak ve dogrulama notlari icin bkz. README.
            """
        )

    # v1.2 Madde 10: Metodolojik SSS - Nelson kurallari ve OOS/OOT ayrimi
    # kullanicinin kafasini karistirabilecek iki yeni kavram (v1.2 ile
    # eklendi); statik aciklama, yeni bir formul/mantik icermiyor.
    with st.container(border=True, key="card-27"):
        st.subheader("Metodolojik SSS")
        st.caption(
            "Nelson kurallari ve OOS/OOT ayrimi, v1.2 ile eklenen ve ilk "
            "bakista kafa karistirabilecek iki kavram - bu bolum onlari "
            "aciklar."
        )

        with st.expander("Nelson kurallari nedir, UCL/LCL asimi yetmiyor mu?"):
            st.markdown(
                "UCL/LCL asimi, surecin ANLIK olarak kontrolden ciktigini "
                "gosterir (tek bir nokta 3σ disina cikmis). Ama bir surec "
                "hicbir zaman UCL/LCL'yi asmadan da SISTEMATIK bir kaymaya "
                "girebilir - orn. 9 ardisik nokta merkez cizginin ayni "
                "tarafinda kalirsa, hicbiri limiti asmasa da bu istatistiksel "
                "olarak 'rastgele degil' demektir (Nelson, 1984). Bu "
                "uygulama UCL/LCL asiminin YANI SIRA 3 Nelson kuralini da "
                "kontrol eder: Test 5 (2/3 nokta 2σ disinda, ayni yonde), "
                "Test 6 (4/5 nokta 1σ disinda, ayni yonde), Test 2 (9 "
                "ardisik nokta merkez cizginin ayni tarafinda)."
            )

        with st.expander("OOS ve OOT ne fark eder?"):
            st.markdown(
                "**OOS (Out of Specification):** Ham bir olcumun urunun "
                "spesifikasyon araligi (LSL/USL) DISINA cikmasi - musteri/"
                "regulasyon acisindan tanimlanan sinirdir, SPC'den "
                "BAGIMSIZDIR (spesifikasyon degismedigi surece hep aynidir). "
                "\n\n"
                "**OOT (Out of Trend):** Bir alt grubun/noktanin kontrol "
                "limitlerini (UCL/LCL) asmasi VEYA bir Nelson kuralini "
                "tetiklemesi - surecin ISTATISTIKSEL olarak beklenmedik "
                "davrandigini gosterir, spesifikasyondan BAGIMSIZDIR (surec "
                "ortalamasina ve varyasyonuna gore hesaplanir). "
                "\n\n"
                "Bu ikisi **birbirinden bagimsizdir**: bir nokta OOS olup "
                "OOT olmayabilir (spesifikasyon disi ama surecin normal "
                "varyasyonu icinde), OOT olup OOS olmayabilir (surec "
                "istatistiksel olarak beklenmedik ama hala spesifikasyon "
                "icinde) - ya da ikisi birden olabilir. Uygulama bu ikisini "
                "AYRI AYRI raporlar, tek bir 'kontrol disi' sayisinda "
                "birlestirmez."
            )

        with st.expander("Normallik testi (Shapiro-Wilk) beni engelliyor mu?"):
            st.markdown(
                "Hayir. Cpk/Ppk formulleri verinin yaklasik normal dagildigi "
                "varsayimina dayanir; Shapiro-Wilk testi bu varsayimin ne "
                "kadar gecerli oldugunu SEFFAF bir sekilde gosterir (p<0.05 "
                "ise 'veri normal dagilimdan sapiyor olabilir' uyarisi). "
                "Bu bir KAPI degildir - sonuc normal cikmasa bile Cpk/Ppk "
                "hesaplanmaya ve gosterilmeye devam eder, sadece yorumlarken "
                "dikkatli olunmasi gerektigi belirtilir."
            )

        with st.expander("Ppk, Cpk'dan farkli bir sey mi?"):
            st.markdown(
                "Ikisi de ayni USL/LSL formulunu kullanir, tek fark σ̂'in "
                "nasil hesaplandigidir. **Cpk** kisa vadeli tahmini "
                "(R̄/d2 veya MR̄/d2) kullanir - alt gruplar ARASI degil, alt "
                "grup ICI varyasyonu yansitir. **Ppk** tum ham verinin genel "
                "(N-1 duzeltmeli) standart sapmasini kullanir - hem alt grup "
                "ici hem alt gruplar arasi varyasyonu icerir. Ppk, Cpk'dan "
                "belirgin sekilde dusukse, surec zaman icinde kaymis/"
                "kaymakta olabilir demektir - kisa vadede 'iyi' gorunen bir "
                "surec uzun vadede kayabilir."
            )

# ---------------------------------------------------------------------------
# FOOTER - tum sekmelerin altinda, her zaman gorunur (with tab_x: bloklarinin
# disinda oldugu icin hangi sekme secili olursa olsun sayfanin en altinda kalir)
# ---------------------------------------------------------------------------
st.divider()
st.caption(f"SPC FoodLab v1.7 · [GitHub]({GITHUB_URL})")
