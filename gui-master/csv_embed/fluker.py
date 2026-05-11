"""
csv_embed/fluker.py - Logic for modifying (fluking) CSV data for educational purposes.
Updated: 01.04.2026 - Robust field mapping and raw reconstruction.
"""

import csv
import io
import os
from datetime import datetime

class CsvFluker:
    """Handles the modification and corruption of CSV data."""
    
    @staticmethod
    def fluke_data(csv_path: str, rules: list, new_rows: list = None) -> str:
        """Apply fluke rules to a CSV file."""
        output = io.StringIO()
        
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            rows = list(reader)
            
        # 1. Apply fluke rules to existing rows
        for rule in rules:
            idx = rule.get('row_index')
            field = rule.get('field')
            val = rule.get('new_value')
            
            if 0 <= idx < len(rows):
                rows[idx][field] = str(val)
                # After fluking a specific field, we update raw_message.
                # If the field WAS raw_message, we keep the user's manual string.
                if field != 'raw_message':
                    rows[idx]['raw_message'] = CsvFluker._reconstruct_raw(rows[idx])
                
        # 2. Insert new custom commands
        if new_rows:
            for nr in new_rows:
                complete_row = {fn: '' for fn in fieldnames}
                complete_row.update(nr)
                if not complete_row.get('timestamp'):
                    complete_row['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if not complete_row.get('raw_message'):
                    complete_row['raw_message'] = CsvFluker._reconstruct_raw(complete_row)
                pos = nr.get('_pos', len(rows))
                rows.insert(pos, complete_row)

        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        return output.getvalue()

    @staticmethod
    def _reconstruct_raw(row: dict) -> str:
        """Reconstruct the raw protocol string using robust field lookups."""
        
        def g(keys, default='0'):
            """Get first available key from list."""
            for k in keys:
                val = row.get(k)
                if val is not None and str(val).strip() != "":
                    return str(val).strip()
            return default

        def to_int(val, default=0):
            """Convert common string modes/types to ints."""
            s = str(val).upper()
            if s.isdigit(): return int(s)
            # Modes
            if "RUN" in s: return 0
            if "TEST" in s: return 1
            if "IDLE" in s: return 2
            if "ERROR" in s: return 3
            # Types
            if "STATUS" in s: return 0
            if "EVENT" in s: return 1
            if "COMMAND" in s: return 2
            if "RESPONSE" in s: return 3
            if "FAULT" in s: return 4
            return default

        rid = g(['robot_id', 'rid'], '1')
        msg_type_raw = g(['msg_type', 'type'], '0')
        mt_id = to_int(msg_type_raw, 0)
            
        if mt_id == 0: # STATUS
            # robot_id;0;sequence;battery;app;mode;ver
            seq = g(['sequence', 'seq'])
            bat = g(['battery_mv', 'bat_mv', 'battery'])
            app = g(['app_id', 'app'])
            mode = to_int(g(['mode']), 2)
            ver = g(['protocol_v', 'protocol', 'ver'], '1')
            return f"{rid};0;{seq};{bat};{app};{mode};{ver}"
        
        elif mt_id == 1: # EVENT
            # robot_id;1;event_code;tag
            code = g(['event_code', 'event'])
            tag = g(['tag'], '')
            base = f"{rid};1;{code}"
            if tag: base += f";{tag}"
            return base
            
        elif mt_id == 2: # COMMAND
            # robot_id;2;cmd_code;v1;v2;time
            code = g(['cmd_code', 'cmd'])
            v1 = g(['v1', 'value'], '0')
            v2 = g(['v2', 'value2'], '0')
            time = g(['time', 'value3'], '0')
            return f"{rid};2;{code};{v1};{v2};{time}"
            
        elif mt_id == 4: # FAULT
            # robot_id;4;fault_code
            code = g(['fault_code', 'fault'])
            return f"{rid};4;{code}"
            
        return row.get('raw_message', '')
