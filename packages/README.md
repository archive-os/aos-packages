# ArchiveOS paket deposu

ArchiveStore uygulama ve sistem güncellemelerini bu depodan kontrol eder.
Store sürümü **1.2.8**; diğer uygulamaların sürümleri korunmuştur.
Yerel katalog hazırlanmıştır; GitHub yayını henüz yapılmamıştır.

## Yapı

```text
packages/
  repository.json       Depo/ana dal/katalog bilgisi
  packages.json         Uygulama ve sistem DEB metadatası
  logos.json            Uygulamaların logo yolları
  screenshots.json      Uygulamaların önizleme yolları
  logos/                Küçük görseller; Git içinde
  screenshots/          Önizlemeler; Git içinde
  release-assets/       Yerel DEB hazırlama alanı; yeni DEBler Git'e eklenmez
  system.json           ArchiveOS Desktop 2.0.4 sistem paketi manifesti
  examples/             Etkin olmayan, doldurulacak sistem paketi örnekleri
  validate.py           Yerel bütünlük ve şema kontrolü
  publish.py            Hazırlık / kontrol / açık yayın komutu
  test_repository.py    Ağsız depo ve yayın akışı testleri
```

DEBler **GitHub Releases** dosyaları olarak sunulur. JSON ve görseller `main`
dalındaki `packages/` altında kalır. Store kataloğu ve görselleri aynı committen
okur; DEB boyutunu, SHA256 değerini ve paket kimliğini doğrular.
`release-assets/` APT deposu değildir ve bir HTTP sunucusu olarak kullanılmaz.

## Yerel hazırlık ve kontrol

Depo kökünde:

```bash
python3 packages/publish.py --prepare
python3 packages/publish.py --check
python3 -m unittest discover -s packages -p 'test_repository.py'
```

`--prepare` dosya içeriklerinden kararlı bir katalog etiketi üretir ve Release
bağlantılarını yazar. **Sürüm numarası belirlemez/artırmaz.** Ağ erişimi, yükleme,
Git stage/commit/push veya sistem kurulumu yapmaz. `--check` dosya değiştirmez.

Yeni sürüm eklerken önce gerçek DEB `release-assets/` içine yerleştirilir.
`packages.json` girdisindeki sürüm, dosya adı, boyut ve SHA256 gerçek DEB ile
uyumlu olmalıdır. Sonra `--prepare` ve `--check` çalıştırılır.
Yayın sonrası yeni checkout içinde DEBler bulunmaz. Daha önce yayınlanmış kataloğun
DEBlerini yerel hazırlama alanına almak için `python3 packages/publish.py --download`
kullanılır. Bu komut ağdan indirir ve doğrular; sürüm değiştirmez veya yayın yapmaz.
Mevcut farklı yerel DEBin üzerine yazmaz. Henüz yayınlanmamış bu yeni kataloğun
Release dosyaları uzak sunucuda bulunmayabilir; mevcut yerel DEBler korunmalıdır.

Sistem sürümünü Hakkı belirler; uygulama sürümü yalnız açık yayın kararıyla değişir.

## GitHub yayını

Bu komut **yayın yapar**; yalnız yayın istendiğinde çalıştırılır:

```bash
python3 packages/publish.py --publish
```

Gereksinimler: Python3, Pillow, dpkg/dpkg-deb, git, gh ve yetkili GitHub oturumu.
Checkout `main` dalında, origin `https://github.com/archive-os/aos-packages`
olmalıdır (`.git` son eki de kabul edilir). Önceden stage edilmiş değişiklikler
varsa betik durur; ilgisiz kullanıcı değişikliklerini commit etmez.

Akış: yerel doğrulama → uzak dal kontrolü → taslak Release → eksik DEBleri yükleme
→ uzaktan her dosyayı indirip boyut/SHA256 doğrulama → Release'i görünür yapma
→ yalnız katalog/görsel/depo araçlarını commit/push → uzak commit ve katalog kontrolü.
Mevcut farklı bir Release dosyasının üzerine yazılmaz; hata durumunda katalog
push edilmez. Yayın yeniden çalıştırılabilir; eşleşen dosyalar yeniden yüklenmez.
Git metadata push'u başarısızsa doğrulanmış ama henüz katalogdan bağlanmayan Release
kalabilir; normal push hatası çözülüp aynı komut tekrar çalıştırılır.

Eski takip edilen DEBler yalnız yayın sırasında Git indeksinden çıkarılır;
**yerel dosyalar korunur**. Geçmiş commitler yeniden yazılmaz, force push yapılmaz.
Katalog etiketi paket içeriklerinden üretilen teknik bir etikettir, sistem sürümü değildir.

## Sistem paketleri

Branding, Plymouth, GRUB, SDDM, temalar ve Recovery de aynı `packages.json`
içinde ayrı DEBler olarak yer alabilir. Girdide `system_package: true` bulunur;
arayüzsüz paketlerde desktop_id, logo ve ekran görüntüsü zorunlu değildir.
Bu paketlerin kendileri henüz hazırlanmadı. Initramfs/GRUB yenilemesini ilgili
DEB maintainer script/triggerları yürütür. Plymouth değişikliği tek başına
kernel sürümünü artırmayı gerektirmez; açılış imajı yenilenir.

Dağıtım sürümü yayınlanacağı zaman `examples/system.json.example` doldurulup
`system.json` olarak kopyalanır. `version` Hakkı'nın söylediği sürüm olur;
`packages` yalnız zorunlu, system_package olarak işaretli sistem DEBlerini içerir.
Örnekteki null/boş alanlarla yayın kontrolü geçmez; örnek dosya etkin değildir.
Store tüm gerekli paketler doğrulanmadan sistem sürümünü tamamlandı saymaz.

Archive/Pomodoro gibi kaldırılabilir uygulamalar zorunlu sistem listesine eklenmez.
Eksik isteğe bağlı uygulamalar mevcut güncelleme akışında geri kurulmaz.
Yeni uygulamayı bir kez otomatik kurma/sonraki kaldırma tercihini izleme politikası
ve Store Onar sayfası ayrı geliştirmelerdir; katalog alanı eklemek bunları etkinleştirmez.

## Hazır uygulamalar

Gaming Center, Terminal, Touch Keyboard, Welcome, Windows App Support, About,
ArchiveStore, Pomodoro ve Archive: ArchiveOS Desktop ile toplam 10 paket. Archive adı ve görünen sürümü
1.0.1, teknik sürümü 2:1.0.1 olarak korunur. Siyah tema ve mevcut görseller korunur.
Önizlemeler izole Qt ortamında alınmıştır; fiziksel sistem kurulum kanıtı değildir.
Büyük DEBler de Release asset olarak taşınır; her dosya 2 GiB'den küçük olmalıdır.
## Beyaz tema görselleri
Beyaz tema destekleyen sekiz uygulama için screenshots/<paket>/white.png eklendi ve screenshots.json içine bağlandı. Siyah görseller korunur. Archive mevcut sürümde sabit siyah tasarım kullandığı için beyaz görsel eklenmedi. Terminalin beyaz görseli gerçek Görünüm/Ayarlar penceresidir. Görseller izole Qt offscreen çekimleridir; örnek durumlar BILGI.txt dosyalarında açıklanır.

## ArchiveOS Desktop — güncel hazırlık
`archiveos-desktop_2.0.4_all.deb` mevcut main2.0.4 içeriğinden hazırlanmıştır;
branding, Plasma/SDDM/Plymouth temaları, ikonlar, duvar kâğıtları ve masaüstü
varsayılanlarını içerir. Recovery ve uygulama DEBleri dahil değildir. APT source
listesi ve OS kimlik dosyaları paketlenmez. `system_package:true`,
`store_hidden:true`; uygulama mağazası listelerinde görünmez. `system.json` ilk
kurulumu da sistem güncellemesi olarak seçer. Store1.2.8 gelişmiş ayarlar altında
kaynak listesi düzenleme ve gizli sistem paketi desteği içerir. Yerel paketler
hazırdır; gerçek VM kurulum/boot testi ve yayın henüz yapılmadı.

## Güncel katalog uyumluluğu ve mağaza kuralları
Düzenlenecek ana katalog **packages-v2.json** (10paket). `publish.py --prepare`,
aynı Release etiketiyle eski1.2.7uyumlu8uygulamalık `packages.json` üretir.
EskiStore1.2.8güncellemesini buradan görür;1.2.8 extended_catalog işaretini okuyup
aynısabitcommitten tamkataloğa geçer. Önce elle kurulum zorunluluğu çözüldü.
Yalnız `packages.json` değiştirmeyin; --check iki katalog eşliğini denetler.
Desktop yalnız güncelleme varsa Güncellemelerde görünür;mağazadan kaldırılamaz.
Ubuntu/Kubuntu vb masaüstü metapaketleri mağazanın hiçbir listesinde bulunmaz,
doğrudan/dolaylı güncelleme planlarına alınmaz;temel güvenlik/kernel/Plasma
kütüphanelerinin güncellemeleri sürer.
Store simgeleri elle hazırlanmış SVG;görseller ayrı pencere yerine mağaza içinde.
GerçekVM kurulum/Timeshift/boot testi hâlâ açık;hostkurulum/yayın yapılmadı.

Son hazırlık: Desktop açıkmavi monitör/AOSSVG logosu DEB+hicolor ve logos.json içinde. APT/Flatpak/ArchiveOS kaynakları Gelişmiş kullanıcı ayarları altında. Yenile/metin veDEB/maviDebiangirdabı ayrımı. Son medya talebi:gerçek sistem güncellemesindePlaying MPRIS duraklatılır,Başlatma ile aynıowner/track geri sürer,rebootta sürmez;önizleme medyaya dokunmaz.
