#!/bin/sh

# ONVIF Service Management Script
# Manages the ONVIF WS-Discovery service

HACK_INI=/tmp/hack.ini
LOGFILE=/tmp/log/onvif.log

if [ "$1" = "off" ]; then
  /scripts/onvif_discovery.sh stop
  echo "$(date +"%Y/%m/%d %H:%M:%S") : ONVIF service stopped" >> "$LOGFILE"
  exit 0
fi

if [ "$1" = "watchdog" ]; then
  ONVIF_ENABLE=$(awk -F "=" '/^ONVIF_ENABLE *=/ {print $2}' $HACK_INI)
  [ "$ONVIF_ENABLE" != "on" ] && exit 0
  PIDFILE=/var/run/onvif_discovery.pid
  if [ -f "$PIDFILE" ]; then
    PID=$(cat "$PIDFILE")
    kill -0 "$PID" 2>/dev/null && exit 0
  fi
  # Restart discovery if not running
  /scripts/onvif_discovery.sh start
  exit 0
fi

ONVIF_ENABLE=$(awk -F "=" '/^ONVIF_ENABLE *=/ {print $2}' $HACK_INI)

if [ "$ONVIF_ENABLE" != "on" ]; then
  /scripts/onvif_discovery.sh stop
  exit 0
fi

mkdir -p /tmp/log
echo "$(date +"%Y/%m/%d %H:%M:%S") : ONVIF service starting" >> "$LOGFILE"

# Start WS-Discovery
/scripts/onvif_discovery.sh start

echo "$(date +"%Y/%m/%d %H:%M:%S") : ONVIF service started" >> "$LOGFILE"
exit 0
