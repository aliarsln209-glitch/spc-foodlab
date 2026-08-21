# Nem/Kuru Madde Birleşik Panel (Design)

**Durum:** Onaylandı, implementasyon planına geçilecek.

**Alt-proje sırası:** İKİNCİSİ — [[2026-08-21-paylasilan-subgroups-izlenebilirlik-design]]
(Alt-proje 1) üzerine kurulur; `build_bridge_subgroup_entry`'nin
`shift`/`notes`/`urun`/`timestamp` alanları ve `subgroups` şemasının bu
alanlarla genişlemesi burada AYNEN kullanılır, tekrar değiştirilmez.

## Bağlam

`Nem/Rutubet` ve `Kuru Madde` matematiksel olarak bağlı iki ayrı SPC
parametresidir (100 − Nem% = Kuru Madde%), ama bugün tamamen ayrı akışlar:
kullanıcı `Hızlı Hesaplayıcılar` sekmesindeki Gravimetrik Nem/KM
hesaplayıcısıyla TEK bir dara/yaş/kuru ağırlığından ikisini de hesaplıyor,
ama `render_bridge_widget` üzerinden bir dropdown'la SADECE BİRİNİ SPC veri
setine köprüleyebiliyor — diğerini köprülemek için formu tekrar doldurup
diğer hedefi seçmesi gerekiyor. Ayrıca iki parametre farklı chart tipinde
(`Nem/Rutubet` X-bar/R, `Kuru Madde` I-MR) — Veri Girişi/Chart sekmelerinde
birini analiz ederken diğerini görmek için `active_parameter`'ı elden
değiştirmek gerekiyor.

Kod incelemesi: Renk Paneli (`L*`) benzer bir "birden fazla ölçüm tek
numuneden, birlikte kaydedilir/görüntülenir" ihtiyacını `tab_data`/
`tab_chart` içinde `active_parameter == "L*"` kontrolüyle YÖNLENDİREREK
çözüyor (ayrı bir `st.tabs()` girdisi DEĞİL). Aynı desen burada da
kullanılacak.

## Kapsam

**KAPSAM DARALTILDI (self-review sırasında, veri modeli doğrulamasından
sonra):** `st.session_state.subgroups` TEK bir global listedir —
`active_parameter` değişince TAMAMEN silinir (`app.py:306-320`, kullanıcı
onayıyla). Yani `Nem/Rutubet` ve `Kuru Madde` verileri AYNI ANDA session
state'te bulunamaz — "tek Kaydet ikisine birden yazsın" tasarımı bu
mimariyle ÇALIŞMAZ (iki listeyi ayrı tutmak `subgroups`'u
`dict[str, list]`'e çevirmek gibi çok daha büyük, ayrı bir işi
gerektirir — bu spec'in kapsamı DIŞINDA tutuluyor). Bunun yerine: panel
UI'ı (n-üçlü form + lot_no/notes + birlikte görünüm) eklenir, ama "Kaydet"
mevcut `render_bridge_widget` dropdown'ıyla (kullanıcı hedef seçer, TEK
hedefe yazılır) çalışmaya devam eder — `subgroups` mimarisine
DOKUNULMAZ.

**Dahil:**
- Yeni birleşik panel: `active_parameter` `Nem/Rutubet` VEYA `Kuru Madde`
  olduğunda hem `tab_data` hem `tab_chart` bu panele yönlenir.
- Veri girişi: `n` adet (aktif `subgroup_size`) dara/yaş-numune/kuru-kalıntı
  üçlüsü TEK formda (generic formun X-bar/R deseniyle aynı — `st.columns(n)`),
  artı `lot_no`/`notes` (opsiyonel), `urun`/`timestamp` otomatik damgalı.
  Her üçlüden hesaplanan %Nem ve %Kuru Madde CANLI gösterilir (liste
  halinde, n satır).
- "SPC Veri Setine Aktar": mevcut `render_bridge_widget(values_by_target=
  {"Nem/Rutubet": [n adet %Nem], "Kuru Madde": [n adet %Kuru Madde]}, ...)`
  ÇAĞRISI AYNEN KULLANILIR — dropdown'dan `Nem/Rutubet` seçilirse n
  değer BİR X-bar/R alt grubu olarak, `Kuru Madde` seçilirse n değer AYRI
  I-MR köprü çağrılarıyla (döngüde, `render_bridge_widget` I-MR dalı TEK
  değer beklediği için) eklenir. Kullanıcı ikisini de kaydetmek isterse
  dropdown'ı değiştirip AYNI n-üçlü veriyle tekrar basar (ekstra tıklama,
  ama mimari değişikliği gerektirmez).
- Chart sekmesi: `active_parameter`'a göre (Nem/Rutubet SEÇİLİYSE
  X-bar/R, Kuru Madde SEÇİLİYSE I-MR) mevcut `render_generic_chart_tab`
  ÇAĞRILIR (değişmez) — SADECE üstüne, o an `subgroups` içinde HANGİ
  parametrenin verisi varsa (aktif parametre) onun için
  `build_dry_matter_moisture_consistency_note` çağrılabiliyorsa (diğer
  parametrenin AYRI bir referans değeri elle girilmişse, bkz. mevcut
  `app.py:2186-2196`) not gösterilir — bu zaten VAR olan davranış, panel
  SADECE aynı sayfaya n-üçlü giriş formunu ekler.
- `Hızlı Hesaplayıcılar`'daki eski Gravimetrik Nem/KM hesaplayıcısı
  (`render_bridge_widget` çağrısı dahil, `app.py:3282-3309` civarı)
  KALDIRILIR — yeni panel onun yerini alır.

**Hariç:**
- İki parametreyi TEK bir SPC parametresine indirmek (registry'de yapısal
  değişiklik) — reddedilen seçenek, aşırı riskli.
- `subgroup_size` değişikliği/yeni bir alt-grup UI'ı icat etmek — mevcut
  `st.session_state.subgroup_size` aynen kullanılır.
- Renk Paneli'ne dokunmak.

## Veri Modeli

Değişiklik YOK. `st.session_state.subgroups` tek global liste olarak
kalır, `active_parameter` değişince sıfırlanma davranışı (`app.py:306-320`)
AYNEN korunur. Panel, bu listeye `render_bridge_widget` üzerinden yazan
BEŞİNCİ değil, altıncı bir "kaynak" olur — mimari olarak Titrasyon/Tuz/F0/
Totox köprüleriyle birebir aynı.

## Bileşenler

- `render_moisture_dry_matter_data_entry_tab()` (yeni, `app.py`) —
  Veri Girişi yönlendirmesi, n-üçlü form + Kaydet.
- `render_moisture_dry_matter_chart_tab()` (yeni, `app.py`) — iki chart +
  tutarlılık notu.
- `qc_converters.gravimetric_moisture()` — DEĞİŞMEZ, aynen çağrılır (n kez,
  bir döngüde).
- `render_bridge_widget(values_by_target={"Nem/Rutubet": [...n], "Kuru
  Madde": [...n]}, source_label="Gravimetrik Nem/Kuru Madde",
  widget_key_prefix="qc_moisture")` — DEĞİŞTİRİLMEDEN, sadece yeni panel
  içinden çağrılır (bugün `tab_calc` içinde çağrıldığı yerin AYNISI,
  sadece dosyada taşınıyor). Fonksiyonun kendisi SİLİNMEZ, imzası
  değişmez (diğer 4 hesaplayıcı — Titrasyon, Tuz, F0, Totox — hâlâ
  kullanıyor).

## Hata Yönetimi

- `gravimetric_moisture()` her üçlü için ayrı `ValueError` fırlatabilir
  (örn. kuru > yaş) — n üçlüden biri hatalıysa Kaydet butonuna basılmadan
  ÖNCE (canlı, her üçlü hesaplanırken) o üçlünün altında hata gösterilir,
  Kaydet DEVRE DIŞI kalır (mevcut generic formun sayısal-olmayan-değer
  UX'iyle tutarlı — sessizce kısmi kayıt YOK).
- `n` değişirse (sidebar'dan subgroup_size değiştirilirse) form yeniden
  render edilir (mevcut generic formun `key=f"...{active_parameter}"`
  deseniyle aynı — widget key'lerine `n` de eklenmeli ki n değişince eski
  girişler görsel olarak kalmasın).

## Test Stratejisi

- `qc_converters.gravimetric_moisture()` zaten test edili, değişmiyor.
- Yeni: n-üçlü döngüsünün doğru sayıda I-MR noktası + doğru şekilli X-bar/R
  alt grubu ürettiğini doğrulayan smoke/regresyon testleri (`app.py` kaynak
  metni üzerinden, mevcut `test_app_render_smoke.py` deseniyle).
- Canlı (Playwright/manuel) doğrulama ZORUNLU: n=1 ve n=3 ile panели test
  et, her ikisinde de Kuru Madde VE Nem/Rutubet chart'larının doğru
  sayıda nokta aldığını, `lot_no`/`urun`'ün ikisine de doğru yazıldığını
  doğrula.
