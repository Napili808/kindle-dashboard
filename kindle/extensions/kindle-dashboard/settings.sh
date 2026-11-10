# Edit this one line: your Pi's IP address (run `hostname -I` on the Pi).
PI_IP="192.168.1.50"

# Usually leave these alone.
PI_URL="http://${PI_IP}:8080/dashboard.png"
REFRESH_SECONDS=900        # 15 minutes, matches the Pi's rebuild timer
FULL_FLASH_EVERY=4         # full black/white refresh every Nth update to clear ghosting
