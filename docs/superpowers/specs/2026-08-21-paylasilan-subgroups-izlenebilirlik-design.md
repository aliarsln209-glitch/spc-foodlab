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

**`urun` alanının doğruluğu (spec review'da soruldu, kod incelemesiyle
doğrulandı):** köprü noktalarında (Totox, F₀ vb.) aktif "Ürün/Hammadde"
seçiminin köprünün kendi ürünüyle alakasız olabileceği endişesi vardı.
Kod incelemesi şunu gösterdi: `render_bridge_widget()`'ın
`target_is_active` kapısı, köprü butonunun SADECE `target ==
st.session_state.active_parameter` iken render edilmesini zorunlu
kılıyor (`app.py`, mevcut Faz 1 tasarımı) — yani kullanıcı köprüyü
tetiklemeden ÖNCE hedef parametrenin Chart sekmesine gidip orada ürünü
seçmiş OLMAK ZORUNDADIR. `reset_parameter_scoped_state()` her parametre
değişiminde `product_select` widget key'ini siler (`app.py:225`), ve
sekmeler arası geçiş bir rerun TETİKLEMEDİĞİ için (`tab_chart`,
`tab_calc`'tan ÖNCE aynı script çalışmasında render edilir) köprü
tıklandığı anda `st.session_state.product_select` her zaman O AN aktif
parametrenin gerçekten seçili ürününü taşır — yanlış ürün yakalama
riski yapısal olarak yoktur. **Yine de implementasyon planına canlı
(Playwright) doğrulama adımı eklenecek** (iddia değil, kanıt).

Geriye dönük uyumluluk: session-state-only mimari (kalıcı depolama
yok), migrasyon gerekmez. Eski/yeni-alansız kayıt okuyan her kod yolu
`.get("lot_no", "")` vb. ile savunmalı okur (sayfa canlıyken parametre
değişse bile kırılmaz).

## 2) `qc_converters.build_bridge_subgroup_entry` imza değişikliği

**Düzeltme (spec review sonrası):** ilk taslakta X-bar/R köprüleri için
sabit `shift="Sabah"` varsayımı vardı — bu, "sessiz dışlama"yı "sessiz
yanlış-etiketleme"yle değiştirirdi (akşam vardiyasında girilen bir
Totox köprü kaydı yanlışlıkla "Sabah" grubuna sayılırdı). Doğrusu:
kullanıcı gerçek vardiyayı seçsin.

```python
def build_bridge_subgroup_entry(value: float | list[float], shift: str, notes: str) -> dict:
    """... 'shift_label' parametresi kaldirildi, yerine IKI ayri parametre
    geldi: 'shift' (gercek vardiya degeri - cagiran taraf belirler) ve
    'notes' (kaynak etiketi, orn. "QC Donusturucu - Totox" - artik
    notes alanina yazilir, shift'i HACKLEMEZ)."""
```

`render_bridge_widget()` (app.py) çağıran taraf artık şunu yapar:
- **I-MR hedefler:** `shift = "-"` (mevcut I-MR kuralıyla tutarlı, değişmedi).
- **X-bar/R hedefler:** yeni bir `st.selectbox("Vardiya", SHIFT_OPTIONS, key=f"{widget_key_prefix}_shift")` eklenir — kullanıcı köprüyü tetiklemeden ÖNCE gerçek vardiyayı seçer, bu değer `shift` olarak geçirilir. Sabit varsayım YOK.
- Her iki durumda da `notes = f"QC Dönüştürücü - {source_label}"`.

Bu değişiklik `render_bridge_widget()`'ı çağıran 5 köprü noktasını
(Gravimetrik Nem/KM, Titrasyon Asitliği, Tuz/Mohr, Termal Letalite F₀,
Totox) etkiler — hepsi aynı ortak fonksiyonu çağırdığı için tek bir
değişiklik hepsine yayılır; X-bar/R hedefleyen köprüler (şu an: Gravimetrik
Nem/KM, Titrasyon Asitliği, Tuz/Mohr) yeni Vardiya seçiciyi otomatik kazanır.

**Neden `render_shift_comparison`'ı bozmuyor, aksine düzeltiyor:** bu
fonksiyon `subgroups`'u `shift in SHIFT_OPTIONS` ile gruplar — eski kod
`shift="QC Dönüştürücü - Totox"` yazdığı için bu kayıtlar HİÇBİR
vardiya grubuna dahil edilmiyordu (sessizce dışlanıyordu, bir bug değil
ama fark edilmemiş bir kenar durumdu). Yeni davranışta köprü kaydı,
kullanıcının O AN seçtiği GERÇEK vardiyaya yazılır — veri artık hem
görünür hem doğru etiketli.

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

**Düzeltme (plan yazarken kod okunarak bulundu):** ilk taslakta
`lot_no`/`notes` düzenlenebilir (`disabled=False`) olacaktı — ama
`csv_io.py` incelemesi şunu gösterdi: "Değişiklikleri kaydet" butonu
`edited_df`'i `csv_io.parse_uploaded_dataframe()`'e verir, bu fonksiyon
(CSV import ile PAYLAŞILAN aynı kod) **"Olcum" ile başlamayan ve
"Vardiya" olmayan HER sütunu sessizce yok sayıp atar** (docstring:
"'Ortalama'/'Range' gibi export'ta bulunan ama 'Olcum' ile başlamayan
ekstra sütunlar yok sayılır"). Yani `lot_no`/`notes`'u düzenlenebilir
yapıp CSV import'a dokunmamak (kapsam dışı kararı, yukarıda) BİRLİKTE
şu anlama gelirdi: kullanıcı geçmiş tabloda bir `lot_no` düzenleyip
"Değişiklikleri kaydet"e bassa, düzenlemesi SESSİZCE kaybolurdu — tam
da bu oturumda defalarca yakaladığımız türden bir sessiz veri kaybı.

**Düzeltilmiş karar:** yeni 4 sütunun (`lot_no`, `notes`, `urun`,
`timestamp`) HEPSİ `disabled=True` (salt-okunur) — hücre-düzenleme bu
turda YOK, sadece görüntüleme. `parse_uploaded_dataframe`'e dokunmadan
bu, tek tutarlı seçenektir (CSV import'a dokunmama kararıyla çelişmez).
Satır ekleme/silme (`num_rows="dynamic"`) hâlâ çalışır çünkü o zaten
`parse_uploaded_dataframe`'in "Olcum"/"Vardiya" sütunlarını yeniden
işlemesiyle uyumlu — yeni satırlar `lot_no=""`, `notes=""`,
`urun=<mevcut secili urun>`, `timestamp=<o anki zaman>` ile
otomatik doldurulur (CSV import'un zaten yaptığı gibi, mevcut değer
yoksa varsayılana düşer).

## 4) Test planı

- `tests/test_qc_converters.py` (mevcut dosya): `build_bridge_subgroup_entry` yeni imza (`shift`, `notes` parametreleri açıkça geçiriliyor; `notes` kaynak etiketini taşıyor, `shift` hackleme YOK) için testler.
- Mevcut `render_shift_comparison` davranışını (köprü kayıtlarının artık kullanıcının seçtiği GERÇEK vardiyayla gruplamaya dahil olduğunu) doğrulayan bir regresyon testi.
- Mevcut tüm testler (267+) değişmeden geçmeli — sadece yeni alanlar eklendiği için hiçbir mevcut assertion bozulmamalı (yeni alanlar mevcut testlerin kontrol ettiği anahtarlara dokunmuyor).
- **Canlı (Playwright) doğrulama, zorunlu adım:** `urun` alanının köprü noktalarında gerçekten doğru ürünü yakaladığı iddia değil kanıtla gösterilecek — örn. "Peroksit Değeri" parametresinde "Zeytinyağı (naturel sızma)" ürününü seçip Totox köprüsüyle bir kayıt eklendiğinde, geçmiş tablosundaki `urun` sütununun "Zeytinyağı (naturel sızma)" gösterdiği ekran görüntüsüyle doğrulanacak. Ayrıca yeni Vardiya seçicinin (X-bar/R köprüleri) gerçekten seçilen değeri kaydettiği ve `render_shift_comparison` tablosunda doğru grupta göründüğü de canlı test edilecek.

## Bilinçli olarak ertelenenler

- CSV import/export'a lot_no/notes/urun sütunu eklenmesi.
- Demo veri üreticisinin bu alanları "anlamlı" doldurması (şu an
  boş/otomatik değerlerle dolduruluyor, senaryo bazlı değil).
- Renk Paneli'nin bu ortak şemaya geçirilmesi (kasıtlı olarak kendi
  izole modelinde kalıyor — 3 bağımsız eksen mimarisi farklı).
