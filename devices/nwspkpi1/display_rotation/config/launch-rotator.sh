#!/bin/bash

# Debug logging
exec 1> >(logger -s -t $(basename $0)) 2>&1
echo "Script started"
echo "Current user: $(whoami)"
echo "Current directory: $(pwd)"
echo "PATH: $PATH"

# Path to your pages directory
PAGES_DIR="/home/nwspkpi1/telescreen/devices/nwspkpi1/display_rotation/pages"

# Start a simple PHP server in the background
cd "$PAGES_DIR"
php -S 0.0.0.0:8080 &
PHP_SERVER_PID=$!

# Wait a moment for the server to start
sleep 2

# Launch Epiphany browser with the rotator page
epiphany-browser "http://localhost:8080/rotator.html"

# If Epiphany browser is closed, kill the PHP server
kill $PHP_SERVER_PID