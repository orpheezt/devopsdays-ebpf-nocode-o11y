#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

MODE="${1:-local}" # "local", "smoke", or "k8s"
GATEWAY_URL="${GATEWAY_URL:-http://localhost:8000}"

echo "================================================================="
echo "  🚀 Grafana k6 Load Generator (DevOpsDays Bogotá 2026)"
echo "  Target Mode: ${MODE}"
echo "================================================================="

run_local_k6() {
  local script_file="$1"
  if command -v k6 &> /dev/null; then
    echo "▶️ Running via local k6 CLI..."
    GATEWAY_URL="${GATEWAY_URL}" k6 run "${ROOT_DIR}/k6/${script_file}"
  elif command -v podman &> /dev/null; then
    echo "▶️ Running via Podman container..."
    podman run --rm -i --net=host \
      -e GATEWAY_URL="${GATEWAY_URL}" \
      -v "${ROOT_DIR}/k6:/k6:ro,z" \
      docker.io/grafana/k6:latest run "/k6/${script_file}"
  elif command -v docker &> /dev/null; then
    echo "▶️ Running via Docker container..."
    docker run --rm -i --net=host \
      -e GATEWAY_URL="${GATEWAY_URL}" \
      -v "${ROOT_DIR}/k6:/k6:ro" \
      docker.io/grafana/k6:latest run "/k6/${script_file}"
  else
    echo "❌ Error: Neither k6, podman, nor docker was found in PATH."
    exit 1
  fi
}

case "${MODE}" in
  "smoke")
    echo "🔥 Executing 5-second smoke test..."
    run_local_k6 "smoke-test.js"
    ;;
  "local")
    echo "📊 Executing full e-commerce checkout load test..."
    run_local_k6 "checkout-load-test.js"
    ;;
  "k8s")
    echo "☸️ Launching in-cluster k6 Kubernetes Job..."
    kubectl delete job k6-load-test -n devopsdays --ignore-not-found=true
    kubectl apply -f "${ROOT_DIR}/k8s/k6-job.yaml"
    echo "⏳ Waiting for k6 Job pod..."
    kubectl wait --for=condition=Ready pod -l app.kubernetes.io/name=k6 -n devopsdays --timeout=30s || true
    echo "📜 Streaming k6 Job logs:"
    kubectl logs -f job/k6-load-test -n devopsdays
    ;;
  *)
    echo "Usage: $0 [local|smoke|k8s]"
    exit 1
    ;;
esac

echo "================================================================="
echo "  🏁 Test Complete!"
echo "  Explore APM & Traces at: http://localhost:3000"
echo "================================================================="
