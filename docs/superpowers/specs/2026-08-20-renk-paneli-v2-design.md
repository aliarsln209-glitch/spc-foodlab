# Renk (L*a*b*) Paneli v2 — İzlenebilirlik + Okunabilirlik İyileştirmeleri (Design)

**Durum:** Onaylandı, implementasyon planına geçilecek.

## Bağlam

v1.7.1 Renk Panelini (bkz. `docs/superpowers/plans/2026-08-20-v1.7.1-renk-lab-paneli.md`)
canlı denetimde inceleyen kullanıcı geri bildirimi: panel diğer I-MR
parametrelerine kıyasla eksik kalıyor — parti/not takibi yok, form
gönderiminde yanlışlıkla aynı ölçüm iki kez eklenebiliyor (canlı vaka:
L=65,a=10,b=20 iki kez kaydedildi), grafik LSL/USL çizgisi göstermiyor,
düşük örnek sayısında Cpk rozeti yanıltıcı "Yeterli" diyebiliyor.

**Araştırma bulguları (bu tasarımdan önce doğrulandı):**
- `lot_no`/`timestamp`/`notes` hiçbir parametrede (Renk Paneli dahil,
  sadece orada değil) yok — şemada hiç var olmamış bir kapsam, düşürülmüş
  değil. Genele yayma (tüm parametreler) `METHODOLOGY.md`'ye v1.8+
  backlog notu olarak ayrıca düşüldü, bu tasarımın kapsamı DEĞİL.
- Duplicate kayıt kök nedeni: `st.form(...)` çağrısında
  `clear_on_submit=True` yok — submit sonrası alanlar önceki girilen
  değerlerde kalıyor, ikinci tıklamada sessizce aynı satır tekrar
  ekleniyor.
- Diğer I-MR parametrelerinde de `lot_no`/`notes`/canlı önizleme YOK
  (tek izlenebilirlik alanı `Vardiya`, o da sadece X-bar/R'de) — Renk
  Paneli bu konuda bir standarttan geride kalmamış. Gerçek geri kalma:
  demo veri, CSV import, geçmiş tablo, baseline dondurma, Nelson
  kuralları, OOS/OOT işaretleme, PNG export — bunlar METHODOLOGY.md'de
  bilinçli olarak v1 dışı bırakılmış, bu tasarımın kapsamı DEĞİL (export
  hariç, aşağıya bkz.).

## Kapsam

**Dahil:**
1. `color_lab.py` veri modeli: `lot_no`, `notes`, otomatik `timestamp` alanları.
2. Veri Girişi sekmesi: form kaldırılıp canlı swatch önizlemesi, lot_no/notes girişi, submit-sonrası otomatik temizlenen alanlar, geçmiş tabloda yeni sütunlar + tek satır silme.
3. Chart & Cpk sekmesi: düşük-n uyarısı (n<20), LSL/USL çizgileri, opsiyonel hedef swatch, 3-eksen trend özet uyarısı.
4. Testler: `test_color_lab.py` genişletmesi, smoke test güncellemesi.

**Kapsam DIŞI (bu turda):** CSV/Excel toplu içe aktarma, PNG/CSV export, numune fotoğrafı, ürün bazlı LSL/USL tablosu, tüm-parametrelere-genelleme (v1.8+ backlog, `METHODOLOGY.md`).

## 1) `color_lab.py` — veri modeli

```python
def append_color_sample(
    samples: list[dict], l: float, a: float, b: float,
    lot_no: str = "", notes: str = "",
) -> list[dict]:
    """... timestamp burada otomatik eklenir (datetime.now()), kullanici girmez."""
    entry = {
        "L": l, "a": a, "b": b,
        "lot_no": lot_no, "notes": notes,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }
    return samples + [entry]


def remove_color_sample(samples: list[dict], index: int) -> list[dict]:
    """Belirtilen index'teki ornegi cikarir - orijinal listeyi DEGISTIRMEZ,
    yeni bir liste doner (append_color_sample ile ayni desen)."""
    return samples[:index] + samples[index + 1:]
```

Geriye dönük uyumluluk sorunu yok — veri modeli session-state-only, kalıcı depolama yok, uygulama yeniden başlayınca zaten sıfırlanıyor.

## 2) Veri Girişi sekmesi (`render_color_lab_data_entry_tab`)

- `st.form("color_lab_entry_form")` kaldırılır. L*/a*/b* `number_input`'ları `key="color_lab_l_input"` vb. ile normal widget olur (her değişiklik anında rerun tetikler).
- Widget değerlerinden `lab_to_hex(...)` ile canlı swatch önizlemesi hesaplanıp inputların hemen altında gösterilir (aynı "yaklaşık önizleme, D65 varsayımlı..." notuyla).
- `lot_no = st.text_input("Parti/Lot No (opsiyonel)", key="color_lab_lot_input")`, `notes = st.text_area("Not (opsiyonel)", key="color_lab_notes_input")`.
- "Ölçümü Ekle" butonuna basınca: `append_color_sample(...)` çağrılır; ardından `color_lab_l_input`/`color_lab_a_input`/`color_lab_b_input`/`color_lab_lot_input`/`color_lab_notes_input` key'leri `st.session_state`'ten silinir (`del st.session_state[key]`) ve `st.rerun()` yapılır — widget'lar varsayılan değerlere döner, yanlışlıkla ikinci tıklamada aynı satırın tekrar eklenmesi riski büyük ölçüde azalır.
- Geçmiş tablo (`st.dataframe`) artık `lot_no`, `notes`, `timestamp` sütunlarını da gösterir.
- Her satırın yanında 🗑️ silme butonu (`key=f"color_lab_del_{i}"`) → `remove_color_sample(samples, i)` çağırıp `st.rerun()`.

## 3) Chart & Cpk sekmesi (`render_color_lab_chart_tab`)

- **Düşük-n uyarısı:** mevcut `MIN_RECOMMENDED_BASELINE = 20` sabiti (app.py'de zaten tanımlı, Montgomery kaynaklı) import edilip kullanılır. `n < MIN_RECOMMENDED_BASELINE` iken her eksen kartında Cpk rozeti yerine `st.warning(f"Cpk guvenilir yorum icin en az {MIN_RECOMMENDED_BASELINE} olcum onerilir (su an n={n}).")` gösterilir — sayı yine hesaplanıp `st.caption` ile gösterilir, sadece rozet/"Yeterli" ifadesi bastırılır.
- **LSL/USL çizgileri:** her eksenin I-MR grafiğine mevcut `annotate_hline` yardımcı fonksiyonu ile LSL/USL yatay çizgileri eklenir (diğer parametrelerdeki desenle aynı).
- **Hedef swatch:** üç adet opsiyonel `number_input` (hedef L*/a*/b*, varsayılan boş/None — kullanıcı doldurmazsa gösterilmez). Doldurulursa `lab_to_hex(hedef L, hedef a, hedef b)` ile ikinci bir swatch, mevcut "son ölçüm" swatch'inin yanına çizilir, "Hedef (yaklaşık önizleme)" etiketiyle. ΔE hesaplanmaz.
- **Trend özet uyarısı:** üç eksenin OOS/Cpk durumuna bakılır; herhangi biri kontrol dışıysa `st.warning(f"⚠️ {eksen} ekseni kontrol dışı, diğerleri normal")` (birden fazla eksen sorunluysa hepsi listelenir), hiçbiri sorunlu değilse `st.success("✅ Üç eksen de kontrol altında")` — 3 grafiğin üstünde, swatch'lerin altında gösterilir.

## 4) Test planı

- `tests/test_color_lab.py`: `append_color_sample` yeni imza (lot_no/notes/otomatik timestamp — timestamp formatının ISO olduğu, boş lot_no/notes varsayılanının çalıştığı) + `remove_color_sample` (mutasyonsuz, index sınırları) için testler.
- Mevcut `test_app_render_smoke.py` deseniyle uyumlu bir kaynak-yapısı kontrolü (import + PARAMETER_CATEGORIES/FOOD_QUALITY_PARAMETER_CONFIG bütünlüğü) — tam UI çalıştırma değil, mevcut desenle aynı.
- Mevcut tüm testler (Renk Paneli dışı parametreler) değişmeden geçmeli — hiçbir ortak kod (`spc_core.py`, generic tab fonksiyonları) değişmiyor.

## Bilinçli olarak ertelenenler (bu spec'in dışı, unutulmuş değil)

- CSV/Excel toplu içe aktarma — ayrı, daha büyük bir iş (paylaşılan import fonksiyonuna bağımlı).
- PNG/CSV export — kapsamı sınırlı tutmak için bu turda yok.
- Numune fotoğrafı — dosya depolama gerektirir, session-state-only mimariyle uyumsuz, v2.0 kalıcılık çalışmasını bekliyor.
- Ürün bazlı LSL/USL tablosu — kaynaksız veri uydurmamak için "Özel/Manuel gir" yeterli sayıldı.
- lot_no/timestamp/notes'un TÜM parametrelere genellenmesi — `METHODOLOGY.md`'de v1.8+ backlog notu olarak ayrı belgelendi.
