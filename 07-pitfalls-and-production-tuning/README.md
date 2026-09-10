# LAB-ELK-07 — Prodüksiyon İpuçları, Shard Yönetimi ve Sorun Giderme

| Seviye | Tahmini Süre | Profil / Araçlar | Açık Portlar |
| :--- | :--- | :--- | :--- |
| İleri (Advanced) | 35 Dakika | Elasticsearch Admin API, cURL, jq, ILM | 9200 (Elasticsearch), 5601 (Kibana) |

[LAB-ELK-07.zip](LAB-ELK-07.zip)

## Amaç

- Elasticsearch küme sağlığı (`green`, `yellow`, `red`) metriklerini ve atanmamış shard (`unassigned shard`) nedenlerini analiz etmek.
- Disk doluluğunda devreye giren `disk watermark flood_stage` kilidini (`read_only_allow_delete: true`) teşhis edip açmak.
- Dinamik eşleme patlamasını (`mapping explosion`) ve JVM OOM (Out Of Memory) risklerini önleme tekniklerini kavramak.
- JVM bellek yönetiminde %50 kuralı ve 32 GB Compressed OOPs (Ordinary Object Pointers) mimari sınırını anlamak.
- İndeks Yaşam Döngüsü Yönetimi (ILM - Index Lifecycle Management) ile otomatik indeks rotasyonu ve saklama (retention) politikaları uygulamak.

## Ön Koşullar

- `00-elk-core-stack` servislerinin ayakta olması (`http://localhost:9200`).
- Terminalde `curl` ve `jq` araçlarının hazır olması.

## Kritik Prodüksiyon Mimarisi ve Tuzaklar

### 1. Küme Sağlığı Neden Sarı (YELLOW) Olur?
Elasticsearch'te varsayılan olarak her indeks 1 birincil (primary) ve 1 kopya (replica) shard ile oluşturulur. Tek düğümlü (single-node) bir geliştirme veya test ortamında kopya shard yerleşecek ikinci bir düğüm bulamadığı için küme durumu `YELLOW` olur (Veri kaybı yoktur ancak yüksek erişilebilirlik sağlanamaz).

### 2. Disk Watermark Kademeleri
Elasticsearch disk doluluk oranını 3 eşikle kontrol eder:
- **Low Watermark (%85):** Yeni indeks shard'ları bu düğüme atanmaz.
- **High Watermark (%90):** Düğümdeki shard'lar diğer düğümlere taşınmaya (relocation) çalışılır.
- **Flood Stage (%95):** Kümedeki tüm indeksler otomatik olarak salt-okunur (`read_only_allow_delete`) moda alınır. Yeni veri yazılamaz ve istemcilere `429 Too Many Requests` veya `ClusterBlockException` döner. Disk boşalsa dahi bu kilit manuel komut verilene kadar kaldırılmaz!

### 3. JVM %50 Kuralı ve 32 GB Sınırı
- Sunucu RAM'inin en fazla %50'si Elasticsearch JVM heap'ine (`-Xms` ve `-Xmx`) verilmelidir. Kalan %50 RAM, Linux işletim sistemi çekirdeğinin disk dosya önbelleği (OS Page Cache) için serbest kalmalıdır. Lucene disk aramalarını doğrudan OS page cache üzerinden hızlandırır.
- JVM Heap boyutu asla **31-32 GB** sınırını aşmamalıdır (Önerilen: `30GB` veya `31GB`). 32 GB aşıldığında Java sanal makinesi bellek tasarrufu sağlayan **Compressed OOPs (Compressed Ordinary Object Pointers)** özelliğini devre dışı bırakır ve 64-bit tam adreslemeye geçer. Bu durum bellek kullanımını %40 artırır ve CPU L1/L2/L3 önbellek verimini düşürür.

### 4. Eşleme Patlaması (Mapping Explosion)
Geliştiricilerin rastgele JSON anahtarları üretmesi (`metric_2026_09_11_user_abc: 123`) durumunda Elasticsearch küme durumu (Cluster State) yüz binlerce alan adıyla şişer. Bu durum JVM Heap çökmesine (OOM) yol açar. Prodüksiyonda `index.mapping.total_fields.limit` değeri (varsayılan 1000) kontrol altında tutulmalıdır.

## Adım Adım Uygulama Rehberi

### Adım 1: Küme Sağlığı ve Shard Tanılaması

Kümenin genel durumunu, JVM bellek kullanımını ve disk alanını analiz edin:

```bash
cd 07-pitfalls-and-production-tuning
./scripts/diagnose-cluster.sh
```

Terminalde şu komutla doğrudan atanmamış shard'ların nedenini sorgulayabilirsiniz:

```bash
curl -s -X POST "http://localhost:9200/_cluster/allocation/explain?pretty"
```

Çıktıda `unassigned_info.reason: "INDEX_CREATED"` ve `explanation: "cannot allocate because allocation is not permitted to any of the nodes"` ibaresi kopya shard için ikinci bir düğüm olmadığını gösterir.

### Adım 2: Tek Düğümlü Ortamda Kümeyi YEŞİL (GREEN) Yapma

Tek düğümlü lab ortamında tüm indekslerin `number_of_replicas` değerini 0'a çekerek gereksiz atanmamış shard'ları kaldırın:

```bash
./scripts/fix-yellow-cluster.sh
```

Doğrulama:
```bash
curl -s "http://localhost:9200/_cluster/health?pretty" | grep status
```
Çıktının `"status" : "green"` olduğunu görün.

### Adım 3: Disk Flood Stage Kilidini Çözme

Disk dolduğunda kilitlenen indekslerin yazma kilidini kaldırmak için:

```bash
./scripts/unlock-flood-stage.sh
```

Doğrulama için indeks ayarını kontrol edin:
```bash
curl -s "http://localhost:9200/*/_settings/index.blocks.read_only_allow_delete"
```
Herhangi bir indeks üzerinde blok kalmadığını doğrulayın.

### Adım 4: İndeks Yaşam Döngüsü (ILM) Politikası Tanımlama

Logların sonsuza dek disk doldurmasını önlemek için 1 gün veya 30 GB dolduğunda yeni indekse geçen (rollover), 7 gün sonra ise eski indeksleri otomatik silen bir ILM politikası oluşturun:

```bash
./scripts/configure-ilm-policy.sh
```

Politikanın Elasticsearch'e kaydedildiğini teyit edin:

```bash
curl -s "http://localhost:9200/_ilm/policy/devops_7day_retention?pretty"
```

## Doğal Doğrulama ve Beklenen Sonuç

1. Küme durumunun tamamen `green` olduğunu ve `unassigned_shards` değerinin `0` olduğunu doğrulayın:
   ```bash
   curl -s "http://localhost:9200/_cluster/health" | jq '{status: .status, unassigned: .unassigned_shards, active_shards: .active_shards}'
   ```
   Beklenen çıktı:
   ```json
   {
     "status": "green",
     "unassigned": 0,
     "active_shards": 5
   }
   ```

2. İndeks bazında shard dağılımını doğrulayın:
   ```bash
   curl -s "http://localhost:9200/_cat/shards?v"
   ```
   Tüm shard'ların `STARTED` durumunda olduğunu teyit edin.

## Temizlik

Test ILM politikasını kaldırmak isterseniz:

```bash
curl -s -X DELETE "http://localhost:9200/_ilm/policy/devops_7day_retention"
```
