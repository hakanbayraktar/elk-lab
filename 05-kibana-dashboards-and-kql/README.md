# LAB-ELK-05 — Kibana Arayüzü, KQL Sorguları ve Görselleştirme Panoları

| Seviye | Tahmini Süre | Profil / Araçlar | Açık Portlar |
| :--- | :--- | :--- | :--- |
| Başlangıç / Orta | 30 Dakika | Kibana 8.x, Lens, KQL (Kibana Query Language) | 5601 (Kibana) |

[LAB-ELK-05.zip](LAB-ELK-05.zip)

## Amaç

- Kibana 8 arayüzünde Data View (İndeks Kalıbı) tanımlamak.
- KQL (Kibana Query Language) sözdizimi ile yapılandırılmış loglar üzerinde gelişmiş filtreleme ve arama yapmak.
- Kibana Lens aracı ile zaman serisi, pasta/halka (donut) ve sayısal metrik görselleştirmeleri üretmek.
- Üretilen grafikleri tek bir operasyonel panoda (Dashboard) birleştirmek ve dışa/içe aktarmak (`Saved Objects`).

## Ön Koşullar

- `00-elk-core-stack` servislerinin ayakta olması (`http://localhost:5601`).
- Önceki lablarda toplanan logların Elasticsearch'te bulunması (`app-logs-*`, `filebeat-*`, `system-logs-*`).

## KQL (Kibana Query Language) Referans Rehberi

KQL, kullanıcı dostu ve otomatik tamamlama (autocomplete) destekli modern sorgu dilidir.

| Senaryo | KQL Sözdizimi Örneği | Açıklama |
| :--- | :--- | :--- |
| **Alan Değeri Eşleşmesi** | `response_code : 200` | `response_code` alanı tam 200 olanlar |
| **Metin Eşleşmesi** | `message : "Failed password"` | `message` içinde geçen kelimeleri arar |
| **Mantıksal VE (AND)** | `response_code >= 400 and method : "POST"` | 400 üzeri ve POST olan istekler |
| **Mantıksal VEYA (OR)** | `response_code : 500 or response_code : 502` | 500 veya 502 olan kayıtlar |
| **Olumsuzlama (NOT)** | `not response_code : 200` | Başarılı (200) olmayan tüm kayıtlar |
| **Joker Karakter (Wildcard)** | `url : "/api/v1/*"` | Belirli bir URL ön ekiyle başlayanlar |
| **Alan Varlığı Kontrolü** | `error : *` | `error` alanı mevcut ve dolu olanlar |
| **Kubernetes Filtresi** | `kubernetes.pod.name : payment-* and kubernetes.namespace : "default"` | Belirli pod ve namespace kayıtları |

## Adım Adım Uygulama Rehberi

### Adım 1: Data View (Veri Görünümü) Tanımlama

Kibana'nın Elasticsearch indekslerini okuyabilmesi için Data View tanımlanmalıdır:

1. Tarayıcıdan `http://localhost:5601` adresine gidin.
2. Sol menüden **Stack Management > Data Views** adımlarını izleyin.
3. **Create data view** butonuna tıklayın:
   - **Name:** `Application Logs`
   - **Index pattern:** `app-logs-*`
   - **Timestamp field:** `@timestamp`
4. **Save data view to Kibana** butonuna basarak kaydedin.
5. Benzer şekilde `filebeat-*` ve `system-logs-*` indeksleri için de Data View oluşturabilirsiniz.

*(Not: Bu işlemi otomatikleştirmek için `scripts/import-dashboards.sh` betiğini çalıştırabilirsiniz).*

### Adım 2: Kibana Discover ile Log İnceleme ve Güvenlik Avcılığı (Threat Hunting)

Logların canlı analizi, hata ayıklama ve siber güvenlik araştırmaları **Kibana Discover** ekranında yürütülür:
👉 **Kibana Discover Arayüzü:** [http://localhost:5601/app/discover](http://localhost:5601/app/discover)

Öğrencilere sınıfta gösterilebilecek 4 pratik inceleme senaryosu:

#### 1. Senaryo: SSH Kaba Kuvvet (Brute-Force) Saldırı Analizi
1. Sol üstteki Veri Görünümünden **`Linux System Logs (Auth & Syslog)`** seçin.
2. Sağ üstten zaman aralığını **`Last 24 hours`** yapın.
3. KQL arama çubuğuna şu sorguyu girin:
   ```kql
   message : "Failed password"
   ```
4. **Gözlem:** Saldırganın (`198.51.100.77`) sırayla `root`, `admin`, `ubuntu`, `deploy`, `oracle` hesaplarını ele geçirmek için yaptığı başarısız denemeleri anlık olarak listeleyin.

#### 2. Senaryo: Web Dizin Atlama (Path Traversal) ve SQL Injection Tespiti
1. Veri Görünümünü **`Application Logs (Nginx & API)`** olarak değiştirin.
2. KQL arama çubuğuna şu sorguyu girin:
   ```kql
   url : *../* or url : */etc/passwd* or url : *UNION*
   ```
3. Sol menüden `client_ip`, `method`, `url`, `response_code` alanlarını sütun olarak ekleyin (`+` simgesi).
4. **Gözlem:** Saldırganın sistem dosyalarını okumaya veya SQL injection yapmaya çalıştığını ve web sunucusunun `404` yanıtı vererek isteği engellediğini görün.

#### 3. Senaryo: Kubernetes Kümesinde OOMKilled ve CrashLoopBackOff Olayları
1. Veri Görünümünü **`Kubernetes Pod & Cluster Logs`** yapın.
2. KQL sorgusu:
   ```kql
   event.reason : "OOMKilled" or event.reason : "CrashLoopBackOff"
   ```
3. **Gözlem:** Aşırı bellek tüketen konteynerlerin cgroup sınırını aştığı için Linux çekirdeği tarafından sonlandırıldığını teşhis edin.

#### 4. Senaryo: CI/CD Pipeline Hata Analizi
1. Veri Görünümünü **`CI/CD Pipelines (Jenkins & GitLab)`** yapın.
2. KQL sorgusu:
   ```kql
   ci.status : "FAILED"
   ```
3. **Gözlem:** Hangi pipeline aşamasında (`trivy-container-scan`, `unit-test`) derlemenin başarısız olduğunu ve sürelerini inceleyin.

---

### Adım 3: Manuel Olarak Sample Data (Örnek Veri Seti) Ekleme ve Kaldırma

Kibana, öğrencilerin öğrenmesini hızlandırmak için 3 hazır endüstriyel veri seti sunar:

* **Kibana Arayüzünden (UI):**
  1. Sol üstteki Elastic logosuna tıklayarak ana sayfaya gidin (`http://localhost:5601`).
  2. Sayfanın en altındaki **Try sample data** bağlantısına tıklayın.
  3. Açılan sayfada 3 kart göreceksiniz:
     - **Sample eCommerce orders:** E-ticaret satış, sepet ve ürün analizleri.
     - **Sample flight data:** Küresel uçuş gecikmeleri, rotalar ve hava durumu.
     - **Sample web logs:** Apache/Nginx web erişim logları, GeoIP ve işletim sistemi dökümleri.
  4. İstediğiniz kartın altındaki **Add data** butonuna basın. Kibana otomatik olarak hem indeksi oluşturur hem de hazır panoları yükler.
  5. Kaldırmak istediğinizde aynı butonda çıkan **Remove** seçeneğine tıklamanız yeterlidir.

* **API Üzerinden (Terminalden):**
  ```bash
  # Web logları ekleme:
  curl -s -X POST "http://localhost:5601/api/sample_data/logs" -H 'kbn-xsrf: true'

  # E-ticaret verilerini ekleme:
  curl -s -X POST "http://localhost:5601/api/sample_data/ecommerce" -H 'kbn-xsrf: true'

  # Uçuş verilerini ekleme:
  curl -s -X POST "http://localhost:5601/api/sample_data/flights" -H 'kbn-xsrf: true'
  ```

---

### Adım 4: Manuel Olarak Sıfırdan Dashboard ve Görselleştirme Tasarımı

1. Sol menüden **Analytics > Dashboard** bölümüne gidin ve **Create dashboard** butonuna tıklayın.
2. **Create visualization** butonuna tıklayarak **Lens** editörünü açın.
3. **Grafik 1: Zaman Serisi Çubuk Grafik (HTTP Durum Kodları)**
   - Sağ üstteki veri görünümü seçicisinden `Application Logs (Nginx & API)` seçin.
   - Sol taraftaki alan listesinden `@timestamp` alanını yatay eksene (**Horizontal axis**) sürükleyin.
   - Sol taraftan `Records` alanını düşey eksene (**Primary metric**) sürükleyin.
   - `response_code` alanını sürükleyip **Break down by** alanına bırakın.
   - Sağ üstten **Save and return** butonuna basarak panoya ekleyin.
4. **Grafik 2: Pasta / Halka Grafik (HTTP Metot Dağılımı)**
   - Panonun üstündeki **Create visualization** butonuna tekrar tıklayın.
   - Grafik türünü (sağ üst) **Donut** (Halka) yapın.
   - `method` alanını sürükleyip **Slice by** alanına bırakın.
   - **Save and return** ile panoya ekleyin.
5. **Panel 3: Canlı Log Tablosu Ekleme (Saved Search)**
   - Panonun üstündeki **Add from library** butonuna tıklayın.
   - Arama kutusuna `Live Application Log Stream` yazıp seçin. Panonun altına anlık olarak canlı logların aktığı renkli bir veri tablosu eklenecektir.
6. Panonun sağ üstündeki **Save** butonuna basarak başlığı `DevOps Operasyonel Pano` olarak kaydedin.

---

### Adım 5: Canlı Çalışan 8 Panoyu Açma (Doğrudan Bağlantılar)

Sistemde hazır ve canlı verilerle beslenmiş 8 adet pano bulunmaktadır:

| No | Pano Adı | Doğrudan Erişim Bağlantısı | Kapsam ve Açıklama |
|:---:|:---|:---|:---|
| 1 | **DevOps Unified Dashboard** | [Aç](http://localhost:5601/app/dashboards#/view/devops-ops-overview) | HTTP yanıt kodları, en çok istek alan URL'ler, saldırgan IP'ler ve canlı log akışı |
| 2 | **Microservices & API Observability** | [Aç](http://localhost:5601/app/dashboards#/view/devops-microservices-observability) | Servis bazında gecikme (latency), hata dağılımı ve mikroservis erişim tablosu |
| 3 | **Kubernetes Cluster & Pods** | [Aç](http://localhost:5601/app/dashboards#/view/k8s-cluster-pod-health) | OOMKilled, CrashLoopBackOff olayları, namespace log hacmi ve canlı Pod log dökümü |
| 4 | **CI/CD Pipeline Performance** | [Aç](http://localhost:5601/app/dashboards#/view/cicd-pipeline-performance) | Jenkins & GitLab build başarı/başarısızlık trendleri, aşama süreleri ve hata analizi |
| 5 | **Security & Threat Hunting** | [Aç](http://localhost:5601/app/dashboards#/view/security-siem-threat-center) | MITRE ATT&CK T1110 SSH kaba kuvvet analizi, firewall drop kayıtları ve SIEM günlüğü |
| 6 | **Official Web Logs Traffic** | [Aç](http://localhost:5601/app/dashboards#/view/edf84fe0-e1a0-11e7-b6d5-4dc382ef7f5b) | Resmi web erişim trafiği, coğrafi dünya haritası ve bant genişliği dağılımı |
| 7 | **Official E-Commerce Orders** | [Aç](http://localhost:5601/app/dashboards#/view/722b74f0-b882-11e8-a6d9-e546fe2bba5f) | Resmi e-ticaret sipariş hacimleri, satış gelirleri ve müşteri segmentasyonu |
| 8 | **Official Global Flights** | [Aç](http://localhost:5601/app/dashboards#/view/7adfa750-4c81-11e8-b3d7-01146121b73d) | Küresel uçuş gecikmeleri, havayolu analizleri ve hava durumu korelasyonu |

---

### Adım 6: Otomasyon Scriptleri ile Tüm Altyapıyı Kurma

İleride tüm veri setlerini ve 8 panoyu tek komutla baştan kurmak için:

```bash
# 1. 40.000+ yüksek hacimli DevOps, K8s, CI/CD ve Güvenlik logunu üretir
python3 scripts/generate_rich_devops_datasets.py

# 2. Tüm Data View'ları, Lens grafiklerini ve 8 panoyu Kibana'ya aktarır
./05-kibana-dashboards-and-kql/scripts/import-dashboards.sh
```

---

## Doğal Doğrulama ve Beklenen Sonuç

1. Terminalden kayıtlı pano sayısını doğrulayın:
   ```bash
   curl -s -X GET "http://localhost:5601/api/saved_objects/_find?type=dashboard&per_page=20" -H "kbn-xsrf: true" | jq '.saved_objects[].attributes.title'
   ```
   *Çıktıda 8 panonun tamamının listelendiğini teyit edin.*

2. Tarayıcıdan `http://localhost:5601/app/dashboards` sayfasına gidin ve panoların sıfır hata ile açıldığını doğrulayın.

---

## Temizlik

Oluşturulan Data View veya Saved Object'leri temizlemek isterseniz:
1. **Stack Management > Saved Objects** menüsünden ilgili dashboard veya data view'ları seçip **Delete** diyebilirsiniz.

