import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import time
import csv
from protocol_parser import ProtocolParser
from message import CommandMessage


def play_commands_from_csv(filename, robot_id=1, serial_connection=None):
    with open(filename, mode='r') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            if row.get('direction') != 'TX':
                continue
                
            # delay handling
            delay_sec = float(row.get('delay_ms', 0)) / 1000.0
            time.sleep(delay_sec)
            
            raw_msg = row.get('raw_message', '').strip()
            if raw_msg:
                print(f"Sending: {raw_msg}")
                if serial_connection:
                    serial_connection.write((raw_msg + '\n').encode('utf-8'))
                continue
            
            # Fallback
            try:
                args = [int(x) for x in [row.get('arg1'), row.get('arg2')] if x and x.strip()]
                cmd = CommandMessage(
                    robot_id=robot_id, 
                    command_code=int(row['command_code']), 
                    args=args
                )
                raw_cmd = ProtocolParser.serialize(cmd)
                print(f"Sending (reconstructed): {raw_cmd}")
                if serial_connection:
                    serial_connection.write((raw_cmd + '\n').encode('utf-8'))
            except Exception as e:
                print(f"Skip row due to error: {e}")
                