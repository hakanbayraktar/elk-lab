# LAB-ELK-06 — Elastic SIEM ve Güvenlik Olayları Analizi

| Seviye | Profil / Araçlar | Açık Portlar |
| :--- | :--- | :--- |
| İleri (Advanced) | Elastic SIEM, Kibana Security, ECS, Netcat, cURL | 15601 / 5601 (Kibana), 5000/5044 (Logstash), 8081 (Nginx) |

---

## Amaç

- Elastic Stack'in SIEM (Security Information and Event Management) yeteneklerini ve ECS (Elastic Common Schema) normalizasyonunu incelemek.
- Linux sistem loglarında SSH kaba kuvvet (brute-force) oturum açma denemelerini eşik (threshold) kuralları ile otomatik tespit etmek (MITRE ATT&CK T1110).
- Web sunucu erişim loglarında Path Traversal (`../../etc/passwd`), SQL Injection ve bilgi ifşası taramalarını tespit etmek (OWASP Top 10).
- Simüle edilen siber saldırıları Kibana Discover ve KQL sorguları ile adli bilişim (forensics) bakış açısıyla analiz etmek.

---

## Ön Koşullar ve Bağlı Olduğu Laboratuvarlar

Bu laboratuvar ortamda daha önce ayağa kaldırılmış olan şu iki modülü kullanır:

1. **`00-elk-core-stack` (Zorunlu — Ana Omurga):**
   - Elasticsearch (`:9200`), Logstash (`:5000` TCP / `:5044` Beats), Kibana (`:15601 / :5601`).
2. **`02-workspace-apps-logging` (Zorunlu — Hedef Web Servisi):**
   - Nginx Web Sunucusu (`:8081`) saldırı simülasyonundaki HTTP isteklerinin canlı hedefidir.

Servisler henüz çalışmıyorsa başlatın:

```bash
# 1. ELK Omurgasını Başlatın
cd ../00-elk-core-stack && docker compose up -d

# 2. Hedef Web Uygulamasını Başlatın
cd ../02-workspace-apps-logging/sample-apps && docker compose -f docker-compose.apps.yml up -d
```

## Mimari ve Çalışma Modeli

```text
[Saldırgan (Attacker IP: 198.51.100.77)]
   │
   ├─► 1. SSH Brute-Force Denemeleri (root, admin, deploy...) ──► [Logstash :5000 TCP]
   │                                                                     │
   └─► 2. Web Dizin Atlama & SQLi İstekleri ──► [Nginx :8081] ───────────┤
                                                                         ▼
                                                          [Elasticsearch Depolama]
                                                          ├── system-logs-* (SSH)
                                                          └── app-logs-* (Web)
                                                                         │
                                                          ┌──────────────┴──────────────┐
                                                          ▼                             ▼
                                                [SIEM Tespit Kuralları]         [Kibana UI :5601]
                                                - SSH Threshold (>= 5 hata)     - Discover KQL
                                                - Web Pattern (*../*, *union*)  - Security Dashboard
```

## Adım Adım Uygulama Rehberi

### Adım 1: Güvenlik Kurallarının Mantığı

`rules/` dizininde tanımlanan iki temel SIEM kuralını inceleyin:

1. **`rules/ssh-bruteforce-rule.json`**:
   - Belirli bir kaynak IP'den (`client_ip`) 5 dakika içinde 5 veya daha fazla `Failed password` olayı geldiğinde tetiklenir (MITRE ATT&CK T1110 - Brute Force).

2. **`rules/web-attack-detection.json`**:
   - URL parametrelerinde dizin geçişi (`../*`, `/etc/passwd`), veritabanı saldırı anahtar kelimeleri (`union select`) veya hassas dosya erişimleri (`.env`, `.git`) arar (OWASP Top 10 A01 / A03).

### Adım 2: Saldırı Simülasyonunun Çalıştırılması

Önceden hazırlanan saldırı simülasyon betiğini çalıştırın:

```bash
cd 06-siem-and-security-analytics
./scripts/simulate-attacks.sh
```

Bu betik:
- Logstash TCP portuna `198.51.100.77` IP adresinden 6 adet başarısız SSH oturum denemesi gönderir (`root`, `admin`, `ubuntu`, `deploy`, `test`, `oracle`).
- Nginx uygulamasına (`http://localhost:8081`) hassas dosya ve SQL injection sorguları göndererek erişim kayıtlarını oluşturur.

### Adım 3: Kibana Üzerinde Olay Korelasyonu ve KQL Analizi

1. Tarayıcıdan `http://localhost:5601` adresine gidin.
2. **Analytics > Discover** bölümünü açın.

**SSH Brute Force Analizi İçin KQL Sorgusu:**
```kql
message : "Failed password" and client_ip : "198.51.100.77"
```
Veri görünümü olarak `system-logs-*` seçin. Sol menüden `client_ip`, `user`, `@timestamp` alanlarını sütun olarak ekleyin. Saldırganın sırayla hangi kullanıcı adlarını denediğini ve zaman aralıklarını inceleyin.

**Web Uygulama Saldırısı Analizi İçin KQL Sorgusu:**
```kql
url : *../* or url : */etc/passwd* or url : *UNION*
```
Veri görünümü olarak `app-logs-*` seçin. Gelen sonuçlarda `client_ip`, `method`, `url`, `response_code` alanlarını inceleyerek saldırganın dizin atlatma ve SQLi denemelerini doğrulayın.

**Tüm Saldırıyı Tek Ekranda Görme (Korelasyon):**
```kql
client_ip : "198.51.100.77"
```
Bu sorguyla saldırganın önce web sunucusunu taradığını, ardından SSH portuna brute-force uyguladığını tek bir zaman çizelgesinde (timeline) korele edin.

## Doğal Doğrulama ve Beklenen Sonuç

### 1. Elasticsearch REST API üzerinden Olay Sayımı

Terminalden saldırgan IP'sine ait tüm kayıtları sorgulayın:

```bash
curl -s "http://localhost:9200/_search?q=client_ip:198.51.100.77" | jq '.hits.total.value'
```
* **Beklenen Sonuç:** En az `13` (6 SSH brute-force + 7 web attack kaydı).

### 2. SSH Brute Force Saldırgan Analizi

```bash
curl -s "http://localhost:9200/system-logs-*/_search?pretty" | jq '.hits.hits[]._source | {time: ."@timestamp", user: .user, ip: .client_ip, msg: .message}'
```
* **Beklenen Sonuç:**
```json
{
  "time": "2026-09-10T21:58:14.000Z",
  "user": "root",
  "ip": "198.51.100.77",
  "msg": "Failed password for invalid user root from 198.51.100.77 port 49822 ssh2"
}
```

### 3. Web Dizin Atlama & SQLi Analizi

```bash
curl -s "http://localhost:9200/app-logs-*/_search?pretty" | jq '.hits.hits[]._source | {time: ."@timestamp", ip: .client_ip, method: .method, url: .url, status: .response_code}'
```
* **Beklenen Sonuç:**
```json
{
  "time": "2026-09-10T21:58:22.000Z",
  "ip": "198.51.100.77",
  "method": "GET",
  "url": "/../../../../etc/passwd",
  "status": 404
}
```

## Temizlik

Test saldırgan IP'sine ait logları indekslerden temizlemek isterseniz:

```bash
curl -s -X POST "http://localhost:9200/*/_delete_by_query" \
  -H 'Content-Type: application/json' \
  -d '{"query":{"term":{"client_ip":"198.51.100.77"}}}'
```
