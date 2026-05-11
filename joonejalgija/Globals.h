#pragma once
#include <Arduino.h>
#include <Servo.h>
#include "Config.h"
#include "ProtocolDefs.h"

/**
 * @file Globals.h
 * @brief Declarations for all global runtime variables.
 */

extern Servo g_left_wheel;
extern Servo g_right_wheel;

extern RobotMode g_mode;

extern uint8_t g_robot_id;
extern uint8_t g_map_number;
extern uint8_t g_status_seq;
extern uint8_t g_telemetry_enabled;
extern uint8_t g_debug_mode;
extern uint8_t g_show_qti_values;

extern unsigned long g_last_status_ms;
extern unsigned long g_last_step_ms;
extern unsigned long g_last_sensor_event_ms;
extern unsigned long g_last_debug_event_ms;

extern bool g_line_seen_last;
extern unsigned long g_line_lost_since_ms;
extern unsigned long g_last_line_event_ms;
extern bool g_off_track_reported;
extern unsigned long g_qti_fault_since_ms;

/**
 * @brief Last emitted hard-turn event direction.
 *
 * Values:
 * -1 = last emitted was left
 *  0 = none yet
 *  1 = last emitted was right
 */
extern int8_t g_last_turn_event_dir;

/**
 * @brief Timestamp of the most recent hard-turn event.
 */
extern unsigned long g_last_turn_event_ms;

extern int8_t g_last_dir;

extern bool g_start_countdown_active;
extern unsigned long g_start_begin_ms;

extern bool g_start_boost_active;
extern unsigned long g_start_boost_begin_ms;

extern bool g_lap_pause_active;
extern unsigned long g_lap_pause_begin_ms;

extern bool g_marker_pause_active;
extern unsigned long g_marker_pause_begin_ms;

extern uint16_t g_lap_counter;
extern uint8_t g_marker_counter;

extern uint8_t g_special_line_consec;
extern uint8_t g_centered_consec;
extern bool g_special_line_armed;

extern unsigned long g_finish_cooldown_until_ms;
extern unsigned long g_marker_cooldown_until_ms;

extern unsigned long g_button_ready_after_ms;
extern int g_last_button_state;

extern char g_rx_buf[RX_BUF_SIZE];
extern uint8_t g_rx_len;

extern unsigned int g_qti_threshold_us;
extern uint8_t g_motor_delta_limit;

extern int g_manual_left_us;
extern int g_manual_right_us;
extern bool g_manual_drive_active;
extern unsigned long g_manual_drive_until_ms;

extern int g_last_left_us;
extern int g_last_right_us;

extern uint16_t g_battery_buffer[BATTERY_FILTER_SAMPLES];
extern uint8_t g_battery_buffer_index;
extern uint8_t g_battery_buffer_count;
