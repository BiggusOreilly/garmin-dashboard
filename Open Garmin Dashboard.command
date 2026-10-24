#!/bin/bash
set -u
umask 077
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  printf 'Please double-click Setup Garmin Dashboard.command first.\n'
  read -r -p 'Press Return to close. ' _
  exit 1
fi
printf 'Opening Stride in your browser.\nKeep this window open while using the dashboard. Close it to stop the local server.\n'
.venv/bin/python -m companion open
