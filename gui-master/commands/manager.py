
"""
commands/manager.py - Logic for formatting and validating robot commands.
Update: 01.04.26 - Updated to new protocol format (ID;2;CMD;V1;V2;TIME)
"""

from enum import IntEnum

class Mode(IntEnum):
    RUN   = 0
    TEST  = 1
    IDLE  = 2
    ERROR = 3

class CommandManager:
    """Handles command formatting and validation."""
    
    @staticmethod
    def format_core_cmd(robot_id: int, cmd_code: int, v1=0, v2=0, time=0) -> str:
        """
        Format a core command (type 2) with 6-part protocol.
        Format: robot_id;2;cmd_code;v1;v2;time
        """
        return f"{robot_id};2;{cmd_code};{v1};{v2};{time}"

    @staticmethod
    def validate_set_motor(current_mode: int) -> (bool, str):
        """
        Check if set_motor is allowed in the current mode.
        Returns (is_allowed, error_message).
        """
        # Allowed in TEST (1) or IDLE (2)
        if current_mode not in (Mode.TEST, Mode.IDLE):
            mode_name = "Unknown"
            try:
                mode_name = Mode(current_mode).name
            except ValueError:
                mode_name = str(current_mode)
            return False, f"Set Motor is allowed only in TEST or IDLE mode! (Current: {mode_name})"
        return True, ""

    @staticmethod
    def get_ping_cmd(robot_id: int) -> str:
        return CommandManager.format_core_cmd(robot_id, 1)

    @staticmethod
    def get_status_cmd(robot_id: int) -> str:
        return CommandManager.format_core_cmd(robot_id, 2)
    
    @staticmethod
    def get_mem_dump_cmd(robot_id: int) -> str:
        return CommandManager.format_core_cmd(robot_id, 2)

    @staticmethod
    def get_set_mode_cmd(robot_id: int, mode: int) -> str:
        return CommandManager.format_core_cmd(robot_id, 6, mode)

    @staticmethod
    def get_set_motor_cmd(robot_id: int, m1: int, m2: int, time: int = 0) -> str:
        """CMD_SET_MOTOR (7) uses v1, v2, and optionally time."""
        return CommandManager.format_core_cmd(robot_id, 7, m1, m2, time)

    @staticmethod
    def get_max_speed_cmd(robot_id: int, val: int) -> str:
        return CommandManager.format_core_cmd(robot_id, 8, val)

    @staticmethod
    def get_qti_thres_cmd(robot_id: int, val: int) -> str:
        return CommandManager.format_core_cmd(robot_id, 9, val)

    @staticmethod
    def get_change_id_cmd(robot_id: int, new_id: int) -> str:
        return CommandManager.format_core_cmd(robot_id, 10, new_id)
