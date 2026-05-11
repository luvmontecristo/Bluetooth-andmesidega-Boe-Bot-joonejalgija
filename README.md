Riistvara:
Arduino Uno (BOE-Bot), 
HC-05 Bluetooth moodul, 
QTI sensorid (joonejälgimine), 
Toide (5x AA), 
Takistid 2x 10k

Tarkvara:
Arduino IDE 
Python 3.10+

Arvuti ja roboti ühendus:
1. Lülita robot sisse
2. leia Bluetooth seadmetes HC-05
3. Sisesta pin:1234
4. Kontrolli, milline virtuaalne COM-port loodi (oletame com 5)

CLI kasutamine:
1. CMD-sse:
2. pip install
3. python python_cli.py --port COM5 --baud 9600 --id 1

CLI sees:
kirjuta help käskude loendi kuvamiseks

GUI kasutamine:
1. CMD-sse:
2. pip install PyQt6 pyserial
3. python robot_gui.py

GUI sees:
1. Vali serial port connection
2. port 5
3. baud 9600
4. Kaardi kuvamises vali rippmenüüst joonejälgimine
5. Vaheta roboti töörežiim RUN-i peale
