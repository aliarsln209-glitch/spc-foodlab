"""SPC FoodLab - pH/Brix/Aw/Viskozite Istatistiksel Proses Kontrolu (Streamlit MVP)."""

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
    MAX_SUBGROUP_SIZE,
    MIN_SUBGROUP_SIZE,
    PARAMETER_CONFIG,
    PARAMETER_DESCRIPTIONS,
    PARAMETER_INFO,
    PARAMETER_SOURCES,
    RAW_MATERIAL_PREFIX,
    RAW_MATERIAL_QC_REFERENCE,
    SHIFT_OPTIONS,
)
from demo_data import generate_demo_individual, generate_demo_subgroups
from pdf_report import build_pdf_report
from result_helpers import (
    build_quick_summary,
    compute_trend,
    demo_scenario_targets,
    format_cpk,
    get_cpk_level,
)
from spc_core import (
    I_CHART_CONSTANT,
    MR_CHART_D2,
    MR_CHART_D4,
    compute_cpk,
    compute_imr_limits,
    compute_moving_ranges,
    compute_xbar_r_limits,
    is_spec_valid,
)

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


# "Vazgec" ile parametre secici radyo'yu eski degerine dondurmek icin: bu,
# radio widget'i BU RUN'DA ZATEN olusturulmadan once yapilmali (Streamlit,
# bir widget'in session_state degerini o widget instantiate edildikten sonra
# degistirmeye izin vermiyor). Bu yuzden reset islemini bir onceki run'da
# birakilan bayrakla, widget'tan once burada uyguluyoruz.
if st.session_state.pop("_reset_parameter_radio", False):
    st.session_state.parameter_radio = st.session_state.active_parameter
# Ayni sekilde n secici icin: iptal edildiginde widget'i eski degere dondurur
# (widget instantiate edilmeden ONCE yapilmali - bkz. yukaridaki aciklama).
if st.session_state.pop("_reset_subgroup_n_input", False):
    st.session_state.subgroup_size_input = st.session_state.subgroup_size

with st.sidebar:
    st.subheader("Ayarlar")

    param_options = list(PARAMETER_CONFIG.keys())
    selected_param_radio = st.radio(
        "Parametre", param_options,
        index=param_options.index(st.session_state.active_parameter),
        key="parameter_radio",
        captions=[PARAMETER_DESCRIPTIONS.get(p, "") for p in param_options],
    )

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
                    st.rerun()
            with pc2:
                if st.button("Vazgec", key="param_switch_no"):
                    st.session_state._reset_parameter_radio = True
                    st.rerun()
        else:
            st.session_state.active_parameter = selected_param_radio
            reset_parameter_scoped_state()
            st.rerun()

    st.divider()
    chart_theme = st.selectbox("Tema (grafik + arayuz)", ["Acik", "Koyu"], key="chart_theme")
    accent_color = st.color_picker(
        "Vurgu rengi", value=st.session_state.get("accent_color", "#4c6ef5"),
        key="accent_color",
        help="Butonlar ve KPI kartlarindaki vurgu rengini degistirir (basari/uyari/hata renkleri sabit kalir).",
    )

dark = chart_theme == "Koyu"
param_config = PARAMETER_CONFIG[st.session_state.active_parameter]
unit = param_config["unit"]
# Laboratuvar cihazinin gercek olcum hassasiyetini yansitir (orn. pH metre
# 2 basamak verirken ekranda 4.5512344 gostermek sahte kesinlik olur) -
# tum grafik etiketi/tablo/Cpk-adim gosterimi buna gore yuvarlanir.
decimal_places = param_config["decimal_places"]
is_individual = param_config.get("is_individual", False)  # True: I-MR (alt grup yok), False: X-bar/R

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


def inject_theme_css(dark: bool, accent: str) -> None:
    """Secilen acik/koyu temayi + vurgu rengini grafiklerin otesinde tum
    arayuze (sidebar, kartlar, metrikler, uyari kutulari) uygular. Streamlit'in
    kendi config.toml temasi Community Cloud'da calisma anindan
    degistirilemedigi icin bu, custom CSS injection ile yapiliyor.

    Ayrica hafif (agir olmayan) hover/gecis animasyonlari icerir - buton
    hover'da kucuk buyume, karti gecisi, uyari kutularinda fade-in. Amac
    sadece arayuzu biraz daha 'canli' hissettirmek, dikkat dagitmamak."""
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
        [data-testid="stSidebar"] { background-color: #161a23 !important; }
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
    {theme_css}

    /* Vurgu rengi (kullanici secimi) - primary butonlar + slider */
    button[kind="primary"] {{
        background-color: {accent} !important;
        border-color: {accent} !important;
    }}
    [data-testid="stSlider"] div[role="slider"] {{ background-color: {accent} !important; }}
    a {{ color: {accent}; }}

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


inject_theme_css(dark, accent_color)

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


def render_cpk_message(cpk: float, cpk_label: str) -> None:
    """Cpk/Cpu degerine gore uygun basari/uyari/hata mesajini gosterir.
    Iki yerde (X-bar/R ve I-MR) aynen kullanilir, tekrar onlemek icin
    ortak fonksiyon haline getirildi."""
    if cpk == float("inf"):
        st.success(
            f"{cpk_label} = ∞: olculen degerlerde hic varyasyon yok (R̄/MR̄ = 0) "
            "ve ortalama spesifikasyon icinde - surec kusursuz (Mukemmel)."
        )
    elif cpk == float("-inf"):
        st.error(
            f"{cpk_label} = -∞: olculen degerlerde varyasyon yok ama ortalama "
            "zaten spesifikasyon disinda - surec yeterli degil (Yetersiz)."
        )
    elif abs(cpk) > CPK_SANITY_THRESHOLD:
        st.warning(
            f"{cpk_label} anlamsiz derecede yuksek/dusuk cikti. Sectigin "
            "urunun spesifikasyon araligi, girdigin verilerle ortusmuyor "
            "olabilir - LSL/USL degerlerini kontrol et."
        )
    elif cpk < 1.0:
        st.error(f"{cpk_label} < 1.0: Surec yeterli degil (Yetersiz), spesifikasyon limitlerine gore.")
    elif cpk < 1.33:
        st.warning(f"{cpk_label} 1.0-1.33 arasi: Surec sinirda duzeyde yeterli (Sinirda).")
    else:
        st.success(f"{cpk_label} >= 1.33: Surec yeterli (Yeterli).")


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
                         chart_png_bytes: bytes | None, key: str) -> None:
    """'PDF olarak indir' butonu - build_pdf_report() ile ayni verilerden
    tek sayfalik bir rapor uretir."""
    pdf_bytes = build_pdf_report(
        parameter, product, chart_type_label, n_samples, n_out_of_control,
        cpk, cpk_label, quick_summary_text, chart_png_bytes,
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


def render_kpi_panel(unit: str, center_value: float, cpk: float, cpk_label: str,
                      n_samples: int, n_out_of_control: int, decimal_places: int,
                      trend: tuple[str, float] | None = None, cpk_valid: bool = True) -> None:
    """Chart'tan once gosterilen 4'lu hizli ozet paneli - detayli karti
    tekrar etmez, sadece en onemli 4 sayiyi renkli kart + ikon + (Cpk
    kartinda) sonuc rozeti + (Ortalama kartinda, varsa) trend okuyla one
    cikarir. trend, compute_trend()'in donusu: (yon, delta) veya None.

    cpk_valid=False (LSL>=USL gecersiz spesifikasyon) durumunda Cpk karti
    gercek sayiyi/rozeti GOSTERMEZ - get_cpk_level() gecersiz bir Cpk'yi
    (orn. -6.998) yine de bir renge/etikete siniflandirip yaniltici bir
    "sonuc" gostermis olurdu; bunun yerine notr bir 'Gecersiz' notu gosterilir."""
    if cpk_valid:
        emoji, level_label, color = get_cpk_level(cpk)
        cpk_value_str = format_cpk(cpk)
        cpk_tooltip = (
            "Surecin spesifikasyon limitlerini karsilama yetenegini gosterir. "
            "Genel kabul: >=1.67 excellent, 1.33-1.67 capable, 1.0-1.33 marginal, <1.0 not capable."
        )
    else:
        emoji, level_label, color = "⚠️", "Gecersiz", "#f08c00"
        cpk_value_str = "—"
        cpk_tooltip = "LSL >= USL - spesifikasyon gecersiz oldugu icin Cpk/Cpu hesaplanmadi."
    card_bg = "#161a23" if dark else "#ffffff"
    card_border = "#333c4a" if dark else "#E4E7EC"
    text_color = "#fafafa" if dark else "#31333f"
    sub_color = "#9aa4b2" if dark else "#666666"
    oos_color = "#e03131" if n_out_of_control else "#2f9e44"
    oos_icon = "⚠️" if n_out_of_control else "✅"

    trend_badge = None
    if trend is not None:
        direction, delta = trend
        trend_icon = {"up": "▲", "down": "▼", "flat": "→"}[direction]
        trend_badge = f"{trend_icon} {delta:+.{decimal_places}f} (son {min(6, n_samples // 2)} nokta)"

    cards = [
        ("\U0001F4CA", f"Ortalama ({unit})", f"{center_value:.{decimal_places}f}", trend_badge, sub_color,
         accent_color, "Surecin genel ortalamasi (X-bar/R'de x-double-bar, I-MR'de x-bar) "
         "ve son verilere gore basit bir egilim (trend) gostergesi."),
        (emoji, cpk_label, cpk_value_str, level_label, color, color, cpk_tooltip),
        ("\U0001F522", "Ornek Sayisi", str(n_samples), None, sub_color, accent_color,
         "Toplam olcum (I-MR) veya alt grup (X-bar/R) sayisi."),
        (oos_icon, "Kontrol Disi Nokta", str(n_out_of_control), None, sub_color, oos_color,
         "Istatistiksel kontrol limitlerinin (UCL/LCL) disinda kalan nokta sayisi."),
    ]

    cols = st.columns(4)
    for col, (icon, label, value, badge, badge_color, card_accent, tooltip) in zip(cols, cards):
        badge_html = (
            f'<div style="font-size:0.72rem;font-weight:700;color:{badge_color};'
            f'margin-top:2px;">{badge}</div>' if badge else ""
        )
        with col:
            st.markdown(
                f"""
                <div class="kpi-card" title="{tooltip}" style="background:{card_bg};
                            border:1px solid {card_border}; border-left:4px solid {card_accent};
                            border-radius:12px; padding:0.7rem 0.9rem; height:100%;
                            box-shadow:0 1px 2px rgba(15,23,42,0.06), 0 2px 10px rgba(15,23,42,0.09);">
                    <div style="font-size:0.78rem; color:{sub_color};">{icon} {label}</div>
                    <div style="font-size:1.45rem; font-weight:700; color:{text_color};
                                line-height:1.3;">{value}</div>
                    {badge_html}
                </div>
                """,
                unsafe_allow_html=True,
            )


def render_capability_histogram(values: list[float], lsl: float, usl: float,
                                 one_sided: bool, dark: bool, unit: str):
    """Mevcut olcumlerden histogram + normal dagilim egrisi (scipy.stats.norm),
    LSL/USL dikey cizgileri ve (iki tarafliysa) Target (LSL/USL ortalamasi)
    cizgisi ile bir 'surec yeterlilik' gorseli olusturur. Figur objesini
    dondurur - cagiran taraf st.pyplot + PNG export + plt.close yapar."""
    values_arr = np.array(values, dtype=float)
    mu = float(values_arr.mean())
    sigma = float(values_arr.std(ddof=1)) if len(values_arr) > 1 else 0.0

    fig, ax = plt.subplots(figsize=(8, 3.5), constrained_layout=True)

    bins = min(15, max(5, len(values_arr) // 2))
    ax.hist(
        values_arr, bins=bins, density=True, color="steelblue", alpha=0.6,
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


def annotate_hline(ax, x_pos: float, y_value: float, text: str, color: str) -> None:
    """Bir yatay kontrol/spesifikasyon cizgisinin sag ucuna kucuk bir deger
    etiketi ekler (orn. 'UCL=7.098'), grafigi okumayi kolaylastirir."""
    ax.annotate(
        text, xy=(x_pos, y_value), xytext=(3, 0), textcoords="offset points",
        color=color, fontsize=7, va="center", ha="left", annotation_clip=False,
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
            if is_individual:
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
                shift = st.selectbox("Vardiya", SHIFT_OPTIONS)
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
            if submitted:
                st.session_state.subgroups.append({"shift": shift, "values": measurements})
                st.success("Olcum eklendi." if is_individual else "Alt grup eklendi.")

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

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("\U0001F9EA Demo veri yukle (24 olcum)" if is_individual else "\U0001F9EA Demo veri yukle (24 alt grup)", type="primary"):
                scenario_product = None if demo_scenario == "Genel (varsayilan)" else demo_scenario
                demo_mean, demo_spread, demo_shift_amount = demo_scenario_targets(param_config, scenario_product)
                if is_individual:
                    demo_values = generate_demo_individual(
                        target_mean=demo_mean,
                        target_sigma=demo_spread,
                        shift_amount=demo_shift_amount,
                    )
                    st.session_state.subgroups = [{"shift": "-", "values": [v]} for v in demo_values]
                else:
                    demo = generate_demo_subgroups(
                        subgroup_size=subgroup_n,
                        target_mean=demo_mean,
                        target_r_bar=demo_spread,
                        shift_amount=demo_shift_amount,
                        clip_min=param_config["min_value"],
                        clip_max=param_config["max_value"],
                    )
                    st.session_state.subgroups = [
                        {"shift": SHIFT_OPTIONS[i % len(SHIFT_OPTIONS)], "values": vals}
                        for i, vals in enumerate(demo)
                    ]
                st.session_state.baseline = None
                st.session_state.confirm_clear = False
                st.success(f"Demo veri yuklendi ({demo_scenario}).")
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
            expected_cols = "Sira, Olcum 1" if is_individual else f"Grup, Vardiya, Olcum 1..{subgroup_n}"
            st.caption(
                f"Uygulamanin kendi 'CSV olarak indir' formatiyla uyumlu olmalidir - "
                f"beklenen sutunlar: **{expected_cols}** (birim: {unit}). "
                "Yuklenen veri MEVCUT VERININ YERINI ALIR (baseline da sifirlanir)."
            )

            if is_individual:
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
                            import_df, is_individual, subgroup_n, SHIFT_OPTIONS, unit
                        )
                        if err:
                            st.error(err)
                        else:
                            st.session_state.subgroups = new_subgroups
                            st.session_state.baseline = None
                            label = "olcum" if is_individual else "alt grup"
                            st.success(f"{len(new_subgroups)} {label} CSV'den yuklendi.")

    st.write("")

    with st.container(border=True, key="card-04"):
        st.subheader("Kayitli olculer" if is_individual else "Kayitli alt gruplar")

        if not st.session_state.subgroups:
            st.info("Henuz veri yok. Yukaridan manuel ekleyin veya demo veri yukleyin.")
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

            with st.expander("\U0001F4CB Ham verileri goruntule", expanded=False):
                rows = csv_io.subgroups_to_records(st.session_state.subgroups, is_individual)
                df = pd.DataFrame(rows)
                # Sadece GORUNUMU laboratuvar hassasiyetine yuvarlar - alttaki veri
                # (ve CSV export'u) kullanicinin girdigi tam degerleri korur.
                numeric_cols = [c for c in df.columns if c not in ("Sira", "Grup", "Vardiya")]
                column_config = {
                    c: st.column_config.NumberColumn(format=f"%.{decimal_places}f") for c in numeric_cols
                }
                st.dataframe(df, use_container_width=True, hide_index=True, column_config=column_config)

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
        st.warning("Grafik icin en az 2 alt grup gerekli. Once veri girisi sekmesinden veri ekleyin.")
    else:
        with st.container(border=True, key="card-05"):
            info_col, clear_col = st.columns([5, 1])
            with info_col:
                st.caption(
                    f"ℹ️ **{st.session_state.active_parameter}** — "
                    f"{PARAMETER_INFO.get(st.session_state.active_parameter, '')}"
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
            else:  # HMF
                st.caption(
                    "Bu degerler TGK Bal Tebligi, TGK Uzum Pekmezi Tebligi ve "
                    "genel sektor pratigine dayanir. **Sadece USL anlamlidir**: "
                    "HMF, isil islem/depolama sirasinda sekerlerin bozunmasinin "
                    "gostergesidir; alt limit kavrami yoktur."
                )

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

        st.write("")

        if is_individual:
            with st.container(border=True, key="card-07"):
                st.subheader("Kontrol limitleri (Baseline)")

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

            limits = compute_imr_limits(x_bar, mr_bar)
            cpk = compute_cpk(x_bar, mr_bar, 2, lsl, usl, one_sided=one_sided)

            st.write("")

            with st.container(border=True, key="card-08"):
                m1, m2, m3, m4 = st.columns(4)
                m1.metric(f"Genel Ortalama (x̄, {unit})", f"{x_bar:.{decimal_places}f}")
                m2.metric(f"Ortalama Moving Range (MR̄, {unit})", f"{mr_bar:.{decimal_places}f}")
                m3.metric(
                    "UCL / LCL (I chart)", f"{limits.ucl_i:.{decimal_places}f} / {limits.lcl_i:.{decimal_places}f}",
                    help="Istatistiksel kontrol limitleri (Ust/Alt Kontrol Siniri) - surecin dogal varyasyon araligi, spesifikasyon limitleriyle (LSL/USL) karistirilmamalidir.",
                )
                if spec_valid:
                    m4.metric(
                        cpk_label, format_cpk(cpk),
                        help="Surecin spesifikasyon limitlerini karsilama yetenegini gosterir.",
                    )
                    render_cpk_message(cpk, cpk_label)
                    with st.expander("\U0001F9EE Hesaplama adimlarini goster"):
                        render_calculation_steps_imr(x_bar, mr_bar, limits, cpk, cpk_label, lsl, usl, one_sided, unit, decimal_places)
                else:
                    m4.metric(
                        cpk_label, "Gecersiz",
                        help="LSL >= USL - once yukaridaki spesifikasyon limitlerini duzeltin.",
                    )
                    st.warning(
                        f"{cpk_label} hesaplanmadi: spesifikasyon gecersiz (LSL >= USL). "
                        "Once yukaridaki LSL/USL degerlerini duzeltin."
                    )

            st.write("")

            indices_i = list(range(1, len(values) + 1))
            indices_mr = list(range(2, len(values) + 1))
            out_of_control_i = [i for i, v in enumerate(values) if v > limits.ucl_i or v < limits.lcl_i]
            out_of_control_mr = [
                i for i, mr in enumerate(moving_ranges) if mr > limits.ucl_mr or mr < limits.lcl_mr
            ]
            flagged_points = sorted({i + 1 for i in out_of_control_i} | {i + 2 for i in out_of_control_mr})

            with st.container(border=True, key="card-09"):
                render_kpi_panel(
                    unit, x_bar, cpk, cpk_label, len(values), len(flagged_points), decimal_places,
                    trend=compute_trend(values), cpk_valid=spec_valid,
                )
                render_formula_method_card("I-MR", 2)

            st.write("")

            if spec_valid:
                imr_quick_summary = build_quick_summary("olcum", len(values), len(flagged_points), cpk, cpk_label)
            else:
                oos_text = "kontrol disi nokta yok" if not flagged_points else f"{len(flagged_points)} kontrol disi nokta var"
                imr_quick_summary = (
                    f"{len(values)} olcum analiz edildi, {oos_text}, "
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
                ax.plot(indices_i, values, marker="o", color="steelblue", linewidth=1, label="Olcum")
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
                if out_of_control_i:
                    ax.scatter(
                        [indices_i[i] for i in out_of_control_i],
                        [values[i] for i in out_of_control_i],
                        color="red", s=100, zorder=5, label="Kontrol disi",
                    )
                ax.set_xlabel("Olcum no")
                ax.set_ylabel(unit)
                ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1), fontsize=8)
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
                hist_fig = render_capability_histogram(values, lsl, usl, one_sided, dark, unit)
                st.pyplot(hist_fig, use_container_width=True)
                render_png_download(
                    hist_fig, f"{st.session_state.active_parameter.lower()}_histogram.png", key="png_histogram"
                )
                plt.close(hist_fig)

            st.write("")

            with st.container(border=True, key="card-13"):
                st.subheader("MR (Moving Range) Kontrol Grafigi")

                fig2, ax2 = plt.subplots(figsize=(8, 2.8), constrained_layout=True)
                ax2.plot(
                    indices_mr, moving_ranges, marker="o", color="steelblue", linewidth=1,
                    label="Moving range",
                )
                ax2.axhline(mr_bar, color="green", linestyle="-", label="MR̄")
                ax2.axhline(limits.ucl_mr, color="red", linestyle="--", label="UCL_MR")
                ax2.axhline(limits.lcl_mr, color="red", linestyle="--", label="LCL_MR")
                annotate_hline(ax2, indices_mr[-1], limits.ucl_mr, f"UCL={limits.ucl_mr:.{decimal_places}f}", "red")
                annotate_hline(ax2, indices_mr[-1], mr_bar, f"MR̄={mr_bar:.{decimal_places}f}", "green")
                if out_of_control_mr:
                    ax2.scatter(
                        [indices_mr[i] for i in out_of_control_mr],
                        [moving_ranges[i] for i in out_of_control_mr],
                        color="red", s=100, zorder=5, label="Kontrol disi",
                    )
                ax2.set_xlabel("Olcum no")
                ax2.set_ylabel("Moving Range")
                ax2.legend(loc="upper left", bbox_to_anchor=(1.02, 1), fontsize=8)
                style_chart(fig2, ax2, dark)
                st.pyplot(fig2, use_container_width=True)
                render_png_download(fig2, f"{st.session_state.active_parameter.lower()}_mr_chart.png", key="png_mr_chart")
                plt.close(fig2)

            with st.container(border=True, key="card-14"):
                if spec_valid:
                    render_pdf_download(
                        st.session_state.active_parameter, selected_product, "I-MR",
                        len(values), len(flagged_points), cpk, cpk_label, imr_quick_summary,
                        imr_main_chart_png, key="pdf_imr",
                    )
                else:
                    st.info(
                        "PDF raporu, spesifikasyon (LSL/USL) gecerli hale getirilene "
                        "kadar devre disi - gecersiz bir Cpk iceren rapor uretilmez."
                    )

            if flagged_points:
                st.warning(
                    f"Kontrol disi olcumler: {flagged_points} "
                    "- surec bu noktalarda 'kontrol disi' kabul edilir."
                )
        else:
            means, ranges, live_x_double_bar, live_r_bar = compute_stats(st.session_state.subgroups)

            with st.container(border=True, key="card-15"):
                st.subheader("Kontrol limitleri (Baseline)")

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

            limits = compute_xbar_r_limits(x_double_bar, r_bar, subgroup_n)
            cpk = compute_cpk(x_double_bar, r_bar, subgroup_n, lsl, usl, one_sided=one_sided)

            st.write("")

            with st.container(border=True, key="card-16"):
                m1, m2, m3, m4 = st.columns(4)
                m1.metric(f"Genel Ortalama (x̄̄, {unit})", f"{x_double_bar:.{decimal_places}f}")
                m2.metric(f"Ortalama Range (R̄, {unit})", f"{r_bar:.{decimal_places}f}")
                m3.metric(
                    "UCL / LCL (X-bar)", f"{limits.ucl_x:.{decimal_places}f} / {limits.lcl_x:.{decimal_places}f}",
                    help="Istatistiksel kontrol limitleri (Ust/Alt Kontrol Siniri) - surecin dogal varyasyon araligi, spesifikasyon limitleriyle (LSL/USL) karistirilmamalidir.",
                )
                if spec_valid:
                    m4.metric(
                        cpk_label, format_cpk(cpk),
                        help="Surecin spesifikasyon limitlerini karsilama yetenegini gosterir.",
                    )
                    render_cpk_message(cpk, cpk_label)
                    with st.expander("\U0001F9EE Hesaplama adimlarini goster"):
                        render_calculation_steps_xbar(x_double_bar, r_bar, limits, cpk, cpk_label, lsl, usl, one_sided, unit, decimal_places)
                else:
                    m4.metric(
                        cpk_label, "Gecersiz",
                        help="LSL >= USL - once yukaridaki spesifikasyon limitlerini duzeltin.",
                    )
                    st.warning(
                        f"{cpk_label} hesaplanmadi: spesifikasyon gecersiz (LSL >= USL). "
                        "Once yukaridaki LSL/USL degerlerini duzeltin."
                    )

            st.write("")

            indices = list(range(1, len(means) + 1))
            out_of_control_x = [i for i, m in enumerate(means) if m > limits.ucl_x or m < limits.lcl_x]
            out_of_control_r = [i for i, r in enumerate(ranges) if r > limits.ucl_r or r < limits.lcl_r]
            groups = sorted({i + 1 for i in out_of_control_x} | {i + 1 for i in out_of_control_r})

            with st.container(border=True, key="card-17"):
                render_kpi_panel(
                    unit, x_double_bar, cpk, cpk_label, len(means), len(groups), decimal_places,
                    trend=compute_trend(means), cpk_valid=spec_valid,
                )
                render_formula_method_card("X-bar/R", subgroup_n)

            st.write("")

            if spec_valid:
                xbar_quick_summary = build_quick_summary("alt grup", len(means), len(groups), cpk, cpk_label)
            else:
                oos_text = "kontrol disi nokta yok" if not groups else f"{len(groups)} kontrol disi nokta var"
                xbar_quick_summary = (
                    f"{len(means)} alt grup analiz edildi, {oos_text}, "
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
                ax.plot(indices, means, marker="o", color="steelblue", linewidth=1, label="Alt grup ortalamasi")
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
                if out_of_control_x:
                    ax.scatter(
                        [indices[i] for i in out_of_control_x],
                        [means[i] for i in out_of_control_x],
                        color="red", s=100, zorder=5, label="Kontrol disi",
                    )
                ax.set_xlabel("Alt grup no")
                ax.set_ylabel(unit)
                ax.legend(loc="upper left", bbox_to_anchor=(1.02, 1), fontsize=8)
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
                hist_fig = render_capability_histogram(all_values, lsl, usl, one_sided, dark, unit)
                st.pyplot(hist_fig, use_container_width=True)
                render_png_download(
                    hist_fig, f"{st.session_state.active_parameter.lower()}_histogram.png", key="png_histogram"
                )
                plt.close(hist_fig)

            st.write("")

            with st.container(border=True, key="card-22"):
                st.subheader("R Kontrol Grafigi")

                fig2, ax2 = plt.subplots(figsize=(8, 2.8), constrained_layout=True)
                ax2.plot(indices, ranges, marker="o", color="steelblue", linewidth=1, label="Alt grup range")
                ax2.axhline(r_bar, color="green", linestyle="-", label="R̄")
                ax2.axhline(limits.ucl_r, color="red", linestyle="--", label="UCL_R")
                ax2.axhline(limits.lcl_r, color="red", linestyle="--", label="LCL_R")
                annotate_hline(ax2, indices[-1], limits.ucl_r, f"UCL={limits.ucl_r:.{decimal_places}f}", "red")
                annotate_hline(ax2, indices[-1], r_bar, f"R̄={r_bar:.{decimal_places}f}", "green")
                if out_of_control_r:
                    ax2.scatter(
                        [indices[i] for i in out_of_control_r],
                        [ranges[i] for i in out_of_control_r],
                        color="red", s=100, zorder=5, label="Kontrol disi",
                    )
                ax2.set_xlabel("Alt grup no")
                ax2.set_ylabel("Range")
                ax2.legend(loc="upper left", bbox_to_anchor=(1.02, 1), fontsize=8)
                style_chart(fig2, ax2, dark)
                st.pyplot(fig2, use_container_width=True)
                render_png_download(fig2, f"{st.session_state.active_parameter.lower()}_r_chart.png", key="png_r_chart")
                plt.close(fig2)

            with st.container(border=True, key="card-23"):
                if spec_valid:
                    render_pdf_download(
                        st.session_state.active_parameter, selected_product, "X-bar/R",
                        len(means), len(groups), cpk, cpk_label, xbar_quick_summary,
                        xbar_main_chart_png, key="pdf_xbar",
                    )
                else:
                    st.info(
                        "PDF raporu, spesifikasyon (LSL/USL) gecerli hale getirilene "
                        "kadar devre disi - gecersiz bir Cpk iceren rapor uretilmez."
                    )

            if groups:
                st.warning(
                    f"Kontrol disi alt gruplar: {groups} "
                    "- surec bu noktalarda 'kontrol disi' kabul edilir."
                )

# ---------------------------------------------------------------------------
# SEKME 3: Hizli Hesaplayicilar
# ---------------------------------------------------------------------------
# NOT: Bu sekme, mevcut SPC chart/veri akisindan BILINCLI OLARAK izole tutuldu.
# Totox tek seferlik bir hesap makinesidir - session_state.subgroups'a hicbir
# sekilde dokunmaz, kontrol grafigi/baseline mantigiyla etkilesime girmez.
with tab_calc:
    with st.container(border=True, key="card-24"):
        st.subheader("Totox Hesaplayici")
        st.caption(
            "Totox = 2 × Peroksit Degeri + Anisidin Degeri. Bu bir SPC kontrol "
            "grafigi degildir - tek seferlik bir hesap makinesidir, mevcut "
            "veri girisi/chart akisindan bagimsizdir ve onu etkilemez."
        )

        tc1, tc2 = st.columns(2)
        with tc1:
            totox_peroxide = st.number_input(
                "Peroksit Degeri (meq O2/kg)", min_value=0.0, value=5.0,
                step=0.1, format="%.2f", key="totox_peroxide",
            )
        with tc2:
            totox_anisidine = st.number_input(
                "Anisidin Degeri", min_value=0.0, value=3.0,
                step=0.1, format="%.2f", key="totox_anisidine",
            )

        totox_value = 2 * totox_peroxide + totox_anisidine
        st.metric("Totox Degeri", f"{totox_value:.2f}")

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

# ---------------------------------------------------------------------------
# FOOTER - tum sekmelerin altinda, her zaman gorunur (with tab_x: bloklarinin
# disinda oldugu icin hangi sekme secili olursa olsun sayfanin en altinda kalir)
# ---------------------------------------------------------------------------
st.divider()
st.caption(f"SPC FoodLab v1.1.1 · [GitHub]({GITHUB_URL})")
