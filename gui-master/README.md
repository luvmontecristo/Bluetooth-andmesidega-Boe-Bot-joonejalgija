# Robot Monitor GUI (gui-prototype-p2)

PyQt6-based GUI for monitoring and controlling the robot + DT functionality.

## Features (v0.3a)

- **TCP/Serial Connection** 
- **Real-time Status** + **Message Logging**
- **CSV Recording**
- **CSV->CMD Send/Playback**
- **Command Interface and custom command sending**
- **CSV->XOR/b64 and .exe embedding**
- **Data Generation via localhost for testing**
- **Virtual viewer - real-time and playback possible**
- **RX-TX translation with command send**

## v0.2 notes (14.03.26) - embedding groundwork
- bugfix for race condition with conn
- bugfix for log feed (issue command sending) for command sending
- bugfix for csv to cmd, improved logic
- QoL added autoscroll stop and enable feature
- QoL added refresh for logs
- QoL added RX and TX to logs for verbose reading
- QoL updated log max count to 1000 from 200
- **feature added csv embedding module, enables from CSV generation of XOR/b64 py files and exec files** 

## v0.2b notes (15/16.03.26)
- QoL dt server functionality
- QoL minor changes
- **project structure update (cmd separate)**
- **added set_motor, qti, mode, max speed, robot id, mem dump commands**

## v0.3 notes (17.03.26) - visualization groundwork
- improved timestamp/csv compatibility
- added smooth SVG resizing
- added custom (blank) svg
- **visualization update, ability to replay robot's data (including live) on SVGs and on blank**
- ability to customize speed, turning angles and starting position + clear road

## v0.3a notes (17.03.26)
- mismatch/underspecced protocol; based on current robot integration(s); cmdpayload needs change
- QoL TCP/Serial selection improved
- improved UI
- further customizable robot viewer + settings (saveable)
- **basic configuration (via json) added**
- **RX-TX translation including cmd send to TCP/Serial (fundamentals)**
some bugs to fix, not fully tested, sometimes "stops" working (killing dt_server routine fixes)

## v0.3b notes (20.03.26)
- Tracking calibration fix
- Closing app (gui) localhost is running leaves routine running and breas conn fix (dt_server)
- **Universal app control (csv) aka inconsistences fixed. CMD_SET_MODE->_pending_mode and EV_MODE_CHANGED firing reads _pending... (setting is_moving) sets is_moving**

## v0.4-1 notes (01.04.26)
- Protocol udpate (cmdPayload x app values)
- Decoupling feature (disconnect live-feed RX/TX from CSV/manual feed for SVG tracking)
- **b64/xor/exe file full compatibility added (updated csvreplayworker)**
- **data-fluking (custom) added to b64/xor/exe file outs enabling broken data**

## v0.4-2 notes (02.04.26)
- **Semi-advanced auto svg picker**
- Configuration update
- Search filter 
- Dark mode bc why not

## v0.5 notes (20.04.26)
- Segment tracking for Mazes + mapped out available SVGs
- Fallback to improved line tracking
- Added events
- Map drawing (custom)
- Easter egg? 
- UI/UX improvements 


bugs still in: Mode inconsistensies is still not fixed. When playing back blackbox2.csv it breaks (bricks) the system. dt server stops working w no logs (have to pause it, disconnect) and reconnect (in gui). If not Using dt server, it doesn't move whatsoever. It's not moving either way. It does post into logs.

### Example of msg format (for csv) v0.3
`timestamp,direction,raw_message,msg_type,robot_id,sequence,bat_mv,app,mode,protocol,cmd_code,cmd_name,value,value2,value3,event_code,event_name,tag,fault_code,fault_name`
with robot RX being for example (unix ts): 
`2026-01-13 20:06:08.007683,RX,"1;1;27;30",MSG_EVENT,1,,,,,,,,,,,27,EV_TURN_LEFT,30,,`


## TODO:
- data tracking + visual* (unpolished)
- data fluking
- command conversion (RX data -> TX command conversion -> TX CSV)* (cmd needs change)
- autodetect svg + enable/disable svg live-viewer
- (exe/xor/b64) file playback support and reconversion
- configuration via txt, svg upload?

## Dependencies
This project includes the `development_tools` module from the digital_twin project.

### Setup
   ```bash
   git clone git@gitlab.pld.ttu.ee:Arvutisysteemide_projekt/gui.git
   pip install PyQt6 pyserial #gui 
   ```

## Usage

### DT Server (optional, for testing)

```bash
py dt_server.py 
```

### Run the GUI

```bash
python robot_gui.py
```

### Connect to Robot

1. **TCP (Digital Twin)** - Default: `localhost:9000`
2. **Serial** - Select COM port and baud rate
