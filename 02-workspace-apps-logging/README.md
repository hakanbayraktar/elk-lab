# LAB-ELK-02 — Uygulama Loglarının Yapısal Parse Edilmesi (Grok & JSON)

| Seviye | Tahmini Süre | Profil / Araçlar | Açık Portlar |
|:---:|:---:|:---:|:---:|
| Orta | 35 Dakika | `docker compose`, `logstash`, `grok`, `json` | 8081 (Nginx), 3001 (Node.js API) |

---

## Mimari ve Çalışma Modeli

```text
[ Nginx (Port 8081) ] ──(access.log)──────┐
                                          ▼
                                 [ Logstash Pipeline ]
                                 - Nginx: Grok (%{COMBINEDAPACHELOG})
                                 - API: JSON Codec + Integer Mutate
                                          │
                                          ▼
[ Node.js API (Port 3001) ] ──(api.log)───┴──> [ Elasticsearch: apps-* ]
```

---

## Adım Adım Uygulama Rehberi

### 1. Örnek Uygulamaları Başlatma

```bash
cd 02-workspace-apps-logging/sample-apps
docker compose -f docker-compose.apps.yml up -d
docker compose -f docker-compose.apps.yml ps
```

### 2. Logstash Pipeline'ını Merkezi ELK'ya Bağlama

Merkezi Logstash servisinin (`00-elk-core-stack`) bu log dosyalarını okuyabilmesi için `00-elk-core-stack/pipeline/` altına pipeline dosyasını ekleyin veya güncelleyin:

```bash
cp ../logstash/app-pipeline.conf ../../00-elk-core-stack/pipeline/
```

### 3. Test Trafiği Üretme

```bash
cd 02-workspace-apps-logging/sample-apps
./generate-app-traffic.sh
```

---

## Doğal Doğrulama ve Beklenen Sonuç

### 1. Elasticsearch'te Ayrıştırılmış (Parsed) Nginx Alanlarını Doğrulama

```bash
curl -s "http://localhost:9200/apps-nginx_access-*/_search?pretty" | jq '.hits.hits[0]._source | {clientip, verb, request, response, bytes}'
```

* **Beklenen Çıktı:**
```json
{
  "clientip": "172.18.0.1",
  "verb": "GET",
  "request": "/",
  "response": 200,
  "bytes": 615
}
```
*Grok filtresinin metin satırını yapısal JSON alanlarına böldüğünü ve `response` alanının tam sayı (integer) olduğunu görün.*

### 2. JSON Formatlı API Loglarını Doğrulama

```bash
curl -s "http://localhost:9200/apps-api_json-*/_search?pretty" | jq '.hits.hits[0]._source | {level, service, message, http_status}'
```

---

## Temizlik

```bash
cd 02-workspace-apps-logging/sample-apps
docker compose -f docker-compose.apps.yml down -v
```
