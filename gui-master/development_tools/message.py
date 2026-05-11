from dataclasses import dataclass, field
from typing import List, Optional
from protocol_enums import MsgType, Mode, EventCode, FaultCode


@dataclass
class StatusMessage:
    robot_id: int
    sequence: int
    battery_mv: int
    app_id: int
    mode: Mode
    protocol_version: int


@dataclass
class EventMessage:
    robot_id: int
    event_code: EventCode
    data: Optional[List[int]] = None


@dataclass
class CommandMessage:
    robot_id: int
    command_code: int
    v1: int = 0
    v2: int = 0
    time: int = 0
    args: List[int] = field(default_factory=list)


@dataclass
class ResponseMessage:
    robot_id: int
    command_code: int
    response_data: List[int]


@dataclass
class FaultMessage:
    robot_id: int
    fault_code: FaultCode
