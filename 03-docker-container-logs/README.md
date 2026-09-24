# LAB-ELK-03 — Docker Daemon ve Konteyner Loglarının Toplanması

| Seviye | Profil / Araçlar | Açık Portlar |
|:---:|:---:|:---:|
| Orta | Docker, Filebeat, add_docker_metadata, Kibana | 9200 (ES), 15601 (Kibana) |

[LAB-ELK-03.zip](LAB-ELK-03.zip)

> [!IMPORTANT]
> **DİKKAT: `00-elk-core-stack` AÇIK KALMALIDIR!**
> Bu laboratuvardaki işlemler merkezi ELK omurgasına bağlanır. `00-elk-core-stack` dizinindeki Elasticsearch ve Kibana servislerini **kesinlikle durdurmayın veya silmeyin**. Tüm lablar bu ortak omurga üzerinden çalışır.

---

## Amaç
* Docker motorunun host üzerinde `/var/lib/docker/containers/*/*.log` dizininde tuttuğu konteyner günlüklerini Filebeat ile toplamak.
* `/var/run/docker.sock` soketi üzerinden `add_docker_metadata` işlemcisi ile loglara konteyner adı, imajı ve ID'sini otomatik eklemek.
* Test amacıyla çalıştırılan geçici bir konteynerin (`demo-worker`) loglarının sisteme dinamik olarak düştüğünü kanıtlamak.
* Toplanan verilerin Elasticsearch üzerinde `docker-containers-*` indeksine yazıldığını doğrulamak.
* Kibana Discover üzerinde konteyner isimlerine göre KQL sorgulamaları yapmak.

---

## Ön Koşullar
* **Merkezi ELK Omurgası:** `00-elk-core-stack` servislerinin (`elasticsearch`, `kibana`) çalışıyor olması gereklidir.
* Docker soketine (`/var/run/docker.sock`) erişim izninizin bulunması.
* Giriş Bilgileri: Kullanıcı: `elastic` | Şifre: `BilginIT454` | Port: `15601`.

---

## Mimari ve Çalışma Modeli

```text
[ Docker Daemon & Konteynerlar ]
├── elasticsearch, kibana, logstash, demo-apps
└── Geçici Test Konteynerı (demo-worker)
                 │ (stdout / stderr JSON dosyaları)
                 ▼
     [/var/lib/docker/containers/*/*.log]
                 │
                 ▼
      [ Filebeat Konteyneri ]
      - Soket: /var/run/docker.sock
      - Processor: add_docker_metadata
                 │
                 ▼ (Basic Auth: elastic/BilginIT454)
      [ Elasticsearch (:9200) ]
      - İndeks: docker-containers-YYYY.MM.DD
                 ▲
                 │
      [ Kibana UI (:15601) ]
      - Data View: docker-containers-* veya docker-container-*
```

---

## Adım Adım Uygulama Rehberi

### Adım 1: Lab Dizinine Geçin ve Toplayıcıyı Başlatın

İlgili dizine geçerek Docker loglarını toplayacak Filebeat konteynerini çalıştırın:

```bash
cd ~/elk-lab/03-docker-container-logs
docker compose -f docker-compose.filebeat.yml up -d
docker compose -f docker-compose.filebeat.yml ps
```

*Toplayıcının çalıştığını loglardan doğrulayın:*

```bash
docker logs --tail=15 filebeat-docker
```

---

### Adım 2: Test Konteyneri Çalıştırıp Log Üretin

Sistemde dinamik log akışı oluşturmak için 5 saniye çalışıp kapanan geçici bir konteyner başlatın:

```bash
docker run --rm --name demo-worker alpine sh -c '
  for i in $(seq 1 5); do
    echo "{\"event\": \"job_processed\", \"job_id\": $i, \"status\": \"success\", \"duration_ms\": $((i * 15))}"
    sleep 1
  done
'
```

*Bu işlem bittiğinde konteyner kendini silecektir; ancak logları Filebeat tarafından Elasticsearch'e çoktan aktarılmış olacaktır.*

---

### Adım 3: Docker Metadata Entegrasyonunu İnceleyin

`filebeat-docker.yml` içindeki `add_docker_metadata` işlemcisi:
* Host üzerindeki `/var/run/docker.sock` soketine bağlanır.
* Okuduğu log dosyasının hangi konteynere ait olduğunu tespit eder.
* Log kaydına `container.name`, `container.image.name` ve `container.id` alanlarını ekler.

---

## Doğal Doğrulama ve Beklenen Sonuç

### 1. Elasticsearch API ile Otomatik Metaverileri Doğrulama

Elasticsearch'ten `demo-worker` isimli konteynere ait logları sorgulayın:

```bash
curl -s -u elastic:BilginIT454 "http://localhost:9200/docker-containers-*/_search?q=container.name:demo-worker&pretty" | jq '.hits.hits[0]._source | {container: .container.name, image: .container.image.name, message: .message}'
```

* **Beklenen Örnek Çıktı:**
```json
{
  "container": "demo-worker",
  "image": "alpine",
  "message": "{\"event\": \"job_processed\", \"job_id\": 1, \"status\": \"success\", \"duration_ms\": 15}"
}
```

---

### 2. Kibana Discover Ekranında Arama

1. Tarayıcınızdan Kibana'yı açın (`http://<SUNUCU_IP>:15601` veya `https://studentXX-kibana.devopsatolyesi.com`).
2. **Analytics > Discover** bölümüne gidin.
3. Veri Görünümünden `docker-containers-*` veya `docker-container-*` seçin.
4. KQL arama çubuğuna şunu yazın:
   ```text
   container.name : "demo-worker"
   ```
5. Listelenen log kayıtlarında konteyner adı ve mesajının eksiksiz görüntülendiğini teyit edin.

---

## Temizlik

Yalnızca bu lab için başlattığınız Docker toplayıcı konteynerini durdurun:

```bash
cd ~/elk-lab/03-docker-container-logs
docker compose -f docker-compose.filebeat.yml down
```

> [!WARNING]
> **Merkezi Omurga Hatırlatması:** `00-elk-core-stack` servislerini (`elasticsearch`, `kibana`) **kesinlikle kapatmayın**. Sonraki tüm laboratuvarlar bu omurga üzerinde çalışır.
