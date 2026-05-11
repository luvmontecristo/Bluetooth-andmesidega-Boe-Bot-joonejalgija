"""
test_parser
testid protocol_parser.py jaoks; töötab. 
output:
Status parse OK
Command serialize OK
Roundtrip OK

PASS
"""

from protocol_parser import ProtocolParser
from message import StatusMessage, CommandMessage
from protocol_enums import RobotMode, EventCode, CoreCommand



def test_status():
    raw = "5;0;100;12000;1;0;1"
    msg = ProtocolParser.parse(raw)
    assert msg.robot_id == 5
    assert msg.mode == RobotMode.MODE_RUN
    print("Status parse OK")


def test_command():
    cmd = CommandMessage(robot_id=1, command_code=CoreCommand.CMD_PING, args=[])
    raw = ProtocolParser.serialize(cmd)
    assert raw == "1;2;1"
    print("Command serialize OK")


def test_roundtrip():
    raw = "3;1;21"
    msg1 = ProtocolParser.parse(raw)
    raw2 = ProtocolParser.serialize(msg1)
    msg2 = ProtocolParser.parse(raw2)
    assert msg1 == msg2
    print("Roundtrip OK")


if __name__ == "__main__":
    test_status()
    test_command()
    test_roundtrip()
    print("\nPASS")
    