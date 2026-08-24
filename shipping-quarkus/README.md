# shipping-quarkus

Reactive logistics rate calculator microservice built with **Java 25**, **Quarkus 3.x**, and **Gradle Kotlin DSL**. Part of the polyglot e-commerce architecture for DevOpsDays Bogotá 2026.

---

## 🎯 Role & Architecture

`shipping-quarkus` receives shipping rate calculation requests from downstream consumers (primarily `inventory-rs`) and calculates carrier rates, transit times, and volume discounts.

- **Port**: `8084`
- **Runtime**: OpenJDK 25 / Quarkus 3.x
- **Build System**: Gradle Kotlin DSL (`build.gradle.kts`)

```
[gateway-py :8000]
       │
       ▼ (POST /reserve)
[inventory-rs :8082] ───► (GET /quote?destination_country=CO&items_count=1) ───► [shipping-quarkus :8084]
```

---

## 🚀 Endpoints

### 1. Shipping Rate Quote
- **Path**: `GET /quote`
- **Query Parameters**:
  - `destination_country` (String, default: `"CO"`): 2-letter ISO country code.
  - `items_count` (int, default: `1`): Number of items in shipment.
- **Response Payload**:
  ```json
  {
    "carrier": "DHL / Servientrega",
    "cost": 12.50,
    "est_days": 2
  }
  ```

### 2. Health & Probe Endpoints
- **`GET /livez`**: Liveness probe returning HTTP 200 with status `UP`.
- **`GET /readyz`**: Readiness probe returning HTTP 200 with status `UP` verifying carrier rate tables are loaded.

---

## 📦 Rate Calculation Matrix

| Destination Region | Example Countries | Carrier | Base Rate | Per-Item Rate | Est. Transit |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Domestic Colombia** | `CO`, `COL` | DHL / Servientrega | $8.50 | $4.00 | 2 days |
| **Regional LATAM** | `MX`, `BR`, `CL`, `AR`, `PE`, `EC`, `PA` | DHL Express / LATAM | $18.00 | $5.50 | 3 days |
| **North America** | `US`, `USA`, `CA`, `CAN` | FedEx International | $24.00 | $6.00 | 3 days |
| **Global / Other** | `DE`, `FR`, `JP`, `GB`, etc. | DHL Express Worldwide | $35.00 | $8.00 | 5 days |

### Volume Discounts
- **1–4 items**: Standard rate (no discount).
- **5–9 items**: 10% volume discount applied to subtotal.
- **10+ items**: 20% bulk logistics discount applied to subtotal.

---

## 🛠️ Development & Testing

### Running the application in dev mode
```bash
./gradlew quarkusDev
```

### Running unit and integration tests
```bash
./gradlew test
```

### Building the application
```bash
./gradlew build
```

### Manual Verification
```bash
# Liveness probe
curl -s http://localhost:8084/livez

# Readiness probe
curl -s http://localhost:8084/readyz

# Domestic Colombia shipping quote
curl -s "http://localhost:8084/quote?destination_country=CO&items_count=1"

# US shipping quote with 2 items
curl -s "http://localhost:8084/quote?destination_country=US&items_count=2"
```
