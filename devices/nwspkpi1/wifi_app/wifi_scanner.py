"""
WiFi Network Scanner - Detects devices on the same WiFi network
Uses ARP scanning to discover devices on the local network
"""

import argparse
import csv
import logging
import subprocess
from pathlib import Path
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def get_network_range():
    """Auto-detect the network range from the default interface (cross-platform)."""
    import platform

    try:
        system = platform.system()

        if system == "Linux":
            # Linux: Use ip command
            result = subprocess.run(
                ["ip", "route", "show", "default"], capture_output=True, text=True
            )

            # Parse output to get interface
            default_line = result.stdout.strip().split("\n")[0]
            interface = default_line.split("dev ")[1].split()[0]

            # Get IP address and netmask for that interface
            result = subprocess.run(
                ["ip", "addr", "show", interface], capture_output=True, text=True
            )

            for line in result.stdout.split("\n"):
                if "inet " in line and "127.0.0.1" not in line:
                    # Extract CIDR notation (e.g., 192.168.1.5/24)
                    ip_cidr = line.strip().split()[1]
                    # Convert to network range (e.g., 192.168.1.0/24)
                    ip_parts = ip_cidr.split("/")
                    ip = ip_parts[0]
                    netmask = ip_parts[1]

                    # Get network address
                    network_ip = ".".join(ip.split(".")[:-1]) + ".0/" + netmask
                    logger.info(f"Auto-detected network: {network_ip}")
                    return network_ip

        elif system == "Darwin":  # macOS
            # macOS: Use ifconfig and netstat
            result = subprocess.run(["netstat", "-rn"], capture_output=True, text=True)

            # Find default route
            for line in result.stdout.split("\n"):
                if line.startswith("default"):
                    parts = line.split()
                    interface = parts[-1] if len(parts) > 0 else "en0"
                    break
            else:
                interface = "en0"  # Fallback to en0

            # Get IP address from ifconfig
            result = subprocess.run(
                ["ifconfig", interface], capture_output=True, text=True
            )

            for line in result.stdout.split("\n"):
                if "inet " in line and "127.0.0.1" not in line:
                    parts = line.strip().split()
                    ip = parts[1]
                    netmask_hex = parts[3] if len(parts) > 3 else "0xffffff00"

                    # Convert hex netmask to CIDR (e.g., 0xffffff00 -> /24)
                    if netmask_hex.startswith("0x"):
                        netmask_int = int(netmask_hex, 16)
                        cidr = bin(netmask_int).count("1")
                    else:
                        cidr = 24  # Default

                    # Get network address
                    network_ip = ".".join(ip.split(".")[:-1]) + ".0/" + str(cidr)
                    logger.info(f"Auto-detected network: {network_ip}")
                    return network_ip

        # Fallback
        return "192.168.1.0/24"

    except Exception as e:
        logger.error(f"Error detecting network range: {e}")
        return "192.168.1.0/24"


def scan_network(network_range):
    """Scan the network for active devices using arp-scan."""
    try:
        # Using arp-scan (more reliable than nmap for local network)
        result = subprocess.run(
            ["sudo", "arp-scan", "--localnet", "--retry=3", "--timeout=500"],
            capture_output=True,
            text=True,
            timeout=60,
        )

        devices = []

        for line in result.stdout.split("\n"):
            # Skip header and footer lines
            if "\t" in line and not line.startswith("Interface:"):
                parts = line.split("\t")
                if len(parts) >= 3:
                    ip = parts[0].strip()
                    mac = parts[1].strip()
                    vendor = parts[2].strip() if len(parts) > 2 else "Unknown"

                    devices.append({"ip": ip, "mac": mac, "vendor": vendor})

        return devices

    except subprocess.TimeoutExpired:
        logger.error("ARP scan timed out")
        return []
    except FileNotFoundError:
        logger.error("arp-scan not found. Install with: sudo apt-get install arp-scan")
        return []
    except Exception as e:
        logger.error(f"Error scanning network: {e}")
        return []


def scan_network_nmap(network_range):
    """Alternative: Scan network using nmap (fallback method)."""
    try:
        result = subprocess.run(
            ["nmap", "-sn", network_range], capture_output=True, text=True, timeout=60
        )

        devices = []
        current_ip = None

        for line in result.stdout.split("\n"):
            if "Nmap scan report for" in line:
                current_ip = line.split()[-1].strip("()")
            elif "MAC Address:" in line and current_ip:
                parts = line.split("MAC Address:")[1].strip().split()
                mac = parts[0]
                vendor = (
                    " ".join(parts[1:]).strip("()") if len(parts) > 1 else "Unknown"
                )

                devices.append({"ip": current_ip, "mac": mac, "vendor": vendor})
                current_ip = None

        return devices

    except subprocess.TimeoutExpired:
        logger.error("Nmap scan timed out")
        return []
    except FileNotFoundError:
        logger.error("nmap not found. Install with: sudo apt-get install nmap")
        return []
    except Exception as e:
        logger.error(f"Error scanning with nmap: {e}")
        return []


def scan_network_arp_table():
    """Scan using system ARP table (works without external tools)."""
    import platform

    try:
        devices = []
        system = platform.system()

        # Get ARP table
        if system == "Darwin":  # macOS
            result = subprocess.run(["arp", "-a"], capture_output=True, text=True)
        else:  # Linux
            result = subprocess.run(["arp", "-n"], capture_output=True, text=True)

        for line in result.stdout.split("\n"):
            if system == "Darwin":
                # macOS format: hostname (ip) at mac on interface
                if " at " in line and "(" in line:
                    parts = line.split()
                    ip = parts[1].strip("()")
                    mac_idx = parts.index("at") + 1
                    mac = parts[mac_idx] if mac_idx < len(parts) else None

                    # Filter out broadcast, multicast, and incomplete entries
                    if mac and mac != "(incomplete)" and ":" in mac:
                        # Skip broadcast (ff:ff:ff:ff:ff:ff) and multicast (starts with 01:)
                        if mac.lower() == "ff:ff:ff:ff:ff:ff" or mac.lower().startswith(
                            "1:0:5e"
                        ):
                            continue
                        # Skip multicast IPs
                        if (
                            ip.startswith("224.")
                            or ip.startswith("239.")
                            or ip.endswith(".0")
                            or ip.endswith(".255")
                        ):
                            continue

                        devices.append({"ip": ip, "mac": mac, "vendor": "Unknown"})
            else:
                # Linux format: ip hwtype hwaddr flags mask iface
                parts = line.split()
                if len(parts) >= 3 and ":" in parts[2]:
                    ip = parts[0]
                    mac = parts[2]

                    # Filter out broadcast, multicast, and invalid entries
                    if mac == "00:00:00:00:00:00" or mac.lower() == "ff:ff:ff:ff:ff:ff":
                        continue
                    # Skip multicast IPs
                    if (
                        ip.startswith("224.")
                        or ip.startswith("239.")
                        or ip.endswith(".0")
                        or ip.endswith(".255")
                    ):
                        continue

                    devices.append({"ip": ip, "mac": mac, "vendor": "Unknown"})

        logger.info(f"Found {len(devices)} devices in ARP table")
        return devices

    except Exception as e:
        logger.error(f"Error reading ARP table: {e}")
        return []


def initialize_csv_file():
    """Initialize the CSV file with headers if it doesn't exist."""
    today = datetime.now().strftime("%Y-%m-%d")
    logs_dir = Path("wifi_logs")
    logs_dir.mkdir(parents=True, exist_ok=True)

    filename = logs_dir / f"wifi_log_{today}.csv"
    if not filename.exists():
        with open(filename, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp", "MAC Address", "IP Address"])
    return filename


def main():
    parser = argparse.ArgumentParser(description="WiFi Network Scanner")
    parser.add_argument(
        "--network",
        type=str,
        help="Network range to scan (e.g., 192.168.1.0/24). Auto-detected if not provided.",
    )
    parser.add_argument(
        "--method",
        type=str,
        default="arp-table",
        choices=["arp-scan", "nmap", "arp-table"],
        help="Scanning method to use. arp-table is the default and works without external tools.",
    )
    args = parser.parse_args()

    # Get network range
    network_range = args.network if args.network else get_network_range()

    # Initialize output file
    output_file = initialize_csv_file()

    try:
        # Scan network based on method
        if args.method == "arp-scan":
            devices = scan_network(network_range)
        elif args.method == "nmap":
            devices = scan_network_nmap(network_range)
        else:  # arp-table (default)
            devices = scan_network_arp_table()

        # Write to CSV
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with open(output_file, "a", newline="") as f:
            writer = csv.writer(f)
            for device in devices:
                writer.writerow([timestamp, device["mac"], device["ip"]])

        logger.info("=" * 80)
        logger.info(f"WIFI SCAN RESULTS - {timestamp}")
        logger.info("=" * 80)
        logger.info(f"Network: {network_range}")
        logger.info(f"Method: {args.method}")
        logger.info(f"Total Devices Found: {len(devices)}")
        logger.info("=" * 80)

        if devices:
            logger.info("\nDETAILED DEVICE INFORMATION:")
            logger.info("-" * 80)
            for idx, device in enumerate(devices, 1):
                logger.info(f"\nDevice #{idx}:")
                logger.info(f"  IP Address:  {device['ip']}")
                logger.info(f"  MAC Address: {device['mac']}")
                logger.info(f"  Vendor:      {device['vendor']}")
                logger.info(f"  Timestamp:   {timestamp}")

                # Parse first 3 octets of MAC for vendor lookup
                mac_oui = ":".join(device["mac"].split(":")[:3]).upper()
                logger.info(
                    f"  MAC OUI:     {mac_oui} (first 3 octets identify manufacturer)"
                )

                # Additional info
                logger.info(f"  Network:     {network_range}")
                logger.info(f"  Scan Method: {args.method}")

            logger.info("-" * 80)

            # Summary table
            logger.info("\nQUICK SUMMARY TABLE:")
            logger.info(
                f"{'#':<5} {'IP Address':<17} {'MAC Address':<19} {'Vendor':<30}"
            )
            logger.info("-" * 80)
            for idx, device in enumerate(devices, 1):
                vendor_display = (
                    device["vendor"][:28] + ".."
                    if len(device["vendor"]) > 30
                    else device["vendor"]
                )
                logger.info(
                    f"{idx:<5} {device['ip']:<17} {device['mac']:<19} {vendor_display:<30}"
                )
        else:
            logger.info("\n⚠️  No devices found!")

    except Exception as e:
        logger.error(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
