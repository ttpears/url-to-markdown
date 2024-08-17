#!/bin/bash

COMMAND=$1
URL=$2

if [ "$COMMAND" == "convert" ]; then
    xvfb-run --server-args="-screen 0 1920x1080x24" python url-to-markdown.py "$URL"
elif [ "$COMMAND" == "crawl" ]; then
    xvfb-run --server-args="-screen 0 1920x1080x24" python crawler.py "$URL"
else
    echo "Invalid command. Use 'convert' to convert a URL or 'crawl' to crawl a site."
fi
