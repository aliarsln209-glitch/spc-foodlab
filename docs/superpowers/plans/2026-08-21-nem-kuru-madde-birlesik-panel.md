# Nem/Kuru Madde Birleşik Panel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `active_parameter` `Nem/Rutubet` veya `Kuru Madde` iken Veri Girişi sekmesine, gravimetrik (AOAC 925.10) dara/yaş/kuru-kalıntı girişinden `n` numune için hem %Nem hem %Kuru Madde hesaplayan, `lot_no`/`notes` alan içeren ve doğrudan aktif parametreye (X-bar/R veya I-MR) yazan birleşik bir giriş paneli eklemek; `Hızlı Hesaplayıcılar`'daki eski tekil Gravimetrik Nem/KM hesaplayıcısını kaldırmak.

**Architecture:** Yeni `render_moisture_dry_matter_data_entry_tab()` fonksiyonu `tab_data` içinde `active_parameter in ("Nem/Rutubet", "Kuru Madde")` olduğunda çağrılır (Renk Paneli'nin `active_parameter == "L*"` yönlendirme deseniyle birebir aynı) — gravimetrik n-üçlü formu üstte gösterir, altında mevcut `render_generic_data_entry_tab()`'ı DEĞİŞTİRMEDEN çağırır (doğrudan-değer girişi/CSV/pano yapıştırma/geçmiş tablo aynen kullanılabilir kalır). Hedef HER ZAMAN aktif parametre olduğu için (kullanıcı ayrıca seçmez), `render_bridge_widget`'ın seçim/gating UI'ı bu panelde KULLANILMAZ — `build_bridge_subgroup_entry()` doğrudan çağrılır (Kuru Madde için n kez, her biri ayrı I-MR noktası; Nem/Rutubet için 1 kez, n değerlik bir X-bar/R alt grubu olarak). `lot_no`, Alt-proje 1'in bridge fonksiyonunda YOK sayıldığı için (`build_bridge_subgroup_entry` parametresi değil) dönen dict'e append'den ÖNCE elle eklenir. `tab_chart` HİÇ DEĞİŞMEZ — `render_generic_chart_tab()` zaten `active_parameter`'a göre doğru chart tipini render ediyor ve Kuru Madde için mevcut "Çapraz kontrol: Kuru Madde + Nem" expander'ı zaten var.

**Tech Stack:** Python, Streamlit, pytest — mevcut stack, yeni bağımlılık yok.

**Spec:** `docs/superpowers/specs/2026-08-21-nem-kuru-madde-birlesik-panel-design.md`

## Global Constraints

- **`subgroups` mimarisine DOKUNULMAZ:** tek global liste, `active_parameter` değişince sıfırlanır — bu davranış AYNEN kalır (bilerek kabul edilen state-drift riski, bkz. spec).
- **`render_bridge_widget` DEĞİŞMEZ:** imzası ve gövdesi bu plan kapsamında hiç değiştirilmez (diğer 4 hesaplayıcı — Titrasyon, Tuz, F0, Totox — hâlâ kullanıyor).
- **`gravimetric_moisture()` DEĞİŞMEZ:** `src/qc_converters.py`'deki saf fonksiyon aynen çağrılır, n kez bir döngüde.
- **Hedef her zaman aktif parametre:** kullanıcıya "hangi parametreye aktarılsın" sorusu SORULMAZ — panel zaten sadece `active_parameter` `Nem/Rutubet`/`Kuru Madde` iken görünür.
- **`n` girdi kutusu sayısı:** `Kuru Madde` için `n=1` (I-MR — tek numune), `Nem/Rutubet` için `n=st.session_state.subgroup_size` (X-bar/R — tam alt grup).
- **Hatalı üçlü varsa Kaydet devre dışı:** `gravimetric_moisture()` bir `ValueError` fırlatırsa (örn. kuru kalıntı > yaş numune) o numunenin altında hata gösterilir, buton `disabled=True` olur — sessiz kısmi kayıt YOK.
- **Mevcut tüm testler (290) değişmeden geçmeli.**
- **Canlı (manuel) doğrulama zorunlu adım** (Task 2'de detaylandırıldığı gibi) — n=1 ve n=3 ile test edilecek.

---

### Task 1: `render_moisture_dry_matter_data_entry_tab()` + routing + eski hesaplayıcının kaldırılması

**Files:**
- Modify: `src/app.py` (`tab_data` routing bloğu, `~2139-2144`; yeni fonksiyon `render_generic_data_entry_tab()`'dan hemen ÖNCE eklenir; eski Gravimetrik Nem/KM bloğu `tab_calc` içinde, `~3282-3309`, SİLİNİR)
- Test: `tests/test_app_render_smoke.py`

**Interfaces:**
- Consumes: `qc_converters.gravimetric_moisture(dish_tare_g, wet_with_dish_g, dry_with_dish_g) -> dict` (mevcut, değişmez), `qc_converters.build_bridge_subgroup_entry(value, shift, notes="", urun="") -> dict` (Alt-proje 1, değişmez), `render_generic_data_entry_tab() -> None` (mevcut, değişmez), `SHIFT_OPTIONS` (mevcut sabit).
- Produces: `render_moisture_dry_matter_data_entry_tab() -> None` — başka hiçbir task bu fonksiyonu tüketmez (sadece routing bloğundan çağrılır).

- [ ] **Step 1: Mevcut kaynak metni oku ve tam eşleştiğini doğrula**

`src/app.py` içinde şu iki bloğun HÂLÂ verilen satırlarda olduğunu doğrula (dosya bu plan yazıldıktan sonra değişmiş olabilir — farklıysa isim/metinle ara):

```python
with tab_data:
    if st.session_state.active_parameter == "L*":
        render_color_lab_data_entry_tab()
    else:
        render_generic_data_entry_tab()
```

ve `tab_calc` içinde (Gravimetrik Nem/Kuru Madde bloğu):

```python
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
```

- [ ] **Step 2: Write the regression test (henüz FAIL edecek)**

`tests/test_app_render_smoke.py`'nin sonuna ekle:

```python
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
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/test_app_render_smoke.py -v -k "moisture_dry_matter or old_gravimetric"`
Expected: FAIL — `test_moisture_dry_matter_panel_exists_and_is_routed` fails çünkü fonksiyon yok (`source.index` `ValueError: substring not found`); `test_old_gravimetric_calculator_removed_from_tab_calc` fails çünkü `qc_moisture_tare` hâlâ mevcut.

- [ ] **Step 4: Eski Gravimetrik Nem/KM bloğunu `tab_calc`'tan sil**

Step 1'de gösterilen tam bloğu (`st.markdown("### ⚖️ Gravimetrik Nem / Kuru Madde")`'dan başlayıp sondaki `st.divider()`'a kadar, `render_bridge_widget(...)` çağrısı dahil) `src/app.py`'den TAMAMEN çıkar — hemen altındaki `st.markdown("### 🧪 Titre Edilebilir Asitlik")` bloğu (ve devamı) OLDUĞU GİBİ kalır.

- [ ] **Step 5: `render_moisture_dry_matter_data_entry_tab()` fonksiyonunu ekle**

`render_generic_data_entry_tab()` fonksiyon tanımının HEMEN ÜSTÜNE ekle (`def render_generic_data_entry_tab() -> None:` satırından önce):

```python
def render_moisture_dry_matter_data_entry_tab() -> None:
    """Nem/Kuru Madde Birlesik Paneli - SEKME 1. bkz. docs/superpowers/
    specs/2026-08-21-nem-kuru-madde-birlesik-panel-design.md.

    Gravimetrik (AOAC 925.10) n-uclu (dara/yas/kuru) giris formu ustte,
    render_generic_data_entry_tab() (dogrudan deger girisi/CSV/pano
    yapıştırma/gecmis tablo, DEGISMEDEN) altta. Hedef HER ZAMAN aktif
    parametredir (Nem/Rutubet veya Kuru Madde) - kullanici ayrica
    secmez, bu yuzden render_bridge_widget'in secim/gating UI'i BURADA
    KULLANILMAZ; build_bridge_subgroup_entry DOGRUDAN cagrilir.

    Kuru Madde (I-MR): n numune -> n AYRI I-MR noktasi (dongude).
    Nem/Rutubet (X-bar/R): n numune -> TEK bir X-bar/R alt grubu (n
    degerlik values listesi).

    lot_no: build_bridge_subgroup_entry'nin parametresi DEGIL (Alt-proje
    1'de bilerek disaridan birakildi, bkz. o spec) - donen dict'e
    append'den ONCE elle eklenir.
    """
    st.markdown("#### ⚖️ Gravimetrik Nem/Kuru Madde Girişi (AOAC 925.10)")
    st.caption(
        "Dara + yaş numune + kuru kalıntı ağırlığından hem Nem hem Kuru "
        "Madde hesaplar ve doğrudan aktif parametreye ("
        f"**{st.session_state.active_parameter}**) yazar. Aşağıda ayrıca "
        "doğrudan değer girişi/CSV/pano yapıştırma seçenekleri de mevcuttur."
    )

    is_individual = st.session_state.active_parameter == "Kuru Madde"
    n = 1 if is_individual else st.session_state.subgroup_size
    # Widget key'lerine active_parameter EKLENIR (sadece i/n degil) - aksi
    # halde Nem/Rutubet icin subgroup_size=1 iken Kuru Madde ile (o da
    # daima n=1) AYNI key'ler uretilir, parametreler arasi gecişte eski
    # yazilmis degerler yanlislikla tasinir (canli testte bu senaryo
    # ayrica dogrulanacak, bkz. implementasyon plani Task 2).
    key_scope = f"{st.session_state.active_parameter}_{n}"

    triples = []
    has_error = False
    cols = st.columns(n)
    for i, col in enumerate(cols):
        with col:
            st.markdown(f"**Numune {i + 1}**")
            tare = st.number_input(
                "Kap darası (g)", min_value=0.0, value=25.000, step=0.001,
                format="%.3f", key=f"moist_tare_{i}_{key_scope}",
            )
            wet = st.number_input(
                "Kap + yaş (g)", min_value=0.0, value=30.000, step=0.001,
                format="%.3f", key=f"moist_wet_{i}_{key_scope}",
            )
            dry = st.number_input(
                "Kap + kuru (g)", min_value=0.0, value=29.400, step=0.001,
                format="%.3f", key=f"moist_dry_{i}_{key_scope}",
            )
            try:
                result = gravimetric_moisture(tare, wet, dry)
                triples.append(result)
                st.caption(
                    f"Nem: %{result['moisture_pct']:.2f} · "
                    f"Kuru Madde: %{result['dry_matter_pct']:.2f}"
                )
            except ValueError as exc:
                has_error = True
                st.error(str(exc))

    moist_shift = "-"
    if not is_individual:
        moist_shift = st.selectbox("Vardiya", SHIFT_OPTIONS, key=f"moist_shift_{key_scope}")
    lot_no = st.text_input("Parti/Lot No (opsiyonel)", key=f"moist_lot_no_{key_scope}")
    notes = st.text_area("Not (opsiyonel)", key=f"moist_notes_{key_scope}")

    if st.button(
        "\U0001F4CC SPC Veri Setine Aktar", key=f"moist_bridge_button_{key_scope}",
        disabled=has_error,
    ):
        urun = st.session_state.get("product_select", "")
        if is_individual:
            for result in triples:
                entry = build_bridge_subgroup_entry(
                    value=result["dry_matter_pct"], shift="-", notes=notes, urun=urun,
                )
                entry["lot_no"] = lot_no
                st.session_state.subgroups.append(entry)
            st.success(f"{len(triples)} Kuru Madde ölçümü SPC veri setine eklendi (I-MR).")
        else:
            entry = build_bridge_subgroup_entry(
                value=[t["moisture_pct"] for t in triples], shift=moist_shift,
                notes=notes, urun=urun,
            )
            entry["lot_no"] = lot_no
            st.session_state.subgroups.append(entry)
            st.success(f"1 Nem/Rutubet alt grubu SPC veri setine eklendi (X-bar/R, n={n}).")

    st.divider()
    render_generic_data_entry_tab()
```

- [ ] **Step 6: `tab_data` routing bloğunu güncelle**

```python
with tab_data:
    if st.session_state.active_parameter == "L*":
        render_color_lab_data_entry_tab()
    elif st.session_state.active_parameter in ("Nem/Rutubet", "Kuru Madde"):
        render_moisture_dry_matter_data_entry_tab()
    else:
        render_generic_data_entry_tab()
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `pytest tests/test_app_render_smoke.py -v -k "moisture_dry_matter or old_gravimetric"`
Expected: PASS (2 yeni test).

- [ ] **Step 8: Run full test suite to check for regressions**

Run: `pytest tests/ -q`
Expected: 292 passed (290 mevcut + 2 yeni), hiçbir regresyon.

- [ ] **Step 9: Commit**

```bash
git add src/app.py tests/test_app_render_smoke.py
git commit -m "feat: Nem/Kuru Madde Birlesik Paneli - n-uclu gravimetrik giris + dogrudan hedefe yazma, eski tekil hesaplayici kaldirildi"
```

---

### Task 2: Canlı doğrulama + METHODOLOGY.md + versiyon rozeti

**Files:**
- Modify: `METHODOLOGY.md`
- Modify: `src/app.py` (versiyon rozeti)

**Interfaces:**
- Consumes: yok
- Produces: yok (sadece belge + doğrulama)

- [ ] **Step 1: Run full test suite one more time (temiz baseline)**

Run: `pytest tests/ -q`
Expected: 292 passed.

- [ ] **Step 2: Canlı (manuel) doğrulama**

Run: `streamlit run src/app.py` (yerelde):

1. Sidebar'dan `Kuru Madde` parametresini seç (n etkisiz, I-MR). Veri Girişi sekmesinde YENİ gravimetrik panelin göründüğünü, `render_generic_data_entry_tab()`'ın (doğrudan değer girişi formu) ALTINDA hâlâ göründüğünü doğrula.
2. Tek bir numune için dara=25.000, yaş=30.000, kuru=29.400 gir (beklenen: Nem %12.00, Kuru Madde %88.00), `lot_no="LOT-M1"`, not="test" gir, "SPC Veri Setine Aktar"a bas — "1 Kuru Madde ölçümü... eklendi" mesajını gör.
3. Geçmiş tabloyu aç (aşağıdaki `render_generic_data_entry_tab()` içindeki expander) — yeni satırda `Kullanılan`/`log10` DEĞİL, doğrudan `Olçum 1=88.0`, `Parti/Lot No=LOT-M1` görünmeli (Kuru Madde mikrobiyoloji DEĞİL, düz I-MR).
4. Chart sekmesine geç — I-MR chart'ta yeni noktayı gör, "Çapraz kontrol: Kuru Madde + Nem" expander'ının hâlâ çalıştığını doğrula (mevcut davranış, değişmedi).
5. Sidebar'dan `Nem/Rutubet`'e geç (mevcut veri silinecek uyarısını onayla). Sidebar'dan alt grup büyüklüğünü `n=3` yap. Veri Girişi sekmesinde panelin 3 numune sütunu gösterdiğini doğrula.
6. 3 numune için farklı dara/yaş/kuru değerleri gir, `Vardiya="Öğle"` seç, "SPC Veri Setine Aktar"a bas — "1 Nem/Rutubet alt grubu... (X-bar/R, n=3)" mesajını gör.
7. Chart sekmesinde X-bar/R chart'ta yeni alt grubun göründüğünü, "Vardiya Karşılaştırması" tablosunda "Öğle" grubuna doğru düştüğünü doğrula.
8. Bir numunede kasıtlı hata yap (kuru > yaş) — o numunenin altında hata mesajı, "SPC Veri Setine Aktar" butonunun DEVRE DIŞI (tıklanamaz) olduğunu doğrula.
9. Geçmiş tabloda Kuru Madde adımında eklenen kaydın `Urun`/`Zaman` sütunlarının DOLU ve salt-okunur (gri) olduğunu doğrula.
10. **Parametre-değişimi güvenlik testi** (kullanıcı geri bildirimi — Faz 1'in kökeni olan senaryo bu panelde MİRAS ALINMADIĞINI kanıtlamak için): `Kuru Madde` aktifken n-üçlü formu KISMEN doldur (örn. dara/yaş/kuru gir ama "SPC Veri Setine Aktar"a BASMA). Sidebar'dan `Nem/Rutubet`'e geçmeyi dene — "mevcut veri silinecek, emin misiniz?" onay adımını gör, "Evet, değiştir"e bas. Panelin şimdi `Nem/Rutubet`'in n-üçlü formunu (BOŞ/varsayılan değerlerle, önceki Kuru Madde girdileri TAŞINMAMIŞ) gösterdiğini doğrula — `moist_tare_0_Kuru Madde_1` ile `moist_tare_0_Nem/Rutubet_<n>` farklı key'ler olduğu için bu beklenen davranıştır. Sonra bu yeni formu doldurup "SPC Veri Setine Aktar"a bas — kaydın `Nem/Rutubet`'e (X-bar/R) yazıldığını, YANLIŞLIKLA `Kuru Madde`'ye YAZILMADIĞINI doğrula.

- [ ] **Step 3: `METHODOLOGY.md`'ye not ekle**

`METHODOLOGY.md`'de Alt-proje 1'in eklediği `**v1.8 — Tüm parametrelere lot_no/timestamp/notes/Ürün (TAMAMLANDI)**` bölümünün HEMEN ALTINA, `**v1.9+ — Nem/Kuru Madde kanonikleştirme**` bölümünün ÜSTÜNE yeni bir bölüm ekle:

```markdown
**v1.8.1 — Nem/Kuru Madde Birleşik Panel (TAMAMLANDI)**

`active_parameter` `Nem/Rutubet` veya `Kuru Madde` iken Veri Girişi
sekmesi artık gravimetrik (AOAC 925.10) n-üçlü (dara/yaş/kuru-kalıntı)
giriş paneli gösteriyor — tek "SPC Veri Setine Aktar" ile hem %Nem hem
%Kuru Madde hesaplanıp DOĞRUDAN aktif parametreye (kullanıcı hedef
seçmeden) yazılıyor; `lot_no`/`notes` alanları ve otomatik `urun`/
`timestamp` damgalaması dahil. `Hızlı Hesaplayıcılar`'daki eski tekil
hesaplayıcı (dropdown'la tek hedef seçilen) bu panelle DEĞİŞTİRİLDİ.
Detay ve bilerek kabul edilen state-drift riski notu:
`docs/superpowers/specs/2026-08-21-nem-kuru-madde-birlesik-panel-
design.md`.
```

- [ ] **Step 4: Versiyon rozetini güncelle**

`src/app.py`'nin en altındaki `st.caption(f"SPC FoodLab v1.8 · ...")` satırını `v1.8.1` yap.

- [ ] **Step 5: Run full test suite one final time**

Run: `pytest tests/ -q`
Expected: 292 passed.

- [ ] **Step 6: Commit**

```bash
git add METHODOLOGY.md src/app.py
git commit -m "docs: Nem/Kuru Madde Birlesik Panel METHODOLOGY.md v1.8.1 TAMAMLANDI notu + versiyon rozeti"
```
