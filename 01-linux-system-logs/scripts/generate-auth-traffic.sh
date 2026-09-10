#!/usr/bin/env bash
echo ">>> [Test] Linux sistem ve kimlik doğrulama logları üretiliyor..."
# 1. Başarısız SSH giriş denemesi simülasyonu
ssh -o StrictHostKeyChecking=no -o ConnectTimeout=2 nonexistent_user@127.0.0.1 2>/dev/null || true

# 2. Sistem logger komutu ile test logu basma
logger -t security_test "UYARI: Bilinmeyen IP adresinden yetkisiz erisim denemesi tespit edildi! (Simulasyon)"
logger -t sudo_test "INFO: appuser tarafindan 'sudo apt update' komutu calistirildi."

echo ">>> Loglar /var/log/auth.log ve /var/log/syslog içerisine yazıldı."
