# LAB-ELK-01 — Linux Host Sistem ve Güvenlik Loglarının Toplanması

| Seviye | Profil / Araçlar | Açık Portlar |
|:---:|:---:|:---:|
| Başlangıç | Filebeat, systemd, Logstash, Kibana | 9200 (ES), 15601 (Kibana), 5044 (Logstash Beats) |

[LAB-ELK-01.zip](LAB-ELK-01.zip)

> [!IMPORTANT]
> **DİKKAT: `00-elk-core-stack` AÇIK KALMALIDIR!**
> Bu laboratuvardaki işlemler merkezi ELK omurgasına bağlanır. `00-elk-core-stack` dizinindeki Elasticsearch, Logstash ve Kibana servislerini **kesinlikle durdurmayın veya silmeyin**. Tüm lablar bu ortak omurga üzerinden çalışır.

---

## Amaç
* Linux işletim sisteminin kimlik doğrulama (`/var/log/auth.log`) ve sistem olaylarını (`/var/log/syslog`) Filebeat ajanı ile toplamak.
* Filebeat'i merkezi Logstash boru hattına (`port 5044`) bağlamak.
* Sunucu üzerinde başarısız SSH oturum denemeleri yaparak gerçek log akışı üretmek.
* Toplanan logların Elasticsearch üzerinde `system-logs-*` indeksine yazıldığını doğrulamak.
* Kibana Discover ekranında KQL ile logları aramak ve incelemek.

---

## Ön Koşullar
* **Merkezi ELK Omurgası:** `00-elk-core-stack` servislerinin (`elasticsearch`, `logstash`, `kibana`) çalışıyor olması gereklidir.
* Port Kontrolü: Terminalden `nc -zv localhost 5044` yazarak Logstash Beats portunun açık olduğunu doğrulayın.
* Giriş Bilgileri: Kullanıcı: `elastic` | Şifre: `BilginIT454` | Port: `15601`.

---

## Mimari ve Çalışma Modeli

```text
[ Ubuntu Host (/var/log) ]
├── auth.log (SSH & Yetkilendirme) ──┐
└── syslog   (Sistem & Çekirdek)     ▼
                                [ Filebeat Ajanı ]
                                     │
                                     ▼ (Port 5044 Beats)
                          [ Logstash Boru Hattı ]
                                     │
                                     ▼ (Basic Auth: elastic/BilginIT454)
                          [ Elasticsearch (:9200) ]
                          - İndeks: system-logs-YYYY.MM.DD
                                     ▲
                                     │
                          [ Kibana UI (:15601) ]
                          - Data View: system-logs-*
```

---

## Adım Adım Uygulama Rehberi

### Adım 1: Lab Dizinine Geçin ve Ayarları İnceleyin

Terminalde ilgili dizine geçin ve Filebeat yapılandırmasını görüntüleyin:

```bash
cd ~/elk-lab/01-linux-system-logs
cat filebeat-linux.yml
```

*Bu dosyada `/var/log/auth.log` ve `/var/log/syslog` dosyalarının okunup `localhost:5044` portundaki Logstash'e gönderildiği tanımlanmıştır.*

---

### Adım 2: Filebeat Ajanını Başlatın

Host loglarını bağlayarak Filebeat'i tek komutla Docker üzerinden başlatın:

```bash
docker run -d --name filebeat-linux --net=host \
  --user=root \
  -v $(pwd)/filebeat-linux.yml:/usr/share/filebeat/filebeat.yml:ro \
  -v /var/log:/var/log:ro \
  docker.elastic.co/beats/filebeat:8.17.0 -e -strict.perms=false
```

Filebeat'in Logstash'e bağlandığını doğrulamak için loglarına bakın:

```bash
docker logs --tail=15 filebeat-linux
```

*Çıktıda `Connection to backoff(async(tcp://localhost:5044)) established` yazısını görüyorsanız bağlantı başarılıdır.*

---

### Adım 3: Test Güvenlik ve SSH Logu Üretin

Sistemde SSH oturum hatası ve test mesajları oluşturmak için hazırlanan scripti çalıştırın:

```bash
./scripts/generate-auth-traffic.sh
```

*Bu script, sisteme sahte bir kullanıcıyla bağlanmaya çalışarak `/var/log/auth.log` içine anında kayıt düşürür.*

---

## Doğal Doğrulama ve Beklenen Sonuç

### 1. Elasticsearch API ile Sorgulama

Toplanan logların Elasticsearch'e ulaştığını terminalden test edin:

```bash
curl -s -u elastic:BilginIT454 "http://localhost:9200/system-logs-*/_search?q=log_type:system_auth&pretty" | jq '{toplam_kayit: .hits.total.value, ornek_mesaj: .hits.hits[0]._source.message}'
```

* **Beklenen Sonuç:** `toplam_kayit` 0'dan büyük olmalı ve `ornek_mesaj` içinde `Failed password` ifadesi görünmelidir.

---

### 2. Kibana Discover Ekranında Arama

1. Tarayıcınızdan Kibana'yı açın:
   * **Adres:** `http://<SUNUCU_IP>:15601` (veya `https://studentXX-kibana.devopsatolyesi.com`)
   * **Giriş:** `elastic` / `BilginIT454`
2. Sol menüden **Analytics > Discover** seçeneğine tıklayın.
3. Sol üstteki Veri Görünümünden **`Linux Sistem Logs (Auth & Syslog)`** veya `system-logs-*` seçin.
4. Sağ üstteki zaman aralığını **Last 15 minutes** yapın.
5. Arama çubuğuna şunu yazıp Enter'a basın:
   ```text
   message : "Failed password"
   ```
6. Ekranda başarısız SSH denemesinin zamanı, sunucu adı ve mesajı listelenecektir.

---

## Temizlik

Yalnızca bu lab için başlattığınız geçici Filebeat konteynerini silin:

```bash
docker rm -f filebeat-linux
```

> [!WARNING]
> **Merkezi Omurga Hatırlatması:** `00-elk-core-stack` servislerini (`elasticsearch`, `logstash`, `kibana`) **kesinlikle kapatmayın**. Sonraki tüm laboratuvarlar bu omurga üzerinde çalışır.
