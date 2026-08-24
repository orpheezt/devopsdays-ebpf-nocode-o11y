import http from 'k6/http';
import { check, sleep } from 'k6';
import { Trend, Rate, Counter } from 'k6/metrics';

// Custom metrics for observability validation
const checkoutDuration = new Trend('checkout_duration_ms');
const errorRate = new Rate('checkout_errors');
const successfulOrders = new Counter('successful_orders');

// Seed products from inventory-rs database
const PRODUCTS = [
  { id: '0191234a-5b6c-7123-9000-000000000001', name: 'Headphones', price: '150.00' },
  { id: '0191234a-5b6c-7123-9000-000000000002', name: 'Keyboard', price: '95.50' },
  { id: '0191234a-5b6c-7123-9000-000000000003', name: 'Desk Chair', price: '280.00' },
  { id: '0191234a-5b6c-7123-9000-000000000004', name: 'Docking Station', price: '120.00' },
];

const COUPONS = ['DEVOPSDAYS', 'EBPF_DISCOUNT', 'SUMMER2026', ''];

const BASE_URL = __ENV.GATEWAY_URL || 'http://localhost:8000';

export const options = {
  stages: [
    { duration: '30s',  target: 30  }, // Ramp-up warm-up
    { duration: '60s',  target: 80  }, // Sustained load
    { duration: '90s',  target: 150 }, // Stress peak
    { duration: '60s',  target: 100 }, // Hold
    { duration: '60s',  target: 0   }, // Ramp-down
  ],
  thresholds: {
    'http_req_duration': ['p(95)<1500'],
    'checkout_errors': ['rate<0.25'],
  },
};

export default function () {
  const rand = Math.random();
  let customerId = `cust_k6_${__VU}_${__ITER}`;
  let items = [];
  let coupon = COUPONS[Math.floor(Math.random() * COUPONS.length)];

  if (rand < 0.80) {
    // Scenario 1: Standard Valid Checkout (80% traffic)
    const product = PRODUCTS[Math.floor(Math.random() * PRODUCTS.length)];
    const quantity = Math.floor(Math.random() * 3) + 1;
    items.push({
      product_id: product.id,
      quantity: quantity,
      unit_price: product.price,
    });
  } else if (rand < 0.90) {
    // Scenario 2: Multi-Item High-Value Checkout (10% traffic - exercises anti-fraud risk score)
    items.push({
      product_id: PRODUCTS[0].id,
      quantity: 5,
      unit_price: '1200.00',
    });
    items.push({
      product_id: PRODUCTS[2].id,
      quantity: 4,
      unit_price: '850.00',
    });
  } else {
    // Scenario 3: Fault Injection (10% traffic - exercises RED Error Rate and 4xx/5xx tracing)
    items.push({
      product_id: '00000000-0000-0000-0000-000000000000',
      quantity: 1,
      unit_price: '50.00',
    });
  }

  const payload = JSON.stringify({
    customer_id: customerId,
    items: items,
    coupon_code: coupon || undefined,
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
      'User-Agent': 'k6-load-generator/1.0',
    },
    tags: { name: 'POST /order' },
  };

  const startTime = new Date();
  const res = http.post(`${BASE_URL}/order`, payload, params);
  const duration = new Date() - startTime;

  checkoutDuration.add(duration);

  if (res.status === 200 || res.status === 201) {
    errorRate.add(0);
    successfulOrders.add(1);
    check(res, {
      'status is 200/201': (r) => r.status === 200 || r.status === 201,
      'has valid order_id': (r) => {
        try {
          const body = JSON.parse(r.body);
          return body.order_id !== undefined && body.payment_status === 'confirmed';
        } catch {
          return false;
        }
      },
    });
  } else {
    errorRate.add(1);
    check(res, {
      'handled error response': (r) => r.status >= 400,
    });
  }

  // Realistic user think time between actions (100ms - 400ms)
  sleep(0.1 + Math.random() * 0.3);
}
