#pragma once
#include <Arduino.h>

/**
 * @file ProtocolDefs.h
 * @brief Protocol enums for message types, modes, events, faults, and commands.
 */

/**
 * @brief Protocol message types.
 */
enum MessageType : uint8_t {
  MSG_STATUS   = 0,
  MSG_EVENT    = 1,
  MSG_COMMAND  = 2,
  MSG_RESPONSE = 3,
  MSG_FAULT    = 4
};

/**
 * @brief Robot operating modes.
 */
enum RobotMode : uint8_t {
  MODE_RUN   = 0,
  MODE_TEST  = 1,
  MODE_IDLE  = 2,
  MODE_ERROR = 3
};

/**
 * @brief Event codes used by the protocol.
 */
enum EventCode : uint8_t {
  EV_MODE_CHANGED    = 1,
  EV_BUTTON_PRESSED  = 2,
  EV_FAULT           = 3,
  EV_WARNING         = 4,
  EV_RESET           = 5,

  EV_LINE_DETECTED   = 20,
  EV_LINE_LOST       = 21,
  EV_OFF_TRACK       = 22,
  EV_INTERSECTION    = 23,
  EV_MOTOR_THRESHOLD = 24,
  EV_WALL_DETECTED   = 25,
  EV_DEAD_END        = 26,
  EV_TURN_LEFT       = 27,
  EV_TURN_RIGHT      = 28,
  EV_PATH_COMPLETE   = 29,
  EV_STUCK           = 30,

  EV_APP_SENS        = 100,
  EV_APP_LAP         = 101,
  EV_APP_START       = 102,
  EV_APP_FINISH      = 103,
  EV_APP_BOOST       = 104,
  EV_APP_TURN_AHEAD  = 105,
  EV_APP_BAT         = 106,
  EV_APP_MOTOR       = 107
};

/**
 * @brief Fault codes returned by the protocol.
 */
enum FaultCode : uint8_t {
  FAULT_UNKNOWN_CMD = 1,
  FAULT_BAD_ARG     = 2,
  FAULT_BAD_MODE    = 3,
  FAULT_INTERNAL    = 4,
  FAULT_NOT_ALLOWED = 5
};

/**
 * @brief Core command codes supported by the robot.
 *
 * These values were aligned with the protocol guide.
 */
enum CoreCommand : uint16_t {
  CMD_PING               = 1,
  CMD_MEMORY_DUMP        = 2,
  CMD_SET_LED            = 3,
  CMD_SET_TELEMETRY      = 4,
  CMD_SET_DEBUG_MODE     = 5,
  CMD_SET_MODE           = 6,
  CMD_SET_MOTOR          = 7,
  CMD_REDUCE_MAX_SPEED   = 8,
  CMD_SET_QTI_THRESHOLD  = 9,
  CMD_CHANGE_ROBOT_ID    = 10,
  CMD_RESET_EEPROM       = 11
};

/**
 * @brief Application-specific command codes.
 *
 * These are kept as extensions so the firmware functionality stays available
 * while the core command numbers follow the guide.
 */
enum AppCommand : uint16_t {
  CMD_GET_STATUS      = 100,
  CMD_START_APP       = 101,
  CMD_STOP_APP        = 102,
  CMD_SHOW_QTI_VALUES = 103,
  CMD_SET_MAP_NUMBER  = 104
};

/**
 * @brief Test command codes supported in test mode.
 */
enum TestCommand : uint16_t {
  CMD_TEST_DATA_DUMP   = 200,
  CMD_TEST_READ_QTI    = 201,
  CMD_TEST_READ_BAT    = 202,
  CMD_TEST_ULTRA_SWEEP = 203,
  CMD_TEST_ULTRASOUND  = 204,
  CMD_TEST_RFID_VALUE  = 205,
  CMD_TEST_MOTOR_VALUE = 206
};

/**
 * @brief LED identifiers used by LED control commands.
 */
enum LedId : uint8_t {
  LED_ID_LEFT  = 1,
  LED_ID_RIGHT = 2,
  LED_ID_BOTH  = 3
};

/**
 * @brief LED control modes used by SET_LED.
 */
enum LedMode : uint8_t {
  LED_MODE_WRITE  = 0,
  LED_MODE_TOGGLE = 1
};

/**
 * @brief Logical LED states.
 */
enum LedState : uint8_t {
  LED_STATE_OFF = 0,
  LED_STATE_ON  = 1
};