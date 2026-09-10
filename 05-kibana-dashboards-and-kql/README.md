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

### Adım 2: Kibana Discover ile Log İnceleme

1. Sol menüden **Analytics > Discover** bölümüne geçin.
2. Sol üst açılır menüden `Application Logs` veri görünümünü seçin.
3. Zaman filtresini sağ üstten **Last 1 hour** yapın.
4. KQL arama çubuğuna şu sorguyu girip Enter'a basın:
   ```kql
   response_code >= 400
   ```
5. Sol paneldeki **Available fields** listesinden `client_ip`, `method`, `url`, `response_code` alanlarının üzerine gelip `+` (Add field as column) simgesine tıklayın. Tablonun okunabilir bir HTTP erişim günlüğüne dönüştüğünü görün.

### Adım 3: Kibana Lens ile Görselleştirme Üretme

1. Sol menüden **Analytics > Dashboard** bölümüne gidin ve **Create dashboard** butonuna tıklayın.
2. **Create visualization** butonuna tıklayarak **Lens** editörünü açın.
3. **Grafik 1: Zaman Serisi Çubuk Grafik (HTTP Durum Kodları)**
   - Sağdaki menüden veri görünümü olarak `Application Logs` seçin.
   - Sol taraftaki alan listesinden `@timestamp` alanını yatay eksene (Horizontal axis) sürükleyin.
   - Sol taraftan `Records` alanını düşey eksene (Primary metric) sürükleyin.
   - `response_code` alanını sürükleyip **Break down by** alanına bırakın.
   - Sağ üstten **Save and return** butonuna basarak panoya ekleyin.
4. **Grafik 2: Pasta / Halka Grafik (HTTP Metot Dağılımı)**
   - Tekrar **Create visualization** deyin.
   - Grafik türünü (sağ üst) **Donut** yapın.
   - `method` alanını sürükleyip **Slice by** alanına bırakın.
   - **Save and return** ile panoya ekleyin.
5. Panonun sağ üstündeki **Save** butonuna basarak adını `DevOps Observability Overview` olarak kaydedin.

### Adım 4: Otomatik Dışa / İçe Aktarma (Import / Export)

Hazırlanan panoyu JSON (NDJSON) olarak dışa aktarmak veya hazır panoyu içeri almak için:

```bash
# Hazır panoyu ve Data View'ları tek komutla Kibana'ya aktarın
cd 05-kibana-dashboards-and-kql
./scripts/import-dashboards.sh
```

## Doğal Doğrulama ve Beklenen Sonuç

1. Terminalden Kibana Saved Objects API'sini sorgulayın:
   ```bash
   curl -s http://localhost:5601/api/saved_objects/_find?type=dashboard | jq '.saved_objects[].attributes.title'
   ```
   Çıktıda `"DevOps Observability Overview"` başlığının yer aldığını doğrulayın.

2. Tarayıcıda `http://localhost:5601/app/dashboards` sayfasına gidin.
3. Panonun üzerinde filtreleme yaparak (örneğin grafikten `500` dilimine tıklayarak) tüm panonun anlık olarak dinamik şekilde filtrelendiğini gözlemleyin.

## Temizlik

Oluşturulan Data View veya Saved Object'leri temizlemek isterseniz:
1. **Stack Management > Saved Objects** menüsünden ilgili dashboard veya data view'ları seçip **Delete** diyebilirsiniz.
