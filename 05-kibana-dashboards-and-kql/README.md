# LAB-ELK-05 — Kibana Arayüzü, KQL Sorguları ve Görselleştirme Panoları

| Seviye | Profil / Araçlar | Açık Portlar |
|:---:|:---:|:---:|
| Başlangıç / Orta | Kibana 8.x, Lens, KQL, Saved Objects | 9200 (ES), 15601 (Kibana) |

[LAB-ELK-05.zip](LAB-ELK-05.zip)

## Amaç
* Kibana 8 modern web arayüzünde Data View (Veri Görünümü / İndeks Kalıbı) tanımlamak ve alan eşlemelerini incelemek.
* KQL (Kibana Query Language) sözdizimi ile yapılandırılmış loglar üzerinde boolean mantık (`and`, `or`, `not`), joker karakter (`*`) ve sayısal eşik sorguları gerçekleştirmek.
* Kibana Lens arayüzünü kullanarak sürükle-bırak yöntemiyle zaman serisi (XY Chart), çubuk (Bar Chart) ve pasta/halka (Donut) grafikleri üretmek.
* Üretilen grafikleri merkezi bir operasyonel panoda (Dashboard) birleştirmek ve dışa/içe aktarmak (`Saved Objects`).
* Hazırlanan otomatik aktarım betiği (`import-dashboards.sh`) ile DevOps, Kubernetes ve SIEM operasyonel panolarını tek adımda sisteme yüklemek.

---

## Ön Koşullar
* **Merkezi ELK Omurgası:** `00-elk-core-stack` servislerinin (`elasticsearch`, `kibana`) çalışır durumda olması.
* Önceki laboratuvarlarda Elasticsearch'e aktarılan logların bulunması (`system-logs-*`, `app-logs-*`, `k8s-logs-*`, `docker-containers-*`).
* Kimlik Doğrulama: Kullanıcı: `elastic` | Şifre: `BilginIT454`.

---

## Mimari ve Çalışma Modeli

```text
[ Elasticsearch İndeksleri (:9200) ]
(system-logs-*, app-logs-*, k8s-logs-*, docker-containers-*)
                    │
                    ▼ (Kibana REST API / Basic Auth)
       [ Kibana Veri Katmanı ]
       ├── Data Views (Index Patterns)
       ├── Saved Searches (Tablolar)
       └── Lens Visualizations (Grafikler)
                    │
                    ▼
       [ Kibana Dashboards (:15601) ]
       ├── 1. Core Altyapı ve Sistem Genel Bakış
       ├── 2. DevOps Observability & Security Dashboard
       ├── 3. Kubernetes Küme ve Pod Sağlık Panosu
       └── 4. Resmi Örnek Veri Setleri (E-Commerce, Web Logs, Flights)
```

---

## KQL (Kibana Query Language) Hızlı Referans Rehberi

KQL, arama yaparken otomatik tamamlama (autocomplete) sunan modern sorgulama dilidir:

| Senaryo | Örnek KQL Sözdizimi | Açıklama |
| :--- | :--- | :--- |
| **Alan Değeri Eşleşmesi** | `response_code : 200` | Yanıt kodu tam 200 olan istekler |
| **Metin Araması** | `message : "Failed password"` | Mesaj içinde anahtar kelimeleri arar |
| **Mantıksal VE (AND)** | `service : "payment-api" and response_code >= 400` | Belirli servisteki hataları filtreler |
| **Mantıksal VEYA (OR)** | `response_code : 500 or response_code : 502` | Sunucu taraflı 5xx hatalarını yakalar |
| **Olumsuzlama (NOT)** | `not response_code : 200` | Başarılı olmayan tüm kayıtlar |
| **Joker Karakter (*)** | `url : "/api/v1/*"` | Belirli bir URL ön ekiyle başlayan istekler |
| **Güvenlik / SQLi** | `url : *../* or url : *UNION*` | Dizin atlatma ve SQL injection denemeleri |

---

## Adım Adım Uygulama Rehberi

### 1. Kibana Arayüzüne Bağlanma

Tarayıcınızdan Kibana paneline gidin:
* **URL:** `http://<SUNUCU_IP>:15601` veya `https://studentXX-kibana.devopsatolyesi.com`
* **Giriş Bilgileri:** Kullanıcı: `elastic` | Şifre: `BilginIT454`

Sol menüden **Analytics > Discover** bölümünü açın.

---

### 2. Discover Ekranında 4 Temel Analiz Senaryosu

1. **Senaryo A: Başarısız SSH Oturum Girişleri (Güvenlik Analizi):**
   * Veri Görünümünden **`Linux Sistem Logs (Auth & Syslog)`** seçin.
   * Zaman aralığını **Last 24 hours** yapın.
   * KQL Sorgusu: `message : "Failed password"`
2. **Senaryo B: Web Sunucusunda Şüpheli URL Taramaları:**
   * Veri Görünümünden **`Application Logs (Nginx & API)`** seçin.
   * KQL Sorgusu: `response_code >= 400 and method : "GET"`
3. **Senaryo C: Kubernetes Pod Hata Taraması:**
   * Veri Görünümünden **`Kubernetes Pod & Cluster Logs`** seçin.
   * KQL Sorgusu: `message : "Traceback" or message : "ERROR"`
4. **Senaryo D: Konteyner İsimlerine Göre Filtreleme:**
   * Veri Görünümünden **`Docker Konteyner Durumları`** seçin.
   * KQL Sorgusu: `container.name : "elasticsearch" or container.name : "kibana"`

---

### 3. Kibana Lens ile Adım Adım Görselleştirme Oluşturma

1. Sol menüden **Analytics > Dashboard** seçeneğine tıklayın.
2. Sağ üstten **Create dashboard** butonuna basın.
3. **Create visualization** butonuna tıklayarak Kibana Lens ekranına geçin.
4. Sol üstten Data View olarak **`Application Logs (Nginx & API)`** seçin.
5. Sol paneldeki alan listesinden `response_code` alanını tutup ortadaki geniş alana sürükleyip bırakın.
6. Sağ üstteki grafik türünden **Donut (Halka)** seçin.
7. Grafiğin başlığını **"HTTP Yanıt Kodları Dağılımı"** olarak belirleyin ve sağ üstten **Save and return** butonuna basarak panoya ekleyin.
8. Panonuzu sağ üstteki **Save** butonuna basarak **"Operasyonel İzleme Panom"** adıyla kaydedin.

---

### 4. Hazır Panoları Script ile Tek Komutta İçe Aktarma

Tüm hazır DevOps, Kubernetes, CI/CD ve SIEM panolarını otomatik yüklemek için hazırlanan scripti çalıştırın:

```bash
cd ~/elk-lab/05-kibana-dashboards-and-kql
./scripts/import-dashboards.sh
```

Bu script sırasıyla:
* Resmi Elastic örnek veri setlerini (`logs`, `ecommerce`, `flights`) yükler.
* Tüm standart Data View'ları tanımlar.
* Lens grafiklerini ve **DevOps Observability & Security Dashboard** panosunu oluşturur.

---

## Doğal Doğrulama ve Beklenen Sonuç

Kibana'da **Analytics > Dashboard** listesini açın. Aşağıdaki panoların listelendiğini ve tıklandığında grafiklerin dolu olarak açıldığını doğrulayın:

* 👉 **DevOps Altyapı Panosu:** `http://<SUNUCU_IP>:15601/app/dashboards#/view/devops-ops-overview`
* 👉 **Çekirdek Sistem Panosu:** `http://<SUNUCU_IP>:15601/app/dashboards#/view/core-infrastructure-overview`
* 👉 **Resmi Web Trafik Panosu:** `http://<SUNUCU_IP>:15601/app/dashboards#/view/edf84fe0-e1a0-11e7-b6d5-4dc382ef7f5b`

---

## Temizlik

Bu laboratuvar bir görselleştirme ve analiz modülüdür; arka planda çalışan ayrı bir ajan bulunmadığından herhangi bir konteyneri kapatmanız gerekmez.

> **Önemli Not:** Merkezi ELK omurgası (`00-elk-core-stack`), sonraki SIEM ve Sorun Giderme laboratuvarları için açık kalmalıdır.
