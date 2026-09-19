# LAB-ELK-04 — Kubernetes Cluster ve Pod Loglarının Toplanması

| Seviye | Profil / Araçlar | Açık Portlar |
| :--- | :--- | :--- |
| Orta (Intermediate) | Kubernetes (Kind/Minikube/K8s), Filebeat DaemonSet, Kibana | 15601 / 5601 (Kibana), 5044 (Logstash) |

---

## Amaç

- Kubernetes podlarının standart çıktı (`stdout`/`stderr`) akışlarını `Filebeat DaemonSet` ile küme seviyesinde otomatik olarak toplamak.
- `add_kubernetes_metadata` işlemcisi ile loglara pod adı, namespace, container adı, node adı ve etiket (label) bilgilerini otomatik olarak eklemek.
- Çok satırlı (multiline) hata yığınlarını (Python/Java stack traces) tek bir log olayında birleştirmek (`multiline regex`).
- Kibana Discover üzerinde pod bazlı filtreleme (`kubernetes.pod.name`, `kubernetes.namespace`) ve KQL sorguları gerçekleştirmek.

---

## Ön Koşullar ve Bağımlılıklar

- **Merkezi Omurga:** `00-elk-core-stack` modülündeki Elasticsearch, Logstash ve Kibana servislerinin çalışıyor olması gerekmektedir.
- **Mevcut Kind Kümesi:** Önceki günlerden gelen mevcut Kind Kubernetes kümesi (`kubectl get nodes` çıktısının Ready dönmesi). Yeni bir küme kurulmaz; mevcut küme kesinlikle **silinmemelidir**.
- Küme içinden host üzerindeki Logstash portuna (`5044`) erişim (Kind için standart bridge gateway IP'si: `172.17.0.1` veya host IP).

---

## Mimari ve Çalışma Modeli

```text
+-------------------------------------------------------------------------------+
| Kubernetes Cluster (Kind / Minikube / K3s)                                    |
|                                                                               |
|  [payment-service Pod]              [other-app Pod]                           |
|         │ (stdout/stderr)                  │                                  |
|         ▼                                  ▼                                  |
|  /var/log/pods/...                  /var/log/pods/...                         |
|  /var/log/containers/*.log          /var/log/containers/*.log                 |
|         │                                  │                                  |
|         +──────────────────┬───────────────+                                  |
|                            ▼                                                  |
|               [Filebeat DaemonSet (Node)]                                     |
|                 - CRI log parser                                              |
|                 - multiline parser (stack traces)                             |
|                 - add_kubernetes_metadata (K8s API)                           |
+────────────────────────────┼──────────────────────────────────────────────────+
                             │ (Beats TCP :5044)
                             ▼
              [Logstash Pipeline (Host :5044)]
                             │
                             ▼
              [Elasticsearch (Host :9200)] ──► [Kibana UI (:15601 / :5601)]
```

---

## Adım Adım Uygulama Rehberi

### Adım 1: Host ve Ağ Yapılandırmasının Belirlenmesi

Kubernetes DaemonSet podlarının host üzerindeki Logstash'e erişebilmesi için gateway IP adresini teyit edin:

```bash
# Docker bridge ağının gateway IP adresini öğrenin (genellikle 172.17.0.1)
docker network inspect bridge --format='{{range .IPAM.Config}}{{.Gateway}}{{end}}'
```

Eğer Kind kullanıyorsanız `kind` ağı gateway IP adresini de kontrol edebilirsiniz:

```bash
docker network inspect kind --format='{{range .IPAM.Config}}{{.Gateway}}{{end}}' 2>/dev/null || true
```

### Adım 2: Filebeat DaemonSet ve RBAC Kurulumu

Filebeat'in Kubernetes API'sinden pod metadata çekebilmesi için gerekli RBAC izinleri, ConfigMap ve DaemonSet nesnesini oluşturun:

```bash
kubectl apply -f filebeat-kubernetes-daemonset.yaml
```

DaemonSet podlarının durumunu kontrol edin:

```bash
kubectl get pods -n logging -l app=filebeat -o wide
```

Pod loglarını izleyerek Logstash bağlantısının başarılı olduğunu doğrulayın:

```bash
kubectl logs -n logging -l app=filebeat --tail=50
```

Çıktıda `Connection to backoff(async(tcp://...:5044)) established` ibaresi görülmelidir.

### Adım 3: Örnek Multiline Uygulamasının Dağıtımı

Hem normal JSON logları hem de Python stack trace hata logları üreten örnek mikroservisi devreye alın:

```bash
kubectl apply -f multiline-app-deployment.yaml
```

Uygulamanın çalıştığını ve log ürettiğini kontrol edin:

```bash
kubectl get deployment payment-service-demo
kubectl logs -l app=payment-service --tail=20
```

### Adım 4: Filebeat Multiline Birleştirme Mantığı

`filebeat-kubernetes-daemonset.yaml` içinde tanımlanan şu kural:

```yaml
parsers:
  - container:
      stream: all
      format: auto
  - multiline:
      type: pattern
      pattern: '^[0-9]{4}-[0-9]{2}-[0-9]{2}|^\\[[0-9]{4}-[0-9]{2}-[0-9]{2}'
      negate: true
      match: after
```

Tarih damgasıyla (`YYYY-MM-DD` veya `[YYYY-MM-DD`) başlamayan satırları (örneğin Python `Traceback`, `File ...`, `ZeroDivisionError`) önceki log satırının devamı olarak kabul eder ve tek bir Elastic belgesinde birleştirir.

---

## Doğal Doğrulama ve Beklenen Sonuç

### 1. Elasticsearch İndeks Kontrolü

Kubernetes loglarının Elasticsearch'e ulaştığını terminalden sorgulayın:

```bash
curl -s http://localhost:9200/_cat/indices?v | grep beats
```

### 2. Kubernetes Metadata Doğrulaması

Son gelen belgelerdeki `kubernetes` alanlarını JSON çıktısı ile teyit edin:

```bash
curl -s "http://localhost:9200/filebeat-*/_search?size=1&q=kubernetes.pod.name:payment-service*" | jq '.hits.hits[0]._source.kubernetes'
```

Beklenen çıktı:
```json
{
  "container": {
    "name": "payment-worker"
  },
  "namespace": "default",
  "node": {
    "name": "kind-control-plane"
  },
  "pod": {
    "name": "payment-service-demo-...",
    "uid": "..."
  }
}
```

### 3. Kibana Arayüzünde İnceleme

1. Tarayıcınızda `https://studentXX-kibana.devopsatolyesi.com` veya `http://<UBUNTU_IP>:15601` (yerel `http://localhost:5601`) adresini açın.
2. **Analytics > Discover** menüsüne gidin.
3. Arama çubuğuna şu KQL sorgusunu yazın:
   ```kql
   kubernetes.pod.name : "payment-service*" and message : "Traceback"
   ```
4. Gelen belgenin `message` alanını genişletin. Tüm Python hata yığınının tek bir olay altında eksiksiz görüntülendiğini doğrulayın.

---

## Temizlik

> **Not:** Bu temizlik komutları Kubernetes kümenizi silmez; yalnızca bu laboratuvara ait Filebeat DaemonSet ve test podlarını temizler.

```bash
kubectl delete -f multiline-app-deployment.yaml
kubectl delete -f filebeat-kubernetes-daemonset.yaml
```
