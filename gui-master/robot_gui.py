#!/usr/bin/env python3
"""
BOE-BOT ROBOT GUI v0.5
ver-date: 20.04.2026
python 3.12.10

robot_gui.py - Robot Monitor GUI

Conn:
  - Physical robot via serial port (COM3, /dev/ttyUSB0, etc.)
  - Digital Twin via TCP (localhost:9000)

Req:
    pip install PyQt6 pyserial
"""

import sys
import os
import time
import math
import socket
import threading
import serial
import serial.tools.list_ports
import io
import re
import subprocess
import base64
import csv

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QGroupBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QSplitter, QLineEdit,
    QRadioButton, QButtonGroup, QSpinBox, QStatusBar, QFrame,
    QTabWidget, QFormLayout, QFileDialog, QMessageBox, QDialog,
    QCheckBox
)
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QFileSystemWatcher, QStandardPaths, QPoint, QUrl
from PyQt6.QtGui import QColor, QFont, QPixmap, QPainter, QDesktopServices, QResizeEvent

from wpm_test import WpmTestDialog

# ─── Custom Widgets ───────────────────────────────────────────────────────────
class ClickableLabel(QLabel):
    clicked = pyqtSignal(QPoint)
    mousePressed = pyqtSignal(QPoint)
    mouseMoved = pyqtSignal(QPoint)
    mouseReleased = pyqtSignal(QPoint)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(event.pos())
            self.mousePressed.emit(event.pos())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.mouseMoved.emit(event.pos())
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.mouseReleased.emit(event.pos())
        super().mouseReleaseEvent(event)

# ─── SVG Paths ────────────────────────────────────────────────────────────────
SVGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'svgs')
CSVS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'csvs')

# Ensure csvs directory exists
os.makedirs(CSVS_DIR, exist_ok=True)

MAZES = {
    'Hashwell-1': os.path.join(SVGS_DIR, 'maze-Hashwell-1.svg'),
    'Barcelo-X': os.path.join(SVGS_DIR, 'maze-Barcelo-X.svg'),
    'Skylake-X': os.path.join(SVGS_DIR, 'maze-Skylake-X.svg'),
}

TRACKS = {
    'Granite-X': os.path.join(SVGS_DIR, 'track-Granite-X.svg'),
    'Custom (Empty)': None,
}

LINE_FOLLOWING_TRACKS = {
    'Roswell-1upgraded': os.path.join(SVGS_DIR, 'track-Roswell-1upgraded.svg'),
}

# ─── App Configuration ────────────────────────────────────────────────────────
def load_app_config():
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'configs', 'robot_profiles.json')
    if os.path.exists(config_path):
        try:
            import json
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f).get('apps', {})
        except Exception as e:
            print(f"Error loading app config: {e}")
    return {}

APP_CONFIG = load_app_config()

# Mapping app_id to SVG file name (from MAZES or TRACKS)
APP_MAPS = {}
for app_id, data in APP_CONFIG.items():
    if app_id.isdigit() and data.get('map'):
        APP_MAPS[int(app_id)] = data['map']

# ─── CSV Recorder ─────────────────────────────────────────────────────────────
class CsvRecorder:
    """Records incoming messages to CSV file."""
    
    def __init__(self, output_dir: str = CSVS_DIR):
        self.output_dir = output_dir
        self.file_path = None
        self.file = None
        self.is_recording = False
        self.message_count = 0
    
    def start_recording(self) -> str:
        """Start recording to a new CSV file. Returns file path."""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        self.file_path = os.path.join(self.output_dir, f"robot_log_{timestamp}.csv")

        self.file = open(self.file_path, 'w', newline='', encoding='utf-8')
        self.file.write("timestamp,direction,raw_message,msg_type,robot_id,sequence,battery_mv,app_id,mode,protocol_v,event_code,fault_code\n")
        self.is_recording = True
        self.message_count = 0

        return self.file_path

    def record_message(self, msg: dict):
        """Record a parsed message to CSV."""
        if not self.is_recording or not self.file:
            return

        self.message_count += 1
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        raw = msg.get("raw", "")
        msg_type = msg.get("type_name", "")
        robot_id = msg.get("robot_id", "")
        sequence = msg.get("sequence", "")
        battery_mv = msg.get("battery_mv", "")
        app_id = msg.get("app_id", "")
        mode = msg.get("mode", "")
        protocol_v = msg.get("protocol_v", "")
        event_code = msg.get("event_code", "")
        fault_code = msg.get("fault_code", "")
        direction = msg.get("direction", "RX")

        self.file.write(f'{timestamp},"{direction}","{raw}",{msg_type},{robot_id},{sequence},{battery_mv},{app_id},{mode},{protocol_v},{event_code},{fault_code}\n')
        self.file.flush()
    
    def stop_recording(self) -> str:
        """Stop recording and close file. Returns file path."""
        if self.file:
            self.file.close()
            self.file = None
        self.is_recording = False
        
        return self.file_path
    
    def set_output_dir(self, path: str):
        """Change the output directory for recordings."""
        self.output_dir = path
        os.makedirs(path, exist_ok=True)

# ─── Connection worker (runs in background thread) ────────────────────────────
class ConnectionWorker(QThread):
    message_received = pyqtSignal(str)   # raw protocol line
    connection_lost  = pyqtSignal(str)   # error message
    connected        = pyqtSignal()

    def __init__(self, mode: str, port: str = None,
                 baud: int = 115200, host: str = "localhost", tcp_port: int = 9000):
        super().__init__()
        self.mode     = mode   # "serial" or "tcp"
        self.port     = port
        self.baud     = baud
        self.host     = host
        self.tcp_port = tcp_port
        self._running = False
        self._conn    = None

    def run(self):
        self._running = True
        try:
            if self.mode == "serial":
                self._run_serial()
            else:
                self._run_tcp()
        except Exception as e:
            self.connection_lost.emit(str(e))

    def _run_serial(self):
        with serial.Serial(self.port, self.baud, timeout=1) as ser:
            self._conn = ser
            self.connected.emit()
            buf = ""
            while self._running:
                raw = ser.readline().decode("utf-8", errors="replace").strip()
                if raw:
                    self.message_received.emit(raw)

    def _run_tcp(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.host, self.tcp_port))
        self._conn = sock
        self.connected.emit()
        buf = ""
        try:
            while self._running:
                data = sock.recv(256)
                if not data:
                    break
                buf += data.decode("utf-8", errors="replace")
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    line = line.strip()
                    if line:
                        self.message_received.emit(line)
        finally:
            sock.close()

    def send(self, raw: str):
        """Send a raw command string."""
        if not self._conn:
            return
        try:
            if self.mode == "serial" and self._conn:
                self._conn.write((raw + "\n").encode("utf-8"))
            elif self.mode == "tcp" and self._conn:
                self._conn.sendall((raw + "\n").encode("utf-8"))
        except Exception as e:
            # Don't emit connection_lost for send errors - just log them
            print(f"Send error: {e}")

    def stop(self):
        self._running = False
        try:
            if self._conn:
                self._conn.close()
        except Exception:
            pass


# ─── Protocol parser (minimal, no dependency on DT internals) ────────────────
MSG_TYPES = {0: "STATUS", 1: "EVENT", 2: "COMMAND", 3: "RESPONSE", 4: "FAULT"}
ROBOT_MODES = {0: "RUN", 1: "TEST", 2: "IDLE", 3: "ERROR"}

def get_app_name(app_id: int) -> str:
    """Identify application category and name from config or range."""
    if app_id == 0: return "—"
    if app_id == 255: return "Generated Data"
    
    # Try to get from config
    app_data = APP_CONFIG.get(str(app_id))
    if app_data:
        name = app_data.get('name', '')
        category = app_data.get('category', '')
        if name and category:
            return f"{category}: {name} ({app_id})"
        elif name:
            return f"{name} ({app_id})"
            
    # Fallback to category ranges
    if 1 <= app_id <= 9: return f"Joonejälgimine ({app_id})"
    if 10 <= app_id <= 19: return f"Labürint ({app_id})"
    if 20 <= app_id <= 29: return f"Ultraheli ({app_id})"
    if app_id == 30: return f"Buss ({app_id})"
    return f"Äpp {app_id}"

def parse_message(raw: str) -> dict:
    """Parse raw protocol string into a dict. Returns None on error."""
    try:
        parts = raw.strip().split(";")
        robot_id  = int(parts[0])
        msg_type  = int(parts[1])
        type_name = MSG_TYPES.get(msg_type, f"TYPE_{msg_type}")

        result = {
            "robot_id":  robot_id,
            "msg_type":  msg_type,
            "type_name": type_name,
            "raw":       raw,
            "payload":   parts[2:],
        }

        if msg_type == 0 and len(parts) >= 7:   # STATUS
            result["sequence"]    = int(parts[2])
            result["battery_mv"]  = int(parts[3])
            result["app_id"]      = int(parts[4])
            result["mode"]        = int(parts[5])
            result["protocol_v"]  = int(parts[6])

        elif msg_type == 1 and len(parts) >= 3:  # EVENT
            result["event_code"] = int(parts[2])
            if len(parts) >= 4:
                try:
                    result["tag"] = int(parts[3])
                except (ValueError, IndexError):
                    result["tag"] = 0

        elif msg_type == 2 and len(parts) >= 6:  # COMMAND (new 6-part format)
            result["cmd_code"] = int(parts[2])
            result["v1"]       = int(parts[3])
            result["v2"]       = int(parts[4])
            result["time"]     = int(parts[5])

        elif msg_type == 4 and len(parts) >= 3:  # FAULT
            result["fault_code"] = int(parts[2])

        return result
    except Exception:
        return None


# ─── Status panel widget ──────────────────────────────────────────────────────
class StatusPanel(QGroupBox):
    def __init__(self):
        super().__init__("Staatus")
        layout = QVBoxLayout()

        self.protocol_v_clicks = 0
        self.fields = {}
        items = [
            ("robot_id",   "Robot ID"),
            ("mode",       "Mode"),
            ("app",        "Äpp"),
            ("battery",    "Aku (mV)"),
            ("angle",      "Nurk (°)"),
            ("sequence",   "Sequence"),
            ("protocol_v", "Protokoll v"),
        ]
        for i, (key, label) in enumerate(items):
            row = QHBoxLayout()
            if key == "protocol_v":
                lbl = ClickableLabel(label + ":")
                lbl.clicked.connect(self._on_protocol_v_clicked)
            else:
                lbl = QLabel(label + ":")
            lbl.setFixedWidth(90)
            val = QLabel("—")
            val.setAlignment(Qt.AlignmentFlag.AlignRight)
            val.setStyleSheet("font-weight: bold;")
            self.fields[key] = val
            row.addWidget(lbl)
            row.addWidget(val)
            layout.addLayout(row)
            
            # Add a thin separator line except after the last item
            if i < len(items) - 1:
                line = QFrame()
                line.setFrameShape(QFrame.Shape.HLine)
                line.setFrameShadow(QFrame.Shadow.Plain)
                line.setLineWidth(1)
                line.setStyleSheet("color: rgba(128, 128, 128, 64);") # Subtle line
                layout.addWidget(line)

        layout.addStretch()
        self.setLayout(layout)

    def _on_protocol_v_clicked(self):
        """Easter egg: clicking protocol v label 5 times opens WPM test."""
        self.protocol_v_clicks += 1
        if self.protocol_v_clicks >= 5:
            self.protocol_v_clicks = 0
            dialog = WpmTestDialog(self)
            dialog.exec()

    def update_angle(self, angle: float):
        self.fields["angle"].setText(f"{angle:.1f}°")

    def update_from_status(self, msg: dict):
        self.fields["robot_id"].setText(str(msg.get("robot_id", "—")))
        mode_id = msg.get("mode", -1)
        self.fields["mode"].setText(ROBOT_MODES.get(mode_id, str(mode_id)))
        app_id = msg.get("app_id", 0)
        self.fields["app"].setText(get_app_name(app_id))
        self.fields["battery"].setText(str(msg.get("battery_mv", "—")))
        self.fields["sequence"].setText(str(msg.get("sequence", "—")))
        self.fields["protocol_v"].setText(str(msg.get("protocol_v", "—")))

        # Colour mode label
        mode_colours = {0: "#4caf50", 1: "#2196f3", 2: "#9e9e9e", 3: "#f44336"}
        colour = mode_colours.get(mode_id, "#ffffff")
        self.fields["mode"].setStyleSheet(f"font-weight: bold; color: {colour};")


# ─── Log table ────────────────────────────────────────────────────────────────
class LogTable(QGroupBox):
    def __init__(self, max_rows: int = 1000, parent=None):
        super().__init__("Sõnumilogi", parent)
        layout = QVBoxLayout()

        self.max_rows = max_rows
        self.parent_window = parent
        self.auto_scroll = True
        
        # Header with buttons
        header_layout = QHBoxLayout()
        
        # Search Box
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Otsi logist (raw)...")
        self.search_edit.setFixedWidth(200)
        self.search_edit.textChanged.connect(self._filter_table)
        header_layout.addWidget(self.search_edit)
        
        header_layout.addStretch()
        
        # Auto-scroll toggle
        self.auto_scroll_btn = QPushButton("📜 Auto-scroll: sees")
        self.auto_scroll_btn.setFixedHeight(24)
        self.auto_scroll_btn.clicked.connect(self._toggle_auto_scroll)
        header_layout.addWidget(self.auto_scroll_btn)
        
        # Refresh button
        self.refresh_btn = QPushButton("↻ Värskenda")
        self.refresh_btn.setFixedHeight(24)
        self.refresh_btn.clicked.connect(self._refresh_log)
        header_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(header_layout)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Aeg", "Suund", "Tüüp", "Robot ID", "Raw"])
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(False)

        layout.addWidget(self.table)
        self.setLayout(layout)

    def _toggle_auto_scroll(self):
        """Toggle auto-scroll on/off."""
        self.auto_scroll = not self.auto_scroll
        if self.auto_scroll:
            self.auto_scroll_btn.setText("📜 Auto-scroll: sees")
            self.auto_scroll_btn.setStyleSheet("background: #4caf50; color: white;")
        else:
            self.auto_scroll_btn.setText("📜 Auto-scroll: väljas")
            self.auto_scroll_btn.setStyleSheet("background: #9e9e9e; color: white;")

    def _refresh_log(self):
        """Clear the log display."""
        # Don't clear if recording
        if self.parent_window and hasattr(self.parent_window, 'recorder') and self.parent_window.recorder.is_recording:
            QMessageBox.warning(self, "Salvestamine käib", 
                "Ei saa logi tühjendada, kuna salvestamine on käimas.\n\nPeata salvestamine enne logi tühjendamist.")
            return
        
        self.table.setRowCount(0)

    TYPE_COLOURS = {
        "STATUS":   QColor("#e8f5e9"),
        "EVENT":    QColor("#fff3e0"),
        "FAULT":    QColor("#ffebee"),
        "RESPONSE": QColor("#e3f2fd"),
        "COMMAND":  QColor("#f3e5f5"),
    }

    DIRECTION_COLOURS = {
        "RX": QColor("#c8e6c9"),  # Light green for incoming
        "TX": QColor("#bbdefb"),  # Light blue for outgoing
    }

    def _filter_table(self):
        """Filter the table based on search text."""
        search_text = self.search_edit.text().lower()
        for i in range(self.table.rowCount()):
            raw_val = self.table.item(i, 4).text().lower()
            self.table.setRowHidden(i, search_text not in raw_val)

    def add_row(self, msg: dict):
        ts   = time.strftime("%H:%M:%S")
        typ  = msg.get("type_name", "?")
        rid  = str(msg.get("robot_id", "?"))
        raw  = msg.get("raw", "")
        
        # Get direction - explicitly check for TX, otherwise default to RX
        direction = msg.get("direction", None)
        if direction == "TX":
            direction = "TX"
        else:
            direction = "RX"

        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(ts))

        # Direction item with explicit text
        dir_item = QTableWidgetItem(direction)
        dir_item.setForeground(QColor("#000000"))
        self.table.setItem(row, 1, dir_item)

        self.table.setItem(row, 2, QTableWidgetItem(typ))
        self.table.setItem(row, 3, QTableWidgetItem(rid))
        self.table.setItem(row, 4, QTableWidgetItem(raw))

        # Apply type color
        colour = self.TYPE_COLOURS.get(typ, QColor("#ffffff"))
        # Apply direction tint
        if direction == "TX":
            dir_tint = self.DIRECTION_COLOURS["TX"]
        else:
            dir_tint = self.DIRECTION_COLOURS["RX"]

        for col in range(5):
            self.table.item(row, col).setBackground(colour)

        # Set direction column specific styling
        self.table.item(row, 1).setBackground(dir_tint)
        
        # Check filter for new row
        search_text = self.search_edit.text().lower()
        if search_text and search_text not in raw.lower():
            self.table.setRowHidden(row, True)

        if self.auto_scroll:
            self.table.scrollToBottom()

        # Keep max rows
        if self.table.rowCount() > self.max_rows:
            self.table.removeRow(0)

    def add_error_row(self, raw: str):
        row = self.table.rowCount()
        self.table.insertRow(row)
        ts_item = QTableWidgetItem(time.strftime("%H:%M:%S"))
        err_item = QTableWidgetItem("PARSE ERROR")
        raw_item = QTableWidgetItem(raw)
        self.table.setItem(row, 0, ts_item)
        self.table.setItem(row, 1, QTableWidgetItem("?"))
        self.table.setItem(row, 2, QTableWidgetItem("?"))
        self.table.setItem(row, 3, QTableWidgetItem("?"))
        self.table.setItem(row, 4, raw_item)
        for col in range(5):
            self.table.item(row, col).setBackground(QColor("#ffcccc"))
        
        if self.auto_scroll:
            self.table.scrollToBottom()


from tracking.tracker import RobotTracker

class TrackingConfigDialog(QDialog):
    def __init__(self, tracker: RobotTracker, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Tracking Calibration")
        self.tracker = tracker
        layout = QFormLayout(self)
        
        _, _, current_angle = self.tracker.get_pos()

        # Row for Speed
        speed_row = QHBoxLayout()
        self.speed_spin = QSpinBox()
        self.speed_spin.setRange(1, 500)
        self.speed_spin.setValue(int(tracker.speed_px_per_s))
        self.preserve_speed = QCheckBox("Save")
        self.preserve_speed.setChecked(tracker.preserve_speed)
        speed_row.addWidget(self.speed_spin)
        speed_row.addWidget(self.preserve_speed)
        layout.addRow("Speed (px/s):", speed_row)
        
        # Row for Turn
        turn_row = QHBoxLayout()
        self.turn_spin = QSpinBox()
        self.turn_spin.setRange(1, 360)
        self.turn_spin.setValue(int(tracker.turn_deg))
        self.preserve_turn = QCheckBox("Save")
        self.preserve_turn.setChecked(tracker.preserve_turn)
        turn_row.addWidget(self.turn_spin)
        turn_row.addWidget(self.preserve_turn)
        layout.addRow("Turn angle (deg):", turn_row)

        # Row for Angle
        angle_row = QHBoxLayout()
        self.angle_spin = QSpinBox()
        self.angle_spin.setRange(0, 359)
        self.angle_spin.setValue(int(current_angle))
        self.preserve_angle = QCheckBox("Save")
        self.preserve_angle.setChecked(tracker.preserve_angle)
        angle_row.addWidget(self.angle_spin)
        angle_row.addWidget(self.preserve_angle)
        layout.addRow("Start Angle (deg):", angle_row)
        
        btns = QHBoxLayout()
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(ok_btn)
        btns.addWidget(cancel_btn)
        layout.addRow(btns)

    def apply(self):
        """Update tracker with dialog values."""
        self.tracker.set_config(self.speed_spin.value(), self.turn_spin.value())
        self.tracker.angle = float(self.angle_spin.value())
        self.tracker.saved_angle = self.tracker.angle # Save as the reference angle
        self.tracker.preserve_speed = self.preserve_speed.isChecked()
        self.tracker.preserve_turn = self.preserve_turn.isChecked()
        self.tracker.preserve_angle = self.preserve_angle.isChecked()

# ─── SVG Viewer Panel ─────────────────────────────────────────────────────────
class SvgViewer(QGroupBox):
    def __init__(self):
        super().__init__("SVG Vaataja")
        layout = QVBoxLayout()

        # Category toggle (Maze / Track)
        category_layout = QHBoxLayout()
        category_layout.addWidget(QLabel("Kategooria:"))
        self.category_combo = QComboBox()
        self.category_combo.addItems(["Maze", "Joonejälgimine", "Track"])
        self.category_combo.currentTextChanged.connect(self._on_category_change)
        category_layout.addWidget(self.category_combo)
        
        # Tracking tools
        category_layout.addStretch()
        self.clear_btn = QPushButton("↻")
        self.clear_btn.setFixedWidth(30)
        self.clear_btn.setToolTip("Puhasta tee")
        self.clear_btn.clicked.connect(self.clear_path)
        category_layout.addWidget(self.clear_btn)

        self.rotate_btn = QPushButton("Pööra robotit")
        self.rotate_btn.setToolTip("Pööra robot 180°")
        self.rotate_btn.clicked.connect(self.rotate_robot)
        category_layout.addWidget(self.rotate_btn)

        self.clear_draw_btn = QPushButton("🗑️")
        self.clear_draw_btn.setFixedWidth(30)
        self.clear_draw_btn.setToolTip("Puhasta joonistus")
        self.clear_draw_btn.clicked.connect(self.clear_user_lines)
        category_layout.addWidget(self.clear_draw_btn)
        
        self.draw_btn = QPushButton("✏️")
        self.draw_btn.setFixedWidth(40)
        self.draw_btn.setCheckable(True)
        self.draw_btn.setToolTip("Joonistamise režiim")
        self.draw_btn.toggled.connect(self._on_draw_toggled)
        category_layout.addWidget(self.draw_btn)
        
        self.pause_btn = QPushButton("⏸️")
        self.pause_btn.setFixedWidth(40)
        self.pause_btn.setCheckable(True)
        self.pause_btn.toggled.connect(self._on_pause_toggled)
        self.pause_btn.setToolTip("Pausi/Jätka vaadet")
        category_layout.addWidget(self.pause_btn)

        self.live_btn = QPushButton("🛜")
        self.live_btn.setFixedWidth(40)
        self.live_btn.setCheckable(True)
        self.live_btn.setChecked(True)
        self.live_btn.toggled.connect(self._on_live_toggled)
        self.live_btn.setToolTip("Live-jälgimine: SEES")
        self.live_btn.setStyleSheet("background: #e3f2fd; border: 1px solid #2196f3;")
        category_layout.addWidget(self.live_btn)

        self.settings_btn = QPushButton("⚙️")
        self.settings_btn.setFixedWidth(40)
        self.settings_btn.clicked.connect(self._open_settings)
        self.settings_btn.setToolTip("Seaded")
        category_layout.addWidget(self.settings_btn)

        self.lock_map_check = QCheckBox("Lukk")
        self.lock_map_check.setToolTip("Lukusta kaart (keela automaatne vahetus)")
        self.lock_map_check.setStyleSheet("font-size: 10px; font-weight: normal; margin-left: 5px;")
        category_layout.addWidget(self.lock_map_check)
        
        layout.addLayout(category_layout)

        # SVG selector
        selector_layout = QHBoxLayout()
        selector_layout.addWidget(QLabel("SVG:"))
        self.svg_combo = QComboBox()
        self.svg_combo.currentTextChanged.connect(self._on_svg_change)
        selector_layout.addWidget(self.svg_combo)
        layout.addLayout(selector_layout)

        # SVG display widget (using ClickableLabel)
        self.svg_label = ClickableLabel()
        self.svg_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.svg_label.setMinimumSize(400, 300)
        self.svg_label.setStyleSheet("background: #f5f5f5; border: 1px solid #ccc;")
        self.svg_label.clicked.connect(self._on_label_clicked)
        self.svg_label.mousePressed.connect(self._on_mouse_pressed)
        self.svg_label.mouseMoved.connect(self._on_mouse_moved)
        self.svg_label.mouseReleased.connect(self._on_mouse_released)
        layout.addWidget(self.svg_label)

        self.setLayout(layout)

        # State
        self.current_category = "Maze"
        self.current_svg_path = MAZES['Hashwell-1']
        self.base_pixmap = None
        self.tracker = RobotTracker()
        self.tracker.set_segment_mode(True)
        
        # Drawing state
        self.user_lines = []     # List of strokes (each stroke is a list of coordinates in world-space)
        self.current_stroke = [] # Points in currently drawing stroke
        
        self._update_svg_combo()
        self._load_svg()

    def set_map_by_app_id(self, app_id: int):
        """Automatically switch map based on application ID."""
        if self.lock_map_check.isChecked():
            return
            
        if app_id == 255: # Generated data/special mode
            return
            
        svg_name = APP_MAPS.get(app_id)
        if not svg_name and 1 <= app_id <= 9:
            svg_name = "Roswell-1upgraded"
        if not svg_name:
            return

        # Config may contain a filename; combo boxes use display names.
        if isinstance(svg_name, str):
            svg_name = os.path.basename(svg_name)
            for prefix in ("maze-", "track-"):
                if svg_name.startswith(prefix):
                    svg_name = svg_name[len(prefix):]
            if svg_name.endswith(".svg"):
                svg_name = svg_name[:-4]
            
        # Determine category by app id range
        if 1 <= app_id <= 9:
            category = "Joonejälgimine"
        elif 10 <= app_id <= 19:
            category = "Maze"
        else:
            category = "Track"
        
        # If already set, do nothing
        if self.current_category == category and self.svg_combo.currentText() == svg_name:
            return
            
        # Switch
        self.category_combo.setCurrentText(category)
        self.svg_combo.setCurrentText(svg_name)

    def _on_label_clicked(self, pos: QPoint):
        """Handle map click for tracker placement / start segment selection."""
        if self.draw_btn.isChecked():
            return

        world_pos = self._map_to_world(pos)
        if world_pos is None:
            return

        world_x, world_y = world_pos

        if self.current_category == "Maze":
            segment_name = self.tracker.find_nearest_segment(world_x, world_y)
            if segment_name is not None:
                self.tracker.set_start_segment(segment_name)
        elif self.current_category == "Joonejälgimine":
            # Keep marker-track controlled by marker events; clicking should not move it off route.
            return
        else:
            self.tracker.reset(world_x, world_y, self.tracker.angle)

        self._draw_tracking()

    def _on_category_change(self, category: str):
        self.current_category = category
        if category == "Maze":
            self.tracker.set_segment_mode(True)
            self.tracker.set_marker_mode(False)
        elif category == "Joonejälgimine":
            self.tracker.set_marker_mode(True)
        else:
            self.tracker.set_segment_mode(False)
            self.tracker.set_marker_mode(False)
        self._update_svg_combo()

        current_name = self.svg_combo.currentText()
        if category == "Maze" and current_name:
            self.tracker.load_maze_from_json(current_name)
        elif category == "Joonejälgimine" and current_name:
            self.tracker.load_marker_track_from_json(current_name)
        else:
            self.tracker.full_reset()
        
        self._load_svg()

    def _update_svg_combo(self):
        self.svg_combo.clear()
        if self.current_category == "Maze":
            self.svg_combo.addItems(list(MAZES.keys()))
        elif self.current_category == "Joonejälgimine":
            self.svg_combo.addItems(list(LINE_FOLLOWING_TRACKS.keys()))
        else:
            self.svg_combo.addItems(list(TRACKS.keys()))

    def _on_svg_change(self, name: str):
        if self.current_category == "Maze":
            self.current_svg_path = MAZES.get(name)
            self.tracker.set_segment_mode(True)
            self.tracker.set_marker_mode(False)
            self.tracker.load_maze_from_json(name)
        elif self.current_category == "Joonejälgimine":
            self.current_svg_path = LINE_FOLLOWING_TRACKS.get(name)
            self.tracker.set_marker_mode(True)
            self.tracker.load_marker_track_from_json(name)
        else:
            self.current_svg_path = TRACKS.get(name)
            self.tracker.set_segment_mode(False)
            self.tracker.set_marker_mode(False)
            self.tracker.full_reset()
            
        self._load_svg()

    def _open_settings(self):
        dlg = TrackingConfigDialog(self.tracker, self)
        if dlg.exec():
            dlg.apply()
            self._draw_tracking()

    def _on_live_toggled(self, checked):
        if checked:
            self.live_btn.setToolTip("Live-jälgimine: SEES")
            self.live_btn.setStyleSheet("background: #e3f2fd; border: 1px solid #2196f3;")
        else:
            self.live_btn.setToolTip("Live-jälgimine: VÄLJAS")
            self.live_btn.setStyleSheet("background: #f5f5f5; border: 1px solid #9e9e9e; color: #9e9e9e;")

    def _on_draw_toggled(self, checked):
        if checked:
            self.draw_btn.setStyleSheet("background: #fff9c4; border: 1px solid #fbc02d;")
            self.svg_label.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.draw_btn.setStyleSheet("")
            self.svg_label.setCursor(Qt.CursorShape.ArrowCursor)

    def _map_to_world(self, pos: QPoint):
        """Map label coordinate to world (pixmap) coordinate."""
        if self.base_pixmap is None:
            return None
        lw, lh = self.svg_label.width(), self.svg_label.height()
        pw, ph = self.base_pixmap.width(), self.base_pixmap.height()
        scale = min(lw / pw, lh / ph)
        dw, dh = pw * scale, ph * scale
        ox = (lw - dw) / 2
        oy = (lh - dh) / 2
        
        click_x, click_y = pos.x(), pos.y()
        if ox <= click_x <= ox + dw and oy <= click_y <= oy + dh:
            return (click_x - ox) / scale, (click_y - oy) / scale
        return None

    def _on_mouse_pressed(self, pos: QPoint):
        if not self.draw_btn.isChecked():
            return
        world_pos = self._map_to_world(pos)
        if world_pos:
            self.current_stroke = [world_pos]
            self._draw_tracking()

    def _on_mouse_moved(self, pos: QPoint):
        if not self.draw_btn.isChecked() or not self.current_stroke:
            return
        world_pos = self._map_to_world(pos)
        if world_pos:
            self.current_stroke.append(world_pos)
            self._draw_tracking()

    def _on_mouse_released(self, pos: QPoint):
        if not self.draw_btn.isChecked() or not self.current_stroke:
            return
        self.user_lines.append(self.current_stroke)
        self.current_stroke = []
        self._draw_tracking()

    def clear_user_lines(self):
        self.user_lines = []
        self.current_stroke = []
        self._draw_tracking()

    def _on_pause_toggled(self, checked):
        if checked:
            self.pause_btn.setText("▶️")
            self.pause_btn.setStyleSheet("background: #4caf50; color: white;")
        else:
            self.pause_btn.setText("⏸️")
            self.pause_btn.setStyleSheet("")
        
        # Sync with replay worker if active
        try:
            from __main__ import win
            if hasattr(win, 'dt_options') and win.dt_options.replay_worker:
                if checked:
                    win.dt_options.replay_worker.pause()
                else:
                    win.dt_options.replay_worker.resume()
        except Exception:
            # Fallback if global access fails, search for DtOptionsPanel
            # This is a bit hacky but works for this structure
            pass

    def clear_path(self):
        # Full reset: return to middle (400,300) and clear path
        self.tracker.full_reset()
        self._draw_tracking()

    def rotate_robot(self):
        """Rotate robot direction on the maze visualisation map."""
        if self.current_category != "Maze":
            return
        self.tracker.rotate_robot_direction(clockwise=True)
        self._draw_tracking()

    def process_msg(self, msg: dict, ts_str: str = None):
        """Update robot position and redraw."""
        if self.pause_btn.isChecked():
            return
            
        ts = None
        if ts_str:
            try:
                # Expecting format from CSV: "2026-01-13 20:06:01.839929"
                from datetime import datetime
                dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S.%f")
                ts = dt.timestamp()
            except ValueError:
                try:
                    dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                    ts = dt.timestamp()
                except ValueError:
                    pass
        
        self.tracker.process_message(msg, ts)
        self._draw_tracking()

    def _load_svg(self):
        """Load and display SVG file or show blank if None."""
        try:
            if self.current_svg_path is None:
                # Show blank/empty canvas for custom tracking
                self.base_pixmap = QPixmap(800, 600)
                self.base_pixmap.fill(QColor("#f0f0f0"))
                self.svg_label.setText("") # Clear any previous error text
            else:
                renderer = QSvgRenderer(self.current_svg_path)
                self.base_pixmap = QPixmap(renderer.defaultSize())
                self.base_pixmap.fill(Qt.GlobalColor.transparent)
                painter = QPainter(self.base_pixmap)
                renderer.render(painter)
                painter.end()

            self._draw_tracking()
        except Exception as e:
            self.svg_label.setText(f"Error loading SVG:\n{e}")

    def _draw_tracking(self):
        if self.base_pixmap is None:
            return

        scaled_bg = self.base_pixmap.scaled(
            self.svg_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )

        pw, ph = self.base_pixmap.width(), self.base_pixmap.height()
        sw, sh = scaled_bg.width(), scaled_bg.height()
        scale_x = sw / pw
        scale_y = sh / ph

        with QPainter(scaled_bg) as painter:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            # Draw User Lines
            painter.setPen(QColor("#424242"))
            draw_pen = painter.pen()
            draw_pen.setWidth(2)
            painter.setPen(draw_pen)
            
            all_strokes = self.user_lines + ([self.current_stroke] if self.current_stroke else [])
            for stroke in all_strokes:
                if len(stroke) > 1:
                    for i in range(len(stroke) - 1):
                        p1 = stroke[i]
                        p2 = stroke[i + 1]
                        painter.drawLine(
                            int(p1[0] * scale_x), int(p1[1] * scale_y),
                            int(p2[0] * scale_x), int(p2[1] * scale_y)
                        )

            if self.current_category in ("Maze", "Joonejälgimine"):
                states = self.tracker.get_segment_states()
                visited = states["visited"]
                current = states["current"]
                completed = states["completed"]
                error_segment = states["error_segment"]

                for seg_name, (p1, p2) in self.tracker.segments.items():
                    # Set line width (maybe need to change with different maps?)
                    width = 12
                    if completed and seg_name in visited:
                        # Path completed -> all passed segments turn green
                        color = QColor("#39b63e")
                    elif error_segment is not None and seg_name == error_segment:
                        # EV_LINE_LOST -> last segment turns red
                        color = QColor("#e4382c")
                    elif (seg_name in current if isinstance(current, set) else seg_name == current):
                        # Segment where robot currently is
                        color = QColor("#38a4e2")
                    elif seg_name in visited:
                        # Segment where robot has been 
                        color = QColor("#376580")
                    else:
                        continue


                    pen = painter.pen()
                    pen.setColor(color)
                    pen.setWidth(width)
                    painter.setPen(pen)

                    painter.drawLine(
                        int(p1[0] * scale_x), int(p1[1] * scale_y),
                        int(p2[0] * scale_x), int(p2[1] * scale_y)
                    )
            else:
                if len(self.tracker.path) > 1:
                    painter.setPen(QColor("#ff5722"))
                    path_pen = painter.pen()
                    path_pen.setWidth(3)
                    painter.setPen(path_pen)

                    for i in range(len(self.tracker.path) - 1):
                        p1 = self.tracker.path[i]
                        p2 = self.tracker.path[i + 1]
                        painter.drawLine(
                            int(p1[0] * scale_x), int(p1[1] * scale_y),
                            int(p2[0] * scale_x), int(p2[1] * scale_y)
                        )

            x, y, angle = self.tracker.get_pos()
            sx, sy = x * scale_x, y * scale_y

            painter.setBrush(QColor("#f44336"))
            painter.setPen(Qt.GlobalColor.black)
            painter.drawEllipse(int(sx - 8), int(sy - 8), 16, 16)

            rad = math.radians(angle)
            px = sx + 15 * math.cos(rad)
            py = sy - 15 * math.sin(rad)
            painter.drawLine(int(sx), int(sy), int(px), int(py))

        self.svg_label.setPixmap(scaled_bg)
        self.svg_label.setText("")




    def resizeEvent(self, event: QResizeEvent):
        super().resizeEvent(event)
        # Reload SVG on resize to get proper scaling
        if hasattr(self, 'svg_label') and self.svg_label.pixmap():
            self._load_svg()


# ─── Connection panel ─────────────────────────────────────────────────────────
class ConnectionPanel(QGroupBox):
    def __init__(self):
        super().__init__("Ühendus")
        layout = QVBoxLayout()

        # Mode selection
        mode_layout = QHBoxLayout()
        self.rb_serial = QRadioButton("Serial (päris robot)")
        self.rb_tcp    = QRadioButton("TCP (Digital Twin)")
        self.rb_tcp.setChecked(True)
        mode_layout.addWidget(self.rb_serial)
        mode_layout.addWidget(self.rb_tcp)
        layout.addLayout(mode_layout)

        # Serial settings
        self.serial_group = QGroupBox("Serial")
        serial_layout = QHBoxLayout()
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(120)
        self._refresh_ports()
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["9600", "57600", "115200"])
        self.baud_combo.setCurrentText("115200")
        serial_layout.addWidget(QLabel("Port:"))
        serial_layout.addWidget(self.port_combo)
        serial_layout.addWidget(QLabel("Baud:"))
        serial_layout.addWidget(self.baud_combo)
        refresh_btn = QPushButton("↻")
        refresh_btn.setFixedWidth(30)
        refresh_btn.clicked.connect(self._refresh_ports)
        serial_layout.addWidget(refresh_btn)
        self.serial_group.setLayout(serial_layout)
        layout.addWidget(self.serial_group)

        # TCP settings
        self.tcp_group = QGroupBox("TCP / Digital Twin")
        tcp_layout = QHBoxLayout()
        self.host_edit = QLineEdit("localhost")
        self.host_edit.setFixedWidth(120)
        self.tcp_port_spin = QSpinBox()
        self.tcp_port_spin.setRange(1024, 65535)
        self.tcp_port_spin.setValue(9000)
        tcp_layout.addWidget(QLabel("Host:"))
        tcp_layout.addWidget(self.host_edit)
        tcp_layout.addWidget(QLabel("Port:"))
        tcp_layout.addWidget(self.tcp_port_spin)
        self.tcp_group.setLayout(tcp_layout)
        layout.addWidget(self.tcp_group)

        # Connect button
        self.connect_btn = QPushButton("Ühenda")
        self.connect_btn.setStyleSheet("font-weight: bold; padding: 6px;")
        layout.addWidget(self.connect_btn)

        self.setLayout(layout)

        # Toggle visibility based on mode
        self.rb_serial.toggled.connect(self._toggle_mode)
        self.rb_tcp.toggled.connect(self._toggle_mode)
        self._toggle_mode()

    def _toggle_mode(self):
        is_serial = self.rb_serial.isChecked()
        self.serial_group.setVisible(is_serial)
        self.tcp_group.setVisible(not is_serial)

    def _refresh_ports(self):
        self.port_combo.clear()
        ports = [p.device for p in serial.tools.list_ports.comports()]
        if ports:
            self.port_combo.addItems(ports)
        else:
            self.port_combo.addItem("(portid puuduvad)")

    def get_mode(self) -> str:
        return "serial" if self.rb_serial.isChecked() else "tcp"

    def get_serial_port(self) -> str:
        return self.port_combo.currentText()

    def get_baud(self) -> int:
        return int(self.baud_combo.currentText())

    def get_host(self) -> str:
        return self.host_edit.text()

    def get_tcp_port(self) -> int:
        return self.tcp_port_spin.value()


# ─── Command panel ────────────────────────────────────────────────────────────
from PyQt6.QtWidgets import QInputDialog

class CommandPanel(QGroupBox):
    send_command = pyqtSignal(str)

    def __init__(self):
        super().__init__("Käsud")
        layout = QVBoxLayout()

        self.current_robot_id = 1
        self.current_mode = 2  # Default to IDLE

        # Quick command buttons - Row 1
        btn_layout1 = QHBoxLayout()
        self.ping_btn   = QPushButton("Ping")
        self.status_btn = QPushButton("Get Status")
        self.mem_dump_btn = QPushButton("Mem Dump")
        
        self.ping_btn.clicked.connect(lambda: self._send_core_cmd(1))
        self.status_btn.clicked.connect(lambda: self._send_core_cmd(2)) # Note: status is often 2 or just ping
        self.mem_dump_btn.clicked.connect(lambda: self._send_core_cmd(2)) # As requested: 2. memory_dump
        
        btn_layout1.addWidget(self.ping_btn)
        btn_layout1.addWidget(self.status_btn)
        btn_layout1.addWidget(self.mem_dump_btn)
        layout.addLayout(btn_layout1)

        # Quick command buttons - Row 2
        btn_layout2 = QHBoxLayout()
        self.motor_btn = QPushButton("Set Motor")
        self.mode_btn = QPushButton("Set Mode")
        
        self.motor_btn.clicked.connect(self._send_set_motor)
        self.mode_btn.clicked.connect(self._send_set_mode)
        
        btn_layout2.addWidget(self.motor_btn)
        btn_layout2.addWidget(self.mode_btn)
        layout.addLayout(btn_layout2)

        # Quick command buttons - Row 3 (EEPROM/Settings)
        btn_layout3 = QHBoxLayout()
        self.speed_btn = QPushButton("Max Speed")
        self.qti_btn = QPushButton("QTI Thres")
        self.id_btn = QPushButton("Change ID")
        
        self.speed_btn.clicked.connect(self._send_max_speed)
        self.qti_btn.clicked.connect(self._send_qti_thres)
        self.id_btn.clicked.connect(self._send_change_id)
        
        btn_layout3.addWidget(self.speed_btn)
        btn_layout3.addWidget(self.qti_btn)
        btn_layout3.addWidget(self.id_btn)
        layout.addLayout(btn_layout3)

        # Manual command input
        raw_layout = QHBoxLayout()
        self.raw_edit = QLineEdit()
        self.raw_edit.setPlaceholderText("robot_id;2;command_code;...")
        self.raw_edit.returnPressed.connect(self._send_raw)
        send_btn = QPushButton("Saada")
        send_btn.clicked.connect(self._send_raw)
        raw_layout.addWidget(self.raw_edit)
        raw_layout.addWidget(send_btn)
        layout.addLayout(raw_layout)

        self.setLayout(layout)

    def update_robot_info(self, robot_id, mode):
        self.current_robot_id = robot_id
        self.current_mode = mode

    def _send_core_cmd(self, cmd_code):
        # Using CommandManager to format
        cmd = CommandManager.format_core_cmd(self.current_robot_id, cmd_code)
        self.send_command.emit(cmd)

    def _send_set_motor(self):
        # Validate using CommandManager
        allowed, err = CommandManager.validate_set_motor(self.current_mode)
        if not allowed:
            QMessageBox.critical(self, "Viga", err)
            return
        
        m1, ok1 = QInputDialog.getInt(self, "Motor 1", "Sisesta mootor 1 kiirus (-255 kuni 255):", 0, -255, 255)
        if not ok1: return
        m2, ok2 = QInputDialog.getInt(self, "Motor 2", "Sisesta mootor 2 kiirus (-255 kuni 255):", 0, -255, 255)
        if ok2:
            cmd = CommandManager.get_set_motor_cmd(self.current_robot_id, m1, m2)
            self.send_command.emit(cmd)

    def _send_set_mode(self):
        modes = ["RUN (0)", "TEST (1)", "IDLE (2)", "ERROR (3)"]
        mode_str, ok = QInputDialog.getItem(self, "Set Mode", "Vali uus režiim:", modes, 2, False)
        if ok:
            mode_val = int(mode_str.split('(')[1].split(')')[0])
            cmd = CommandManager.get_set_mode_cmd(self.current_robot_id, mode_val)
            self.send_command.emit(cmd)

    def _send_max_speed(self):
        val, ok = QInputDialog.getInt(self, "Max Speed", "Sisesta max kiirus (0-255):", 255, 0, 255)
        if ok:
            cmd = CommandManager.get_max_speed_cmd(self.current_robot_id, val)
            self.send_command.emit(cmd)

    def _send_qti_thres(self):
        val, ok = QInputDialog.getInt(self, "QTI Threshold", "Sisesta QTI lävi:", 500, 0, 1023)
        if ok:
            cmd = CommandManager.get_qti_thres_cmd(self.current_robot_id, val)
            self.send_command.emit(cmd)

    def _send_change_id(self):
        val, ok = QInputDialog.getInt(self, "Change Robot ID", "Sisesta uus Robot ID (1-255):", self.current_robot_id, 1, 255)
        if ok:
            cmd = CommandManager.get_change_id_cmd(self.current_robot_id, val)
            self.send_command.emit(cmd)

    def _send_raw(self):
        text = self.raw_edit.text().strip()
        if text:
            self.send_command.emit(text)
            self.raw_edit.clear()

    def set_enabled(self, enabled: bool):
        self.ping_btn.setEnabled(enabled)
        self.status_btn.setEnabled(enabled)
        self.mem_dump_btn.setEnabled(enabled)
        self.motor_btn.setEnabled(enabled)
        self.mode_btn.setEnabled(enabled)
        self.speed_btn.setEnabled(enabled)
        self.qti_btn.setEnabled(enabled)
        self.id_btn.setEnabled(enabled)
        self.raw_edit.setEnabled(enabled)


# ─── CSV Decoder Utility ──────────────────────────────────────────────────────
class CsvDecoder:
    """Decodes data from various Robot Monitor formats (CSV, Embedded PY, EXE)."""
    
    @staticmethod
    def decode(file_path: str) -> str:
        """Determines file type and extracts original CSV content."""
        ext = os.path.splitext(file_path)[1].lower()
        
        if ext == ".csv":
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        
        elif ext == ".py":
            return CsvDecoder._decode_python(file_path)
            
        elif ext == ".exe":
            return CsvDecoder._decode_exe(file_path)
            
        else:
            raise ValueError(f"Tundmatu failivorming: {ext}")

    @staticmethod
    def _decode_python(file_path: str) -> str:
        """Extracts and decrypts data from embedded Python script using regex."""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Extract CSV_DATA
        data_match = re.search(r'CSV_DATA\s*=\s*"""(.*?)"""', content, re.DOTALL)
        if not data_match:
            # Fallback for single quotes or no quotes
            data_match = re.search(r"CSV_DATA\s*=\s*['\"](.*?)['\"]", content)
            
        if not data_match:
            raise ValueError("Viga: Ei leidnud CSV_DATA väljat embedded failist.")
            
        raw_b64 = data_match.group(1).strip()
        
        # Extract XOR_KEY if present
        key_match = re.search(r"XOR_KEY\s*=\s*bytes\(\[(.*?)\]\)", content)
        
        if key_match:
            # XOR Decryption
            key_bytes = bytes([int(x.strip()) for x in key_match.group(1).split(",") if x.strip()])
            encrypted = base64.b64decode(raw_b64)
            decrypted = bytes(b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(encrypted))
            return decrypted.decode("utf-8")
        else:
            # Base64 only
            return base64.b64decode(raw_b64).decode("utf-8")

    @staticmethod
    def _decode_exe(file_path: str) -> str:
        """Executes the compiled binary and captures the CSV output from stdout."""
        try:
            # The template script prints the CSV to stdout when run
            # We use startupinfo to hide the console window on Windows
            startupinfo = None
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
            output = subprocess.check_output(
                [file_path], 
                stderr=subprocess.STDOUT, 
                startupinfo=startupinfo,
                timeout=10
            )
            return output.decode("utf-8", errors="replace")
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"EXE faili käivitamine ebaõnnestus: {e.output.decode('utf-8', errors='replace')}")
        except Exception as e:
            raise RuntimeError(f"Viga EXE dekodeerimisel: {e}")


# ─── CSV Replay Worker ────────────────────────────────────────────────────────
class CsvReplayWorker(QThread):
    """Replays CSV data with timing."""

    line_replayed = pyqtSignal(str, str, str)  # raw message, direction, timestamp
    replay_started = pyqtSignal()
    replay_finished = pyqtSignal()
    progress_update = pyqtSignal(int, int)  # current, total

    def __init__(self, file_path: str, use_timing: bool = True,
                 send_via_connection=None, direction_filter: str = None,
                 behavioral_replay: bool = False, csv_content: str = None):
        """
        Args:
            file_path: Path to CSV file
            use_timing: Whether to preserve original timing
            send_via_connection: ConnectionWorker instance to send commands through
            direction_filter: Filter by direction ('RX', 'TX', or None for all)
            behavioral_replay: Translate RX to TX commands (send to robot)
            csv_content: Raw CSV string (if already decoded from PY/EXE)
        """
        super().__init__()
        self.file_path = file_path
        self.csv_content = csv_content
        self.use_timing = use_timing
        self.send_via_connection = send_via_connection
        self.direction_filter = direction_filter
        self.behavioral_replay = behavioral_replay
        self.translator = RXToTXTranslator() if behavioral_replay else None
        self._running = False
        self._paused = False
        self._pause_cond = threading.Condition(threading.Lock())
    
    def pause(self):
        with self._pause_cond:
            self._paused = True
    
    def resume(self):
        with self._pause_cond:
            self._paused = False
            self._pause_cond.notify_all()
    
    def run(self):
        import csv
        from datetime import datetime
        
        self._running = True
        self.replay_started.emit()
        
        try:
            if self.csv_content:
                f = io.StringIO(self.csv_content)
                reader = csv.DictReader(f)
                rows = list(reader)
            else:
                with open(self.file_path, mode='r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    rows = list(reader)
            
            total = len(rows)
            prev_timestamp = None
            
            for i, row in enumerate(rows):
                if not self._running:
                    break

                # Support pausing the thread
                with self._pause_cond:
                    while self._paused and self._running:
                        self._pause_cond.wait(0.1)

                # Get direction from CSV, or infer from message type if missing
                direction = row.get('direction', '').strip()
                if not direction:
                    # Infer direction from msg_type for old CSV format
                    msg_type = row.get('msg_type', '').strip()
                    if msg_type in ['COMMAND', 'RESPONSE']:
                        direction = 'TX'
                    else:
                        direction = 'RX'
                
                if self.direction_filter and direction != self.direction_filter:
                    continue

                raw_msg = row.get('raw_message', '').strip()
                if not raw_msg:
                    continue
                
                # Handle timing
                if self.use_timing:
                    ts_value = row.get('timestamp', '0')
                    # Try to parse timestamp (could be float or datetime string)
                    try:
                        # Try as float (Unix timestamp)
                        timestamp = float(ts_value)
                    except ValueError:
                        # Try as datetime string
                        formats = ["%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"]
                        timestamp = 0
                        for fmt in formats:
                            try:
                                dt = datetime.strptime(ts_value, fmt)
                                timestamp = dt.timestamp()
                                break
                            except ValueError:
                                continue
                    
                    if prev_timestamp is not None:
                        delay = timestamp - prev_timestamp
                        if delay > 0:
                            time.sleep(min(delay, 5.0))  # Cap at 5s
                    prev_timestamp = timestamp
                
                # Send via connection if enabled
                if self.send_via_connection:
                    if direction == 'TX':
                        # Original TX command from CSV
                        self.send_via_connection.send(raw_msg)
                    elif direction == 'RX' and self.behavioral_replay:
                        # Translate RX (reported by robot) to TX (drive robot)
                        msg_dict = parse_message(raw_msg)
                        if msg_dict:
                            tx_cmds = self.translator.translate(msg_dict)
                            for cmd in tx_cmds:
                                self.send_via_connection.send(cmd)

                # Always emit for log display
                self.line_replayed.emit(raw_msg, direction, row.get('timestamp', ''))
                self.progress_update.emit(i + 1, total)
            
            self.replay_finished.emit()

        except Exception as e:
            print(f"REPLAY ERROR: {e}")
            self.line_replayed.emit(f"REPLAY ERROR: {e}", "RX", "")
            self.replay_finished.emit()
    
    def stop(self):
        self._running = False


from csv_embed.fluker import CsvFluker

class CsvFlukeDialog(QDialog):
    """Dialog for configuring data corruption (fluking) in CSV files."""
    
    def __init__(self, csv_path: str, existing_rules=None, existing_rows=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Data Fluking (Andmete rikkumine)")
        self.setMinimumWidth(800)
        self.setMinimumHeight(500)
        self.csv_path = csv_path
        self.fluke_rules = list(existing_rules) if existing_rules else []
        self.new_rows = list(existing_rows) if existing_rows else []
        self._loading = True
        
        self._build_ui()
        self._load_csv()
        self._apply_existing_visuals()
        
        self._loading = False
        self.table.itemChanged.connect(self._on_item_changed)

    def _on_item_changed(self, item):
        if self._loading: return
        
        row_idx = item.row()
        col_idx = item.column()
        new_val = item.text()
        
        # Map columns to CSV fields
        col_to_field = {
            3: "battery_mv",
            4: "mode",
            7: "raw_message"
        }
        
        if col_idx in col_to_field:
            field = col_to_field[col_idx]
            # Update or add rule, removing duplicates for same row/field
            self.fluke_rules = [r for r in self.fluke_rules if not (r['row_index'] == row_idx and r['field'] == field)]
            self.fluke_rules.append({
                'row_index': row_idx,
                'field': field,
                'new_value': new_val
            })
            # Visual feedback for manual edit
            item.setForeground(QColor("#f44336"))
            # If they edited Raw, we can't easily auto-update other columns, 
            # but the replayer uses Raw anyway.

    def _apply_existing_visuals(self):
        """Show already configured rules in the table."""
        for rule in self.fluke_rules:
            row_idx = rule['row_index']
            if row_idx < self.table.rowCount():
                self.table.setItem(row_idx, 6, QTableWidgetItem(f"{rule['field']} → {rule['new_value']}"))
                self.table.item(row_idx, 6).setForeground(QColor("#f44336"))
        
        # Note: New rows visuals are already added in _load_csv if we logic it, 
        # but for now _add_custom_row adds them fresh. 
        # To keep it simple, we'll just allow adding new ones for now.

    def _build_ui(self):
        layout = QVBoxLayout()

        # 1. Main Table
        self.table = QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels([
            "Vali", "Rida", "Tüüp", "Aku (mV)", "Mode", "Event/Cmd", "Väärtus", "Raw"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        # 2. Controls
        ctrl_layout = QHBoxLayout()
        self.field_combo = QComboBox()
        self.field_combo.addItems(["battery_mv", "mode", "event_code", "cmd_code", "v1", "v2", "time"])
        self.val_edit = QLineEdit()
        self.val_edit.setPlaceholderText("Uus väärtus...")
        apply_btn = QPushButton("📉 Rakenda valitud ridadele")
        apply_btn.clicked.connect(self._apply_fluke)
        
        ctrl_layout.addWidget(QLabel("Muuda välja:"))
        ctrl_layout.addWidget(self.field_combo)
        ctrl_layout.addWidget(self.val_edit)
        ctrl_layout.addWidget(apply_btn)
        layout.addLayout(ctrl_layout)

        # 3. Add Custom Row
        add_layout = QHBoxLayout()
        add_btn = QPushButton("➕ Lisa uus rida lõppu")
        add_btn.clicked.connect(self._add_custom_row)
        add_layout.addWidget(add_btn)
        add_layout.addStretch()
        layout.addLayout(add_layout)

        # 4. Final Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        ok_btn = QPushButton("OK")
        ok_btn.setStyleSheet("background: #4caf50; color: white; padding: 6px 20px;")
        ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(ok_btn)
        cancel_btn = QPushButton("Tühista")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def _load_csv(self):
        """Load CSV content into the table."""
        try:
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self.csv_rows = list(reader)
            
            self.table.setRowCount(len(self.csv_rows))
            for i, row in enumerate(self.csv_rows):
                # Checkbox
                chk_item = QTableWidgetItem()
                chk_item.setCheckState(Qt.CheckState.Unchecked)
                self.table.setItem(i, 0, chk_item)
                
                # Metadata
                self.table.setItem(i, 1, QTableWidgetItem(str(i)))
                self.table.setItem(i, 2, QTableWidgetItem(row.get('msg_type', '')))
                
                # Use fallbacks for common battery/mode fields
                bat = row.get('battery_mv') or row.get('bat_mv') or ""
                self.table.setItem(i, 3, QTableWidgetItem(str(bat)))
                
                mode = row.get('mode') or ""
                self.table.setItem(i, 4, QTableWidgetItem(str(mode)))
                
                # Logic to show event/cmd code
                mt = str(row.get('msg_type', '')).upper()
                code = ''
                if mt in ('EVENT', '1'): 
                    code = row.get('event_code') or row.get('event') or ""
                elif mt in ('COMMAND', '2'):
                    code = row.get('cmd_code') or row.get('cmd') or ""
                    if not code:
                        parts = row.get('raw_message', '').split(';')
                        if len(parts) >= 3: code = parts[2]
                self.table.setItem(i, 5, QTableWidgetItem(str(code)))
                
                self.table.setItem(i, 6, QTableWidgetItem("")) # Visual status
                self.table.setItem(i, 7, QTableWidgetItem(row.get('raw_message', '')))
                
        except Exception as e:
            QMessageBox.critical(self, "Viga", f"CSV lugemine ebaõnnestus: {e}")

    def _apply_fluke(self):
        field = self.field_combo.currentText()
        val = self.val_edit.text().strip()
        if not val: return

        count = 0
        for i in range(self.table.rowCount()):
            if self.table.item(i, 0).checkState() == Qt.CheckState.Checked:
                # Add to rules
                self.fluke_rules.append({'row_index': i, 'field': field, 'new_value': val})
                # Update table visual
                self.table.item(i, 6).setText(f"{field} → {val}")
                self.table.item(i, 6).setForeground(QColor("#f44336"))
                count += 1
        
        if count > 0:
            self.val_edit.clear()
            # Uncheck all
            for i in range(self.table.rowCount()):
                self.table.item(i, 0).setCheckState(Qt.CheckState.Unchecked)

    def _add_custom_row(self):
        # Simplified: just adds a blank CMD row for now
        # Ideally would pop another small dialog for field entry
        from datetime import datetime
        new_row = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'direction': 'RX',
            'msg_type': '1', # EVENT by default
            'event_code': '30', # STUCK
            '_pos': len(self.csv_rows)
        }
        self.new_rows.append(new_row)
        
        row_idx = self.table.rowCount()
        self.table.insertRow(row_idx)
        self.table.setItem(row_idx, 0, QTableWidgetItem("-"))
        self.table.setItem(row_idx, 1, QTableWidgetItem("*NEW*"))
        self.table.setItem(row_idx, 2, QTableWidgetItem("EVENT"))
        self.table.setItem(row_idx, 5, QTableWidgetItem("30"))
        self.table.setItem(row_idx, 6, QTableWidgetItem("Added manually"))
        self.table.item(row_idx, 6).setForeground(QColor("#4caf50"))

    def get_results(self):
        return self.fluke_rules, self.new_rows

# ─── CSV Embed Dialog ─────────────────────────────────────────────────────────
class CsvEmbedDialog(QDialog):
    """Dialog for embedding CSV data into source code."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("CSV → Kood Embedder")
        self.setMinimumWidth(500)
        
        self.fluke_rules = []
        self.new_rows = []
        
        self._build_ui()

    def _on_fluke_toggled(self, checked):
        self.fluke_btn.setEnabled(checked)
        self.dual_version_check.setEnabled(checked)

    def _open_fluke_config(self):
        csv_path = self.file_edit.text()
        if not csv_path or not os.path.exists(csv_path):
            QMessageBox.warning(self, "Viga", "Vali esmalt kehtiv CSV fail!")
            return
            
        dlg = CsvFlukeDialog(csv_path, self.fluke_rules, self.new_rows, self)
        if dlg.exec():
            self.fluke_rules, self.new_rows = dlg.get_results()
            rules_cnt = len(self.fluke_rules)
            rows_cnt = len(self.new_rows)
            self.fluke_status.setText(f"Olek: {rules_cnt} muutust, {rows_cnt} uut rida")
            self.fluke_status.setStyleSheet("color: #4caf50; font-weight: bold;")

    def _build_ui(self):
        layout = QVBoxLayout()

        # File selection
        file_layout = QHBoxLayout()
        file_layout.addWidget(QLabel("CSV fail:"))
        self.file_edit = QLineEdit()
        file_layout.addWidget(self.file_edit)
        browse_btn = QPushButton("Sirvi...")
        browse_btn.clicked.connect(self._browse_file)
        file_layout.addWidget(browse_btn)
        layout.addLayout(file_layout)

        # Encryption selection
        enc_layout = QHBoxLayout()
        enc_layout.addWidget(QLabel("Krüpteering:"))
        self.enc_combo = QComboBox()
        self.enc_combo.addItems(["XOR (soovitatud)", "Base64"])
        enc_layout.addWidget(self.enc_combo)
        enc_layout.addStretch()
        layout.addLayout(enc_layout)

        # Fluking Section
        fluke_group = QGroupBox("Andmete rikkumine (Fluking)")
        fluke_layout = QVBoxLayout()
        self.fluke_check = QCheckBox("Luba andmete rikkumine")
        self.fluke_check.toggled.connect(self._on_fluke_toggled)
        fluke_layout.addWidget(self.fluke_check)
        
        self.fluke_btn = QPushButton("Konfigureeri rikkumist...")
        self.fluke_btn.setEnabled(False)
        self.fluke_btn.clicked.connect(self._open_fluke_config)
        fluke_layout.addWidget(self.fluke_btn)
        
        self.fluke_status = QLabel("Olek: Pole konfigureeritud")
        self.fluke_status.setStyleSheet("font-size: 10px; color: #666;")
        fluke_layout.addWidget(self.fluke_status)
        
        self.dual_version_check = QCheckBox("Genereeri mõlemad (puhas + rikutud)")
        self.dual_version_check.setEnabled(False)
        fluke_layout.addWidget(self.dual_version_check)
        
        fluke_group.setLayout(fluke_layout)
        layout.addWidget(fluke_group)

        # PyInstaller option
        self.compile_check = QCheckBox("Genereeri .exe (PyInstaller)")
        self.compile_check.setChecked(False)
        layout.addWidget(self.compile_check)

        # Output directory
        out_layout = QHBoxLayout()
        out_layout.addWidget(QLabel("Väljundkaust:"))
        self.out_edit = QLineEdit()
        out_layout.addWidget(self.out_edit)
        out_btn = QPushButton("Sirvi...")
        out_btn.clicked.connect(self._browse_output)
        out_layout.addWidget(out_btn)
        layout.addLayout(out_layout)

        # Info label
        self.info_label = QLabel("")
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(self.info_label)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        generate_btn = QPushButton("Genereeri")
        generate_btn.setStyleSheet("background: #9c27b0; color: white; font-weight: bold; padding: 8px;")
        generate_btn.clicked.connect(self._generate)
        btn_layout.addWidget(generate_btn)
        cancel_btn = QPushButton("Tühista")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

        # Set default output dir
        self.out_edit.setText(os.path.join(os.path.dirname(__file__), 'csv_embed', 'output'))

    def _browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Vali CSV fail", "", "CSV files (*.csv);;All files (*)"
        )
        if file_path:
            self.file_edit.setText(file_path)
            self._update_info()

    def _browse_output(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Vali väljundkaust", self.out_edit.text()
        )
        if folder:
            self.out_edit.setText(folder)

    def _update_info(self):
        csv_path = self.file_edit.text()
        if csv_path and os.path.exists(csv_path):
            from csv_embed.encoder import get_csv_info
            info = get_csv_info(csv_path)
            self.info_label.setText(
                f"Fail: {info['filename']} | Suurus: {info['size_bytes']} B | "
                f"Read: {info['lines']} | Veerge: {info['columns']}"
            )
        else:
            self.info_label.setText("")

    def _generate(self):
        csv_path = self.file_edit.text()
        out_dir = self.out_edit.text()
        
        if not csv_path or not os.path.exists(csv_path):
            QMessageBox.warning(self, "Viga", "Vali esmalt kehtiv CSV fail!")
            return
            
        os.makedirs(out_dir, exist_ok=True)
        
        try:
            from csv_embed.csv_embedder import embed_csv, EmbedConfig
            
            enc = 'xor' if "XOR" in self.enc_combo.currentText() else 'base64'
            config = EmbedConfig(
                encryption=enc,
                output_dir=out_dir,
                compile_exe=self.compile_check.isChecked()
            )
            
            generated_files = []
            
            # 1. Generate Clean Version if requested
            if not self.fluke_check.isChecked() or self.dual_version_check.isChecked():
                res = embed_csv(csv_path, config=config)
                if isinstance(res, tuple):
                    for f in res: generated_files.append(f)
                else:
                    generated_files.append(res)
            
            # 2. Generate Fluked Version if requested
            if self.fluke_check.isChecked():
                fluked_content = CsvFluker.fluke_data(csv_path, self.fluke_rules, self.new_rows)
                
                # Suffix for fluked version
                base_name = os.path.splitext(os.path.basename(csv_path))[0]
                fluked_out_path = os.path.join(out_dir, f"{base_name}_rikutud.py")
                
                # Update config for possible EXE naming
                if config.compile_exe:
                    config.exe_name = f"{base_name}_rikutud"
                
                res = embed_csv(csv_path, output_path=fluked_out_path, config=config, raw_csv_content=fluked_content)
                if isinstance(res, tuple):
                    for f in res: generated_files.append(f)
                else:
                    generated_files.append(res)
                    
            msg = "Fail(id) genereeritud edukalt:\n\n" + "\n".join([os.path.basename(f) for f in generated_files])
            QMessageBox.information(self, "Edu", msg)
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "Viga", f"Genereerimine ebaõnnestus:\n{e}")


import subprocess
from commands.manager import CommandManager
from commands.translator import RXToTXTranslator

# ─── Digital Twin Options Panel ───────────────────────────────────────────────
class DtOptionsPanel(QGroupBox):
    """Panel for Digital Twin options including CSV recording."""

    def __init__(self, recorder: CsvRecorder, log_table=None, parent=None):
        super().__init__("Digital Twin Valikud", parent)
        self.recorder = recorder
        self.log_table = log_table
        self.parent_window = parent
        self.replay_worker = None
        self.dt_process = None
        layout = QVBoxLayout()
        
        # --- Local DT Server Control ---
        server_group = QGroupBox("DT Server (Andmete generaator)")
        server_layout = QVBoxLayout()
        
        self.server_status = QLabel("Server: Running")
        self.server_status.setStyleSheet("font-weight: bold; color: #666;")
        server_layout.addWidget(self.server_status)
        
        self.server_btn = QPushButton("Käivita DT Server")
        self.server_btn.setStyleSheet("background: #607d8b; color: white; font-weight: bold;")
        self.server_btn.clicked.connect(self._toggle_dt_server)
        server_layout.addWidget(self.server_btn)
        
        server_group.setLayout(server_layout)
        layout.addWidget(server_group)

        # Recording status
        self.status_label = QLabel("Salvestamine: Peatatud")
        self.status_label.setStyleSheet("font-weight: bold; color: #f44336;")
        layout.addWidget(self.status_label)
        
        # Record/Stop buttons
        btn_layout = QHBoxLayout()
        self.record_btn = QPushButton("Alusta salvestamist")
        self.record_btn.setStyleSheet("background: #4caf50; font-weight: bold;")
        self.record_btn.clicked.connect(self._toggle_recording)
        btn_layout.addWidget(self.record_btn)
        
        self.count_label = QLabel("Sõnumeid: 0")
        self.count_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        btn_layout.addWidget(self.count_label)
        layout.addLayout(btn_layout)
        
        # CSV folder button
        folder_layout = QHBoxLayout()
        self.folder_btn = QPushButton("📁 Ava CSV kaust")
        self.folder_btn.clicked.connect(self._open_csv_folder)
        folder_layout.addWidget(self.folder_btn)

        self.change_folder_btn = QPushButton("📂 Muuda kausta")
        self.change_folder_btn.clicked.connect(self._change_csv_folder)
        folder_layout.addWidget(self.change_folder_btn)
        layout.addLayout(folder_layout)

        # Replay button
        self.replay_btn = QPushButton("▶️ Esita CSV fail")
        self.replay_btn.setStyleSheet("background: #2196f3; color: white; font-weight: bold;")
        self.replay_btn.clicked.connect(self._start_replay)
        layout.addWidget(self.replay_btn)

        # Replay status
        self.replay_status = QLabel("")
        self.replay_status.setStyleSheet("font-size: 10px; color: #666;")
        layout.addWidget(self.replay_status)

        # CSV Embed button
        self.embed_btn = QPushButton("Embed CSV → Kood")
        self.embed_btn.setStyleSheet("background: #9c27b0; color: white; font-weight: bold;")
        self.embed_btn.clicked.connect(self._open_csv_embed)
        layout.addWidget(self.embed_btn)

        # Current folder path
        self.folder_label = QLabel(f"Kaust: {self.recorder.output_dir}")
        self.folder_label.setWordWrap(True)
        self.folder_label.setStyleSheet("font-size: 10px; color: #666;")
        layout.addWidget(self.folder_label)

        self.setLayout(layout)
    
    def _toggle_dt_server(self):
        """Start or stop the local DT server process."""
        if self.dt_process and self.dt_process.poll() is None:
            # Server is running, stop it
            self.dt_process.terminate()
            self.dt_process.wait(2000)
            self.dt_process = None
            self.server_status.setText("Server: Seisab")
            self.server_status.setStyleSheet("font-weight: bold; color: #666;")
            self.server_btn.setText("🚀 Käivita DT Server")
            self.server_btn.setStyleSheet("background: #607d8b; color: white; font-weight: bold;")
        else:
            # Start the server
            try:
                # Find dt_server.py in the same directory
                script_path = os.path.join(os.path.dirname(__file__), "dt_server.py")
                if not os.path.exists(script_path):
                    raise FileNotFoundError(f"Ei leidnud faili: {script_path}")
                
                # Start process - using python executable
                self.dt_process = subprocess.Popen(
                    [sys.executable, script_path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                # Update UI
                self.server_status.setText("Server: Töötab (9000)")
                self.server_status.setStyleSheet("font-weight: bold; color: #4caf50;")
                self.server_btn.setText("🛑 Peata DT Server")
                self.server_btn.setStyleSheet("background: #f44336; color: white; font-weight: bold;")
                
            except Exception as e:
                QMessageBox.critical(self, "Viga", f"Serveri käivitamine ebaõnnestus:\n{e}")

    def __del__(self):
        # Ensure process is killed on close
        if self.dt_process and self.dt_process.poll() is None:
            self.dt_process.terminate()

    def _toggle_recording(self):
        if self.recorder.is_recording:
            # Stop recording
            file_path = self.recorder.stop_recording()
            self.status_label.setText("Salvestamine: Peatatud")
            self.status_label.setStyleSheet("font-weight: bold; color: #f44336;")
            self.record_btn.setText("Alusta salvestamist")
            self.record_btn.setStyleSheet("background: #4caf50; font-weight: bold;")
            
            msg = f"Salvestamine peatatud.\nSalvestatud {self.recorder.message_count} sõnumit.\nFail: {file_path}"
            QMessageBox.information(self, "Salvestamine peatatud", msg)
        else:
            # Start recording
            file_path = self.recorder.start_recording()
            self.status_label.setText("Salvestamine: Käimas...")
            self.status_label.setStyleSheet("font-weight: bold; color: #4caf50;")
            self.record_btn.setText("⏹ Peata salvestamine")
            self.record_btn.setStyleSheet("background: #f44336; font-weight: bold;")
            
            msg = f"Salvestamine alustatud.\nFail: {file_path}"
            QMessageBox.information(self, "Salvestamine alustatud", msg)
    
    def _open_csv_folder(self):
        """Open the CSV folder in file explorer."""
        QDesktopServices.openUrl(QUrl.fromLocalFile(self.recorder.output_dir))
    
    def _change_csv_folder(self):
        """Change the CSV output folder."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Vali CSV salvestuskaust",
            self.recorder.output_dir
        )
        if folder:
            self.recorder.set_output_dir(folder)
            self.folder_label.setText(f"Kaust: {folder}")
    
    def _start_replay(self):
        """Start replaying a CSV file."""
        if self.replay_worker and self.replay_worker.isRunning():
            QMessageBox.warning(self, "Esitamine käib", "CSV faili esitamine on juba käimas.")
            return
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Vali robot-andmete fail",
            self.recorder.output_dir,
            "Robot Data (*.csv *.py *.exe);;CSV files (*.csv);;Embedded Python (*.py);;Executables (*.exe);;All files (*)"
        )
        if not file_path:
            return

        # Decode data
        try:
            csv_content = CsvDecoder.decode(file_path)
        except Exception as e:
            QMessageBox.critical(self, "Dekodeerimise viga", f"Faili ei saanud lugeda:\n{e}")
            return
        
        # Ask about timing
        reply = QMessageBox.question(
            self,
            "Ajastus",
            "Kas esitada algse ajastusega (soovitatud)?\n\nJah - algne ajastus\nEi - kohene esitus",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes
        )
        use_timing = (reply == QMessageBox.StandardButton.Yes)
        
        # Ask about sending via connection
        send_via_conn = None
        direction_filter = None
        behavioral_replay = False

        if self.parent_window and hasattr(self.parent_window, 'worker') and self.parent_window.worker:
            reply = QMessageBox.question(
                self,
                "Edastamine",
                "Kas edastada käsud ühenduse kaudu?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                send_via_conn = self.parent_window.worker
                
                # Behavioral replay question
                beh_reply = QMessageBox.question(
                    self,
                    "Käitumuslik esitus (RX->TX)",
                    "Kas soovid kasutada käitumuslikku esitust?\n\nSee tõlgib robotilt tulnud RX teated (nt pööre) uuteks mootori käskudeks (TX), võimaldades robotil liikumist kopeerida.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No
                )
                behavioral_replay = (beh_reply == QMessageBox.StandardButton.Yes)

                if not behavioral_replay:
                    # Ask which direction to replay if NOT using translation
                    dir_reply = QMessageBox.question(
                        self,
                        "Suund",
                        "Milliseid sõnumeid esitada?\n\nJah - ainult TX (algsetest käsudest)\nEi - kõik sõnumid",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                        QMessageBox.StandardButton.No
                    )
                    if dir_reply == QMessageBox.StandardButton.Yes:
                        direction_filter = 'TX'
        
        # Setup worker
        self.replay_worker = CsvReplayWorker(
            file_path, 
            use_timing, 
            send_via_connection=send_via_conn,
            direction_filter=direction_filter,
            behavioral_replay=behavioral_replay,
            csv_content=csv_content
        )
        self.replay_worker.line_replayed.connect(self._on_replay_line)
        self.replay_worker.replay_started.connect(self._on_replay_started)
        self.replay_worker.replay_finished.connect(self._on_replay_finished)
        self.replay_worker.progress_update.connect(self._on_replay_progress)
        self.replay_worker.start()
    
    def _on_replay_line(self, raw_msg: str, direction: str, timestamp: str):
        """Handle replayed line - add to log and parse."""
        # Update log table
        msg = parse_message(raw_msg)
        if msg:
            msg["direction"] = direction
            if self.log_table:
                self.log_table.add_row(msg)
            
            # Auto map switch on replayed STATUS
            if msg.get("msg_type") == 0 and self.parent_window:
                app_id = msg.get("app_id")
                if app_id != self.parent_window._last_app_id:
                    self.parent_window.svg_viewer.set_map_by_app_id(app_id)
                    self.parent_window._last_app_id = app_id

            # Also update SVG viewer for visualization
            if self.parent_window and hasattr(self.parent_window, 'svg_viewer'):
                self.parent_window.svg_viewer.process_msg(msg, timestamp)
        else:
            if self.log_table:
                self.log_table.add_error_row(raw_msg)
    
    def _on_replay_started(self):
        """Replay started."""
        if self.parent_window:
            self.parent_window.replay_active = True
        self.replay_btn.setEnabled(False)
        self.replay_btn.setText("⏹ Esitamine...")
        self.replay_status.setText("Esitamine käib...")
    
    def _on_replay_finished(self):
        """Replay finished."""
        if self.parent_window:
            self.parent_window.replay_active = False
        self.replay_btn.setEnabled(True)
        self.replay_btn.setText("▶️ Esita CSV fail")
        self.replay_status.setText("Esitamine lõpetatud")
        QMessageBox.information(self, "Esitamine lõpetatud", "CSV faili esitamine on lõpetatud.")
    
    def _on_replay_progress(self, current: int, total: int):
        """Update replay progress."""
        self.replay_status.setText(f"Esitamine: {current}/{total}")

    def _open_csv_embed(self):
        """Open CSV embed dialog."""
        dialog = CsvEmbedDialog(self)
        dialog.exec()

    def update_count(self, count: int):
        """Update the message count display."""
        self.count_label.setText(f"Sõnumeid: {count}")


# ─── Main window ──────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Robot Monitor GUI v0.4")
        self.resize(1100, 700)

        self.worker = None
        self.recorder = CsvRecorder()
        self.replay_active = False
        self._last_app_id = None

        self._build_ui()
        self._apply_style()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)

        # ── Left column ───────────────────────────────────────────────────────
        left = QVBoxLayout()

        self.conn_panel = ConnectionPanel()
        self.conn_panel.connect_btn.clicked.connect(self._toggle_connection)
        left.addWidget(self.conn_panel)

        self.cmd_panel = CommandPanel()
        self.cmd_panel.send_command.connect(self._send_command)
        self.cmd_panel.set_enabled(False)
        left.addWidget(self.cmd_panel)

        left.addStretch()
        left_widget = QWidget()
        left_widget.setLayout(left)
        left_widget.setFixedWidth(320)
        main_layout.addWidget(left_widget)

        # ── Right column ──────────────────────────────────────────────────────
        right = QVBoxLayout()

        self.status_panel = StatusPanel()
        right.addWidget(self.status_panel)

        self.svg_viewer = SvgViewer()
        right.addWidget(self.svg_viewer)

        self.log_table = LogTable(parent=self)
        right.addWidget(self.log_table)

        right_widget = QWidget()
        right_widget.setLayout(right)
        main_layout.addWidget(right_widget)

        # Add dt_options to left column after log_table is created
        self.dt_options = DtOptionsPanel(self.recorder, self.log_table, self)
        left.addWidget(self.dt_options)

        # ── Status bar ────────────────────────────────────────────────────────
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ühendamata")

        # Dark Mode Toggle Button in Status Bar
        self.dark_mode_btn = QPushButton("🌙 Tume režiim")
        self.dark_mode_btn.setCheckable(True)
        self.dark_mode_btn.setFixedWidth(120)
        self.dark_mode_btn.toggled.connect(self._toggle_dark_mode)
        self.status_bar.addPermanentWidget(self.dark_mode_btn)

    def _toggle_dark_mode(self, checked):
        if checked:
            self.dark_mode_btn.setText("☀️ Hele režiim")
            self._apply_dark_style()
        else:
            self.dark_mode_btn.setText("🌙 Tume režiim")
            self._apply_style()

    def _apply_dark_style(self):
        self.setStyleSheet("""
            QMainWindow { 
                background: #1e1e1e; 
                color: #ffffff;
            }
            QWidget {
                color: #ffffff;
                background: #1e1e1e;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #555;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
                color: #ffffff;
                background: #2d2d2d;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
                background: transparent;
            }
            QComboBox {
                color: #ffffff;
                background: #3c3c3c;
                border: 1px solid #555;
            }
            QComboBox QAbstractItemView {
                background: #3c3c3c;
                color: #ffffff;
            }
            QPushButton {
                background: #0d47a1;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 4px 10px;
            }
            QPushButton:hover  { background: #1565c0; }
            QPushButton:disabled { background: #424242; color: #757575; }
            QTableWidget { 
                font-size: 11px;
                color: #ffffff;
                background: #252526;
                gridline-color: #444;
                border: 1px solid #444;
            }
            QHeaderView::section {
                color: #ffffff;
                background: #333333;
                border: 1px solid #444;
            }
            QStatusBar {
                color: #ffffff;
                background: #1e1e1e;
                border-top: 1px solid #333;
            }
            QStatusBar::item {
                border: none;
            }
            QStatusBar QLabel {
                background: transparent;
            }
            QRadioButton {
                color: #ffffff;
            }
            QSpinBox {
                color: #ffffff;
                background: #3c3c3c;
                border: 1px solid #555;
            }
            QLineEdit {
                color: #ffffff;
                background: #3c3c3c;
                border: 1px solid #555;
                padding: 4px;
            }
            QCheckBox {
                color: #ffffff;
            }
            QFrame[frameShape="4"], QFrame[frameShape="5"] { /* Separator lines */
                color: #555;
                background: #555;
            }
        """)
        # Update LogTable colors for dark mode if they were hardcoded
        if hasattr(self, 'log_table'):
            self.log_table.TYPE_COLOURS = {
                "STATUS":   QColor("#1b3321"),
                "EVENT":    QColor("#3e2723"),
                "FAULT":    QColor("#3e1919"),
                "RESPONSE": QColor("#0d47a1"),
                "COMMAND":  QColor("#311b92"),
            }
            self.log_table.DIRECTION_COLOURS = {
                "RX": QColor("#1b3321"),
                "TX": QColor("#0d47a1"),
            }
            # Re-apply to existing rows
            for i in range(self.log_table.table.rowCount()):
                typ_item = self.log_table.table.item(i, 2)
                dir_item = self.log_table.table.item(i, 1)
                if typ_item and dir_item:
                    typ = typ_item.text()
                    direction = dir_item.text()
                    bg_color = self.log_table.TYPE_COLOURS.get(typ, QColor("#252526"))
                    dir_tint = self.log_table.DIRECTION_COLOURS.get(direction, QColor("#252526"))
                    for col in range(5):
                        item = self.log_table.table.item(i, col)
                        if item:
                            item.setBackground(bg_color)
                            item.setForeground(QColor("#ffffff"))
                    self.log_table.table.item(i, 1).setBackground(dir_tint)

    def closeEvent(self, event):
        """Clean up resources on exit."""
        if hasattr(self, 'dt_options'):
            # Stop DT server if running
            if self.dt_options.dt_process and self.dt_options.dt_process.poll() is None:
                self.dt_options.dt_process.terminate()
        if self.worker:
            self.worker.stop()
            self.worker.wait(1000)
        event.accept()

    def _apply_style(self):
        self.setStyleSheet("""
            QMainWindow { 
                background: #f5f5f5; 
                color: #000000;
            }
            QWidget {
                color: #000000;
                background: #f5f5f5;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #ccc;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
                color: #000000;
                background: #ffffff;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                color: #000000;
            }
            QLabel {
                color: #000000;
            }
            QComboBox {
                color: #000000;
                background: #ffffff;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border: none;
            }
            QPushButton {
                background: #1976d2;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 4px 10px;
            }
            QPushButton:hover  { background: #1565c0; }
            QPushButton:disabled { background: #bdbdbd; }
            QTableWidget { 
                font-size: 11px;
                color: #000000;
                background: #ffffff;
            }
            QHeaderView::section {
                color: #000000;
                background: #e0e0e0;
            }
            QStatusBar {
                color: #000000;
                background: #f5f5f5;
            }
            QRadioButton {
                color: #000000;
            }
            QSpinBox {
                color: #000000;
                background: #ffffff;
            }
            QLineEdit {
                color: #000000;
                background: #ffffff;
                border: 1px solid #ccc;
                padding: 4px;
            }
            QCheckBox {
                color: #000000;
            }
            QFrame[frameShape="4"], QFrame[frameShape="5"] { /* Separator lines */
                color: #ddd;
                background: #ddd;
            }
        """)
        # Update LogTable colors back to light mode
        if hasattr(self, 'log_table'):
            self.log_table.TYPE_COLOURS = {
                "STATUS":   QColor("#e8f5e9"),
                "EVENT":    QColor("#fff3e0"),
                "FAULT":    QColor("#ffebee"),
                "RESPONSE": QColor("#e3f2fd"),
                "COMMAND":  QColor("#f3e5f5"),
            }
            self.log_table.DIRECTION_COLOURS = {
                "RX": QColor("#c8e6c9"),
                "TX": QColor("#bbdefb"),
            }
            # Re-apply to existing rows
            for i in range(self.log_table.table.rowCount()):
                typ_item = self.log_table.table.item(i, 2)
                dir_item = self.log_table.table.item(i, 1)
                if typ_item and dir_item:
                    typ = typ_item.text()
                    direction = dir_item.text()
                    bg_color = self.log_table.TYPE_COLOURS.get(typ, QColor("#ffffff"))
                    dir_tint = self.log_table.DIRECTION_COLOURS.get(direction, QColor("#ffffff"))
                    for col in range(5):
                        item = self.log_table.table.item(i, col)
                        if item:
                            item.setBackground(bg_color)
                            item.setForeground(QColor("#000000"))
                    self.log_table.table.item(i, 1).setBackground(dir_tint)

    def _toggle_connection(self):
        if self.worker and self.worker.isRunning():
            self._disconnect()
        else:
            self._connect()

    def _connect(self):
        mode = self.conn_panel.get_mode()

        if mode == "serial":
            port = self.conn_panel.get_serial_port()
            baud = self.conn_panel.get_baud()
            self.worker = ConnectionWorker(mode="serial", port=port, baud=baud)
        else:
            host     = self.conn_panel.get_host()
            tcp_port = self.conn_panel.get_tcp_port()
            self.worker = ConnectionWorker(mode="tcp", host=host, tcp_port=tcp_port)

        self.worker.message_received.connect(self._on_message)
        self.worker.connection_lost.connect(self._on_connection_lost)
        self.worker.connected.connect(self._on_connected)
        self.worker.start()

        self.conn_panel.connect_btn.setText("Katkesta")
        self.status_bar.showMessage("Ühendub...")

    def _disconnect(self):
        if self.worker:
            self.worker.stop()
            self.worker.wait(2000)
            self.worker = None
        self.conn_panel.connect_btn.setText("Ühenda")
        self.cmd_panel.set_enabled(False)
        self.status_bar.showMessage("Ühendus katkestatud")

    def _on_connected(self):
        self.cmd_panel.set_enabled(True)
        mode = self.conn_panel.get_mode()
        if mode == "tcp":
            label = f"Ühendatud TCP {self.conn_panel.get_host()}:{self.conn_panel.get_tcp_port()}"
        else:
            label = f"Ühendatud serial {self.conn_panel.get_serial_port()}"
        self.status_bar.showMessage(label)

    def _on_connection_lost(self, error: str):
        self.conn_panel.connect_btn.setText("Ühenda")
        self.cmd_panel.set_enabled(False)
        self.status_bar.showMessage(f"Ühendus kadunud: {error}")

    def _on_message(self, raw: str, timestamp: str = None):
        if not raw or not raw.strip():
            return
        msg = parse_message(raw)
        if msg is None:
            self.log_table.add_error_row(raw)
            return

        # Add direction info for incoming messages
        msg["direction"] = "RX"
        self.log_table.add_row(msg)

        # Update tracking ONLY if NOT replaying a CSV AND live tracking is enabled
        if not self.replay_active and self.svg_viewer.live_btn.isChecked():
            self.svg_viewer.process_msg(msg, timestamp)
            # Update angle display in status panel
            _, _, angle = self.svg_viewer.tracker.get_pos()
            self.status_panel.update_angle(angle)

        # Record message if recording is active
        if self.recorder.is_recording:
            self.recorder.record_message(msg)
            self.dt_options.update_count(self.recorder.message_count)

        if msg["msg_type"] == 0:   # STATUS beacon
            app_id = msg.get("app_id")
            if app_id != self._last_app_id:
                self.svg_viewer.set_map_by_app_id(app_id)
                self._last_app_id = app_id
                
            self.status_panel.update_from_status(msg)
            self.cmd_panel.update_robot_info(msg["robot_id"], msg["mode"])

    def _send_command(self, raw: str):
        if self.worker and self.worker.isRunning():
            self.worker.send(raw)
            # Show sent command in log too
            print(f"DEBUG: Sending TX command: {raw}")
            self.log_table.add_row({
                "robot_id":  "TX",
                "type_name": "COMMAND",
                "raw":       raw,
                "direction": "TX",
            })
        else:
            # Not connected - still show in log but mark as not sent
            print(f"DEBUG: Not connected, command not sent: {raw}")
            self.log_table.add_row({
                "robot_id":  "TX",
                "type_name": "COMMAND",
                "raw":       raw,
                "direction": "TX",
            })


# ─── Entry point ─────────────────────────────────────────────────────────────
def main():
    global win
    app = QApplication(sys.argv)
    app.setApplicationName("Robot Monitor GUI")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
