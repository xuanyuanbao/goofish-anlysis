#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

BASE_IMAGE="${BASE_IMAGE:-m.daocloud.io/docker.io/library/python:3.12-slim}"
APT_MIRROR="${APT_MIRROR:-https://mirrors.tuna.tsinghua.edu.cn}"
PIP_INDEX_URL="${PIP_INDEX_URL:-https://pypi.tuna.tsinghua.edu.cn/simple}"
PIP_TRUSTED_HOST="${PIP_TRUSTED_HOST:-pypi.tuna.tsinghua.edu.cn}"
IMAGE_NAME="${IMAGE_NAME:-goofish-analysis:latest}"

cd "${ROOT_DIR}"
docker build \
  --build-arg BASE_IMAGE="${BASE_IMAGE}" \
  --build-arg APT_MIRROR="${APT_MIRROR}" \
  --build-arg PIP_INDEX_URL="${PIP_INDEX_URL}" \
  --build-arg PIP_TRUSTED_HOST="${PIP_TRUSTED_HOST}" \
  -f deploy/linux/Dockerfile \
  -t "${IMAGE_NAME}" \
  .
