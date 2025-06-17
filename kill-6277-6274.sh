#!/bin/bash

# Define the target ports
PORTS=(6277 6274)

for PORT in "${PORTS[@]}"; do
  PID=$(lsof -ti tcp:$PORT)
  if [ -n "$PID" ]; then
    echo "Killing process on port $PORT (PID: $PID)"
    kill -9 $PID
  else
    echo "No process found on port $PORT"
  fi
done
