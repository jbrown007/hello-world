#!/usr/bin/env bash
# One-time setup for WSL (Ubuntu). Run: bash setup.sh
set -euo pipefail

if ! command -v python3 >/dev/null; then
  echo "Installing python3..."
  sudo apt update && sudo apt install -y python3 python3-venv python3-pip
fi

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .

echo
echo "Done. Activate with:  source .venv/bin/activate"
echo "Then try:             ff settings"
