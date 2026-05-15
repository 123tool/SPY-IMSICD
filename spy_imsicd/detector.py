import time
import logging
import requests
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from .database import Database
from .alert import AlertSystem

logger = logging.getLogger(__name__)

class IMSIDetector:
    def __init__(self, db: Database, alert: AlertSystem, opencellid_api_key: str = None):
        self.db = db
        self.alert = alert
        self.opencellid_key = opencellid_api_key
        self.last_cell = None
        self.last_rssi = None
        self.cell_change_times = []  # store timestamps for rate detection

    def check_opencellid(self, mcc: str, mnc: str, lac: int, cid: int) -> Optional[bool]:
        """Return True if cell exists in OpenCellID, False if suspicious, None if error"""
        if not self.opencellid_key:
            return None
        try:
            url = "https://opencellid.org/cell/get"
            params = {
                "key": self.opencellid_key,
                "mcc": mcc,
                "mnc": mnc,
                "lac": lac,
                "cellid": cid,
                "format": "json"
            }
            resp = requests.get(url, params=params, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                # If 'cell' exists and has data, it's known
                if data.get("cell") and len(data["cell"]) > 0:
                    return True
                else:
                    return False
            else:
                return None
        except Exception as e:
            logger.error(f"OpenCellID error: {e}")
            return None

    def check_cell_consistency(self, cell: Dict) -> Tuple[bool, str]:
        """Check if cell ID is consistent with known data. Returns (is_suspicious, reason)"""
        mcc = cell.get("mcc")
        mnc = cell.get("mnc")
        lac = cell.get("lac")
        cid = cell.get("cid")
        if not all([mcc, mnc, lac is not None, cid is not None]):
            return False, "Incomplete cell data"

        # Check whitelist
        if self.db.is_whitelisted(mcc, mnc, lac, cid):
            return False, "Whitelisted"

        # Check OpenCellID
        if self.opencellid_key:
            known = self.check_opencellid(mcc, mnc, lac, cid)
            if known is False:
                return True, f"Cell not found in OpenCellID (MCC={mcc}, MNC={mnc}, LAC={lac}, CID={cid})"

        # Check for impossible LAC/CID values (like 65535 or 0)
        if lac == 65535 or cid == 65535 or lac == 0 or cid == 0:
            return True, "Suspicious LAC/CID value (0 or 65535)"
        return False, ""

    def check_signal_anomaly(self, current_rssi: int) -> Tuple[bool, str]:
        if self.last_rssi is None:
            self.last_rssi = current_rssi
            return False, ""
        spike = current_rssi - self.last_rssi
        if spike > 20:  # more than 20 dB increase
            return True, f"Signal spike of {spike} dBm (previous {self.last_rssi}, now {current_rssi})"
        return False, ""

    def check_neighbor_absence(self, neighbor_list: List[Dict], current_rssi: int) -> Tuple[bool, str]:
        # IMSI catchers often operate alone without neighboring cells
        if len(neighbor_list) == 0 and current_rssi > -60:  # strong signal but no neighbors
            return True, f"Strong signal ({current_rssi} dBm) but no neighbor cells reported"
        return False, ""

    def check_downgrade_attack(self, current_network: str) -> Tuple[bool, str]:
        # If previously on 4G/3G and now on 2G without moving
        # This requires state tracking; simplified: if network type is 2G and previous was better
        if self.last_cell:
            prev_net = self.last_cell.get("network_type", "")
            if prev_net in ["LTE", "WCDMA", "UMTS"] and current_network in ["GSM", "GPRS", "EDGE"]:
                return True, f"Network downgrade from {prev_net} to {current_network} - possible IMSI catcher"
        return False, ""

    def check_cell_change_rate(self, current_lac, current_cid) -> Tuple[bool, str]:
        now = time.time()
        if self.last_cell:
            prev_lac = self.last_cell.get("lac")
            prev_cid = self.last_cell.get("cid")
            if (prev_lac != current_lac or prev_cid != current_cid):
                self.cell_change_times.append(now)
                # Keep only last 60 seconds
                self.cell_change_times = [t for t in self.cell_change_times if now - t <= 60]
                if len(self.cell_change_times) > 3:  # more than 3 changes per minute
                    return True, f"Too many cell changes in short time ({len(self.cell_change_times)} in last minute)"
        return False, ""

    def check_femtocell(self, cell: Dict, rssi: int) -> Tuple[bool, str]:
        # FemtoCells often have very strong signal (-40 dBm) and unusual LAC/CID
        if rssi > -50 and (cell.get("lac", 0) < 100 or cell.get("cid", 0) < 100):
            return True, f"FemtoCell suspected: very strong signal ({rssi} dBm) with small LAC/CID"
        return False, ""

    def detect_silent_sms(self, modem) -> Tuple[bool, str]:
        """Attempt to detect silent SMS (Class 0) - requires modem in PDU mode"""
        # This is complex; we'll simulate by checking for unread SMS without notification
        # For now, return False as it needs deeper integration
        # Future: use AT+CNMI to set up unsolicited indication and capture Class 0
        return False, ""

    def update(self, cell: Dict, neighbor_list: List[Dict], rssi: int):
        suspicious = False
        reasons = []

        # Run checks
        cons_issue, cons_reason = self.check_cell_consistency(cell)
        if cons_issue:
            suspicious = True
            reasons.append(cons_reason)

        signal_issue, signal_reason = self.check_signal_anomaly(rssi)
        if signal_issue:
            suspicious = True
            reasons.append(signal_reason)

        neighbor_issue, neighbor_reason = self.check_neighbor_absence(neighbor_list, rssi)
        if neighbor_issue:
            suspicious = True
            reasons.append(neighbor_reason)

        downgrade_issue, downgrade_reason = self.check_downgrade_attack(cell.get("network_type", ""))
        if downgrade_issue:
            suspicious = True
            reasons.append(downgrade_reason)

        rate_issue, rate_reason = self.check_cell_change_rate(cell.get("lac"), cell.get("cid"))
        if rate_issue:
            suspicious = True
            reasons.append(rate_reason)

        femto_issue, femto_reason = self.check_femtocell(cell, rssi)
        if femto_issue:
            suspicious = True
            reasons.append(femto_reason)

        # Silent SMS check (optional)
        # silent_issue, silent_reason = self.detect_silent_sms(modem)
        # if silent_issue: ...

        if suspicious:
            details = "; ".join(reasons)
            severity = "high" if "spike" in details or "downgrade" in details else "medium"
            detection_record = {
                "timestamp": datetime.utcnow().isoformat(),
                "mcc": cell.get("mcc"),
                "mnc": cell.get("mnc"),
                "lac": cell.get("lac"),
                "cid": cell.get("cid"),
                "network_type": cell.get("network_type"),
                "rssi": rssi,
                "detection_type": "IMSI_Catcher_Suspicion",
                "severity": severity,
                "details": details,
            }
            self.db.add_detection(detection_record)
            self.alert.send(
                title="IMSI Catcher Detected!",
                message=details,
                severity=severity
            )
            # Optionally blacklist this cell
            self.db.add_to_blacklist(cell.get("mcc"), cell.get("mnc"), cell.get("lac"), cell.get("cid"), details)

        # Update state
        self.last_cell = cell.copy()
        self.last_rssi = rssi
