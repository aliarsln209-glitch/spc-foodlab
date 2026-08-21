# Paylaşılan `subgroups` İzlenebilirlik Alanları Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `L*/a*/b*` HARİÇ tüm 23 parametrenin paylaştığı `st.session_state.subgroups` şemasına `lot_no`, `notes`, `urun`, `timestamp` alanlarını eklemek — manuel giriş, CSV import/geçmiş-tablo-düzenleme (aynı `parse_uploaded_dataframe` fonksiyonu üzerinden), Excel/pano yapıştırma ve QC Dönüştürücü köprüsü dahil TÜM giriş yollarında.

**Architecture:** Mevcut `{"shift": str, "values": [...]}` sözlük şeması 4 yeni alanla genişler. `csv_io.parse_uploaded_dataframe()` bu alanları (varsa) koruyacak, (yoksa) varsayılana düşecek şekilde genişletilir — bu fonksiyon hem CSV import'ta hem geçmiş-tablo "Değişiklikleri kaydet" akışında PAYLAŞILDIĞI için tek bir değişiklik ikisini de kapsar. `qc_converters.build_bridge_subgroup_entry()` imza değişikliği (`shift_label` yerine ayrı `shift`/`notes`/`urun` parametreleri) 5 QC Dönüştürücü köprüsünün ortak çağırdığı `render_bridge_widget()`'a tek noktadan yansır.

**Tech Stack:** Python, Streamlit, pytest — mevcut stack, yeni bağımlılık yok.

**Spec:** `docs/superpowers/specs/2026-08-21-paylasilan-subgroups-izlenebilirlik-design.md`

## Global Constraints

- **Kapsam:** `L*/a*/b*` HARİÇ tüm 23 parametre. Renk Paneli'ne (`color_lab_samples`, ayrı model) dokunulmaz.
- **`timestamp` her zaman otomatik:** `datetime.now().isoformat(timespec="seconds")` — kullanıcı elle girmez.
- **`lot_no`/`notes` opsiyonel, varsayılan `""`.**
- **`urun` otomatik damgalanır:** kullanıcı hiçbir yeni UI görmez — o an `st.session_state.get("product_select", "")` değeri okunup kaydedilir.
- **CSV import'a YENİ bir UI/davranış eklenmez** — beklenen sütun mesajları, "Boş şablon indir" içeriği değişmez, eski formatlı bir CSV hâlâ sorunsuz yüklenir. `parse_uploaded_dataframe`'e dokunmak SADECE mevcut "Değişiklikleri kaydet" özelliğinin bu 4 alanı sessizce silmemesi için zorunludur (bkz. spec, "İkinci düzeltme").
- **Demo veri üreticisi ve `parse_pasted_text` DEĞİŞMEZ** — bu yollardan gelen kayıtlar yeni alanlara sahip olmadan üretilir/eklenir, çağıran taraf (app.py) onları ekleme anında damgalar (paste) veya hiç damgalamaz (demo — `.get(key, "")` ile güvenli okunur).
- **Bridge (QC Dönüştürücü) X-bar/R hedeflerinde artık gerçek bir Vardiya seçici var** — sabit `"Sabah"` varsayımı YOK. I-MR hedeflerde `shift="-"` (değişmedi).
- **Mevcut tüm testler (267+) değişmeden geçmeli.**
- **Canlı (Playwright) doğrulama zorunlu adım** (spec'te detaylandırıldığı gibi) — `urun` alanının köprü noktalarında doğru ürünü yakaladığı ve Vardiya seçicinin `render_shift_comparison`'da doğru grupladığı ekran görüntüsüyle kanıtlanacak.

---

### Task 1: `qc_converters.build_bridge_subgroup_entry` imza değişikliği

**Files:**
- Modify: `src/qc_converters.py:39-64` (`build_bridge_subgroup_entry`)
- Test: `tests/test_qc_converters.py`

**Interfaces:**
- Consumes: yok
- Produces: `build_bridge_subgroup_entry(value: float | list[float], shift: str, notes: str = "", urun: str = "") -> dict` — artık `{"shift", "values", "notes", "urun", "timestamp"}` anahtarlarını içerir. `lot_no` bu fonksiyonda YOK (köprüler kullanıcıdan lot_no almaz — sadece manuel giriş formunda var, bkz. Task 4) — okuyan taraflar `.get("lot_no", "")` ile güvenli okur.

- [ ] **Step 1: Mevcut 6 testi yeni imzaya güncelle (bunlar `shift_label=` kullanıyor, imza değişince kırılacak)**

`tests/test_qc_converters.py` içindeki şu 6 testi (satır ~38-70) BUL ve TAMAMEN şununla DEĞİŞTİR (`shift_label=` yerine `shift=`/`notes=`, dict eşitlik kontrolleri yeni alanları da içerecek şekilde genişletildi):

```python
def test_build_bridge_subgroup_entry_shape():
    entry = build_bridge_subgroup_entry(value=12.34, shift="-", notes="QC Donusturucu - Test")
    assert entry["shift"] == "-"
    assert entry["values"] == [12.34]
    assert entry["notes"] == "QC Donusturucu - Test"
    assert entry["urun"] == ""
    assert "timestamp" in entry


def test_build_bridge_subgroup_entry_rejects_non_finite_value():
    with pytest.raises(ValueError, match="sonlu"):
        build_bridge_subgroup_entry(value=float("nan"), shift="-", notes="QC Donusturucu - Test")


def test_build_bridge_subgroup_entry_accepts_list_for_xbar_r():
    entry = build_bridge_subgroup_entry(
        value=[1.1, 1.2, 1.0, 1.3], shift="Sabah", notes="QC Donusturucu - Test XR",
    )
    assert entry["shift"] == "Sabah"
    assert entry["values"] == [1.1, 1.2, 1.0, 1.3]
    assert entry["notes"] == "QC Donusturucu - Test XR"


def test_build_bridge_subgroup_entry_rejects_empty_list():
    with pytest.raises(ValueError, match="bos olamaz"):
        build_bridge_subgroup_entry(value=[], shift="Sabah", notes="QC Donusturucu - Test XR")


def test_build_bridge_subgroup_entry_rejects_non_finite_value_in_list():
    with pytest.raises(ValueError, match="sonlu"):
        build_bridge_subgroup_entry(
            value=[1.0, float("nan"), 1.2], shift="Sabah", notes="QC Donusturucu - Test XR",
        )


def test_build_bridge_subgroup_entry_single_float_still_works():
    # Faz 1 davranisi degismemeli - regresyon kontrolu
    entry = build_bridge_subgroup_entry(value=12.34, shift="-", notes="QC Donusturucu - Test")
    assert entry["shift"] == "-"
    assert entry["values"] == [12.34]
```

- [ ] **Step 2: Run updated tests to verify they fail (yeni imza henüz yok)**

Run: `pytest tests/test_qc_converters.py -v`
Expected: FAIL - `build_bridge_subgroup_entry() got an unexpected keyword argument 'shift'` (mevcut kod hâlâ `shift_label` bekliyor).

- [ ] **Step 3: Write the NEW failing tests**

Aynı dosyaya, yukarıdaki güncellenmiş testlerin ALTINA ekle (dosyanın import bloğuna `from datetime import datetime as _dt` ekle, mevcut importların yanına):

```python
def test_build_bridge_subgroup_entry_individual_uses_given_shift_and_notes():
    entry = build_bridge_subgroup_entry(5.5, shift="-", notes="QC Donusturucu - Totox")
    assert entry["shift"] == "-"
    assert entry["values"] == [5.5]
    assert entry["notes"] == "QC Donusturucu - Totox"
    assert entry["urun"] == ""


def test_build_bridge_subgroup_entry_xbar_r_uses_given_shift():
    entry = build_bridge_subgroup_entry([1.0, 2.0, 3.0], shift="Ogle", notes="QC Donusturucu - Titre Edilebilir Asitlik")
    assert entry["shift"] == "Ogle"
    assert entry["values"] == [1.0, 2.0, 3.0]
    assert entry["notes"] == "QC Donusturucu - Titre Edilebilir Asitlik"


def test_build_bridge_subgroup_entry_stores_urun_when_given():
    entry = build_bridge_subgroup_entry(5.5, shift="-", notes="x", urun="Zeytinyagi (naturel sizma)")
    assert entry["urun"] == "Zeytinyagi (naturel sizma)"


def test_build_bridge_subgroup_entry_timestamp_is_iso_format_string():
    entry = build_bridge_subgroup_entry(5.5, shift="-", notes="x")
    _dt.fromisoformat(entry["timestamp"])  # ValueError firlatirsa test FAIL olur


def test_build_bridge_subgroup_entry_no_longer_accepts_shift_label():
    import pytest
    with pytest.raises(TypeError):
        build_bridge_subgroup_entry(5.5, shift_label="eski API")
```

- [ ] **Step 4: Run all (updated + new) tests to verify they fail**

Run: `pytest tests/test_qc_converters.py -v`
Expected: FAIL - hepsi `build_bridge_subgroup_entry() got an unexpected keyword argument 'shift'` ile (mevcut kod hâlâ `shift_label` bekliyor).

- [ ] **Step 5: Write minimal implementation**

`src/qc_converters.py`'nin en üstüne `from datetime import datetime` ekle (henüz yoksa), sonra mevcut `build_bridge_subgroup_entry` fonksiyonunu tamamen şununla değiştir:

```python
def build_bridge_subgroup_entry(
    value: float | list[float], shift: str, notes: str = "", urun: str = "",
) -> dict:
    """QC donusturucu sonucunu, mevcut subgroups sema formatina cevirir.

    app.py'deki st.session_state.subgroups listesi {"shift": str, "values":
    list[float], "notes": str, "urun": str, "timestamp": str} sekli bekler
    (bkz. docs/superpowers/specs/2026-08-21-paylasilan-subgroups-
    izlenebilirlik-design.md) - kopru bu formati degistirmez, sadece dogru
    sekli uretir.

    v2 (bu spec): eskiden 'shift_label' parametresi kaynak etiketini
    ('QC Donusturucu - Totox' gibi) shift alanina YAZARAK hackliyordu - bu,
    render_shift_comparison()'in bu kayitlari HICBIR vardiya grubuna dahil
    etmemesine (sessiz disi birakma) yol aciyordu. Artik 'shift' GERCEK bir
    vardiya degeri (cagiran taraf - render_bridge_widget - kullanicidan
    aliyor veya I-MR icin "-" veriyor), kaynak etiketi 'notes' alanina
    yaziliyor. timestamp OTOMATIK eklenir, kullanici girmez.

    value bir float ise (I-MR koprusu - tek olcum): {"values": [value]}.
    value bir list[float] ise (X-bar/R koprusu - n adet tekrar olcumu,
    ayni numunenin n kez titre edilmesi gibi gercek bir alt grup): tum
    liste dogrudan {"values": ...} olarak kullanilir. Hedefin X-bar/R
    olup olmadigina ve n'in dogru sayida olup olmadigina bu fonksiyon
    KARAR VERMEZ - o kontrol render_bridge_widget()'ta (app.py) yapilir,
    burasi sadece sekil/gecerlilik kontrolu yapan saf bir donusum katmanidir.
    """
    if isinstance(value, list):
        if not value:
            raise ValueError("kopru degerleri listesi bos olamaz")
        for v in value:
            if not math.isfinite(v):
                raise ValueError("kopru degeri sonlu bir sayi olmalidir (NaN/inf kabul edilmez)")
        values = list(value)
    else:
        if not math.isfinite(value):
            raise ValueError("kopru degeri sonlu bir sayi olmalidir (NaN/inf kabul edilmez)")
        values = [value]
    return {
        "shift": shift, "values": values, "notes": notes, "urun": urun,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/test_qc_converters.py -v`
Expected: PASS (6 güncellenmiş + 5 yeni test).

- [ ] **Step 7: Run full test suite to check for regressions**

Run: `pytest tests/ -q`
Expected: `tests/test_app_render_smoke.py` ve diğerleri hâlâ PASS - `build_bridge_subgroup_entry`'yi henüz sadece bu dosya çağırıyor test amaçlı, `app.py`'deki gerçek çağrı noktaları Task 2'de güncellenecek (bu ara adımda `app.py` henüz eski `shift_label=` ile çağırdığı için köprü UI'ı ÇALIŞMAZ hale gelir - bu BEKLENEN bir ara durumdur, `app.py`'yi import eden bir test yok, bkz. `tests/test_app_render_smoke.py`'nin kendi docstring notu).

- [ ] **Step 8: Commit**

```bash
git add src/qc_converters.py tests/test_qc_converters.py
git commit -m "feat: build_bridge_subgroup_entry - shift/notes ayri parametre, urun+otomatik timestamp eklendi"
```

---

### Task 2: `render_bridge_widget()` — gerçek Vardiya seçici + `urun`/`notes` damgalama

**Files:**
- Modify: `src/app.py` (`render_bridge_widget`, ara `3109-3227` civarı — fonksiyonu isme göre bul, dosya kaymış olabilir)

**Interfaces:**
- Consumes: `build_bridge_subgroup_entry(value, shift, notes="", urun="")` (Task 1)
- Produces: `render_bridge_widget(values_by_target, source_label, widget_key_prefix, extra_note=None) -> None` (imza değişmez, davranış genişler — 5 çağıran nokta hiç değişmeden yeni davranışı otomatik kazanır)

- [ ] **Step 1: `render_bridge_widget` içindeki X-bar/R dalına Vardiya seçici ekle, her iki dalda da `build_bridge_subgroup_entry` çağrısını güncelle**

Fonksiyonun X-bar/R dalını (`if not target_is_individual:` bloğu) bul, `required_n`/`bridge_value_count_matches` kontrolünden SONRA, `st.button(...)` çağrısından ÖNCE bir Vardiya seçici ekle; `st.button` içindeki `build_bridge_subgroup_entry` çağrısını güncelle:

```python
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
        bridge_shift = st.selectbox(
            "Vardiya", SHIFT_OPTIONS, key=f"{widget_key_prefix}_shift",
            help="Bu köprüyle eklenecek verinin hangi vardiyada ölçüldüğünü belirtin.",
        )
        st.caption(f"Aktif parametre: {target} (X-bar/R, n={required_n})")
        if st.button(f"📌 SPC Veri Setine Aktar ({source_label})", key=f"{widget_key_prefix}_bridge_button"):
            entry = build_bridge_subgroup_entry(
                value=target_values, shift=bridge_shift,
                notes=f"QC Dönüştürücü - {source_label}",
                urun=st.session_state.get("product_select", ""),
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
```

I-MR dalını (fonksiyonun geri kalanı) bul, `build_bridge_subgroup_entry` çağrısını güncelle:

```python
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
            value=imr_value, shift="-",
            notes=f"QC Dönüştürücü - {source_label}",
            urun=st.session_state.get("product_select", ""),
        )
        st.session_state.subgroups.append(entry)
        message = f"{source_label} değeri SPC veri setine eklendi ({target}, I-MR)."
        if extra_note:
            message += " " + extra_note
        st.success(message)
```

- [ ] **Step 2: Run full test suite**

Run: `pytest tests/ -q`
Expected: TÜM testler PASS (272+, `app.py` artık `build_bridge_subgroup_entry`'yi doğru imzayla çağırıyor).

- [ ] **Step 3: Manuel + canlı (Playwright) doğrulama**

Run: `streamlit run src/app.py` (yerelde), Playwright ile veya elle. **Dikkat:** Vardiya seçici SADECE X-bar/R hedeflerde görünür (I-MR hedeflerde `shift="-"` sabit kalır, seçici hiç render edilmez) — bu yüzden aşağıdaki 1-4 adımları X-bar/R hedefleyen bir köprüyle (Titrasyon Asitliği → "Titrasyon Asitliği" parametresi) test edilir; `urun` damgalamasını I-MR bir köprüyle de (Totox → "Peroksit Değeri") ayrıca doğrula (5. adım).

1. Sidebar'dan "Titrasyon Asitliği" parametresini seç, Chart sekmesinde "Ürün / Hammadde" olarak bir ürün seç (örn. "Domates salçası").
2. "Hızlı Hesaplayıcılar" sekmesine geç, Titre Edilebilir Asitlik köprüsünde `n` adet titre hacmi gir, "SPC Veri Setine Aktar" öncesi görünen yeni "Vardiya" seçicisinden "Öğle" seç, aktar.
3. Veri Girişi sekmesine dön, geçmiş tabloyu aç — yeni satırda `urun="Domates salçası"`, `notes="QC Dönüştürücü - Titre Edilebilir Asitlik"` görünmeli (Task 5'te tabloya bu sütunlar eklenecek — bu adımda henüz görünmeyebilir, sadece `st.session_state.subgroups`'un doğru içerikte olduğunu bir `st.write(st.session_state.subgroups)` geçici satırıyla veya tarayıcı konsolundan doğrula, kalıcı kod DEĞİŞTİRME).
4. Chart sekmesinde "Vardiya Karşılaştırması" tablosunu aç — yeni kaydın "Öğle" grubunda göründüğünü doğrula (önceden hiç görünmüyordu, sabit "Sabah"a da düşmediğini — gerçekten SEÇİLEN vardiyaya gittiğini kontrol et).
5. "Peroksit Değeri" parametresine geç, Chart sekmesinde farklı bir ürün seç (örn. "Zeytinyağı (naturel sızma)"), Totox Hesaplayıcı'dan aktar (bu hedef I-MR olduğu için Vardiya seçici GÖRÜNMEMELİ — bunu da doğrula) — geçmiş tabloda `urun="Zeytinyağı (naturel sızma)"` doğru yakalandığını kontrol et.

- [ ] **Step 4: Commit**

```bash
git add src/app.py
git commit -m "feat: render_bridge_widget - X-bar/R kopruleri icin gercek Vardiya secici, urun/notes damgalama"
```

---

### Task 3: `csv_io.parse_uploaded_dataframe` — `lot_no`/`notes`/`urun`/`timestamp` koruma

**Files:**
- Modify: `src/csv_io.py` (`parse_uploaded_dataframe`, `_parse_microbio_dataframe`, `subgroups_to_records`)
- Test: `tests/test_csv_io.py`

**Interfaces:**
- Consumes: yok
- Produces:
  - `parse_uploaded_dataframe(df, is_individual, subgroup_n, shift_options, unit="", is_microbio=False, default_lod=None, default_urun="") -> tuple[list[dict] | None, str | None]` — yeni `default_urun` parametresi (varsayılan `""`); dönen her sözlükte artık `lot_no`, `notes`, `urun`, `timestamp` anahtarları da var (df'de ilgili sütun VARSA okunur, YOKSA sırasıyla `""`, `""`, `default_urun`, `datetime.now().isoformat(timespec="seconds")`).
  - `subgroups_to_records(subgroups, is_individual, is_microbio=False) -> list[dict]` — dönen her satır sözlüğüne `Parti/Lot No`, `Not`, `Urun`, `Zaman` sütunları eklendi (mevcut sütunların YANINA, sırası bozulmadan).

- [ ] **Step 1: Write the failing tests**

`tests/test_csv_io.py` içine ekle (dosyanın başındaki importlara `import pandas as pd` zaten var, `from datetime import datetime as _dt` ekle):

```python
def test_parse_uploaded_dataframe_preserves_lot_no_and_notes_when_present():
    df = pd.DataFrame({
        "Olcum 1": [7.0, 7.1],
        "lot_no": ["LOT-1", "LOT-2"],
        "notes": ["ilk numune", ""],
    })
    subgroups, err = parse_uploaded_dataframe(df, is_individual=True, subgroup_n=1, shift_options=["Sabah", "Ogle", "Gece"])
    assert err is None
    assert subgroups[0]["lot_no"] == "LOT-1"
    assert subgroups[0]["notes"] == "ilk numune"
    assert subgroups[1]["lot_no"] == "LOT-2"
    assert subgroups[1]["notes"] == ""


def test_parse_uploaded_dataframe_defaults_lot_no_and_notes_when_absent():
    df = pd.DataFrame({"Olcum 1": [7.0]})
    subgroups, err = parse_uploaded_dataframe(df, is_individual=True, subgroup_n=1, shift_options=["Sabah", "Ogle", "Gece"])
    assert err is None
    assert subgroups[0]["lot_no"] == ""
    assert subgroups[0]["notes"] == ""


def test_parse_uploaded_dataframe_preserves_urun_when_present_else_uses_default():
    df_with = pd.DataFrame({"Olcum 1": [7.0], "urun": ["Bal"]})
    subgroups, _ = parse_uploaded_dataframe(df_with, is_individual=True, subgroup_n=1, shift_options=["Sabah", "Ogle", "Gece"], default_urun="Ozel/Manuel gir")
    assert subgroups[0]["urun"] == "Bal"

    df_without = pd.DataFrame({"Olcum 1": [7.0]})
    subgroups2, _ = parse_uploaded_dataframe(df_without, is_individual=True, subgroup_n=1, shift_options=["Sabah", "Ogle", "Gece"], default_urun="Ozel/Manuel gir")
    assert subgroups2[0]["urun"] == "Ozel/Manuel gir"


def test_parse_uploaded_dataframe_preserves_timestamp_when_present_else_stamps_now():
    df_with = pd.DataFrame({"Olcum 1": [7.0], "timestamp": ["2026-01-01T10:00:00"]})
    subgroups, _ = parse_uploaded_dataframe(df_with, is_individual=True, subgroup_n=1, shift_options=["Sabah", "Ogle", "Gece"])
    assert subgroups[0]["timestamp"] == "2026-01-01T10:00:00"

    df_without = pd.DataFrame({"Olcum 1": [7.0]})
    subgroups2, _ = parse_uploaded_dataframe(df_without, is_individual=True, subgroup_n=1, shift_options=["Sabah", "Ogle", "Gece"])
    _dt.fromisoformat(subgroups2[0]["timestamp"])  # ValueError firlatirsa FAIL


def test_parse_uploaded_dataframe_xbar_r_preserves_new_fields_too():
    df = pd.DataFrame({
        "Vardiya": ["Sabah", "Sabah"],
        "Olcum 1": [7.0, 7.1], "Olcum 2": [7.05, 7.15],
        "lot_no": ["L1", "L2"],
    })
    subgroups, err = parse_uploaded_dataframe(df, is_individual=False, subgroup_n=2, shift_options=["Sabah", "Ogle", "Gece"])
    assert err is None
    assert subgroups[0]["lot_no"] == "L1"
    assert subgroups[1]["lot_no"] == "L2"


def test_parse_uploaded_dataframe_microbio_preserves_new_fields_too():
    df = pd.DataFrame({"Raw (KOB/g)": [500.0], "lot_no": ["LOT-M1"]})
    subgroups, err = parse_uploaded_dataframe(
        df, is_individual=True, subgroup_n=1, shift_options=["Sabah", "Ogle", "Gece"],
        is_microbio=True, default_lod=10.0,
    )
    assert err is None
    assert subgroups[0]["lot_no"] == "LOT-M1"


def test_subgroups_to_records_includes_traceability_columns():
    subgroups = [{
        "shift": "-", "values": [7.0], "lot_no": "L1", "notes": "n1",
        "urun": "Bal", "timestamp": "2026-01-01T10:00:00",
    }]
    rows = subgroups_to_records(subgroups, is_individual=True)
    assert rows[0]["Parti/Lot No"] == "L1"
    assert rows[0]["Not"] == "n1"
    assert rows[0]["Urun"] == "Bal"
    assert rows[0]["Zaman"] == "2026-01-01T10:00:00"


def test_subgroups_to_records_defaults_missing_traceability_fields():
    subgroups = [{"shift": "-", "values": [7.0]}]  # eski/demo kaydi - yeni alanlar yok
    rows = subgroups_to_records(subgroups, is_individual=True)
    assert rows[0]["Parti/Lot No"] == ""
    assert rows[0]["Not"] == ""
    assert rows[0]["Urun"] == ""
    assert rows[0]["Zaman"] == ""
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_csv_io.py -v`
Expected: FAIL - `KeyError: 'lot_no'` / `TypeError: parse_uploaded_dataframe() got an unexpected keyword argument 'default_urun'` vb.

- [ ] **Step 3: Write minimal implementation**

`src/csv_io.py`'nin en üstüne `from datetime import datetime` ekle. `_parse_microbio_dataframe` fonksiyonunu güncelle — imzasına `default_urun: str = ""` ekle, döndürdüğü her sözlüğe yeni alanları ekle:

```python
def _parse_microbio_dataframe(
    df: pd.DataFrame, unit: str, default_lod: float | None, default_urun: str = "",
) -> tuple[list[dict] | None, str | None]:
    """... (mevcut docstring aynen kalir, sonuna ekle:) v2: lot_no/notes/
    urun/timestamp sutunlari df'de VARSA korunur, YOKSA sirasiyla ""/""/
    default_urun/simdiki-zamana duser (bkz. docs/superpowers/specs/
    2026-08-21-paylasilan-subgroups-izlenebilirlik-design.md)."""
    raw_col = "Raw (KOB/g)" if "Raw (KOB/g)" in df.columns else "Olcum 1"
    if raw_col not in df.columns:
        return None, (
            "Beklenen sutun bulunamadi: mikrobiyoloji parametreleri icin 'Raw (KOB/g)' "
            "(veya 'Olcum 1') sutunu gereklidir. CSV'deki sutunlar: "
            f"{', '.join(df.columns) or '(sutun yok)'}."
        )

    below_col = next((c for c in df.columns if c.lower() in ("lod altimi", "is_below_lod")), None)
    lod_col = next((c for c in df.columns if c.lower() == "lod"), None)
    lot_no_col = "lot_no" if "lot_no" in df.columns else None
    notes_col = "notes" if "notes" in df.columns else None
    urun_col = "urun" if "urun" in df.columns else None
    timestamp_col = "timestamp" if "timestamp" in df.columns else None

    subgroups = []
    for i in range(len(df)):
        raw_cell = df[raw_col].iloc[i]
        is_below = False
        if below_col is not None:
            below_cell = df[below_col].iloc[i]
            is_below = str(below_cell).strip().lower() in ("true", "1", "evet", "yes")
        lod = default_lod
        if lod_col is not None and pd.notna(df[lod_col].iloc[i]):
            lod = float(df[lod_col].iloc[i])

        raw_val = None if (is_below or pd.isna(raw_cell)) else float(raw_cell)
        try:
            entry = build_subgroup_entry(raw=raw_val, is_below_lod=is_below, lod=lod)
        except ValueError as exc:
            return None, f"{i + 1}. satir: {exc}"
        subgroups.append({
            "shift": "-", "values": [entry["log_value"]],
            "raw": entry["raw"], "is_below_lod": entry["is_below_lod"], "lod": entry["lod"],
            "lot_no": str(df[lot_no_col].iloc[i]) if lot_no_col and pd.notna(df[lot_no_col].iloc[i]) else "",
            "notes": str(df[notes_col].iloc[i]) if notes_col and pd.notna(df[notes_col].iloc[i]) else "",
            "urun": str(df[urun_col].iloc[i]) if urun_col and pd.notna(df[urun_col].iloc[i]) else default_urun,
            "timestamp": (
                str(df[timestamp_col].iloc[i]) if timestamp_col and pd.notna(df[timestamp_col].iloc[i])
                else datetime.now().isoformat(timespec="seconds")
            ),
        })
    return subgroups, None
```

`parse_uploaded_dataframe` fonksiyonunun imzasına `default_urun: str = ""` ekle, `_parse_microbio_dataframe` çağrısına geçir, ve fonksiyonun geri kalanında (is_individual ve X-bar/R dalları) her `subgroups.append(...)`/liste-comprehension satırını yeni alanları içerecek şekilde güncelle:

```python
def parse_uploaded_dataframe(
    df: pd.DataFrame, is_individual: bool, subgroup_n: int, shift_options: list[str], unit: str = "",
    is_microbio: bool = False, default_lod: float | None = None, default_urun: str = "",
) -> tuple[list[dict] | None, str | None]:
    """... (mevcut docstring aynen kalir, sonuna ekle:) v2: lot_no/notes/
    urun/timestamp sutunlari df'de VARSA korunur (round-trip icin gerekli -
    "Degisiklikleri kaydet" bu fonksiyonu kullanir), YOKSA sirasiyla ""/""/
    default_urun/simdiki-zamana duser."""
    if is_individual and is_microbio:
        return _parse_microbio_dataframe(df, unit, default_lod, default_urun)

    measurement_cols = [c for c in df.columns if c.startswith("Olcum")]
    expected_count = 1 if is_individual else subgroup_n

    if len(measurement_cols) != expected_count:
        chart_name = "I-MR" if is_individual else f"X-bar/R (n={subgroup_n})"
        return None, (
            f"Beklenen sutun bulunamadi: {chart_name} icin {expected_count} 'Olcum' "
            f"sutunu bekleniyor, {len(measurement_cols)} bulundu. CSV'deki sutunlar: "
            f"{', '.join(df.columns) or '(sutun yok)'}. 'Bos sablon indir' butonuyla "
            "dogru formati indirebilirsiniz."
        )

    lot_no_col = "lot_no" if "lot_no" in df.columns else None
    notes_col = "notes" if "notes" in df.columns else None
    urun_col = "urun" if "urun" in df.columns else None
    timestamp_col = "timestamp" if "timestamp" in df.columns else None

    def _trace_fields(i: int) -> dict:
        return {
            "lot_no": str(df[lot_no_col].iloc[i]) if lot_no_col and pd.notna(df[lot_no_col].iloc[i]) else "",
            "notes": str(df[notes_col].iloc[i]) if notes_col and pd.notna(df[notes_col].iloc[i]) else "",
            "urun": str(df[urun_col].iloc[i]) if urun_col and pd.notna(df[urun_col].iloc[i]) else default_urun,
            "timestamp": (
                str(df[timestamp_col].iloc[i]) if timestamp_col and pd.notna(df[timestamp_col].iloc[i])
                else datetime.now().isoformat(timespec="seconds")
            ),
        }

    if is_individual:
        raw_series = df[measurement_cols[0]]
        numeric_vals = pd.to_numeric(raw_series, errors="coerce")
        if numeric_vals.isna().any():
            return None, friendly_numeric_error(raw_series, numeric_vals, unit)
        subgroups = [
            {"shift": "-", "values": [float(v)], **_trace_fields(i)}
            for i, v in enumerate(numeric_vals)
        ]
        return subgroups, None

    numeric_block = df[measurement_cols].apply(pd.to_numeric, errors="coerce")
    if numeric_block.isna().any().any():
        bad_col = next(c for c in measurement_cols if numeric_block[c].isna().any())
        return None, friendly_numeric_error(df[bad_col], numeric_block[bad_col], unit)

    shift_col = df["Vardiya"] if "Vardiya" in df.columns else None
    subgroups = []
    for i in range(len(df)):
        vals = [float(numeric_block.iloc[i][c]) for c in measurement_cols]
        shift_val = str(shift_col.iloc[i]) if shift_col is not None else shift_options[0]
        if shift_val not in shift_options:
            shift_val = shift_options[0]
        subgroups.append({"shift": shift_val, "values": vals, **_trace_fields(i)})
    return subgroups, None
```

`subgroups_to_records` fonksiyonunu güncelle — her üç dalın (microbio, individual, X-bar/R) döndürdüğü sözlüğe yeni sütunları ekle:

```python
def subgroups_to_records(subgroups: list[dict], is_individual: bool, is_microbio: bool = False) -> list[dict]:
    """... (mevcut docstring aynen kalir, sonuna ekle:) v2: her satira
    Parti/Lot No, Not, Urun, Zaman sutunlari eklendi - eski/demo kayitlarda
    bu alanlar yoksa .get(key, "") ile "" gosterilir (kirilma yok)."""
    rows = []
    for i, sg in enumerate(subgroups, start=1):
        vals = sg["values"]
        trace = {
            "Parti/Lot No": sg.get("lot_no", ""),
            "Not": sg.get("notes", ""),
            "Urun": sg.get("urun", ""),
            "Zaman": sg.get("timestamp", ""),
        }
        if is_individual and is_microbio:
            is_below = sg.get("is_below_lod", False)
            lod = sg.get("lod")
            used_value = (lod / 2) if (is_below and lod is not None) else sg.get("raw")
            rows.append({
                "Sira": i,
                "Raw (KOB/g)": sg.get("raw"),
                "LOD altimi": is_below,
                "LOD": lod,
                "Kullanilan (KOB/g)": used_value,
                "log10": vals[0],
                **trace,
            })
        elif is_individual:
            rows.append({
                "Sira": i,
                **{f"Olcum {j + 1}": v for j, v in enumerate(vals)},
                **trace,
            })
        else:
            rows.append({
                "Grup": i,
                "Vardiya": sg["shift"],
                **{f"Olcum {j + 1}": v for j, v in enumerate(vals)},
                "Ortalama": sum(vals) / len(vals),
                "Range": max(vals) - min(vals),
                **trace,
            })
    return rows
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_csv_io.py -v`
Expected: PASS (yeni 8 test + mevcut testler).

- [ ] **Step 5: Run full test suite**

Run: `pytest tests/ -q`
Expected: TÜM testler PASS.

- [ ] **Step 6: Commit**

```bash
git add src/csv_io.py tests/test_csv_io.py
git commit -m "feat: parse_uploaded_dataframe/subgroups_to_records - lot_no/notes/urun/timestamp korunur veya varsayilana duser"
```

---

### Task 4: Manuel veri girişi formu — `lot_no`/`notes` alanları + `urun`/`timestamp` damgalama

**Files:**
- Modify: `src/app.py` (`render_generic_data_entry_tab`, ~`1550-1690` civarı — isme göre bul)

**Interfaces:**
- Consumes: yok (mevcut form yapısına ekleme)
- Produces: yok (UI davranışı genişler)

- [ ] **Step 1: Form içine `lot_no`/`notes` widget'ları ekle**

`st.form("subgroup_form", clear_on_submit=True):` bloğu içinde, `submitted = st.form_submit_button(...)` satırından HEMEN ÖNCE ekle:

```python
            lot_no = st.text_input(
                "Parti/Lot No (opsiyonel)", key=f"lot_no_input_{st.session_state.active_parameter}",
            )
            notes = st.text_area(
                "Not (opsiyonel)", key=f"notes_input_{st.session_state.active_parameter}",
            )
            submitted = st.form_submit_button("Olcumu kaydet" if is_individual else "Alt grubu kaydet")
```

- [ ] **Step 2: Her iki `subgroups.append(...)` çağrısını yeni alanları içerecek şekilde güncelle**

Mikrobiyoloji dalını bul (`if submitted and is_individual and is_microbio:` altında), `st.session_state.subgroups.append({...})` çağrısını güncelle:

```python
                    st.session_state.subgroups.append({
                        "shift": shift, "values": [entry["log_value"]],
                        "raw": entry["raw"], "is_below_lod": entry["is_below_lod"], "lod": entry["lod"],
                        "lot_no": lot_no, "notes": notes,
                        "urun": st.session_state.get("product_select", ""),
                        "timestamp": datetime.now().isoformat(timespec="seconds"),
                    })
```

Genel dalı bul (`elif submitted:` altında), `st.session_state.subgroups.append({"shift": shift, "values": measurements})` satırını güncelle:

```python
                st.session_state.subgroups.append({
                    "shift": shift, "values": measurements,
                    "lot_no": lot_no, "notes": notes,
                    "urun": st.session_state.get("product_select", ""),
                    "timestamp": datetime.now().isoformat(timespec="seconds"),
                })
```

`datetime`, dosyanın en üstünde zaten import edilmiş (`from datetime import datetime`, `app.py:5`) — yeni bir import gerekmez.

- [ ] **Step 3: "Excel/pano yapıştır" akışını damgala (parse_pasted_text değişmiyor, çağıran taraf ekliyor)**

`paste_submitted` bloğunu bul (`new_rows, err = csv_io.parse_pasted_text(...)` sonrası), `st.session_state.subgroups.extend(new_rows)` satırından ÖNCE her satırı damgala:

```python
                    if err:
                        st.error(err)
                    else:
                        _paste_urun = st.session_state.get("product_select", "")
                        _paste_ts = datetime.now().isoformat(timespec="seconds")
                        for _row in new_rows:
                            _row.setdefault("lot_no", "")
                            _row.setdefault("notes", "")
                            _row.setdefault("urun", _paste_urun)
                            _row.setdefault("timestamp", _paste_ts)
                        st.session_state.subgroups.extend(new_rows)
                        st.session_state.baseline = None
                        label = "olcum" if is_individual else "alt grup"
                        st.success(f"{len(new_rows)} {label} eklendi (baseline sifirlandi).")
```

- [ ] **Step 4: CSV import ve "Değişiklikleri kaydet" çağrılarına `default_urun` geçir**

İki `csv_io.parse_uploaded_dataframe(...)` çağrısını (CSV import bloğu ve "Değişiklikleri kaydet" bloğu) bul, ikisine de `default_urun=st.session_state.get("product_select", "")` ekle:

```python
                        new_subgroups, err = csv_io.parse_uploaded_dataframe(
                            import_df, is_individual, subgroup_n, SHIFT_OPTIONS, unit,
                            is_microbio=is_microbio, default_lod=param_config.get("default_lod"),
                            default_urun=st.session_state.get("product_select", ""),
                        )
```

```python
                            new_subgroups, err = csv_io.parse_uploaded_dataframe(
                                clean_df, is_individual, subgroup_n, SHIFT_OPTIONS, unit,
                                is_microbio=is_microbio, default_lod=param_config.get("default_lod"),
                                default_urun=st.session_state.get("product_select", ""),
                            )
```

- [ ] **Step 5: Run full test suite**

Run: `pytest tests/ -q`
Expected: TÜM testler PASS (bu task sadece Streamlit UI kodu değiştiriyor, hiçbir pytest testi bu fonksiyonu doğrudan çağırmıyor).

- [ ] **Step 6: Manuel + canlı (Playwright) doğrulama**

Run: `streamlit run src/app.py`:
1. Herhangi bir parametrede (örn. pH) `lot_no="LOT-100"`, not="test" gir, kaydet — form temizlenmeli (`clear_on_submit=True` zaten çalışıyordu, regresyon olmadığını doğrula).
2. Excel/pano yapıştır ile 2 satır ekle — eklenen kayıtların `lot_no=""`, `urun=<o an seçili ürün>` aldığını doğrula (Task 5'te tabloya sütun eklenene kadar `st.session_state.subgroups`'u geçici bir `st.write` ile veya sonraki task'ta doğrula).

- [ ] **Step 7: Commit**

```bash
git add src/app.py
git commit -m "feat: manuel veri girisi formuna lot_no/notes eklendi, urun/timestamp otomatik damgalanir (paste/CSV dahil)"
```

---

### Task 5: Geçmiş tablo — yeni sütunlar (`lot_no`/`notes` düzenlenebilir, `urun`/`timestamp` salt-okunur)

**Files:**
- Modify: `src/app.py` (geçmiş tablo bloğu, `render_generic_data_entry_tab` içinde, ~`2018-2070` civarı — `st.data_editor` çağrısını ara)
- Test: `tests/test_app_render_smoke.py`

**Interfaces:**
- Consumes: `csv_io.subgroups_to_records` (Task 3, artık `Parti/Lot No`/`Not`/`Urun`/`Zaman` sütunlarını da döndürüyor)
- Produces: yok (UI davranışı genişler)

- [ ] **Step 1: `column_config`'e yeni sütunları ekle**

Microbio-olmayan dalı bul (`else:` bloğu, `numeric_cols = [c for c in df.columns if c not in ("Sira", "Grup", "Vardiya")]` satırının hemen altı), `numeric_cols` hesaplamasını yeni sütunları da hariç tutacak şekilde güncelle ve `column_config`'e yeni giriş ekle:

```python
                    numeric_cols = [
                        c for c in df.columns
                        if c not in ("Sira", "Grup", "Vardiya", "Parti/Lot No", "Not", "Urun", "Zaman")
                    ]
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
                    column_config["Parti/Lot No"] = st.column_config.TextColumn()
                    column_config["Not"] = st.column_config.TextColumn()
                    column_config["Urun"] = st.column_config.TextColumn(disabled=True)
                    column_config["Zaman"] = st.column_config.TextColumn(disabled=True)
```

Mikrobiyoloji dalını bul (`if is_microbio:` bloğu), `column_config` sözlüğüne aynı 4 girdiyi ekle (mevcut `index_col: ...` satırının hemen altına):

```python
                    column_config = {
                        "Raw (KOB/g)": st.column_config.NumberColumn(format="%.0f"),
                        "LOD altimi": st.column_config.CheckboxColumn(),
                        "LOD": st.column_config.NumberColumn(format="%.2f"),
                        "Kullanilan (KOB/g)": st.column_config.NumberColumn(format="%.2f", disabled=True),
                        "log10": st.column_config.NumberColumn(format="%.3f", disabled=True),
                        index_col: st.column_config.NumberColumn(disabled=True),
                        "Parti/Lot No": st.column_config.TextColumn(),
                        "Not": st.column_config.TextColumn(),
                        "Urun": st.column_config.TextColumn(disabled=True),
                        "Zaman": st.column_config.TextColumn(disabled=True),
                    }
```

- [ ] **Step 2: Write the regression test**

`tests/test_app_render_smoke.py`'nin sonuna ekle:

```python
def test_history_table_column_config_includes_traceability_columns():
    # Task 5: gecmis tablosunda lot_no/notes duzenlenebilir, urun/timestamp
    # salt-okunur olmali - regresyon: biri yanlislikla bu sutunlari
    # cikarirsa veya disabled durumunu ters cevirirse bu test yakalar.
    with open(APP_PATH, encoding="utf-8") as f:
        source = f.read()
    start = source.index("def render_generic_data_entry_tab()")
    end = source.index("def render_color_lab_chart_tab()")
    body = source[start:end]
    assert 'column_config["Parti/Lot No"] = st.column_config.TextColumn()' in body
    assert 'column_config["Not"] = st.column_config.TextColumn()' in body
    assert 'column_config["Urun"] = st.column_config.TextColumn(disabled=True)' in body
    assert 'column_config["Zaman"] = st.column_config.TextColumn(disabled=True)' in body
    assert '"Urun": st.column_config.TextColumn(disabled=True),' in body  # microbio dali
```

- [ ] **Step 3: Run test to verify it passes**

Run: `pytest tests/test_app_render_smoke.py -v`
Expected: PASS.

- [ ] **Step 4: Run full test suite**

Run: `pytest tests/ -q`
Expected: TÜM testler PASS.

- [ ] **Step 5: Manuel + canlı (Playwright) doğrulama**

Run: `streamlit run src/app.py`:
1. Task 4'te eklenen `lot_no="LOT-100"` kaydını geçmiş tabloda gör — `Parti/Lot No` sütununda görünmeli.
2. `Not` sütununda bir hücreyi düzenle, "Değişiklikleri kaydet"e bas — sayfa yenilendiğinde değişikliğin KALICI olduğunu doğrula (round-trip fix'inin gerçekten çalıştığının kanıtı — Task 3'ün asıl amacı).
3. `Urun`/`Zaman` sütunlarının tabloda görünüp DÜZENLENEMEDİĞİNİ (gri/disabled) doğrula.
4. Bir satırı sil, "Değişiklikleri kaydet"e bas — SİLİNMEYEN diğer satırların `lot_no`/`notes`/`urun`/`timestamp` değerlerinin KORUNDUĞUNU doğrula (round-trip'in TÜM satırlar için çalıştığının kanıtı, sadece düzenlenen satır için değil).

- [ ] **Step 6: Commit**

```bash
git add src/app.py tests/test_app_render_smoke.py
git commit -m "feat: gecmis tablosuna Parti/Lot No, Not, Urun, Zaman sutunlari eklendi"
```

---

### Task 6: `render_shift_comparison` regresyon testi + METHODOLOGY.md notu + versiyon rozeti

**Files:**
- Modify: `tests/test_app_render_smoke.py`
- Modify: `METHODOLOGY.md`
- Modify: `src/app.py` (versiyon rozeti)

**Interfaces:**
- Consumes: yok
- Produces: yok (sadece test + belge)

- [ ] **Step 1: Write the regression test**

`tests/test_app_render_smoke.py`'nin sonuna ekle:

```python
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
```

- [ ] **Step 2: Run tests to verify they pass**

Run: `pytest tests/test_app_render_smoke.py -v`
Expected: PASS.

- [ ] **Step 3: `METHODOLOGY.md`'ye not ekle**

`METHODOLOGY.md`'de `**v1.8 veya sonrası — Tüm parametrelere lot_no/timestamp/notes**` başlığını bul, TAMAMEN şununla değiştir (artık "sonrası" değil, tamamlandı):

```markdown
**v1.8 — Tüm parametrelere lot_no/timestamp/notes/Ürün (TAMAMLANDI)**

Daha önce buraya "bilinçli olarak ertelenmiş" diye not düşülmüştü - artık
tamamlandı. `L*/a*/b*` HARİÇ tüm 23 parametrenin paylaştığı
`st.session_state.subgroups` şeması `lot_no`, `notes`, `urun`,
`timestamp` alanlarıyla genişledi - manuel giriş, CSV import, Excel/pano
yapıştırma, geçmiş-tablo düzenleme VE 5 QC Dönüştürücü köprüsü (Gravimetrik
Nem/KM, Titrasyon Asitliği, Tuz/Mohr, Termal Letalite F₀, Totox) dahil
TÜM giriş yollarında. Yan bulgu ve düzeltme: köprü noktaları eskiden
kaynak etiketini (`"QC Dönüştürücü - Totox"` gibi) `shift` alanına
YAZARAK hackliyordu - bu, bu kayıtların `render_shift_comparison`'ın
vardiya gruplamasından SESSİZCE dışlanmasına yol açıyordu (fark
edilmemiş bir kenar durum, bug raporu yoktu). Artık köprüler gerçek bir
Vardiya seçici sunuyor, kaynak etiketi `notes`'a taşındı - köprüyle
eklenen veri artık vardiya karşılaştırmasında görünür VE doğru
etiketli. Detay: `docs/superpowers/specs/2026-08-21-paylasilan-
subgroups-izlenebilirlik-design.md`.

Kapsam dışı kalanlar (bilinçli): Renk Paneli (zaten kendi ayrı
modelinde bu alanlara sahip), CSV import'a yeni bir UI/davranış
eklenmesi (sadece mevcut "Değişiklikleri kaydet" özelliğinin bu
alanları KORUMASI sağlandı, yeni bir CSV formatı/sütun beklentisi
YOK), demo veri üreticisinin bu alanları anlamlı doldurması.
```

- [ ] **Step 4: Versiyon rozetini güncelle**

`src/app.py`'nin en altındaki `st.caption(f"SPC FoodLab v1.7.2 · ...")` satırını `v1.8` yap.

- [ ] **Step 5: Run full test suite one final time**

Run: `pytest tests/ -q`
Expected: TÜM testler PASS.

- [ ] **Step 6: Commit**

```bash
git add tests/test_app_render_smoke.py METHODOLOGY.md src/app.py
git commit -m "test: render_bridge_widget regresyon testleri + METHODOLOGY.md v1.8 TAMAMLANDI notu + versiyon rozeti"
```
