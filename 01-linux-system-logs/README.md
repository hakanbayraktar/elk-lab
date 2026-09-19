# LAB-ELK-01 — Linux Host Sistem ve Güvenlik Loglarının Toplanması

| Seviye | Profil / Araçlar | Açık Portlar |
|:---:|:---:|:---:|
| Başlangıç | `filebeat`, `systemd`, `logger` | 15601 / 5601 (Kibana) |

---

## Ön Koşullar ve Bağımlılıklar

* **Zorunlu Bağımlılık:** `00-elk-core-stack` modülünün (`elasticsearch`, `logstash`, `kibana`) çalışıyor olması gerekmektedir. Logstash `:5044` portunun dinlemede olduğunu doğrulayın (`nc -zv localhost 5044`).
* Bu modüldeki Filebeat ajanları logları merkezi Logstash servisine aktaracaktır.

---

## Mimari ve Çalışma Modeli

```text
[ Ubuntu Host (/var/log) ]
├── auth.log (SSH & Sudo)  ──> [ Filebeat (Agent) ] ──> [ Logstash (:5044) ] ──> [ Elasticsearch ]
└── syslog   (Sistem & Çekirdek)
```

---

## Adım Adım Uygulama Rehberi

### Yöntem A: Doğrudan Ubuntu Üzerine Kurulum (Önerilen)

```bash
cd 01-linux-system-logs/scripts
chmod +x install-filebeat-ubuntu.sh
./install-filebeat-ubuntu.sh
```

### Yöntem B: Konteyner ile Çalıştırma (Host Loglarını Bağlayarak)

Eğer sisteme paket kurmak istemiyorsanız, host `/var/log` dizinini salt-okunur mount ederek Docker konteyneri olarak da çalıştırabilirsiniz:

```bash
cd 01-linux-system-logs
docker run -d --name filebeat-linux --net=host \
  --user=root \
  -v $(pwd)/filebeat-linux.yml:/usr/share/filebeat/filebeat.yml:ro \
  -v /var/log:/var/log:ro \
  docker.elastic.co/beats/filebeat:8.17.0 -e -strict.perms=false
```

---

## Doğal Doğrulama ve Beklenen Sonuç

### 1. Test Log Trafiği Üretme

```bash
cd 01-linux-system-logs/scripts
./generate-auth-traffic.sh
```

### 2. Elasticsearch Üzerinde İndekslenen Logları Sorgulama

```bash
curl -s "http://localhost:9200/logstash-*/_search?q=log_type:system_auth&pretty" | jq '.hits.total.value'
```

*Toplam değer 0'dan büyük dönmeli ve `nonexistent_user` veya `sudo_test` ifadeleri listelenmelidir.*

### 3. Kibana Discover Ekranında İnceleme

1. Tarayıcınızdan `https://studentXX-kibana.devopsatolyesi.com` veya `http://<UBUNTU_IP>:15601` (yerel `http://localhost:5601`) adresine gidin.
2. **Management > Stack Management > Data Views** sekmesinden `logstash-*` kalıbıyla yeni bir Data View oluşturun (`@timestamp` seçili).
3. **Discover** ekranına gidin ve arama çubuğuna şunu yazın:
   ```kql
   log_type : "system_auth"
   ```
*Host adı, auth log satırları ve zaman damgaları listelenecektir.*

---

## Temizlik

> **Not:** Bu temizlik işlemi yalnızca bu labda başlatılan Filebeat ajanını durdurur. Ana omurga (`00-elk-core-stack`) sonraki lablar için çalışır durumda kalmalıdır.

```bash
# Eğer native servis olarak kurduysanız:
sudo systemctl stop filebeat

# Eğer Docker ile çalıştırdıysanız:
docker rm -f filebeat-linux
```
