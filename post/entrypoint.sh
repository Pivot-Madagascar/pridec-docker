#!/bin/bash
# run_script.sh

if [ "$1" == "--analytics" ]; then
    echo "Rebuilding Analytics Tables"
    python scripts/launch_analytics.py
else
    echo "Posting data to instance"
    python scripts/post.py
fi