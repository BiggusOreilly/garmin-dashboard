#!/bin/bash
set -eu
umask 077
cd "$(dirname "$0")"
trap 'printf "\nSetup stopped. Read the message above, then try again.\nPress Return to close."; read -r _' ERR
printf '\nStride · Private Garmin Dashboard\nChecking your Mac…\n'
PYTHON=""
for candidate in python3.14 python3.13 python3.12 /opt/homebrew/bin/python3 /usr/local/bin/python3 python3; do
  if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3,12) else 1)' 2>/dev/null; then
    PYTHON="$candidate"
    break
  fi
done
if [ -z "$PYTHON" ]; then
  printf '\nPython 3.12 or newer is needed once.\nInstall the macOS universal installer from https://www.python.org/downloads/macos/\nThen double-click this Setup file again. No Terminal commands are needed.\n'
  open 'https://www.python.org/downloads/macos/' || true
  read -r -p 'Press Return to close. ' _
  exit 1
fi
"$PYTHON" -m venv .venv
printf '\nInstalling the official Garmin client and local FIT reader…\n'
.venv/bin/python -m pip install --disable-pip-version-check -r requirements.txt
mkdir -p data
chmod 700 data
.venv/bin/python -m companion setup
printf '\nSetup complete. Next: double-click Refresh Garmin Data.command.\n'
read -r -p 'Press Return to close. ' _
