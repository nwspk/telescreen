#!/usr/bin/env python3
"""
WiFi Network Scanner with Web Interface
Scans devices on the network and displays current occupancy and history
"""

import argparse
import csv
import logging
import subprocess
import threading
import time
from pathlib import Path
from datetime import datetime
import platform

from flask import Flask, jsonify, request
import pandas as pd
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Global cache for data
class DataCache:
    def __init__(self):
        self.current_devices = []
        self.hourly_history = []
        self.last_update = None
        self.lock = threading.Lock()

cache = DataCache()

# Device registry file
DEVICES_FILE = Path('wifi_logs/devices.json')


def load_devices():
    """Load claimed devices from JSON file."""
    if DEVICES_FILE.exists():
        try:
            with open(DEVICES_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading devices: {e}")
            return {}
    return {}


def save_devices(devices):
    """Save claimed devices to JSON file."""
    try:
        DEVICES_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(DEVICES_FILE, 'w') as f:
            json.dump(devices, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving devices: {e}")


def get_network_range():
    """Auto-detect the network range from the default interface (cross-platform)."""
    try:
        system = platform.system()

        if system == "Linux":
            # Linux: Use ip command
            result = subprocess.run(
                ['ip', 'route', 'show', 'default'],
                capture_output=True, text=True
            )

            # Parse output to get interface
            default_line = result.stdout.strip().split('\n')[0]
            interface = default_line.split('dev ')[1].split()[0]

            # Get IP address and netmask for that interface
            result = subprocess.run(
                ['ip', 'addr', 'show', interface],
                capture_output=True, text=True
            )

            for line in result.stdout.split('\n'):
                if 'inet ' in line and '127.0.0.1' not in line:
                    # Extract CIDR notation (e.g., 192.168.1.5/24)
                    ip_cidr = line.strip().split()[1]
                    # Convert to network range (e.g., 192.168.1.0/24)
                    ip_parts = ip_cidr.split('/')
                    ip = ip_parts[0]
                    netmask = ip_parts[1]

                    # Get network address
                    network_ip = '.'.join(ip.split('.')[:-1]) + '.0/' + netmask
                    logger.info(f"Auto-detected network: {network_ip}")
                    return network_ip

        elif system == "Darwin":  # macOS
            # macOS: Use ifconfig and netstat
            result = subprocess.run(
                ['netstat', '-rn'],
                capture_output=True, text=True
            )

            # Find default route
            for line in result.stdout.split('\n'):
                if line.startswith('default'):
                    parts = line.split()
                    interface = parts[-1] if len(parts) > 0 else 'en0'
                    break
            else:
                interface = 'en0'  # Fallback to en0

            # Get IP address from ifconfig
            result = subprocess.run(
                ['ifconfig', interface],
                capture_output=True, text=True
            )

            for line in result.stdout.split('\n'):
                if 'inet ' in line and '127.0.0.1' not in line:
                    parts = line.strip().split()
                    ip = parts[1]
                    netmask_hex = parts[3] if len(parts) > 3 else '0xffffff00'

                    # Convert hex netmask to CIDR (e.g., 0xffffff00 -> /24)
                    if netmask_hex.startswith('0x'):
                        netmask_int = int(netmask_hex, 16)
                        cidr = bin(netmask_int).count('1')
                    else:
                        cidr = 24  # Default

                    # Get network address
                    network_ip = '.'.join(ip.split('.')[:-1]) + '.0/' + str(cidr)
                    logger.info(f"Auto-detected network: {network_ip}")
                    return network_ip

        # Fallback
        return "192.168.1.0/24"

    except Exception as e:
        logger.error(f"Error detecting network range: {e}")
        return "192.168.1.0/24"


def scan_network_arp_table():
    """Scan using system ARP table (works without external tools)."""
    try:
        devices = []
        system = platform.system()

        # Get ARP table
        if system == "Darwin":  # macOS
            result = subprocess.run(['arp', '-a'], capture_output=True, text=True)
        else:  # Linux
            result = subprocess.run(['arp', '-n'], capture_output=True, text=True)

        for line in result.stdout.split('\n'):
            if system == "Darwin":
                # macOS format: hostname (ip) at mac on interface
                if ' at ' in line and '(' in line:
                    parts = line.split()
                    ip = parts[1].strip('()')
                    mac_idx = parts.index('at') + 1
                    mac = parts[mac_idx] if mac_idx < len(parts) else None

                    # Filter out broadcast, multicast, and incomplete entries
                    if mac and mac != '(incomplete)' and ':' in mac:
                        # Skip broadcast (ff:ff:ff:ff:ff:ff) and multicast (starts with 01:)
                        if mac.lower() == 'ff:ff:ff:ff:ff:ff' or mac.lower().startswith('1:0:5e'):
                            continue
                        # Skip multicast IPs
                        if ip.startswith('224.') or ip.startswith('239.') or ip.endswith('.0') or ip.endswith('.255'):
                            continue

                        devices.append({
                            'ip': ip,
                            'mac': mac,
                            'vendor': 'Unknown'
                        })
            else:
                # Linux format: ip hwtype hwaddr flags mask iface
                parts = line.split()
                if len(parts) >= 3 and ':' in parts[2]:
                    ip = parts[0]
                    mac = parts[2]

                    # Filter out broadcast, multicast, and invalid entries
                    if mac == '00:00:00:00:00:00' or mac.lower() == 'ff:ff:ff:ff:ff:ff':
                        continue
                    # Skip multicast IPs
                    if ip.startswith('224.') or ip.startswith('239.') or ip.endswith('.0') or ip.endswith('.255'):
                        continue

                    devices.append({
                        'ip': ip,
                        'mac': mac,
                        'vendor': 'Unknown'
                    })

        logger.info(f"Found {len(devices)} devices in ARP table")
        return devices

    except Exception as e:
        logger.error(f"Error reading ARP table: {e}")
        return []


def initialize_csv_file():
    """Initialize the CSV file with headers if it doesn't exist."""
    today = datetime.now().strftime('%Y-%m-%d')
    logs_dir = Path('wifi_logs')
    logs_dir.mkdir(parents=True, exist_ok=True)

    filename = logs_dir / f'wifi_log_{today}.csv'
    if not filename.exists():
        with open(filename, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Timestamp", "MAC Address", "IP Address"
            ])
    return filename


def read_wifi_logs():
    """Read WiFi logs and aggregate data for visualization."""
    logs_dir = Path('wifi_logs')

    if not logs_dir.exists():
        return [], []

    # Get all log files from the last 3 days
    log_files = sorted(logs_dir.glob('wifi_log_*.csv'))
    recent_logs = log_files[-3:] if len(log_files) >= 3 else log_files

    if not recent_logs:
        return [], []

    # Read all logs into a DataFrame
    all_data = []
    for log_file in recent_logs:
        try:
            df = pd.read_csv(log_file)
            all_data.append(df)
        except Exception as e:
            logger.error(f"Error reading {log_file}: {e}")

    if not all_data:
        return [], []

    combined_df = pd.concat(all_data, ignore_index=True)

    # Convert timestamps
    combined_df['Timestamp'] = pd.to_datetime(combined_df['Timestamp'])

    # Filter to last 48 hours
    now = pd.Timestamp.now()
    last_48_hours = now - pd.Timedelta(hours=48)
    combined_df = combined_df[combined_df['Timestamp'] >= last_48_hours]

    # Current devices (last 10 minutes)
    last_10_min = now - pd.Timedelta(minutes=10)
    recent_df = combined_df[combined_df['Timestamp'] >= last_10_min]
    current_devices = recent_df.groupby('MAC Address').agg({
        'IP Address': 'last',
        'Timestamp': 'last'
    }).reset_index()
    current_devices = current_devices.to_dict('records')

    # Hourly aggregation
    combined_df['Hour'] = combined_df['Timestamp'].dt.floor('h')
    hourly_counts = combined_df.groupby('Hour')['MAC Address'].nunique().reset_index()
    hourly_counts.columns = ['Hour', 'Device Count']

    # Fill in missing hours with 0
    hour_range = pd.date_range(start=last_48_hours.floor('h'), end=now.floor('h'), freq='h')
    full_hours = pd.DataFrame({'Hour': hour_range})
    hourly_counts = full_hours.merge(hourly_counts, on='Hour', how='left').fillna(0)
    hourly_counts['Device Count'] = hourly_counts['Device Count'].astype(int)

    hourly_history = hourly_counts.to_dict('records')

    return current_devices, hourly_history


def scan_and_log():
    """Continuous scanning function that runs in the background."""
    while True:
        try:
            # Scan network
            devices = scan_network_arp_table()

            # Write to CSV
            output_file = initialize_csv_file()
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            with open(output_file, "a", newline="") as f:
                writer = csv.writer(f)
                for device in devices:
                    writer.writerow([
                        timestamp,
                        device['mac'],
                        device['ip']
                    ])

            logger.info(f"[{timestamp}] Scanned and logged {len(devices)} devices")

            # Update cache
            current_devices, hourly_history = read_wifi_logs()
            with cache.lock:
                cache.current_devices = current_devices
                cache.hourly_history = hourly_history
                cache.last_update = datetime.now()

        except Exception as e:
            logger.error(f"Error in scan_and_log: {e}")

        # Wait 15 minutes before next scan
        time.sleep(900)


@app.route('/')
def index():
    """Main dashboard page."""
    template_path = Path(__file__).parent / 'template.html'
    with open(template_path, 'r') as f:
        template = f.read()
    return template


@app.route('/api/data')
def api_data():
    """API endpoint to get current data."""
    with cache.lock:
        current_devices = cache.current_devices
        hourly_history = cache.hourly_history

    # Load device registry
    device_registry = load_devices()

    # Merge current devices with registry info
    enriched_devices = []
    people_online = set()

    for device in current_devices:
        mac = device['MAC Address']
        enriched_device = device.copy()

        if mac in device_registry:
            enriched_device['device_name'] = device_registry[mac].get('device_name', '')
            enriched_device['owner'] = device_registry[mac].get('owner', '')
            enriched_device['claimed'] = True
            if device_registry[mac].get('owner'):
                people_online.add(device_registry[mac]['owner'])
        else:
            enriched_device['device_name'] = ''
            enriched_device['owner'] = ''
            enriched_device['claimed'] = False

        enriched_devices.append(enriched_device)

    # Format history for chart
    history = []
    for item in hourly_history:
        history.append({
            'hour': item['Hour'].isoformat() if hasattr(item['Hour'], 'isoformat') else str(item['Hour']),
            'count': int(item['Device Count'])
        })

    return jsonify({
        'current_count': len(current_devices),
        'current_devices': enriched_devices,
        'people_online': sorted(list(people_online)),
        'history': history
    })


@app.route('/api/devices/claim', methods=['POST'])
def claim_device():
    """Claim a device by adding owner and device name."""
    try:
        data = request.json
        mac = data.get('mac')
        device_name = data.get('device_name', '')
        owner = data.get('owner', '')

        if not mac:
            return jsonify({'error': 'MAC address required'}), 400

        # Load current registry
        devices = load_devices()

        # Update or add device
        devices[mac] = {
            'device_name': device_name,
            'owner': owner,
            'claimed_at': datetime.now().isoformat()
        }

        # Save registry
        save_devices(devices)

        return jsonify({'success': True, 'mac': mac})

    except Exception as e:
        logger.error(f"Error claiming device: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/devices/unclaim', methods=['POST'])
def unclaim_device():
    """Remove a device claim."""
    try:
        data = request.json
        mac = data.get('mac')

        if not mac:
            return jsonify({'error': 'MAC address required'}), 400

        # Load current registry
        devices = load_devices()

        # Remove device if it exists
        if mac in devices:
            del devices[mac]
            save_devices(devices)

        return jsonify({'success': True, 'mac': mac})

    except Exception as e:
        logger.error(f"Error unclaiming device: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/devices/registry')
def get_registry():
    """Get all claimed devices."""
    devices = load_devices()
    return jsonify(devices)


def main():
    parser = argparse.ArgumentParser(description='WiFi Network Scanner with Web Interface')
    parser.add_argument('--port', type=int, default=5002,
                        help='Port for web interface (default: 5002)')
    parser.add_argument('--scan-only', action='store_true',
                        help='Run scanner only (no web interface)')
    args = parser.parse_args()

    if args.scan_only:
        # Run scanner only
        logger.info("Starting scanner in scan-only mode...")
        scan_and_log()
    else:
        # Start background scanner thread
        scanner_thread = threading.Thread(target=scan_and_log, daemon=True)
        scanner_thread.start()

        # Give it a moment to collect initial data
        time.sleep(2)

        # Run Flask app
        logger.info(f"Starting web interface on http://0.0.0.0:{args.port}")
        app.run(host='0.0.0.0', port=args.port, threaded=True, debug=False)


if __name__ == "__main__":
    main()
