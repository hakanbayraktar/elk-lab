# 🔍 Elastic Stack (ELK 8.x) Hands-on Lab Serisi

Bu çalışma serisi; Linux işletim sistemi temellerinden başlayarak Elasticsearch 8.x, Logstash, Kibana ve Filebeat bileşenlerinin kurulumunu, Linux sistem loglarının, çok dilli mikroservislerin, Docker konteynerlerinin ve Kubernetes küme loglarının merkezi olarak toplanmasını, Kibana görselleştirmelerini, SIEM güvenlik analizini ve prodüksiyon optimizasyonlarını uygulamalı olarak deneyimlemek için hazırlanmış uçtan uca pratik rehberidir.

---

## 🏛️ Mimari ve Çalışma Modeli

Bu laboratuvar serisinde **Aşamalı Tekil Yığın (Single-Stack Architecture)** prensibi uygulanır. Modül 00'da merkezi ELK omurgası tek bir Docker Compose dosyası ile ayağa kaldırılır. Ardından gelen her modülde bu omurgaya sırasıyla yeni bir log kaynağı bağlanır:

```text
                               ┌─────────────────────────────┐
                               │     Kibana UI (:5601)       │
                               │  (Discover, Lens, Dashboards│
                               │    KQL & Security SIEM)     │
                               └──────────────▲──────────────┘
                                              │
                               ┌──────────────┴──────────────┐
                               │  Elasticsearch Node (:9200) │
                               │  (Lucene Indeksleri, ILM)   │
                               └──────────────▲──────────────┘
                                              │
                     ┌────────────────────────┴────────────────────────┐
                     │            Logstash Pipeline (:5044 / :5000)    │
                     │         (Grok, JSON Codec, Mutate, Date)        │
                     └───────▲────────────────▲──────────────▲─────────┘
                             │                │              │
    ┌────────────────────────┴───────┐        │              │
    │                                │        │              │
┌───┴───────────────┐     ┌──────────┴─────┐  │  ┌───────────┴───────────────────┐
│  01-Linux Host    │     │ 02-Workspace   │  │  │ 04-Kubernetes Cluster (Kind)  │
│  auth.log, syslog │     │ Nginx & API    │  │  │ Pod logs, cri parser,         │
│  (Filebeat /var)  │     │ (Grok & JSON)  │  │  │ add_kubernetes_metadata       │
└───────────────────┘     └────────────────┘  │  └───────────────────────────────┘
                                              │
                                 ┌────────────┴────────────────┐
                                 │ 03-Docker Container Logs    │
                                 │ JSON File /var/run/docker   │
                                 │ add_docker_metadata         │
                                 └─────────────────────────────┘
```

---

## 📚 Laboratuvar Modül Haritası

| Dizin | Modül Adı | Seviye | Süre | Açık Portlar | Odak Alanı |
| :--- | :--- | :--- | :--- | :--- | :--- |
| [`00-elk-core-stack`](00-elk-core-stack/README.md) | **Merkezi ELK 8.x Kurulumu** | Başlangıç | 30 Dk | `9200`, `5601`, `5044`, `5000` | Elasticsearch, Logstash, Kibana, Docker Compose, `vm.max_map_count` |
| [`01-linux-system-logs`](01-linux-system-logs/README.md) | **Linux Sistem Logları** | Başlangıç | 25 Dk | `5601` | `auth.log`, `syslog`, Filebeat filestream, SSH oturum izleme |
| [`02-workspace-apps-logging`](02-workspace-apps-logging/README.md) | **Mikroservis Logları** | Orta | 30 Dk | `8081`, `3001`, `5601` | Nginx Combined Access Log (Grok), Node.js Express JSON API |
| [`03-docker-container-logs`](03-docker-container-logs/README.md) | **Docker Konteyner Logları** | Orta | 25 Dk | `5601` | Docker JSON Driver, `/var/run/docker.sock`, `add_docker_metadata` |
| [`04-kubernetes-cluster-logs`](04-kubernetes-cluster-logs/README.md) | **Kubernetes Küme Logları** | Orta | 35 Dk | `5601` | Filebeat DaemonSet, RBAC, CRI Parser, Çok Satırlı (Multiline) Hata Ayrıştırma |
| [`05-kibana-dashboards-and-kql`](05-kibana-dashboards-and-kql/README.md) | **Kibana, KQL & Panolar** | Başlangıç/Orta | 30 Dk | `5601` | KQL Filtreleme, Kibana Lens Görselleştirmeleri, Saved Objects İçe Aktarma |
| [`06-siem-and-security-analytics`](06-siem-and-security-analytics/README.md) | **Elastic SIEM & Güvenlik** | İleri | 35 Dk | `5601`, `5000` | SSH Kaba Kuvvet (Brute Force) Tespiti, Web Dizin Atlama (Path Traversal), ECS |
| [`07-pitfalls-and-production-tuning`](07-pitfalls-and-production-tuning/README.md) | **Prodüksiyon & Sorun Giderme** | İleri | 35 Dk | `9200`, `5601` | Sarı (YELLOW) Küme Teşhisi, Disk Flood Stage Kilidi Açma, 32GB JVM Kuralı, ILM |

---

## 🚀 Hızlı Başlangıç

### Seçenek A: Tek Komutla Uçtan Uca Otomatik Kurulum (Turnkey Setup)

Tüm ELK omurgasını, canlı mikroservisleri, 40.000+ örnek log verisini, 8 farklı Dashboard'u ve Data View'ları tek komutla kurmak için kök dizinden çalıştırın:

```bash
./setup-all.sh
```

Kurulum tamamlandığında Kibana arayüzüne tarayıcınızdan erişebilirsiniz:
👉 **Kibana Dashboard Merkezi:** [http://localhost:5601/app/dashboards](http://localhost:5601/app/dashboards)

Laboratuvarı tamamen kapatıp sıfırlamak için:
```bash
./teardown-all.sh
```

---

### Seçenek B: Adım Adım ve Anlayarak Kurulum (Eğitmen ve Sınıf Akışı)

Öğrencilerin mimariyi kavrayarak, her bir bileşenin görevini anlayarak ilerlemesi için adım adım kurulum akışı:

#### 1. Linux Çekirdek Bellek Parametresi (`vm.max_map_count`)
* **Neden Gerekli?** Elasticsearch, Lucene indeks dosyalarını yüksek hızda okuyup yazabilmek için doğrudan sanal bellek adreslerine haritalar (mmapfs). Linux'un varsayılan sınırı (`65530`) yetersiz kalarak `OutOfMemory` hatalarına neden olur.
* **Komut:**
  ```bash
  sudo sysctl -w vm.max_map_count=262144
  ```

#### 2. Çekirdek Elastic Stack Omurgasını Başlatma
* **Neden Gerekli?** Logların toplanması ve görselleştirilmesi için önce omurganın hazır olması gerekir: Elasticsearch (`:9200`), Logstash (`:5000/:5044`) ve Kibana (`:5601`).
* **Komut:**
  ```bash
  docker compose -f 00-elk-core-stack/docker-compose.yml up -d
  ```

#### 3. Küme ve Servis Sağlık Durumunu Doğrulama
* **Neden Gerekli?** Log boru hatlarını çalıştırmadan önce Elasticsearch'ün REST API üzerinden hazır (`green` veya `yellow`) olduğu doğrulanır.
* **Komut:**
  ```bash
  # Konteyner durumları
  docker compose -f 00-elk-core-stack/docker-compose.yml ps

  # Elasticsearch küme sağlığı
  curl -s http://localhost:9200/_cluster/health?pretty
  ```

#### 4. Canlı Örnek Mikroservisleri Başlatma
* **Neden Gerekli?** Gerçek bir DevOps ortamındaki gibi Nginx Web Sunucusu (`:8081`) ve Node.js Ödeme/Auth API'si (`:3001`) ayağa kaldırılarak gerçek HTTP istek ve hata logları üretilir.
* **Komut:**
  ```bash
  docker compose -f 02-workspace-apps-logging/sample-apps/docker-compose.apps.yml up -d
  ```

#### 5. Canlı Uygulama Trafiği ve Güvenlik Tehditleri Simülasyonu
* **Neden Gerekli?** Elasticsearch indekslerine canlı veriler düşmesi için hem meşru uygulama trafiği hem de kaba kuvvet (brute force) saldırıları simüle edilir.
* **Komut:**
  ```bash
  # 1. Nginx ve Node API'ye HTTP istekleri gönderir (200, 404, 500 kodları üretir)
  ./02-workspace-apps-logging/sample-apps/generate-and-ship-traffic.sh 30

  # 2. SSH Brute Force (T1110) ve Web Dizin Atlama (Path Traversal) saldırılarını enjekte eder
  ./06-siem-and-security-analytics/scripts/simulate-attacks.sh 10
  ```

#### 6. Yüksek Hacimli DevOps ve Küme Veri Setlerini İndeksleme
* **Neden Gerekli?** Kubernetes pod yaşam döngüsü (OOMKilled, CrashLoopBackOff), CI/CD build performansları ve mikroservis gecikmelerini içeren 40.000+ dokümanlık gerçekçi üretim verisi sisteme kazandırılır.
* **Komut:**
  ```bash
  python3 scripts/generate_rich_devops_datasets.py
  ```

#### 7. Kibana Veri Görünümleri (Data Views) ve 8 Dashboard'u Kaydetme
* **Neden Gerekli?** Kibana'nın oluşturulan indeksleri (`app-logs-*`, `system-logs-*`, `k8s-logs-*`, `cicd-logs-*`) okuyabilmesi ve öğrencilerin hazır 8 adet uzmanlık panosuna doğrudan erişebilmesi sağlanır.
* **Komut:**
  ```bash
  ./05-kibana-dashboards-and-kql/scripts/import-dashboards.sh
  ```

#### 8. Canlı Doğrulama ve Arayüzü Açma
* **Tarayıcıda Açın:**
  * 👉 **Dashboard Merkezi:** [http://localhost:5601/app/dashboards](http://localhost:5601/app/dashboards)
  * 👉 **Discover (Canlı Log Akışı):** [http://localhost:5601/app/discover](http://localhost:5601/app/discover)

---

## 🛡️ Prodüksiyon Kuralları ve En İyi Uygulamalar

1. **JVM %50 Kuralı ve 32 GB Sınırı:** Sunucu RAM'inin en fazla %50'si JVM heap'e (`-Xms = -Xmx`) ayrılır; kalan bellek OS Page Cache için bırakılır. Heap hiçbir zaman **32 GB**'ı aşmamalıdır (Compressed OOPs devre dışı kalır).
2. **Disk Watermark Koruması:** Disk doluluğu %95'e ulaştığında küme otomatik olarak `read_only_allow_delete: true` kilidine geçer. Disk temizlendikten sonra kilit `07-pitfalls-and-production-tuning/scripts/unlock-flood-stage.sh` ile kaldırılır.
3. **Temiz Yaşam Döngüsü:** Tüm lablar Docker Compose ve Kubernetes manifestleri ile izole edilmiştir. Çalışma bittiğinde ortam host üzerinde artık dosya bırakmadan `docker compose down -v` ile tamamen sıfırlanabilir.
