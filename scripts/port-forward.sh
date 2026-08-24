#!/usr/bin/env bash
set -euo pipefail

NAMESPACE="${NAMESPACE:-devopsdays}"

echo "================================================================="
echo "  🔌 Port-Forwarding DevOpsDays eBPF Observability Services"
echo "================================================================="
echo "  • Grafana APM Dashboard:  http://localhost:3000 (admin/devopsdays2026)"
echo "  • Tempo Distributed Trace: http://localhost:3200"
echo "  • Prometheus Metrics:     http://localhost:9090"
echo "  • API Gateway:            http://localhost:8000"
echo "================================================================="
echo "Press Ctrl+C to terminate all port forwards."

PIDS=()

cleanup() {
  echo ""
  echo "🛑 Stopping port forwards..."
  for pid in "${PIDS[@]}"; do
    kill "${pid}" 2>/dev/null || true
  done
  wait 2>/dev/null || true
  echo "✨ Done."
}

trap cleanup SIGINT SIGTERM EXIT

kubectl port-forward svc/grafana 3000:3000 -n "${NAMESPACE}" >/dev/null 2>&1 &
PIDS+=($!)

kubectl port-forward svc/tempo 3200:3200 -n "${NAMESPACE}" >/dev/null 2>&1 &
PIDS+=($!)

kubectl port-forward svc/prometheus 9090:9090 -n "${NAMESPACE}" >/dev/null 2>&1 &
PIDS+=($!)

kubectl port-forward svc/gateway-py 8000:8000 -n "${NAMESPACE}" >/dev/null 2>&1 &
PIDS+=($!)

wait
