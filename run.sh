#!/usr/bin/env bash
cd "$(dirname "$0")"

PY="$(command -v python3 || command -v python || true)"
if [ -z "$PY" ]; then
  echo
  echo "Could not find Python. Install Python 3.11 from https://python.org and re-run."
  read -r -p "Press Enter to close..."
  exit 1
fi

if [ ! -x ".venv/bin/python" ]; then
  echo
  echo "First run: setting up a private environment for the game..."
  "$PY" -m venv .venv
  if ! .venv/bin/python -m pip install --upgrade pip; then
    echo
    echo "Failed to install pip. Check your internet connection and re-run."
    read -r -p "Press Enter to close..."
    exit 1
  fi
  if ! .venv/bin/python -m pip install "pygame-ce>=2.5"; then
    echo
    echo "Failed to install pygame-ce. Check your internet connection and re-run."
    read -r -p "Press Enter to close..."
    exit 1
  fi
fi

.venv/bin/python main.py
if [ $? -ne 0 ]; then
  echo
  echo "The game exited with an error. Tell the developer what you saw."
  read -r -p "Press Enter to close..."
fi