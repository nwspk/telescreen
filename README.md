## Overview
This repository manages multiple Raspberry Pi devices that control displays around Newspeak House. Each device has its own configuration.

## Device Structure
The repository is organized with individual device configurations in the devices/ directory:

```
devices/
  └── nwspkpi1/         # Configuration for specific device
      ├── app.py        # Main application
      ├── ble_scanner.py  # Bluetooth scanning
      ├── counts.csv    # Device count data
      └── ...
```
