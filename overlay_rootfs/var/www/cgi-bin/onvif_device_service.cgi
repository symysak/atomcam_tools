#!/bin/sh

# ONVIF Device Management Service
# Handles SOAP requests for device information, capabilities, and services

echo "Content-Type: application/soap+xml; charset=utf-8"
echo ""

HACK_INI=/tmp/hack.ini
HOSTNAME=$(hostname)
HWADDR=$(ifconfig | awk '/HWaddr/ { gsub(/^.*HWaddr */, ""); print $0; exit }')
SERIAL=$(echo "$HWADDR" | sed 's/://g')
PRODUCT_MODEL=$(awk -F "=" '/^PRODUCT_MODEL/ {print $2}' /atom/configs/.product_config 2>/dev/null || echo "ATOMCAM")
FIRMWARE_VER=$(cat /etc/atomhack.ver 2>/dev/null || echo "1.0.0")
IP_ADDR=$(ifconfig wlan0 2>/dev/null | awk '/inet addr/ {gsub(/.*addr:/, ""); gsub(/ .*/, ""); print}')
[ -z "$IP_ADDR" ] && IP_ADDR=$(ifconfig eth0 2>/dev/null | awk '/inet addr/ {gsub(/.*addr:/, ""); gsub(/ .*/, ""); print}')
ONVIF_PORT=$(awk -F "=" '/^ONVIF_PORT *=/ {print $2}' $HACK_INI)
[ -z "$ONVIF_PORT" ] && ONVIF_PORT=80

# Read SOAP request from stdin
REQUEST=$(cat)

# Extract SOAP action from request body
ACTION=$(echo "$REQUEST" | sed -n 's/.*<[^>]*:\?\(Get[A-Za-z]*\)[> /].*/\1/p' | head -1)
[ -z "$ACTION" ] && ACTION=$(echo "$REQUEST" | sed -n 's/.*<\(Get[A-Za-z]*\)[> /].*/\1/p' | head -1)

# Also check for non-Get actions
if [ -z "$ACTION" ]; then
  ACTION=$(echo "$REQUEST" | sed -n 's/.*<[^>]*:\?\(SystemReboot\)[> /].*/\1/p' | head -1)
fi

SERVICE_ADDR="http://${IP_ADDR}:${ONVIF_PORT}"

case "$ACTION" in
  GetDeviceInformation)
    cat << XMLEOF
<?xml version="1.0" encoding="UTF-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope"
            xmlns:tds="http://www.onvif.org/ver10/device/wsdl">
  <s:Body>
    <tds:GetDeviceInformationResponse>
      <tds:Manufacturer>ATOM</tds:Manufacturer>
      <tds:Model>${PRODUCT_MODEL}</tds:Model>
      <tds:FirmwareVersion>${FIRMWARE_VER}</tds:FirmwareVersion>
      <tds:SerialNumber>${SERIAL}</tds:SerialNumber>
      <tds:HardwareId>${PRODUCT_MODEL}</tds:HardwareId>
    </tds:GetDeviceInformationResponse>
  </s:Body>
</s:Envelope>
XMLEOF
    ;;

  GetCapabilities)
    cat << XMLEOF
<?xml version="1.0" encoding="UTF-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope"
            xmlns:tds="http://www.onvif.org/ver10/device/wsdl"
            xmlns:tt="http://www.onvif.org/ver10/schema">
  <s:Body>
    <tds:GetCapabilitiesResponse>
      <tds:Capabilities>
        <tt:Device>
          <tt:XAddr>${SERVICE_ADDR}/cgi-bin/onvif_device_service.cgi</tt:XAddr>
          <tt:Network>
            <tt:IPFilter>false</tt:IPFilter>
            <tt:ZeroConfiguration>false</tt:ZeroConfiguration>
            <tt:IPVersion6>false</tt:IPVersion6>
            <tt:DynDNS>false</tt:DynDNS>
          </tt:Network>
          <tt:System>
            <tt:DiscoveryResolve>false</tt:DiscoveryResolve>
            <tt:DiscoveryBye>true</tt:DiscoveryBye>
            <tt:RemoteDiscovery>false</tt:RemoteDiscovery>
            <tt:SystemBackup>false</tt:SystemBackup>
            <tt:FirmwareUpgrade>false</tt:FirmwareUpgrade>
            <tt:SystemLogging>false</tt:SystemLogging>
          </tt:System>
        </tt:Device>
        <tt:Media>
          <tt:XAddr>${SERVICE_ADDR}/cgi-bin/onvif_media_service.cgi</tt:XAddr>
          <tt:StreamingCapabilities>
            <tt:RTPMulticast>false</tt:RTPMulticast>
            <tt:RTP_TCP>true</tt:RTP_TCP>
            <tt:RTP_RTSP_TCP>true</tt:RTP_RTSP_TCP>
          </tt:StreamingCapabilities>
        </tt:Media>
      </tds:Capabilities>
    </tds:GetCapabilitiesResponse>
  </s:Body>
</s:Envelope>
XMLEOF
    ;;

  GetServices)
    cat << XMLEOF
<?xml version="1.0" encoding="UTF-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope"
            xmlns:tds="http://www.onvif.org/ver10/device/wsdl">
  <s:Body>
    <tds:GetServicesResponse>
      <tds:Service>
        <tds:Namespace>http://www.onvif.org/ver10/device/wsdl</tds:Namespace>
        <tds:XAddr>${SERVICE_ADDR}/cgi-bin/onvif_device_service.cgi</tds:XAddr>
        <tds:Version>
          <tds:Major>2</tds:Major>
          <tds:Minor>0</tds:Minor>
        </tds:Version>
      </tds:Service>
      <tds:Service>
        <tds:Namespace>http://www.onvif.org/ver10/media/wsdl</tds:Namespace>
        <tds:XAddr>${SERVICE_ADDR}/cgi-bin/onvif_media_service.cgi</tds:XAddr>
        <tds:Version>
          <tds:Major>2</tds:Major>
          <tds:Minor>0</tds:Minor>
        </tds:Version>
      </tds:Service>
    </tds:GetServicesResponse>
  </s:Body>
</s:Envelope>
XMLEOF
    ;;

  GetScopes)
    cat << XMLEOF
<?xml version="1.0" encoding="UTF-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope"
            xmlns:tds="http://www.onvif.org/ver10/device/wsdl"
            xmlns:tt="http://www.onvif.org/ver10/schema">
  <s:Body>
    <tds:GetScopesResponse>
      <tds:Scopes>
        <tt:ScopeDef>Fixed</tt:ScopeDef>
        <tt:ScopeItem>onvif://www.onvif.org/type/video_encoder</tt:ScopeItem>
      </tds:Scopes>
      <tds:Scopes>
        <tt:ScopeDef>Fixed</tt:ScopeDef>
        <tt:ScopeItem>onvif://www.onvif.org/type/Network_Video_Transmitter</tt:ScopeItem>
      </tds:Scopes>
      <tds:Scopes>
        <tt:ScopeDef>Fixed</tt:ScopeDef>
        <tt:ScopeItem>onvif://www.onvif.org/Profile/Streaming</tt:ScopeItem>
      </tds:Scopes>
      <tds:Scopes>
        <tt:ScopeDef>Configurable</tt:ScopeDef>
        <tt:ScopeItem>onvif://www.onvif.org/name/${HOSTNAME}</tt:ScopeItem>
      </tds:Scopes>
      <tds:Scopes>
        <tt:ScopeDef>Fixed</tt:ScopeDef>
        <tt:ScopeItem>onvif://www.onvif.org/hardware/${PRODUCT_MODEL}</tt:ScopeItem>
      </tds:Scopes>
    </tds:GetScopesResponse>
  </s:Body>
</s:Envelope>
XMLEOF
    ;;

  GetSystemDateAndTime)
    YEAR=$(date +%Y)
    MONTH=$(date +%-m)
    DAY=$(date +%-d)
    HOUR=$(date -u +%-H)
    MIN=$(date -u +%-M)
    SEC=$(date -u +%-S)
    TZ=$(date +%Z)
    cat << XMLEOF
<?xml version="1.0" encoding="UTF-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope"
            xmlns:tds="http://www.onvif.org/ver10/device/wsdl"
            xmlns:tt="http://www.onvif.org/ver10/schema">
  <s:Body>
    <tds:GetSystemDateAndTimeResponse>
      <tds:SystemDateAndTime>
        <tt:DateTimeType>NTP</tt:DateTimeType>
        <tt:DaylightSavings>false</tt:DaylightSavings>
        <tt:TimeZone>
          <tt:TZ>${TZ}</tt:TZ>
        </tt:TimeZone>
        <tt:UTCDateTime>
          <tt:Time>
            <tt:Hour>${HOUR}</tt:Hour>
            <tt:Minute>${MIN}</tt:Minute>
            <tt:Second>${SEC}</tt:Second>
          </tt:Time>
          <tt:Date>
            <tt:Year>${YEAR}</tt:Year>
            <tt:Month>${MONTH}</tt:Month>
            <tt:Day>${DAY}</tt:Day>
          </tt:Date>
        </tt:UTCDateTime>
      </tds:SystemDateAndTime>
    </tds:GetSystemDateAndTimeResponse>
  </s:Body>
</s:Envelope>
XMLEOF
    ;;

  GetNetworkInterfaces)
    cat << XMLEOF
<?xml version="1.0" encoding="UTF-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope"
            xmlns:tds="http://www.onvif.org/ver10/device/wsdl"
            xmlns:tt="http://www.onvif.org/ver10/schema">
  <s:Body>
    <tds:GetNetworkInterfacesResponse>
      <tds:NetworkInterfaces token="wlan0">
        <tt:Enabled>true</tt:Enabled>
        <tt:Info>
          <tt:Name>wlan0</tt:Name>
          <tt:HwAddress>${HWADDR}</tt:HwAddress>
        </tt:Info>
      </tds:NetworkInterfaces>
    </tds:GetNetworkInterfacesResponse>
  </s:Body>
</s:Envelope>
XMLEOF
    ;;

  *)
    # Default: return empty response for unknown actions
    cat << XMLEOF
<?xml version="1.0" encoding="UTF-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope"
            xmlns:tds="http://www.onvif.org/ver10/device/wsdl">
  <s:Body>
    <s:Fault>
      <s:Code>
        <s:Value>s:Sender</s:Value>
        <s:Subcode>
          <s:Value>ter:ActionNotSupported</s:Value>
        </s:Subcode>
      </s:Code>
      <s:Reason>
        <s:Text xml:lang="en">Action not supported</s:Text>
      </s:Reason>
    </s:Fault>
  </s:Body>
</s:Envelope>
XMLEOF
    ;;
esac
