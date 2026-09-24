# LAB-ELK-01 — Linux Host Sistem ve Güvenlik Loglarının Toplanması

| Seviye | Profil / Araçlar | Açık Portlar |
|:---:|:---:|:---:|
| Başlangıç | Filebeat, systemd, Logstash, Kibana | 9200 (ES), 15601 (Kibana), 5044 (Logstash Beats) |

[LAB-ELK-01.zip](LAB-ELK-01.zip)

## Amaç
* Linux işletim sisteminin kimlik doğrulama (`/var/log/auth.log`) ve çekirdek/sistem olaylarını (`/var/log/syslog`) Filebeat ajanı ile toplamak.
* Filebeat'i merkezi Logstash boru hattına (`port 5044`) Beats protokolü üzerinden güvenle bağlamak.
* Sunucu üzerinde başarısız SSH oturum denemeleri ve yetkisiz erişim simülasyonları gerçekleştirerek gerçek log akışını tetiklemek.
* Toplanan logların Elasticsearch üzerinde `system-logs-*` indeksine yazıldığını REST API ile doğrulamak.
* Kibana Discover arayüzünde KQL (Kibana Query Language) ile sistem günlüklerini filtrelemek ve alan bazlı inceleme yapmak.

---

## Ön Koşullar
* **Merkezi ELK Omurgası:** `00-elk-core-stack` servislerinin (`elasticsearch`, `logstash`, `kibana`) çalışır durumda olması gerekmektedir. *(Bu servisler kesinlikle durdurulmamalıdır).*
* Logstash servisinin Beats portunun açık olduğunu doğrulayın (`nc -zv localhost 5044`).
* Kimlik Doğrulama Bilgileri: Kullanıcı: `elastic` | Şifre: `BilginIT454`.

---

## Mimari ve Çalışma Modeli

```text
[ Ubuntu Host (/var/log) ]
├── auth.log (SSH & Sudo Olayları) ──┐
└── syslog   (Sistem & Kernel)       ▼
                                [ Filebeat Ajanı ]
                                (Inputs: log, Output: beats)
                                     │
                                     ▼ (Port 5044 Beats TCP)
                          [ Logstash Boru Hattı ]
                          - Index: system-logs-YYYY.MM.DD
                                     │
                                     ▼ (Basic Auth: elastic/BilginIT454)
                          [ Elasticsearch (:9200) ]
                                     ▲
                                     │
                          [ Kibana UI (:15601) ]
                          - Data View: system-logs-*
```

---

## Adım Adım Uygulama Rehberi

### 1. Filebeat Yapılandırmasını İnceleme

`01-linux-system-logs` dizinindeki yapılandırma dosyasını inceleyin:

```bash
cd ~/elk-lab/01-linux-system-logs
cat filebeat-linux.yml
```

Bu yapılandırmada:
* `/var/log/auth.log` dosyası `log_type: system_auth` etiketiyle toplanır.
* `/var/log/syslog` dosyası `log_type: system_syslog` etiketiyle toplanır.
* Çıktı hedefi olarak doğrudan Logstash Beats portu (`localhost:5044`) tanımlıdır.

---

### 2. Filebeat Ajanını Başlatma

Ajanı sisteminize paket kurmadan, host log dizinini salt-okunur (`:ro`) bağlayarak Docker konteyneri ile başlatın:

```bash
docker run -d --name filebeat-linux --net=host \
  --user=root \
  -v $(pwd)/filebeat-linux.yml:/usr/share/filebeat/filebeat.yml:ro \
  -v /var/log:/var/log:ro \
  docker.elastic.co/beats/filebeat:8.17.0 -e -strict.perms=false
```

Konteynerin çalıştığını ve Logstash bağlantısını doğrulayın:

```bash
docker logs --tail=20 filebeat-linux
```

*Loglarda `Connection to backoff(async(tcp://localhost:5044)) established` çıktısını görün.*

---

### 3. Test Güvenlik ve Kimlik Doğrulama Logu Üretme

Sistemde SSH oturum hatası ve logger olayları oluşturmak için hazırlanan test scriptini çalıştırın:

```bash
./scripts/generate-auth-traffic.sh
```

Bu script:
* `127.0.0.1` adresine sahte bir kullanıcı (`nonexistent_user`) ile SSH bağlantısı deneyerek `/var/log/auth.log` içine başarısız oturum kaydı düşürür.
* `logger` komutu ile `/var/log/syslog` dosyasına güvenlik ve sudo test bildirimleri yazar.

---

## Doğal Doğrulama ve Beklenen Sonuç

### 1. Elasticsearch REST API ile Sorgulama

Toplanan logların Elasticsearch'e indekslendiğini terminalden sorgulayın:

```bash
curl -s -u elastic:BilginIT454 "http://localhost:9200/system-logs-*/_search?q=log_type:system_auth&pretty" | jq '{total_hits: .hits.total.value, sample_message: .hits.hits[0]._source.message}'
```

* **Beklenen Sonuç:** `total_hits` değeri 0'dan büyük olmalı ve `sample_message` alanında `Failed password for ... nonexistent_user` veya benzeri kimlik denetim kaydı görüntülenmelidir.

---

### 2. Kibana Discover Ekranında Log İnceleme

1. Tarayıcınızdan Kibana paneline bağlanın:
   * **URL:** `http://<SUNUCU_IP>:15601` veya `https://studentXX-kibana.devopsatolyesi.com`
   * **Giriş:** `elastic` / `BilginIT454`
2. Sol menüden **Analytics > Discover** sekmesine gidin.
3. Sol üstteki Veri Görünümü (Data View) alanından **`Linux Sistem Logs (Auth & Syslog)`** veya kalıp olarak `system-logs-*` seçin. *(Gerekirse Stack Management > Data Views altından `system-logs-*` oluşturabilirsiniz).*
4. Sağ üstteki zaman seçicisini **Last 15 minutes** olarak ayarlayın.
5. KQL arama çubuğuna şu filtreleri yazıp **Enter**'a basın:
   ```text
   log_type : "system_auth"
   ```
   veya sadece SSH hatalarını görmek için:
   ```text
   message : "Failed password"
   ```
6. Sol sütundan `host.name`, `log_type` ve `message` alanlarını ekleyerek olay tablonuzu özelleştirin.

---

## Temizlik

Bu aşamadaki temizlik yalnızca test amacıyla çalıştırılan Filebeat konteynerini durdurur:

```bash
docker rm -f filebeat-linux
```

> **Önemli Not:** Merkezi ELK omurgası (`00-elk-core-stack`), sonraki tüm laboratuvarlar için çalışır durumda kalmalıdır. `docker compose down` komutunu **çalıştırmayın**.
