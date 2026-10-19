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
About ArchiveOS ve Pomodoro. Store'a birleşen eski kaldırıcı/kurucu/updater ayrı sunulmaz.
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
