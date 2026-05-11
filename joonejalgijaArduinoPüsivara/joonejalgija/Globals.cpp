#include "Globals.h"

/**
 * @file Globals.cpp
 * @brief Defines all global runtime variables used by the application.
 */

Servo g_left_wheel;
Servo g_right_wheel;

RobotMode g_mode = MODE_IDLE;

uint8_t g_robot_id = ROBOT_ID_DEFAULT;
uint8_t g_map_number = MAP_NUMBER_DEFAULT;
uint8_t g_status_seq = 0;
uint8_t g_telemetry_enabled = 1;
uint8_t g_debug_mode = 0;
uint8_t g_show_qti_values = 0;

unsigned long g_last_status_ms = 0;
unsigned long g_last_step_ms = 0;
unsigned long g_last_sensor_event_ms = 0;
unsigned long g_last_debug_event_ms = 0;

bool g_line_seen_last = true;
unsigned long g_line_lost_since_ms = 0;
unsigned long g_last_line_event_ms = 0;
bool g_off_track_reported = false;
unsigned long g_qti_fault_since_ms = 0;
int8_t g_last_turn_event_dir = 0;
unsigned long g_last_turn_event_ms = 0;

int8_t g_last_dir = 1;

bool g_start_countdown_active = false;
unsigned long g_start_begin_ms = 0;

bool g_start_boost_active = false;
unsigned long g_start_boost_begin_ms = 0;

bool g_lap_pause_active = false;
unsigned long g_lap_pause_begin_ms = 0;

bool g_marker_pause_active = false;
unsigned long g_marker_pause_begin_ms = 0;

uint16_t g_lap_counter = 0;
uint8_t g_marker_counter = 0;

uint8_t g_special_line_consec = 0;
uint8_t g_centered_consec = 0;
bool g_special_line_armed = false;

unsigned long g_finish_cooldown_until_ms = 0;
unsigned long g_marker_cooldown_until_ms = 0;

unsigned long g_button_ready_after_ms = 0;
int g_last_button_state = HIGH;

char g_rx_buf[RX_BUF_SIZE] = {0};
uint8_t g_rx_len = 0;

unsigned int g_qti_threshold_us = QTI_THRESHOLD_DEFAULT;
uint8_t g_motor_delta_limit = MOTOR_DELTA_DEFAULT;

int g_manual_left_us = SERVO_STOP_LEFT_US;
int g_manual_right_us = SERVO_STOP_RIGHT_US;
bool g_manual_drive_active = false;
unsigned long g_manual_drive_until_ms = 0;

int g_last_left_us = SERVO_STOP_LEFT_US;
int g_last_right_us = SERVO_STOP_RIGHT_US;

uint16_t g_battery_buffer[BATTERY_FILTER_SAMPLES] = {0};
uint8_t g_battery_buffer_index = 0;
uint8_t g_battery_buffer_count = 0;
