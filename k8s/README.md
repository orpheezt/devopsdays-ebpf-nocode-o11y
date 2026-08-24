# Kubernetes Microservices Architecture (DevOpsDays Bogotá 2026)

Production-hardened polyglot microservices deployment for **eBPF No-Code Observability**, featuring **ArgoCD Sync Waves & Hooks** lifecycle orchestration, state persistence, secret management, and Kubernetes best practices.

---

## 🏛️ Topology & Dependency Graph

```
[Client / curl]
      │
      ▼ HTTP (Port 8000)
┌──────────────────────────────────────────────────────────┐
│ gateway-py (FastAPI / Python 3.14 on BellSoft Alpaquita) │
└──────────────┬────────────────────────────┬──────────────┘
               │ POST /pay                  │ POST /reserve
               ▼                            ▼
┌──────────────────────────────┐  ┌──────────────────────────────┐
│ payment-go (Gin / Go 1.26    │  │ inventory-rs (Axum / Rust    │
│ on BellSoft Alpaquita)       │  │ on Static Alpine)            │
└──────────────┬───────────────┘  └──────────────┬───────────────┘
               │ GET /check-fraud                │ GET /quote
               ▼                                 ▼
┌──────────────────────────────┐  ┌──────────────────────────────┐
│ antifraud-fastify            │  │ shipping-quarkus (Java 25    │
│ (Bun 1.4.0 Distroless)       │  │ on BellSoft Hardened JRE)    │
└──────────────┬───────────────┘  └──────────────────────────────┘
               │                                 │
               ▼                                 ▼
┌──────────────────────────────┐  ┌──────────────────────────────┐
│ valkey:6379 (Valkey 9.1.1)   │  │ postgres:5432 (Postgres 18.6)│
└──────────────────────────────┘  └──────────────────────────────┘
```

---

## 🌊 ArgoCD Sync Waves & Deployment Lifecycle

The deployment is ordered into deterministic phases using `argocd.argoproj.io/sync-wave` and `argocd.argoproj.io/hook`:

```
Wave -1 (Namespace)
  └── Namespace: devopsdays

Wave 0 (Secrets & Data Tier)
  ├── secretGenerator (postgres-secrets, antifraud-secrets)
  ├── StatefulSet: postgres (10Gi PVC storage) + ConfigMap: postgres-init-db
  ├── Deployment: valkey
  └── ConfigMaps: payment-go-seeds-sql, inventory-rs-seeds-sql

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

Wave 4 (API Gateway)
  └── Deployment: gateway-py (:8000)
```

> **Dual Compatibility**: In addition to ArgoCD Sync Waves, all Jobs specify `ttlSecondsAfterFinished: 120` and `initContainers` waiting for PostgreSQL, so standard `kubectl apply -k k8s/` works reliably in local Minikube environments.

---

## 📁 Manifest Structure

| Manifest | Kind(s) | ArgoCD Wave | Description |
| :--- | :--- | :--- | :--- |
| [`namespace.yaml`](./namespace.yaml) | Namespace | Wave -1 | Dedicated `devopsdays` namespace with standard labels. |
| [`kustomization.yaml`](./kustomization.yaml) | Kustomization | Wave 0 | Bundles all resources and generates `postgres-secrets` and `antifraud-secrets`. |
| [`postgres.yaml`](./postgres.yaml) | ConfigMap, StatefulSet, Service | Wave 0 | PostgreSQL 18.6-trixie `StatefulSet` with 10Gi PersistentVolumeClaim and startup probes. |
| [`valkey.yaml`](./valkey.yaml) | Deployment, Service | Wave 0 | Valkey 9.1.1-trixie in-memory cache/store with startup probes. |
| [`payment-go.yaml`](./payment-go.yaml) | Job (migrations), Job (seeds), ConfigMap, Deployment, Service | Waves 0, 1, 2, 3 | Goose migration Job (Wave 1) + Seed Job (Wave 2) + Payment service (Wave 3). |
| [`inventory-rs.yaml`](./inventory-rs.yaml) | Job (migrations), Job (seeds), ConfigMap, Deployment, Service | Waves 0, 1, 2, 3 | Toasty migration Job (Wave 1) + Seed Job (Wave 2) + Inventory service (Wave 3). |
| [`shipping-quarkus.yaml`](./shipping-quarkus.yaml) | Deployment, Service | Wave 3 | Standalone logistics rate calculator (`:8084`) on BellSoft Liberica Hardened JRE 25. |
| [`antifraud-fastify.yaml`](./antifraud-fastify.yaml) | Deployment, Service | Wave 3 | Real-time fraud detection (`:8083`) on official Bun 1.4.0 Distroless. |
| [`gateway-py.yaml`](./gateway-py.yaml) | Deployment, Service | Wave 4 | Ingress API gateway (`:8000`) on BellSoft Alpaquita base. |
| [`argocd-application.yaml`](./argocd-application.yaml) | Application | N/A | Turnkey ArgoCD Application custom resource for GitOps. |

---

## 🚀 Quickstart & Deployment

### 1. Build and Load Images into Minikube

```bash
# Data Stores
podman save docker.io/valkey/valkey:9.1.1-trixie docker.io/library/postgres:18.6-trixie | minikube image load -

# Leaf 1: Shipping (Quarkus JVM on Liberica JRE 25)
podman save localhost/shipping-quarkus:jvm | minikube image load -

# Leaf 2: Anti-Fraud (Bun 1.4.0 Distroless)
podman build -t localhost/antifraud-fastify:latest -f antifraud-fastify/Dockerfile antifraud-fastify
podman save localhost/antifraud-fastify:latest | minikube image load -

# Layer 2 Migrations & Services (Payment & Inventory)
podman build -t localhost/payment-go-migrations:latest -f payment-go/Dockerfile.migrations payment-go
podman build -t localhost/payment-go:latest -f payment-go/Dockerfile payment-go
podman save localhost/payment-go-migrations:latest localhost/payment-go:latest | minikube image load -

podman build -t localhost/inventory-rs-migrations:latest -f inventory-rs/Dockerfile.migrations inventory-rs
podman build -t localhost/inventory-rs:latest -f inventory-rs/Dockerfile inventory-rs
podman save localhost/inventory-rs-migrations:latest localhost/inventory-rs:latest | minikube image load -

# Layer 3: Gateway (Python 3.14 on BellSoft Alpaquita)
podman build -t localhost/api-server:latest -f gateway-py/Dockerfile gateway-py
podman save localhost/api-server:latest | minikube image load -
```

### 2. Deploy via Kustomize (Minikube / Local)

```bash
kubectl apply -k k8s/
```

### 3. Or Deploy via ArgoCD (GitOps)

```bash
kubectl apply -f k8s/argocd-application.yaml
```

### 4. Verify Pods & Rollout Status

```bash
kubectl get pods,svc,jobs,pvc,statefulset -n devopsdays
```

---

## 🧪 Testing & Verification

### Port-Forward Gateway

```bash
kubectl port-forward svc/gateway-py 8000:8000 -n devopsdays
```

### Run End-to-End Checkout Test

```bash
curl -X POST http://localhost:8000/order \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "cust_devopsdays_e2e",
    "items": [
      {
        "product_id": "0191234a-5b6c-7123-9000-000000000003",
        "quantity": 2,
        "unit_price": "30.00"
      }
    ],
    "coupon_code": "DEVOPSDAYS"
  }'
```

**Expected Response (`HTTP 201 Created`):**
```json
{
  "order_id": "01a03225-73d1-70cf-9106-9d2c0fb0a79a",
  "customer_id": "cust_devopsdays_e2e",
  "summary": {
    "subtotal": "60.00",
    "total": "51.00",
    "coupon_applied": "DEVOPSDAYS"
  },
  "payment_status": "confirmed",
  "inventory_status": "reserved"
}
```
