## SPY-IMSICD - IMSI Catcher Detector

Detects rogue cell towers (IMSI catchers / StingRays) using GSM/LTE modem heuristics.

## Features
- Cell ID consistency check (OpenCellID, whitelist)
- Signal spike detection
- Neighbor cell absence detection
- Network downgrade detection (4G→2G)
- Cell change rate anomaly
- FemtoCell detection
- Desktop & Telegram alerts
- Export logs (JSON/CSV)

## Installation
```bash
git clone https://github.com/123tool/SPY-IMSICD.git
cd SPY-IMSICD
pip install -e .
```

## Usage
1. Configure modem port in config.ini (copy from config.example.ini)
2. Run monitor:
   ```bash
   spy-imsicd monitor --port /dev/ttyUSB0 --interval 10
   ```
3. Single scan:
   ```bash
   spy-imsicd scan_once
   ```
4. Whitelist known cells:
   ```bash
   spy-imsicd whitelist add --mcc 510 --mnc 10 --lac 1234 --cid 5678
   ```
5. Export detections:
   ```bash
   spy-imsicd export --format json --output mylog.json
   ```

## Requirements
1. Linux/macOS (Windows with WSL recommended)
2. 3G/4G USB modem with AT command support (Huawei E3372, Sierra Wireless, etc.)
3. Optional: RTL-SDR for additional passive scanning

## Disclaimer

This tool is for educational and defensive security research only. Use only on your own devices and with proper authorization.
