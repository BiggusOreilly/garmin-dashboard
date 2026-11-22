#!/bin/bash
set -u
umask 077
cd "$(dirname "$0")" || exit 1
if [ ! -x .venv/bin/python ]; then
  printf 'Please double-click Setup Garmin Dashboard.command first.\n'
  status=1
else
  .venv/bin/python -m companion.export_run --reveal
  status=$?
fi
printf '\n'
read -r -p 'Press Return to close. ' _
exit "$status"
