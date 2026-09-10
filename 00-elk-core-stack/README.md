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

## Temizlik

Laboratuvarı sıfırlamak veya kaynakları serbest bırakmak istediğinizde:

```bash
docker compose down -v
```
