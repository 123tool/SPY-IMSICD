import serial
import time
import re
import logging
from typing import Tuple, List, Dict, Optional

logger = logging.getLogger(__name__)

class GSMProbe:
    def __init__(self, port: str, baudrate: int = 115200, timeout: int = 2):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.ser = None
        self._connect()

    def _connect(self):
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
            logger.info(f"Connected to modem on {self.port}")
        except Exception as e:
            logger.error(f"Failed to connect to modem: {e}")
            self.ser = None

    def send_at(self, cmd: str, wait: float = 0.5) -> str:
        if not self.ser:
            return ""
        self.ser.write((cmd + "\r\n").encode())
        time.sleep(wait)
        response = self.ser.read_all().decode(errors="ignore")
        logger.debug(f"AT({cmd}) -> {response}")
        return response

    def get_signal_quality(self) -> Optional[int]:
        """Return RSSI in dBm or None"""
        resp = self.send_at("AT+CSQ")
        match = re.search(r"\+CSQ:\s*(\d+),", resp)
        if match:
            rssi_val = int(match.group(1))
            # Convert to dBm: 0=-113 dBm, 1=-111, 2..30 = -109 to -53, 31=-51, 99=unknown
            if rssi_val == 99:
                return None
            rssi_dbm = -113 + (rssi_val * 2)
            return rssi_dbm
        return None

    def get_serving_cell(self) -> Dict:
        """Return dict with mcc, mnc, lac, cid, network_type, rssi"""
        cell_info = {
            "mcc": None,
            "mnc": None,
            "lac": None,
            "cid": None,
            "network_type": None,
            "rssi": None,
        }
        rssi = self.get_signal_quality()
        cell_info["rssi"] = rssi

        # Try Huawei specific command (most common)
        resp = self.send_at("AT+QENG=\"servingcell\"", wait=1)
        if "+QENG:" in resp:
            # Parse example: +QENG: "servingcell","LTE",...,"MCC","MNC","LAC","CID",...
            # Simpler: use regex to find MCC, MNC, LAC, CID
            mcc_match = re.search(r'"MCC":\s*"(\d+)"', resp)
            mnc_match = re.search(r'"MNC":\s*"(\d+)"', resp)
            lac_match = re.search(r'"LAC":\s*(\d+)', resp) or re.search(r'"LAC":\s*"(\d+)"', resp)
            cid_match = re.search(r'"CID":\s*(\d+)', resp) or re.search(r'"CID":\s*"(\d+)"', resp)
            net_match = re.search(r'"servingcell","(\w+)"', resp)
            if net_match:
                cell_info["network_type"] = net_match.group(1)
            if mcc_match:
                cell_info["mcc"] = mcc_match.group(1)
            if mnc_match:
                cell_info["mnc"] = mnc_match.group(1)
            if lac_match:
                cell_info["lac"] = int(lac_match.group(1))
            if cid_match:
                cell_info["cid"] = int(cid_match.group(1))

        # Fallback to generic AT+CREG?
        if cell_info["lac"] is None:
            resp = self.send_at("AT+CREG?")
            # +CREG: <mode>,<stat>[,<lac>,<ci>]
            match = re.search(r"\+CREG:\s*\d+,\d+,\s*([0-9A-Fa-f]+),\s*([0-9A-Fa-f]+)", resp)
            if match:
                lac_hex = match.group(1)
                cid_hex = match.group(2)
                cell_info["lac"] = int(lac_hex, 16)
                cell_info["cid"] = int(cid_hex, 16)

        return cell_info

    def get_neighbor_cells(self) -> List[Dict]:
        """Return list of neighbor cells (if supported)"""
        neighbors = []
        # Try AT+CCED command (Huawei)
        resp = self.send_at("AT+CCED=0,1", wait=1)
        if "+CCED:" in resp:
            lines = resp.split("\n")
            for line in lines:
                if "+CCED:" in line:
                    # Example format: +CCED: 1,1,1, 2G, 16, 68, 99, - ...
                    # simplified parsing
                    parts = re.findall(r"(\d+)", line)
                    if len(parts) >= 4:
                        neighbor = {"lac": None, "cid": int(parts[0]), "rssi": None}
                        neighbors.append(neighbor)
        # Alternative: AT+CRSM for SIM access? Not recommended.
        return neighbors

    def get_network_registration_status(self) -> str:
        """Return registration status: registered, roaming, searching, denied"""
        resp = self.send_at("AT+CREG?")
        if "+CREG:" in resp:
            parts = resp.split(",")
            if len(parts) >= 2:
                stat = parts[1].strip()
                if stat == "1":
                    return "registered"
                elif stat == "5":
                    return "roaming"
                elif stat == "2":
                    return "searching"
                elif stat == "3":
                    return "denied"
        return "unknown"

    def is_2g_only(self) -> bool:
        """Check if current network is 2G (GSM)"""
        info = self.get_serving_cell()
        net = info.get("network_type", "").upper()
        return net in ["GSM", "GPRS", "EDGE"]

    def close(self):
        if self.ser:
            self.ser.close()
