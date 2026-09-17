# LAB-ELK-00 — Çekirdek Elastic Stack Kurulumu (Elasticsearch, Logstash, Kibana)

| Seviye | Tahmini Süre | Profil / Araçlar | Açık Portlar |
|:---:|:---:|:---:|:---:|
| Başlangıç | 25 Dakika | `docker compose`, `curl`, `jq` | 9200 (ES), 5601 (Kibana), 5044 (Beats), 5000 (TCP) |

---

## Mimari ve Çalışma Modeli

```text
[ Beats / İstemciler ] ──(Port 5044)──> [ Logstash (:5044/:5000) ]
                                                │
                                                ▼ (HTTP REST)
                                      [ Elasticsearch (:9200) ] <──(Web UI)── [ Kibana (:5601) ]
                                      - Tek Düğüm (Single-Node)
                                      - Heap: 1 GB (-Xms1g -Xmx1g)
```

---

## Adım Adım Uygulama Rehberi

### 1. Linux Çekirdek Bellek Parametresini Ayarlama

Elasticsearch mmap dosya sayıları için sistem parametresinin en az `262144` olmasını zorunlu kılar:

```bash
# Canlı sistemde parametreyi güncelleme
sudo sysctl -w vm.max_map_count=262144

# Kalıcı hale getirme
echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.d/99-elasticsearch.conf
```

### 2. Stack'i Ayağa Kaldırma

```bash
cd 00-elk-core-stack
docker compose up -d
```

### 3. Konteyner Durumlarını ve Sağlık Kontrollerini İzleme

```bash
docker compose ps
```

*Elasticsearch servisi `healthy` durumuna geçtikten sonra Logstash ve Kibana otomatik olarak devreye girer.*

---

## Doğal Doğrulama ve Beklenen Sonuç

### 1. Elasticsearch API Sağlık Kontrolü

```bash
curl -s http://localhost:9200/_cluster/health | jq .
```

* **Beklenen Çıktı:**
```json
{
  "cluster_name": "docker-cluster",
  "status": "green",
  "number_of_nodes": 1,
  "number_of_data_nodes": 1,
  "active_primary_shards": 0,
  "active_shards": 0
}
```

### 2. Kibana Web Arayüzünü Test Etme

```bash
curl -s -I http://localhost:5601/api/status | head -n 5
```

*Tarayıcınızdan `http://localhost:5601` adresine giderek Kibana ana ekranına erişin.*

### 3. Logstash TCP Portuna Örnek Log Gönderme

```bash
echo '{"message": "ELK Stack kurulum testi basarili!", "service": "healthcheck", "level": "INFO"}' | nc -N localhost 5000
```

10 saniye sonra Elasticsearch indeksini kontrol edin:
```bash
curl -s "http://localhost:9200/logstash-*/_search?pretty" | jq '.hits.hits[0]._source'
```

---

## 📌 Sürüm Notu: Elastic Stack 8.x ve Gelecek 9.0 Sürümü

* **Neden 8.17.x Kullanıyoruz?**
  Elastic NV tarafından henüz resmi olarak **Elasticsearch 9.0 sürümü yayınlanmamıştır** (GA / General Availability değildir). Şu an prodüksiyon ortamlarında kullanılan en kararlı, güncel ve LTS destekli ana sürüm serisi **Elasticsearch 8.17.x** serisidir.
* **"Deprecated in 8.15.0: Search Sessions are deprecated" Uyarısı Nedir?**
  Kibana konsolunda veya arayüzde görebileceğiniz bu uyarı bir hata değil; Elastic'in gelecekte çıkacak olan 9.0 majör sürümüne hazırlık amacıyla eskiyen bileşenleri (Search Sessions API) bildiren standart bir **kullanımdan kaldırma (deprecation)** uyarısıdır.

---

## 🛠️ Manuel Yönetim ve Eğitmen / Öğrenci Kılavuzu

Bu bölümde öğrencilere sınıfta canlı gösterilebilecek temel ELK yönetim komutları ve adımları yer almaktadır.

### 1. Elasticsearch Küme Sağlığı ve Shard Analizi

Kümenin anlık durumunu incelemek için REST API uç noktaları kullanılır:

* **Genel Küme Sağlığı (`_cluster/health`):**
  ```bash
  curl -s http://localhost:9200/_cluster/health?pretty
  ```
  * **`green`:** Tüm birincil (primary) ve yedek (replica) shard'lar tahsis edilmiş ve sağlıklıdır.
  * **`yellow`:** Tüm birincil shard'lar aktiftir fakat en az bir replica shard tahsis edilememiştir. *(Tek düğümlü/single-node geliştirme ortamlarında bu durum tamamen normaldir; çünkü replica aynı düğüme yazılamaz).*
  * **`red`:** En az bir birincil shard eksiktir veya erişilemez durumdadır; veri kaybı riski vardır.

* **Shard Durumlarının Dökümü (`_cat/shards`):**
  ```bash
  curl -s "http://localhost:9200/_cat/shards?v"
  ```
  Hangi indeksin hangi düğümde kaç shard ile tutulduğunu (`PRI/REP`, `STARTED`, `UNASSIGNED`) gösterir.

* **Düğüm (Node) Kaynak Kullanımı (`_cat/nodes`):**
  ```bash
  curl -s "http://localhost:9200/_cat/nodes?v&h=ip,name,heap.percent,ram.percent,cpu,load_1m,node.role"
  ```

---

### 2. İndeks Yaşam Döngüsü: Oluşturma, Listeleme, Mapping ve Silme

* **Tüm İndeksleri Boyut ve Doküman Sayısıyla Görme (`_cat/indices`):**
  ```bash
  curl -s "http://localhost:9200/_cat/indices/*?v&s=docs.count:desc"
  ```

* **Manuel Olarak Yeni Bir İndeks ve Mapping Tanımlama (PUT):**
  ```bash
  curl -s -X PUT "http://localhost:9200/egitim-uygulamasi" -H "Content-Type: application/json" -d '{
    "settings": {
      "number_of_shards": 1,
      "number_of_replicas": 0
    },
    "mappings": {
      "properties": {
        "@timestamp": { "type": "date" },
        "service":    { "type": "keyword" },
        "status":     { "type": "integer" },
        "message":    { "type": "text", "fields": { "keyword": { "type": "keyword" } } }
      }
    }
  }'
  ```

* **İndekse Manuel Doküman Ekleme (POST):**
  ```bash
  curl -s -X POST "http://localhost:9200/egitim-uygulamasi/_doc" -H "Content-Type: application/json" -d '{
    "@timestamp": "2026-09-11T04:00:00.000Z",
    "service": "odeme-servisi",
    "status": 200,
    "message": "Islem basariyla tamamlandi"
  }'
  ```

* **İndeksten Arama Yapma (`_search`):**
  ```bash
  curl -s "http://localhost:9200/egitim-uygulamasi/_search?pretty" -H "Content-Type: application/json" -d '{
    "query": {
      "match": { "service": "odeme-servisi" }
    }
  }'
  ```

* **İndeksi Silme (DELETE):**
  ```bash
  curl -s -X DELETE "http://localhost:9200/egitim-uygulamasi"
  ```

---

### 3. ELK Güvenliği: Kullanıcı Adı, Şifre ve Yetkilendirme (Security)

Prodüksiyon ortamında Elasticsearch ve Kibana'ya kullanıcı adı ve parola tanımlamak için iki ana yaklaşım uygulanır:

#### Yöntem 1: Dahili Elastic X-Pack Güvenliği (Native Security)

1. **`docker-compose.yml` Dosyasında Güvenliği Aktif Etme:**
   ```yaml
   environment:
     - xpack.security.enabled=true
     - xpack.security.enrollment.enabled=true
   ```

2. **Varsayılan Kullanıcı Şifrelerini Belirleme:**
   Konteyner çalışırken terminalden şifre belirleme komutu çalıştırılır:
   ```bash
   # Otomatik rastgele şifre üretmek için:
   docker exec -it elasticsearch /usr/share/elasticsearch/bin/elasticsearch-setup-passwords auto

   # Veya 'elastic' süper kullanıcısının şifresini elle belirlemek için:
   docker exec -it elasticsearch /usr/share/elasticsearch/bin/elasticsearch-reset-password -u elastic -i
   ```

3. **Kibana ve Logstash Konfigürasyonuna Şifre Tanımlama:**
   * **Kibana (`kibana.yml`):**
     ```yaml
     elasticsearch.username: "kibana_system"
     elasticsearch.password: "BelirlenenSifre"
     ```
   * **Logstash (`logstash.conf`):**
     ```ruby
     output {
       elasticsearch {
         hosts => ["elasticsearch:9200"]
         user => "elastic"
         password => "BelirlenenSifre"
       }
     }
     ```

4. **Kibana UI Üzerinden Yeni Kullanıcı ve Rol Tanımlama:**
   * Tarayıcıdan `http://localhost:5601` > **Stack Management > Security > Users** bölümüne gidin.
   * **Create user** butonuna tıklayarak stajyer/öğrenci kullanıcısı (`devops_read_only`) oluşturun ve sadece `kibana_user` ile `read` yetkisi verin.

---

#### Yöntem 2: DevOps Standardı — Nginx Reverse Proxy ile HTTP Basic Auth (Dış Erişim Koruması)

Gerçek dünya DevOps altyapılarında Kibana ve Elasticsearch API'si sıklıkla bir **Ters Proxy (Nginx / Traefik / Ingress)** arkasında korunur.

* **Neden Bu Yöntem Tercih Edilir?**
  * **Sıfır Kesinti:** Dahili çalışan Logstash, Filebeat veya Fluent-Bit ajanlarının konfigürasyonunu bozmadan ve konteynerleri yeniden başlatmadan anında şifre koruması sağlar.
  * **Hafif ve Güvenli:** Dahili Docker ağında (`novashop-network`) servisler yerel IP/port üzerinden kimlik doğrulama yükü olmadan ultra hızlı log basarken; internetten Kibana veya Elasticsearch'e erişmeye çalışan tarayıcılar Nginx katmanında HTTP Basic Auth ile karşılanır.

**Adım Adım Kurulum:**

1. **Parola Dosyası Oluşturma:**
   ```bash
   sudo apt-get update && sudo apt-get install -y apache2-utils
   sudo htpasswd -cb /etc/nginx/.htpasswd-observability admin BilgincIT454
   sudo chmod 640 /etc/nginx/.htpasswd-observability
   sudo chown root:www-data /etc/nginx/.htpasswd-observability
   ```

2. **Nginx Sanal Sunucu Bloklarına Korumayı Ekleme:**
   `/etc/nginx/sites-available/student-tools.conf` içinde Kibana ve Elastic blokları:
   ```nginx
   # KIBANA (Port 5601)
   server {
       listen 443 ssl http2;
       server_name student101-kibana.devopsatolyesi.com;
       ssl_certificate /etc/letsencrypt/live/devopsatolyesi.com/fullchain.pem;
       ssl_certificate_key /etc/letsencrypt/live/devopsatolyesi.com/privkey.pem;

       location / {
           auth_basic "DevOps Atolyesi - Guvenli Erisim";
           auth_basic_user_file /etc/nginx/.htpasswd-observability;

           proxy_pass http://127.0.0.1:5601;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }

   # ELASTICSEARCH API (Port 9200)
   server {
       listen 443 ssl http2;
       server_name student101-elastic.devopsatolyesi.com;
       ssl_certificate /etc/letsencrypt/live/devopsatolyesi.com/fullchain.pem;
       ssl_certificate_key /etc/letsencrypt/live/devopsatolyesi.com/privkey.pem;

       location / {
           auth_basic "DevOps Atolyesi - Guvenli Erisim";
           auth_basic_user_file /etc/nginx/.htpasswd-observability;

           proxy_pass http://127.0.0.1:9200;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```

3. **Nginx'i Test Edip Yeniden Yükleme:**
   ```bash
   sudo nginx -t
   sudo systemctl reload nginx
   ```

4. **Doğrulama (CURL ile Test):**
   ```bash
   # Şifresiz -> 401 Unauthorized
   curl -s -o /dev/null -w "%{http_code}\n" -k https://student101-kibana.devopsatolyesi.com
   # Beklenen Çıktı: 401

   # Şifreli -> 200 OK
   curl -s -o /dev/null -w "%{http_code}\n" -k -u admin:BilgincIT454 https://student101-kibana.devopsatolyesi.com/api/status
   # Beklenen Çıktı: 200
   ```

---

### 4. Logstash Pipeline Mimarisi ve Ayarları

Logstash üç temel bloktan (`input`, `filter`, `output`) oluşur:

```ruby
# /usr/share/logstash/pipeline/logstash.conf

input {
  # Beats istemcilerinden gelen loglar (Port 5044)
  beats {
    port => 5044
  }
  # Doğrudan TCP/JSON üzerinden gelen loglar (Port 5000)
  tcp {
    port => 5000
    codec => json_lines
  }
}

filter {
  # 1. Nginx erişim logunu Grok ile ayrıştırma
  if [log_type] == "nginx_access" {
    grok {
      match => { "message" => "%{COMBINEDAPACHELOG}" }
    }
    date {
      match => [ "timestamp", "dd/MMM/yyyy:HH:mm:ss Z" ]
      target => "@timestamp"
    }
    mutate {
      convert => { "response" => "integer" }
      convert => { "bytes" => "integer" }
    }
  }

  # 2. IP adresinden coğrafi konum çıkarma
  if [clientip] {
    geoip {
      source => "clientip"
    }
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "%{[@metadata][target_index]}-%{+YYYY.MM.dd}"
  }
}
```

---

### 5. Veri Import Etme (İçe Aktarma) Yöntemleri

1. **Toplu Veri Aktarımı (Bulk API):**
   NDJSON formatındaki dosyayı tek komutla aktarın:
   ```bash
   curl -s -X POST "http://localhost:9200/_bulk" \
     -H "Content-Type: application/x-ndjson" \
     --data-binary @veriler.ndjson
   ```
2. **Kibana UI Üzerinden CSV/Log Yükleme:**
   * Sol menüden **Machine Learning > Data Visualizer > Upload file** seçeneğine gidin.
   * Elinizdeki CSV veya Apache/Nginx log dosyasını sürükleyin. Kibana otomatik olarak mapping ve format çıkaracaktır.
3. **Netcat ile Canlı Log Basma:**
   ```bash
   echo '{"service":"api","response_code":500,"url":"/fail"}' | nc -N localhost 5000
   ```

---

## Temizlik

Laboratuvarı sıfırlamak veya kaynakları serbest bırakmak istediğinizde:

```bash
docker compose down -v
```

