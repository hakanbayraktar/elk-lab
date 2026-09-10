# LAB-ELK-06 — Elastic SIEM ve Güvenlik Olayları Analizi

| Seviye | Tahmini Süre | Profil / Araçlar | Açık Portlar |
| :--- | :--- | :--- | :--- |
| İleri (Advanced) | 35 Dakika | Elastic SIEM, Kibana Security, ECS, Netcat, cURL | 5601 (Kibana), 5000/5044 (Logstash) |

[LAB-ELK-06.zip](LAB-ELK-06.zip)

## Amaç

- Elastic Stack'in SIEM (Security Information and Event Management) yeteneklerini ve ECS (Elastic Common Schema) normalizasyonunu incelemek.
- Linux sistem loglarında SSH kaba kuvvet (brute-force) oturum açma denemelerini eşik (threshold) kuralları ile otomatik tespit etmek.
- Web sunucu erişim loglarında Path Traversal (`../../etc/passwd`), SQL Injection ve bilgi ifşası taramalarını tespit etmek.
- Simüle edilen siber saldırıları Kibana Discover ve KQL sorguları ile adli bilişim (forensics) bakış açısıyla analiz etmek.

## Ön Koşullar

- `00-elk-core-stack` ve `02-workspace-apps-logging` servislerinin ayakta olması.
- `curl`, `netcat` (`nc`) ve `jq` araçlarının terminalde kurulu olması.

## Mimari ve Çalışma Modeli

```text
[Saldırgan (Attacker)]
   │
   ├─► SSH Port Tarama & Brute-Force (Port 22 / auth.log)
   └─► Web Dizin Atlama & SQLi Denemeleri (Nginx Port 8081)
          │
          ▼
   [Filebeat / Logstash Ingestion]
          │ (ECS Normalizasyonu: source.ip, event.action, url.path)
          ▼
   [Elasticsearch Depolama & İndeksleme]
          │
          ▼
   [SIEM Algılama Motoru (Detection Rules)]
     ├── Kural 1: Eşik Kuralı (Aynı IP'den 1 dakikada >= 5 hatalı SSH parolası)
     └── Kural 2: Sorgu Kuralı (URL içinde '../' veya 'UNION SELECT' geçen 403/404 istekleri)
          │
          ▼
   [Kibana Security / Güvenlik Analisti Görünümü]
```

## Adım Adım Uygulama Rehberi

### Adım 1: Güvenlik Kurallarının Mantığı

`rules/` dizininde tanımlanan iki temel SIEM kuralını inceleyin:

1. **`rules/ssh-bruteforce-rule.json`**:
   - Belirli bir kaynak IP'den (`client_ip` veya `source.ip`) 5 dakika içinde 5 veya daha fazla `Failed password` olayı geldiğinde tetiklenir (MITRE ATT&CK T1110 - Brute Force).

2. **`rules/web-attack-detection.json`**:
   - URL parametrelerinde dizin geçişi (`../*`, `/etc/passwd`), veritabanı saldırı anahtar kelimeleri (`union select`) veya hassas dosya erişimleri (`.env`, `.git`) arar (OWASP Top 10 A01 / A03).

### Adım 2: Saldırı Simülasyonunun Çalıştırılması

Önceden hazırlanan saldırı simülasyon betiğini çalıştırın:

```bash
cd 06-siem-and-security-analytics
./scripts/simulate-attacks.sh
```

Bu betik:
- Logstash TCP portuna `198.51.100.77` IP adresinden 6 adet başarısız SSH oturum denemesi gönderir (`root`, `admin`, `deploy`, vb.).
- Nginx uygulamasına hassas dosya ve SQL injection sorguları gönderir (`/../../../../etc/passwd`, `/.env`, `UNION SELECT`).

### Adım 3: Kibana Üzerinde Olay Korelasyonu ve KQL Analizi

1. Tarayıcıdan `http://localhost:5601` adresine gidin.
2. **Analytics > Discover** bölümünü açın.

**SSH Brute Force Analizi İçin KQL Sorgusu:**
```kql
message : "Failed password" and client_ip : "198.51.100.77"
```
Sol menüden `client_ip`, `user`, `@timestamp` alanlarını sütun olarak ekleyin. Saldırganın sırayla hangi kullanıcı adlarını denediğini ve zaman aralıklarını inceleyin.

**Web Uygulama Saldırısı Analizi İçin KQL Sorgusu:**
```kql
url : *../* or url : */etc/passwd* or url : *UNION*
```
Gelen sonuçlarda `client_ip`, `method`, `url`, `response_code` alanlarını inceleyerek saldırganın dizin atlatma ve SQLi denemelerini doğrulayın.

### Adım 4: SIEM Tespit Pano Görselleştirmesi

Kibana Lens veya Dashboard üzerinde:
1. **Top Attacker IPs (En Çok Hata Alan IP'ler):**
   - X Ekseni: `client_ip` (Top 5 Terms)
   - Y Ekseni: `Count of records`
   - Filtre: `message : "Failed password"`
2. **Suspicious HTTP Requests (Şüpheli İstek Dağılımı):**
   - Tablo Görünümü: `url`, `response_code`, `@timestamp`

## Doğal Doğrulama ve Beklenen Sonuç

1. Elasticsearch REST API üzerinden SSH saldırganının olay sayısını doğrulayın:
   ```bash
   curl -s "http://localhost:9200/_search?q=client_ip:198.51.100.77" | jq '.hits.total.value'
   ```
   Çıktının en az `6` olduğunu teyit edin.

2. Web saldırı kayıtlarını Elasticsearch'ten çekin:
   ```bash
   curl -s "http://localhost:9200/app-logs-*/_search?q=url:*passwd*" | jq '.hits.hits[]._source | {time: ."@timestamp", ip: .client_ip, url: .url, status: .response_code}'
   ```
   Dizin atlatma denemesinin JSON olarak başarıyla indekslendiğini ve yanıt kodunun `404` veya `403` döndüğünü görün.

## Temizlik

Lab süresince üretilen güvenlik test loglarını indekslerden temizlemek isterseniz:

```bash
# Sadece test saldırgan IP'sine ait dokümanları silin:
curl -s -X POST "http://localhost:9200/*/_delete_by_query" \
  -H 'Content-Type: application/json' \
  -d '{"query":{"term":{"client_ip":"198.51.100.77"}}}'
```
