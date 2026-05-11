import math
import time
import json
import os

class RobotTracker:
    def __init__(self):
        # Existing freeform tracking settings
        self.DEFAULT_SPEED = 50.0
        self.DEFAULT_TURN = 90.0
        self.DEFAULT_ANGLE = 0.0

        self.speed_px_per_s = self.DEFAULT_SPEED
        self.turn_deg = self.DEFAULT_TURN
        self.saved_angle = self.DEFAULT_ANGLE

        # Freeform tracker state
        self.x = 400.0
        self.y = 300.0
        self.angle = self.DEFAULT_ANGLE
        self.last_ts = None
        self.is_moving = False
        self.path = []
        self._pending_mode = None
        self.last_scan_angle = 90.0 # Default scan angle
        self.is_scanning = False
        self.wall_distance = None

        self.preserve_speed = False
        self.preserve_turn = False
        self.preserve_angle = False

        # Maze segment tracker state
        self.segment_mode = False

        self.maze_name = None
        self.start_segment = None
        self.start_heading = "E"
        self.segments = {}
        self.node_exits = {}

        self.current_segment = None
        self.heading = "E"
        self.last_intersection = None
        self.pending_intersection = False
        self.finished = False
        self.completed = False
        self.visited_segments = set()
        self.error_segment = None

        # Marker-based line follower state (Joonejälgimine).
        # This mirrors Maze state: segments are named, one section is active,
        # and the GUI colours active/visited segments from get_segment_states().
        self.marker_mode = False
        self.marker_track_name = None
        self.marker_start = (400.0, 300.0)
        self.marker_positions = []
        self.marker_finish = None
        self.marker_sections = []
        self.current_marker_number = 0
        self.current_section_index = 0
        self.current_segments = set()

        self.reset()

    def load_maze_from_json(self, maze_name: str):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(base_dir, "maze_segments", f"maze-{maze_name}.json")

        if not os.path.exists(json_path):
            self.maze_name = None
            self.start_segment = None
            self.start_heading = "E"
            self.segments = {}
            self.node_exits = {}
            self.current_segment = None
            self.visited_segments = set()
            return False

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.maze_name = maze_name
        self.start_segment = data["start_segment"]
        self.start_heading = data.get("start_heading", "E")

        self.segments = {
            name: (tuple(points[0]), tuple(points[1]))
            for name, points in data["segments"].items()
        }

        self.node_exits = {
            tuple(int(v.strip()) for v in key.split(",")): value
            for key, value in data["node_exits"].items()
        }

        self.reset()
        return True

    def load_marker_track_from_json(self, track_name: str):
        """Load a Maze-like ordered marker track from maze_segments/track-*.json."""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(base_dir, "maze_segments", f"track-{track_name}.json")

        if not os.path.exists(json_path):
            self.marker_track_name = None
            self.marker_start = (400.0, 300.0)
            self.marker_positions = []
            self.marker_finish = None
            self.marker_sections = []
            self.current_marker_number = 0
            self.current_section_index = 0
            self.current_segments = set()
            self.segments = {}
            self.start_segment = None
            self.current_segment = None
            self.visited_segments = set()
            return False

        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.marker_track_name = track_name
        self.marker_start = tuple(data.get("start", [400.0, 300.0]))
        self.marker_positions = [tuple(p) for p in data.get("markers", [])]
        self.marker_finish = tuple(data.get("finish", self.marker_start))
        self.start_heading = data.get("start_heading", "E")

        self.segments = {
            name: (tuple(points[0]), tuple(points[1]))
            for name, points in data.get("segments", {}).items()
            if isinstance(points, list) and len(points) == 2
        }

        self.marker_sections = []
        for section in data.get("sections", []):
            names = section.get("segment_names", []) if isinstance(section, dict) else section
            self.marker_sections.append([name for name in names if name in self.segments])

        if not self.marker_sections and self.segments:
            for name in self.segments:
                self.marker_sections.append([name])

        self.start_segment = data.get("start_segment") or (
            self.marker_sections[0][0] if self.marker_sections and self.marker_sections[0] else None
        )

        self.current_marker_number = 0
        self.current_section_index = 0
        self.current_segments = set()
        self.reset()
        return True

    def set_marker_mode(self, enabled: bool):
        self.marker_mode = enabled
        if enabled:
            self.segment_mode = False

    def set_segment_mode(self, enabled: bool):
        self.segment_mode = enabled
        if enabled:
            self.marker_mode = False
    
    def set_maze_map(self, maze_name: str):
        """Compatibility wrapper for older GUI code; loads maze data from JSON."""
        return self.load_maze_from_json(maze_name)

    def reset(self, x=400, y=300, angle=None):
        self.x = x
        self.y = y
        if angle is not None:
            self.angle = angle
        self.last_ts = None
        self.is_moving = False
        self.path = [(self.x, self.y)]
        self._pending_mode = None

        self.current_segment = self.start_segment
        self.heading = self.start_heading
        self.last_intersection = None
        self.pending_intersection = False
        self.finished = False
        self.completed = False
        self.error_segment = None

        if self.start_segment is not None:
            self.visited_segments = {self.start_segment}
        else:
            self.visited_segments = set()

        if self.marker_mode:
            self.current_marker_number = 0
            self.current_section_index = 0
            self.visited_segments = set()
            self._activate_marker_section(0, clear_path=True)
        elif self.segment_mode:
            self._sync_visual_position()

    def full_reset(self):
        self.x = 400.0
        self.y = 300.0

        if not self.preserve_speed:
            self.speed_px_per_s = self.DEFAULT_SPEED
        if not self.preserve_turn:
            self.turn_deg = self.DEFAULT_TURN

        if self.preserve_angle:
            self.angle = self.saved_angle
        else:
            self.angle = self.DEFAULT_ANGLE
            self.saved_angle = self.DEFAULT_ANGLE

        self.last_ts = None
        self.is_moving = False
        self.path = [(self.x, self.y)]
        self._pending_mode = None

        self.current_segment = self.start_segment
        self.heading = self.start_heading
        self.last_intersection = None
        self.pending_intersection = False
        self.finished = False
        self.completed = False
        self.error_segment = None

        if self.start_segment is not None:
            self.visited_segments = {self.start_segment}
        else:
            self.visited_segments = set()

        if self.marker_mode:
            self.current_marker_number = 0
            self.current_section_index = 0
            self.visited_segments = set()
            self._activate_marker_section(0, clear_path=True)
        elif self.segment_mode:
            self._sync_visual_position()

    def process_message(self, msg: dict, ts: float = None):
        if self.marker_mode:
            self._process_marker_message(msg, ts)
        elif self.segment_mode:
            self._process_segment_message(msg, ts)
        else:
            self._process_freeform_message(msg, ts)

    def _section_midpoint(self, section_index: int):
        """Return midpoint of one route section polyline."""
        if not self.marker_sections or not (0 <= section_index < len(self.marker_sections)):
            return self.marker_start

        pieces = []
        total = 0.0
        for name in self.marker_sections[section_index]:
            if name not in self.segments:
                continue
            p1, p2 = self.segments[name]
            length = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            if length <= 0:
                continue
            pieces.append((p1, p2, length))
            total += length

        if not pieces:
            return self.marker_start

        target = total / 2.0
        walked = 0.0
        for p1, p2, length in pieces:
            if walked + length >= target:
                t = (target - walked) / length
                return (p1[0] + (p2[0] - p1[0]) * t,
                        p1[1] + (p2[1] - p1[1]) * t)
            walked += length
        return pieces[-1][1]

    def _activate_marker_section(self, section_index: int, clear_path: bool = False):
        """Activate one section and place robot dot in that section's middle."""
        if not self.marker_sections:
            self.current_segments = set()
            self.current_segment = None
            self.x, self.y = self.marker_start
        else:
            section_index = max(0, min(section_index, len(self.marker_sections) - 1))
            self.current_section_index = section_index
            self.current_segments = set(self.marker_sections[section_index])
            self.current_segment = next(iter(self.current_segments), None)
            self.x, self.y = self._section_midpoint(section_index)

        if clear_path:
            self.path = [(self.x, self.y)]
        else:
            self.path.append((self.x, self.y))

    def _process_marker_message(self, msg: dict, ts: float = None):
        """Process marker-based line-following events.

        EV_APP_TURN_AHEAD (105;N) moves the robot to the next track section.
        EV_APP_FINISH (103) places the robot at the finish point instead of
        resetting immediately.
        """
        if msg.get("msg_type") != 1:
            return

        event_code = msg.get("event_code")
        tag = msg.get("tag")

        # Marker detected: robot_id;1;105;N
        if event_code == 105:
            try:
                marker_no = int(tag)
            except (TypeError, ValueError):
                marker_no = self.current_marker_number + 1

            if 1 <= marker_no <= len(self.marker_positions):
                self.current_marker_number = marker_no

                # Section before the marker is now visited/dark.
                completed_index = marker_no - 1
                if 0 <= completed_index < len(self.marker_sections):
                    self.visited_segments.update(self.marker_sections[completed_index])

                # Active/blue section is after marker N.
                next_index = marker_no
                if next_index < len(self.marker_sections):
                    self._activate_marker_section(next_index)
                else:
                    self.current_segments = set()
                    self.current_segment = None
                    self.x, self.y = self.marker_finish or self.marker_start
                    self.path.append((self.x, self.y))

                self.completed = False
                self.finished = False
                self.error_segment = None
                self.is_moving = False
            return

        # Finish detected: robot_id;1;103
        if event_code == 103:
            for section in self.marker_sections:
                self.visited_segments.update(section)

            self.current_segments = set()
            self.current_segment = None
            self.x, self.y = self.marker_finish or self.marker_start
            self.path.append((self.x, self.y))

            self.finished = True
            self.completed = True
            self.error_segment = None
            self.is_moving = False
            return

        # Lap/start event: reset to the first active section.
        if event_code in (101, 102):
            self.current_marker_number = 0
            self.current_section_index = 0
            self.visited_segments = set()
            self.completed = False
            self.finished = False
            self.error_segment = None
            self.is_moving = False
            self._activate_marker_section(0)
            return

    def _process_freeform_message(self, msg: dict, ts: float = None):
        if ts is None:
            ts = time.time()

        if self.is_moving and self.last_ts is not None:
            dt = ts - self.last_ts
            if 0 < dt < 5.0:
                dist = self.speed_px_per_s * dt
                rad = math.radians(self.angle)
                self.x += dist * math.cos(rad)
                self.y -= dist * math.sin(rad)
                self.path.append((self.x, self.y))

        self.last_ts = ts
        msg_type = msg.get("msg_type")

        if msg_type == 0:
            mode = msg.get("mode")
            self.is_moving = (mode == 0)

        elif msg_type == 2:
            raw = msg.get("raw", "")
            parts = raw.split(";")
            if len(parts) >= 6:
                try:
                    if int(parts[2]) == 6:
                        self._pending_mode = int(parts[3])
                except (ValueError, IndexError):
                    pass

        elif msg_type == 1:
            event_code = msg.get("event_code")
            tag = msg.get("tag")

            if event_code == 1:
                if self._pending_mode is not None:
                    self.is_moving = (self._pending_mode == 0)
                    self._pending_mode = None
                else:
                    self.is_moving = True
            elif event_code == 25: # EV_WALL_DETECTED
                self.wall_distance = tag
                self.is_moving = False # Robot stops when wall is detected
            elif event_code == 27: # EV_TURN_LEFT
                turn_val = tag if tag is not None and tag > 0 else self.turn_deg
                self.angle += turn_val
                self.is_moving = True  # Robot resumes moving forward after turning
                self.is_scanning = False
            elif event_code == 28: # EV_TURN_RIGHT
                turn_val = tag if tag is not None and tag > 0 else self.turn_deg
                self.angle -= turn_val
                self.is_moving = True  # Robot resumes moving forward after turning
                self.is_scanning = False
            elif event_code in (29, 30): # Complete or Stuck
                self.is_moving = False
            elif event_code == 33: # EV_SCAN_STARTED
                self.is_scanning = True
                self.is_moving = False # Robot is stationary during scan
                # Fallback to user's turn_deg if scan tag is missing/0
                self.last_scan_angle = float(tag) if tag is not None and tag > 0 else self.turn_deg

        self.angle %= 360

    def _process_segment_message(self, msg: dict, ts: float = None):
        if not self.segments or self.current_segment is None:
            return
        
        msg_type = msg.get("msg_type")

        if msg_type == 2:
            raw = msg.get("raw", "")
            parts = raw.split(";")
            if len(parts) >= 4:
                try:
                    if int(parts[2]) == 6:
                        self._pending_mode = int(parts[3])
                except (ValueError, IndexError):
                    pass
            return

        if msg_type == 0:
            mode = msg.get("mode")
            self.is_moving = (mode == 0)
            return

        if msg_type != 1:
            return

        event_code = msg.get("event_code")

        if event_code == 1:
            if self._pending_mode is not None:
                self.is_moving = (self._pending_mode == 0)
                self._pending_mode = None
            return
        
        if event_code == 22:
            self.error_segment = self.current_segment
            self.finished = True
            self.is_moving = False
            return

        if event_code == 23:
            self.pending_intersection = True
            self.last_intersection = self._segment_front_node(self.current_segment, self.heading)
            return
        
        if event_code == 26:
            self._turn_around()
            return
        
        if event_code == 27:
            self._take_turn("L")
            return

        if event_code == 28:
            self._take_turn("R")
            return
        
        if event_code == 29:
            self.completed = True
            self.finished = True
            self.is_moving = False
            return

        if event_code == 32:
            self.is_moving = True
            return

        if event_code in (30, 31):
            self.finished = True
            self.is_moving = False
            return

    def set_config(self, speed, turn):
        self.speed_px_per_s = float(speed)
        self.turn_deg = float(turn)

    def get_pos(self):
        return self.x, self.y, self.angle

    def get_segment_states(self):
        return {
            "visited": set(self.visited_segments),
            "current": set(self.current_segments) if self.marker_mode else self.current_segment,
            "finished": self.finished,
            "completed": self.completed,
            "error_segment": self.error_segment,
        }

    def set_start_segment(self, segment_name: str, heading: str = None):
        if segment_name not in self.segments:
            return False

        self.start_segment = segment_name
        if heading is not None:
            self.start_heading = heading
        else:
            self.start_heading = self.heading if self.current_segment is not None else self.start_heading

        self.reset()
        return True

    def rotate_robot_direction(self, clockwise=True):
        if self.current_segment is None:
            return

        order = ["N", "E", "S", "W"]
        idx = order.index(self.heading)

        if clockwise:
            idx = (idx + 1) % 4
        else:
            idx = (idx - 1) % 4

        self.heading = order[idx]
        self._sync_visual_position()

    def find_nearest_segment(self, x: float, y: float, max_distance: float = 80.0):
        if not self.segments:
            return None

        nearest_segment = None
        nearest_distance = None

        for segment_name, (p1, p2) in self.segments.items():
            distance = self._point_to_segment_distance(x, y, p1, p2)
            if nearest_distance is None or distance < nearest_distance:
                nearest_distance = distance
                nearest_segment = segment_name

        if nearest_distance is not None and nearest_distance <= max_distance:
            return nearest_segment
        return None

    def _turn_around(self):
        self.heading = self._opposite(self.heading)
        self._sync_visual_position()

    def _take_turn(self, turn_dir):
        if not self.pending_intersection:
            return

        node = self.last_intersection
        if node is None:
            return

        new_heading = self._turned_heading(self.heading, turn_dir)
        next_segment = self.node_exits.get(node, {}).get(new_heading)

        if next_segment is None:
            return

        self.heading = new_heading
        self.current_segment = next_segment
        self.visited_segments.add(next_segment)
        self.pending_intersection = False
        self._sync_visual_position()

    def _sync_visual_position(self):

        if self.current_segment is None or self.current_segment not in self.segments:
            return
        
        p1, p2 = self.segments[self.current_segment]
        self.x = (p1[0] + p2[0]) / 2.0
        self.y = (p1[1] + p2[1]) / 2.0
        self.angle = self._heading_to_angle(self.heading)

    def _segment_front_node(self, segment_name, heading):
        p1, p2 = self.segments[segment_name]
        if heading == "E":
            return p1 if p1[0] > p2[0] else p2
        if heading == "W":
            return p1 if p1[0] < p2[0] else p2
        if heading == "N":
            return p1 if p1[1] < p2[1] else p2
        if heading == "S":
            return p1 if p1[1] > p2[1] else p2
        return p2

    def _point_to_segment_distance(self, x: float, y: float, p1, p2):
        x1, y1 = p1
        x2, y2 = p2
        dx = x2 - x1
        dy = y2 - y1

        if dx == 0 and dy == 0:
            return math.hypot(x - x1, y - y1)

        t = ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy)
        t = max(0.0, min(1.0, t))

        proj_x = x1 + t * dx
        proj_y = y1 + t * dy
        return math.hypot(x - proj_x, y - proj_y)

    def _heading_to_angle(self, heading):
        return {"E": 0.0, "N": 90.0, "W": 180.0, "S": 270.0}[heading]

    def _opposite(self, heading):
        return {"N": "S", "S": "N", "E": "W", "W": "E"}[heading]

    def _turned_heading(self, heading, turn_dir):
        left_map = {"N": "W", "W": "S", "S": "E", "E": "N"}
        right_map = {"N": "E", "E": "S", "S": "W", "W": "N"}
        if turn_dir == "L":
            return left_map[heading]
        return right_map[heading]
