# LAB-ELK-07 — Prodüksiyon İpuçları, Shard Yönetimi ve Sorun Giderme

| Seviye | Profil / Araçlar | Açık Portlar |
|:---:|:---:|:---:|
| İleri | Elasticsearch Admin API, cURL, jq, ILM | 9200 (ES), 15601 (Kibana) |

[LAB-ELK-07.zip](LAB-ELK-07.zip)

> [!IMPORTANT]
> **DİKKAT: `00-elk-core-stack` AÇIK KALMALIDIR!**
> Bu laboratuvardaki küme sağlığı, replica optimizasyonu, disk kilidi açma ve ILM operasyonları doğrudan `00-elk-core-stack` üzerinde çalışan canlı Elasticsearch kümesi üzerinde icra edilir. Bu nedenle 00 labındaki servisleri **kesinlikle durdurmayın veya silmeyin**.

---

## Amaç
* Elasticsearch küme sağlığı durumlarını (`green`, `yellow`, `red`) ve atanmamış shard (`unassigned shard`) nedenlerini analiz etmek.
* Tek düğümlü (single-node) ortamlarda kopya (replica) sayısını 0'a çekerek küme sağlığını `YELLOW` durumundan `GREEN` durumuna getirmek.
* Disk doluluğunda devreye giren ve Elasticsearch'e yeni veri yazılmasını engelleyen `disk watermark flood_stage` kilidini teşhis edip açmak.
* Prodüksiyon ortamlarında JVM %50 kuralı ve 32 GB Compressed OOPs bellek sınırının önemini kavramak.
* İndeks Yaşam Döngüsü Yönetimi (ILM - Index Lifecycle Management) ile 7 günlük otomatik indeks rotasyonu ve saklama politikası oluşturmak.

---

## Ön Koşullar
* **Merkezi ELK Omurgası:** `00-elk-core-stack` servislerinin (`elasticsearch`, `kibana`) çalışır durumda olması gereklidir.
* Terminalde `curl` ve `jq` araçlarının bulunması.
* Kimlik Doğrulama: Kullanıcı: `elastic` | Şifre: `BilginIT454` | Port: `15601`.

---

## Kritik Prodüksiyon Mimarisi ve Tuzaklar

### 1. Küme Sağlığı Neden Sarı (YELLOW) Olur?
Elasticsearch'te varsayılan olarak her indeks 1 birincil (primary) ve 1 kopya (replica) shard ile oluşturulur. Tek düğümlü (single-node) bir ortamda kopya shard'ın atanabileceği ikinci bir düğüm bulunamadığı için küme durumu `YELLOW` olur. Herhangi bir veri kaybı yoktur ancak yüksek erişilebilirlik (HA) sağlanamaz.

### 2. Disk Watermark Kademeleri (%85, %90, %95)
Elasticsearch disk doluluk oranını 3 eşikle takip eder:
* **Low Watermark (%85):** Yeni indeks shard'ları bu düğüme atanmaz.
* **High Watermark (%90):** Shard'lar diğer düğümlere taşınmaya çalışılır.
* **Flood Stage (%95):** Kümedeki tüm indeksler otomatik olarak salt-okunur (`read_only_allow_delete`) moda kilitlenir. Yeni veri yazılamaz ve `429 Too Many Requests` döner. Disk boşalsa dahi bu kilit komut verilene kadar kalkmaz!

### 3. JVM %50 Kuralı ve 32 GB Sınırı
* Sunucu RAM'inin en fazla %50'si Elasticsearch JVM Heap'ine (`-Xms` ve `-Xmx`) ayrılmalıdır. Kalan %50 RAM, Linux işletim sisteminin dosya önbelleği (OS Page Cache / Lucene) için boş bırakılmalıdır.
* JVM Heap boyutu asla **32 GB** sınırını aşmamalıdır (Önerilen: en fazla `31GB`). 32 GB aşıldığında Java sanal makinesi bellek tasarrufu sağlayan **Compressed OOPs (Ordinary Object Pointers)** özelliğini kapatır ve 64-bit tam işaretçilere geçer; bu da bellek kullanımını gereksiz %40 artırır.

---

## Adım Adım Uygulama Rehberi

### Adım 1: Küme Sağlığını ve Shard Durumunu Teşhis Edin

Kümenin genel durumunu, JVM bellek kullanımını ve disk alanını analiz eden tanı betiğini çalıştırın:

```bash
cd ~/elk-lab/07-pitfalls-and-production-tuning
./scripts/diagnose-cluster.sh
```

Atanmamış shard'ların nedenini doğrudan Elasticsearch API'sine sorun:

```bash
curl -s -u elastic:BilginIT454 -X POST "http://localhost:9200/_cluster/allocation/explain?pretty"
```

*Çıktıda `unassigned_info.reason: "INDEX_CREATED"` ve `cannot allocate because allocation is not permitted to any of the nodes` ibaresini göreceksiniz.*

---

### Adım 2: Tek Düğümlü Ortamda Kümeyi YEŞİL (GREEN) Yapın

Tek düğümlü lab ortamında tüm indekslerin replica sayısını 0'a çekerek gereksiz bekleyen shard'ları kaldırın:

```bash
./scripts/fix-yellow-cluster.sh
```

Doğrulama için küme durumunu sorgulayın:

```bash
curl -s -u elastic:BilginIT454 "http://localhost:9200/_cluster/health?pretty" | grep status
```

* **Beklenen Sonuç:** `"status" : "green"`

---

### Adım 3: Disk %95 Dolduğunda Kilitlenen Flood Stage Kilidini Açın

Eğer sunucu diski dolduğu için indeksler salt-okunur duruma kilitlenmişse, kilidi açmak için hazırlanan scripti çalıştırın:

```bash
./scripts/unlock-flood-stage.sh
```

İndeks ayarından kilidin kaldırıldığını teyit edin:

```bash
curl -s -u elastic:BilginIT454 "http://localhost:9200/*/_settings/index.blocks.read_only_allow_delete"
```

---

### Adım 4: 7 Günlük İndeks Yaşam Döngüsü (ILM) Politikası Tanımlayın

Logların diski sınırsız doldurmasını engellemek için 1 gün veya 30 GB dolduğunda yeni indekse geçen (rollover), 7 gün sonra ise eski indeksleri otomatik silen ILM politikasını tanımlayın:

```bash
./scripts/configure-ilm-policy.sh
```

Politikanın Elasticsearch'e başarıyla kaydedildiğini doğrulayın:

```bash
curl -s -u elastic:BilginIT454 "http://localhost:9200/_ilm/policy/devops_7day_retention?pretty"
```

---

## Doğal Doğrulama ve Beklenen Sonuç

1. **Yeşil Küme ve 0 Atanmamış Shard:**
   ```bash
   curl -s -u elastic:BilginIT454 "http://localhost:9200/_cluster/health" | jq '{status: .status, unassigned_shards: .unassigned_shards, active_shards: .active_shards}'
   ```
   * **Beklenen Çıktı:** `status: "green"`, `unassigned_shards: 0`

2. **Shard Detay Listesi:**
   ```bash
   curl -s -u elastic:BilginIT454 "http://localhost:9200/_cat/shards?v"
   ```

---

## Temizlik

Test ILM politikasını temizlemek için:

```bash
curl -s -u elastic:BilginIT454 -X DELETE "http://localhost:9200/_ilm/policy/devops_7day_retention"
```

---

## Tüm Eğitim Bitiminde Tam Temizlik

Tüm ELK eğitim modüllerini (00'dan 07'ye kadar) tamamladığınızda, ayrılan sistem kaynaklarını ve Docker konteynerlarını serbest bırakmak için kök dizindeki temizlik betiğini çalıştırın:

```bash
cd ~/elk-lab
./teardown-all.sh
```

*Bu komut yalnızca ELK eğitimine ait konteyner ve birimleri kaldırır; Kind Kubernetes kümenize veya diğer projelere dokunmaz.*
