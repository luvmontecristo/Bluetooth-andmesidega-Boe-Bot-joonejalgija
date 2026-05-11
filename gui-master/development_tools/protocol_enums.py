from enum import IntEnum

# --- Constants (#define) ---
PROTOCOL_VER = 1

CORE_CMD_MIN = 1
CORE_CMD_MAX = 99

APP_CMD_MIN = 100
APP_CMD_MAX = 199

TEST_CMD_MIN = 200
TEST_CMD_MAX = 239

# enums (Match C++ uint8_t enums)
# enum ver. 200426

class MsgType(IntEnum):
    MSG_STATUS   = 0  
    MSG_EVENT    = 1  
    MSG_COMMAND  = 2  
    MSG_RESPONSE = 3  
    MSG_FAULT    = 4  

class EventCode(IntEnum):
    EV_MODE_CHANGED    = 1
    EV_BUTTON_PRESSED  = 2
    EV_FAULT           = 3
    EV_WARNING         = 4
    EV_RESET           = 5

    EV_LINE_DETECTED   = 20
    EV_LINE_LOST       = 21
    EV_OFF_TRACK       = 22
    EV_INTERSECTION    = 23

    EV_MOTOR_THRESHOLD = 24
    EV_WALL_DETECTED   = 25
    EV_DEAD_END        = 26
    EV_TURN_LEFT       = 27
    EV_TURN_RIGHT      = 28
    EV_PATH_COMPLETE   = 29
    EV_STUCK           = 30
    EV_DESTINATION     = 31
    EV_MOVING_FORWARD  = 32
    EV_SCAN_STARTED    = 33

class CoreCmd(IntEnum):
    CMD_PING             = 1
    CMD_MEMORY_DUMP      = 2
    CMD_SET_LED          = 3
    CMD_SET_TELEMETRY    = 4
    CMD_SET_DEBUG_MODE   = 5
    CMD_SET_MODE         = 6
    CMD_SET_MOTOR        = 7
    CMD_SET_MAX_SPEED    = 8
    CMD_SET_QTI_THRES    = 9
    CMD_CHANGE_ROBOT_ID  = 10

class AppCategory(IntEnum):
    RESERVED    = 0
    LINE        = 1   # 1-9
    LABYRINTH   = 10  # 10-19
    ULTRASOUND  = 20  # 20-29
    BUS         = 30  # 30

class AppCmd(IntEnum):
    CMD_PEOPLE_CNT = 100  

class TestCmd(IntEnum):
    CMD_TEST_DATA_DUMP     = 200
    CMD_TEST_READ_QTI      = 201
    CMD_TEST_READ_BAT      = 202
    CMD_TEST_ULTRA_SWEEP   = 203
    CMD_TEST_ULTRASOUND    = 204
    CMD_TEST_RFID_VALUE    = 205
    CMD_TEST_MOTOR_VALUE   = 206

class RunModeState(IntEnum):
    RUN_FOLLOW_LINE      = 0
    RUN_AT_INTERSECTION  = 1
    RUN_POST_TAG_FORWARD = 2

class Mode(IntEnum):
    MODE_RUN   = 0
    MODE_TEST  = 1
    MODE_IDLE  = 2
    MODE_ERROR = 3

class FaultCode(IntEnum):
    FAULT_UNKNOWN_CMD = 1
    FAULT_BAD_ARG     = 2
    FAULT_BAD_MODE    = 3
    FAULT_INTERNAL    = 4
    FAULT_NOT_ALLOWED = 5

class LedId(IntEnum):
    LED1 = 1
    LED2 = 2

class State(IntEnum):
    OFF = 0
    ON = 1

PAYLOAD_FORMATS = {
    "StatusPayload":   ["robot_id", "msg_type", "sequence", "bat_mv", "app", "mode", "protocol"],
    "EventPayload":    ["robot_id", "msg_type", "event_code", "tag"],
    "CommandPayload":  ["robot_id", "msg_type", "cmd_code", "v1", "v2", "time"],
    "ResponsePayload": ["robot_id", "msg_type", "cmd_code", "value", "value2", "value3"],
    "FaultPayload":    ["robot_id", "msg_type", "fault_code"]
}
