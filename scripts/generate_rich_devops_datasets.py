#!/usr/bin/env python3
import base64
import json
import os
import random
import time
import urllib.request
from datetime import datetime, timezone, timedelta

ES_URL = os.getenv("ES_URL", "http://localhost:9200")
ES_USER = os.getenv("ES_USER", "elastic")
ES_PASSWORD = os.getenv("ES_PASSWORD", "BilginIT454")
auth_token = base64.b64encode(f"{ES_USER}:{ES_PASSWORD}".encode("utf-8")).decode("utf-8")

print("[+] Starting high-volume DevOps sample data generation...")

now = datetime.now(timezone.utc)

def send_bulk(bulk_lines):
    if not bulk_lines:
        return
    data = "\n".join(bulk_lines) + "\n"
    req = urllib.request.Request(
        f"{ES_URL}/_bulk",
        data=data.encode("utf-8"),
        headers={
            "Content-Type": "application/x-ndjson",
            "Authorization": f"Basic {auth_token}"
        }
    )
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode())
        if res.get("errors"):
            print(f"    [!] Bulk partial errors: {len(res.get('items', []))} items")
        else:
            print(f"    [✓] Bulk indexed {len(bulk_lines)//2} docs successfully.")

# -------------------------------------------------------------
# 1. Generate Application Microservice Logs (app-logs-*)
# -------------------------------------------------------------
print("[+] Generating 3,000 Microservice & Web Application Logs...")
services = ["payment-service", "auth-service", "order-service", "frontend-web", "api-gateway", "demo-nginx"]
endpoints = [
    ("/api/v1/orders", "POST", [200, 201, 400, 500]),
    ("/api/v1/payments/process", "POST", [200, 400, 402, 500, 502]),
    ("/api/v1/auth/login", "POST", [200, 401, 403]),
    ("/api/v1/cart", "GET", [200, 304, 500]),
    ("/catalog", "GET", [200, 304]),
    ("/products/featured", "GET", [200, 404]),
    ("/healthz", "GET", [200]),
    ("/static/app.bundle.js", "GET", [200, 304]),
    ("/images/logo.png", "GET", [200, 304])
]
client_ips = [
    "192.168.1.100", "192.168.1.105", "10.0.0.12", "10.0.0.24",
    "198.51.100.77", "203.0.113.45", "185.220.101.5", "172.16.0.88",
    "192.168.50.12", "10.244.1.44"
]
user_agents = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/128.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_6 like Mac OS X) AppleWebKit/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:130.0) Gecko/20100101 Firefox/130.0",
    "curl/8.7.1",
    "Go-http-client/1.1",
    "ELB-HealthChecker/2.0"
]

app_bulk = []
for i in range(3000):
    mins_ago = random.randint(0, 1440) # past 24 hours
    ts = (now - timedelta(minutes=mins_ago, seconds=random.randint(0, 59))).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    ep, method, possible_codes = random.choice(endpoints)
    code = random.choice(possible_codes)
    service = random.choice(services)
    
    if code >= 500:
        level = "ERROR"
        latency = random.randint(450, 2800)
        msg = f"HTTP {method} {ep} - Internal server exception in {service}: connection reset by peer"
    elif code >= 400:
        level = "WARN"
        latency = random.randint(30, 350)
        msg = f"HTTP {method} {ep} - Client warning: resource not found or unauthorized"
    else:
        level = "INFO"
        latency = random.randint(8, 180)
        msg = f"HTTP {method} {ep} - Successfully served request in {latency}ms"

    doc = {
        "@timestamp": ts,
        "service": service,
        "method": method,
        "url": ep,
        "response_code": code,
        "latency_ms": latency,
        "bytes": random.randint(250, 18500),
        "client_ip": random.choice(client_ips),
        "user_agent": random.choice(user_agents),
        "level": level,
        "message": msg,
        "log_type": "application"
    }
    app_bulk.append(json.dumps({"index": {"_index": f"app-logs-{now.strftime('%Y.%m.%d')}"}}))
    app_bulk.append(json.dumps(doc))
    if len(app_bulk) >= 1000:
        send_bulk(app_bulk)
        app_bulk = []
send_bulk(app_bulk)

# -------------------------------------------------------------
# 2. Generate Security & SIEM Attack Logs (system-logs-*)
# -------------------------------------------------------------
print("[+] Generating 1,500 Security & SIEM Threat Logs...")
threat_ips = ["198.51.100.77", "203.0.113.45", "185.220.101.5", "45.154.255.89", "91.240.118.172"]
benign_ips = ["192.168.1.50", "192.168.1.51", "10.0.0.10"]
users = ["root", "admin", "deploy", "ubuntu", "test", "postgres", "oracle", "ftpuser"]
sec_bulk = []

for i in range(1500):
    mins_ago = random.randint(0, 1440)
    ts = (now - timedelta(minutes=mins_ago, seconds=random.randint(0, 59))).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    attack_roll = random.random()
    
    if attack_roll < 0.65:
        # SSH Brute Force
        u = random.choice(users)
        ip = random.choice(threat_ips)
        port = random.randint(32000, 64000)
        doc = {
            "@timestamp": ts,
            "service": "sshd",
            "event": {"category": "authentication", "action": "ssh_login_failed", "outcome": "failure"},
            "client_ip": ip,
            "user": u,
            "level": "ALERT",
            "severity": "HIGH",
            "message": f"Failed password for invalid user {u} from {ip} port {port} ssh2",
            "log_type": "security"
        }
    elif attack_roll < 0.85:
        # Sudo Commands
        u = random.choice(["ubuntu", "deploy", "hakan"])
        cmd = random.choice(["/usr/bin/docker ps", "/bin/systemctl restart nginx", "/usr/bin/apt update", "/bin/cat /etc/shadow"])
        doc = {
            "@timestamp": ts,
            "service": "sudo",
            "event": {"category": "privilege_escalation", "action": "sudo_command", "outcome": "success"},
            "client_ip": "127.0.0.1",
            "user": u,
            "level": "INFO",
            "severity": "LOW",
            "message": f"{u} : TTY=pts/1 ; PWD=/home/{u} ; USER=root ; COMMAND={cmd}",
            "log_type": "system"
        }
    else:
        # Firewall UFW Block / Port Scan
        ip = random.choice(threat_ips)
        dpt = random.choice([22, 23, 80, 443, 3306, 5432, 6379, 8080, 9200])
        doc = {
            "@timestamp": ts,
            "service": "kernel",
            "event": {"category": "network", "action": "firewall_drop", "outcome": "blocked"},
            "client_ip": ip,
            "dest_port": dpt,
            "level": "WARN",
            "severity": "MEDIUM",
            "message": f"[UFW BLOCK] IN=eth0 OUT= MAC=02:42:ac:11:00:02 SRC={ip} DST=10.0.0.5 PROTO=TCP DPT={dpt}",
            "log_type": "security"
        }
        
    sec_bulk.append(json.dumps({"index": {"_index": f"system-logs-{now.strftime('%Y.%m.%d')}"}}))
    sec_bulk.append(json.dumps(doc))
    if len(sec_bulk) >= 1000:
        send_bulk(sec_bulk)
        sec_bulk = []
send_bulk(sec_bulk)

# -------------------------------------------------------------
# 3. Generate Kubernetes Cluster & Pod Logs (k8s-logs-*)
# -------------------------------------------------------------
print("[+] Generating 2,000 Kubernetes Pod & Event Logs...")
k8s_namespaces = ["production", "staging", "ingress-nginx", "kube-system"]
k8s_pods = [
    ("production", "order-service-79db8f8-b8xqw", "order-service"),
    ("production", "payment-service-58dc4-kk9pl", "payment-service"),
    ("production", "auth-service-678bb-mn32k", "auth-service"),
    ("production", "frontend-nginx-546bf-zz901", "frontend-nginx"),
    ("staging", "api-gateway-test-6bb7f-lk890", "api-gateway"),
    ("kube-system", "coredns-768b85b76-pq789", "coredns"),
    ("ingress-nginx", "ingress-nginx-controller-5c8-hh44m", "controller")
]
k8s_bulk = []

for i in range(2000):
    mins_ago = random.randint(0, 1440)
    ts = (now - timedelta(minutes=mins_ago, seconds=random.randint(0, 59))).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    ns, pod, container = random.choice(k8s_pods)
    roll = random.random()
    
    if roll < 0.08:
        level = "FATAL"
        event = "OOMKilled"
        msg = f"Container {container} exceeded memory limit (cgroup limit exceeded). Pod terminated with OOMKilled."
    elif roll < 0.18:
        level = "ERROR"
        event = "CrashLoopBackOff"
        msg = f"Readiness probe failed: HTTP probe failed with statuscode: 503. Back-off restarting failed container."
    elif roll < 0.35:
        level = "WARN"
        event = "HighCPU"
        msg = f"Pod {pod} CPU throttling detected: 82% throttling over 5 minute period."
    else:
        level = "INFO"
        event = "Ready"
        msg = f"Pod {pod} healthy, serving traffic normally. All health probes passed."

    doc = {
        "@timestamp": ts,
        "kubernetes": {
            "namespace": ns,
            "pod": {"name": pod},
            "container": {"name": container},
            "node": {"name": random.choice(["kind-control-plane", "kind-worker-1", "kind-worker-2"])}
        },
        "event": {"reason": event},
        "level": level,
        "message": msg,
        "log_type": "k8s"
    }
    k8s_bulk.append(json.dumps({"index": {"_index": f"k8s-logs-{now.strftime('%Y.%m.%d')}"}}))
    k8s_bulk.append(json.dumps(doc))
    if len(k8s_bulk) >= 1000:
        send_bulk(k8s_bulk)
        k8s_bulk = []
send_bulk(k8s_bulk)

# -------------------------------------------------------------
# 4. Generate CI/CD Pipeline Logs (cicd-logs-*)
# -------------------------------------------------------------
print("[+] Generating 1,500 CI/CD Pipeline & Build Logs...")
ci_tools = ["jenkins", "gitlab-ci", "github-actions"]
branches = ["main", "feature/payment-gateway-v2", "bugfix/auth-token-refresh", "release/v2.4.0"]
stages = ["unit-test", "sonarqube-analysis", "trivy-container-scan", "docker-build", "helm-deploy-staging", "k8s-deploy-production"]
cicd_bulk = []

for i in range(1500):
    mins_ago = random.randint(0, 1440)
    ts = (now - timedelta(minutes=mins_ago, seconds=random.randint(0, 59))).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    tool = random.choice(ci_tools)
    branch = random.choice(branches)
    stage = random.choice(stages)
    pipe_num = random.randint(101, 199)
    
    roll = random.random()
    if roll < 0.15:
        status = "FAILED"
        dur = random.randint(35, 140)
        msg = f"Pipeline #{pipe_num} failed at stage '{stage}': Exit code 1. Assertion failure or vulnerability threshold exceeded."
    elif roll < 0.25:
        status = "UNSTABLE"
        dur = random.randint(90, 220)
        msg = f"Pipeline #{pipe_num} finished with warnings at stage '{stage}': Non-blocking code smells detected."
    else:
        status = "SUCCESS"
        dur = random.randint(45, 180)
        msg = f"Pipeline #{pipe_num} passed stage '{stage}' in {dur}s. Artifacts pushed to registry."

    doc = {
        "@timestamp": ts,
        "ci": {
            "tool": tool,
            "pipeline_id": f"build-{pipe_num}",
            "stage": stage,
            "status": status,
            "branch": branch,
            "duration_sec": dur
        },
        "level": "ERROR" if status == "FAILED" else "INFO",
        "message": msg,
        "log_type": "cicd"
    }
    cicd_bulk.append(json.dumps({"index": {"_index": f"cicd-logs-{now.strftime('%Y.%m.%d')}"}}))
    cicd_bulk.append(json.dumps(doc))
    if len(cicd_bulk) >= 1000:
        send_bulk(cicd_bulk)
        cicd_bulk = []
send_bulk(cicd_bulk)

print("[✓] All sample DevOps datasets generated and indexed successfully!")
