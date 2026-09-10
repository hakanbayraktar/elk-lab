# LAB-ELK-03 — Docker Daemon ve Konteyner Loglarının Toplanması

| Seviye | Tahmini Süre | Profil / Araçlar | Açık Portlar |
|:---:|:---:|:---:|:---:|
| Orta | 30 Dakika | `docker`, `filebeat`, `add_docker_metadata` | - |

---

## Mimari ve Çalışma Modeli

```text
[ Docker Daemon ] ──(Konteyner stdout / stderr)──> [/var/lib/docker/containers/*/*.log]
                                                              │
                                                              ▼
                                                   [ Filebeat Konteyneri ]
                                                   - Mount: /var/run/docker.sock
                                                   - Processor: add_docker_metadata
                                                              │
                                                              ▼
                                                   [ Elasticsearch (:9200) ]
                                                   (docker.container.name, image, labels)
```

---

## Adım Adım Uygulama Rehberi

### 1. Konteyner Log Toplayıcıyı Başlatma

```bash
cd 03-docker-container-logs
docker compose -f docker-compose.filebeat.yml up -d
docker compose -f docker-compose.filebeat.yml ps
```

### 2. Test Konteyneri Başlatma (Log Üretimi)

Log toplayıcının dinamik olarak yeni açılan konteynerları tespit ettiğini kanıtlamak için bir test konteyneri çalıştırın:

```bash
docker run --rm --name demo-worker alpine sh -c '
  for i in $(seq 1 5); do
    echo "{\"event\": \"job_processed\", \"job_id\": $i, \"duration_ms\": $((i * 12))}"
    sleep 1
  done
'
```

---

## Doğal Doğrulama ve Beklenen Sonuç

### 1. Elasticsearch'te Otomatik Docker Meta Verilerini Doğrulama

```bash
curl -s "http://localhost:9200/docker-containers-*/_search?q=container.name:demo-worker&pretty" | jq '.hits.hits[0]._source.container'
```

* **Beklenen Çıktı:**
```json
{
  "name": "demo-worker",
  "image": {
    "name": "alpine"
  }
}
```
*Filebeat'in Docker soketi (`docker.sock`) üzerinden konteyner adını, imajını ve ID'sini otomatik olarak log satırına eklediğini doğrulayın.*

---

## Temizlik

```bash
cd 03-docker-container-logs
docker compose -f docker-compose.filebeat.yml down -v
```
