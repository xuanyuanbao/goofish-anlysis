#!/usr/bin/env bash
set -euo pipefail

if command -v docker >/dev/null 2>&1; then
  echo "[INFO] Docker is already installed."
  exit 0
fi

if ! command -v curl >/dev/null 2>&1; then
  if command -v apt-get >/dev/null 2>&1; then
    sudo apt-get update
    sudo apt-get install -y curl ca-certificates
  elif command -v yum >/dev/null 2>&1; then
    sudo yum install -y curl ca-certificates
  elif command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y curl ca-certificates
  else
    echo "[ERROR] curl is required, but no supported package manager was found."
    exit 1
  fi
fi

curl -fsSL https://get.docker.com | sh
sudo systemctl enable --now docker

echo "[INFO] Docker installation finished."
echo "[INFO] If you want to run docker without sudo, execute:"
echo "       sudo usermod -aG docker \$USER"
