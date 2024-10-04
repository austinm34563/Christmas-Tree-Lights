COMMAND_NAME="python3 server.py"

# Find the PIDs of the processes matching the command name
PIDS=$(pgrep -f "$COMMAND_NAME")

# Check if any PIDs were found
if [ -z "$PIDS" ]; then
    echo "No processes found for command: $COMMAND_NAME"
    exit 0
fi

# Kill the processes
echo "Killing the following processes: $PIDS"
kill $PIDS

# Optional: Wait for a moment to ensure processes are terminated
sleep 1

# Verify if the processes were killed
for PID in $PIDS; do
    if ps -p $PID > /dev/null; then
        echo "Failed to kill process: $PID"
    else
        echo "Successfully killed process: $PID"
    fi
done
