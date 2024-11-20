export PULSE_SERVER=unix:/run/user/1000/pulse/native
nohup sudo -E python server.py > /dev/null 2>&1 &
echo "Server started"
