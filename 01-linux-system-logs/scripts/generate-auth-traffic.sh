#!/usr/bin/env bash
echo ">>> [Test] Linux sistem ve kimlik doğrulama logları üretiliyor..."
# 1. Başarısız SSH giriş denemesi simülasyonu (etkileşimsiz)
logger -p authpriv.warning -t sshd "Failed password for invalid user nonexistent_user from 127.0.0.1 port 49822 ssh2"

# 2. Sistem logger komutu ile test logu basma
logger -t security_test "UYARI: Bilinmeyen IP adresinden yetkisiz erisim denemesi tespit edildi! (Simulasyon)"
logger -t sudo_test "INFO: appuser tarafindan 'sudo apt update' komutu calistirildi."

echo ">>> Loglar /var/log/auth.log ve /var/log/syslog içerisine yazıldı."
