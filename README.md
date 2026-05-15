# SPY-IMSICD - IMSI Catcher Detector

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
git clone https://github.com/yourname/spy-imsicd
cd spy-imsicd
pip install -e .
