# Paket deposunu yükleme

Güncel dağıtım biçimi: repository. Önceki GitHub Releases talimatlarının yerine geçer.
GitHub deposunun köküne `packages` klasörünü bütün olarak yükleyin. `release-assets/` altındaki DEB dosyalarını da mutlaka ekleyin. Kataloglar paketleri bu klasörden indirir; ayrıca Release oluşturmak gerekmez.

Yerelde: `python3 packages/publish.py --prepare` ardından `python3 packages/publish.py --check`. İsteğe bağlı `--publish` doğrulama, commit ve push yapar. Sürüm numaralarını değiştirmez.

Store güncellemesi tüm ArchiveOS indirmelerini kurulum öncesinde doğrular. Eksik dosya varsa diğer güncellemeleri başlatmadan durur.
