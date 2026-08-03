"""SPC FoodLab - pH Istatistiksel Proses Kontrolu (Streamlit MVP)."""

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from constants import SHIFT_OPTIONS, SUBGROUP_SIZE
from demo_data import generate_demo_subgroups
from spc_core import compute_cpk, compute_xbar_r_limits

MIN_RECOMMENDED_BASELINE = 20

st.set_page_config(page_title="SPC FoodLab", page_icon="\U0001F4CA", layout="wide")

if "subgroups" not in st.session_state:
    st.session_state.subgroups = []  # list of dict: {"shift": str, "values": list[float]}
if "baseline" not in st.session_state:
    st.session_state.baseline = None  # dict: {"x_double_bar", "r_bar", "n_baseline"}

with st.sidebar:
    st.subheader("Ayarlar")
    chart_theme = st.selectbox("Grafik temasi", ["Acik", "Koyu"], key="chart_theme")


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

# ---------------------------------------------------------------------------
# SEKME 1: Veri Girisi / Goruntuleme
# ---------------------------------------------------------------------------
with tab_data:
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
        if st.button("\U0001F9EA Demo veri yukle (24 alt grup)"):
            demo = generate_demo_subgroups()
            st.session_state.subgroups = [
                {"shift": SHIFT_OPTIONS[i % len(SHIFT_OPTIONS)], "values": vals}
                for i, vals in enumerate(demo)
            ]
            st.session_state.baseline = None
            st.success("Demo veri yuklendi.")
    with col_b:
        if st.button("\U0001F5D1️ Tum verileri temizle"):
            st.session_state.subgroups = []
            st.session_state.baseline = None
            st.info("Veriler temizlendi.")

    st.divider()
    st.subheader("Kayitli alt gruplar")

    if not st.session_state.subgroups:
        st.info("Henuz veri yok. Yukaridan manuel ekleyin veya demo veri yukleyin.")
    else:
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
# SEKME 2: X-bar/R Chart & Cpk
# ---------------------------------------------------------------------------
with tab_chart:
    if len(st.session_state.subgroups) < 2:
        st.warning("Grafik icin en az 2 alt grup gerekli. Once veri girisi sekmesinden veri ekleyin.")
    else:
        st.subheader("Spesifikasyon limitleri (Cpk icin)")
        col1, col2 = st.columns(2)
        with col1:
            lsl = st.number_input("Alt spesifikasyon limiti (LSL)", value=6.8, step=0.01, format="%.2f")
        with col2:
            usl = st.number_input("Ust spesifikasyon limiti (USL)", value=7.2, step=0.01, format="%.2f")

        means = [sum(sg["values"]) / len(sg["values"]) for sg in st.session_state.subgroups]
        ranges = [max(sg["values"]) - min(sg["values"]) for sg in st.session_state.subgroups]

        live_x_double_bar = sum(means) / len(means)
        live_r_bar = sum(ranges) / len(ranges)

        st.divider()
        st.subheader("Kontrol limitleri (Baseline)")

        baseline = st.session_state.baseline

        if baseline is None:
            st.info(
                "Baseline henuz dondurulmadi. Asagidaki UCL/LCL, mevcut TUM alt "
                "gruplardan canli hesaplaniyor; yeni veri eklendikce degisir. "
                "Bu, kontrol disi bir noktanin limitleri kendine dogru cekmesine "
                "yol acabilir (SPC'de 'limitleri kovalamak' olarak bilinen hata)."
            )
            n_current = len(st.session_state.subgroups)
            if n_current < MIN_RECOMMENDED_BASELINE:
                st.warning(
                    f"Su an {n_current} alt grup var. Guvenilir kontrol limitleri "
                    f"icin en az {MIN_RECOMMENDED_BASELINE} alt grup onerilir "
                    "(Montgomery, Introduction to Statistical Quality Control)."
                )
            if st.button("\U0001F4CC Baseline'i hesapla ve dondur"):
                st.session_state.baseline = {
                    "x_double_bar": live_x_double_bar,
                    "r_bar": live_r_bar,
                    "n_baseline": n_current,
                }
                st.rerun()

            x_double_bar = live_x_double_bar
            r_bar = live_r_bar
        else:
            x_double_bar = baseline["x_double_bar"]
            r_bar = baseline["r_bar"]
            st.success(
                f"Baseline donduruldu: ilk {baseline['n_baseline']} alt grup ile "
                "hesaplandi. UCL/LCL artik sabit; yeni eklenen alt gruplar bu "
                "limitlerle karsilastirilir, limitleri degistirmez."
            )
            if st.button("\U0001F513 Baseline'i sifirla"):
                st.session_state.baseline = None
                st.rerun()

        limits = compute_xbar_r_limits(x_double_bar, r_bar, SUBGROUP_SIZE)
        cpk = compute_cpk(x_double_bar, r_bar, SUBGROUP_SIZE, lsl, usl)

        st.divider()
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Genel Ortalama (x̄̄)", f"{x_double_bar:.4f}")
        m2.metric("Ortalama Range (R̄)", f"{r_bar:.4f}")
        m3.metric("UCL / LCL (X-bar)", f"{limits.ucl_x:.4f} / {limits.lcl_x:.4f}")
        m4.metric("Cpk", f"{cpk:.3f}")

        if cpk < 1.0:
            st.error("Cpk < 1.0: Surec yeterli degil (spesifikasyon limitlerine gore).")
        elif cpk < 1.33:
            st.warning("Cpk 1.0-1.33 arasi: Surec marjinal yeterli.")
        else:
            st.success("Cpk >= 1.33: Surec yeterli.")

        st.divider()
        st.subheader("X-bar Kontrol Grafigi")

        indices = list(range(1, len(means) + 1))
        dark = chart_theme == "Koyu"
        out_of_control_x = [i for i, m in enumerate(means) if m > limits.ucl_x or m < limits.lcl_x]

        fig, ax = plt.subplots(figsize=(10, 4))
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
        ax.legend(loc="upper left", fontsize=8)
        style_chart(fig, ax, dark)
        st.pyplot(fig)
        plt.close(fig)

        st.subheader("R Kontrol Grafigi")
        out_of_control_r = [i for i, r in enumerate(ranges) if r > limits.ucl_r or r < limits.lcl_r]

        fig2, ax2 = plt.subplots(figsize=(10, 3))
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
        ax2.legend(loc="upper left", fontsize=8)
        style_chart(fig2, ax2, dark)
        st.pyplot(fig2)
        plt.close(fig2)

        if out_of_control_x or out_of_control_r:
            groups = sorted({i + 1 for i in out_of_control_x} | {i + 1 for i in out_of_control_r})
            st.warning(
                f"Kontrol disi alt gruplar: {groups} "
                "- surec bu noktalarda 'kontrol disi' kabul edilir."
            )

# ---------------------------------------------------------------------------
# SEKME 3: Hakkinda
# ---------------------------------------------------------------------------
with tab_about:
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
