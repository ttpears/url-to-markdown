#!/bin/bash
xvfb-run --server-args="-screen 0 1920x1080x24" python url-to-markdown.py "$@"
