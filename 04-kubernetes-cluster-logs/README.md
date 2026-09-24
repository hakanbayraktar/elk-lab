# LAB-ELK-04 — Kubernetes Cluster ve Pod Loglarının Toplanması

| Seviye | Profil / Araçlar | Açık Portlar |
|:---:|:---:|:---:|
| Orta | Kubernetes (Kind/K8s), Filebeat DaemonSet, Kibana | 9200 (ES), 15601 (Kibana), 5044 (Logstash Beats) |

[LAB-ELK-04.zip](LAB-ELK-04.zip)

## Amaç
* Mevcut Kind Kubernetes kümesindeki tüm podların `stdout` ve `stderr` günlüklerini küme genelinde çalışan bir `Filebeat DaemonSet` ile otomatik olarak toplamak.
* `add_kubernetes_metadata` işlemcisi sayesinde loglara pod adı, namespace, konteyner adı ve node adı metaverilerini dinamik olarak eklemek.
* Çok satırlı (multiline) Python/Java hata yığınlarını (`Exception Stack Trace`) `multiline regex` kuralıyla tek bir Elastic olayında birleştirmek.
* Toplanan Kubernetes loglarını Elasticsearch'te `k8s-logs-*` indeksine yazmak ve REST API ile doğrulamak.
* Kibana Discover üzerinde `kubernetes.pod.name` ve `kubernetes.namespace` alanlarıyla KQL sorguları yürütmek.

---

## Ön Koşullar
* **Merkezi ELK Omurgası:** `00-elk-core-stack` servislerinin (`elasticsearch`, `logstash`, `kibana`) çalışır durumda olması gerekmektedir. *(Bu servisler kapatılmaz).*
* **Mevcut Kind Kümesi:** Önceki eğitim modüllerinde kurulan mevcut Kind Kubernetes kümesi (`kubectl get nodes` çıktısı `Ready` olmalıdır). **Yeni bir küme kurulmaz; mevcut küme silinmez.**
* Kimlik Doğrulama: Kullanıcı: `elastic` | Şifre: `BilginIT454`.

---

## Mimari ve Çalışma Modeli

```text
+───────────────────────────────────────────────────────────────+
| Kubernetes Kümesi (Kind)                                      |
|                                                               |
|  [ payment-service Pod ]            [ Diğer Uygulama Podları ]|
|         │ (stdout/stderr)                     │               |
|         ▼                                     ▼               |
|  /var/log/pods/...                  /var/log/pods/...         |
|  /var/log/containers/*.log          /var/log/containers/*.log |
|         │                                     │               |
|         └──────────────────┬──────────────────┘               |
|                            ▼                                  |
|               [ Filebeat DaemonSet (Node) ]                   |
|               - multiline regex: Stack trace birleştirme      |
|               - add_kubernetes_metadata (K8s API)             |
+────────────────────────────┼──────────────────────────────────+
                             │ (Host Ağından Port 5044 Beats)
                             ▼
              [ Logstash Pipeline (:5044) ]
              - Index: k8s-logs-YYYY.MM.DD
                             │
                             ▼ (Basic Auth: elastic/BilginIT454)
              [ Elasticsearch (:9200) ] ──► [ Kibana UI (:15601) ]
```

---

## Adım Adım Uygulama Rehberi

### 1. Filebeat DaemonSet ve RBAC Kurulumu

Filebeat'in Kubernetes API'sinden pod bilgilerini okuyabilmesi için gerekli RBAC izinlerini ve DaemonSet podunu oluşturun:

```bash
cd ~/elk-lab/04-kubernetes-cluster-logs
kubectl apply -f filebeat-kubernetes-daemonset.yaml
```

DaemonSet podlarının çalıştığını doğrulayın:

```bash
kubectl get pods -n logging -l app=filebeat -o wide
```

Pod loglarını inceleyerek Logstash bağlantısının kurulduğunu teyit edin:

```bash
kubectl logs -n logging -l app=filebeat --tail=25
```

*`Connection to backoff(async(tcp://...:5044)) established` mesajını görün.*

---

### 2. Çok Satırlı (Multiline) Hata Üreten Test Uygulamasını Dağıtma

Hem normal sipariş logları hem de çok satırlı Python `ZeroDivisionError` hata yığını basan örnek uygulamayı kümede çalıştırın:

```bash
kubectl apply -f multiline-app-deployment.yaml
kubectl get deployment payment-service-demo
```

Uygulamanın loglarını doğrudan kubectl ile izleyin:

```bash
kubectl logs -l app=payment-service --tail=15
```

*Python `Traceback (most recent call last):` hata bloklarının ekrana basıldığını göreceksiniz.*

---

### 3. Filebeat Çok Satır (Multiline) Birleştirme Mantığı

`filebeat-kubernetes-daemonset.yaml` içinde tanımlanan kural:

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

* **Açıklama:** Standart bir tarih damgasıyla (`YYYY-MM-DD` veya `[YYYY-MM-DD`) başlamayan her yeni satır (örneğin `Traceback`, `File ...`, `ZeroDivisionError`), önceki satırın bir devamı kabul edilir ve Elasticsearch tarafında **tek bir log kaydında** toplanır.

---

## Doğal Doğrulama ve Beklenen Sonuç

### 1. Elasticsearch API ile Kubernetes Metaverisini Doğrulama

Toplanan logların Kubernetes pod bilgileriyle zenginleştirildiğini REST API ile sorgulayın:

```bash
curl -s -u elastic:BilginIT454 "http://localhost:9200/k8s-logs-*/_search?q=kubernetes.pod.name:payment-service*&pretty" | jq '.hits.hits[0]._source.kubernetes'
```

* **Beklenen Örnek Çıktı:**
```json
{
  "container": {
    "name": "payment-worker"
  },
  "namespace": "default",
  "pod": {
    "name": "payment-service-demo-..."
  }
}
```

---

### 2. Kibana Discover Ekranında Çok Satırlı Hata Analizi

1. Tarayıcınızdan Kibana'ya bağlanın (`http://<SUNUCU_IP>:15601` veya `https://studentXX-kibana.devopsatolyesi.com`).
2. **Analytics > Discover** bölümüne gidin.
3. Veri Görünümü olarak **`Kubernetes Pod & Cluster Logs`** (`k8s-logs-*`) seçin.
4. KQL arama çubuğuna şu filtreyi girin:
   ```text
   kubernetes.pod.name : "payment-service*" and message : "Traceback"
   ```
5. Sonuç listesindeki herhangi bir hata kaydını açın. `message` alanında tüm Python hata yığınının bölünmeden, tek bir blok halinde okunduğunu doğrulayın.

---

## Temizlik

Kubernetes kaynaklarını serbest bırakmak için yalnızca bu modülde oluşturulan DaemonSet ve test podunu silin:

```bash
kubectl delete -f multiline-app-deployment.yaml
kubectl delete -f filebeat-kubernetes-daemonset.yaml
```

> **Önemli Not:** Kind Kubernetes kümenizi silmeyin. Merkezi ELK omurgası (`00-elk-core-stack`), sonraki Kibana ve SIEM laboratuvarları için açık kalmalıdır.
