"""SPC FoodLab - pH/Brix/Aw/Viskozite Istatistiksel Proses Kontrolu (Streamlit MVP)."""

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from constants import PARAMETER_CONFIG, SHIFT_OPTIONS, SUBGROUP_SIZE
from demo_data import generate_demo_individual, generate_demo_subgroups
from spc_core import compute_cpk, compute_imr_limits, compute_moving_ranges, compute_xbar_r_limits

MIN_RECOMMENDED_BASELINE = 20
CPK_SANITY_THRESHOLD = 10  # |Cpk| bu esigi asarsa LSL/USL-veri uyumsuzlugu uyarisi goster

st.set_page_config(page_title="SPC FoodLab", page_icon="\U0001F4CA", layout="wide")

if "subgroups" not in st.session_state:
    st.session_state.subgroups = []  # list of dict: {"shift": str, "values": list[float]}
if "baseline" not in st.session_state:
    st.session_state.baseline = None  # dict: {"x_double_bar", "r_bar", "n_baseline"}
if "active_parameter" not in st.session_state:
    st.session_state.active_parameter = "pH"
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

with st.sidebar:
    st.subheader("Ayarlar")

    param_options = list(PARAMETER_CONFIG.keys())
    selected_param_radio = st.radio(
        "Parametre", param_options,
        index=param_options.index(st.session_state.active_parameter),
        key="parameter_radio",
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

dark = chart_theme == "Koyu"
param_config = PARAMETER_CONFIG[st.session_state.active_parameter]
unit = param_config["unit"]
is_individual = param_config.get("is_individual", False)  # True: I-MR (alt grup yok), False: X-bar/R


def inject_theme_css(dark: bool) -> None:
    """Secilen acik/koyu temayi grafiklerin otesinde tum arayuze (sidebar,
    kartlar, metrikler, uyari kutulari) uygular. Streamlit'in kendi
    config.toml temasi Community Cloud'da calisma anindan degistirilemedigi
    icin bu, custom CSS injection ile yapiliyor."""
    if dark:
        css = """
        <style>
        .stApp { background-color: #0e1117; }
        [data-testid="stSidebar"] { background-color: #161a23; }
        .stApp, .stApp p, .stApp span, .stApp label,
        h1, h2, h3, h4, h5, h6 { color: #fafafa; }
        [data-testid="stMetricValue"], [data-testid="stMetricLabel"] { color: #fafafa; }
        [data-testid="stVerticalBlockBorderWrapper"] {
            background-color: #161a23;
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
        </style>
        """
    else:
        css = """
        <style>
        .stApp { background-color: #ffffff; }
        </style>
        """
    st.markdown(css, unsafe_allow_html=True)


inject_theme_css(dark)


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


def format_cpk(cpk: float) -> str:
    """Cpk/Cpu metrik gosterimi - r_bar/mr_bar=0 (varyasyon yok) durumunda
    compute_cpk() sonsuz dondurur; bunu okunakli sekilde gosterir."""
    if cpk == float("inf"):
        return "∞"
    if cpk == float("-inf"):
        return "-∞"
    return f"{cpk:.3f}"


def render_cpk_message(cpk: float, cpk_label: str) -> None:
    """Cpk/Cpu degerine gore uygun basari/uyari/hata mesajini gosterir.
    Iki yerde (X-bar/R ve I-MR) aynen kullanilir, tekrar onlemek icin
    ortak fonksiyon haline getirildi."""
    if cpk == float("inf"):
        st.success(
            f"{cpk_label} = ∞: olculen degerlerde hic varyasyon yok (R̄/MR̄ = 0) "
            "ve ortalama spesifikasyon icinde - surec kusursuz."
        )
    elif cpk == float("-inf"):
        st.error(
            f"{cpk_label} = -∞: olculen degerlerde varyasyon yok ama ortalama "
            "zaten spesifikasyon disinda - surec yeterli degil."
        )
    elif abs(cpk) > CPK_SANITY_THRESHOLD:
        st.warning(
            f"{cpk_label} anlamsiz derecede yuksek/dusuk cikti. Sectigin "
            "urunun spesifikasyon araligi, girdigin verilerle ortusmuyor "
            "olabilir - LSL/USL degerlerini kontrol et."
        )
    elif cpk < 1.0:
        st.error(f"{cpk_label} < 1.0: Surec yeterli degil (spesifikasyon limitlerine gore).")
    elif cpk < 1.33:
        st.warning(f"{cpk_label} 1.0-1.33 arasi: Surec marjinal yeterli.")
    else:
        st.success(f"{cpk_label} >= 1.33: Surec yeterli.")


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

tab_data, tab_chart, tab_calc, tab_about = st.tabs([
    "\U0001F4DD Veri Girisi", "\U0001F4C8 X-bar/R Chart & Cpk",
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
# ara run'larda (ör. onay akislarindaki rerun'lar) render edilmeyip Streamlit
# tarafindan temizlenmesi ihtimaline karsi asagida setdefault() kullaniliyor -
# bu, sirlamaya bagli olmadan 0.0'a dusmeyi onluyor.

# ---------------------------------------------------------------------------
# SEKME 1: Veri Girisi / Goruntuleme
# ---------------------------------------------------------------------------
with tab_data:
    with st.container(border=True):
        if is_individual:
            st.subheader("Yeni olcum ekle")
            st.write(
                f"I-MR chart icin alt grup/vardiya kavrami yok - her satir tek bir {unit} "
                f"olcumudur. Olcum SIRASI onemlidir (ardisik olcumler arasindaki fark - "
                f"moving range - hesaba katilir). (Parametre: {st.session_state.active_parameter})"
            )
        else:
            st.subheader("Yeni alt grup ekle")
            st.write(f"Her alt grup icin {SUBGROUP_SIZE} {unit} olcumu girilir. (Parametre: {st.session_state.active_parameter})")

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
                cols = st.columns(SUBGROUP_SIZE)
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

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("\U0001F9EA Demo veri yukle (24 olcum)" if is_individual else "\U0001F9EA Demo veri yukle (24 alt grup)", type="primary"):
                if is_individual:
                    demo_values = generate_demo_individual(
                        target_mean=param_config["demo_target_mean"],
                        target_sigma=param_config["demo_target_sigma"],
                    )
                    st.session_state.subgroups = [{"shift": "-", "values": [v]} for v in demo_values]
                else:
                    demo = generate_demo_subgroups(
                        target_mean=param_config["demo_target_mean"],
                        target_r_bar=param_config["demo_target_r_bar"],
                        shift_amount=param_config.get("demo_shift_amount", 0.35),
                        clip_min=param_config["min_value"],
                        clip_max=param_config["max_value"],
                    )
                    st.session_state.subgroups = [
                        {"shift": SHIFT_OPTIONS[i % len(SHIFT_OPTIONS)], "values": vals}
                        for i, vals in enumerate(demo)
                    ]
                st.session_state.baseline = None
                st.session_state.confirm_clear = False
                st.success("Demo veri yuklendi.")
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

    with st.container(border=True):
        st.subheader("Kayitli olculer" if is_individual else "Kayitli alt gruplar")

        if not st.session_state.subgroups:
            st.info("Henuz veri yok. Yukaridan manuel ekleyin veya demo veri yukleyin.")
        else:
            if is_individual:
                _, _, summary_x_bar, summary_mr_bar = compute_individual_stats(st.session_state.subgroups)
                sm1, sm2 = st.columns(2)
                sm1.metric(f"Genel Ortalama (x̄, {unit})", f"{summary_x_bar:.4f}")
                sm2.metric(
                    f"Ortalama Moving Range (MR̄, {unit})",
                    f"{summary_mr_bar:.4f}" if summary_mr_bar is not None else "—",
                )
            else:
                _, _, summary_x_double_bar, summary_r_bar = compute_stats(st.session_state.subgroups)
                sm1, sm2 = st.columns(2)
                sm1.metric(f"Genel Ortalama (x̄̄, {unit})", f"{summary_x_double_bar:.4f}")
                sm2.metric(f"Ortalama Range (R̄, {unit})", f"{summary_r_bar:.4f}")

            st.divider()

            rows = []
            for i, sg in enumerate(st.session_state.subgroups, start=1):
                vals = sg["values"]
                if is_individual:
                    rows.append({
                        "Sira": i,
                        **{f"Olcum {j + 1}": v for j, v in enumerate(vals)},
                    })
                else:
                    rows.append({
                        "Grup": i,
                        "Vardiya": sg["shift"],
                        **{f"Olcum {j + 1}": v for j, v in enumerate(vals)},
                        "Ortalama": sum(vals) / len(vals),
                        "Range": max(vals) - min(vals),
                    })
            df = pd.DataFrame(rows)
            st.dataframe(df, use_container_width=True, hide_index=True)

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

        with st.container(border=True):
            st.subheader(f"Spesifikasyon limitleri ({unit}, {cpk_label} icin)")

            selected_product = st.selectbox("Urun", products, index=default_index, key="product_select")
            one_sided = _resolve_one_sided(selected_product)
            cpk_label = "Cpu (tek tarafli)" if one_sided else "Cpk"

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
            if active_param == "pH":
                st.caption(
                    "Bu degerler literatur/sektor pratiginden alinan gosterge "
                    "degerlerdir. Turk Gida Kodeksi cogu urunde sayisal bir pH "
                    "limiti belirlemez; bu tablo TGK uyumlulugu icin degil, kalite "
                    "kontrol referansi olarak kullanilir. LSL/USL degerlerini "
                    "kendi urun/spesifikasyonuna gore elle degistirebilirsin."
                )
            elif active_param == "Brix":
                st.caption(
                    "Bu degerler 19 CFR 151.91 (ABD federal regülasyonu, meyve "
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
                    key="lsl_input", disabled=one_sided,
                    help="Bu urun/parametrede LSL kullanilmiyor (bkz. yukaridaki not)." if one_sided else None,
                )
            with col2:
                usl = st.number_input(
                    f"Ust spesifikasyon limiti (USL, {unit})", step=0.01, format="%.2f", key="usl_input"
                )

        st.write("")

        if is_individual:
            with st.container(border=True):
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

            with st.container(border=True):
                m1, m2, m3, m4 = st.columns(4)
                m1.metric(f"Genel Ortalama (x̄, {unit})", f"{x_bar:.4f}")
                m2.metric(f"Ortalama Moving Range (MR̄, {unit})", f"{mr_bar:.4f}")
                m3.metric("UCL / LCL (I chart)", f"{limits.ucl_i:.4f} / {limits.lcl_i:.4f}")
                m4.metric(cpk_label, format_cpk(cpk))

                render_cpk_message(cpk, cpk_label)

            st.write("")

            indices_i = list(range(1, len(values) + 1))
            indices_mr = list(range(2, len(values) + 1))
            out_of_control_i = [i for i, v in enumerate(values) if v > limits.ucl_i or v < limits.lcl_i]
            out_of_control_mr = [
                i for i, mr in enumerate(moving_ranges) if mr > limits.ucl_mr or mr < limits.lcl_mr
            ]

            with st.container(border=True):
                st.subheader("I (Individual) Kontrol Grafigi")

                fig, ax = plt.subplots(figsize=(8, 3.5), constrained_layout=True)
                ax.plot(indices_i, values, marker="o", color="steelblue", linewidth=1, label="Olcum")
                ax.axhline(x_bar, color="green", linestyle="-", label="Genel ortalama (x̄)")
                ax.axhline(limits.ucl_i, color="red", linestyle="--", label="UCL")
                if not one_sided:
                    # Tek tarafli (one_sided) analizde LSL/LCL anlamsizdir (bkz.
                    # Spesifikasyon limitleri karti) - grafik sadelestirmesi
                    # olarak bu durumda LCL cizgisi/etiketi cizilmez.
                    ax.axhline(limits.lcl_i, color="red", linestyle="--", label="LCL")
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
                plt.close(fig)

            st.write("")

            with st.container(border=True):
                st.subheader("MR (Moving Range) Kontrol Grafigi")

                fig2, ax2 = plt.subplots(figsize=(8, 2.8), constrained_layout=True)
                ax2.plot(
                    indices_mr, moving_ranges, marker="o", color="steelblue", linewidth=1,
                    label="Moving range",
                )
                ax2.axhline(mr_bar, color="green", linestyle="-", label="MR̄")
                ax2.axhline(limits.ucl_mr, color="red", linestyle="--", label="UCL_MR")
                ax2.axhline(limits.lcl_mr, color="red", linestyle="--", label="LCL_MR")
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
                plt.close(fig2)

            if out_of_control_i or out_of_control_mr:
                points = sorted({i + 1 for i in out_of_control_i} | {i + 2 for i in out_of_control_mr})
                st.warning(
                    f"Kontrol disi olcumler: {points} "
                    "- surec bu noktalarda 'kontrol disi' kabul edilir."
                )
        else:
            means, ranges, live_x_double_bar, live_r_bar = compute_stats(st.session_state.subgroups)

            with st.container(border=True):
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

            limits = compute_xbar_r_limits(x_double_bar, r_bar, SUBGROUP_SIZE)
            cpk = compute_cpk(x_double_bar, r_bar, SUBGROUP_SIZE, lsl, usl, one_sided=one_sided)

            st.write("")

            with st.container(border=True):
                m1, m2, m3, m4 = st.columns(4)
                m1.metric(f"Genel Ortalama (x̄̄, {unit})", f"{x_double_bar:.4f}")
                m2.metric(f"Ortalama Range (R̄, {unit})", f"{r_bar:.4f}")
                m3.metric("UCL / LCL (X-bar)", f"{limits.ucl_x:.4f} / {limits.lcl_x:.4f}")
                m4.metric(cpk_label, format_cpk(cpk))

                render_cpk_message(cpk, cpk_label)

            st.write("")

            indices = list(range(1, len(means) + 1))
            out_of_control_x = [i for i, m in enumerate(means) if m > limits.ucl_x or m < limits.lcl_x]
            out_of_control_r = [i for i, r in enumerate(ranges) if r > limits.ucl_r or r < limits.lcl_r]

            with st.container(border=True):
                st.subheader("X-bar Kontrol Grafigi")

                fig, ax = plt.subplots(figsize=(8, 3.5), constrained_layout=True)
                ax.plot(indices, means, marker="o", color="steelblue", linewidth=1, label="Alt grup ortalamasi")
                ax.axhline(x_double_bar, color="green", linestyle="-", label="Genel ortalama (x̄̄)")
                ax.axhline(limits.ucl_x, color="red", linestyle="--", label="UCL")
                if not one_sided:
                    # Tek tarafli (one_sided) analizde LSL/LCL anlamsizdir (bkz.
                    # Spesifikasyon limitleri karti) - grafik sadelestirmesi
                    # olarak bu durumda LCL cizgisi/etiketi cizilmez.
                    ax.axhline(limits.lcl_x, color="red", linestyle="--", label="LCL")
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
                plt.close(fig)

            st.write("")

            with st.container(border=True):
                st.subheader("R Kontrol Grafigi")

                fig2, ax2 = plt.subplots(figsize=(8, 2.8), constrained_layout=True)
                ax2.plot(indices, ranges, marker="o", color="steelblue", linewidth=1, label="Alt grup range")
                ax2.axhline(r_bar, color="green", linestyle="-", label="R̄")
                ax2.axhline(limits.ucl_r, color="red", linestyle="--", label="UCL_R")
                ax2.axhline(limits.lcl_r, color="red", linestyle="--", label="LCL_R")
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
                plt.close(fig2)

            if out_of_control_x or out_of_control_r:
                groups = sorted({i + 1 for i in out_of_control_x} | {i + 1 for i in out_of_control_r})
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
    with st.container(border=True):
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
    with st.container(border=True):
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

Bu formuller ve A2/D3/D4/d2 sabit tablosu parametreden bagimsizdir (n=4 icin
ayni sabitler pH'da, Brix'te ve aw'de de gecerlidir) - degisen sadece olcum
birimi, urun spesifikasyon tablosu ve aw icin tek/iki tarafli Cpk secimidir.

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
