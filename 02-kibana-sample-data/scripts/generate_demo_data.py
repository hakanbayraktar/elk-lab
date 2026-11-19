#!/usr/bin/env python3
"""Hazir panolar icin son 24 saate yayilmis demo verisi uretir.

Veri sentetiktir ve yalnizca demo-* index'lerine yazilir; LAB-03/03/04'un gercek
loglari (system-logs-*, docker-logs-*, k8s-logs-*) ile karismaz. Betik her
calistiginda bu dort index'i silip yeniden olusturur.
"""
import base64
import json
import os
import random
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

ES_URL = os.getenv("ES_URL", "http://localhost:9200").rstrip("/")
ES_PASSWORD = os.getenv("ELASTIC_PASSWORD", "DevOps2026!")
AUTH = "Basic " + base64.b64encode(f"elastic:{ES_PASSWORD}".encode()).decode()
NOW = datetime.now(timezone.utc)
random.seed(42)

KW = {"type": "keyword"}
MAPPINGS = {
    "demo-app-logs": {
        "service.name": KW, "http.request.method": KW, "url.original": KW,
        "http.response.status_code": {"type": "integer"},
        "event.duration_ms": {"type": "integer"}, "source.ip": {"type": "ip"},
        "log.level": KW, "message": {"type": "text"},
    },
    "demo-security-logs": {
        "event.action": KW, "event.outcome": KW, "source.ip": {"type": "ip"},
        "user.name": KW, "destination.port": {"type": "integer"}, "message": {"type": "text"},
    },
    "demo-k8s-logs": {
        "kubernetes.namespace": KW, "kubernetes.pod.name": KW, "kubernetes.node.name": KW,
        "event.reason": KW, "log.level": KW, "message": {"type": "text"},
    },
    "demo-cicd-logs": {
        "ci.tool": KW, "ci.pipeline_id": KW, "ci.stage": KW, "ci.status": KW,
        "ci.branch": KW, "ci.duration_sec": {"type": "integer"}, "message": {"type": "text"},
    },
}


def es(method, path, body=None, ndjson=False):
    data = None
    if body is not None:
        data = body.encode() if ndjson else json.dumps(body).encode()
    req = urllib.request.Request(ES_URL + path, data=data, method=method, headers={
        "Authorization": AUTH,
        "Content-Type": "application/x-ndjson" if ndjson else "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as exc:
        if method == "DELETE" and exc.code == 404:
            return {}
        raise SystemExit(f"{method} {path}: HTTP {exc.code} {exc.read().decode()[:300]}")


def nested(flat):
    """{'a.b': 1} -> {'a': {'b': 1}}"""
    out = {}
    for key, value in flat.items():
        cur = out
        parts = key.split(".")
        for part in parts[:-1]:
            cur = cur.setdefault(part, {})
        cur[parts[-1]] = value
    return out


def ts():
    return (NOW - timedelta(seconds=random.randint(0, 86400))).isoformat()


def app_doc():
    service = random.choice(["payment-service", "order-service", "auth-service", "frontend", "api-gateway"])
    url, method, codes = random.choice([
        ("/api/v1/orders", "POST", [201, 201, 201, 400, 500]),
        ("/api/v1/payments", "POST", [200, 200, 200, 402, 500, 502]),
        ("/api/v1/login", "POST", [200, 200, 401, 403]),
        ("/api/v1/cart", "GET", [200, 200, 304, 500]),
        ("/products", "GET", [200, 200, 304, 404]),
        ("/healthz", "GET", [200]),
    ])
    code = random.choice(codes)
    level = "ERROR" if code >= 500 else "WARN" if code >= 400 else "INFO"
    duration = random.randint(400, 2800) if code >= 500 else random.randint(8, 250)
    return {"@timestamp": ts(), "service.name": service, "http.request.method": method,
            "url.original": url, "http.response.status_code": code, "event.duration_ms": duration,
            "source.ip": random.choice(["10.0.0.12", "10.0.0.24", "192.168.1.100", "203.0.113.45"]),
            "log.level": level, "message": f"{method} {url} {code} {duration}ms"}


def security_doc():
    roll = random.random()
    if roll < 0.65:
        user = random.choice(["root", "admin", "deploy", "ubuntu", "test", "postgres", "oracle"])
        ip = random.choice(["198.51.100.77", "203.0.113.45", "185.220.101.5", "45.154.255.89"])
        return {"@timestamp": ts(), "event.action": "ssh_login", "event.outcome": "failure",
                "source.ip": ip, "user.name": user,
                "message": f"Failed password for invalid user {user} from {ip} port 52144 ssh2"}
    if roll < 0.80:
        user = random.choice(["deploy", "ubuntu"])
        return {"@timestamp": ts(), "event.action": "ssh_login", "event.outcome": "success",
                "source.ip": "10.0.0.10", "user.name": user,
                "message": f"Accepted publickey for {user} from 10.0.0.10 port 50122 ssh2"}
    ip = random.choice(["198.51.100.77", "91.240.118.172", "45.154.255.89"])
    port = random.choice([22, 23, 3306, 5432, 6379, 9200])
    return {"@timestamp": ts(), "event.action": "firewall_block", "event.outcome": "failure",
            "source.ip": ip, "destination.port": port,
            "message": f"[UFW BLOCK] IN=eth0 SRC={ip} DST=10.0.0.5 PROTO=TCP DPT={port}"}


def k8s_doc():
    ns, pod = random.choice([
        ("production", "order-service-79db8f8-b8xqw"), ("production", "payment-service-58dc4-kk9pl"),
        ("production", "auth-service-678bb-mn32k"), ("staging", "api-gateway-6bb7f-lk890"),
        ("kube-system", "coredns-768b85b76-pq789")])
    roll = random.random()
    if roll < 0.06:
        reason, level, msg = "OOMKilled", "ERROR", f"Container in {pod} exceeded memory limit"
    elif roll < 0.15:
        reason, level, msg = "CrashLoopBackOff", "ERROR", "Back-off restarting failed container"
    elif roll < 0.30:
        reason, level, msg = "Unhealthy", "WARN", "Readiness probe failed: HTTP 503"
    else:
        reason, level, msg = "Started", "INFO", f"Pod {pod} healthy"
    return {"@timestamp": ts(), "kubernetes.namespace": ns, "kubernetes.pod.name": pod,
            "kubernetes.node.name": random.choice(["worker-1", "worker-2", "worker-3"]),
            "event.reason": reason, "log.level": level, "message": msg}


def cicd_doc():
    stage = random.choice(["unit-test", "sonarqube", "trivy-scan", "docker-build", "deploy-staging", "deploy-prod"])
    roll = random.random()
    status = "FAILED" if roll < 0.15 else "UNSTABLE" if roll < 0.25 else "SUCCESS"
    duration = random.randint(20, 90) if stage in ("unit-test", "trivy-scan") else random.randint(60, 300)
    pipeline = f"build-{random.randint(100, 199)}"
    return {"@timestamp": ts(), "ci.tool": random.choice(["jenkins", "gitlab-ci", "github-actions"]),
            "ci.pipeline_id": pipeline, "ci.stage": stage, "ci.status": status,
            "ci.branch": random.choice(["main", "develop", "feature/payment-v2"]),
            "ci.duration_sec": duration, "message": f"{pipeline} {stage} {status} in {duration}s"}


def main():
    plan = [("demo-app-logs", app_doc, 3000), ("demo-security-logs", security_doc, 1500),
            ("demo-k8s-logs", k8s_doc, 2000), ("demo-cicd-logs", cicd_doc, 1500)]
    for index, make, count in plan:
        es("DELETE", f"/{index}")
        es("PUT", f"/{index}", {"settings": {"number_of_replicas": 0},
                                "mappings": {"properties": {"@timestamp": {"type": "date"},
                                                            **nested_props(MAPPINGS[index])}}})
        lines = []
        for _ in range(count):
            lines.append(json.dumps({"index": {}}))
            lines.append(json.dumps(nested(make())))
        result = es("POST", f"/{index}/_bulk?refresh=true", "\n".join(lines) + "\n", ndjson=True)
        if result.get("errors"):
            raise SystemExit(f"{index}: bulk hatasi")
        print(f"[+] {index}: {count} belge")


def nested_props(flat):
    """{'a.b': {'type': 'keyword'}} -> mapping 'properties' agaci"""
    out = {}
    for key, mapping in flat.items():
        cur = out
        parts = key.split(".")
        for part in parts[:-1]:
            cur = cur.setdefault(part, {"properties": {}})["properties"]
        cur[parts[-1]] = mapping
    return out


if __name__ == "__main__":
    main()
