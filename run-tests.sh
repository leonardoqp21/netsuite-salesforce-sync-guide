#!/bin/sh
set -e
cd "$(dirname "$0")"
python3 -m unittest discover -s tests
echo "all tests passed"
