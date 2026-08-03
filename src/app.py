"""SPC FoodLab - pH Istatistiksel Proses Kontrolu (Streamlit MVP)."""

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from constants import PRODUCT_PH_RANGES, SHIFT_OPTIONS, SUBGROUP_SIZE
from demo_data import generate_demo_subgroups
from spc_core import compute_cpk, compute_xbar_r_limits

MIN_RECOMMENDED_BASELINE = 20
CPK_SANITY_THRESHOLD = 10  # |Cpk| bu esigi asarsa LSL/USL-veri uyumsuzlugu uyarisi goster

st.set_page_config(page_title="SPC FoodLab", page_icon="\U0001F4CA", layout="wide")

if "subgroups" not in st.session_state:
    st.session_state.subgroups = []  # list of dict: {"shift": str, "values": list[float]}
if "baseline" not in st.session_state:
    st.session_state.baseline = None  # dict: {"x_double_bar", "r_bar", "n_baseline"}
for _flag in ("confirm_clear", "confirm_freeze", "confirm_reset_baseline"):
    if _flag not in st.session_state:
        st.session_state[_flag] = False

with st.sidebar:
    st.subheader("Ayarlar")
    chart_theme = st.selectbox("Tema (grafik + arayuz)", ["Acik", "Koyu"], key="chart_theme")

dark = chart_theme == "Koyu"


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
st.caption("Gida uretiminde pH olcumlerinden istatistiksel proses kontrolu (SPC)")

tab_data, tab_chart, tab_about = st.tabs(["\U0001F4DD Veri Girisi", "\U0001F4C8 X-bar/R Chart & Cpk", "ℹ️ Hakkinda"])

# NOT: "SEKME 2" kodu bilerek "SEKME 1"den once yazildi (gorsel sekme sirasini
# etkilemez - st.tabs() zaten sirayi belirler). Boylece tab_data icindeki onay
# akislarinin cagirdigi st.rerun(), lsl_input/usl_input widget'lari bu run'da
# ZATEN render edilmisken tetiklenir. Aksi sirada (rerun tab_chart'in widget'lari
# render OLMADAN once tetiklenirse) Streamlit o run'da render edilmeyen widget'in
# session_state degerini temizler ve bir sonraki run'da deger 0.0'a duser - bu
# projede once yasanmis, kok nedeni tespit edilmis bir hata.

# ---------------------------------------------------------------------------
# SEKME 2: X-bar/R Chart & Cpk
# ---------------------------------------------------------------------------
with tab_chart:
    if len(st.session_state.subgroups) < 2:
        st.warning("Grafik icin en az 2 alt grup gerekli. Once veri girisi sekmesinden veri ekleyin.")
    else:
        means, ranges, live_x_double_bar, live_r_bar = compute_stats(st.session_state.subgroups)

        with st.container(border=True):
            st.subheader("Spesifikasyon limitleri (Cpk icin)")

            products = list(PRODUCT_PH_RANGES.keys())
            default_index = products.index("Ozel/Manuel gir")
            selected_product = st.selectbox("Urun", products, index=default_index, key="product_select")

            if "prev_product" not in st.session_state:
                st.session_state.prev_product = selected_product
            # setdefault: widget bir onceki run'da (subgroups gecici olarak <2
            # oldugunda vb.) render edilmeyip Streamlit tarafindan temizlenmis
            # olsa bile makul bir varsayilana geri doner (0.0'a degil).
            st.session_state.setdefault("lsl_input", 6.8)
            st.session_state.setdefault("usl_input", 7.2)

            if selected_product != st.session_state.prev_product:
                product_range = PRODUCT_PH_RANGES[selected_product]
                if product_range is not None:
                    st.session_state.lsl_input, st.session_state.usl_input = product_range
                st.session_state.prev_product = selected_product

            st.caption(
                "Bu degerler literatur/sektor pratiginden alinan gosterge "
                "degerlerdir. Turk Gida Kodeksi cogu urunde sayisal bir pH "
                "limiti belirlemez; bu tablo TGK uyumlulugu icin degil, kalite "
                "kontrol referansi olarak kullanilir. LSL/USL degerlerini "
                "kendi urun/spesifikasyonuna gore elle degistirebilirsin."
            )

            col1, col2 = st.columns(2)
            with col1:
                lsl = st.number_input(
                    "Alt spesifikasyon limiti (LSL)", step=0.01, format="%.2f", key="lsl_input"
                )
            with col2:
                usl = st.number_input(
                    "Ust spesifikasyon limiti (USL)", step=0.01, format="%.2f", key="usl_input"
                )

        st.write("")

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
        cpk = compute_cpk(x_double_bar, r_bar, SUBGROUP_SIZE, lsl, usl)

        st.write("")

        with st.container(border=True):
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Genel Ortalama (x̄̄)", f"{x_double_bar:.4f}")
            m2.metric("Ortalama Range (R̄)", f"{r_bar:.4f}")
            m3.metric("UCL / LCL (X-bar)", f"{limits.ucl_x:.4f} / {limits.lcl_x:.4f}")
            m4.metric("Cpk", f"{cpk:.3f}")

            if abs(cpk) > CPK_SANITY_THRESHOLD:
                st.warning(
                    "Cpk anlamsiz derecede yuksek/dusuk cikti. Sectigin urunun "
                    "spesifikasyon araligi, girdigin verilerle ortusmuyor "
                    "olabilir - LSL/USL degerlerini kontrol et."
                )
            elif cpk < 1.0:
                st.error("Cpk < 1.0: Surec yeterli degil (spesifikasyon limitlerine gore).")
            elif cpk < 1.33:
                st.warning("Cpk 1.0-1.33 arasi: Surec marjinal yeterli.")
            else:
                st.success("Cpk >= 1.33: Surec yeterli.")

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
            ax.axhline(limits.lcl_x, color="red", linestyle="--", label="LCL")
            if out_of_control_x:
                ax.scatter(
                    [indices[i] for i in out_of_control_x],
                    [means[i] for i in out_of_control_x],
                    color="red", s=100, zorder=5, label="Kontrol disi",
                )
            ax.set_xlabel("Alt grup no")
            ax.set_ylabel("pH")
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
# SEKME 1: Veri Girisi / Goruntuleme
# ---------------------------------------------------------------------------
with tab_data:
    with st.container(border=True):
        st.subheader("Yeni alt grup ekle")
        st.write(f"Her alt grup icin {SUBGROUP_SIZE} pH olcumu girilir.")

        with st.form("subgroup_form", clear_on_submit=True):
            shift = st.selectbox("Vardiya", SHIFT_OPTIONS)
            cols = st.columns(SUBGROUP_SIZE)
            measurements = []
            for i, col in enumerate(cols):
                with col:
                    val = st.number_input(
                        f"Olcum {i + 1}", min_value=0.0, max_value=14.0,
                        value=7.0, step=0.01, format="%.2f", key=f"m_{i}",
                    )
                    measurements.append(val)
            submitted = st.form_submit_button("Alt grubu kaydet")
            if submitted:
                st.session_state.subgroups.append({"shift": shift, "values": measurements})
                st.success("Alt grup eklendi.")

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("\U0001F9EA Demo veri yukle (24 alt grup)", type="primary"):
                demo = generate_demo_subgroups()
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
        st.subheader("Kayitli alt gruplar")

        if not st.session_state.subgroups:
            st.info("Henuz veri yok. Yukaridan manuel ekleyin veya demo veri yukleyin.")
        else:
            _, _, summary_x_double_bar, summary_r_bar = compute_stats(st.session_state.subgroups)
            sm1, sm2 = st.columns(2)
            sm1.metric("Genel Ortalama (x̄̄)", f"{summary_x_double_bar:.4f}")
            sm2.metric("Ortalama Range (R̄)", f"{summary_r_bar:.4f}")

            st.divider()

            rows = []
            for i, sg in enumerate(st.session_state.subgroups, start=1):
                vals = sg["values"]
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
            st.download_button("CSV olarak indir", csv, "ph_olcumleri.csv", "text/csv")

# ---------------------------------------------------------------------------
# SEKME 3: Hakkinda
# ---------------------------------------------------------------------------
with tab_about:
    with st.container(border=True):
        st.subheader("SPC FoodLab hakkinda")
        st.markdown(
            """
Gida uretim hatlarinda pH olcumlerinden **istatistiksel proses kontrolu (SPC)**
grafigi ve **surec yeterlilik analizi (Cpk)** ureten bir arac.

**Kullanilan formuller:**
- X-bar UCL/LCL: `x̄̄ ± A2 × R̄`
- R chart UCL/LCL: `D4 × R̄` / `D3 × R̄`
- Cpk: `min[(USL - x̄̄)/(3σ̂), (x̄̄ - LSL)/(3σ̂)]`, `σ̂ = R̄/d2`

**Baseline mantigi:** Kontrol limitleri, "Baseline'i hesapla ve dondur"
butonuyla o ana kadar girilen verilerden bir kez hesaplanip sabitlenir.
Bu sayede sonradan eklenen (ozellikle kontrol disi) noktalar limitleri
kendine dogru cekmez - SPC'de limitlerin bir baseline donemden turetilip
sabit tutulmasi gerektigi icin bu mekanizma eklendi.

Detayli kaynak ve dogrulama notlari icin bkz. README.
            """
        )
