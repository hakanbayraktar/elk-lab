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

### 1. Sistem Çekirdek Parametresinin Ayarlanması (Önemli)

Elasticsearch mmap sistem çağrısı sınırının Linux çekirdeğinde en az 262144 olmasını şart koşar:

```bash
sudo sysctl -w vm.max_map_count=262144
```

### 2. Merkezi ELK Omurgasının Başlatılması

```bash
cd 00-elk-core-stack
docker compose up -d
```

Servislerin sağlık durumunu kontrol edin:

```bash
docker compose ps
curl -s http://localhost:9200/_cluster/health?pretty
```

Durum `"green"` veya `"yellow"` olduğunda Kibana arayüzüne tarayıcınızdan erişebilirsiniz:
👉 **`http://localhost:5601`**

---

## 🛡️ Prodüksiyon Kuralları ve En İyi Uygulamalar

1. **JVM %50 Kuralı ve 32 GB Sınırı:** Sunucu RAM'inin en fazla %50'si JVM heap'e (`-Xms = -Xmx`) ayrılır; kalan bellek OS Page Cache için bırakılır. Heap hiçbir zaman **32 GB**'ı aşmamalıdır (Compressed OOPs devre dışı kalır).
2. **Disk Watermark Koruması:** Disk doluluğu %95'e ulaştığında küme otomatik olarak `read_only_allow_delete: true` kilidine geçer. Disk temizlendikten sonra kilit `07-pitfalls-and-production-tuning/scripts/unlock-flood-stage.sh` ile kaldırılır.
3. **Temiz Yaşam Döngüsü:** Tüm lablar Docker Compose ve Kubernetes manifestleri ile izole edilmiştir. Çalışma bittiğinde ortam host üzerinde artık dosya bırakmadan `docker compose down -v` ile tamamen sıfırlanabilir.
