import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import csv
import time
from protocol_parser import ProtocolParser

# ajaühik (timestamp) lisatud client-side

class ProtocolLogger:
    def __init__(self, filename="robot_telemetry.csv"):
        self.filename = filename
        self.file = open(filename, mode='w', newline='')
        self.writer = csv.writer(self.file)
        self.writer.writerow(["timestamp", "direction", "raw_message", "msg_type", "parsed_data"])

    def log_message(self, direction: str, raw_msg: str):
        timestamp = time.time()
        try:
            parsed_msg = ProtocolParser.parse(raw_msg)
            msg_type = parsed_msg.__class__.__name__
            parsed_data = str(parsed_msg.__dict__) 
        except Exception as e:
            msg_type = "ERROR"
            parsed_data = str(e)

        self.writer.writerow([timestamp, direction, raw_msg.strip(), msg_type, parsed_data])
        self.file.flush()

    def close(self):
        self.file.close()
        