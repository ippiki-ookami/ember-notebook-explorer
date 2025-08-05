#!/bin/bash
# Quick test script to verify --no-cache works
.venv/bin/python ember.py tiny_demo.ipynb --export-json --no-cache 2>/dev/null | python3 -m json.tool | grep -A5 '"components"'