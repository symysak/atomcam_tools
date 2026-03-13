#!/bin/sh

# ONVIF Media Service
# Handles SOAP requests for media profiles and stream URIs

echo "Content-Type: application/soap+xml; charset=utf-8"
echo ""

HACK_INI=/tmp/hack.ini
HOSTNAME=$(hostname)
IP_ADDR=$(ifconfig wlan0 2>/dev/null | awk '/inet addr/ {gsub(/.*addr:/, ""); gsub(/ .*/, ""); print}')
[ -z "$IP_ADDR" ] && IP_ADDR=$(ifconfig eth0 2>/dev/null | awk '/inet addr/ {gsub(/.*addr:/, ""); gsub(/ .*/, ""); print}')

RTSP_VIDEO0=$(awk -F "=" '/^RTSP_VIDEO0 *=/ {print $2}' $HACK_INI)
RTSP_VIDEO1=$(awk -F "=" '/^RTSP_VIDEO1 *=/ {print $2}' $HACK_INI)
RTSP_VIDEO2=$(awk -F "=" '/^RTSP_VIDEO2 *=/ {print $2}' $HACK_INI)
RTSP_AUDIO0=$(awk -F "=" '/^RTSP_AUDIO0 *=/ {print $2}' $HACK_INI)
RTSP_AUDIO1=$(awk -F "=" '/^RTSP_AUDIO1 *=/ {print $2}' $HACK_INI)
RTSP_AUDIO2=$(awk -F "=" '/^RTSP_AUDIO2 *=/ {print $2}' $HACK_INI)
RTSP_OVER_HTTP=$(awk -F "=" '/^RTSP_OVER_HTTP *=/ {print $2}' $HACK_INI)
RTSP_AUTH=$(awk -F "=" '/^RTSP_AUTH *=/ {print $2}' $HACK_INI)
RTSP_USER=$(awk -F "=" '/^RTSP_USER *=/ {print $2}' $HACK_INI)
RTSP_PASSWD=$(awk -F "=" '/^RTSP_PASSWD *=/ {print $2}' $HACK_INI)

RTSP_PORT=8554
[ "$RTSP_OVER_HTTP" = "on" ] && RTSP_PORT=8080

# Build auth string for RTSP URIs
RTSP_AUTH_STR=""
if [ "$RTSP_AUTH" = "on" ] && [ -n "$RTSP_USER" ] && [ -n "$RTSP_PASSWD" ]; then
  RTSP_AUTH_STR="${RTSP_USER}:${RTSP_PASSWD}@"
fi

# Read SOAP request from stdin
REQUEST=$(cat)

# Extract SOAP action from request body
ACTION=$(echo "$REQUEST" | sed -n 's/.*<[^>]*:\?\(Get[A-Za-z]*\)[> /].*/\1/p' | head -1)
[ -z "$ACTION" ] && ACTION=$(echo "$REQUEST" | sed -n 's/.*<\(Get[A-Za-z]*\)[> /].*/\1/p' | head -1)

# Extract ProfileToken for GetStreamUri
PROFILE_TOKEN=$(echo "$REQUEST" | sed -n 's/.*<[^>]*:\?\(ProfileToken\)[> ]*>\([^<]*\)<.*/\2/p' | head -1)
[ -z "$PROFILE_TOKEN" ] && PROFILE_TOKEN=$(echo "$REQUEST" | sed -n 's/.*<\(ProfileToken\)[> ]*>\([^<]*\)<.*/\2/p' | head -1)

# Generate profile XML block
generate_profile_main() {
  AUDIO_CONFIG=""
  if [ "$RTSP_AUDIO0" != "off" ] && [ -n "$RTSP_AUDIO0" ] && [ "$RTSP_AUDIO0" != "OPUS" ]; then
    AUDIO_ENC="G711"
    [ "$RTSP_AUDIO0" = "AAC" ] && AUDIO_ENC="AAC"
    AUDIO_CONFIG="
        <tt:AudioSourceConfiguration token=\"audio_src_config0\">
          <tt:Name>AudioSource0</tt:Name>
          <tt:UseCount>1</tt:UseCount>
          <tt:SourceToken>audio_src0</tt:SourceToken>
        </tt:AudioSourceConfiguration>
        <tt:AudioEncoderConfiguration token=\"audio_enc_config0\">
          <tt:Name>AudioEncoder0</tt:Name>
          <tt:UseCount>1</tt:UseCount>
          <tt:Encoding>${AUDIO_ENC}</tt:Encoding>
          <tt:Bitrate>64</tt:Bitrate>
          <tt:SampleRate>8</tt:SampleRate>
        </tt:AudioEncoderConfiguration>"
  fi
  cat << XMLEOF
      <trt:Profiles token="main_stream" fixed="true">
        <tt:Name>MainStream</tt:Name>
        <tt:VideoSourceConfiguration token="video_src_config0">
          <tt:Name>VideoSource0</tt:Name>
          <tt:UseCount>1</tt:UseCount>
          <tt:SourceToken>video_src0</tt:SourceToken>
          <tt:Bounds x="0" y="0" width="1920" height="1080" />
        </tt:VideoSourceConfiguration>
        <tt:VideoEncoderConfiguration token="video_enc_config0">
          <tt:Name>VideoEncoder0</tt:Name>
          <tt:UseCount>1</tt:UseCount>
          <tt:Encoding>H264</tt:Encoding>
          <tt:Resolution>
            <tt:Width>1920</tt:Width>
            <tt:Height>1080</tt:Height>
          </tt:Resolution>
          <tt:Quality>5</tt:Quality>
          <tt:RateControl>
            <tt:FrameRateLimit>20</tt:FrameRateLimit>
            <tt:EncodingInterval>1</tt:EncodingInterval>
            <tt:BitrateLimit>2048</tt:BitrateLimit>
          </tt:RateControl>
          <tt:H264>
            <tt:GovLength>20</tt:GovLength>
            <tt:H264Profile>Main</tt:H264Profile>
          </tt:H264>
          <tt:Multicast>
            <tt:Address>
              <tt:Type>IPv4</tt:Type>
              <tt:IPv4Address>0.0.0.0</tt:IPv4Address>
            </tt:Address>
            <tt:Port>0</tt:Port>
            <tt:TTL>0</tt:TTL>
            <tt:AutoStart>false</tt:AutoStart>
          </tt:Multicast>
          <tt:SessionTimeout>PT60S</tt:SessionTimeout>
        </tt:VideoEncoderConfiguration>${AUDIO_CONFIG}
      </trt:Profiles>
XMLEOF
}

generate_profile_sub() {
  AUDIO_CONFIG=""
  if [ "$RTSP_AUDIO1" != "off" ] && [ -n "$RTSP_AUDIO1" ] && [ "$RTSP_AUDIO1" != "OPUS" ]; then
    AUDIO_ENC="G711"
    [ "$RTSP_AUDIO1" = "AAC" ] && AUDIO_ENC="AAC"
    AUDIO_CONFIG="
        <tt:AudioSourceConfiguration token=\"audio_src_config1\">
          <tt:Name>AudioSource1</tt:Name>
          <tt:UseCount>1</tt:UseCount>
          <tt:SourceToken>audio_src0</tt:SourceToken>
        </tt:AudioSourceConfiguration>
        <tt:AudioEncoderConfiguration token=\"audio_enc_config1\">
          <tt:Name>AudioEncoder1</tt:Name>
          <tt:UseCount>1</tt:UseCount>
          <tt:Encoding>${AUDIO_ENC}</tt:Encoding>
          <tt:Bitrate>64</tt:Bitrate>
          <tt:SampleRate>8</tt:SampleRate>
        </tt:AudioEncoderConfiguration>"
  fi
  cat << XMLEOF
      <trt:Profiles token="sub_stream" fixed="true">
        <tt:Name>SubStream</tt:Name>
        <tt:VideoSourceConfiguration token="video_src_config1">
          <tt:Name>VideoSource1</tt:Name>
          <tt:UseCount>1</tt:UseCount>
          <tt:SourceToken>video_src0</tt:SourceToken>
          <tt:Bounds x="0" y="0" width="640" height="360" />
        </tt:VideoSourceConfiguration>
        <tt:VideoEncoderConfiguration token="video_enc_config1">
          <tt:Name>VideoEncoder1</tt:Name>
          <tt:UseCount>1</tt:UseCount>
          <tt:Encoding>H264</tt:Encoding>
          <tt:Resolution>
            <tt:Width>640</tt:Width>
            <tt:Height>360</tt:Height>
          </tt:Resolution>
          <tt:Quality>3</tt:Quality>
          <tt:RateControl>
            <tt:FrameRateLimit>20</tt:FrameRateLimit>
            <tt:EncodingInterval>1</tt:EncodingInterval>
            <tt:BitrateLimit>512</tt:BitrateLimit>
          </tt:RateControl>
          <tt:H264>
            <tt:GovLength>20</tt:GovLength>
            <tt:H264Profile>Main</tt:H264Profile>
          </tt:H264>
          <tt:Multicast>
            <tt:Address>
              <tt:Type>IPv4</tt:Type>
              <tt:IPv4Address>0.0.0.0</tt:IPv4Address>
            </tt:Address>
            <tt:Port>0</tt:Port>
            <tt:TTL>0</tt:TTL>
            <tt:AutoStart>false</tt:AutoStart>
          </tt:Multicast>
          <tt:SessionTimeout>PT60S</tt:SessionTimeout>
        </tt:VideoEncoderConfiguration>${AUDIO_CONFIG}
      </trt:Profiles>
XMLEOF
}

case "$ACTION" in
  GetProfiles)
    PROFILES=""
    [ "$RTSP_VIDEO0" = "on" ] && PROFILES=$(generate_profile_main)
    [ "$RTSP_VIDEO1" = "on" ] && PROFILES="${PROFILES}
$(generate_profile_sub)"
    # If no streams enabled, still return main profile as default
    [ -z "$PROFILES" ] && PROFILES=$(generate_profile_main)
    cat << XMLEOF
<?xml version="1.0" encoding="UTF-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope"
            xmlns:trt="http://www.onvif.org/ver10/media/wsdl"
            xmlns:tt="http://www.onvif.org/ver10/schema">
  <s:Body>
    <trt:GetProfilesResponse>
${PROFILES}
    </trt:GetProfilesResponse>
  </s:Body>
</s:Envelope>
XMLEOF
    ;;

  GetProfile)
    if [ "$PROFILE_TOKEN" = "sub_stream" ]; then
      PROFILE=$(generate_profile_sub)
    else
      PROFILE=$(generate_profile_main)
    fi
    cat << XMLEOF
<?xml version="1.0" encoding="UTF-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope"
            xmlns:trt="http://www.onvif.org/ver10/media/wsdl"
            xmlns:tt="http://www.onvif.org/ver10/schema">
  <s:Body>
    <trt:GetProfileResponse>
${PROFILE}
    </trt:GetProfileResponse>
  </s:Body>
</s:Envelope>
XMLEOF
    ;;

  GetStreamUri)
    # Map profile token to RTSP stream path
    STREAM_PATH="video0_unicast"
    [ "$PROFILE_TOKEN" = "sub_stream" ] && STREAM_PATH="video1_unicast"
    RTSP_URI="rtsp://${RTSP_AUTH_STR}${IP_ADDR}:${RTSP_PORT}/${STREAM_PATH}"
    cat << XMLEOF
<?xml version="1.0" encoding="UTF-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope"
            xmlns:trt="http://www.onvif.org/ver10/media/wsdl"
            xmlns:tt="http://www.onvif.org/ver10/schema">
  <s:Body>
    <trt:GetStreamUriResponse>
      <trt:MediaUri>
        <tt:Uri>${RTSP_URI}</tt:Uri>
        <tt:InvalidAfterConnect>false</tt:InvalidAfterConnect>
        <tt:InvalidAfterReboot>false</tt:InvalidAfterReboot>
        <tt:Timeout>PT60S</tt:Timeout>
      </trt:MediaUri>
    </trt:GetStreamUriResponse>
  </s:Body>
</s:Envelope>
XMLEOF
    ;;

  GetVideoSources)
    cat << XMLEOF
<?xml version="1.0" encoding="UTF-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope"
            xmlns:trt="http://www.onvif.org/ver10/media/wsdl"
            xmlns:tt="http://www.onvif.org/ver10/schema">
  <s:Body>
    <trt:GetVideoSourcesResponse>
      <trt:VideoSources token="video_src0">
        <tt:Framerate>20</tt:Framerate>
        <tt:Resolution>
          <tt:Width>1920</tt:Width>
          <tt:Height>1080</tt:Height>
        </tt:Resolution>
      </trt:VideoSources>
    </trt:GetVideoSourcesResponse>
  </s:Body>
</s:Envelope>
XMLEOF
    ;;

  GetVideoSourceConfigurations)
    cat << XMLEOF
<?xml version="1.0" encoding="UTF-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope"
            xmlns:trt="http://www.onvif.org/ver10/media/wsdl"
            xmlns:tt="http://www.onvif.org/ver10/schema">
  <s:Body>
    <trt:GetVideoSourceConfigurationsResponse>
      <trt:Configurations token="video_src_config0">
        <tt:Name>VideoSource0</tt:Name>
        <tt:UseCount>2</tt:UseCount>
        <tt:SourceToken>video_src0</tt:SourceToken>
        <tt:Bounds x="0" y="0" width="1920" height="1080" />
      </trt:Configurations>
    </trt:GetVideoSourceConfigurationsResponse>
  </s:Body>
</s:Envelope>
XMLEOF
    ;;

  GetSnapshotUri)
    SNAPSHOT_AUTH=""
    if [ "$RTSP_AUTH" = "on" ] && [ -n "$RTSP_USER" ] && [ -n "$RTSP_PASSWD" ]; then
      SNAPSHOT_AUTH="${RTSP_USER}:${RTSP_PASSWD}@"
    fi
    SNAPSHOT_URI="http://${SNAPSHOT_AUTH}${IP_ADDR}/cgi-bin/get_jpeg.cgi"
    cat << XMLEOF
<?xml version="1.0" encoding="UTF-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope"
            xmlns:trt="http://www.onvif.org/ver10/media/wsdl"
            xmlns:tt="http://www.onvif.org/ver10/schema">
  <s:Body>
    <trt:GetSnapshotUriResponse>
      <trt:MediaUri>
        <tt:Uri>${SNAPSHOT_URI}</tt:Uri>
        <tt:InvalidAfterConnect>false</tt:InvalidAfterConnect>
        <tt:InvalidAfterReboot>false</tt:InvalidAfterReboot>
        <tt:Timeout>PT60S</tt:Timeout>
      </trt:MediaUri>
    </trt:GetSnapshotUriResponse>
  </s:Body>
</s:Envelope>
XMLEOF
    ;;

  GetVideoEncoderConfigurations)
    cat << XMLEOF
<?xml version="1.0" encoding="UTF-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope"
            xmlns:trt="http://www.onvif.org/ver10/media/wsdl"
            xmlns:tt="http://www.onvif.org/ver10/schema">
  <s:Body>
    <trt:GetVideoEncoderConfigurationsResponse>
      <trt:Configurations token="video_enc_config0">
        <tt:Name>VideoEncoder0</tt:Name>
        <tt:UseCount>1</tt:UseCount>
        <tt:Encoding>H264</tt:Encoding>
        <tt:Resolution>
          <tt:Width>1920</tt:Width>
          <tt:Height>1080</tt:Height>
        </tt:Resolution>
        <tt:Quality>5</tt:Quality>
        <tt:RateControl>
          <tt:FrameRateLimit>20</tt:FrameRateLimit>
          <tt:EncodingInterval>1</tt:EncodingInterval>
          <tt:BitrateLimit>2048</tt:BitrateLimit>
        </tt:RateControl>
        <tt:H264>
          <tt:GovLength>20</tt:GovLength>
          <tt:H264Profile>Main</tt:H264Profile>
        </tt:H264>
        <tt:Multicast>
          <tt:Address>
            <tt:Type>IPv4</tt:Type>
            <tt:IPv4Address>0.0.0.0</tt:IPv4Address>
          </tt:Address>
          <tt:Port>0</tt:Port>
          <tt:TTL>0</tt:TTL>
          <tt:AutoStart>false</tt:AutoStart>
        </tt:Multicast>
        <tt:SessionTimeout>PT60S</tt:SessionTimeout>
      </trt:Configurations>
      <trt:Configurations token="video_enc_config1">
        <tt:Name>VideoEncoder1</tt:Name>
        <tt:UseCount>1</tt:UseCount>
        <tt:Encoding>H264</tt:Encoding>
        <tt:Resolution>
          <tt:Width>640</tt:Width>
          <tt:Height>360</tt:Height>
        </tt:Resolution>
        <tt:Quality>3</tt:Quality>
        <tt:RateControl>
          <tt:FrameRateLimit>20</tt:FrameRateLimit>
          <tt:EncodingInterval>1</tt:EncodingInterval>
          <tt:BitrateLimit>512</tt:BitrateLimit>
        </tt:RateControl>
        <tt:H264>
          <tt:GovLength>20</tt:GovLength>
          <tt:H264Profile>Main</tt:H264Profile>
        </tt:H264>
        <tt:Multicast>
          <tt:Address>
            <tt:Type>IPv4</tt:Type>
            <tt:IPv4Address>0.0.0.0</tt:IPv4Address>
          </tt:Address>
          <tt:Port>0</tt:Port>
          <tt:TTL>0</tt:TTL>
          <tt:AutoStart>false</tt:AutoStart>
        </tt:Multicast>
        <tt:SessionTimeout>PT60S</tt:SessionTimeout>
      </trt:Configurations>
    </trt:GetVideoEncoderConfigurationsResponse>
  </s:Body>
</s:Envelope>
XMLEOF
    ;;

  GetAudioSources)
    cat << XMLEOF
<?xml version="1.0" encoding="UTF-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope"
            xmlns:trt="http://www.onvif.org/ver10/media/wsdl"
            xmlns:tt="http://www.onvif.org/ver10/schema">
  <s:Body>
    <trt:GetAudioSourcesResponse>
      <trt:AudioSources token="audio_src0">
        <tt:Channels>1</tt:Channels>
      </trt:AudioSources>
    </trt:GetAudioSourcesResponse>
  </s:Body>
</s:Envelope>
XMLEOF
    ;;

  *)
    cat << XMLEOF
<?xml version="1.0" encoding="UTF-8"?>
<s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope"
            xmlns:trt="http://www.onvif.org/ver10/media/wsdl">
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
