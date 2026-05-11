"""
dataGen.py v0.2 (010426)

Simuleerib/genereerib robotilt tulevat telemeetriat/sündmusi jm. 

OUTPUT:
Generating...

Enter number of message to generate: 5
STATUS: 5;0;0;11990;1;0;1
STATUS: 5;0;1;11987;1;0;1
STATUS: 5;0;2;11984;3;0;1
STATUS: 5;0;3;11975;2;0;1
STATUS: 5;0;4;11970;1;0;1

EVENTS:
5;1;21
5;1;23
5;1;25;50

FAULT:
5;4;2

"""


import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import random
import time
from protocol_parser import ProtocolParser
from message import StatusMessage, EventMessage, FaultMessage
from protocol_enums import Mode, EventCode, FaultCode, MsgType


class RobotDataGenerator:
    # fake data for from boebot (sim)
    
    def __init__(self, robot_id=1):
        self.robot_id = robot_id
        self.sequence = 0
        self.battery_mv = 12000  # Start at 12V
    
    def generate_status(self) -> str:
        # bat. drain sim
        self.battery_mv = max(9000, self.battery_mv - random.randint(0, 10))
        
        msg = StatusMessage(
            robot_id=self.robot_id,
            sequence=self.sequence % 256,
            battery_mv=self.battery_mv,
            app_id=255,  # 255 = generated data / ignore auto-map
            mode=Mode.MODE_RUN,
            protocol_version=1
        )
        self.sequence += 1
        return ProtocolParser.serialize(msg)
    
    def generate_event(self, event_code: EventCode = None, data: list = None) -> str:
        if event_code is None:
            event_code = random.choice(list(EventCode))
        
        msg = EventMessage(
            robot_id=self.robot_id,
            event_code=event_code,
            data=data
        )
        return ProtocolParser.serialize(msg)
    
    def generate_fault(self, fault_code: FaultCode = None) -> str:
        if fault_code is None:
            fault_code = random.choice(list(FaultCode))
        
        msg = FaultMessage(
            robot_id=self.robot_id,
            fault_code=fault_code
        )
        return ProtocolParser.serialize(msg)
    
    def generate_session(self, duration_sec: int = 10, status_interval: float = 1.0):
        messages = []
        start_time = time.time()
        
        while time.time() - start_time < duration_sec:
            messages.append(('RX', self.generate_status()))
            
            if random.random() < 0.2:
                event = random.choice([
                    (EventCode.EV_LINE_DETECTED, None),
                    (EventCode.EV_LINE_LOST, None),
                    (EventCode.EV_INTERSECTION, None),
                    (EventCode.EV_WALL_DETECTED, [random.randint(10, 100)]),
                ])
                messages.append(('RX', self.generate_event(event[0], event[1])))
            
            if random.random() < 0.05:
                messages.append(('RX', self.generate_fault()))
            
            time.sleep(status_interval)
        
        return messages


# scuffed CLI
if __name__ == "__main__":
    gen = RobotDataGenerator(robot_id=5)
    
    print("Generating...\n")
    num_messages = int(input("Enter number of message to generate: "))
    for i in range(num_messages):
        msg = gen.generate_status()
        print(f"STATUS: {msg}")
    
    # Generate events
    print("\nEVENTS:")
    print(gen.generate_event(EventCode.EV_LINE_LOST))
    print(gen.generate_event(EventCode.EV_INTERSECTION))
    print(gen.generate_event(EventCode.EV_WALL_DETECTED, [50]))
    
    # Generate a fault
    print("\nFAULT:")
    print(gen.generate_fault(FaultCode.FAULT_BAD_ARG))
    