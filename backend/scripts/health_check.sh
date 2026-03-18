#!/usr/bin/env bash
# Backend convenience wrapper – delegates to the canonical infra health-check script.
# Usage: health_check.sh [--url <endpoint>] ...
#
# Checks these endpoints by default:
#   http://localhost:8000/health   (liveness)
#   http://localhost:8000/ready    (readiness)
#   http://localhost:8000/metrics  (Prometheus)
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
INFRA_SCRIPT="${SCRIPT_DIR}/../../infra/scripts/health_check.sh"

if [[ ! -f "${INFRA_SCRIPT}" ]]; then
  echo "ERROR: Infra health-check script not found at ${INFRA_SCRIPT}" >&2
  exit 1
fi

exec bash "${INFRA_SCRIPT}" "$@"
