# LAB-ELK-02 — Uygulama Loglarının Yapısal Parse Edilmesi (Grok & JSON)

| Seviye | Profil / Araçlar | Açık Portlar |
|:---:|:---:|:---:|
| Orta | Docker Compose, Logstash, Grok, JSON Codec | 8081 (Nginx), 3001 (Node.js API), 15601 (Kibana), 5000 (Logstash TCP) |

[LAB-ELK-02.zip](LAB-ELK-02.zip)

## Amaç
* Nginx web sunucusu ve Node.js Express REST API servislerini Docker Compose ile devreye almak.
* Nginx'in düz metin (Combined Apache/Nginx formatı) erişim günlüklerini Logstash Grok filtresiyle yapısal JSON alanlarına (`client_ip`, `method`, `url`, `response_code`, `bytes`) ayrıştırmak.
* Node.js uygulamasının ürettiği yerel JSON günlüklerini Logstash JSON codec ile karşılamak ve veri tiplerini (`mutate convert integer`) optimize etmek.
* Ayrıştırılan uygulama verilerinin Elasticsearch üzerinde `app-logs-*` indeksine başarıyla yazıldığını REST API ile doğrulamak.
* Kibana Discover arayüzünde HTTP yanıt kodları ve mikroservis bazında KQL sorguları gerçekleştirmek.

---

## Ön Koşullar
* **Merkezi ELK Omurgası:** `00-elk-core-stack` servislerinin (`elasticsearch`, `logstash`, `kibana`) çalışır durumda olması gerekmektedir.
* 8081 (Nginx), 3001 (Node API) ve 5000 (Logstash TCP) portlarının erişilebilir olması.
* **Sonraki Lablarla Kritik İlişki:** Burada ayağa kaldırılan Nginx (`:8081`) web sunucusu, **`LAB-ELK-06` (SIEM ve Güvenlik Analizi)** aşamasında web saldırı simülasyonunun canlı hedefi olacaktır. Bu nedenle Modül 06 tamamlanana kadar servislerin açık bırakılması tavsiye edilir.

---

## Mimari ve Çalışma Modeli

```text
[ Nginx Web Sunucusu (:8081) ] ──(Düz Metin Loglar)──┐
                                                      ▼
                                           [ Logstash (:5000 TCP) ]
                                           - Grok: %{COMBINEDAPACHELOG}
                                           - JSON Codec & Mutate
                                                      │
                                                      ▼ (Basic Auth: elastic/BilginIT454)
[ Node.js Payment API (:3001) ] ──(JSON Log Akışı)───┴──► [ Elasticsearch (:9200) ]
                                                           - Index: app-logs-YYYY.MM.DD
                                                                  ▲
                                                                  │
                                                           [ Kibana UI (:15601) ]
                                                           - Data View: app-logs-*
```

---

## Adım Adım Uygulama Rehberi

### 1. Örnek Uygulamaları Başlatma

Uygulama dizinine geçin ve Nginx ile Node.js API servislerini arka planda başlatın:

```bash
cd ~/elk-lab/02-workspace-apps-logging/sample-apps
docker compose -f docker-compose.apps.yml up -d
docker compose -f docker-compose.apps.yml ps
```

* `demo-nginx` (Port 8081) ve `demo-api` (Port 3001) konteynerlerinin `Up` durumunda olduğunu doğrulayın.

---

### 2. Canlı Trafik ve Uygulama Logu Üretme

Uygulamalara hem başarılı HTTP istekleri (`200 OK`) hem de hata durumları (`500 Internal Server Error`, `404 Not Found`) gönderip Logstash boru hattına ileten test scriptini çalıştırın:

```bash
./generate-app-traffic.sh
```

Bu script:
* Nginx web sunucusuna dinamik yollar (`/products`, `/api/v1/orders`, `/catalog`, `/non-existent-page`) üzerinden 30 adet HTTP isteği gönderir.
* Node.js API servisinin `/api/pay` ve `/api/fail` uç noktalarını tetikleyerek ödeme ve veritabanı hata logları üretir.
* Üretilen yapılandırılmış logları Logstash'in 5000 numaralı TCP JSON portuna doğrudan iletir.

---

### 3. Logstash Ayrıştırma (Grok & JSON) Mantığı

Logstash gelen ham logları `app-pipeline.conf` kurallarıyla işler:
* **Grok Filtresi:** Düz metin halindeki `"192.168.1.45 - - [24/Sep/2026...] "GET /products HTTP/1.1" 200 1420"` satırını ayrıştırarak `client_ip`, `method`, `url`, `response_code` ve `bytes` alanlarını üretir.
* **Mutate Filtresi:** `response_code` ve `bytes` alanlarını metin (string) tipinden sayısal (integer) tipe dönüştürür. Bu sayede Kibana üzerinde `response_code >= 400` gibi sayısal filtreler ve toplamsal metrikler hesaplanabilir.

---

## Doğal Doğrulama ve Beklenen Sonuç

### 1. Elasticsearch API ile Ayrıştırılmış Logları Doğrulama

Toplanan logların Elasticsearch'e yapısal JSON olarak indekslendiğini terminalden sorgulayın:

```bash
curl -s -u elastic:BilginIT454 "http://localhost:9200/app-logs-*/_search?pretty" | jq '.hits.hits[0]._source | {service, client_ip, method, url, response_code, level}'
```

* **Beklenen Örnek Çıktı:**
```json
{
  "service": "nginx-web",
  "client_ip": "192.168.1.45",
  "method": "GET",
  "url": "/products",
  "response_code": 200,
  "level": null
}
```
*Grok ve JSON ayrıştırıcısının ham log metnini ayrı ayrı sorgulanabilir JSON alanlarına böldüğünü ve `response_code` alanının tamsayı olduğunu teyit edin.*

---

### 2. Kibana Discover Ekranında İnceleme

1. Tarayıcınızdan Kibana paneline bağlanın (`http://<SUNUCU_IP>:15601` veya `https://studentXX-kibana.devopsatolyesi.com`).
2. Sol menüden **Analytics > Discover** bölümüne geçin.
3. Veri Görünümü (Data View) olarak **`Application Logs (Nginx & API)`** veya kalıp olarak `app-logs-*` seçin.
4. KQL arama çubuğunda şu pratik sorguları deneyin:
   * **Ödeme API'sindeki 500 Hatalarını Filtreleme:**
     ```text
     service : "payment-api" and response_code >= 500
     ```
   * **Başarılı Nginx Web İstekleri:**
     ```text
     service : "nginx-web" and response_code : 200
     ```
   * **Bulunamayan (404) Sayfaları İnceleme:**
     ```text
     response_code : 404
     ```

---

## Temizlik

> **Önemli Bağımlılık Uyarısı:** Eğer `LAB-ELK-06` (SIEM ve Güvenlik Analizi) çalışmasını yapacaksanız, Nginx servisinin açık kalması gerekmektedir. Yalnızca bu modülü tek başına denediyseniz veya eğitim serisini tamamladıysanız uygulamaları durdurun:

```bash
cd ~/elk-lab/02-workspace-apps-logging/sample-apps
docker compose -f docker-compose.apps.yml down
```

*Merkezi ELK omurgası (`00-elk-core-stack`) sonraki adımlar için çalışmaya devam etmelidir.*
