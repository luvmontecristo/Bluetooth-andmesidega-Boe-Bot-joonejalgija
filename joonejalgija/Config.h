#pragma once
#include <Arduino.h>

/**
 * @file Config.h
 * @brief Static configuration constants for the robot application.
 */

/* ===================== PINS ===================== */
const uint8_t PIN_BUTTON      = 2;
const uint8_t PIN_SERVO_RIGHT = 5;
const uint8_t PIN_SERVO_LEFT  = 6;
const uint8_t PIN_LED_RIGHT   = 7;
const uint8_t PIN_LED_LEFT    = 8;
const uint8_t PIN_QTI_LEFT    = A0;
const uint8_t PIN_QTI_MIDDLE  = A1;
const uint8_t PIN_QTI_RIGHT   = A2;
const uint8_t PIN_BATTERY     = A5;

/* ===================== SERIAL ===================== */
const unsigned long SERIAL_BAUD = 9600;

/* ===================== LED ===================== */
const uint8_t LED_ON  = HIGH;
const uint8_t LED_OFF = LOW;

/* ===================== APP / PROTOCOL ===================== */
const uint8_t ROBOT_ID_DEFAULT   = 1;
const uint8_t MAP_NUMBER_DEFAULT = 1;
const uint8_t PROTOCOL_V1        = 1;

/* ===================== TIMING ===================== */
const unsigned long BOOT_BLINK_MS            = 200;
const unsigned long STATUS_INTERVAL_MS       = 1000;
const unsigned long STEP_INTERVAL_MS         = 20;
const unsigned long SENSOR_EVENT_MS          = 200;
const unsigned long VERBOSE_EVENT_MS         = 500;
const unsigned long LINE_EVENT_MIN_GAP_MS    = 250;
const unsigned long BUTTON_DEBOUNCE_MS       = 200;
const unsigned long BUTTON_STARTUP_IGNORE_MS = 1000;
const unsigned long RUN_START_HOLD_MS        = 5000;
const unsigned long START_BOOST_MS           = 350;

const unsigned long LINE_LOST_OFF_TRACK_MS   = 5000;
const unsigned long QTI_SENSOR_ERROR_MS      = 1000;
const uint8_t HARD_TURN_RELEASE_STEPS        = 3;

/* ===================== SPECIAL LINE DETECTION ===================== */
const unsigned int CENTER_TRACK_MIN_US         = 700;
const unsigned int SPECIAL_LINE_CENTER_MIN_US  = 1050;
const unsigned int SPECIAL_LINE_SIDE_MIN_US    = 1600;
const unsigned int SPECIAL_LINE_LR_DIFF_MAX_US = 700;

const uint8_t SPECIAL_LINE_MIN_STEPS  = 12;
const uint8_t FINISH_LINE_MIN_STEPS   = 16;
const uint8_t SPECIAL_LINE_CONSEC_MAX = 80;

const unsigned long MARKER_PAUSE_MS    = 1200;
const unsigned long FINISH_PAUSE_MS    = 5000;
const unsigned long MARKER_COOLDOWN_MS = 1200;
const unsigned long FINISH_COOLDOWN_MS = 3000;

/* ===================== RX ===================== */
const uint8_t RX_BUF_SIZE = 64;

/* ===================== QTI ===================== */
const unsigned int QTI_CHARGE_DELAY_US   = 300;
const unsigned int QTI_TIMEOUT_US        = 3000;
const unsigned int QTI_THRESHOLD_DEFAULT = 400;
const unsigned int QTI_THRESHOLD_MIN     = 1;
const unsigned int QTI_THRESHOLD_MAX     = 3000;

const unsigned int ALL_BLACK_THRESHOLD_US = 900;

/* ===================== BATTERY ===================== */
const uint16_t ADC_REFERENCE_MV       = 5000;
const uint16_t ADC_MAX_VALUE          = 1023;
const uint8_t  BATTERY_DIVIDER_RATIO  = 2;
const uint8_t  BATTERY_FILTER_SAMPLES = 8;

/* ===================== WATCHDOG ===================== */
const uint8_t WATCHDOG_ENABLED = 1;

/* ===================== SERVO / MOTOR ===================== */
const int SERVO_STOP_LEFT_US  = 1495;
const int SERVO_STOP_RIGHT_US = 1495;

const uint8_t MOTOR_DELTA_DEFAULT = 55;
const uint8_t MOTOR_DELTA_MIN     = 0;
const uint8_t MOTOR_DELTA_MAX     = 200;
const int MOTOR_RAMP_STEP_US      = 25;

/* Base forward */
const int SPEED_FWD_LEFT_US  = 1550;
const int SPEED_FWD_RIGHT_US = 1445;

/* Soft turn */
const int SPEED_SOFT_LEFT_US_LEFT   = 1525;
const int SPEED_SOFT_LEFT_US_RIGHT  = 1450;
const int SPEED_SOFT_RIGHT_US_LEFT  = 1550;
const int SPEED_SOFT_RIGHT_US_RIGHT = 1475;

/* Hard turn */
const int SPEED_HARD_LEFT_US_LEFT   = 1435;
const int SPEED_HARD_LEFT_US_RIGHT  = 1435;
const int SPEED_HARD_RIGHT_US_LEFT  = 1565;
const int SPEED_HARD_RIGHT_US_RIGHT = 1565;
