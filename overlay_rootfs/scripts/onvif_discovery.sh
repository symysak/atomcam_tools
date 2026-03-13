#!/bin/sh

# ONVIF WS-Discovery Responder
# Listens for WS-Discovery Probe messages on UDP multicast 239.255.255.250:3702
# and responds with ProbeMatch messages advertising the ONVIF device

HACK_INI=/tmp/hack.ini
PIDFILE=/var/run/onvif_discovery.pid
LOGFILE=/tmp/log/onvif.log
DISCOVERY_PORT=3702
MULTICAST_ADDR=239.255.255.250

get_ip() {
  IP_ADDR=$(ifconfig wlan0 2>/dev/null | awk '/inet addr/ {gsub(/.*addr:/, ""); gsub(/ .*/, ""); print}')
  [ -z "$IP_ADDR" ] && IP_ADDR=$(ifconfig eth0 2>/dev/null | awk '/inet addr/ {gsub(/.*addr:/, ""); gsub(/ .*/, ""); print}')
  echo "$IP_ADDR"
}

get_uuid() {
  HWADDR=$(ifconfig | awk '/HWaddr/ { gsub(/^.*HWaddr */, ""); gsub(/:/, ""); print; exit }')
  # Generate a stable UUID from MAC address
  echo "urn:uuid:${HWADDR:0:8}-${HWADDR:8:4}-1000-8000-${HWADDR}"
}

send_hello() {
  IP_ADDR=$(get_ip)
  [ -z "$IP_ADDR" ] && return 1
  ONVIF_PORT=$(awk -F "=" '/^ONVIF_PORT *=/ {print $2}' $HACK_INI)
  [ -z "$ONVIF_PORT" ] && ONVIF_PORT=80
  UUID=$(get_uuid)
  HOSTNAME=$(hostname)
  MSG_ID="urn:uuid:$(cat /proc/sys/kernel/random/uuid 2>/dev/null || echo $(date +%s)-$$-hello)"

  HELLO="<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<s:Envelope xmlns:s=\"http://www.w3.org/2003/05/soap-envelope\"
            xmlns:a=\"http://schemas.xmlsoap.org/ws/2004/08/addressing\"
            xmlns:d=\"http://schemas.xmlsoap.org/ws/2005/04/discovery\"
            xmlns:dn=\"http://www.onvif.org/ver10/network/wsdl\">
  <s:Header>
    <a:Action>http://schemas.xmlsoap.org/ws/2005/04/discovery/Hello</a:Action>
    <a:MessageID>${MSG_ID}</a:MessageID>
    <a:To>urn:schemas-xmlsoap-org:ws:2005:04:discovery</a:To>
    <d:AppSequence InstanceId=\"1\" MessageNumber=\"1\" />
  </s:Header>
  <s:Body>
    <d:Hello>
      <a:EndpointReference>
        <a:Address>${UUID}</a:Address>
      </a:EndpointReference>
      <d:Types>dn:NetworkVideoTransmitter</d:Types>
      <d:Scopes>onvif://www.onvif.org/type/video_encoder onvif://www.onvif.org/type/Network_Video_Transmitter onvif://www.onvif.org/Profile/Streaming onvif://www.onvif.org/name/${HOSTNAME} onvif://www.onvif.org/hardware/ATOMCAM</d:Scopes>
      <d:XAddrs>http://${IP_ADDR}:${ONVIF_PORT}/cgi-bin/onvif_device_service.cgi</d:XAddrs>
      <d:MetadataVersion>1</d:MetadataVersion>
    </d:Hello>
  </s:Body>
</s:Envelope>"

  # Send Hello message via UDP multicast
  echo "$HELLO" | busybox nc -w 1 -u "$MULTICAST_ADDR" "$DISCOVERY_PORT" 2>/dev/null
  echo "$(date +"%Y/%m/%d %H:%M:%S") : ONVIF Hello sent" >> "$LOGFILE"
}

generate_probe_match() {
  RELATES_TO="$1"
  IP_ADDR=$(get_ip)
  ONVIF_PORT=$(awk -F "=" '/^ONVIF_PORT *=/ {print $2}' $HACK_INI)
  [ -z "$ONVIF_PORT" ] && ONVIF_PORT=80
  UUID=$(get_uuid)
  HOSTNAME=$(hostname)
  MSG_ID="urn:uuid:$(cat /proc/sys/kernel/random/uuid 2>/dev/null || echo $(date +%s)-$$-match)"

  cat << XMLEOF
<?xml version="1.0" encoding="UTF-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope"
            xmlns:a="http://schemas.xmlsoap.org/ws/2004/08/addressing"
            xmlns:d="http://schemas.xmlsoap.org/ws/2005/04/discovery"
            xmlns:dn="http://www.onvif.org/ver10/network/wsdl">
  <s:Header>
    <a:Action>http://schemas.xmlsoap.org/ws/2005/04/discovery/ProbeMatches</a:Action>
    <a:MessageID>${MSG_ID}</a:MessageID>
    <a:RelatesTo>${RELATES_TO}</a:RelatesTo>
    <a:To>http://schemas.xmlsoap.org/ws/2004/08/addressing/role/anonymous</a:To>
    <d:AppSequence InstanceId="1" MessageNumber="1" />
  </s:Header>
  <s:Body>
    <d:ProbeMatches>
      <d:ProbeMatch>
        <a:EndpointReference>
          <a:Address>${UUID}</a:Address>
        </a:EndpointReference>
        <d:Types>dn:NetworkVideoTransmitter</d:Types>
        <d:Scopes>onvif://www.onvif.org/type/video_encoder onvif://www.onvif.org/type/Network_Video_Transmitter onvif://www.onvif.org/Profile/Streaming onvif://www.onvif.org/name/${HOSTNAME} onvif://www.onvif.org/hardware/ATOMCAM</d:Scopes>
        <d:XAddrs>http://${IP_ADDR}:${ONVIF_PORT}/cgi-bin/onvif_device_service.cgi</d:XAddrs>
        <d:MetadataVersion>1</d:MetadataVersion>
      </d:ProbeMatch>
    </d:ProbeMatches>
  </s:Body>
</s:Envelope>
XMLEOF
}

start_discovery() {
  echo $$ > "$PIDFILE"
  echo "$(date +"%Y/%m/%d %H:%M:%S") : ONVIF WS-Discovery started (PID: $$)" >> "$LOGFILE"

  # Send Hello on startup
  sleep 2
  send_hello

  # Listen for WS-Discovery probes on multicast
  # Use busybox nc to listen for UDP multicast probes
  while true; do
    PROBE=$(busybox nc -l -u -p "$DISCOVERY_PORT" -w 5 2>/dev/null)
    if [ -n "$PROBE" ]; then
      # Check if it's a Probe message for ONVIF devices
      IS_PROBE=$(echo "$PROBE" | grep -c "Probe")
      IS_ONVIF=$(echo "$PROBE" | grep -c -i "NetworkVideoTransmitter\|onvif\|Device")
      if [ "$IS_PROBE" -gt 0 ]; then
        # Extract MessageID for RelatesTo
        MSG_ID=$(echo "$PROBE" | sed -n 's/.*<[^>]*:MessageID[^>]*>\([^<]*\)<.*/\1/p' | head -1)
        [ -z "$MSG_ID" ] && MSG_ID=$(echo "$PROBE" | sed -n 's/.*<MessageID[^>]*>\([^<]*\)<.*/\1/p' | head -1)
        [ -z "$MSG_ID" ] && MSG_ID="unknown"

        IP_ADDR=$(get_ip)
        if [ -n "$IP_ADDR" ]; then
          echo "$(date +"%Y/%m/%d %H:%M:%S") : ONVIF Probe received, sending ProbeMatch" >> "$LOGFILE"
          RESPONSE=$(generate_probe_match "$MSG_ID")
          # Send ProbeMatch response via UDP unicast back to the sender
          # Also send to multicast in case unicast fails
          echo "$RESPONSE" | busybox nc -w 1 -u "$MULTICAST_ADDR" "$DISCOVERY_PORT" 2>/dev/null
        fi
      fi
    fi
    sleep 1
  done
}

stop_discovery() {
  if [ -f "$PIDFILE" ]; then
    PID=$(cat "$PIDFILE")
    if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
      kill "$PID" 2>/dev/null
      # Also kill any child nc processes
      for CPID in $(ps -o pid,ppid | awk -v ppid="$PID" '$2==ppid {print $1}'); do
        kill "$CPID" 2>/dev/null
      done
    fi
    rm -f "$PIDFILE"
  fi
  echo "$(date +"%Y/%m/%d %H:%M:%S") : ONVIF WS-Discovery stopped" >> "$LOGFILE"
}

case "$1" in
  start)
    mkdir -p /tmp/log
    start_discovery &
    ;;
  stop)
    stop_discovery
    ;;
  restart)
    stop_discovery
    sleep 1
    mkdir -p /tmp/log
    start_discovery &
    ;;
  hello)
    send_hello
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|hello}"
    exit 1
    ;;
esac

exit 0
