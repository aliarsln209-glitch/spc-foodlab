# Paylaşılan `subgroups` Şemasına İzlenebilirlik Alanları (Design)

**Durum:** Onaylandı, implementasyon planına geçilecek.

**Alt-proje sırası:** Bu, iki bağımlı alt-projenin BİRİNCİSİdir. İKİNCİSİ
("Nem/Kuru Madde Birleşik Panel") bu alt-projenin çıktısı (özellikle
`build_bridge_subgroup_entry` imza değişikliği ve `subgroups` şema
genişlemesi) üzerine kurulur — bu spec/plan tamamlanıp implementasyonu
bitmeden Alt-proje 2'nin planı yazılmaz.

## Bağlam

`METHODOLOGY.md`'ye daha önce şu backlog notu düşülmüştü: "hiçbir
parametrede (Renk Paneli dahil, sadece orada değil) parti/lot numarası,
ölçüm zaman damgası veya serbest metin not alanı YOK... bu bilinçli
olarak ertelenmiştir." Nem/Kuru Madde birleşik panel talebi ("Renk
Panelinden Öğrenilenler — BAŞTAN dahil et: lot_no, timestamp, notes,
Ürün/Hat alanları") bu ertelemeyi tekrar gündeme getirdi. Kod incelemesi
şunu gösterdi: Nem/Kuru Madde artık Renk Paneli gibi izole bir veri
modeline ihtiyaç duymuyor (kanonik parametre tek eksenli, X-bar/R,
paylaşılan `subgroups` listesini zaten kullanabilir) — bu yüzden
izlenebilirlik alanlarını Nem/KM'ye özel değil, paylaşılan şemaya
eklemek hem "bir parametrede var 24'ünde yok" tutarsızlığını önler hem
de backlog'daki v1.8 maddesini aynı işle kapatır.

## Kapsam

**Dahil:** `L*/a*/b*` HARİÇ tüm 23 parametre (X-bar/R + I-MR, hepsi
paylaşılan `st.session_state.subgroups` listesini kullanıyor).

**Kapsam DIŞI:** Renk Paneli (zaten kendi ayrı modelinde bu alanlara
sahip, v1.7.2), CSV import/export format değişikliği, demo veri
üreticisine yeni parametre eklenmesi (üretilen kayıtlar yeni alanları
varsayılan/otomatik değerle alır, ama CSV/demo KOD'u bu alanları
"üretmeye" özel olarak genişletilmez — YAGNI, Renk Panelinin "bu turda
CSV yok" kararıyla aynı ölçülülük).

## 1) Veri modeli

`st.session_state.subgroups`'daki her kayıt:

```python
{
    "shift": str,           # mevcut - X-bar/R'de gercek vardiya, I-MR'de "-"
    "values": list[float],  # mevcut
    "lot_no": str,           # YENI - opsiyonel, varsayilan ""
    "notes": str,             # YENI - opsiyonel, varsayilan ""
    "urun": str,              # YENI - o an secili "Urun / Hammadde" degeri, OTOMATIK damgalanir
    "timestamp": str,         # YENI - OTOMATIK, datetime.now().isoformat(timespec="seconds")
}
```

Geriye dönük uyumluluk: session-state-only mimari (kalıcı depolama
yok), migrasyon gerekmez. Eski/yeni-alansız kayıt okuyan her kod yolu
`.get("lot_no", "")` vb. ile savunmalı okur (sayfa canlıyken parametre
değişse bile kırılmaz).

## 2) `qc_converters.build_bridge_subgroup_entry` imza değişikliği

```python
def build_bridge_subgroup_entry(value: float | list[float], source_label: str) -> dict:
    """... 'shift_label' parametresi 'source_label' olarak yeniden
    adlandirildi VE ARTIK shift alanina YAZILMIYOR - kaynak etiketi
    ('Totox', 'Gravimetrik Nem/Kuru Madde' vb.) artik notes alanina
    (f"QC Donusturucu - {source_label}") yazilir. shift alani artik
    GERCEK bir vardiya degeri tasir (I-MR icin hala "-", X-bar/R icin
    SHIFT_OPTIONS[0] = "Sabah" - koprulerin gercek bir vardiya bilgisi
    olmadigi icin notr bir varsayilan, kullanici sonradan gecmis
    tablodan duzenleyebilir)."""
```

Bu değişiklik `render_bridge_widget()`'ı (app.py) çağıran 5 köprü
noktasını (Gravimetrik Nem/KM, Titrasyon Asitliği, Tuz/Mohr, Termal
Letalite F₀, Totox) etkiler — hepsi aynı ortak fonksiyonu çağırdığı için
tek bir değişiklik hepsine yayılır.

**Neden `render_shift_comparison`'ı bozmuyor:** bu fonksiyon
`subgroups`'u `shift in SHIFT_OPTIONS` ile gruplar — eski kod
`shift="QC Dönüştürücü - Totox"` yazdığı için bu kayıtlar HİÇBİR
vardiya grubuna dahil edilmiyordu (sessizce dışlanıyordu, bir bug
değil ama fark edilmemiş bir kenar durumdu). Yeni davranışta
`shift="Sabah"` (X-bar/R köprüleri için) artık gerçek bir grup
oluşturuyor — bu, köprüyle eklenen verinin vardiya karşılaştırma
tablosunda görünür hale gelmesi anlamına gelir (önceki sessiz
dışlamadan daha doğru bir davranış, ama görünür bir değişiklik).

## 3) UI değişiklikleri

### Veri girişi formu (hem X-bar/R hem I-MR, `render_generic_data_entry_tab`)

Mevcut alanların (Vardiya seçici [X-bar/R] veya doğrudan ölçüm [I-MR])
altına:
```python
lot_no = st.text_input("Parti/Lot No (opsiyonel)", key=f"lot_no_input_{st.session_state.active_parameter}")
notes = st.text_area("Not (opsiyonel)", key=f"notes_input_{st.session_state.active_parameter}")
```
(Renk Panelinin Task 2'sindeki widget-key + submit-sonrası-sıfırlama
deseniyle aynı — parametre değiştiğinde eski değerlerin görünür
kalmaması için `key`'e `active_parameter` eklenir.)

`urun` alanı: kullanıcı hiçbir şey girmez — subgroup eklenirken o an
`st.session_state.get("product_select", ...)` değeri otomatik okunup
kaydedilir.

### Geçmiş tablo (`st.data_editor`)

Yeni sütunlar: `lot_no`, `notes`, `urun`, `timestamp`. `urun` ve
`timestamp` `disabled=True` (otomatik damgalanmış, düzenlenmesi
anlamsız/yanıltıcı olur); `lot_no`/`notes` mevcut hücre-düzenleme
desenine (`column_config`, serbest metin) dahil edilir.

## 4) Test planı

- `tests/test_qc_converters.py` (mevcut dosya): `build_bridge_subgroup_entry` yeni imza (`source_label` parametre adı, `shift` artık `SHIFT_OPTIONS`'tan bir değer veya I-MR için `"-"`, `notes` alanının kaynak etiketini taşıdığı) için testler.
- Mevcut `render_shift_comparison` davranışını (köprü kayıtlarının artık gruplamaya dahil olduğunu) doğrulayan bir regresyon testi.
- Mevcut tüm testler (267+) değişmeden geçmeli — sadece yeni alanlar eklendiği için hiçbir mevcut assertion bozulmamalı (yeni alanlar mevcut testlerin kontrol ettiği anahtarlara dokunmuyor).

## Bilinçli olarak ertelenenler

- CSV import/export'a lot_no/notes/urun sütunu eklenmesi.
- Demo veri üreticisinin bu alanları "anlamlı" doldurması (şu an
  boş/otomatik değerlerle dolduruluyor, senaryo bazlı değil).
- Renk Paneli'nin bu ortak şemaya geçirilmesi (kasıtlı olarak kendi
  izole modelinde kalıyor — 3 bağımsız eksen mimarisi farklı).
