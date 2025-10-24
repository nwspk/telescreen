#!/bin/bash
# Enable debug mode
set -x
echo "Script started"
# Print diagnostic information
echo "Current user: $(whoami)"
echo "Current directory: $(pwd)"
echo "PATH: $PATH"
# Get the absolute path to the config directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
CONFIG_DIR="$BASE_DIR/config"
PAGES_DIR="$BASE_DIR/pages"
echo "Config directory: $CONFIG_DIR"
# Change to the config directory
cd "$CONFIG_DIR" || exit 1
# Start PHP development server with router
php -S 0.0.0.0:8080 router.php &
PHP_SERVER_PID=$!
# Wait a moment for the server to start
sleep 2
# Start the web browser in full screen mode
# Update this path based on your system's browser
epiphany-browser 
"http://localhost:8080/rotator.html" &
BROWSER_PID=$!
# Wait for signals
trap "kill $PHP_SERVER_PID $BROWSER_PID; exit" SIGINT SIGTERM
# Keep the script running
wait
