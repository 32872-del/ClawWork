#!/usr/bin/env bash
set -e

python3 -m pip install --upgrade pip
python3 -m pip install -r requirements-fc.txt -t .

# Put Chromium inside the deployed Python package tree when possible.
PLAYWRIGHT_BROWSERS_PATH=0 python3 -m playwright install chromium

