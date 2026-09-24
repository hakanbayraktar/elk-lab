# LAB-ELK-03 — Docker Daemon ve Konteyner Loglarının Toplanması

| Seviye | Profil / Araçlar | Açık Portlar |
|:---:|:---:|:---:|
| Orta | Docker, Filebeat, add_docker_metadata, Kibana | 9200 (ES), 15601 (Kibana) |

[LAB-ELK-03.zip](LAB-ELK-03.zip)

## Amaç
* Docker motorunun host üzerinde `/var/lib/docker/containers/*/*.log` dizininde sakladığı konteyner `stdout` ve `stderr` günlüklerini Filebeat ile toplamak.
* `/var/run/docker.sock` soketi üzerinden çalışan `add_docker_metadata` işlemcisi ile loglara dinamik olarak `container.name`, `container.image` ve `container.id` etiketlerini eklemek.
* Yeni başlatılan geçici bir test konteynerinin (`demo-worker`) loglarının herhangi bir manuel müdahaleye gerek kalmadan anında algılandığını doğrulamak.
* Toplanan verilerin Elasticsearch'te `docker-containers-*` indeksine güvenle kaydedildiğini REST API ile sorgulamak.
* Kibana Discover arayüzünde çalışan konteyner isimlerine göre KQL sorgulamaları ve görsel filtrelemeler yapmak.

---

## Ön Koşullar
* **Merkezi ELK Omurgası:** `00-elk-core-stack` servislerinin (`elasticsearch`, `kibana`) çalışır durumda olması gerekmektedir.
* Host üzerindeki `/var/run/docker.sock` soketine ve Docker daemon'a erişim izni.
* Kimlik Doğrulama: Kullanıcı: `elastic` | Şifre: `BilginIT454`.

---

## Mimari ve Çalışma Modeli

```text
[ Docker Daemon & Konteynerlar ]
├── elasticsearch, kibana, logstash, demo-apps
└── Yeni Başlatılan Konteynerlar (demo-worker)
                 │ (stdout / stderr JSON günlükleri)
                 ▼
     [/var/lib/docker/containers/*/*.log]
                 │
                 ▼
      [ Filebeat Konteyneri ]
      - Volume: /var/run/docker.sock
      - Processor: add_docker_metadata (Docker API sorgular)
                 │
                 ▼ (Basic Auth: elastic/BilginIT454)
      [ Elasticsearch (:9200) ]
      - Index: docker-containers-YYYY.MM.DD
                 ▲
                 │
      [ Kibana UI (:15601) ]
      - Data View: docker-containers-* veya docker-container-*
```

---

## Adım Adım Uygulama Rehberi

### 1. Konteyner Log Toplayıcıyı Başlatma

Docker log toplayıcı servisini çalıştırmak için ilgili dizine geçin:

```bash
cd ~/elk-lab/03-docker-container-logs
docker compose -f docker-compose.filebeat.yml up -d
docker compose -f docker-compose.filebeat.yml ps
```

* `filebeat-docker` servisinin `Up` olduğunu ve host üzerindeki Docker soketini okuyabildiğini loglardan kontrol edin:

```bash
docker logs --tail=15 filebeat-docker
```

---

### 2. Test Konteyneri Başlatma (Dinamik Algılama Testi)

Filebeat'in çalışan yeni bir konteyneri sistemde anında fark edip loglarını metaverisiyle birlikte yakaladığını kanıtlamak için 5 saniyelik geçici bir worker çalıştırın:

```bash
docker run --rm --name demo-worker alpine sh -c '
  for i in $(seq 1 5); do
    echo "{\"event\": \"job_processed\", \"job_id\": $i, \"status\": \"success\", \"duration_ms\": $((i * 15))}"
    sleep 1
  done
'
```

Bu işlem bittiğinde `demo-worker` konteyneri kendini otomatik olarak silecektir; ancak ürettiği loglar Docker daemon tarafından diske yazılmış ve Filebeat tarafından çoktan Elasticsearch'e aktarılmıştır.

---

## Doğal Doğrulama ve Beklenen Sonuç

### 1. Elasticsearch API ile Otomatik Metaverileri Doğrulama

Elasticsearch'ten `demo-worker` adına sahip konteynerin loglarını sorgulayın:

```bash
curl -s -u elastic:BilginIT454 "http://localhost:9200/docker-containers-*/_search?q=container.name:demo-worker&pretty" | jq '.hits.hits[0]._source | {container: .container.name, image: .container.image.name, message: .message}'
```

* **Beklenen Çıktı:**
```json
{
  "container": "demo-worker",
  "image": "alpine",
  "message": "{\"event\": \"job_processed\", \"job_id\": 1, \"status\": \"success\", \"duration_ms\": 15}"
}
```
*`add_docker_metadata` işlemcisinin konteyner adını (`demo-worker`) ve imaj adını (`alpine`) log satırına otomatik olarak iliştirdiğini doğrulayın.*

---

### 2. Kibana Discover Ekranında İnceleme

1. Tarayıcınızdan Kibana'ya bağlanın (`http://<SUNUCU_IP>:15601` veya `https://studentXX-kibana.devopsatolyesi.com`).
2. **Analytics > Discover** sekmesine gidin.
3. Veri Görünümünden `docker-containers-*` veya `docker-container-*` seçin *(Gerekirse Stack Management > Data Views altından `docker-containers-*` oluşturabilirsiniz)*.
4. KQL arama çubuğuna şunu yazın:
   ```text
   container.name : "demo-worker"
   ```
5. Sol sütundaki alan listesinden `container.name`, `container.image.name` ve `message` alanlarını ekleyerek konteyner envanter görünümünüzü inceleyin.

---

## Temizlik

Test toplayıcı konteynerini durdurarak bu laboratuvarı tamamlayın:

```bash
cd ~/elk-lab/03-docker-container-logs
docker compose -f docker-compose.filebeat.yml down
```

> **Önemli Not:** Merkezi ELK omurgası (`00-elk-core-stack`), sonraki Kubernetes ve Dashboard laboratuvarları için çalışmaya devam etmelidir.
