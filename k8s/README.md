# Kubernetes Microservices Architecture (DevOpsDays Bogotá 2026)

Polyglot microservices deployment for **eBPF No-Code Observability**, configured for Minikube and standard Kubernetes clusters.

---

## 🏛️ Topology & Dependency Graph

```
[Client / curl]
      │
      ▼ HTTP (Port 8000)
┌──────────────────────────────────────────────────────────┐
│ gateway-py (FastAPI / Python 3.14)                       │
└──────────────┬────────────────────────────┬──────────────┘
               │ POST /pay                  │ POST /reserve
               ▼                            ▼
┌──────────────────────────────┐  ┌──────────────────────────────┐
│ payment-go (Gin / Go 1.26)   │  │ inventory-rs (Axum / Rust)   │
└──────────────┬───────────────┘  └──────────────┬───────────────┘
               │ GET /check-fraud                │ GET /quote
               ▼                                 ▼
┌──────────────────────────────┐  ┌──────────────────────────────┐
│ antifraud-fastify (Bun/Node) │  │ shipping-quarkus (Java 25)   │
└──────────────┬───────────────┘  └──────────────────────────────┘
               │                                 │
               ▼                                 ▼
┌──────────────────────────────┐  ┌──────────────────────────────┐
│ valkey:6379 (Valkey 9.1.1)   │  │ postgres:5432 (Postgres 18.6)│
└──────────────────────────────┘  └──────────────────────────────┘
```

---

## 📁 Manifest Structure (One YAML per Microservice / Component)

| Manifest | Kind(s) | Description |
| :--- | :--- | :--- |
| [`postgres.yaml`](./postgres.yaml) | ConfigMap, Deployment, Service | Single PostgreSQL 18.6-trixie instance initialized with `payment_db` and `inventory_db`. |
| [`valkey.yaml`](./valkey.yaml) | Deployment, Service | Valkey 9.1.1-trixie in-memory store for rate limiting, cache, and velocity tracking. |
| [`shipping-quarkus.yaml`](./shipping-quarkus.yaml) | Deployment, Service | Standalone logistics rate calculator (`:8084`). |
| [`antifraud-fastify.yaml`](./antifraud-fastify.yaml) | Deployment, Service | Real-time fraud detection & HMAC signer (`:8083`), backed by Valkey. |
| [`payment-go.yaml`](./payment-go.yaml) | Job, Deployment, Service | Goose migration job (BellSoft hardened base glibc) + Payment processing service (`:8081`). |
| [`inventory-rs.yaml`](./inventory-rs.yaml) | Job, Deployment, Service | Toasty migration & catalog seed job (BellSoft hardened base glibc) + Inventory service (`:8082`). |
| [`gateway-py.yaml`](./gateway-py.yaml) | Deployment, Service | Ingress API gateway (`:8000`) dispatching to payment and inventory services. |
| [`kustomization.yaml`](./kustomization.yaml) | Kustomization | Bundles all resources under namespace `devopsdays`. |

---

## 🚀 Quickstart & Deployment

### 1. Build and Load Images into Minikube

```bash
# Leaf 1: Shipping (Quarkus JVM)
podman save localhost/shipping-quarkus:jvm | minikube image load -

# Leaf 2: Anti-Fraud (Fastify)
podman save localhost/antifraud-fastify:latest | minikube image load -

# Layer 2 Migrations & Services (Payment & Inventory)
podman build -t localhost/payment-go-migrations:latest -f payment-go/Dockerfile.migrations payment-go
podman save localhost/payment-go-migrations:latest localhost/payment-go:latest | minikube image load -

podman build -t localhost/inventory-rs-migrations:latest -f inventory-rs/Dockerfile.migrations inventory-rs
podman save localhost/inventory-rs-migrations:latest localhost/inventory-rs:latest | minikube image load -

# Layer 3: Gateway
podman save localhost/api-server:latest | minikube image load -

# Data Stores
podman save docker.io/valkey/valkey:9.1.1-trixie docker.io/library/postgres:18.6-trixie | minikube image load -
```

### 2. Deploy All Resources

```bash
kubectl apply -k k8s/
```

### 3. Verify Pods & Rollout Status

```bash
kubectl get pods,svc -n devopsdays
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
        "product_id": "0191234a-5b6c-7123-9000-000000000000",
        "quantity": 2,
        "unit_price": "20.00"
      }
    ],
    "coupon_code": "DEVOPSDAYS"
  }'
```

**Expected Response (`HTTP 201 Created`):**
```json
{
  "order_id": "01a03211-0a49-74a6-b82a-fbb25eacca5f",
  "customer_id": "cust_devopsdays_e2e",
  "summary": {
    "subtotal": "40.00",
    "total": "34.00",
    "coupon_applied": "DEVOPSDAYS"
  },
  "payment_status": "confirmed",
  "inventory_status": "reserved"
}
```
