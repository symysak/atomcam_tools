#!/bin/sh

# ONVIF WS-Discovery Responder
# Listens for WS-Discovery Probe messages on UDP multicast 239.255.255.250:3702
# and responds with ProbeMatch messages advertising the ONVIF device

HACK_INI=/tmp/hack.ini
PIDFILE=/var/run/onvif_discovery.pid
LOGFILE=/tmp/log/onvif.log
DISCOVERY_PORT=3702
MULTICAST_ADDR=239.255.255.250

get_iface() {
  IFACE=$(ip route 2>/dev/null | awk '/default/ {for(i=1;i<=NF;i++){if($i=="dev"){print $(i+1);exit}}}')
  [ -z "$IFACE" ] && IFACE="wlan0"
  echo "$IFACE"
}

get_ip() {
  IP_ADDR=$(ifconfig wlan0 2>/dev/null | awk '/inet addr/ {gsub(/.*addr:/, ""); gsub(/ .*/, ""); print}')
  [ -z "$IP_ADDR" ] && IP_ADDR=$(ifconfig eth0 2>/dev/null | awk '/inet addr/ {gsub(/.*addr:/, ""); gsub(/ .*/, ""); print}')
  echo "$IP_ADDR"
}

get_uuid() {
  HWADDR=$(ifconfig | awk '/HWaddr/ { gsub(/^.*HWaddr */, ""); gsub(/:/, ""); print; exit }')
  # Generate a stable UUID from MAC address using POSIX-compatible substring extraction
  PART1=$(echo "$HWADDR" | cut -c1-8)
  PART2=$(echo "$HWADDR" | cut -c9-12)
  echo "urn:uuid:${PART1}-${PART2}-1000-8000-${HWADDR}"
}

setup_multicast() {
  IFACE=$(get_iface)
  # Ensure multicast is enabled on the interface
  ifconfig "$IFACE" multicast 2>/dev/null
  # Add route for WS-Discovery multicast traffic
  route add -net 239.255.255.250 netmask 255.255.255.255 dev "$IFACE" 2>/dev/null
  echo "$(date +"%Y/%m/%d %H:%M:%S") : Multicast setup on $IFACE" >> "$LOGFILE"
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
      <d:XAddrs>http://${IP_ADDR}:${ONVIF_PORT}/onvif/device_service</d:XAddrs>
      <d:MetadataVersion>1</d:MetadataVersion>
    </d:Hello>
  </s:Body>
</s:Envelope>"

  # Send Hello message via UDP multicast
  echo "$HELLO" | busybox nc -w 1 -u "$MULTICAST_ADDR" "$DISCOVERY_PORT" 2>/dev/null
  echo "$(date +"%Y/%m/%d %H:%M:%S") : ONVIF Hello sent" >> "$LOGFILE"
}

send_bye() {
  IP_ADDR=$(get_ip)
  [ -z "$IP_ADDR" ] && return 1
  UUID=$(get_uuid)
  MSG_ID="urn:uuid:$(cat /proc/sys/kernel/random/uuid 2>/dev/null || echo $(date +%s)-$$-bye)"

  BYE="<?xml version=\"1.0\" encoding=\"UTF-8\"?>
<s:Envelope xmlns:s=\"http://www.w3.org/2003/05/soap-envelope\"
            xmlns:a=\"http://schemas.xmlsoap.org/ws/2004/08/addressing\"
            xmlns:d=\"http://schemas.xmlsoap.org/ws/2005/04/discovery\">
  <s:Header>
    <a:Action>http://schemas.xmlsoap.org/ws/2005/04/discovery/Bye</a:Action>
    <a:MessageID>${MSG_ID}</a:MessageID>
    <a:To>urn:schemas-xmlsoap-org:ws:2005:04:discovery</a:To>
    <d:AppSequence InstanceId=\"1\" MessageNumber=\"1\" />
  </s:Header>
  <s:Body>
    <d:Bye>
      <a:EndpointReference>
        <a:Address>${UUID}</a:Address>
      </a:EndpointReference>
    </d:Bye>
  </s:Body>
</s:Envelope>"

  echo "$BYE" | busybox nc -w 1 -u "$MULTICAST_ADDR" "$DISCOVERY_PORT" 2>/dev/null
  echo "$(date +"%Y/%m/%d %H:%M:%S") : ONVIF Bye sent" >> "$LOGFILE"
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
        <d:XAddrs>http://${IP_ADDR}:${ONVIF_PORT}/onvif/device_service</d:XAddrs>
        <d:MetadataVersion>1</d:MetadataVersion>
      </d:ProbeMatch>
    </d:ProbeMatches>
  </s:Body>
</s:Envelope>
XMLEOF
}

start_discovery() {
  echo "$(date +"%Y/%m/%d %H:%M:%S") : ONVIF WS-Discovery started (PID: $$)" >> "$LOGFILE"

  # Set up multicast reception on the network interface
  setup_multicast

  # Send Hello on startup after brief delay for network readiness
  sleep 2
  send_hello

  # Main loop: listen for Probes and send periodic Hello
  # nc -w 5 times out after 5 seconds; Hello is sent every HELLO_INTERVAL cycles (~30s)
  HELLO_INTERVAL=6
  HELLO_COUNT=0
  while true; do
    PROBE=$(busybox nc -l -u -p "$DISCOVERY_PORT" -w 5 2>/dev/null)
    if [ -n "$PROBE" ]; then
      # Only respond to WS-Discovery Probe (not ProbeMatch or Hello)
      if echo "$PROBE" | grep -q "discovery/Probe" && ! echo "$PROBE" | grep -q "ProbeMatches"; then
        # Extract MessageID for RelatesTo
        MSG_ID=$(echo "$PROBE" | sed -n 's/.*<[^>]*:MessageID[^>]*>\([^<]*\)<.*/\1/p' | head -1)
        [ -z "$MSG_ID" ] && MSG_ID=$(echo "$PROBE" | sed -n 's/.*<MessageID[^>]*>\([^<]*\)<.*/\1/p' | head -1)
        [ -z "$MSG_ID" ] && MSG_ID="unknown"

        IP_ADDR=$(get_ip)
        if [ -n "$IP_ADDR" ]; then
          echo "$(date +"%Y/%m/%d %H:%M:%S") : ONVIF Probe received, sending ProbeMatch" >> "$LOGFILE"
          RESPONSE=$(generate_probe_match "$MSG_ID")
          echo "$RESPONSE" | busybox nc -w 1 -u "$MULTICAST_ADDR" "$DISCOVERY_PORT" 2>/dev/null
        fi
      fi
    fi

    # Send periodic Hello for clients that discover via announcements
    HELLO_COUNT=$((HELLO_COUNT + 1))
    if [ "$HELLO_COUNT" -ge "$HELLO_INTERVAL" ]; then
      send_hello
      HELLO_COUNT=0
    fi
  done
}

stop_discovery() {
  # Send Bye message to notify clients
  send_bye 2>/dev/null

  if [ -f "$PIDFILE" ]; then
    PID=$(cat "$PIDFILE")
    if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
      kill "$PID" 2>/dev/null
      # Also kill any child nc processes
      for CPID in $(ps -o pid,ppid 2>/dev/null | awk -v ppid="$PID" '$2==ppid {print $1}'); do
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
    echo $! > "$PIDFILE"
    ;;
  stop)
    stop_discovery
    ;;
  restart)
    stop_discovery
    sleep 1
    mkdir -p /tmp/log
    start_discovery &
    echo $! > "$PIDFILE"
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
