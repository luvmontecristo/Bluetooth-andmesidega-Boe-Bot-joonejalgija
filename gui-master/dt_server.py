#!/usr/bin/env python3
"""
dt_server.py - Digital Twin Server Mode

TCP server that emulates a robot:
- Sends status beacons periodically
- Listens for commands and responds per protocol
- Supports behaviours: normal, fault_on_cmd, mirror, random_values
- Logs all traffic to CLI (and optionally CSV)

Optional arguments via CLI:
    python dt_server.py                          # default: localhost:9000, normal behaviour
    python dt_server.py --port 9001              # custom port
    python dt_server.py --behaviour fault_on_cmd # inject faults
    python dt_server.py --behaviour mirror       # echo commands back
    python dt_server.py --behaviour random       # send random/invalid values
    python dt_server.py --speed 2.0              # status beacon 2x faster
    python dt_server.py --replay session.csv     # replay from CSV + respond to commands

(ver. 010426)
    
"""

import socket
import threading
import time
import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'development_tools'))

from protocol_parser import ProtocolParser
from protocol_enums import (
    MsgType, Mode, FaultCode, CoreCmd
)
from message import (
    StatusMessage, CommandMessage, ResponseMessage, FaultMessage
)
from data_generator.dataGen import RobotDataGenerator


# ─── Colour helpers (Windows-safe) ───────────────────────────────────────────
def _c(code, text):
    """Wrap text in ANSI colour if supported."""
    try:
        if sys.stdout.isatty():
            return f"\033[{code}m{text}\033[0m"
    except Exception:
        pass
    return text

RX_COL  = lambda t: _c("92", t)   # green  - received from client (GUI)
TX_COL  = lambda t: _c("94", t)   # blue   - sent to client
ERR_COL = lambda t: _c("91", t)   # red    - errors / faults
INF_COL = lambda t: _c("93", t)   # yellow - server info


# ─── Behaviour definitions ────────────────────────────────────────────────────
BEHAVIOURS = {
    "normal":        "Respond correctly to all commands",
    "fault_on_cmd":  "Reply with FAULT to every command",
    "mirror":        "Echo the raw command back as-is",
    "random":        "Respond with random / out-of-range values",
    "silent":        "Send status beacons but never respond to commands",
}


# ─── Robot state (shared across threads) ─────────────────────────────────────
class RobotState:
    def __init__(self, robot_id: int):
        self.robot_id   = robot_id
        self.mode       = Mode.MODE_IDLE
        self.sequence   = 0
        self.battery_mv = 11800
        self.app_id     = 255
        self.lock       = threading.Lock()

    def next_sequence(self):
        with self.lock:
            seq = self.sequence
            self.sequence = (self.sequence + 1) % 256
            return seq

    def set_mode(self, mode: Mode):
        with self.lock:
            self.mode = mode


# ─── Response builder ─────────────────────────────────────────────────────────
class ResponseBuilder:
    """Builds raw protocol response strings for each command."""

    def __init__(self, state: RobotState):
        self.state = state

    def build(self, cmd_msg: CommandMessage, behaviour: str) -> str:
        rid = self.state.robot_id

        if behaviour == "fault_on_cmd":
            return f"{rid};{MsgType.FAULT.value};{FaultCode.FAULT_UNKNOWN_CMD.value}"

        if behaviour == "mirror":
            return str(cmd_msg)   # echo raw back

        if behaviour == "silent":
            return None           # no response

        if behaviour == "random":
            import random
            # Return a response with random payload - may be invalid
            rand_val = random.randint(0, 99999)
            return f"{rid};{MsgType.RESPONSE.value};{cmd_msg.command_code};{rand_val};{rand_val}"

        # ── normal behaviour ──────────────────────────────────────────────────
        code = cmd_msg.command_code

        if code == CoreCmd.CMD_PING.value:
            return f"{rid};{MsgType.RESPONSE.value};{code};PONG"

        if code == CoreCmd.CMD_MEMORY_DUMP.value:
            s = self.state
            return (f"{rid};{MsgType.RESPONSE.value};{code};"
                    f"{s.sequence};{s.battery_mv};{s.app_id};"
                    f"{s.mode.value};1")

        if code == CoreCmd.CMD_SET_LED.value:
            return f"{rid};{MsgType.RESPONSE.value};{code};OK"

        if code == CoreCmd.CMD_SET_MODE.value:
            # v1 contains the target mode
            try:
                new_mode = Mode(cmd_msg.v1)
                self.state.set_mode(new_mode)
                return f"{rid};{MsgType.RESPONSE.value};{code};OK"
            except Exception:
                return f"{rid};{MsgType.FAULT.value};{FaultCode.FAULT_BAD_ARG.value}"

        if code == CoreCmd.CMD_SET_MOTOR.value:
            if self.state.mode not in (Mode.MODE_TEST, Mode.MODE_IDLE):
                return f"{rid};{MsgType.FAULT.value};{FaultCode.FAULT_NOT_ALLOWED.value}"
            return f"{rid};{MsgType.RESPONSE.value};{code};OK"

        if code in (CoreCmd.CMD_SET_MAX_SPEED.value, 
                   CoreCmd.CMD_SET_QTI_THRES.value,
                   CoreCmd.CMD_CHANGE_ROBOT_ID.value):
            # Just acknowledge for now
            return f"{rid};{MsgType.RESPONSE.value};{code};OK"

        # Unknown command
        return f"{rid};{MsgType.FAULT.value};{FaultCode.FAULT_UNKNOWN_CMD.value}"


# ─── Client handler (one per connected GUI) ───────────────────────────────────
class ClientHandler(threading.Thread):
    def __init__(self, conn, addr, state: RobotState, behaviour: str, log_fn):
        super().__init__(daemon=True)
        self.conn      = conn
        self.addr      = addr
        self.state     = state
        self.behaviour = behaviour
        self.log       = log_fn
        self.builder   = ResponseBuilder(state)
        self.running   = True

    def run(self):
        self.log(INF_COL(f"[SERVER] Client connected: {self.addr}"))
        buf = ""
        try:
            while self.running:
                data = self.conn.recv(256)
                if not data:
                    break
                buf += data.decode("utf-8", errors="replace")

                # Process all complete lines
                while "\n" in buf:
                    line, buf = buf.split("\n", 1)
                    line = line.strip()
                    if line:
                        self._handle_line(line)
        except Exception as e:
            self.log(ERR_COL(f"[SERVER] Client error: {e}"))
        finally:
            self.conn.close()
            self.log(INF_COL(f"[SERVER] Client disconnected: {self.addr}"))

    def _handle_line(self, raw: str):
        self.log(RX_COL(f"[RX] {raw}"))

        try:
            msg = ProtocolParser.parse(raw)
        except Exception as e:
            self.log(ERR_COL(f"[RX] Parse error: {e}"))
            fault = f"{self.state.robot_id};{MsgType.FAULT.value};{FaultCode.FAULT_UNKNOWN_CMD.value}"
            self._send(fault)
            return

        if not isinstance(msg, CommandMessage):
            self.log(ERR_COL(f"[RX] Expected command, got {type(msg).__name__}"))
            return

        response = self.builder.build(msg, self.behaviour)
        if response:
            self._send(response)

    def _send(self, raw: str):
        self.log(TX_COL(f"[TX] {raw}"))
        try:
            self.conn.sendall((raw + "\n").encode("utf-8"))
        except Exception as e:
            self.log(ERR_COL(f"[TX] Send error: {e}"))
            self.running = False


# ─── Beacon thread (sends status periodically to all clients) ─────────────────
class BeaconThread(threading.Thread):
    def __init__(self, clients: list, state: RobotState, interval: float, log_fn):
        super().__init__(daemon=True)
        self.clients  = clients
        self.state    = state
        self.interval = interval
        self.log      = log_fn
        self.gen      = RobotDataGenerator(robot_id=state.robot_id)

    def run(self):
        while True:
            time.sleep(self.interval)
            beacon = self.gen.generate_status()
            self.log(TX_COL(f"[BEACON] {beacon}"))
            dead = []
            for client in list(self.clients):
                try:
                    client.conn.sendall((beacon + "\n").encode("utf-8"))
                except Exception:
                    dead.append(client)
            for d in dead:
                self.clients.remove(d)


# ─── Main server ──────────────────────────────────────────────────────────────
class DTServer:
    def __init__(self, host: str, port: int, robot_id: int,
                 behaviour: str, beacon_interval: float):
        self.host             = host
        self.port             = port
        self.state            = RobotState(robot_id)
        self.behaviour        = behaviour
        self.beacon_interval  = beacon_interval
        self.clients          = []

    def log(self, msg: str):
        ts = time.strftime("%H:%M:%S")
        print(f"{ts}  {msg}", flush=True)

    def run(self):
        self._print_banner()

        beacon = BeaconThread(self.clients, self.state,
                              self.beacon_interval, self.log)
        beacon.start()

        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((self.host, self.port))
        srv.listen(5)

        self.log(INF_COL(f"[SERVER] Listening on {self.host}:{self.port}"))
        self.log(INF_COL(f"[SERVER] Behaviour : {self.behaviour}  |  "
                         f"Beacon interval: {self.beacon_interval:.1f}s"))
        self.log(INF_COL("[SERVER] Waiting for GUI connection... (Ctrl+C to stop)\n"))

        try:
            while True:
                conn, addr = srv.accept()
                handler = ClientHandler(conn, addr, self.state,
                                        self.behaviour, self.log)
                self.clients.append(handler)
                handler.start()
        except KeyboardInterrupt:
            self.log(INF_COL("\n[SERVER] Shutting down."))
        finally:
            srv.close()

    def _print_banner(self):
        print(INF_COL("""
+=======================================================+
|        DIGITAL TWIN - Robot Protocol Server           |
|                                                       |
|  Connect your GUI to: tcp://localhost:<port>          |
|  Protocol: robot_id;msg_type;payload...               |
+=======================================================+
"""))
        print(f"  Available behaviours:")
        for name, desc in BEHAVIOURS.items():
            marker = " <-- active" if name == self.behaviour else ""
            print(f"    {name:<16} {desc}{marker}")
        print()


# ─── Entry point ─────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Digital Twin Server - emulates a robot over TCP"
    )
    parser.add_argument("--host",      default="localhost",  help="Bind address (default: localhost)")
    parser.add_argument("--port",      type=int, default=9000, help="TCP port (default: 9000)")
    parser.add_argument("--robot-id",  type=int, default=1,  help="Robot ID (default: 1)")
    parser.add_argument("--behaviour", choices=list(BEHAVIOURS.keys()),
                        default="normal", help="Emulation behaviour (default: normal)")
    parser.add_argument("--speed",     type=float, default=1.0,
                        help="Beacon speed multiplier (default: 1.0 = 1s interval)")

    args = parser.parse_args()
    beacon_interval = 1.0 / args.speed

    server = DTServer(
        host             = args.host,
        port             = args.port,
        robot_id         = args.robot_id,
        behaviour        = args.behaviour,
        beacon_interval  = beacon_interval,
    )
    server.run()


if __name__ == "__main__":
    main()
