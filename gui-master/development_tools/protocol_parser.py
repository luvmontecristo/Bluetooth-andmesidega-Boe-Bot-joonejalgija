
"""
protocol_parser.py v0.3
Käib läbi sõnumite protokolli ja oskab neid serialiseerida/deserialiseerida.

"""

from message import (
    StatusMessage,
    EventMessage,
    CommandMessage,
    ResponseMessage,
    FaultMessage,
)
from protocol_enums import MsgType, Mode, EventCode, FaultCode


class ProtocolError(Exception):
    pass


class ProtocolParser:
    
    @staticmethod
    def parse(raw: str):
        """Parse raw string into a Message object"""
        parts = raw.strip().split(';')
        
        if len(parts) < 2:
            raise ProtocolError(f"Invalid message: {raw}")
        
        robot_id = int(parts[0])
        msg_type = MsgType(int(parts[1]))
        payload = [int(x) for x in parts[2:]] if len(parts) > 2 else []
        
        if msg_type == MsgType.MSG_STATUS:
            return StatusMessage(
                robot_id=robot_id,
                sequence=payload[0],
                battery_mv=payload[1],
                app_id=payload[2],
                mode=Mode(payload[3]),
                protocol_version=payload[4]
            )
        elif msg_type == MsgType.MSG_EVENT:
            return EventMessage(
                robot_id=robot_id,
                event_code=EventCode(payload[0]),
                data=payload[1:] if len(payload) > 1 else None
            )
        elif msg_type == MsgType.MSG_COMMAND:
            # 6-part: robot_id;2;cmd_code;v1;v2;time
            return CommandMessage(
                robot_id=robot_id,
                command_code=payload[0],
                v1=payload[1] if len(payload) > 1 else 0,
                v2=payload[2] if len(payload) > 2 else 0,
                time=payload[3] if len(payload) > 3 else 0,
                args=payload[4:] if len(payload) > 4 else []
            )
        elif msg_type == MsgType.MSG_RESPONSE:
            return ResponseMessage(
                robot_id=robot_id,
                command_code=payload[0],
                response_data=payload[1:]
            )
        elif msg_type == MsgType.MSG_FAULT:
            return FaultMessage(
                robot_id=robot_id,
                fault_code=FaultCode(payload[0])
            )
        else:
            raise ProtocolError(f"Unknown message type: {msg_type}")
    
    @staticmethod
    def serialize(msg):
        """Convert Message object back to raw string"""
        if isinstance(msg, StatusMessage):
            parts = [
                str(msg.robot_id),
                str(MsgType.MSG_STATUS.value),
                str(msg.sequence),
                str(msg.battery_mv),
                str(msg.app_id),
                str(msg.mode.value),
                str(msg.protocol_version)
            ]
        elif isinstance(msg, EventMessage):
            parts = [
                str(msg.robot_id),
                str(MsgType.MSG_EVENT.value),
                str(msg.event_code.value)
            ]
            if msg.data:
                parts.extend(str(x) for x in msg.data)
        elif isinstance(msg, CommandMessage):
            parts = [
                str(msg.robot_id),
                str(MsgType.MSG_COMMAND.value),
                str(msg.command_code),
                str(msg.v1),
                str(msg.v2),
                str(msg.time)
            ]
            if msg.args:
                parts.extend(str(x) for x in msg.args)
        elif isinstance(msg, ResponseMessage):
            parts = [
                str(msg.robot_id),
                str(MsgType.MSG_RESPONSE.value),
                str(msg.command_code)
            ]
            parts.extend(str(x) for x in msg.response_data)
        elif isinstance(msg, FaultMessage):
            parts = [
                str(msg.robot_id),
                str(MsgType.MSG_FAULT.value),
                str(msg.fault_code.value)
            ]
        else:
            raise ProtocolError(f"Unknown message type: {type(msg)}")
        
        return ';'.join(parts)
    