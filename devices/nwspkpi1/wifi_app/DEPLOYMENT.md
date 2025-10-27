# WiFi Monitor - Raspberry Pi Deployment Guide

## Quick Start (Automated Deployment)

### 1. Transfer Files to Raspberry Pi

From your Mac, in the `nwspkpi1` directory:

```bash
# Replace <raspberry-pi-ip> with your Pi's IP address
rsync -av wifi_app/ pi@<raspberry-pi-ip>:~/wifi_app/
```

Or using the hostname if you have it set up:
```bash
rsync -av wifi_app/ pi@nwspkpi1.local:~/wifi_app/
```

### 2. Run the Deployment Script

SSH into your Raspberry Pi and run the automated deployment:

```bash
ssh pi@<raspberry-pi-ip>
cd ~/wifi_app
chmod +x deploy.sh
./deploy.sh
```

That's it! The script will:
- Install Python dependencies (Flask, Pandas)
- Set up the systemd service
- Start the WiFi Monitor automatically
- Show you the web interface URL

## Manual Deployment (Step-by-Step)

If you prefer to do it manually:

### 1. Install Dependencies

```bash
pip3 install flask pandas
```

### 2. Install Systemd Service

```bash
sudo cp wifi-monitor.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable wifi-monitor.service
sudo systemctl start wifi-monitor.service
```

### 3. Check Status

```bash
sudo systemctl status wifi-monitor.service
```

## Accessing the Web Interface

Once running, access the web interface at:
```
http://<raspberry-pi-ip>:5002
```

For example:
- http://192.168.1.34:5002
- http://nwspkpi1.local:5002

## Managing the Service

### View Logs
```bash
# Real-time logs
sudo journalctl -u wifi-monitor.service -f

# Last 50 lines
sudo journalctl -u wifi-monitor.service -n 50

# Service log file
tail -f ~/wifi_app/service.log
```

### Stop the Service
```bash
sudo systemctl stop wifi-monitor.service
```

### Restart the Service
```bash
sudo systemctl restart wifi-monitor.service
```

### Check Status
```bash
sudo systemctl status wifi-monitor.service
```

### Disable Auto-Start
```bash
sudo systemctl disable wifi-monitor.service
```

## Updating the Application

When you make changes to the code:

1. **From your Mac**, sync the changes:
```bash
rsync -av wifi_app/ pi@<raspberry-pi-ip>:~/wifi_app/
```

2. **On the Raspberry Pi**, restart the service:
```bash
sudo systemctl restart wifi-monitor.service
```

## Data Storage

- **CSV Logs**: `~/wifi_app/wifi_logs/wifi_log_YYYY-MM-DD.csv`
- **Device Registry**: `~/wifi_app/wifi_logs/devices.json`
- **Service Logs**: `~/wifi_app/service.log`

## Configuration

### Change Port

Edit the service file:
```bash
sudo nano /etc/systemd/system/wifi-monitor.service
```

Change `--port 5002` to your desired port, then:
```bash
sudo systemctl daemon-reload
sudo systemctl restart wifi-monitor.service
```

### Change Scan Interval

Edit `wifi_app.py` and change the line:
```python
time.sleep(120)  # Change 120 to desired seconds
```

Then restart the service.

## Troubleshooting

### Service Won't Start

Check logs for errors:
```bash
sudo journalctl -u wifi-monitor.service -n 50
```

Common issues:
- Missing Python dependencies: `pip3 install flask pandas`
- Port already in use: Change the port in the service file
- File permissions: Make sure `pi` user owns the files

### No Devices Detected

- Make sure devices are connected to the same WiFi network
- Check ARP table manually: `arp -a`
- Try pinging a device first: `ping <device-ip>`

### Can't Access Web Interface

- Check firewall: `sudo ufw status`
- Verify service is running: `sudo systemctl status wifi-monitor.service`
- Check the correct IP address: `hostname -I`

## Network Setup

The scanner works by reading the ARP table, which contains devices that have communicated on the network. To ensure devices appear:

1. Devices must be on the same network as the Raspberry Pi
2. Devices should be actively communicating (not in sleep mode)
3. You can trigger ARP updates by pinging the network: `nmap -sn 192.168.1.0/24`

## Security Notes

- The web interface has no authentication
- Consider using a reverse proxy (nginx) with authentication for production
- The device registry contains MAC addresses - keep backups secure
- Only run this on trusted networks
