import argparse
import datetime as dt
import pathlib
import queue
import sys
import threading
import time
from typing import Optional

import serial
from serial import SerialException


# ===================== SERIAL HEALTH =====================

RECONNECT_SETTLE_S = 0.75


# ===================== MESSAGE TYPES =====================

MSG_STATUS = 0
MSG_EVENT = 1
MSG_COMMAND = 2
MSG_RESPONSE = 3
MSG_FAULT = 4


# ===================== CORE COMMANDS =====================

CMD_PING = 1
CMD_MEMORY_DUMP = 2
CMD_SET_LED = 3
CMD_SET_TELEMETRY = 4
CMD_SET_DEBUG_MODE = 5
CMD_SET_MODE = 6
CMD_SET_MOTOR = 7
CMD_REDUCE_MAX_SPEED = 8
CMD_SET_QTI_THRESHOLD = 9
CMD_CHANGE_ROBOT_ID = 10
CMD_RESET_EEPROM = 11


# ===================== APP COMMANDS =====================

CMD_GET_STATUS = 100
CMD_START_APP = 101
CMD_STOP_APP = 102
CMD_SHOW_QTI_VALUES = 103
CMD_SET_MAP_NUMBER = 104


# ===================== TEST COMMANDS =====================

CMD_TEST_DATA_DUMP = 200
CMD_TEST_READ_QTI = 201
CMD_TEST_READ_BAT = 202
CMD_TEST_ULTRA_SWEEP = 203
CMD_TEST_ULTRASOUND = 204
CMD_TEST_RFID_VALUE = 205
CMD_TEST_MOTOR_VALUE = 206


# ===================== MODES =====================

MODE_RUN = 0
MODE_TEST = 1
MODE_IDLE = 2
MODE_ERROR = 3


# ===================== LED IDS =====================

LED_ID_LEFT = 1
LED_ID_RIGHT = 2
LED_ID_BOTH = 3


# ===================== LED MODES =====================

LED_MODE_WRITE = 0
LED_MODE_TOGGLE = 1


# ===================== LED STATES =====================

LED_STATE_OFF = 0
LED_STATE_ON = 1


# ===================== EVENT NAMES =====================

EVENT_NAMES = {
    1: "EV_MODE_CHANGED",
    2: "EV_BUTTON_PRESSED",
    3: "EV_FAULT",
    4: "EV_WARNING",
    5: "EV_RESET",
    20: "EV_LINE_DETECTED",
    21: "EV_LINE_LOST",
    22: "EV_OFF_TRACK",
    23: "EV_INTERSECTION",
    24: "EV_MOTOR_THRESHOLD",
    25: "EV_WALL_DETECTED",
    26: "EV_DEAD_END",
    27: "EV_TURN_LEFT",
    28: "EV_TURN_RIGHT",
    29: "EV_PATH_COMPLETE",
    30: "EV_STUCK",
    31: "EV_DESTINATION",
    32: "EV_MOVING_FORWARD",
    33: "EV_SCAN_STARTED",
    100: "EV_APP_SENS",
    101: "EV_APP_LAP",
    102: "EV_APP_START",
    103: "EV_APP_FINISH",
    104: "EV_APP_BOOST",
    105: "EV_APP_TURN_AHEAD",
    106: "EV_APP_BAT",
    107: "EV_APP_MOTOR",
}


# ===================== FAULT NAMES =====================

FAULT_NAMES = {
    1: "FAULT_UNKNOWN_CMD",
    2: "FAULT_BAD_ARG",
    3: "FAULT_BAD_MODE",
    4: "FAULT_INTERNAL",
    5: "FAULT_NOT_ALLOWED",
}


# ===================== MODE NAMES =====================

MODE_NAMES = {
    0: "RUN",
    1: "TEST",
    2: "IDLE",
    3: "ERROR",
}


# Return the current timestamp with millisecond precision.
def ts_now() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


# Convert a string value to an integer safely and return a default value if conversion fails.
def safe_int(value: str, default: int = -1) -> int:
    try:
        return int(value)
    except Exception:
        return default


# Convert a numeric command code to a human-readable command name.
def cmd_name(cmd: int) -> str:
    mapping = {
        CMD_PING: "PING",
        CMD_MEMORY_DUMP: "MEMORY_DUMP",
        CMD_SET_LED: "SET_LED",
        CMD_SET_TELEMETRY: "SET_TELEMETRY",
        CMD_SET_DEBUG_MODE: "SET_DEBUG_MODE",
        CMD_SET_MODE: "SET_MODE",
        CMD_SET_MOTOR: "SET_MOTOR",
        CMD_REDUCE_MAX_SPEED: "REDUCE_MAX_SPEED",
        CMD_SET_QTI_THRESHOLD: "SET_QTI_THRESHOLD",
        CMD_CHANGE_ROBOT_ID: "CHANGE_ROBOT_ID",
        CMD_RESET_EEPROM: "RESET_EEPROM",
        CMD_GET_STATUS: "GET_STATUS",
        CMD_START_APP: "START_APP",
        CMD_STOP_APP: "STOP_APP",
        CMD_SHOW_QTI_VALUES: "SHOW_QTI_VALUES",
        CMD_SET_MAP_NUMBER: "SET_MAP_NUMBER",
        CMD_TEST_DATA_DUMP: "TEST_DATA_DUMP",
        CMD_TEST_READ_QTI: "TEST_READ_QTI",
        CMD_TEST_READ_BAT: "TEST_READ_BAT",
        CMD_TEST_ULTRA_SWEEP: "TEST_ULTRA_SWEEP",
        CMD_TEST_ULTRASOUND: "TEST_ULTRASOUND",
        CMD_TEST_RFID_VALUE: "TEST_RFID_VALUE",
        CMD_TEST_MOTOR_VALUE: "TEST_MOTOR_VALUE",
    }
    return mapping.get(cmd, f"CMD_{cmd}")


# Parse one semicolon-separated protocol line into generic message fields.
def parse_line(line: str) -> dict:
    parts = line.split(";")
    return {
        "raw": line,
        "parts": parts,
        "robot_id": safe_int(parts[0]) if len(parts) > 0 else -1,
        "msg_type": safe_int(parts[1]) if len(parts) > 1 else -1,
        "code": safe_int(parts[2]) if len(parts) > 2 else -1,
        "args": parts[3:] if len(parts) > 3 else [],
    }


# Validate that an integer value is inside the allowed inclusive range.
def validate_range(value: int, minimum: int, maximum: int, field_name: str) -> int:
    if not (minimum <= value <= maximum):
        raise ValueError(f"{field_name} must be in range {minimum}..{maximum}")
    return value


# Convert a textual robot mode name to its numeric protocol value.
def mode_value(name: str) -> int:
    mapping = {
        "run": MODE_RUN,
        "test": MODE_TEST,
        "idle": MODE_IDLE,
        "error": MODE_ERROR,
    }
    return mapping[name]


# Convert a textual LED target name to its numeric LED identifier.
def led_value(name: str) -> int:
    mapping = {
        "left": LED_ID_LEFT,
        "right": LED_ID_RIGHT,
        "both": LED_ID_BOTH,
    }
    return mapping[name]


# Convert a textual LED control mode name to its numeric protocol value.
def led_mode_value(name: str) -> int:
    mapping = {
        "write": LED_MODE_WRITE,
        "toggle": LED_MODE_TOGGLE,
    }
    return mapping[name]


# Convert a textual test subcommand name to its numeric command code.
def test_value(name: str) -> int:
    mapping = {
        "dump": CMD_TEST_DATA_DUMP,
        "qti": CMD_TEST_READ_QTI,
        "bat": CMD_TEST_READ_BAT,
        "sweep": CMD_TEST_ULTRA_SWEEP,
        "ultra": CMD_TEST_ULTRASOUND,
        "rfid": CMD_TEST_RFID_VALUE,
        "motor": CMD_TEST_MOTOR_VALUE,
    }
    return mapping[name]


# Implement the interactive serial command-line interface for the robot protocol.
class RobotCli:
    # Initialize the CLI state, open the serial port and start the background reader thread.
    def __init__(self, port: str, baud: int, robot_id: Optional[int], log_path: str):
        self.port = port
        self.baud = baud
        self.robot_id = robot_id
        self.log_path = pathlib.Path(log_path)

        self.print_lock = threading.Lock()
        self.serial_lock = threading.Lock()

        self.rx_queue: "queue.Queue[str]" = queue.Queue()
        self.rx_partial = bytearray()

        self.stop_flag = False
        self.reader_error_count = 0
        self.suppress_rx_print = False
        self.last_rx_at: Optional[float] = None

        self.logging_enabled = True
        self.log_error_shown = False

        self.ser: Optional[serial.Serial] = None
        self._open_serial()

        self.reader_thread = threading.Thread(
            target=self._reader_loop,
            name="robot-reader",
            daemon=True,
        )
        self.reader_thread.start()

    # Open the serial connection using the configured port and baud rate.
    def _open_serial(self) -> None:
        self.ser = serial.Serial(
            port=self.port,
            baudrate=self.baud,
            timeout=0,
            write_timeout=1.0,
        )

        try:
            self.ser.reset_input_buffer()
            self.ser.reset_output_buffer()
        except Exception:
            pass

    # Close the serial connection while the serial lock is already held.
    def _close_serial_locked(self) -> None:
        try:
            if self.ser is not None and self.ser.is_open:
                self.ser.close()
        except Exception:
            pass
        self.ser = None

    # Stop the reader thread and close the serial connection.
    def close(self) -> None:
        self.stop_flag = True
        time.sleep(0.15)

        with self.serial_lock:
            self._close_serial_locked()

    # Print text to the console using a lock to avoid mixed output from multiple threads.
    def safe_print(self, text: str, end: str = "\n") -> None:
        with self.print_lock:
            print(text, end=end, flush=True)

    # Return the currently selected robot ID as text.
    def current_id_text(self) -> str:
        return "?" if self.robot_id is None else str(self.robot_id)

    # Check whether the active robot ID has been configured before sending commands.
    def ensure_robot_id_set(self) -> bool:
        if self.robot_id is None:
            self.safe_print(
                "CLI robot_id is not set. Use: useid <1..254> or start with --robot-id <id>"
            )
            return False
        return True

    # Return a short status string about the current serial connection.
    def port_info_text(self) -> str:
        with self.serial_lock:
            is_open = self.ser is not None and self.ser.is_open

        if self.last_rx_at is None:
            last_rx = "never"
        else:
            last_rx = f"{time.monotonic() - self.last_rx_at:.1f}s ago"

        return (
            f"port={self.port} baud={self.baud} "
            f"open={'yes' if is_open else 'no'} "
            f"reader_errors={self.reader_error_count} "
            f"last_rx={last_rx} "
            f"rx_print={'off' if self.suppress_rx_print else 'on'}"
        )

    # Write one transmitted or received protocol message to the CSV log file.
    def log_line(self, direction: str, line: str) -> None:
        if not self.logging_enabled:
            return

        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)

            file_exists = self.log_path.exists()
            parts = line.split(";")

            while len(parts) < 12:
                parts.append("")

            escaped_raw = line.replace('"', '""')

            with self.log_path.open("a", encoding="utf-8", newline="") as f:
                if not file_exists:
                    f.write(
                        "timestamp,direction,raw_message,robot_id,msg_type,code,"
                        "arg1,arg2,arg3,arg4,arg5,arg6,arg7,arg8,arg9\n"
                    )

                f.write(
                    f'"{ts_now()}","{direction}","{escaped_raw}",'
                    f'"{parts[0]}","{parts[1]}","{parts[2]}","{parts[3]}",'
                    f'"{parts[4]}","{parts[5]}","{parts[6]}","{parts[7]}",'
                    f'"{parts[8]}","{parts[9]}","{parts[10]}","{parts[11]}"\n'
                )

        except PermissionError as exc:
            self.logging_enabled = False
            if not self.log_error_shown:
                self.log_error_shown = True
                self.safe_print(
                    f"{ts_now()}  --  Logging was disabled: file cannot be written ({exc})."
                )

        except OSError as exc:
            self.logging_enabled = False
            if not self.log_error_shown:
                self.log_error_shown = True
                self.safe_print(
                    f"{ts_now()}  --  Logging was disabled: file error ({exc})."
                )

    # Reopen the serial port and clear old receive-buffer data after a connection problem.
    def reconnect(self, reason: str = "manual") -> bool:
        self.safe_print(f"{ts_now()}  --  Reconnect started ({reason}).")

        with self.serial_lock:
            self._close_serial_locked()
            time.sleep(0.25)

            try:
                self._open_serial()
                self.last_rx_at = None
                self.rx_partial.clear()
                time.sleep(RECONNECT_SETTLE_S)
            except Exception as exc:
                self.safe_print(f"{ts_now()}  --  Reconnect failed: {exc}")
                return False

        cleared = 0
        while True:
            try:
                self.rx_queue.get_nowait()
                cleared += 1
            except queue.Empty:
                break

        self.safe_print(f"{ts_now()}  --  Reconnect successful. Cleared RX lines: {cleared}")
        return True

    # Continuously read incoming serial data in the background and process complete protocol lines.
    def _reader_loop(self) -> None:
        while not self.stop_flag:
            try:
                with self.serial_lock:
                    if self.ser is None or not self.ser.is_open:
                        ser = None
                    else:
                        ser = self.ser

                if ser is None:
                    time.sleep(0.1)
                    continue

                available = ser.in_waiting
                if available <= 0:
                    time.sleep(0.02)
                    continue

                raw = ser.read(available)

                if not raw:
                    time.sleep(0.02)
                    continue

                with self.serial_lock:
                    if ser is not self.ser:
                        continue

                self.rx_partial.extend(raw)

                while b"\n" in self.rx_partial:
                    raw_line, _, rest = self.rx_partial.partition(b"\n")
                    self.rx_partial = bytearray(rest)

                    line = raw_line.decode("utf-8", errors="replace").strip()
                    if line:
                        self.last_rx_at = time.monotonic()

                        parsed = parse_line(line)
                        self.log_line("RX", line)

                        if parsed["msg_type"] in (MSG_RESPONSE, MSG_FAULT):
                            self.rx_queue.put(line)

                        if not self.suppress_rx_print:
                            try:
                                pretty_print_rx(line, printer=self.safe_print)
                            except Exception as exc:
                                self.safe_print(f"{ts_now()}  --  RX formatting error: {exc}")

            except (SerialException, OSError) as exc:
                self.reader_error_count += 1
                if not self.stop_flag:
                    self.safe_print(f"{ts_now()}  --  Reader error: {exc}")
                    self.reconnect(reason="reader_error")
                time.sleep(0.2)

            except Exception as exc:
                self.reader_error_count += 1
                if not self.stop_flag:
                    self.safe_print(f"{ts_now()}  --  Reader unexpected error: {exc}")
                    time.sleep(0.2)

    # Build and send one semicolon-separated protocol message through the serial port.
    def send_fields(self, *fields: object) -> None:
        line = ";".join(str(field) for field in fields)
        payload = (line + "\r\n").encode("utf-8")

        last_exc: Optional[Exception] = None

        for attempt in range(2):
            try:
                with self.serial_lock:
                    if self.ser is None or not self.ser.is_open:
                        raise SerialException("Serial port is not open")

                    self.ser.write(payload)
                    self.ser.flush()

                self.log_line("TX", line)
                self.safe_print(f"{ts_now()}  TX  {line}")
                return

            except (SerialException, OSError, TimeoutError) as exc:
                last_exc = exc
                self.safe_print(f"{ts_now()}  --  Send error: {exc}")

                if attempt == 0:
                    ok = self.reconnect(reason="write_error")
                    if not ok:
                        break
                    continue
                break

            except Exception as exc:
                last_exc = exc
                self.safe_print(f"{ts_now()}  --  Unexpected send error: {exc}")

                if attempt == 0:
                    ok = self.reconnect(reason="write_unexpected_error")
                    if not ok:
                        break
                    continue
                break

        raise last_exc if last_exc is not None else RuntimeError("Sending failed")

    # Send one command message to the currently selected robot.
    def send_command(self, cmd: int, *args: object) -> bool:
        if not self.ensure_robot_id_set():
            return False

        self.send_fields(self.robot_id, MSG_COMMAND, cmd, *args)
        return True

    # Wait for a response or fault message that belongs to the previously sent command.
    def wait_for_command_result(
        self,
        expected_cmd: int,
        timeout: float = 2.0,
    ) -> Optional[str]:
        deadline = time.time() + timeout
        expected_robot_id = self.robot_id

        while time.time() < deadline:
            remaining = max(0.01, deadline - time.time())

            try:
                line = self.rx_queue.get(timeout=remaining)
            except queue.Empty:
                return None

            parsed = parse_line(line)
            robot_id = parsed["robot_id"]
            msg_type = parsed["msg_type"]
            code = parsed["code"]

            if expected_robot_id is not None and robot_id != expected_robot_id:
                continue

            if msg_type == MSG_FAULT:
                return line

            if msg_type == MSG_RESPONSE and code == expected_cmd:
                return line

        return None

    # Handle a missing command response by reopening the serial connection.
    def handle_command_timeout(self, expected_cmd: int) -> None:
        if self.last_rx_at is None:
            last_rx_text = "no RX lines have been received yet"
        else:
            last_rx_text = f"last RX was {time.monotonic() - self.last_rx_at:.1f}s ago"

        self.safe_print(
            f"{ts_now()}  --  No response for {cmd_name(expected_cmd)}; "
            f"trying reconnect ({last_rx_text})."
        )
        self.reconnect(reason="command_timeout")

    # Collect multiple response lines belonging to the TEST_DATA_DUMP command.
    def collect_test_dump_responses(
        self,
        overall_timeout: float = 2.5,
        idle_gap: float = 0.35,
    ) -> list[str]:
        received: list[str] = []
        deadline = time.time() + overall_timeout
        last_rx_time = None
        expected_robot_id = self.robot_id

        while time.time() < deadline:
            remaining = max(0.01, deadline - time.time())

            try:
                line = self.rx_queue.get(timeout=min(remaining, idle_gap))
            except queue.Empty:
                if received and last_rx_time is not None and (time.time() - last_rx_time) >= idle_gap:
                    break
                continue

            parsed = parse_line(line)
            robot_id = parsed["robot_id"]
            msg_type = parsed["msg_type"]

            if expected_robot_id is not None and robot_id != expected_robot_id:
                continue

            if msg_type == MSG_FAULT:
                received.append(line)
                break

            if msg_type == MSG_RESPONSE:
                received.append(line)
                last_rx_time = time.time()

        return received

    # Set the active robot ID locally inside the CLI.
    def set_robot_id(self, new_id: int) -> None:
        self.robot_id = new_id
        self.safe_print(f"{ts_now()}  --  CLI robot_id set to {new_id}")

    # Update the active CLI robot ID after the robot confirms an ID change.
    def update_robot_id(self, new_id: int) -> None:
        self.robot_id = new_id
        self.safe_print(f"{ts_now()}  --  CLI robot_id updated to {new_id}")


# Print one received protocol line in a more readable human-facing format.
def pretty_print_rx(line: str, printer=print) -> None:
    parts = line.split(";")
    now = ts_now()

    if len(parts) < 3:
        printer(f"\n{now}  RX  {line}")
        return

    robot_id = parts[0]
    msg_type = safe_int(parts[1])
    code = safe_int(parts[2])
    args = parts[3:]

    if msg_type == MSG_STATUS:
        if len(parts) >= 7:
            seq = parts[2]
            bat_mv = parts[3]
            app_or_map = parts[4]
            mode = safe_int(parts[5], -1)
            proto = parts[6]
            mode_name = MODE_NAMES.get(mode, str(mode))

            printer(
                f"\n{now}  RX  STATUS  robot={robot_id} seq={seq} "
                f"bat_mv={bat_mv} app_or_map={app_or_map} mode={mode_name} proto={proto}"
            )
        else:
            printer(f"\n{now}  RX  {line}")
        return

    if msg_type == MSG_EVENT:
        event_name = EVENT_NAMES.get(code, f"EVENT_{code}")

        if code == 1 and len(args) >= 1:
            mode_name = MODE_NAMES.get(safe_int(args[0], -1), args[0])
            printer(
                f"\n{now}  RX  EVENT   robot={robot_id} code={event_name} new_mode={mode_name}"
            )
            return

        if code == 100 and len(args) >= 6:
            printer(
                f"\n{now}  RX  EVENT   robot={robot_id} code={event_name} "
                f"l={args[0]} m={args[1]} r={args[2]} "
                f"tl={args[3]} tm={args[4]} tr={args[5]}"
            )
            return

        if code == 101 and len(args) >= 1:
            printer(
                f"\n{now}  RX  EVENT   robot={robot_id} code={event_name} lap={args[0]}"
            )
            return

        if code == 105 and len(args) >= 1:
            printer(
                f"\n{now}  RX  EVENT   robot={robot_id} code={event_name} marker={args[0]}"
            )
            return

        if code == 106 and len(args) >= 1:
            printer(
                f"\n{now}  RX  EVENT   robot={robot_id} code={event_name} bat_mv={args[0]}"
            )
            return

        if code == 107 and len(args) >= 2:
            printer(
                f"\n{now}  RX  EVENT   robot={robot_id} code={event_name} "
                f"left_us={args[0]} right_us={args[1]}"
            )
            return

        printer(f"\n{now}  RX  EVENT   robot={robot_id} code={event_name} args={args}")
        return

    if msg_type == MSG_RESPONSE:
        response_name = cmd_name(code)

        if code == CMD_MEMORY_DUMP and len(args) >= 4:
            printer(
                f"\n{now}  RX  RESP    robot={robot_id} cmd={response_name} "
                f"robot_id={args[0]} map={args[1]} "
                f"max_speed={args[2]} qti_threshold={args[3]}"
            )
            return

        if code == CMD_SET_MODE and len(args) >= 1:
            mode_name = MODE_NAMES.get(safe_int(args[0]), args[0])
            printer(
                f"\n{now}  RX  RESP    robot={robot_id} cmd={response_name} new_mode={mode_name}"
            )
            return

        if code == CMD_SET_LED and len(args) >= 3:
            printer(
                f"\n{now}  RX  RESP    robot={robot_id} cmd={response_name} "
                f"led_id={args[0]} led_mode={args[1]} applied_state={args[2]}"
            )
            return

        if code == CMD_SET_MOTOR and len(args) >= 3:
            printer(
                f"\n{now}  RX  RESP    robot={robot_id} cmd={response_name} "
                f"left_us={args[0]} right_us={args[1]} time_ms={args[2]}"
            )
            return

        if code == CMD_TEST_READ_QTI and len(args) >= 3:
            printer(
                f"\n{now}  RX  RESP    robot={robot_id} cmd={response_name} "
                f"left={args[0]} mid={args[1]} right={args[2]}"
            )
            return

        if code == CMD_TEST_READ_BAT and len(args) >= 1:
            printer(
                f"\n{now}  RX  RESP    robot={robot_id} cmd={response_name} bat_mv={args[0]}"
            )
            return

        if code == CMD_TEST_ULTRA_SWEEP and len(args) >= 3:
            printer(
                f"\n{now}  RX  RESP    robot={robot_id} cmd={response_name} "
                f"p1={args[0]} p2={args[1]} p3={args[2]}"
            )
            return

        if code == CMD_TEST_ULTRASOUND and len(args) >= 1:
            printer(
                f"\n{now}  RX  RESP    robot={robot_id} cmd={response_name} value={args[0]}"
            )
            return

        if code == CMD_TEST_RFID_VALUE and len(args) >= 1:
            printer(
                f"\n{now}  RX  RESP    robot={robot_id} cmd={response_name} value={args[0]}"
            )
            return

        if code == CMD_TEST_MOTOR_VALUE and len(args) >= 2:
            printer(
                f"\n{now}  RX  RESP    robot={robot_id} cmd={response_name} "
                f"left_us={args[0]} right_us={args[1]}"
            )
            return

        printer(
            f"\n{now}  RX  RESP    robot={robot_id} cmd={response_name} args={args}"
        )
        return

    if msg_type == MSG_FAULT:
        fault_name = FAULT_NAMES.get(code, f"FAULT_{code}")
        printer(f"\n{now}  RX  FAULT   robot={robot_id} code={fault_name}")
        return

    printer(f"\n{now}  RX  {line}")


# Build the command-line argument parser for CLI startup options.
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--port",
        required=True,
        help="Serial/Bluetooth port, for example COM6 or /dev/rfcomm0",
    )
    parser.add_argument(
        "--baud",
        type=int,
        default=9600,
        help="Baud rate",
    )
    parser.add_argument(
        "--robot-id",
        type=int,
        default=None,
        help="Initial CLI robot ID",
    )
    parser.add_argument(
        "--log",
        default="robot_cli.csv",
        help="CSV log file name",
    )
    return parser


# Print the list of available interactive CLI commands.
def print_help() -> None:
    print(
        "\nCommands:\n"
        "  help\n"
        "  whoami\n"
        "  portinfo\n"
        "  reconnect\n"
        "  pause\n"
        "  resume\n"
        "  ping\n"
        "  status\n"
        "  start\n"
        "  stop\n"
        "  mode run|test|idle|error\n"
        "  useid <1..254>\n"
        "  map <1..255>\n"
        "  telemetry 0|1\n"
        "  debug 0|1\n"
        "  showqti 0|1\n"
        "  led <left|right|both> <write|toggle> <0|1>\n"
        "  motor <left_us> <right_us> <time_ms>\n"
        "  maxspeed <0..200>\n"
        "  qti <1..3000>\n"
        "  robotid <1..255>\n"
        "  reseteeprom\n"
        "  memory\n"
        "  test qti|bat|dump|ultra|sweep|rfid|motor\n"
        "  raw <cmd> [arg1] [arg2] [arg3] [arg4]\n"
        "  quit\n"
    )


# Start the CLI program, process user input and handle clean shutdown.
def main() -> int:
    args = build_parser().parse_args()
    cli = RobotCli(args.port, args.baud, args.robot_id, args.log)

    print_help()
    print(f"{ts_now()}  --  Active CLI robot_id: {cli.current_id_text()}")
    print(f"{ts_now()}  --  {cli.port_info_text()}")

    try:
        while True:
            try:
                line = input("> ").strip()
            except EOFError:
                break
            except KeyboardInterrupt:
                print()
                break

            if not line:
                continue

            parts = line.split()
            cmd = parts[0].lower()

            if cmd in ("quit", "exit"):
                break

            if cmd == "help":
                print_help()
                continue

            if cmd == "whoami":
                print(f"{ts_now()}  --  Active CLI robot_id: {cli.current_id_text()}")
                continue

            if cmd == "portinfo":
                print(f"{ts_now()}  --  {cli.port_info_text()}")
                continue

            if cmd == "reconnect":
                cli.reconnect(reason="manual_command")
                continue

            if cmd == "pause":
                cli.suppress_rx_print = True
                print(f"{ts_now()}  --  RX printing paused.")
                continue

            if cmd == "resume":
                cli.suppress_rx_print = False
                print(f"{ts_now()}  --  RX printing resumed.")
                continue

            try:
                sent_cmd = None
                pending_robot_id = None
                ping_started_at = None

                if cmd == "useid" and len(parts) == 2:
                    new_id = validate_range(int(parts[1]), 1, 254, "Robot ID")
                    cli.set_robot_id(new_id)
                    continue

                if cmd == "ping":
                    sent_cmd = CMD_PING
                    ping_started_at = time.perf_counter()
                    if not cli.send_command(CMD_PING):
                        continue

                elif cmd == "status":
                    sent_cmd = CMD_GET_STATUS
                    if not cli.send_command(CMD_GET_STATUS):
                        continue

                elif cmd == "start":
                    sent_cmd = CMD_START_APP
                    if not cli.send_command(CMD_START_APP):
                        continue

                elif cmd == "stop":
                    sent_cmd = CMD_STOP_APP
                    if not cli.send_command(CMD_STOP_APP):
                        continue

                elif cmd == "mode" and len(parts) == 2:
                    sent_cmd = CMD_SET_MODE
                    if not cli.send_command(CMD_SET_MODE, mode_value(parts[1].lower())):
                        continue

                elif cmd == "map" and len(parts) == 2:
                    map_number = validate_range(int(parts[1]), 1, 255, "Map number")
                    sent_cmd = CMD_SET_MAP_NUMBER
                    if not cli.send_command(CMD_SET_MAP_NUMBER, map_number):
                        continue

                elif cmd == "telemetry" and len(parts) == 2:
                    value = validate_range(int(parts[1]), 0, 1, "Telemetry")
                    sent_cmd = CMD_SET_TELEMETRY
                    if not cli.send_command(CMD_SET_TELEMETRY, value):
                        continue

                elif cmd == "debug" and len(parts) == 2:
                    value = validate_range(int(parts[1]), 0, 1, "Debug")
                    sent_cmd = CMD_SET_DEBUG_MODE
                    if not cli.send_command(CMD_SET_DEBUG_MODE, value):
                        continue

                elif cmd == "showqti" and len(parts) == 2:
                    value = validate_range(int(parts[1]), 0, 1, "ShowQTI")
                    sent_cmd = CMD_SHOW_QTI_VALUES
                    if not cli.send_command(CMD_SHOW_QTI_VALUES, value):
                        continue

                elif cmd == "led" and len(parts) == 4:
                    target = led_value(parts[1].lower())
                    mode = led_mode_value(parts[2].lower())
                    state = validate_range(int(parts[3]), 0, 1, "LED state")

                    sent_cmd = CMD_SET_LED
                    if not cli.send_command(CMD_SET_LED, target, mode, state):
                        continue

                elif cmd == "motor" and len(parts) == 4:
                    left_us = int(parts[1])
                    right_us = int(parts[2])
                    time_ms = validate_range(int(parts[3]), 0, 65535, "Time_ms")

                    sent_cmd = CMD_SET_MOTOR
                    if not cli.send_command(CMD_SET_MOTOR, left_us, right_us, time_ms):
                        continue

                elif cmd == "maxspeed" and len(parts) == 2:
                    value = validate_range(int(parts[1]), 0, 200, "Max speed")
                    sent_cmd = CMD_REDUCE_MAX_SPEED
                    if not cli.send_command(CMD_REDUCE_MAX_SPEED, value):
                        continue

                elif cmd == "qti" and len(parts) == 2:
                    value = validate_range(int(parts[1]), 1, 3000, "QTI threshold")
                    sent_cmd = CMD_SET_QTI_THRESHOLD
                    if not cli.send_command(CMD_SET_QTI_THRESHOLD, value):
                        continue

                elif cmd == "robotid" and len(parts) == 2:
                    pending_robot_id = validate_range(int(parts[1]), 1, 255, "Robot ID")
                    sent_cmd = CMD_CHANGE_ROBOT_ID
                    if not cli.send_command(CMD_CHANGE_ROBOT_ID, pending_robot_id):
                        continue

                elif cmd == "reseteeprom" and len(parts) == 1:
                    sent_cmd = CMD_RESET_EEPROM
                    if not cli.send_command(CMD_RESET_EEPROM):
                        continue

                elif cmd == "memory":
                    sent_cmd = CMD_MEMORY_DUMP
                    if not cli.send_command(CMD_MEMORY_DUMP):
                        continue

                elif cmd == "test" and len(parts) == 2:
                    sent_cmd = test_value(parts[1].lower())
                    if not cli.send_command(sent_cmd):
                        continue

                elif cmd == "raw" and len(parts) >= 2:
                    if not cli.ensure_robot_id_set():
                        continue

                    raw_args = [int(value) for value in parts[1:]]
                    sent_cmd = raw_args[0]
                    cli.send_command(*raw_args)

                else:
                    print("Unknown command. Type 'help'.")
                    continue

                if sent_cmd == CMD_TEST_DATA_DUMP:
                    replies = cli.collect_test_dump_responses(overall_timeout=2.5, idle_gap=0.35)

                    if not replies:
                        print(f"{ts_now()}  --  No TEST_DATA_DUMP replies were received within the timeout.")
                    else:
                        print(f"{ts_now()}  --  TEST_DATA_DUMP replies received: {len(replies)}")

                    continue

                if sent_cmd == CMD_GET_STATUS:
                    continue

                reply = cli.wait_for_command_result(expected_cmd=sent_cmd, timeout=2.0)

                if reply is None:
                    print(f"{ts_now()}  --  No response was received within the timeout.")
                    cli.handle_command_timeout(sent_cmd)
                    continue

                if sent_cmd == CMD_PING and ping_started_at is not None:
                    rtt_ms = (time.perf_counter() - ping_started_at) * 1000.0
                    print(f"{ts_now()}  --  Ping response received in {rtt_ms:.2f} ms")

                reply_parts = reply.split(";")

                if len(reply_parts) >= 3:
                    msg_type = safe_int(reply_parts[1])
                    code = safe_int(reply_parts[2])

                    if msg_type == MSG_FAULT:
                        continue

                    if (
                        sent_cmd == CMD_CHANGE_ROBOT_ID
                        and pending_robot_id is not None
                        and msg_type == MSG_RESPONSE
                        and code == CMD_CHANGE_ROBOT_ID
                        and len(reply_parts) >= 4
                    ):
                        new_id = safe_int(reply_parts[3], -1)

                        if new_id == pending_robot_id and 1 <= new_id <= 255:
                            cli.update_robot_id(new_id)

            except KeyError:
                print("Invalid command argument.")

            except ValueError as exc:
                print(f"Invalid number in command: {exc}")

            except KeyboardInterrupt:
                print()
                break

            except Exception as exc:
                print(f"Error: {exc}")

    finally:
        cli.close()

    return 0


# Run the CLI entry point when this file is executed directly.
if __name__ == "__main__":
    sys.exit(main())