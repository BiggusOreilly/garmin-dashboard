#!/bin/bash
set -u
umask 077
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  printf 'Please double-click Setup Garmin Dashboard.command first.\n'
else
  .venv/bin/python -m companion full-refresh
fi
read -r -p 'Press Return to close. ' _
