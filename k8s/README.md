# Kubernetes Microservices & eBPF Observability (DevOpsDays Bogotá 2026)

Production-hardened polyglot microservices deployment with **Grafana Beyla (eBPF No-Code Observability)**, **ArgoCD Sync Waves & Hooks** lifecycle orchestration, state persistence, secret management, **Grafana k6** load generation, and Kubernetes best practices.

---

## 🏛️ Topology & eBPF Observability Graph

```
                        ┌──────────────────────────────────────────────────────────┐
                        │              Grafana k6 Load Generator                   │
                        │  (Local Podman/Docker or In-Cluster Job k6-load-test)    │
                        └────────────────────────────┬─────────────────────────────┘
                                                     │ HTTP POST /order
                                                     ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ Kubernetes Pods (Namespace: devopsdays)                                                                     │
│                                                                                                             │
│                            ┌──────────────────────────────────────────────────────────┐                     │
│                            │ gateway-py (FastAPI / Python 3.14 on BellSoft Alpaquita) │                     │
│                            └──────────────┬────────────────────────────┬──────────────┘                     │
│                                           │ POST /pay                  │ POST /reserve                      │
│                                           ▼                            ▼                                    │
│                            ┌──────────────────────────────┐  ┌──────────────────────────────┐               │
│                            │ payment-go (Gin / Go 1.26    │  │ inventory-rs (Axum / Rust    │               │
│                            │ on BellSoft Alpaquita)       │  │ on Static Alpine)            │               │
│                            └──────────────┬───────────────┘  └──────────────┬───────────────┘               │
│                                           │ GET /check-fraud                │ GET /quote                    │
│                                           ▼                                 ▼                               │
│                            ┌──────────────────────────────┐  ┌──────────────────────────────┐               │
│                            │ antifraud-fastify            │  │ shipping-quarkus (Java 25    │               │
│                            │ (Bun 1.4.0 Distroless)       │  │ on BellSoft Hardened JRE)    │               │
│                            └──────────────┬───────────────┘  └──────────────────────────────┘               │
│                                           │                                 │                               │
│                                           ▼                                 ▼                               │
│                            ┌──────────────────────────────┐  ┌──────────────────────────────┐               │
│                            │ valkey:6379 (Valkey 9.1.1)   │  │ postgres:5432 (Postgres 18.6)│               │
│                            └──────────────────────────────┘  └──────────────────────────────┘               │
└───────────────────────────────────────────────────┬─────────────────────────────────────────────────────────┘
                                                    │ Intercepted at Linux Kernel (kprobes/uprobes/sock_ops)
                                                    ▼
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ Grafana Beyla DaemonSet (eBPF Auto-Instrumentation - Zero Code Changes)                                     │
│   • Auto-discovers all 'devopsdays' pods                                                                    │
│   • Captures HTTP/gRPC RED metrics, status codes, and latency percentiles                                   │
│   • Captures PostgreSQL queries & Valkey/Redis commands                                                     │
│   • W3C tracecontext propagation & distributed trace generation                                             │
└───────────────────────────┬─────────────────────────────────────────────────────────┬───────────────────────┘
                            │ OTLP Traces (:4318)                                     │ Prometheus Scrape (:9090)
                            ▼                                                         ▼
┌──────────────────────────────────────────────────────────┐  ┌───────────────────────────────────────────────┐
│ Grafana Tempo (:3200)                                    │  │ Prometheus TSDB (:9090)                       │
│ Distributed Trace Storage & Search                       │  │ RED Metrics & Kubernetes Resource Metadata    │
└───────────────────────────┬──────────────────────────────┘  └───────────────────────┬───────────────────────┘
                            │                                                         │
                            └───────────────────────────┬─────────────────────────────┘
                                                        │ Queries
                                                        ▼
                                       ┌──────────────────────────────────┐
                                       │ Grafana Dashboard (:3000)        │
                                       │ Pre-provisioned Beyla APM & RED  │
                                       └──────────────────────────────────┘
```

---

## 🌊 ArgoCD Sync Waves & Deployment Lifecycle

The deployment is ordered into deterministic phases using `argocd.argoproj.io/sync-wave` and `argocd.argoproj.io/hook`:

```
Wave -1 (Namespace)
  └── Namespace: devopsdays

Wave 0 (Secrets, Data Tier & Observability Backends)
  ├── secretGenerator (postgres-secrets, antifraud-secrets)
  ├── StatefulSet: postgres (10Gi PVC storage) + ConfigMap: postgres-init-db
  ├── Deployment: valkey
  ├── ConfigMaps: payment-go-seeds-sql, inventory-rs-seeds-sql
  ├── Observability: Tempo Deployment (:3200, :4317, :4318)
  ├── Observability: Prometheus Deployment (:9090) + RBAC
  └── Observability: Grafana Deployment (:3000) + Pre-provisioned Beyla APM Dashboard

Wave 1 (Schema Migrations - Hook: Sync)
  ├── Job: payment-go-migrations (Goose)
  └── Job: inventory-rs-migrations (Toasty)

Wave 2 (Database Seeding - Hook: Sync)
  ├── Job: payment-go-seeds
  └── Job: inventory-rs-seeds

Wave 3 (Core Microservices)
  ├── Deployment: shipping-quarkus (:8084)
  ├── Deployment: antifraud-fastify (:8083)
  ├── Deployment: payment-go (:8081)
  └── Deployment: inventory-rs (:8082)

Wave 4 (API Gateway & eBPF Auto-Instrumentation)
  ├── Deployment: gateway-py (:8000)
  └── DaemonSet: beyla (eBPF probes, route mapping, W3C trace propagation)

Wave 5 (Load Testing - Optional / On-Demand)
  └── Job: k6-load-test (Grafana k6 in-cluster traffic generator)
```

---

## 📁 Manifest Structure

| Manifest | Kind(s) | ArgoCD Wave | Description |
| :--- | :--- | :--- | :--- |
| [`namespace.yaml`](./namespace.yaml) | Namespace | Wave -1 | Dedicated `devopsdays` namespace with standard labels. |
| [`kustomization.yaml`](./kustomization.yaml) | Kustomization | Wave 0 | Bundles all resources and generates `postgres-secrets` and `antifraud-secrets`. |
| [`observability/tempo.yaml`](./observability/tempo.yaml) | ConfigMap, Deployment, Service | Wave 0 | Grafana Tempo 3.0.3 single-binary distributed trace storage with OTLP receivers. |
| [`observability/prometheus.yaml`](./observability/prometheus.yaml) | ServiceAccount, ClusterRole, ClusterRoleBinding, ConfigMap, Deployment, Service | Wave 0 | Prometheus v3.14.0 server scraping Beyla `:9090` metrics. |
| [`observability/grafana.yaml`](./observability/grafana.yaml) | ConfigMap (Datasources, Dashboards Provider, Beyla APM JSON), Deployment, Service | Wave 0 | Grafana 13.0.7-ubuntu-slim visualization pre-configured with Tempo and Prometheus data sources. |
| [`postgres.yaml`](./postgres.yaml) | ConfigMap, StatefulSet, Service | Wave 0 | PostgreSQL 18.6-trixie `StatefulSet` with 10Gi PersistentVolumeClaim and startup probes. |
| [`valkey.yaml`](./valkey.yaml) | Deployment, Service | Wave 0 | Valkey 9.1.1-trixie in-memory cache/store with startup probes. |
| [`payment-go.yaml`](./payment-go.yaml) | Job (migrations), Job (seeds), ConfigMap, Deployment, Service | Waves 0, 1, 2, 3 | Goose migration Job (Wave 1) + Seed Job (Wave 2) + Payment service (Wave 3). |
| [`inventory-rs.yaml`](./inventory-rs.yaml) | Job (migrations), Job (seeds), ConfigMap, Deployment, Service | Waves 0, 1, 2, 3 | Toasty migration Job on Rust 1.98.0 (Wave 1) + Seed Job (Wave 2) + Inventory service (Wave 3). |
| [`shipping-quarkus.yaml`](./shipping-quarkus.yaml) | Deployment, Service | Wave 3 | Standalone logistics rate calculator (`:8084`) on BellSoft Liberica Hardened JRE 25. |
| [`antifraud-fastify.yaml`](./antifraud-fastify.yaml) | Deployment, Service | Wave 3 | Real-time fraud detection (`:8083`) on official Bun 1.4.0 Distroless. |
| [`gateway-py.yaml`](./gateway-py.yaml) | Deployment, Service | Wave 4 | Ingress API gateway (`:8000`) on BellSoft Alpaquita base. |
| [`beyla.yaml`](./beyla.yaml) | ServiceAccount, ClusterRole, ClusterRoleBinding, ConfigMap, DaemonSet, Service | Wave 4 | Grafana Beyla 3.33.0 eBPF auto-instrumentation daemonset. |
| [`k6-job.yaml`](./k6-job.yaml) | ConfigMap, Job | Wave 5 | Grafana k6 in-cluster load generator Job. |
| [`argocd-application.yaml`](./argocd-application.yaml) | Application | N/A | Turnkey ArgoCD Application custom resource for GitOps. |

---

## 🚀 Quickstart & Deployment

### 1. Deploy via Kustomize (Minikube / Local)

```bash
kubectl apply -k k8s/
```

### 2. Verify Pods & Rollout Status

```bash
kubectl get pods,daemonset,svc,jobs,pvc,statefulset -n devopsdays
```

---

## 🔬 Observability & Grafana k6 Load Testing

### 1. Start Observability Port-Forwards

Run the port-forwarding helper script to expose all endpoints locally:

```bash
./scripts/port-forward.sh
```

| Service | Local URL | Credentials |
| :--- | :--- | :--- |
| **Grafana APM Dashboard** | [http://localhost:3000](http://localhost:3000) | `admin` / `devopsdays2026` (or auto-logged in as Admin) |
| **Tempo Trace Explorer** | [http://localhost:3200](http://localhost:3200) | N/A |
| **Prometheus Metrics** | [http://localhost:9090](http://localhost:9090) | N/A |
| **API Gateway** | [http://localhost:8000](http://localhost:8000) | N/A |

---

### 2. Run Traffic Simulation with Grafana k6

#### Quick Smoke Test (5 seconds)
```bash
./scripts/run-k6.sh smoke
```

#### Full E-Commerce Load Test (Ramp-up, steady state, bursts, error injection)
```bash
./scripts/run-k6.sh local
```

#### In-Cluster Kubernetes Job
```bash
./scripts/run-k6.sh k8s
```

---

### 3. Explore eBPF Telemetry in Grafana

1. Open **[http://localhost:3000](http://localhost:3000)**.
2. Open the **Grafana Beyla - eBPF Polyglot Microservices APM** dashboard.
3. Observe:
   - **Global Request Rate & Latency Percentiles (p50/p95)** per microservice.
   - **Error Rate (5xx/4xx)** generated by the k6 fault injection scenario.
   - **HTTP Routes breakdown** (`POST /order`, `POST /pay`, `POST /reserve`, `GET /check-fraud`, `GET /quote`).
   - Click on any trace or go to **Explore > Tempo** to inspect a full distributed trace spanning:
     ```
     gateway-py (Python) ──► payment-go (Go) ──► antifraud-fastify (Bun) ──► valkey (Redis)
     gateway-py (Python) ──► inventory-rs (Rust) ──► shipping-quarkus (Java) ──► postgres (SQL)
     ```
     **All captured automatically with zero lines of application tracing code!**
