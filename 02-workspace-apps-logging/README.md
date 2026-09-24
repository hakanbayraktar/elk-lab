# LAB-ELK-02 — Uygulama Loglarının Yapısal Parse Edilmesi (Grok & JSON)

| Seviye | Profil / Araçlar | Açık Portlar |
|:---:|:---:|:---:|
| Orta | Docker Compose, Logstash, Grok, JSON Codec | 8081 (Nginx), 3001 (Node.js API), 15601 (Kibana), 5000 (Logstash TCP) |

[LAB-ELK-02.zip](LAB-ELK-02.zip)

> [!IMPORTANT]
> **DİKKAT: `00-elk-core-stack` AÇIK KALMALIDIR!**
> Bu laboratuvardaki işlemler merkezi ELK omurgasına bağlanır. `00-elk-core-stack` dizinindeki Elasticsearch, Logstash ve Kibana servislerini **kesinlikle durdurmayın veya silmeyin**.
> Ayrıca bu labda başlatacağınız Nginx (`:8081`) servisi, **`LAB-ELK-06` (SIEM)** laboratuvarında saldırı hedefi olarak kullanılacağı için eğitim süresince açık bırakılmalıdır.

---

## Amaç
* Nginx web sunucusu ve Node.js Express REST API servislerini Docker Compose ile başlatmak.
* Nginx'in düz metin erişim loglarını Logstash Grok filtresiyle JSON alanlarına (`client_ip`, `method`, `url`, `response_code`) ayırmak.
* Node.js API'nin ürettiği JSON loglarını Logstash JSON codec ile doğrudan işlemek.
* Toplanan verilerin Elasticsearch üzerinde `app-logs-*` indeksine yazıldığını doğrulamak.
* Kibana Discover üzerinde HTTP yanıt kodlarına göre KQL aramaları yapmak.

---

## Ön Koşullar
* **Merkezi ELK Omurgası:** `00-elk-core-stack` servislerinin (`elasticsearch`, `logstash`, `kibana`) çalışıyor olması gereklidir.
* Port Kontrolü: 8081 (Nginx), 3001 (Node API) ve 5000 (Logstash TCP) portlarının boşta ve erişilebilir olması.
* Giriş Bilgileri: Kullanıcı: `elastic` | Şifre: `BilginIT454` | Port: `15601`.

---

## Mimari ve Çalışma Modeli

```text
[ Nginx Web Sunucusu (:8081) ] ──(Düz Metin Log)───┐
                                                    ▼
                                         [ Logstash (:5000 TCP) ]
                                         - Grok: %{COMBINEDAPACHELOG}
                                         - JSON Codec & Mutate
                                                    │
                                                    ▼ (Basic Auth: elastic/BilginIT454)
[ Node.js Payment API (:3001) ] ──(JSON Logu)──────┴──► [ Elasticsearch (:9200) ]
                                                         - İndeks: app-logs-YYYY.MM.DD
                                                                ▲
                                                                │
                                                         [ Kibana UI (:15601) ]
                                                         - Data View: app-logs-*
```

---

## Adım Adım Uygulama Rehberi

### Adım 1: Lab Dizinine Geçin ve Uygulamaları Başlatın

Uygulama dizinine geçerek Nginx ve Node.js API konteynerlerini ayağa kaldırın:

```bash
cd ~/elk-lab/02-workspace-apps-logging/sample-apps
docker compose -f docker-compose.apps.yml up -d
docker compose -f docker-compose.apps.yml ps
```

*Her iki servisin de (`demo-nginx` ve `demo-api`) `Up` durumunda olduğunu teyit edin.*

---

### Adım 2: Canlı Web ve API Trafiği Üretin

Uygulamalara hem başarılı istekler (`200 OK`) hem de hatalar (`500 Error`, `404 Not Found`) gönderip logları Logstash'e aktaran test scriptini çalıştırın:

```bash
./generate-app-traffic.sh
```

*Bu script, Nginx'e 30 adet HTTP isteği atar, Node API'yi tetikler ve üretilen logları Logstash'in `:5000` portuna yollar.*

---

### Adım 3: Logstash'in Logları Nasıl Ayrıştırdığını İnceleyin

Logstash gelen düz metin satırını şu mantıkla işler:
* **Grok:** `"192.168.1.45 - - [Tarih] "GET /products HTTP/1.1" 200 1420"` satırını parçalar; `client_ip`, `method`, `url`, `response_code` ve `bytes` alanlarını üretir.
* **Mutate:** `response_code` alanını sayıya (integer) çevirir; böylece Kibana'da `response_code >= 400` şeklinde sayısal filtreler çalışır.

---

## Doğal Doğrulama ve Beklenen Sonuç

### 1. Elasticsearch API ile Ayrıştırılmış Logları Doğrulama

Toplanan logların yapısal JSON olarak kaydedildiğini terminalden kontrol edin:

```bash
curl -s -u elastic:BilginIT454 "http://localhost:9200/app-logs-*/_search?pretty" | jq '.hits.hits[0]._source | {service, client_ip, method, url, response_code}'
```

* **Beklenen Sonuç:** Düz metin yerine `client_ip`, `url`, `response_code` gibi alanların ayrı ayrı ayrıştığını görün.

---

### 2. Kibana Discover Ekranında Arama

1. Tarayıcınızdan Kibana'yı açın (`http://<SUNUCU_IP>:15601` veya `https://studentXX-kibana.devopsatolyesi.com`).
2. **Analytics > Discover** sekmesine gidin.
3. Veri Görünümünden **`Application Logs (Nginx & API)`** (`app-logs-*`) seçin.
4. KQL arama çubuğuna şu örnekleri yazıp test edin:
   * **Ödeme API'sindeki Hataları Filtreleme:**
     ```text
     service : "payment-api" and response_code >= 500
     ```
   * **Başarılı Nginx Web İstekleri:**
     ```text
     service : "nginx-web" and response_code : 200
     ```

---

## Temizlik

> [!WARNING]
> **Önemli Bağımlılık Uyarısı:** Eğer `LAB-ELK-06` (SIEM Güvenlik Analizi) modülünü yapacaksanız, Nginx servisinin açık kalması gereklidir. Yalnızca bu modülü bağımsız test ettiyseniz kapatın:

```bash
cd ~/elk-lab/02-workspace-apps-logging/sample-apps
docker compose -f docker-compose.apps.yml down
```

*Merkezi ELK omurgası (`00-elk-core-stack`) sonraki tüm lablar için çalışır durumda kalmalıdır.*
