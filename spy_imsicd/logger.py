import json
import csv
import logging
from datetime import datetime
from typing import List, Dict

class Logger:
    def __init__(self, log_file: str = "spy_imsicd.log", export_format: str = "json"):
        self.log_file = log_file
        self.export_format = export_format
        # Set up file logging
        logging.basicConfig(
            filename=log_file,
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        self.logger = logging.getLogger("spy_imsicd")

    def log_detection(self, detection: Dict):
        self.logger.warning(f"DETECTION: {json.dumps(detection)}")

    def export_detections(self, detections: List[Dict], filename: str = None):
        if not filename:
            filename = f"export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{self.export_format}"
        if self.export_format == "json":
            with open(filename, 'w') as f:
                json.dump(detections, f, indent=2)
        elif self.export_format == "csv":
            if not detections:
                return
            with open(filename, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=detections[0].keys())
                writer.writeheader()
                writer.writerows(detections)
        print(f"Exported {len(detections)} detections to {filename}")
