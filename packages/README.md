# aos-packages · packages/

ArchiveOS uygulamalarının ArchiveStore kataloğu, logoları ve ekran görüntüleri.

- `packages.json`: gerçek DEB metadatası, indirme URL'si, boyut ve SHA256.
- `logos.json`: DEB `Package` kimliği → depodaki logo yolu.
- `screenshots.json`: DEB `Package` kimliği → depodaki ekran görüntüleri listesi.
- `repository.json`: depo bağlantısı ve şema bilgisi.
- `logos/<paket>.svg|png`: özgün paket simgesi.
- `screenshots/<paket>/1.png`: gerçek uygulamanın izole önizleme ortamında alınmış arayüzü.
- `release-assets/`: DEB dosyaları; katalog ve görsellerle birlikte GitHub main dalında tutulur.

## Hazır paketler

ArchiveStore, Welcome, Terminal, Gaming Center, Windows App Support, Touch Keyboard,
About ArchiveOS, Pomodoro ve Archive (dinamik ada). Store'a birleşen eski kaldırıcı/kurucu/updater ayrı sunulmaz.
Pomodoro mağazada bağımsızdır; Desktop/main güncelleme paketine eklenmez.
Bu katalog mevcut ArchiveOS/KDE hedefi içindir; herhangi bir Debian sistemiyle
uyumluluk garantisi değildir. Ekran görüntüleri gerçek uygulama arayüzlerini gösterir;
önizleme oturumunun sürüm, donanım ve boş kitaplık bilgileri örnektir.

## Yayın

Depo: https://github.com/archive-os/aos-packages
JSON, DEB, logo ve ekran görüntüleri depo kökündeki packages/ klasöründedir.
Store, elle yüklenen packages/release-assets klasöründeki DEB'leri de destekler. JSON'daki
eski null indirme adresi bu klasöre göre çözülür; aynı sabit commit'ten okunan DEB'in
boyutu, SHA256 ve paket kimliği kurulumdan önce doğrulanır.

```bash
python3 packages/publish.py https://github.com/archive-os/aos-packages
```

Gereksinimler: Python 3 + Pillow, dpkg-deb, git, gh; GitHub oturum açılmış olmalı.
Betik kataloğu doğrular, URL'leri bağlar, katalog/görseller/DEB'leri main'e gönderir.
Mevcut depoda yeni bir checkout kullanır; LICENSE gibi ilgisiz dosyaları ve geçmişi
korur. Force push yapmaz. Paket kurulumu yapmaz.

Yerel kontrol (ağa çıkmaz):

```bash
python3 packages/publish.py --check
```

Yalnız yerel URL hazırlığı için `python3 packages/publish.py https://github.com/archive-os/aos-packages --prepare`
kullanılabilir; bu seçenek ağ bağlantısı veya yayın yapmaz.
Göreli görsel yolları depo köküne göredir; Store bunları GitHub raw URL'lerine çözer.
Bu klasör APT deposu değildir; ArchiveStore tarafından okunan uygulama kataloğudur.

## Archive

Uygulamanın adı **Archive**, görünen sürümü **1.0.1**. Paket kimliği `archive-companion`, teknik Debian sürümü `2:1.0.1`; epoch önceki paketlerden normal yükseltme sırasını korur. DEB: `release-assets/archive-companion_1.0.1_all.deb`.

Şarj/USB bildirimleri, tema rengine uyan imagegen simgeleri, yalnız derece ve simge gösteren dock hava durumu, sayfaya özel boyutlar, kaldırılıp geri eklenebilen gözler, dock taşıma ve elle duygu seçimi bulunur.

## Siyah tema iyileştirmesi

Dokuz uygulamanın sürüm notu: **siyah tema iyileştirildi**. Koyu yüzeyler siyah ve nötr gridir; açık temalar korunur. Terminalin yazı alanı da siyahtır. Gaming Center logosu güncel paketle eşleştirilmiştir.

Bütün katalog önizlemeleri siyah temada yenilenmiştir. Görseller izole profilde alınmış gerçek Qt offscreen pencere görüntüleridir; fiziksel masaüstü çekimi değildir. Archive medya/hava durumu ve şarj/USB içerikleri örnektir.

Archive'ın mağazada AOS Apps altında görünmesi ve kaldırılabilmesi için güncellenen `archive-store_1.2.7_all.deb` de yüklenmelidir. Diğer sistem paketlerinin korumaları korunur.

Yalnız katalogda kullanılan 9 güncel DEB tutulur. Paketler bu çalışma sırasında sisteme kurulmamış ve GitHub'a gönderilmemiştir. Aynı sürümlü yeniden oluşturulan paketler için yeniden kurulum gerekebilir.

Archive görünen sürümü1.0.1;Debianepoch2 normalyükseltme sırasını korur.Gözlerwidgetı kaldırılabilir,kenartaşıma veelleduyguseçimi düzeltilmiştir.Tümuygulama katalogönizlemeleri gerçekpencerelerin siyah temalı offscreen çekimleriyle yenilenmiştir.

Archive1.0.1: küçülmüş çizgi seçilenkenar,ekran,hizalamayı açıkadaylabirlikte izler.Sağ/solçizgidikey,üst/altçizgiyataydır.
