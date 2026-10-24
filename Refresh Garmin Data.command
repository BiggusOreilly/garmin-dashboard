#!/bin/bash
set -u
umask 077
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  printf 'Please double-click Setup Garmin Dashboard.command first.\n'
else
  .venv/bin/python -m companion refresh
fi
printf '\nYou can close this window. Double-click Open Garmin Dashboard.command to view your data.\n'
read -r -p 'Press Return to close. ' _
