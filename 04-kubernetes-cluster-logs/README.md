# LAB-ELK-04 — Kubernetes Cluster ve Pod Loglarının Toplanması

| Seviye | Profil / Araçlar | Açık Portlar |
|:---:|:---:|:---:|
| Orta | Kubernetes (Kind/K8s), Filebeat DaemonSet, Kibana | 9200 (ES), 15601 (Kibana), 5044 (Logstash Beats) |

[LAB-ELK-04.zip](LAB-ELK-04.zip)

> [!IMPORTANT]
> **DİKKAT: `00-elk-core-stack` AÇIK KALMALIDIR!**
> Bu laboratuvardaki Kubernetes logları `00-elk-core-stack` içindeki Logstash ve Elasticsearch'e akar. 00 labındaki servisleri **kesinlikle durdurmayın veya silmeyin**.
> Ayrıca eğitim için önceki günlerden gelen mevcut Kind kümeniz kullanılır; **Kind kümesini kesinlikle silmeyin**.

---

## Amaç
* Mevcut Kind Kubernetes kümesindeki tüm podların loglarını küme genelinde çalışan bir `Filebeat DaemonSet` ile otomatik toplamak.
* `add_kubernetes_metadata` işlemcisi ile loglara pod adı, namespace ve node adı bilgilerini dinamik olarak eklemek.
* Çok satırlı (multiline) Python/Java hata yığınlarını (`Exception Stack Trace`) `multiline regex` kuralıyla tek bir olayda birleştirmek.
* Toplanan Kubernetes loglarını Elasticsearch üzerinde `k8s-logs-*` indeksine yazmak ve doğrulamak.
* Kibana Discover üzerinde pod bazlı KQL sorguları yürütmek.

---

## Ön Koşullar
* **Merkezi ELK Omurgası:** `00-elk-core-stack` servislerinin (`elasticsearch`, `logstash`, `kibana`) çalışıyor olması gereklidir.
* **Mevcut Kind Kümesi:** `kubectl get nodes` çıktısının `Ready` olduğunu doğrulayın. *(Yeni küme kurulmaz).*
* Giriş Bilgileri: Kullanıcı: `elastic` | Şifre: `BilginIT454` | Port: `15601`.

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
|               - multiline regex: Hata birleştirme             |
|               - add_kubernetes_metadata (K8s API)             |
+────────────────────────────┼──────────────────────────────────+
                             │ (Host Ağ Portu: 5044 Beats)
                             ▼
              [ Logstash Boru Hattı (:5044) ]
              - İndeks: k8s-logs-YYYY.MM.DD
                             │
                             ▼ (Basic Auth: elastic/BilginIT454)
              [ Elasticsearch (:9200) ] ──► [ Kibana UI (:15601) ]
```

---

## Adım Adım Uygulama Rehberi

### Adım 1: Lab Dizinine Geçin ve DaemonSet'i Kurun

İlgili dizine geçerek Filebeat'in küme seviyesinde çalışması için gerekli RBAC izinlerini ve DaemonSet podunu oluşturun:

```bash
cd ~/elk-lab/04-kubernetes-cluster-logs
kubectl apply -f filebeat-kubernetes-daemonset.yaml
```

DaemonSet podlarının çalıştığını kontrol edin:

```bash
kubectl get pods -n logging -l app=filebeat -o wide
```

Pod loglarını izleyerek Logstash bağlantısını teyit edin:

```bash
kubectl logs -n logging -l app=filebeat --tail=20
```

*`Connection to backoff(async(tcp://...:5044)) established` çıktısını görün.*

---

### Adım 2: Çok Satırlı Hata Üreten Test Uygulamasını Dağıtın

Hem normal sipariş logları hem de Python `ZeroDivisionError` hata yığını basan örnek uygulamayı başlatın:

```bash
kubectl apply -f multiline-app-deployment.yaml
kubectl get deployment payment-service-demo
```

Uygulamanın ürettiği logları doğrudan terminalden izleyin:

```bash
kubectl logs -l app=payment-service --tail=15
```

*Python `Traceback (most recent call last):` hata bloklarını göreceksiniz.*

---

### Adım 3: Filebeat Hata Yığınlarını Nasıl Birleştirir?

`filebeat-kubernetes-daemonset.yaml` içindeki kural:
* Standart tarih damgasıyla (`YYYY-MM-DD`) başlamayan satırları (örneğin `Traceback`, `ZeroDivisionError`) önceki log satırının devamı kabul eder.
* Böylece 10 satırlık hata yığını Elasticsearch'e **10 ayrı log yerine tek bir bütün olay** olarak kaydedilir.

---

## Doğal Doğrulama ve Beklenen Sonuç

### 1. Elasticsearch API ile Kubernetes Metaverisini Doğrulama

Toplanan logların Kubernetes pod bilgileriyle birlikte kaydedildiğini REST API ile sorgulayın:

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

1. Tarayıcınızdan Kibana'yı açın (`http://<SUNUCU_IP>:15601` veya `https://studentXX-kibana.devopsatolyesi.com`).
2. **Analytics > Discover** bölümüne gidin.
3. Veri Görünümünden **`Kubernetes Pod & Cluster Logs`** (`k8s-logs-*`) seçin.
4. KQL arama çubuğuna şunu yazın:
   ```text
   kubernetes.pod.name : "payment-service*" and message : "Traceback"
   ```
5. Sonuç listesindeki kaydı açın; tüm Python hata yığınının bölünmeden, tek parça halinde görüntülendiğini doğrulayın.

---

## Temizlik

Yalnızca bu lab için başlattığınız DaemonSet ve test podunu silin:

```bash
kubectl delete -f multiline-app-deployment.yaml
kubectl delete -f filebeat-kubernetes-daemonset.yaml
```

> [!WARNING]
> **Merkezi Omurga ve Küme Hatırlatması:** Kind Kubernetes kümenizi ve `00-elk-core-stack` servislerini **kesinlikle kapatmayın veya silmeyin**. Sonraki tüm laboratuvarlar bu omurga üzerinde çalışır.
