import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE_URL = __ENV.GATEWAY_URL || 'http://localhost:8000';

export const options = {
  vus: 1,
  iterations: 10,
  thresholds: {
    'http_req_failed': ['rate<0.1'],
    'http_req_duration': ['p(95)<500'],
  },
};

export default function () {
  const payload = JSON.stringify({
    customer_id: `smoke_user_${__ITER}`,
    items: [
      {
        product_id: '0191234a-5b6c-7123-9000-000000000003',
        quantity: 2,
        unit_price: '30.00',
      },
    ],
    coupon_code: 'DEVOPSDAYS',
  });

  const res = http.post(`${BASE_URL}/order`, payload, {
    headers: {
      'Content-Type': 'application/json',
      'User-Agent': 'k6-smoke-test/1.0',
    },
  });

  check(res, {
    'status is 201': (r) => r.status === 201,
    'order is confirmed': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.payment_status === 'confirmed' && body.inventory_status === 'reserved';
      } catch {
        return false;
      }
    },
  });

  sleep(0.5);
}
