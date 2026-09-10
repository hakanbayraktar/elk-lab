#!/usr/bin/env bash
set -euo pipefail

echo ">>> [1/3] Filebeat GPG Anahtarı ve Deposu Ekleniyor..."
sudo apt update && sudo apt install -y curl gnupg ca-certificates
curl -fsSL https://artifacts.elastic.co/GPG-KEY-elasticsearch | sudo gpg --dearmor -o /usr/share/keyrings/elastic-keyring.gpg --yes
echo "deb [signed-by=/usr/share/keyrings/elastic-keyring.gpg] https://artifacts.elastic.co/packages/8.x/apt stable main" | sudo tee /etc/apt/sources.list.d/elastic-8.x.list

echo ">>> [2/3] Filebeat Kuruluyor..."
sudo apt update && sudo apt install -y filebeat

echo ">>> [3/3] Yapılandırma Kopyalanıyor ve Servis Başlatılıyor..."
sudo cp ../filebeat-linux.yml /etc/filebeat/filebeat.yml
sudo chmod 600 /etc/filebeat/filebeat.yml
sudo systemctl enable --now filebeat
sudo systemctl status filebeat --no-pager
echo ">>> Filebeat başarıyla çalışıyor."
