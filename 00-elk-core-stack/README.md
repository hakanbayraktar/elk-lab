# LAB-ELK-00 — Çekirdek Elastic Stack Kurulumu (Elasticsearch, Logstash, Kibana)

| Seviye | Profil / Araçlar | Açık Portlar |
|:---:|:---:|:---:|
| Başlangıç | `docker compose`, `curl`, `jq`, `.env` | 9200 (ES), 15601 (Kibana Host Portu) / 5601, 5044 (Beats), 5000 (TCP) |

> **DİKKAT — Merkezi Omurga Bağımlılığı (Bu Stack'i Silmeyin):**
> Bu laboratuvarda kurulan Elasticsearch, Logstash ve Kibana yığını, sonraki tüm modüllerin (`01` - `07`) bağlandığı merkezi omurgadır. 07. modül tamamlanana kadar bu konteynerları **durdurmayın veya silmeyin**.

---

## Mimari ve Çalışma Modeli

```text
[ Beats / Filebeat / İstemciler ] ──(Port 5044)──> [ Logstash (:5044 / :5000) ]
                                                            │
                                                (HTTP Basic Auth: elastic/BilginIT454)
                                                            │
                                                            ▼
                                                [ Elasticsearch (:9200) ]
                                                - Tek Düğüm (Single-Node)
                                                - X-Pack Security: AKTİF (Native Realm)
                                                - Heap: 1 GB (-Xms1g -Xmx1g)
                                                            ▲
                                                            │ (Internal Docker: :9200)
                                                [ Kibana (:15601 -> :5601) ]
                                                - Web UI Portu: 15601
                                                - Kimlik Doğrulama: elastic / BilginIT454
```

---

## Adım Adım Uygulama Rehberi

### 1. Linux Çekirdek Bellek Parametresini Ayarlama

Elasticsearch mmap dosya sayıları için Linux çekirdek parametresinin (`vm.max_map_count`) en az `262144` olmasını zorunlu kılar:

```bash
# Canlı sistemde parametreyi güncelleme
sudo sysctl -w vm.max_map_count=262144

# Sunucu yeniden başlasa da kalıcı olması için:
echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.d/99-elasticsearch.conf
```

---

### 2. Çevre Değişkenleri (`.env`) Dosyasını Yapılandırma

Tüm güvenlik kimlik bilgileri, bellek boyutları ve Kibana host portu `00-elk-core-stack/.env` dosyası üzerinden yönetilir:

```bash
cd 00-elk-core-stack

# .env dosyasını inceleyin veya oluşturun:
cat <<'EOF' > .env
# ==============================================================================
# DevOps Practitioner Labs - ELK 8.x Stack Environment Configuration
# ==============================================================================
ELASTIC_USERNAME=elastic
ELASTIC_PASSWORD=BilginIT454

# Kibana Port Mapping (Host: 15601 -> Container: 5601)
KIBANA_PORT=15601

# JVM Memory Allocation
ES_JAVA_OPTS=-Xms1g -Xmx1g
LS_JAVA_OPTS=-Xms512m -Xmx512m
EOF
```

---

### 3. Stack'i Ayağa Kaldırma

Docker Compose dosyasını başlatın. Güvenlik özellikleri `.env` dosyasındaki değerlerle otomatik devreye girecektir:

```bash
docker compose up -d
```

---

### 4. Konteyner Durumlarını ve Sağlık Kontrollerini İzleme

```bash
docker compose ps
```

* **Beklenen Durum:**
  * `elasticsearch` servisi `healthy` durumuna geçtikten sonra `logstash` ve `kibana` servisleri otomatik olarak başlar.
  * Kibana host üzerindeki `15601` ve `5601` portlarına yönlendirilir.

---

## Doğal Doğrulama ve Beklenen Sonuç

### 1. Elasticsearch API Sağlık ve Güvenlik Kontrolü

Güvenliğin aktif olduğunu ve kimlik doğrulamanın çalıştığını teyit edin:

* **A) Şifresiz İstek Denemesi (Güvenlik Kanıtı):**
  ```bash
  curl -s -o /dev/null -w "%{http_code}\n" http://localhost:9200/
  ```
  * **Beklenen Çıktı:** `401` *(Yetkisiz erişim engellendi)*

* **B) Tanımlanan Şifre ile Sağlık Kontrolü:**
  ```bash
  curl -s -u elastic:BilginIT454 http://localhost:9200/_cluster/health | jq .
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

---

### 2. Kibana Web Arayüzünü Test Etme ve Giriş Yapma

Kibana servisi host makinenin **`15601`** portunda yayın yapmaktadır:

* **Terminalden API Sağlık Testi:**
  ```bash
  curl -s -u elastic:BilginIT454 -I http://localhost:15601/api/status | head -n 5
  ```
  * **Beklenen Çıktı:** `HTTP/1.1 200 OK`

* **Tarayıcıdan Giriş:**
  * **URL:** `http://<SUNUCU_IP>:15601` *(veya yerel test için `http://localhost:15601`)*
  * **Kullanıcı Adı:** `elastic`
  * **Şifre:** `BilginIT454`
  * Giriş yaptıktan sonra Kibana ana ekranı açılacaktır.

---

### 3. Logstash TCP Portuna Örnek Log Gönderme ve Doğrulama

Logstash'e port 5000 üzerinden JSON formatında canlı log gönderin:

```bash
echo '{"message": "ELK Stack guvenlikli kurulum testi basarili!", "service": "healthcheck", "level": "INFO"}' | nc -N localhost 5000
```

Yaklaşık 5-10 saniye sonra Elasticsearch indeksine yazıldığını sorgulayın:

```bash
curl -s -u elastic:BilginIT454 "http://localhost:9200/logstash-*/_search?pretty" | jq '.hits.hits[0]._source'
```

* **Beklenen Çıktı:**
```json
{
  "message": "ELK Stack guvenlikli kurulum testi basarili!",
  "service": "healthcheck",
  "level": "INFO",
  "@timestamp": "2026-09-24T...",
  "@version": "1"
}
```

---

## Manuel Yönetim ve Eğitmen / Öğrenci Kılavuzu

### 1. Elasticsearch Küme Sağlığı ve Shard Analizi

* **Genel Küme Sağlığı (`_cluster/health`):**
  ```bash
  curl -s -u elastic:BilginIT454 http://localhost:9200/_cluster/health?pretty
  ```

* **Shard Durumlarının Dökümü (`_cat/shards`):**
  ```bash
  curl -s -u elastic:BilginIT454 "http://localhost:9200/_cat/shards?v"
  ```

* **Düğüm (Node) Kaynak Kullanımı (`_cat/nodes`):**
  ```bash
  curl -s -u elastic:BilginIT454 "http://localhost:9200/_cat/nodes?v&h=ip,name,heap.percent,ram.percent,cpu,load_1m,node.role"
  ```

---

### 2. İndeks Yaşam Döngüsü: Oluşturma, Doküman Ekleme ve Arama

* **Tüm İndeksleri Listeleme:**
  ```bash
  curl -s -u elastic:BilginIT454 "http://localhost:9200/_cat/indices/*?v&s=docs.count:desc"
  ```

* **Manuel İndeks Oluşturma (PUT):**
  ```bash
  curl -s -u elastic:BilginIT454 -X PUT "http://localhost:9200/egitim-uygulamasi" -H "Content-Type: application/json" -d '{
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

* **İndekse Doküman Ekleme (POST):**
  ```bash
  curl -s -u elastic:BilginIT454 -X POST "http://localhost:9200/egitim-uygulamasi/_doc" -H "Content-Type: application/json" -d '{
    "@timestamp": "2026-09-24T12:00:00.000Z",
    "service": "odeme-servisi",
    "status": 200,
    "message": "Islem basariyla tamamlandi"
  }'
  ```

* **İndeksten Arama Yapma (`_search`):**
  ```bash
  curl -s -u elastic:BilginIT454 "http://localhost:9200/egitim-uygulamasi/_search?pretty"
  ```

---

### 3. ELK Güvenliği, Parola Yönetimi ve Sorun Giderme

#### A) Parola Sıfırlama veya Manuel Şifre Değiştirme
Güvenlik devredeyken `elastic` kullanıcısının şifresini terminalden değiştirmek için:

```bash
docker exec -it elasticsearch /usr/share/elasticsearch/bin/elasticsearch-reset-password -u elastic -i --url http://localhost:9200
```

> [!TIP]
> **"Exit code 75" Hatası Neden Çıkardı ve Nasıl Çözüldü?**
> Daha önce `docker-compose.yml` içinde `xpack.security.enabled=false` iken bu komut çalıştırıldığında araç şu hatayı veriyordu:
> `ERROR: Failed to reset password for the [elastic] user, with exit code 75`
> **Açıklama:** Güvenlik altyapısı kapalıyken Elasticsearch yerel şifre yönetim API'lerini başlatmaz. Yeni yapılandırmamızda `xpack.security.enabled=true` ve `ELASTIC_PASSWORD=BilginIT454` tanımlandığı için küme sağlıklıdır ve şifre sıfırlama aracı artık hatasız çalışır.

> [!WARNING]
> **Kibana "Exited (78)" Hatası ve Nedeni:**
> Elastic Stack 8.0 ve sonrasında, `elastic` süper kullanıcısının Kibana'nın dahili servis bağlantısı (`elasticsearch.username`) olarak kullanılması güvenlik nedeniyle kesinlikle yasaklanmıştır (`FATAL Error: value of "elastic" is forbidden`). Kibana iç servis bağlantısı için özel tasarlanmış `kibana_system` hesabını kullanmak zorundadır.
>
> `docker-compose.yml` dosyasına eklenen otomatik **`kibana-setup`** servisi, `kibana_system` kullanıcısının şifresini Elasticsearch açılır açılmaz `.env` içindeki `KIBANA_PASSWORD` (`BilginIT454`) olarak ayarlar ve Kibana'nın hatasız bir şekilde ayağa kalkmasını sağlar.

#### B) Kibana UI Üzerinden Yeni Kullanıcı ve Rol Tanımlama
Prodüksiyon ortamında herkesin `elastic` süper kullanıcısını kullanması önerilmez. Kibana arayüzünden sınırlı yetkili stajyer/analist kullanıcısı oluşturabilirsiniz:

1. Tarayıcıdan `http://<IP>:15601` adresine gidin ve `elastic / BilginIT454` ile oturum açın.
2. Sol menüden **Management > Stack Management > Security > Users** bölümüne girin.
3. **Create user** butonuna tıklayın:
   * **Username:** `devops_analyst`
   * **Password:** `Analyst2026!`
   * **Roles:** `kibana_user` ve `viewer`
4. Yeni kullanıcı ile `15601` portundan oturum açarak sadece okuma yetkisiyle panoları inceleyin.

---

### 4. Dış Ağ Koruması: Nginx Reverse Proxy ile HTTP Basic Auth (Opsiyonel)

Gerçek dünya DevOps altyapılarında Kibana (`15601`) ve Elasticsearch API'si (`9200`) internete açıldığında Nginx katmanında da HTTP Basic Auth ile korunabilir:

1. **Parola Dosyası Oluşturma:**
   ```bash
   sudo apt-get update && sudo apt-get install -y apache2-utils
   sudo htpasswd -cb /etc/nginx/.htpasswd-observability admin BilginIT454
   sudo chmod 640 /etc/nginx/.htpasswd-observability
   sudo chown root:www-data /etc/nginx/.htpasswd-observability
   ```

2. **Nginx Sanal Sunucu Bloğu (Kibana Port 15601 Yönlendirmesi):**
   ```nginx
   server {
       listen 443 ssl http2;
       server_name student101-kibana.devopsatolyesi.com;
       ssl_certificate /etc/letsencrypt/live/devopsatolyesi.com/fullchain.pem;
       ssl_certificate_key /etc/letsencrypt/live/devopsatolyesi.com/privkey.pem;

       location / {
           auth_basic "DevOps Atolyesi - Guvenli Erisim";
           auth_basic_user_file /etc/nginx/.htpasswd-observability;

           proxy_pass http://127.0.0.1:15601;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```

3. **Nginx'i Yeniden Yükleme:**
   ```bash
   sudo nginx -t && sudo systemctl reload nginx
   ```

---

## Temizlik

> **Önemli Bağımlılık Uyarısı (Şimdi Silmeyin):**
> `00-elk-core-stack`, sonraki tüm laboratuvarların (`01` - `07`) loglarını topladığı ve görselleştirdiği merkezi omurgadır. 01'den 07'ye kadar olan labları yapacaksanız bu aşamada konteynerları **silmeyin ve durdurmayın**.
>
> Tüm ELK eğitim serisi tamamlandığında (Modül 07 bittikten sonra), sunucu belleğini (~2.5 - 3 GB RAM) geri kazanmak için temizlik komutu çalıştırılmalıdır:

```bash
# SADECE tüm modüller (01-07) bittiğinde çalıştırın:
cd 00-elk-core-stack
docker compose down -v
```
