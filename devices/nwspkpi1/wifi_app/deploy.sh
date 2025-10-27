#!/bin/bash
# Deployment script for WiFi Monitor on Raspberry Pi

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}WiFi Monitor Deployment Script${NC}"
echo "==============================="
echo

# Check if running on Raspberry Pi
if [ ! -f /etc/rpi-issue ]; then
    echo -e "${YELLOW}Warning: This doesn't appear to be a Raspberry Pi${NC}"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Create virtual environment and install dependencies
echo -e "${GREEN}Setting up Python virtual environment...${NC}"
python3 -m venv venv

echo -e "${GREEN}Installing Python dependencies...${NC}"
./venv/bin/pip install flask pandas

# Create systemd service
echo -e "${GREEN}Installing systemd service...${NC}"
sudo cp wifi-monitor.service /etc/systemd/system/
sudo systemctl daemon-reload

# Enable and start the service
echo -e "${GREEN}Enabling and starting WiFi Monitor service...${NC}"
sudo systemctl enable wifi-monitor.service
sudo systemctl restart wifi-monitor.service

# Wait a moment for service to start
sleep 2

# Check service status
if sudo systemctl is-active --quiet wifi-monitor.service; then
    echo -e "${GREEN}✓ WiFi Monitor is running!${NC}"
    echo
    echo "Access the web interface at:"
    echo "  http://$(hostname -I | awk '{print $1}'):5002"
    echo
    echo "Useful commands:"
    echo "  View logs:     sudo journalctl -u wifi-monitor.service -f"
    echo "  Stop service:  sudo systemctl stop wifi-monitor.service"
    echo "  Restart:       sudo systemctl restart wifi-monitor.service"
    echo "  Status:        sudo systemctl status wifi-monitor.service"
else
    echo -e "${RED}✗ Service failed to start${NC}"
    echo "Check logs with: sudo journalctl -u wifi-monitor.service -n 50"
    exit 1
fi
