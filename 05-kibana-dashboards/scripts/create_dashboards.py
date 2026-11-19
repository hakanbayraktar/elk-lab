#!/usr/bin/env python3
"""demo-* index'leri için data view'ları ve üç hazır panoyu kurar.

Kibana Saved Objects API kullanilir; panel nesneleri lens_builder ile uretilip
gonderilmeden once dogrulanir. Betik tekrar calistirilabilir (overwrite=true).
"""
import base64
import json
import os
import sys
import time
from urllib import error, request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lens_builder as lb  # noqa: E402

BASE = os.environ.get("KIBANA_URL", "http://localhost:15601").rstrip("/")
PWD = os.environ.get("ELASTIC_PASSWORD", "DevOps2026!")
HEADERS = {
    "Content-Type": "application/json",
    "kbn-xsrf": "elk-lab",
    "Authorization": "Basic " + base64.b64encode(f"elastic:{PWD}".encode()).decode(),
}

VIEWS = {
    "demo-app": ("demo-app-logs", "Demo Uygulama Logları"),
    "demo-security": ("demo-security-logs", "Demo Güvenlik Logları"),
    "demo-k8s": ("demo-k8s-logs", "Demo Kubernetes Olayları"),
    "demo-cicd": ("demo-cicd-logs", "Demo CI/CD Pipeline Logları"),
    # README Adim 4'te elle kurulan panonun betik kopyasi; ad cakismasin diye "(betik)" eki var
    "elk-system-logs": ("system-logs-*", "Betik: Sistem Logları"),
}

ERR = "http.response.status_code >= 500"
SSH_FAIL = 'event.action : "ssh_login" and event.outcome : "failure"'

# pano id -> (baslik, [(panel_id, baslik, tur, data view, argumanlar, konum)])
DASHBOARDS = {
    "demo-app-overview": ("Uygulama Trafiği ve Hatalar", [
        ("demo-app-total", "Toplam istek", "metric", "demo-app",
         {"metric": ("count",), "label": "İstek"}, (0, 0, 16, 8)),
        ("demo-app-5xx", "5xx hata sayısı", "metric", "demo-app",
         {"metric": ("count", ERR), "label": "5xx"}, (16, 0, 16, 8)),
        ("demo-app-p95", "Yanıt süresi p95 (ms)", "metric", "demo-app",
         {"metric": ("percentile", "event.duration_ms", 95), "label": "p95 ms"}, (32, 0, 16, 8)),
        ("demo-app-by-service", "Zaman içinde servis bazında istek", "xy", "demo-app",
         {"bucket": ("date_histogram", "@timestamp"), "metric": ("count",),
          "split": ("terms", "service.name", 5), "series_type": "bar_stacked"}, (0, 8, 28, 14)),
        ("demo-app-errors", "En çok 5xx veren servisler", "xy", "demo-app",
         {"bucket": ("terms", "service.name", 5), "metric": ("count", ERR), "label": "5xx",
          "series_type": "bar_horizontal"}, (28, 8, 20, 14)),
        ("demo-app-slow", "Endpoint bazında istek ve p95 süre", "table", "demo-app",
         {"buckets": [("terms", "url.original", 10)],
          "metrics": [("count",), ("percentile", "event.duration_ms", 95)]}, (0, 22, 48, 12)),
    ]),
    "demo-security-overview": ("Güvenlik: SSH ve Firewall", [
        ("demo-sec-ssh-fail", "Başarısız SSH girişi", "metric", "demo-security",
         {"metric": ("count", SSH_FAIL), "label": "Başarısız giriş"}, (0, 0, 24, 8)),
        ("demo-sec-blocked", "Firewall'da engellenen bağlantı", "metric", "demo-security",
         {"metric": ("count", 'event.action : "firewall_block"'), "label": "Engellenen"}, (24, 0, 24, 8)),
        ("demo-sec-ips", "Saldırgan IP adresleri", "xy", "demo-security",
         {"bucket": ("terms", "source.ip", 10), "metric": ("count",), "query": SSH_FAIL,
          "label": "Başarısız giriş", "series_type": "bar_horizontal"}, (0, 8, 24, 14)),
        ("demo-sec-users", "Denenen kullanıcı adları", "pie", "demo-security",
         {"slice_by": "user.name", "size": 8, "query": SSH_FAIL}, (24, 8, 24, 14)),
        ("demo-sec-timeline", "Zaman içinde güvenlik olayları", "xy", "demo-security",
         {"bucket": ("date_histogram", "@timestamp"), "metric": ("count",),
          "split": ("terms", "event.action", 3), "series_type": "bar_stacked"}, (0, 22, 48, 12)),
    ]),
    "demo-k8s-cicd-overview": ("Kubernetes ve CI/CD", [
        ("demo-k8s-oom", "OOMKilled olayı", "metric", "demo-k8s",
         {"metric": ("count", 'event.reason : "OOMKilled"'), "label": "OOMKilled"}, (0, 0, 24, 8)),
        ("demo-cicd-failed", "Başarısız pipeline adımı", "metric", "demo-cicd",
         {"metric": ("count", 'ci.status : "FAILED"'), "label": "FAILED"}, (24, 0, 24, 8)),
        ("demo-k8s-reasons", "Namespace bazında olay nedenleri", "xy", "demo-k8s",
         {"bucket": ("terms", "kubernetes.namespace", 5), "metric": ("count",),
          "split": ("terms", "event.reason", 5), "series_type": "bar_stacked"}, (0, 8, 24, 14)),
        ("demo-cicd-status", "Pipeline sonuçları", "pie", "demo-cicd",
         {"slice_by": "ci.status", "size": 3}, (24, 8, 24, 14)),
        ("demo-cicd-stage", "Stage bazında ortalama süre (sn)", "table", "demo-cicd",
         {"buckets": [("terms", "ci.stage", 10)],
          "metrics": [("count",), ("average", "ci.duration_sec")]}, (0, 22, 48, 12)),
    ]),
    # README Adim 4'te elle kurulan "SSH ve Hatalar" panosunun aynisi
    "ssh-errors-script": ("SSH ve Hatalar (betik)", [
        ("ssh-failed-by-ip", "Başarısız SSH girişi: kaynak IP", "xy", "elk-system-logs",
         {"bucket": ("terms", "source.ip.keyword", 5), "metric": ("count",),
          "query": 'event.outcome : "failure"', "series_type": "bar_stacked"}, (0, 0, 24, 15)),
        ("app-5xx-by-service", "En çok 5xx veren servisler", "xy", "demo-app",
         {"bucket": ("terms", "service.name", 5), "metric": ("count",),
          "query": ERR, "series_type": "bar_stacked"}, (24, 0, 24, 15)),
    ]),
}

BUILDERS = {"metric": lb.metric_panel, "xy": lb.xy_panel, "pie": lb.pie_panel, "table": lb.table_panel}


def api(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = request.Request(BASE + path, data=data, headers=HEADERS, method=method)
    try:
        with request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else {}
    except error.HTTPError as exc:
        raise SystemExit(f"{method} {path}: HTTP {exc.code} {exc.read().decode()[:300]}")


def main():
    for _ in range(60):
        try:
            if api("GET", "/api/status")["status"]["overall"]["level"] == "available":
                break
        except (OSError, KeyError, SystemExit):
            pass
        time.sleep(3)

    for view_id, (pattern, name) in VIEWS.items():
        api("POST", "/api/data_views/data_view", {
            "override": True,
            "data_view": {"id": view_id, "title": pattern, "name": name, "timeFieldName": "@timestamp"}})
        print(f"[+] Data view: {name} ({pattern})")

    for dash_id, (title, specs) in DASHBOARDS.items():
        panels, refs = [], []
        for panel_id, panel_title, kind, view_id, options, (x, y, w, h) in specs:
            payload = BUILDERS[kind](panel_id, panel_title, view_id, **options)
            lb.validate(payload)
            api("POST", f"/api/saved_objects/lens/{panel_id}?overwrite=true", payload)
            panel, ref = lb.dashboard_panel(panel_id, panel_id, {"x": x, "y": y, "w": w, "h": h})
            panels.append(panel)
            refs.append(ref)
        lb.validate_dashboard(panels, refs)
        api("POST", f"/api/saved_objects/dashboard/{dash_id}?overwrite=true", {
            "attributes": {
                "title": title,
                "panelsJSON": json.dumps(panels),
                "optionsJSON": json.dumps({"useMargins": True, "syncColors": True, "hidePanelTitles": False}),
                "timeRestore": True, "timeFrom": "now-24h", "timeTo": "now",
                "kibanaSavedObjectMeta": {"searchSourceJSON": json.dumps(
                    {"query": {"query": "", "language": "kuery"}, "filter": []})},
            },
            "references": refs,
        })
        print(f"[+] Pano: {title}  ->  /app/dashboards#/view/{dash_id}")


if __name__ == "__main__":
    main()
