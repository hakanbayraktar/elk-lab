# LAB-ELK-00 — Çekirdek Elastic Stack Kurulumu ve Temel Yönetim

| Seviye | Profil / Araçlar | Açık Portlar |
|:---:|:---:|:---:|
| Başlangıç | `docker compose`, `curl`, `jq`, `kibana` | 9200 (ES), 15601 (Kibana) / 5601, 5044 (Beats), 5000 (TCP) |

[LAB-ELK-00.zip](LAB-ELK-00.zip)

> [!IMPORTANT]
> **DİKKAT: TÜM EĞİTİM BOYUNCA BU LAB AÇIK KALMALIDIR!**
> `00-elk-core-stack`, bu serideki tüm diğer laboratuvarların (01'den 07'ye kadar) merkezi omurgasıdır. Burada ayağa kaldırılan Elasticsearch, Logstash ve Kibana servislerini **kesinlikle durdurmayın veya silmeyin**. Tüm sonraki lablar bu omurgaya bağlanır.

## Amaç
* Docker Compose ile güvenliği aktif Elastic Stack (Elasticsearch, Logstash, Kibana) altyapısını başlatmak.
* Elasticsearch REST API ve Kibana Dev Tools üzerinden manuel doküman indeksleme, güncelleme ve arama işlemlerini gerçekleştirmek.
* Sunucunun canlı Linux kaynaklarını, Docker konteyner durumlarını ve Kubernetes pod bilgilerini toplayıp Elasticsearch'e aktarmak.
* Kibana Discover ekranında KQL (Kibana Query Language) ile canlı log ve metrik sorgulamaları yapmak.
* Kibana Lens arayüzü ile sıfırdan grafik oluşturup panoya (dashboard) kaydetmek.
* Logstash boru hattı (pipeline) üzerinden canlı JSON logu iletmek ve indekslendiğini doğrulamak.

---

## Ön Koşullar
* Çalışan bir Docker motoru ve Docker Compose aracı.
* Linux çekirdek bellek parametresinin ayarlanmış olması (`vm.max_map_count=262144`).
* 9200, 15601, 5044 ve 5000 portlarının boşta olması.

---

## Mimari ve Çalışma Modeli

```text
[ Sistem Verileri & Loglar ] ──(Port 5000 TCP / REST)──┐
[ Canlı Linux / Docker / K8s ] ─────────────────────────┼──► [ Logstash (:5000/:5044) ]
                                                         │              │
                                                         │ (Basic Auth: elastic/BilginIT454)
                                                         │              ▼
                                                         └────► [ Elasticsearch (:9200) ]
                                                                - Tek Düğüm (Single-Node)
                                                                - X-Pack Security Aktif
                                                                - Heap: 1 GB
                                                                        ▲
                                                                        │ (İç Ağ Bağlantısı)
                                                                [ Kibana (:15601) ]
                                                                - Web UI: Port 15601
                                                                - Giriş: elastic / BilginIT454
```

---

## Adım Adım Uygulama Rehberi

### 1. Linux Çekirdek Bellek Parametresini Ayarlama

Elasticsearch mmap dosya sayıları için sistem parametresinin en az `262144` olmasını şart koşar:

```bash
sudo sysctl -w vm.max_map_count=262144
echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.d/99-elasticsearch.conf
```

---

### 2. Çevre Değişkenleri (`.env`) ve Stack'i Başlatma

`00-elk-core-stack` dizinine geçin ve `.env` dosyasını kontrol edin:

```bash
cd 00-elk-core-stack
cat .env
```

Stack'i arka planda ayağa kaldırın:

```bash
docker compose up -d
```

Konteyner durumlarını izleyin:

```bash
docker compose ps
```

* `elasticsearch` servisi `healthy` durumuna geçtikten sonra `kibana-setup` dahili şifreyi tanımlar, ardından `kibana` ve `logstash` servisleri çalışır duruma gelir.

---

### 3. Manuel Doküman Ekleme, Arama ve Yönetim

Elasticsearch bir doküman veritabanıdır. Doküman ekleme ve arama işlemleri hem terminalden REST API (curl) ile hem de Kibana web arayüzündeki **Dev Tools** ekranından yapılabilir.

#### Yöntem A: Terminalden CURL ile REST API Kullanımı

1. **Yeni Bir İndekse Doküman Ekleme (POST):**
   ```bash
   curl -s -u elastic:BilginIT454 -X POST "http://localhost:9200/devops-envanter/_doc" \
     -H "Content-Type: application/json" -d '{
       "sunucu_adi": "web-node-01",
       "ip_adresi": "192.168.1.10",
       "rol": "frontend",
       "durum": "aktif",
       "cpu_kullanimi": 24,
       "tarih": "2026-09-24T12:00:00Z"
     }' | jq .
   ```

2. **Eklenen Dokümanı Arama (GET _search):**
   ```bash
   curl -s -u elastic:BilginIT454 -X GET "http://localhost:9200/devops-envanter/_search?pretty"
   ```

3. **Belirli Bir Kriterle Filtreleme:**
   ```bash
   curl -s -u elastic:BilginIT454 -X POST "http://localhost:9200/devops-envanter/_search?pretty" \
     -H "Content-Type: application/json" -d '{
       "query": {
         "match": {
           "rol": "frontend"
         }
       }
     }'
   ```

4. **İndeksi Silme (DELETE):**
   ```bash
   curl -s -u elastic:BilginIT454 -X DELETE "http://localhost:9200/devops-envanter"
   ```

---

#### Yöntem B: Kibana Dev Tools (Console) Üzerinden Yönetim

Kibana arayüzü, REST API çağrılarını doğrudan tarayıcı üzerinden yazıp çalıştırmanızı sağlayan **Dev Tools Console** aracını sunar.

1. Tarayıcınızdan `http://<SUNUCU_IP>:15601` adresine gidin.
2. `elastic` / `BilginIT454` bilgileriyle oturum açın.
3. Sol gezinti menüsünü açın ve **Management > Dev Tools** bağlantısına tıklayın.
4. Sol konsol penceresine şu komutları yazın:
   ```json
   POST /canli-test/_doc
   {
     "ortam": "production",
     "servis": "odeme-api",
     "hata_kodu": 500,
     "mesaj": "Veritabani baglanti zamanaasimi"
   }

   GET /canli-test/_search
   ```
5. İmleci çalıştırmak istediğiniz komutun üzerine getirip sağ üstteki **Yeşil Üçgen (Play)** butonuna basın. Sağ pencerede JSON yanıtı anında görüntülenecektir.

---

### 4. Canlı Sistem Verilerini Script ile İçe Aktarma

Sunucunun canlı Linux metriklerini, Docker konteyner durumlarını ve Kubernetes pod kayıtlarını Elasticsearch'e yazmak ve Kibana indeks kalıplarını (Data Views) hazır hale getirmek için hazırlanan scripti çalıştırın:

```bash
./scripts/load-system-data.sh
```

Bu script sırasıyla şunları gerçekleştirir:
* Host'un bellek, disk, CPU ve OS bilgilerini okuyup `linux-system-YYYY.MM.DD` indeksine yazar.
* Çalışan Docker konteynerlarını okuyup `docker-container-YYYY.MM.DD` indeksine aktarır.
* Kubernetes pod durumlarını `kubernetes-cluster-YYYY.MM.DD` indeksine yazar.
* Kibana üzerinde 4 adet Data View (`linux-system-*`, `docker-container-*`, `kubernetes-cluster-*`, `logstash-*`) tanımlar.
* 3 adet hazır Lens görselleştirmesi (Docker dağılımı, Kubernetes pod durumları, Linux servis olay trendi) ve canlı arama paneli oluşturur.
* Bu bileşenleri içeren **ELK Core — Altyapı ve Sistem Genel Bakış Panosu**'nu (`core-infrastructure-overview`) otomatik olarak kullanıma hazır hale getirir.

---

### 5. Kibana Discover Ekranında KQL ile Veri Arama

1. Kibana sol menüsünden **Analytics > Discover** bölümüne gidin.
2. Sol üstteki açılır menüden sorgulamak istediğiniz Data View'ı seçin (örneğin: **Linux Sistem & Metrikler** veya **Docker Konteyner Durumları**).
3. Sağ üstteki zaman aralığını **Last 15 minutes** veya **Today** olarak ayarlayın.
4. Üst kısımdaki **KQL (Kibana Query Language)** arama çubuğuna filtrelerinizi yazıp **Enter**'a basın:

* **Sadece hata kayıtlarını görmek için:**
  ```text
  level : "ERROR"
  ```
* **Belirli bir servisin loglarını filtrelemek için:**
  ```text
  service : "system-monitor"
  ```
* **Konteyner adı filtreleme (Docker Data View için):**
  ```text
  container.name : "elasticsearch"
  ```
* **Kubernetes namespace filtreleme:**
  ```text
  kubernetes.namespace : "production" and status : "Running"
  ```

---

### 6. Kibana Lens ile Adım Adım Görselleştirme ve Dashboard Oluşturma

Kendi özel panonuzu arayüzden oluşturmak için şu adımları izleyin:

1. Sol menüden **Analytics > Dashboard** seçeneğine tıklayın.
2. Sağ üstteki **Create dashboard** butonuna basın.
3. Açılan ekranda **Create visualization** butonuna tıklayın (Otomatik olarak Kibana Lens açılır).
4. Sol üstten Data View olarak **Docker Konteyner Durumları (`docker-container-*`)** seçin.
5. Sol paneldeki alan listesinden `container.name.keyword` alanını tutup ortadaki geniş çalışma alanına sürükleyip bırakın:
   * Kibana otomatik olarak konteyner isimlerine göre bir **Çubuk Grafik (Bar Chart)** üretecektir.
6. Sağ üstteki grafik türü seçicisinden grafiği **Donut (Halka)** veya **Pie (Pasta)** grafiğe dönüştürün.
7. Sağ üstteki **Save and return** butonuna basarak grafiği panonuza ekleyin.
8. Panonun sağ üstündeki **Save** butonuna basıp başlık olarak **Sistem ve Konteyner Panom** yazarak kaydedin.

---

### 7. Logstash Pipeline Yapılandırması ve Canlı Log Akışı

Logstash, istemcilerden log kabul eden ve işleyip Elasticsearch'e yazan boru hattıdır (`pipeline/logstash.conf`):

```ruby
input {
  beats { port => 5044 }
  tcp { port => 5000 codec => json_lines }
}
output {
  elasticsearch {
    hosts => ["http://elasticsearch:9200"]
    user => "${ELASTICSEARCH_USERNAME:elastic}"
    password => "${ELASTICSEARCH_PASSWORD:BilginIT454}"
    index => "%{[@metadata][target_index]}"
  }
}
```

Port 5000 üzerinden Logstash'e canlı bir JSON log iletin:

```bash
echo '{"message": "Canli uygulama test logu", "service": "odeme-api", "level": "INFO", "durum": "basarili"}' | nc -N localhost 5000
```

5 saniye sonra Elasticsearch indeksine ulaştığını doğrulayın:

```bash
curl -s -u elastic:BilginIT454 "http://localhost:9200/logstash-*/_search?pretty" | jq '.hits.hits[-1]._source'
```

---

## Doğal Doğrulama ve Beklenen Sonuç

Tüm bileşenlerin sağlıklı çalıştığını doğrulamak için:

1. **Konteyner Durumları:**
   ```bash
   docker compose ps
   ```
   * `elasticsearch` -> `Up (healthy)`
   * `kibana-setup` -> `Exited (0)`
   * `kibana` -> `Up` (Port 15601)
   * `logstash` -> `Up`

2. **Elasticsearch Sağlık Uç Noktası:**
   ```bash
   curl -s -u elastic:BilginIT454 http://localhost:9200/_cluster/health | jq .status
   ```
   * **Beklenen Çıktı:** `"green"` veya `"yellow"`

3. **Kibana HTTP API Testi:**
   ```bash
   curl -s -u elastic:BilginIT454 -I http://localhost:15601/api/status | head -n 1
   ```
   * **Beklenen Çıktı:** `HTTP/1.1 200 OK`

---

## Temizlik

> [!WARNING]
> **Eğitim Süresince Kapatmayın:** Eğer sonraki laboratuvarları (01'den 07'ye kadar) yapacaksanız bu adımı **kesinlikle çalıştırmayın**. Yalnızca tüm eğitim serisi bittiğinde ve ortamı tamamen sıfırlamak istediğinizde bu komutu verin:

```bash
docker compose down -v
```
