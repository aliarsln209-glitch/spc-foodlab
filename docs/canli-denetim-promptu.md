# SPC FoodLab — v1.0→v1.7 Canlı Denetim ve Roadmap Kararı

## Kaynaklar
- Canlı uygulama: https://spc-foodlab.streamlit.app
- Repo: https://github.com/aliarsln209-glitch/spc-foodlab
- README: https://github.com/aliarsln209-glitch/spc-foodlab/blob/main/README.md
- METHODOLOGY: https://github.com/aliarsln209-glitch/spc-foodlab/blob/main/METHODOLOGY.md

## Görev
Bu, v1.0'dan v1.7'ye kadar fazlı olarak geliştirilmiş bir SPC (istatistiksel
süreç kontrolü) uygulaması. Kod tarafında 229/229 test geçiyor ama testler
"kodun kendi iddia ettiği doğru" olduğunu kanıtlıyor — uygulamanın gerçekten
kullanılabilir, tutarlı ve dokümantasyonla örtüşen bir bütün olduğunu
kanıtlamıyor. Senin görevin canlı uygulamayı bizzat kullanıcı gibi test edip
şunları bulmak:

1. **Fonksiyonel hatalar** — uygulamada gerçekten çalışmayan, beklenmedik
   davranan veya hata veren akışlar
2. **README/METHODOLOGY ↔ Uygulama tutarsızlıkları** — dokümanın iddia
   ettiği ama uygulamanın yapmadığı (veya tersi) her şey
3. **v1.0-v1.7 arasında unutulmuş/yarım kalmış maddeler** — roadmap'te
   "✅ Tamamlandı" yazan ama gerçekte eksik/tutarsız kalmış olabilecek
   şeyler (özellikle fazlar arası geçişlerde arada kalmış detaylar)
4. **v2.0'a geçiş için hazır olup olmadığı** — kalıcı depolama (SQLite)
   eklemeden önce mevcut session-state mimarisinin sağlam bir temel
   olup olmadığı

## Test Kapsamı (canlı uygulamada bizzat dene)

### A. Her parametre ailesi için uçtan uca akış
- En az 1 X-bar/R parametresi (örn. pH veya Brix), 1 I-MR parametresi
  (örn. Viskozite), 1 mikrobiyoloji parametresi, 1 v1.4-1.6 parametresi
  (örn. Protein) ile: veri gir → baseline dondur → Cpk/Cpu gör →
  PDF/CSV export al. Her adımda beklenmedik davranış var mı?
- Tek taraflı (LSL=None) bir ürün seçip (örn. Bal/Nem) LSL alanının
  gerçekten devre dışı kaldığını, sadece USL/UCL çizildiğini doğrula.
- Sıfıra bölme durumunu tetiklemeyi dene (aynı değeri art arda gir,
  R̄/MR̄=0 durumu) — ∞/-∞ davranışı dokümanla eşleşiyor mu?

### B. v1.7 Köprü Sistemi (en riskli, en yeni kısım)
- `render_bridge_widget` üzerinden en az 3 farklı panelden (Gravimetrik
  Nem, Totox, Titrimetrik) SPC veri setine aktarım yap.
- **Kritik senaryo:** X-bar/R aktifken köprü butonunu tetiklemeyi dene —
  METHODOLOGY.md'nin iddia ettiği gibi engelleniyor mu?
- **Kritik senaryo:** Totox dropdown'ından aktif olmayan bir parametre
  seçip ne olduğunu gözlemle — sessizce yanlış yere mi yazıyor, engelleniyor
  mu, yoksa aktif parametreyi mi değiştiriyor? (Bu, geçen oturumda
  netleştirilmesi istenip teyit edilmemiş olabilecek bir nokta.)
- Brix sıcaklık düzeltmesi hâlâ "kaynak bekliyor" durumunda mı, yoksa
  kullanıcıya yanlışlıkla tam işlevmiş gibi mi gösteriliyor?
- **Köprü zincirleme senaryosu:** Aynı oturumda önce Gravimetrik Nem'den,
  sonra Totox'tan aynı I-MR parametresine art arda ekleme yap. Subgroup
  sırası/etiketleme (hangi kaynaktan geldiği, shift/tarih etiketi) tutarlı
  kalıyor mu, yoksa karışıyor/üzerine mi yazılıyor?

### C. Hammadde Kütüphanesi + Ürün Referans Tutarlılığı
- "Özel/Manuel gir" gerektiren kombinasyonlarda gerçekten hiçbir
  varsayılan sayı önerilmiyor mu (bir placeholder/default sızıntısı var mı)?
- Kaynaklı bir ürün (örn. Zeytinyağı — Yoğunluk/Refraktif İndeks) ile
  kaynaksız bir ürün arasında geçiş yaparken limit alanları doğru
  temizleniyor/dolduruluyor mu?

### D. Çapraz Parametre Tutarlılık Kontrolü (v1.5)
- Kuru Madde + Nem ≈ 100 uyarısını gerçekten tetikleyip tetiklemediğini
  test et — bloklamıyor mu (dokümanın iddiası), sadece bilgilendiriyor mu?

### E. Dokümantasyon Çapraz Kontrolü
- README.md ve METHODOLOGY.md'yi satır satır uygulamanın gerçek davranışıyla
  karşılaştır. Özellikle:
  - "9 parametre" / "25 parametre" gibi sayısal iddialar güncel mi?
  - Test sayısı (229) güncel mi, README'de farklı bir sayı mı yazıyor?
  - v1.7'nin "🟡 Kısmen tamamlandı" etiketi hem METHODOLOGY hem README'de
    tutarlı mı, yoksa biri güncellenip diğeri unutulmuş mu?

## Kanıt Kuralı (zorunlu)
Her bulgu somut tekrarlama adımlarıyla desteklenmeli: hangi parametre,
hangi ürün, hangi değerler girildi, hangi sırayla tıklandı, ne beklendi,
ne oldu. "Muhtemelen", "büyük ihtimalle" gibi ifadelerle bulgu raporlama —
ya bizzat tetikleyip kanıtla, ya da "doğrulanamadı, şu sebeple test
edilemedi" diye ayrıca işaretle. Doğrulanmamış iddia, iddia değildir.

Sayısal iddialar (hesaplanan Cpk, Cpu, F₀, gerekli sigma vb.) için ekranda
görünen değeri **tam metin/sayı olarak alıntıla** — kendi yorumunla
("yaklaşık", "civarında") aktarma. Mümkünse ekran görüntüsü de ekle.

### F. Ters Cpk Hesaplayıcısı (v1.4, Δσ%/k-faktörü)
- Hedef Cpk gir, gereken sigma + Δσ% + k-faktörü çıktısını al.
  METHODOLOGY.md'de tanımlı formülle (kendi uydurduğun bir formülle değil)
  elle hesapla ve karşılaştır. METHODOLOGY.md'de formül yoksa veya
  belirsizse bunu ayrıca "formül kaynağı doğrulanamadı" diye işaretle —
  kendi varsayımınla "tutarlı" sonucu raporlama.
- Bu özellik "Hızlı Hesaplayıcılar" sekmesinde gerçekten erişilebilir mi,
  yoksa gömülü kalıp bulunması zor mu?

### G. Manuel Giriş Etiketleme Tutarlılığı
- Hammadde Kütüphanesi'nde kaynaksız bir kombinasyon (örn. Süt tozu -
  pH) seçildiğinde arayüzde "kaynaksız, kullanıcı girişi" türü bir
  etiket/uyarı gerçekten görünüyor mu?
- Faz 2 asit faktörleri (Titre Edilebilir Asitlik) veya Tuz (Mohr) için
  kaynaklanamayan bir kombinasyon varsa, aynı etiketleme deseni orada da
  tutarlı mı, yoksa farklı/eksik mi görünüyor?

### H. Deploy/CI Senkronizasyonu
- GitHub Actions'ta son workflow run'ın (main'deki son commit'e karşılık
  gelen) yeşil olduğunu doğrula.
- Canlı Streamlit uygulamasının gerçekten `main`'deki son commit'i
  yansıttığından emin ol (ör. v1.7 köprü panelleri canlıda görünüyor mu,
  yoksa hâlâ eski bir deploy mi çalışıyor?).

### I. Session-State Kalıcılığı (v2.0 kararı için doğrudan girdi)
- Veri girdikten sonra tarayıcı sekmesini yenile (F5) veya kapat-aç —
  veri ne zaman/ne kadarı kayboluyor? Kullanıcıya bu konuda herhangi bir
  uyarı gösteriliyor mu (dokümanda "session-state, kalıcı değil" notu
  var mı, varsa arayüzde de görünür mü, yoksa sadece dokümanda mı kalmış)?
- Aynı oturum içinde birden fazla parametre arasında ileri-geri geçiş
  yap (örn. pH → Viskozite → pH) — önceki girilen veriler korunuyor mu,
  yoksa parametre değişiminde sessizce sıfırlanıyor mu?
- Bu davranış v2.0'ın "kalıcı depolama" gerekçesiyle örtüşüyor mu, yoksa
  README/METHODOLOGY session-state'in kapsamını farklı tarif ediyor mu?

### J. Girdi Doğrulama Sınırları
- Negatif değer, boş alan, aşırı büyük sayı (örn. 1e9), metin girilen
  sayısal alan gibi geçersiz girdileri en az 2-3 parametrede dene.
  Uygulama engelliyor mu, sessizce kabul edip grafiği bozuyor mu, yoksa
  anlamlı bir hata mesajı mı veriyor?
- Bu davranış tüm parametrelerde (X-bar/R, I-MR, köprü panelleri) tutarlı
  mı, yoksa bazı panellerde doğrulama eksik mi?

### K. Mobil/Dar Ekran Görünümü
- Uygulamayı dar bir viewport'ta (mobil genişlik) aç. Dropdown'lar,
  tablolar ve grafikler düzgün render oluyor mu? Köprü widget'ının
  dropdown + buton akışı dar ekranda kullanılabilir mi, yoksa elemanlar
  üst üste biniyor/taşıyor mu?

## Raporlama Formatı
Bulgularını şu başlıklarla raporla:

1. **Kritik hatalar** (kullanıcıyı yanlış sonuca götürebilecek, veri
   bütünlüğünü bozabilecek şeyler) — varsa
2. **Dokümantasyon tutarsızlıkları** (README/METHODOLOGY ↔ gerçek davranış)
3. **Arada kalmış/unutulmuş maddeler** (v1.0-v1.7 roadmap'inde "tamamlandı"
   denip gerçekte eksik kalan noktalar, varsa)
4. **v2.0'a geçiş tavsiyesi:** Doğrudan v2.0'a (kalıcı depolama) geçilmeli
   mi, yoksa önce bir "v1.7.1 — sağlamlaştırma" gibi ara adım mı gerekiyor?
   Gerekçeni somut bulgulara dayandır, varsayımla değil.

Her bulguyu "kanıtlanmış hata" / "şüpheli, doğrulanmalı" / "iyileştirme
önerisi" olarak etiketle — üçünü karıştırma, ciddiyetleri farklı.
