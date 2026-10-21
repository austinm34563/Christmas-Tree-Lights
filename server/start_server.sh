#!/bin/bash
export PULSE_SERVER=unix:/run/user/1000/pulse/native
cd /home/austinm34563/ChristmasProject/Christmas-Tree-Lights/server/
exec /usr/bin/python3 server.py
