#!/bin/bash
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null 2>&1; then
  echo 'Python 3.10 or newer is required. Install Python from python.org, then try again.'
  read -r -p 'Press Return to close.'
  exit 1
fi
python3 -c 'import sys; assert sys.version_info >= (3,10)' || { echo 'Python 3.10 or newer is required.'; read -r; exit 1; }
open http://127.0.0.1:8765/
python3 -m learninglab --db data/full.sqlite serve
