
"""
commands/translator.py - Translates RX messages to TX commands.
"""
import json
import os
from .manager import CommandManager

class RXToTXTranslator:
    def __init__(self, config_path=None):
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), "..", "configs", "robot_profiles.json")
        
        self.profiles = {}
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                self.profiles = json.load(f).get("apps", {})
        except Exception as e:
            print(f"TRANSLATOR ERROR: Failed to load profiles: {e}")

    def translate(self, msg: dict) -> list:
        """
        Translates an RX message (dict) into a list of TX raw strings.
        """
        robot_id = msg.get("robot_id")
        msg_type = msg.get("msg_type")
        app_id = str(msg.get("app_id", "default"))
        
        profile = self.profiles.get(app_id, self.profiles.get("default", {}))
        speeds = profile.get("speeds", {})
        
        results = []
        
        if msg_type == 0: # STATUS
            mode = msg.get("mode")
            if mode == 0: # RUN
                m1, m2 = speeds.get("forward", [0, 0])
                results.append(CommandManager.get_set_motor_cmd(robot_id, m1, m2, 0))
            else:
                results.append(CommandManager.get_set_motor_cmd(robot_id, 0, 0, 0))
                
        elif msg_type == 1: # EVENT
            event_code = msg.get("event_code")
            # 27: EV_TURN_LEFT, 28: EV_TURN_RIGHT
            if event_code == 27:
                m1, m2 = speeds.get("turn_left", [0, 0])
                results.append(CommandManager.get_set_motor_cmd(robot_id, m1, m2, 0))
            elif event_code == 28:
                m1, m2 = speeds.get("turn_right", [0, 0])
                results.append(CommandManager.get_set_motor_cmd(robot_id, m1, m2, 0))
            elif event_code in (29, 30): # Complete or Stuck
                results.append(CommandManager.get_set_motor_cmd(robot_id, 0, 0, 0))
                
        return results
