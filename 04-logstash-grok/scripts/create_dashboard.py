#!/usr/bin/env python3
"""README Adim 8'de elle kurulan "SSH ve Nginx" panosunun betik kopyasini kurar.

Arayuzde secilen data view, sorgu ve alanlar Kibana Saved Objects API'sine gonderilir.
Data view adlari "Betik:" ile baslar; elle kurulan "Sistem Loglari" ve "Docker Loglari"
ile karismaz. Betik tekrar calistirilabilir (overwrite=true).
"""
import base64
import json
import os
import sys
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
    "grok-system-logs": ("system-logs-*", "Betik: Sistem Logları"),
    "grok-docker-logs": ("docker-logs-*", "Betik: Docker Logları"),
}

DASHBOARD_ID = "grok-ssh-nginx"
DASHBOARD_TITLE = "SSH ve Nginx (betik)"
PANELS = [
    ("grok-ssh-by-ip", "Başarısız SSH girişi: kaynak IP", "grok-system-logs",
     {"bucket": ("terms", "source.ip.keyword", 5), "metric": ("count",),
      "query": 'event.outcome : "failure"', "series_type": "bar_stacked"}, (0, 0, 24, 15)),
    ("grok-nginx-by-url", "Nginx: en çok istenen adresler", "grok-docker-logs",
     {"bucket": ("terms", "url.original.keyword", 5), "metric": ("count",),
      "query": 'container.name : "demo-nginx" and http.response.status_code >= 200',
      "series_type": "bar_stacked"}, (24, 0, 24, 15)),
]


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
    for view_id, (pattern, name) in VIEWS.items():
        api("POST", "/api/data_views/data_view", {
            "override": True,
            "data_view": {"id": view_id, "title": pattern, "name": name, "timeFieldName": "@timestamp"}})
        print(f"[+] Data view: {name} ({pattern})")
    panels, refs = [], []
    for panel_id, title, view_id, options, (x, y, w, h) in PANELS:
        payload = lb.xy_panel(panel_id, title, view_id, **options)
        lb.validate(payload)
        api("POST", f"/api/saved_objects/lens/{panel_id}?overwrite=true", payload)
        panel, ref = lb.dashboard_panel(panel_id, panel_id, {"x": x, "y": y, "w": w, "h": h})
        panels.append(panel)
        refs.append(ref)
    lb.validate_dashboard(panels, refs)
    api("POST", f"/api/saved_objects/dashboard/{DASHBOARD_ID}?overwrite=true", {
        "attributes": {
            "title": DASHBOARD_TITLE,
            "panelsJSON": json.dumps(panels),
            "optionsJSON": json.dumps({"useMargins": True, "syncColors": True, "hidePanelTitles": False}),
            "timeRestore": True, "timeFrom": "now-1h", "timeTo": "now",
            "kibanaSavedObjectMeta": {"searchSourceJSON": json.dumps(
                {"query": {"query": "", "language": "kuery"}, "filter": []})},
        },
        "references": refs,
    })
    print(f"[+] Pano: {DASHBOARD_TITLE}  ->  /app/dashboards#/view/{DASHBOARD_ID}")


if __name__ == "__main__":
    main()
