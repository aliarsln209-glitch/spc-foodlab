# Renk (L*a*b*) Paneli v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Renk (L*a*b*) Paneline izlenebilirlik alanları (lot_no/notes/otomatik timestamp), canlı swatch önizlemesi, duplicate-kayıt koruması, tek satır silme, düşük-n Cpk uyarısı, LSL/USL çizgileri, opsiyonel hedef swatch ve 3-eksen trend özet uyarısı eklemek — mevcut ΔE-YOK / 3-bağımsız-I-MR istatistik motorunu değiştirmeden.

**Architecture:** `src/color_lab.py`'deki saf veri modeli fonksiyonları (`append_color_sample`, yeni `remove_color_sample`) genişletilir; `src/app.py`'deki `render_color_lab_data_entry_tab()`/`render_color_lab_chart_tab()` (v1.7.1'de tanımlı) yeniden yazılır. Diğer parametrelerin ortak kodu (`spc_core.py`, `render_generic_*_tab()`) DEĞİŞMEZ.

**Tech Stack:** Python, Streamlit, pytest, matplotlib — mevcut stack, yeni bağımlılık yok.

**Spec:** `docs/superpowers/specs/2026-08-20-renk-paneli-v2-design.md`

## Global Constraints

- **ΔE YOK:** L*, a*, b* arasında hiçbir türetilmiş/birleşik metrik hesaplanmaz (spec'ten değişmedi).
- **Timestamp otomatik, kullanıcı girmez:** `datetime.now().isoformat(timespec="seconds")`.
- **`remove_color_sample`/`append_color_sample` orijinal listeyi DEĞİŞTİRMEZ** — yeni liste döner (mevcut `append_color_sample` deseniyle aynı, Streamlit session_state mutasyon hatalarından kaçınmak için).
- **Kapsam DIŞI (bu planda yapılmaz):** CSV/Excel toplu içe aktarma, PNG/CSV export, numune fotoğrafı, ürün bazlı LSL/USL tablosu, tüm-parametrelere-genelleme.
- **Düşük-n eşiği:** mevcut `MIN_RECOMMENDED_BASELINE = 20` (app.py:96) sabiti yeniden kullanılır, yeni bir eşik İCAT EDİLMEZ.
- **Mevcut testlerin TAMAMI (Renk Paneli dışı) değişmeden geçmeli** — hiçbir ortak kod değişmiyor.

---

### Task 1: `color_lab.py` — lot_no/notes/timestamp + `remove_color_sample`

**Files:**
- Modify: `src/color_lab.py`
- Modify: `tests/test_color_lab.py`

**Interfaces:**
- Consumes: yok
- Produces:
  - `append_color_sample(samples: list[dict], l: float, a: float, b: float, lot_no: str = "", notes: str = "") -> list[dict]` — yeni sözlük artık `{"L", "a", "b", "lot_no", "notes", "timestamp"}` anahtarlarını içerir.
  - `remove_color_sample(samples: list[dict], index: int) -> list[dict]` — belirtilen index'teki örneği çıkarıp YENİ listeyi döner.

- [ ] **Step 1: Write the failing tests**

`tests/test_color_lab.py` içindeki mevcut `test_append_color_sample_adds_entry_without_mutating_original` testini güncelle (yeni alanlar eklendiği için tam sözlük eşitliği artık farklı) ve yeni testleri ekle:

```python
# tests/test_color_lab.py - importlari guncelle
from color_lab import (
    append_color_sample,
    color_samples_to_series,
    lab_to_hex,
    remove_color_sample,
)


# mevcut test_append_color_sample_adds_entry_without_mutating_original'i SIL,
# yerine:

def test_append_color_sample_adds_entry_without_mutating_original():
    original = [{"L": 60.0, "a": 5.0, "b": 10.0, "lot_no": "", "notes": "", "timestamp": "x"}]
    result = append_color_sample(original, 61.0, 5.5, 10.5)
    assert len(original) == 1
    assert len(result) == 2
    assert result[1]["L"] == 61.0
    assert result[1]["a"] == 5.5
    assert result[1]["b"] == 10.5


def test_append_color_sample_defaults_lot_no_and_notes_to_empty_string():
    result = append_color_sample([], 65.0, 10.0, 20.0)
    assert result[0]["lot_no"] == ""
    assert result[0]["notes"] == ""


def test_append_color_sample_stores_provided_lot_no_and_notes():
    result = append_color_sample([], 65.0, 10.0, 20.0, lot_no="LOT-42", notes="vana temizlendi")
    assert result[0]["lot_no"] == "LOT-42"
    assert result[0]["notes"] == "vana temizlendi"


def test_append_color_sample_timestamp_is_iso_format_string():
    result = append_color_sample([], 65.0, 10.0, 20.0)
    ts = result[0]["timestamp"]
    assert isinstance(ts, str)
    # ISO 8601 "YYYY-MM-DDTHH:MM:SS" - datetime.fromisoformat ile geri parse edilebilmeli
    from datetime import datetime as _dt
    _dt.fromisoformat(ts)  # ValueError firlatirsa test FAIL olur


def test_remove_color_sample_removes_entry_without_mutating_original():
    original = [
        {"L": 60.0, "a": 5.0, "b": 10.0, "lot_no": "", "notes": "", "timestamp": "x"},
        {"L": 61.0, "a": 5.5, "b": 10.5, "lot_no": "", "notes": "", "timestamp": "y"},
    ]
    result = remove_color_sample(original, 0)
    assert len(original) == 2
    assert len(result) == 1
    assert result[0]["L"] == 61.0


def test_remove_color_sample_last_index():
    samples = [
        {"L": 60.0, "a": 5.0, "b": 10.0, "lot_no": "", "notes": "", "timestamp": "x"},
        {"L": 61.0, "a": 5.5, "b": 10.5, "lot_no": "", "notes": "", "timestamp": "y"},
    ]
    result = remove_color_sample(samples, 1)
    assert len(result) == 1
    assert result[0]["L"] == 60.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_color_lab.py -v`
Expected: `remove_color_sample` icin ImportError, digerleri icin KeyError/AssertionError (lot_no/notes/timestamp henuz yok).

- [ ] **Step 3: Write minimal implementation**

`src/color_lab.py`'nin en üstüne `from datetime import datetime` ekle, `append_color_sample`'i değiştir, `remove_color_sample`'i ekle:

```python
# src/color_lab.py - dosyanin en ustune (docstring'den sonra) ekle:
from datetime import datetime


# mevcut append_color_sample fonksiyonunu SIL, yerine:

def append_color_sample(
    samples: list[dict], l: float, a: float, b: float,
    lot_no: str = "", notes: str = "",
) -> list[dict]:
    """Yeni bir L*/a*/b* uclusunu (ayni olcume ait) listeye ekler - orijinal
    listeyi DEGISTIRMEZ, yeni bir liste doner (Streamlit session_state
    mutasyon hatalarindan kacinmak icin - bkz. build_bridge_subgroup_entry
    ile ayni desen, kopru sisteminden odunc alindi). lot_no/notes kullanici
    girer (opsiyonel, bos string varsayilan); timestamp OTOMATIK eklenir -
    kullanici elle girmez, hatali tarih riski olmasin diye (bkz.
    docs/superpowers/specs/2026-08-20-renk-paneli-v2-design.md)."""
    entry = {
        "L": l, "a": a, "b": b,
        "lot_no": lot_no, "notes": notes,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }
    return samples + [entry]


def remove_color_sample(samples: list[dict], index: int) -> list[dict]:
    """Belirtilen index'teki ornegi listeden cikarir - orijinal listeyi
    DEGISTIRMEZ, yeni bir liste doner (append_color_sample ile ayni
    desen)."""
    return samples[:index] + samples[index + 1:]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_color_lab.py -v`
Expected: PASS (10 passed - 3 lab_to_hex + 7 yeni/guncellenmis)

- [ ] **Step 5: Run full test suite to check for regressions**

Run: `pytest tests/ -q`
Expected: `tests/test_validation_suite.py::test_lab_to_hex_reference_csv` dahil TUM testler PASS - bu test sadece `lab_to_hex`'i cagirir, `append_color_sample` imza degisikliginden ETKILENMEZ.

- [ ] **Step 6: Commit**

```bash
git add src/color_lab.py tests/test_color_lab.py
git commit -m "feat: Renk Paneli veri modeline lot_no/notes/otomatik timestamp + remove_color_sample"
```

---

### Task 2: Veri Girişi sekmesi — canlı önizleme, lot_no/notes, duplicate koruması, satır silme

**Files:**
- Modify: `src/app.py:1323-1352` (`render_color_lab_data_entry_tab`)

**Interfaces:**
- Consumes: `append_color_sample`, `remove_color_sample`, `lab_to_hex` (Task 1 + mevcut import satırı `src/app.py:36` — `remove_color_sample` bu import listesine eklenmeli)
- Produces: `render_color_lab_data_entry_tab() -> None` (imza değişmez, davranış genişler)

- [ ] **Step 1: Import satırını güncelle**

`src/app.py:36` satırını değiştir:

```python
from color_lab import append_color_sample, color_samples_to_series, lab_to_hex, remove_color_sample
```

- [ ] **Step 2: `render_color_lab_data_entry_tab()`'i yeniden yaz**

`src/app.py:1323-1352` aralığındaki mevcut fonksiyonu (docstring dahil) tamamen şununla değiştir:

```python
def render_color_lab_data_entry_tab() -> None:
    """Renk (L*a*b*) Paneli - SEKME 1: birlesik veri girisi. v2 (bkz.
    docs/superpowers/specs/2026-08-20-renk-paneli-v2-design.md): st.form
    KALDIRILDI (L*/a*/b* normal widget - her degisiklikte anlik rerun,
    canli swatch onizlemesi mumkun olsun diye), lot_no/notes eklendi,
    ekleme sonrasi widget'lar sifirlanir (form'un clear_on_submit=True'una
    esdeger - yanlislikla ayni olcumun iki kez eklenmesini onler), gecmis
    tabloda tek satir silme var."""
    st.subheader("\U0001F3A8 Renk (L*a*b*) - Birlesik Olcum Girisi")
    st.caption(
        "L*, a*, b* ayni spektrofotometre/kolorimetre okumasindan cikar - "
        "ucu birlikte, tek formda girilir. Istatistiksel olarak DAIMA "
        "bagimsiz 3 I-MR serisi olarak izlenir (ΔE hesaplanmaz)."
    )

    c1, c2, c3 = st.columns(3)
    l_val = c1.number_input(
        "L* (0-100)", min_value=0.0, max_value=100.0, value=65.0, step=0.1,
        key="color_lab_l_input",
    )
    a_val = c2.number_input(
        "a* (-128/+127)", min_value=-128.0, max_value=127.0, value=10.0, step=0.1,
        key="color_lab_a_input",
    )
    b_val = c3.number_input(
        "b* (-128/+127)", min_value=-128.0, max_value=127.0, value=20.0, step=0.1,
        key="color_lab_b_input",
    )

    _preview_hex = lab_to_hex(l_val, a_val, b_val)
    pc1, pc2 = st.columns([1, 4])
    with pc1:
        st.markdown(
            f'<div style="width:48px;height:48px;border-radius:8px;'
            f'background-color:{_preview_hex};border:1px solid #888;"></div>',
            unsafe_allow_html=True,
        )
    with pc2:
        st.caption(
            f"Canli onizleme: {_preview_hex}. ⚠️ Yaklasik onizleme, D65 "
            "aydinlatici varsayimiyla hesaplanir - cihazinizin aydinlatici/"
            "gozlemci ayari farkliysa gercek rengi yansitmayabilir."
        )

    lot_no = st.text_input("Parti/Lot No (opsiyonel)", key="color_lab_lot_input")
    notes = st.text_area("Not (opsiyonel)", key="color_lab_notes_input")

    if st.button("Olcumu Ekle", type="primary"):
        st.session_state.color_lab_samples = append_color_sample(
            st.session_state.color_lab_samples, l_val, a_val, b_val,
            lot_no=lot_no, notes=notes,
        )
        st.success(f"Eklendi: L*={l_val:g}, a*={a_val:g}, b*={b_val:g}")
        # Widget'lari varsayilana dondur (st.form'un clear_on_submit=True'una
        # esdeger) - aksi halde ayni degerler ekranda kalir, kullanici
        # farkinda olmadan tekrar "Olcumu Ekle"ye basarsa AYNI satir ikinci
        # kez eklenir (canli denetimde bulunan L=65,a=10,b=20 duplicate'i).
        for _key in (
            "color_lab_l_input", "color_lab_a_input", "color_lab_b_input",
            "color_lab_lot_input", "color_lab_notes_input",
        ):
            if _key in st.session_state:
                del st.session_state[_key]
        st.rerun()

    n_samples = len(st.session_state.color_lab_samples)
    st.caption(f"Toplam {n_samples} olcum.")
    if n_samples > 0:
        if st.button("Tum olcumleri temizle", key="color_lab_clear"):
            st.session_state.color_lab_samples = []
            st.rerun()

        st.dataframe(
            st.session_state.color_lab_samples, width="stretch",
            column_order=["timestamp", "lot_no", "L", "a", "b", "notes"],
        )

        st.caption("Tek satir sil:")
        for _i, _s in enumerate(st.session_state.color_lab_samples):
            _dcol1, _dcol2 = st.columns([5, 1])
            with _dcol1:
                st.caption(
                    f"#{_i + 1}: L*={_s['L']:g}, a*={_s['a']:g}, b*={_s['b']:g}"
                    + (f" (lot: {_s['lot_no']})" if _s["lot_no"] else "")
                )
            with _dcol2:
                if st.button("\U0001F5D1\U0000FE0F", key=f"color_lab_del_{_i}"):
                    st.session_state.color_lab_samples = remove_color_sample(
                        st.session_state.color_lab_samples, _i
                    )
                    st.rerun()
```

- [ ] **Step 3: Run full test suite (regresyon kontrolü — bu adımda henüz UI-özel bir pytest testi yok, sadece kaynak kodun diğer testleri bozmadığını doğruluyoruz)**

Run: `pytest tests/ -q`
Expected: TUM testler PASS (bu task sadece app.py icinde Renk Paneli'ne ozel bir fonksiyonu degistiriyor, diger hicbir test bu fonksiyonu import/cagirmiyor).

- [ ] **Step 4: Manuel doğrulama (Streamlit'i çalıştırıp gerçekten dene)**

Run: `streamlit run src/app.py` (yerel), sidebar'dan "Renk (L*a*b*)" sec, Veri Girisi sekmesinde:
1. L*/a*/b* degerlerini degistir - swatch'in ANINDA (rerun'la) guncellendigini gozle.
2. lot_no="LOT-1", not="test" gir, "Olcumu Ekle" bas - basari mesaji + tablo satirinda lot_no/timestamp gorunmeli, inputlar sifirlanmis olmali (65.0/10.0/20.0/bos'a donmus).
3. Ayni degerlerle tekrar "Olcumu Ekle"ye bas - iki ayri satir eklenir (bu ARTIK bilincli bir kullanici eylemi, yanlislikla degil, cunku inputlar sifirlanmisti ve kullanici BILEREK ayni degerleri yeniden girdi).
4. Bir satiri 🗑️ ile sil - tablo satiri kaybolmali, digerleri kalmali.

- [ ] **Step 5: Commit**

```bash
git add src/app.py
git commit -m "feat: Renk Paneli Veri Girisi - canli onizleme, lot_no/notes, duplicate korumasi, satir silme"
```

---

### Task 3: Chart & Cpk sekmesi — düşük-n uyarısı, LSL/USL çizgileri, hedef swatch, trend özeti

**Files:**
- Modify: `src/app.py:1354-1412` (`render_color_lab_chart_tab`)

**Interfaces:**
- Consumes: `MIN_RECOMMENDED_BASELINE` (app.py:96, mevcut modül-seviyesi sabit), `annotate_hline(ax, x_pos, y_value, text, color)` (app.py:1073, mevcut), `cpk_capability_badge(cpk, cpk_valid) -> (emoji, label, color)` (app.py:860, mevcut), `format_cpk` (result_helpers import, mevcut), diğerleri Task 1/2'deki gibi.
- Produces: `render_color_lab_chart_tab() -> None` (imza değişmez, davranış genişler)

- [ ] **Step 1: `render_color_lab_chart_tab()`'i yeniden yaz**

`src/app.py:1354-1412` aralığındaki mevcut fonksiyonu tamamen şununla değiştir (dikkat: mevcut kodda `cpk_capability_badge(cpk, True)` çağrısı `_emoji, badge_label, _color` şeklinde unpack ediliyordu ama `format_cpk`/`st.metric` çağrısı YOKTU görünen kod parçasında `st.metric(f"{axis_name} Cpk", format_cpk(cpk))` şeklindeydi — bu davranış AYNEN korunur, sadece etrafına düşük-n kontrolü eklenir):

```python
def render_color_lab_chart_tab() -> None:
    """Renk (L*a*b*) Paneli - SEKME 2: 3 bagimsiz I-MR karti + swatch. v2
    (bkz. docs/superpowers/specs/2026-08-20-renk-paneli-v2-design.md):
    dusuk-n uyarisi (Cpk rozeti yerine), LSL/USL cizgileri, opsiyonel hedef
    swatch, 3-eksen trend ozet uyarisi eklendi. Baseline dondurma/Nelson
    kurallari HALA YOK (v1 kapsam kararindan degismedi) - her render'da TUM
    veriyle canli I-MR limitleri hesaplanir."""
    samples = st.session_state.color_lab_samples
    if len(samples) < 2:
        render_empty_state("\U0001F3A8", "Grafik icin en az 2 olcum gerekli. Once Veri Girisi sekmesinden ekleyin.")
        return

    l_vals, a_vals, b_vals = color_samples_to_series(samples)
    last = samples[-1]
    swatch_hex = lab_to_hex(last["L"], last["a"], last["b"])

    st.markdown("**Hedef renk karsilastirmasi (opsiyonel, ΔE HESAPLANMAZ - sadece gorsel)**")
    tc1, tc2, tc3, tc4 = st.columns(4)
    _target_enabled = tc1.checkbox("Hedef renk gir", key="color_lab_target_enabled")
    target_hex = None
    if _target_enabled:
        _tl = tc2.number_input("Hedef L*", min_value=0.0, max_value=100.0, value=65.0, step=0.1, key="color_lab_target_l")
        _ta = tc3.number_input("Hedef a*", min_value=-128.0, max_value=127.0, value=10.0, step=0.1, key="color_lab_target_a")
        _tb = tc4.number_input("Hedef b*", min_value=-128.0, max_value=127.0, value=20.0, step=0.1, key="color_lab_target_b")
        target_hex = lab_to_hex(_tl, _ta, _tb)

    sc1, sc2, sc3 = st.columns([1, 1, 3]) if target_hex else st.columns([1, 4])
    with sc1:
        st.caption("Son olcum")
        st.markdown(
            f'<div style="width:60px;height:60px;border-radius:8px;'
            f'background-color:{swatch_hex};border:1px solid #888;"></div>',
            unsafe_allow_html=True,
        )
    if target_hex:
        with sc2:
            st.caption("Hedef")
            st.markdown(
                f'<div style="width:60px;height:60px;border-radius:8px;'
                f'background-color:{target_hex};border:1px solid #888;"></div>',
                unsafe_allow_html=True,
            )
        _caption_col = sc3
    else:
        _caption_col = sc2
    with _caption_col:
        st.caption(
            f"Son olcum onizlemesi: {swatch_hex} (L*={last['L']:g}, a*={last['a']:g}, b*={last['b']:g}). "
            "⚠️ Yaklasik onizleme, D65 aydinlatici varsayimiyla hesaplanir - "
            "cihazinizin aydinlatici/gozlemci ayari farkliysa gercek rengi yansitmayabilir. "
            "Karar verici DEGILDIR."
        )

    axis_configs = [
        ("L*", l_vals, FOOD_QUALITY_PARAMETER_CONFIG["L*"]),
        ("a*", a_vals, FOOD_QUALITY_PARAMETER_CONFIG["a*"]),
        ("b*", b_vals, FOOD_QUALITY_PARAMETER_CONFIG["b*"]),
    ]

    n_current = len(samples)
    _out_of_control_axes: list[str] = []
    cols = st.columns(3)
    for col, (axis_name, values, axis_cfg) in zip(cols, axis_configs):
        with col:
            st.markdown(f"**{axis_name}**")
            x_bar = sum(values) / len(values)
            mr_list = compute_moving_ranges(values)
            mr_bar = sum(mr_list) / len(mr_list)
            lsl, usl = axis_cfg["default_lsl"], axis_cfg["default_usl"]
            spec_valid = is_spec_valid(axis_cfg["one_sided"], lsl, usl)
            cpk = None
            if spec_valid:
                cpk = compute_cpk(x_bar, mr_bar, 2, lsl, usl, one_sided=axis_cfg["one_sided"])
                if cpk != float("-inf") and cpk < 1.0:
                    _out_of_control_axes.append(axis_name)
                if n_current < MIN_RECOMMENDED_BASELINE:
                    st.warning(
                        f"Cpk guvenilir yorum icin en az {MIN_RECOMMENDED_BASELINE} "
                        f"olcum onerilir (su an n={n_current})."
                    )
                    st.caption(f"{axis_name} Cpk (gosterge): {format_cpk(cpk)}")
                else:
                    _emoji, badge_label, _color = cpk_capability_badge(cpk, True)
                    st.metric(f"{axis_name} Cpk", format_cpk(cpk))
                    st.caption(f"{_emoji} {badge_label}")
            else:
                st.caption("Gecersiz spesifikasyon (LSL >= USL)")

            fig, ax = plt.subplots(figsize=(3.2, 2.4))
            imr = compute_imr_limits(x_bar, mr_bar)
            ax.plot(range(1, len(values) + 1), values, marker="o", markersize=3)
            ax.axhline(imr.ucl_i, color="red", linestyle="--", linewidth=0.8)
            ax.axhline(imr.lcl_i, color="red", linestyle="--", linewidth=0.8)
            ax.axhline(x_bar, color="gray", linestyle=":", linewidth=0.8)
            if spec_valid:
                annotate_hline(ax, len(values), usl, f"USL={usl:g}", "#e8590c")
                ax.axhline(usl, color="#e8590c", linestyle="-.", linewidth=0.8)
                if not axis_cfg["one_sided"]:
                    annotate_hline(ax, len(values), lsl, f"LSL={lsl:g}", "#e8590c")
                    ax.axhline(lsl, color="#e8590c", linestyle="-.", linewidth=0.8)
            style_chart(fig, ax, dark=(st.session_state.get("chart_theme") == "Koyu"))
            st.pyplot(fig)
            plt.close(fig)

    if _out_of_control_axes:
        st.warning(f"⚠️ Kontrol disi eksen(ler): {', '.join(_out_of_control_axes)} — digerleri normal.")
    else:
        st.success("✅ Uc eksen de kontrol altinda (Cpk >= 1.0 veya spesifikasyon tanimsiz).")
```

**Not (implementer için):** `_out_of_control_axes` listesi Cpk<1.0 eşiğine göre dolar (spesifikasyon geçersizse veya Cpk hesaplanamıyorsa o eksen listeye eklenmez — "kontrol dışı" değil "değerlendirilemez" anlamına gelir, bu ayrım bilinçlidir, karıştırılmasın).

- [ ] **Step 2: Run full test suite**

Run: `pytest tests/ -q`
Expected: TUM testler PASS.

- [ ] **Step 3: Manuel doğrulama (Streamlit'i çalıştırıp gerçekten dene)**

Run: `streamlit run src/app.py`, "Renk (L*a*b*)" sec, en az 2 (düşük-n uyarısını görmek için) ve ayrıca en az 20 (rozet moduna geçişi görmek için) ölçüm ekleyip Chart & Cpk sekmesinde:
1. n<20 iken her eksen kartında rozet YERİNE "Cpk güvenilir yorum için..." uyarısı görünmeli.
2. n>=20 iken normal rozet ("Yeterli"/"Sınırda"/"Yetersiz") görünmeli.
3. Grafiklerde turuncu kesikli USL/LSL çizgileri görünmeli.
4. "Hedef renk gir" checkbox'ını işaretle - ikinci swatch görünmeli.
5. Bir eksenin LSL/USL'ini bilerek dar aralığa çekip (örn. b* icin LSL=19,USL=21) Cpk<1.0 yap - alt kısımdaki trend özetinde "Kontrol dışı eksen(ler): b*" görünmeli.

- [ ] **Step 4: Commit**

```bash
git add src/app.py
git commit -m "feat: Renk Paneli Chart & Cpk - dusuk-n uyarisi, LSL/USL cizgileri, hedef swatch, trend ozeti"
```

---

### Task 4: Statik regresyon testi + tam suite + versiyon notu

**Files:**
- Modify: `tests/test_app_render_smoke.py`
- Modify: `METHODOLOGY.md`

**Interfaces:**
- Consumes: `PARAMETER_CATEGORIES`, `FOOD_QUALITY_PARAMETER_CONFIG` (mevcut, `constants.py`)
- Produces: yok (sadece test + belge)

- [ ] **Step 1: Write the regression test**

`tests/test_app_render_smoke.py`'nin sonuna ekle (mevcut dosyanın kaynak-kodu-statik-inceleme deseniyle aynı - bkz. dosyanın başındaki not, Streamlit AppTest widget-senkronizasyon kırılganlığı nedeniyle bilerek kullanılmıyor):

```python
def test_color_lab_data_entry_uses_widget_keys_not_form():
    # Task 2: st.form KALDIRILDI (canli onizleme icin) - regresyon: biri
    # yanlislikla st.form'u geri getirirse bu testin yakalamasi beklenir.
    with open(APP_PATH, encoding="utf-8") as f:
        source = f.read()
    start = source.index("def render_color_lab_data_entry_tab()")
    end = source.index("def render_color_lab_chart_tab()")
    body = source[start:end]
    assert 'st.form("color_lab_entry_form")' not in body
    assert 'key="color_lab_l_input"' in body
    assert 'key="color_lab_lot_input"' in body


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
```

- [ ] **Step 2: Run test to verify it passes**

Run: `pytest tests/test_app_render_smoke.py -v`
Expected: PASS (Task 2/3 doğru uygulandıysa)

- [ ] **Step 3: `METHODOLOGY.md`'ye v1.7.1'in hemen altına kısa bir "v1.7.2" notu ekle**

`METHODOLOGY.md` içinde `**v1.8 veya sonrası — Tüm parametrelere lot_no/timestamp/notes**` başlığından HEMEN ÖNCE (v1.7.1 bölümünün sonunda), ekle:

```markdown
**v1.7.2 — Renk Paneli izlenebilirlik + okunabilirlik iyileştirmeleri**

v1.7.1'in dar v1 kapsamına (bkz. yukarı) canlı denetimde gelen geri
bildirimle şu eklendi: `lot_no`/`notes`/otomatik `timestamp` (Renk
Paneline ÖZGÜ — tüm parametrelere genelleme aşağıdaki v1.8+ notunun
konusu), canlı swatch önizlemesi (form kaldırıldı), duplicate-kayıt
koruması (ekleme sonrası alanlar sıfırlanır), tek satır silme, düşük-n
(<20) Cpk rozeti yerine güvenilirlik uyarısı, grafiklerde LSL/USL
çizgileri, opsiyonel hedef renk swatch'i (ΔE HESAPLANMAZ, sadece
görsel), 3-eksen trend özet uyarısı. Detay: `docs/superpowers/specs/
2026-08-20-renk-paneli-v2-design.md`. CSV/Excel içe aktarma, PNG/CSV
export, numune fotoğrafı, ürün bazlı LSL/USL tablosu HALA YOK (aynı
gerekçelerle ertelendi).
```

- [ ] **Step 4: Versiyon rozetini güncelle**

`src/app.py`'nin en altındaki `st.caption(f"SPC FoodLab v1.7.1 · ...")` satırını `v1.7.2` yap (Task 7'de v1.7.1'e güncellenmişti, bkz. `grep -n "SPC FoodLab v1" src/app.py`).

- [ ] **Step 5: Run full test suite one final time**

Run: `pytest tests/ -q`
Expected: TUM testler PASS.

- [ ] **Step 6: Commit**

```bash
git add tests/test_app_render_smoke.py METHODOLOGY.md src/app.py
git commit -m "test: Renk Paneli v2 statik regresyon testleri + METHODOLOGY.md v1.7.2 notu + versiyon rozeti"
```
