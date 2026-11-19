# LAB-ELK-02 — Filebeat ile Linux ve Docker Logları

| Profil / Araçlar | Açık Portlar |
|---|---|
| Filebeat 8.19, `docker compose` | Yeni port açılmaz (Filebeat → `elk-logstash:5044`) |

## Amaç

- Sunucunun SSH ve sudo kayıtlarını (`/var/log/auth.log`) Filebeat ile toplamak.
- Etiketli Docker container'larının loglarını container adı ve image bilgisiyle toplamak.
- Logların Logstash üzerinden `system-logs-*` ve `docker-logs-*` index'lerine yazıldığını görmek.

## Ön Koşullar

- LAB-ELK-01 stack'i çalışıyor olmalıdır (`elk-net` ağı ve `elk-logstash` container'ı).

## Mimari ve Çalışma Modeli

![Filebeat akışı](../assets/diagrams/02-filebeat-flow.png){width=60%}

Filebeat sunucuda tek bir container olarak çalışır ve iki kaynağı okur:

| Kaynak | Nasıl okunur | Eklenen alan | Index |
|---|---|---|---|
| `/var/log/auth.log` | `filestream` input | `fields.log_source: system` | `system-logs-*` |
| Docker container logları | `docker` autodiscover; yalnız `co.elastic.logs/enabled=true` etiketli container'lar | `fields.log_source: docker`, `container.name`, `container.image.name` | `docker-logs-*` |

Etiket şartı, sunucudaki bütün container'ların (Jenkins, SonarQube…) loglarını toplamamak içindir. Logstash index adını `log_source` alanından üretir (LAB-01 `pipeline/90-output.conf`).

<details>
<summary><strong>filebeat.yml ve compose satırları</strong></summary>

| Satır | Ne işe yarar |
|---|---|
| `type: filestream`, `paths: /var/log/auth.log` | Dosyayı satır satır okur; okuduğu yeri `filebeat-data` volume'unda tutar, yeniden başlayınca kaldığı yerden devam eder. |
| `hints.enabled: true`, `default_config.enabled: false` | Container'lar varsayılan olarak toplanmaz; etiketle açılır. |
| `type: container` | Docker'ın JSON log satırını açar; `message` alanına yalnız uygulamanın yazdığı satır gelir. |
| `hosts: ["elk-logstash:5044"]` | Filebeat `elk-net` ağında olduğu için Logstash'e container adıyla bağlanır. |
| `user: root`, `/var/log:/var/log:ro` | `auth.log` yalnız root ve `adm` grubunca okunabilir. |
| `/var/run/docker.sock:ro` | Autodiscover, başlayan container'ları ve etiketlerini Docker API'den izler. |

</details>

## Adım Adım Uygulama Rehberi

### 1. Filebeat'i başlatma

```bash
cd ~/elk-lab/02-filebeat-host-docker
docker compose up -d
```

Filebeat'in Logstash'e bağlandığını loglardan görün:

```bash
sleep 15
docker logs elk-filebeat 2>&1 | grep -o 'Connection to backoff(async(tcp://elk-logstash:5044)) established' | head -1
```

```text
Connection to backoff(async(tcp://elk-logstash:5044)) established
```

### 2. Linux loglarını görme

Filebeat `auth.log` dosyasını baştan okur; belge sayısı bir süre artmaya devam eder:

```bash
sleep 20
curl -s -u elastic:'DevOps2026!' "http://localhost:9200/_cat/indices/system-logs-*?v&h=index,docs.count"
```

Sunucuya kendiniz bir başarısız SSH girişi yapın; satır `auth.log`'a düşer:

```bash
ssh -o BatchMode=yes -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR deneme@localhost true
```

```text
deneme@localhost: Permission denied (publickey,password,keyboard-interactive).
```

Filebeat önce dosyadaki eski satırları okur; yeni satır en son gelir. Satır Elasticsearch'e düşene kadar bekleyin (birkaç dakika sürebilir):

```bash
until curl -s -u elastic:'DevOps2026!' "http://localhost:9200/system-logs-*/_count?q=message:deneme" | jq -e '.count > 0' > /dev/null; do sleep 10; done
curl -s -u elastic:'DevOps2026!' "http://localhost:9200/_cat/indices/system-logs-*?v&h=index,docs.count"
```

Satırı görün:

```bash
curl -s -u elastic:'DevOps2026!' "http://localhost:9200/system-logs-*/_search?q=message:deneme&size=1&filter_path=hits.hits._source&_source=message,log.file.path,fields" | jq '.hits.hits[0]._source'
```

```json
{
  "fields": {
    "log_source": "system"
  },
  "log": {
    "file": {
      "path": "/var/log/auth.log"
    }
  },
  "message": "2026-11-19T19:02:13.418503+03:00 student103 sshd[20512]: Invalid user deneme from 127.0.0.1 port 51874"
}
```

Satırın tamamı tek bir `message` alanında duruyor; kullanıcı adı ve IP ayrı alan değil. LAB-03'te grok ile bunları alanlara ayıracağız.

### 3. Docker loglarını görme

Etiketli bir test container'ı çalıştırın. Üç satır yazar ve kapanır:

```bash
docker run --rm --name demo-worker --label co.elastic.logs/enabled=true alpine \
  sh -c 'for i in 1 2 3; do echo "job $i tamamlandi"; sleep 1; done; sleep 10'
```

```text
job 1 tamamlandi
job 2 tamamlandi
job 3 tamamlandi
```

Etiketsiz bir container'ın logu toplanmaz:

```bash
docker run --rm --name demo-etiketsiz alpine echo "bu satir toplanmaz"
```

Container loglarını sorgulayın:

```bash
sleep 10
curl -s -u elastic:'DevOps2026!' "http://localhost:9200/docker-logs-*/_search?size=5&sort=@timestamp:desc&filter_path=hits.hits._source&_source=message,container.name,container.image.name" | jq -c '.hits.hits[]._source'
```

```text
{"container":{"image":{"name":"alpine"},"name":"demo-worker"},"message":"job 3 tamamlandi"}
{"container":{"image":{"name":"alpine"},"name":"demo-worker"},"message":"job 2 tamamlandi"}
{"container":{"image":{"name":"alpine"},"name":"demo-worker"},"message":"job 1 tamamlandi"}
```

`demo-etiketsiz` sonuçta yoktur; `container.name` ve `container.image.name` alanlarını autodiscover ekledi.

## Temizlik

Filebeat LAB-03 ve LAB-06'da da kullanılır; açık bırakın. Lablar bitince:

```bash
cd ~/elk-lab/02-filebeat-host-docker
docker compose down -v
```

`-v`, Filebeat'in okuma konumunu tutan `filebeat-data` volume'unu da siler. Elasticsearch'teki index'ler kalır.

Sonraki lab: **[LAB-ELK-03 — Logstash Grok ile Log Ayrıştırma](../03-logstash-grok/README.md)**
