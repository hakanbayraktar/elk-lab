# LAB-ELK-01 — Elastic Stack Kurulumu ve İlk Belgeler

| Profil / Araçlar | Açık Portlar |
|---|---|
| `docker compose`, Elasticsearch 8.19, Kibana 8.19, Logstash 8.19 | 9200 (Elasticsearch), 15601 (Kibana), 5044 (Logstash Beats) |

## Amaç

- Elasticsearch, Kibana ve Logstash'i Docker Compose ile kurmak.
- `curl` ile index oluşturmak, belge eklemek, aramak ve silmek.
- Aynı işlemleri Kibana Dev Tools ekranından yapmak.

## Ön Koşullar

- Sunucuda `docker`, `docker compose`, `curl` ve `jq` olmalıdır.
- `9200`, `15601` ve `5044` portları boş olmalıdır.
- Bu stack sonraki bütün labların ortak altyapısıdır; LAB-07 bitene kadar kapatmayın.

## Mimari ve Çalışma Modeli

![Elastic Stack mimarisi](../assets/diagrams/01-elk-stack.png){width=60%}

- **Elasticsearch** veriyi saklar ve arar. Tek node çalışır, güvenlik açıktır (`elastic` kullanıcısı).
- **Kibana** web arayüzüdür. Elasticsearch'e `kibana_system` kullanıcısıyla bağlanır; bu kullanıcının parolasını `kibana-setup` container'ı verip kapanır.
- **Logstash** Filebeat'lerden `5044` portundan log alır ve Elasticsearch'e yazar. Pipeline dosyaları `pipeline/` klasöründedir.

<details>
<summary><strong>Compose ve pipeline dosyalarındaki önemli satırlar</strong></summary>

| Satır | Ne işe yarar |
|---|---|
| `discovery.type=single-node` | Tek node'lu cluster; başka node aramaz. |
| `ELASTIC_PASSWORD=${ELASTIC_PASSWORD:-DevOps2026!}` | `elastic` kullanıcısının parolası. `.env` dosyası yoksa varsayılan kullanılır. |
| `es-data` volume | Container silinse de veri kalır. `docker compose down -v` ile silinir. |
| `"15601:5601"` | Kibana container içinde 5601'de, sunucuda 15601'de yayınlanır. |
| `CONFIG_RELOAD_AUTOMATIC=true` | `pipeline/` klasöründeki değişiklik Logstash yeniden başlatılmadan yüklenir; pipeline'a yeni filtre eklemek için Logstash'i kapatmak gerekmez. |
| `networks: default: name: elk-net` | Sonraki labların container'ları bu ağa katılıp `elk-logstash` adıyla bağlanır. |
| `index => "%{[fields][log_source]}-logs-%{+YYYY.MM.dd}"` | Filebeat'in eklediği `log_source` alanına göre `system-logs-…`, `docker-logs-…`, `k8s-logs-…` index'leri oluşur. |

</details>

## Adım Adım Uygulama Rehberi

### 1. Stack'i başlatma

```bash
cd ~/elk-lab/01-elk-stack-setup
```

Elasticsearch, index dosyalarını diskten okurken **mmap** (memory-mapped file) kullanır: dosyayı belleğe eşler, böylece işletim sistemi sık okunan kısımları RAM'de tutar ve arama hızlanır. Her index çok sayıda dosyadan oluştuğu için çok sayıda eşleme açılır. Linux bir sürecin açabileceği eşleme sayısını `vm.max_map_count` ile sınırlar; varsayılan değer `65530`'dur. Elasticsearch açılışta bu değerin en az `262144` olduğunu kontrol eder. Daha düşükse `max virtual memory areas vm.max_map_count [65530] is too low` hatasıyla kapanır ve container sürekli yeniden başlar.

Komut, değer zaten yeterliyse hiçbir şey yapmaz; düşükse `262144`'e yükseltir. `sysctl -w` ile verilen değer sunucu yeniden başlayana kadar geçerlidir:

```bash
[ "$(sysctl -n vm.max_map_count)" -ge 262144 ] || sudo sysctl -w vm.max_map_count=262144
sysctl vm.max_map_count
```

Stack'i başlatın. İlk açılışta dört image indirilir (yaklaşık 2 GB). Compose servisleri `depends_on` sırasıyla açar:

1. **elasticsearch** başlar. Healthcheck her 10 saniyede `_cluster/health` adresini sorgular; cevap gelince `healthy` olur.
2. Elasticsearch `healthy` olunca **logstash** ve **kibana-setup** başlar.
3. **kibana-setup** işini bitirip `0` koduyla kapanınca **kibana** başlar.

Komut, Elasticsearch `healthy` olana kadar bekler; bu 1-2 dakika sürebilir:

```bash
docker compose up -d
```

```bash
docker compose ps -a --format "table {{.Name}}\t{{.Status}}"
```

```text
NAME                STATUS
elk-elasticsearch   Up About a minute (healthy)
elk-kibana          Up 9 seconds
elk-kibana-setup    Exited (0) 9 seconds ago
elk-logstash        Up 10 seconds
```

**`elk-kibana-setup` neden var ve neden kapanıyor?** Kibana, Elasticsearch'e bağlanırken `elastic` süper kullanıcısını kullanamaz; Elasticsearch 8 buna izin vermez. Kibana için hazır gelen `kibana_system` kullanıcısı kullanılır, ama bu kullanıcının ilk kurulumda parolası yoktur. `kibana-setup`, Elasticsearch API'sine (`_security/user/kibana_system/_password`) bir istek atıp bu kullanıcıya `.env` dosyasındaki ya da varsayılan parolayı verir ve işi bittiği için kapanır.

- `Exited (0)`: parola verildi, Kibana bu parolayla bağlanıyor. Doğru durum budur.
- `Exited (1)` ya da başka bir kod: parola verilemedi. Kibana açılmaz ve `docker logs elk-kibana` çıktısında kimlik doğrulama hatası görünür. Önce `docker logs elk-kibana-setup` ile nedenine bakın.

`elk-kibana` ve `elk-logstash` için `Up` görmek yeterlidir. Kibana'nın arayüzü açılması, `Up` olduktan sonra 30-60 saniye daha sürer.

### 2. Elasticsearch'e bağlanma

```bash
curl -s -u elastic:'DevOps2026!' http://localhost:9200 | jq '{name, version: .version.number}'
```

```bash
curl -s -u elastic:'DevOps2026!' "http://localhost:9200/_cluster/health?filter_path=status,number_of_nodes"
```

İlk komut Elasticsearch'in çalıştığını ve sürümünü gösterir. `-u elastic:'DevOps2026!'` kullanıcı adı ve parolayı gönderir; güvenlik açık olduğu için parolasız istek `401` ile reddedilir.

İkinci komut cluster sağlığını gösterir. `status` şunlardan biridir:

- `green`: bütün shard'lar yerinde.
- `yellow`: veri tam, ama bazı replica shard'lar atanamamış. Elasticsearch her index'i parçalara (**shard**) böler ve her shard'ın bir yedeğini (**replica**) tutar. Yedek, asıl shard'la aynı node'a konmaz; o node çökerse yedek de giderdi. Tek node'lu cluster'da yedeği koyacak ikinci node olmadığı için replica'lar atanmadan bekler ve durum `yellow` görünür. Veri kaybı yoktur; bu lab ortamında normaldir.
- `red`: bazı verilere erişilemiyor; bu durumda devam etmeyin.

### 3. Belge ekleme, arama ve silme

Elasticsearch'te veri **belge** (document) olarak saklanır: bir JSON nesnesi. Belgeler **index** içinde durur; index, ilişkisel veritabanındaki tabloya benzer.

Bir sunucu envanteri belgesi ekleyin. Adresin parçaları:

- `devops-envanter`: index adı. Yoksa ilk belgeyle birlikte otomatik oluşur ve alanların türü (`sunucu` metin, `cpu` sayı) ilk değerlerden çıkarılır.
- `_doc/web-01`: belgenin kimliği (`_id`). Kimlik vermezseniz Elasticsearch rastgele bir kimlik üretir.
- `?refresh=true`: belgeyi hemen aranabilir yapar. Elasticsearch yeni belgeleri normalde yaklaşık 1 saniye sonra aramaya açar; bu parametre olmadan hemen ardından yapılan arama belgeyi bulamayabilir.

```bash
curl -s -u elastic:'DevOps2026!' -X POST "http://localhost:9200/devops-envanter/_doc/web-01?refresh=true" \
  -H "Content-Type: application/json" \
  -d '{"sunucu": "web-01", "rol": "frontend", "durum": "aktif", "cpu": 24}' | jq '{_index, _id, result}'
```

İkinci belgeyi ekleyin:

```bash
curl -s -u elastic:'DevOps2026!' -X POST "http://localhost:9200/devops-envanter/_doc/db-01?refresh=true" \
  -H "Content-Type: application/json" \
  -d '{"sunucu": "db-01", "rol": "database", "durum": "bakimda", "cpu": 71}' | jq '{_index, _id, result}'
```

Belgeleri `_search` ile arayın. `match` sorgusu metin araması yapar: `rol` alanında `frontend` kelimesi geçen belgeleri bulur. `filter_path` yalnız belgelerin içeriğini (`_source`) döndürür, böylece çıktı kısa kalır:

```bash
curl -s -u elastic:'DevOps2026!' "http://localhost:9200/devops-envanter/_search?filter_path=hits.hits._source" \
  -H "Content-Type: application/json" \
  -d '{"query": {"match": {"rol": "frontend"}}}' | jq -c '.hits.hits[]._source'
```

```text
{"sunucu":"web-01","rol":"frontend","durum":"aktif","cpu":24}
```

Sayı alanlarında `range` sorgusu kullanılır. `gt` (greater than) "büyüktür" demektir; `gte`, `lt`, `lte` de vardır. CPU kullanımı 50'nin üstünde olanlar:

```bash
curl -s -u elastic:'DevOps2026!' "http://localhost:9200/devops-envanter/_search?filter_path=hits.hits._source" \
  -H "Content-Type: application/json" \
  -d '{"query": {"range": {"cpu": {"gt": 50}}}}' | jq -c '.hits.hits[]._source'
```

```text
{"sunucu":"db-01","rol":"database","durum":"bakimda","cpu":71}
```

`_update` belgenin yalnız verilen alanlarını değiştirir; diğer alanlar korunur. `db-01`'in durumunu `aktif` yapın ve belgeyi kimliğiyle (`_doc/db-01`) okuyun:

```bash
curl -s -u elastic:'DevOps2026!' -X POST "http://localhost:9200/devops-envanter/_update/db-01?refresh=true" \
  -H "Content-Type: application/json" -d '{"doc": {"durum": "aktif"}}' | jq -r .result
curl -s -u elastic:'DevOps2026!' "http://localhost:9200/devops-envanter/_doc/db-01" | jq -c ._source
```

```text
updated
{"sunucu":"db-01","rol":"database","durum":"aktif","cpu":71}
```

### 4. Kibana'ya giriş

Tarayıcıda açılacak adres:

```bash
echo "https://$(hostname)-kibana.devopsatolyesi.com"
```

Alan adı yoksa sunucu IP'si ve portuyla da açılır (firewall'da `15601` açık olmalıdır):

```bash
echo "http://$(curl -s ifconfig.me):15601"
```

Kullanıcı `elastic`, parola `DevOps2026!`. İlk girişte çıkan **Welcome to Elastic** ekranında **Explore on my own**'a tıklayın.

### 5. Kibana Dev Tools ile aynı işlemler

1. Sol üstteki menü düğmesine tıklayın.
2. Menünün altında **Management > Dev Tools**'a tıklayın. İlk açılışta çıkan tanıtım penceresini **Skip tour** ile kapatın.

   ![Dev Tools menüsü](../assets/screenshots/LAB-ELK-01/01-devtools-menu.png){width=75%}

3. Sol paneldeki örnek metni silin (**Clear this input**) ve aşağıdaki isteği yapıştırın.
4. İmleci isteğin ilk satırına getirip sağdaki ▶ (**Click to send request**) düğmesine basın. Yanıt sağ panelde görünür.

   ![Dev Tools isteği](../assets/screenshots/LAB-ELK-01/02-devtools-run.png){width=75%}

```http
GET devops-envanter/_search
{
  "query": { "match": { "durum": "aktif" } }
}
```

```http
GET _cat/indices/devops-*?v
```

Dev Tools aynı REST API'yi kullanır; `curl` ile yaptığınız her isteği burada adres ve gövde olarak yazabilirsiniz.

### 6. Index'i silme

```bash
curl -s -u elastic:'DevOps2026!' -X DELETE "http://localhost:9200/devops-envanter" | jq -c .
```

```text
{"acknowledged":true}
```

## Temizlik

Stack sonraki labların altyapısıdır; **bütün lablar bitince** kapatın. `-v` Elasticsearch verisini de siler:

```bash
cd ~/elk-lab/01-elk-stack-setup
docker compose down -v
```

Sonraki lab: **[LAB-ELK-02 — Filebeat ile Linux ve Docker Logları](../02-filebeat-host-docker/README.md)**
