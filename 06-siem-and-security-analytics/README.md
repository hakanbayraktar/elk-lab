# LAB-ELK-06 — Elastic SIEM ve Güvenlik Olayları Analizi

| Seviye | Profil / Araçlar | Açık Portlar |
|:---:|:---:|:---:|
| İleri | Elastic SIEM, Kibana Security, ECS, Netcat, cURL | 9200 (ES), 15601 (Kibana), 5000 (Logstash), 8081 (Nginx) |

[LAB-ELK-06.zip](LAB-ELK-06.zip)

## Amaç
* Elastic Stack'in SIEM (Security Information and Event Management) yeteneklerini ve ECS (Elastic Common Schema) veri uyumunu uygulamalı olarak incelemek.
* Linux sistem loglarında SSH kaba kuvvet (brute-force) oturum açma girişimlerini eşik (threshold) kurallarıyla otomatik tespit etmek (MITRE ATT&CK T1110).
* Web sunucusu erişim günlüklerinde Dizin Atlama (Path Traversal `../../etc/passwd`), SQL Injection ve hassas dosya ifşası taramalarını yakalamak (OWASP Top 10).
* Gerçekleştirilen saldırı simülasyonunu Kibana Discover ve KQL sorguları üzerinden adli bilişim (forensics) bakış açısıyla analiz etmek.

---

## Ön Koşullar
* **Merkezi ELK Omurgası:** `00-elk-core-stack` servislerinin (`elasticsearch`, `logstash`, `kibana`) çalışıyor olması gerekmektedir.
* **Canlı Hedef Web Servisi:** `02-workspace-apps-logging` altındaki Nginx web sunucusunun (`:8081`) ayakta olması gerekmektedir.
* Kimlik Doğrulama: Kullanıcı: `elastic` | Şifre: `BilginIT454`.

Eğer servisler çalışmıyorsa başlatın:

```bash
# 1. ELK Omurgasını Kontrol Edin
cd ~/elk-lab/00-elk-core-stack && docker compose up -d

# 2. Hedef Web Servisini Başlatın
cd ~/elk-lab/02-workspace-apps-logging/sample-apps && docker compose -f docker-compose.apps.yml up -d
```

---

## Mimari ve Çalışma Modeli

```text
[ Saldırgan (IP: 198.51.100.77) ]
   │
   ├─► 1. SSH Brute-Force Denemeleri (root, admin, deploy) ──► [ Logstash :5000 TCP ]
   │                                                                    │
   └─► 2. Web Dizin Atlama & SQLi İstekleri ──► [ Nginx :8081 ] ────────┤
                                                                        ▼
                                                         [ Elasticsearch (:9200) ]
                                                         ├── system-logs-* (SSH)
                                                         └── app-logs-* (Web)
                                                                        │
                                                         ┌──────────────┴──────────────┐
                                                         ▼                             ▼
                                               [ SIEM Tespit Kuralları ]       [ Kibana UI (:15601) ]
                                               - SSH Eşiği (>= 5 hata)         - Discover KQL
                                               - Web Deseni (*../*, *UNION*)   - Security Dashboard
```

---

## Adım Adım Uygulama Rehberi

### 1. Güvenlik Kurallarının Mantığını İnceleme

`rules/` dizini altındaki iki temel SIEM kuralını inceleyin:

```bash
cd ~/elk-lab/06-siem-and-security-analytics
cat rules/ssh-bruteforce-rule.json
cat rules/web-attack-detection.json
```

* **SSH Kaba Kuvvet Kuralı:** Tek bir kaynak IP adresinden (`client_ip`) 5 dakika içinde 5 veya daha fazla `Failed password` kaydı geldiğinde alarm üretir.
* **Web Saldırı Tespiti Kuralı:** URL içinde `../*`, `/etc/passwd`, `union select` gibi şüpheli parametreleri tarar.

---

### 2. Siber Saldırı Simülasyonunu Çalıştırma

Önceden hazırlanan saldırı simülasyon betiğini çalıştırın:

```bash
./scripts/simulate-attacks.sh
```

Bu betik:
* `198.51.100.77` IP adresinden sırayla `root`, `admin`, `ubuntu`, `deploy`, `test` ve `oracle` kullanıcıları için başarısız SSH oturum denemeleri basar.
* Canlı Nginx web sunucusuna (`http://localhost:8081`) dizin atlatma (`/../../../../etc/passwd`), gizli dosya (`/.env`, `/.git/config`) ve SQL Injection istekleri gönderir.

---

### 3. Kibana Üzerinde Tehdit Avcılığı (Threat Hunting)

1. Tarayıcınızdan Kibana'ya bağlanın (`http://<SUNUCU_IP>:15601` veya `https://studentXX-kibana.devopsatolyesi.com`).
2. **Analytics > Discover** ekranını açın ve zaman aralığını **Last 15 minutes** yapın.

* **SSH Kaba Kuvvet Analizi (KQL):**
  * Data View: `system-logs-*`
  ```text
  message : "Failed password" and client_ip : "198.51.100.77"
  ```
  *Sol menüden `client_ip`, `user` ve `@timestamp` alanlarını ekleyerek saldırganın hangi hesapları denediğini kronolojik olarak görün.*

* **Web Uygulama Saldırısı Analizi (KQL):**
  * Data View: `app-logs-*`
  ```text
  url : *../* or url : */etc/passwd* or url : *UNION*
  ```
  *Gelen kayıtlarda `method`, `url` ve `response_code` alanlarını inceleyin. Web sunucusunun `404` yanıtı verdiğini doğrulayın.*

* **Saldırganın Tüm İzlerini Tek Ekranda Birleştirme:**
  ```text
  client_ip : "198.51.100.77"
  ```

---

## Doğal Doğrulama ve Beklenen Sonuç

### 1. Elasticsearch API ile Olay Sayımı

Saldırgan IP adresine ait toplam olay sayısını REST API ile sorgulayın:

```bash
curl -s -u elastic:BilginIT454 "http://localhost:9200/_search?q=client_ip:198.51.100.77&pretty" | jq '.hits.total.value'
```

* **Beklenen Sonuç:** Değer en az `13` olmalıdır (6 adet SSH brute-force + 7 adet web saldırı kaydı).

---

### 2. Saldırı Detaylarını Terminalde İnceleme

SSH saldırı kayıtlarının dökümünü alın:

```bash
curl -s -u elastic:BilginIT454 "http://localhost:9200/system-logs-*/_search?q=client_ip:198.51.100.77&pretty" | jq '.hits.hits[]._source | {user: .user, ip: .client_ip, message: .message}'
```

---

## Temizlik

Test saldırgan IP adresine (`198.51.100.77`) ait kayıtları indekslerden güvenle temizlemek isterseniz:

```bash
curl -s -u elastic:BilginIT454 -X POST "http://localhost:9200/*/_delete_by_query" \
  -H 'Content-Type: application/json' \
  -d '{"query":{"term":{"client_ip":"198.51.100.77"}}}' | jq '{deleted: .deleted}'
```

> **Önemli Not:** Merkezi ELK omurgası (`00-elk-core-stack`), son laboratuvar olan Prodüksiyon İpuçları ve Sorun Giderme için çalışır kalmalıdır.
