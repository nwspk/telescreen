import argparse
import csv
import json
import logging
import os
import time
from pathlib import Path
from datetime import datetime

import pandas as pd
from bluepy.btle import Scanner, DefaultDelegate

# Configure logging
logging.basicConfig(
    level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

def load_manufacturer_data(file_path):
    """Load Bluetooth manufacturer data from a CSV file into a dictionary."""
    try:
        manufacturer_df = pd.read_csv(file_path)
        manufacturer_df.columns = manufacturer_df.columns.str.strip()
        manufacturer_df['Company Identifier'] = (
            manufacturer_df['Company Identifier']
            .str.replace("0x", "", regex=False)
            .str.zfill(4)
            .str.lower()
        )
        manufacturer_dict = dict(
            zip(
                manufacturer_df['Company Identifier'],
                manufacturer_df['Company Name'],
            )
        )
        return manufacturer_dict
    except FileNotFoundError:
        logger.error(f"Manufacturer data file not found: {file_path}")
        return {}
    except Exception as e:
        logger.error(f"Error loading manufacturer data: {e}")
        return {}

def get_manufacturer_name(raw_data_hex, manufacturer_dict):
    """Retrieve the manufacturer name based on the company identifier in raw_data."""
    if raw_data_hex and len(raw_data_hex) >= 4:
        try:
            raw_data_bytes = bytes.fromhex(raw_data_hex)
            company_id_bytes = raw_data_bytes[:2]
            company_id_int = int.from_bytes(company_id_bytes, byteorder='little')
            company_id_hex = format(company_id_int, '04x')
            return manufacturer_dict.get(company_id_hex.lower(), "Unknown")
        except ValueError:
            return "Unknown"
    return "Unknown"

def initialize_csv_file():
    """Initialize the CSV file with headers if it doesn't exist."""
    today = datetime.now().strftime('%Y-%m-%d')
    logs_dir = Path('/home/nwspkpi1/telescreen/devices/nwspkpi1/logs')
    logs_dir.mkdir(parents=True, exist_ok=True)
    
    filename = logs_dir / f'ble_log_{today}.csv'
    if not filename.exists():
        with open(filename, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Timestamp", "MAC Address", "RSSI",
                "Manufacturer", "Raw Data", "Additional Metadata"
            ])
    return filename


def scan_ble_devices(scanner, rssi_threshold, scan_duration, manufacturer_dict):
    logger.info(f"Starting {scan_duration}-second BLE scan...")
    devices = scanner.scan(scan_duration)
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    detected_devices = []

    for dev in devices:
        if dev.rssi >= rssi_threshold:
            try:
                mac_address = dev.addr
                rssi = dev.rssi
                raw_data_hex = dev.getValueText(255) or ""
                manufacturer = get_manufacturer_name(raw_data_hex, manufacturer_dict)

                # Process scanData to ensure JSON serializability
                scan_data_serialized = {}
                for adtype, desc, value in dev.getScanData():
                    scan_data_serialized[desc] = value

                additional_metadata = {
                    "addrType": dev.addrType,
                    "scanData": scan_data_serialized,
                    "rawData": raw_data_hex
                }

                additional_metadata_str = json.dumps(additional_metadata)
                detected_devices.append([
                    timestamp, mac_address, rssi, manufacturer,
                    raw_data_hex, additional_metadata_str
                ])
            except Exception as e:
                logger.error(f"Error processing device {dev.addr}: {e}")
    return detected_devices

def main():
    parser = argparse.ArgumentParser(description='BLE Scanner and Logger')
    parser.add_argument('--manufacturer_file', type=str,
                        default='Bluetooth-Company-Identifiers.csv',
                        help='Path to the Bluetooth manufacturer identifiers CSV file.')
    # parser.add_argument('--output_dir', type=str, default='.',
    #                    help='Base directory for log files.')
    parser.add_argument('--output_file', type=str, 
                    help='Deprecated: Using logs directory instead.')
    parser.add_argument('--rssi_threshold', type=int, default=-75,
                        help='RSSI threshold in dBm.')
    parser.add_argument('--scan_duration', type=float, default=30.0,
                        help='Duration of each BLE scan in seconds.')
    parser.add_argument('--sleep_duration', type=float, default=60.0,
                        help='Time between scans in seconds.')
    args = parser.parse_args()
    
    manufacturer_dict = load_manufacturer_data(args.manufacturer_file)
    if not manufacturer_dict:
        logger.warning("Manufacturer dictionary is empty. Manufacturer names will not be available.")
    
    output_file = initialize_csv_file()

    scanner = Scanner().withDelegate(DefaultDelegate())

    try:
        detected_devices = scan_ble_devices(
            scanner, args.rssi_threshold,
            args.scan_duration, manufacturer_dict
        )
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(output_file, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(detected_devices)
        logger.info(
            f"[{timestamp}] Detected {len(detected_devices)} devices "
            f"with RSSI >= {args.rssi_threshold} dBm"
        )

    except Exception as e:
        logger.error(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
