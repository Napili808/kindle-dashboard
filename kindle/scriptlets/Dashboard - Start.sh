#!/bin/sh
# Name: Dashboard - Start
# Author: Napili808
#
# Kindle scriptlet: copy this file into the Kindle's documents folder, then tap
# it in your library. It hides the normal Kindle screen and shows the dashboard
# image from the Raspberry Pi, refreshing at :02 and :32 past each hour (a couple
# of minutes after the Pi rebuilds the image at :00 and :30).
#
# To stop: hold the power button ~40 seconds until the Kindle restarts.
# Keep the Kindle plugged in; it stays awake with Wi-Fi on.

# ---------- EDIT THIS: your Pi's IP address (run `hostname -I` on the Pi) ----------
PI_IP="192.168.1.50"
# -------------------------------------------------------------------------------------

REFRESH_SECONDS=1800      # 30 minutes, matches the Pi timer
OFFSET_SECONDS=120        # update 2 minutes after the Pi's :00 / :30 rebuild
FULL_FLASH_EVERY=4
PI_URL="http://${PI_IP}:8080/dashboard.png"
LOOP=/tmp/kindle-dashboard-loop.sh

# Don't start a second copy if it's already running.
if [ -f /tmp/kindle-dashboard.pid ] && kill -0 "$(cat /tmp/kindle-dashboard.pid)" 2>/dev/null; then
    exit 0
fi

# Write the refresh loop to /tmp and run it detached, so it keeps going after
# this scriptlet returns. (Firmware notes for 5.19.x on the Paperwhite 5 come
# from TRMNL's MIT-licensed client: github.com/usetrmnl/trmnl-kindle)
cat > "$LOOP" <<EOF
#!/bin/sh
echo \$\$ > /tmp/kindle-dashboard.pid
IMG=/tmp/kindle-dashboard.png

# Hide the normal Kindle UI (5.19.x runs it as upstart jobs).
/etc/init.d/framework stop 2>/dev/null || {
    stop framework 2>/dev/null || initctl stop framework 2>/dev/null
    stop lab126_gui 2>/dev/null
}
initctl stop webreader 2>/dev/null
lipc-set-prop com.lab126.powerd preventScreenSaver 1
lipc-set-prop com.lab126.cmd wirelessEnable 1
sleep 5

i=0
while true; do
    if curl -sf -m 30 -o "\$IMG.new" "$PI_URL" && [ -s "\$IMG.new" ]; then
        mv "\$IMG.new" "\$IMG"
        if [ \$((i % $FULL_FLASH_EVERY)) -eq 0 ]; then
            eips -c
            sleep 1
            eips -f -g "\$IMG"
        else
            eips -g "\$IMG"
        fi
        i=\$((i + 1))
        # Sleep until the next :02 or :32. Epoch math works because Hawaii's
        # offset from UTC is a whole number of hours.
        NOW=\$(date +%s)
        WAIT=\$(( ($OFFSET_SECONDS - NOW % $REFRESH_SECONDS + $REFRESH_SECONDS) % $REFRESH_SECONDS ))
        [ "\$WAIT" -lt 30 ] && WAIT=\$((WAIT + $REFRESH_SECONDS))
        sleep "\$WAIT"
    else
        eips 1 38 "Can't reach Pi at $PI_IP - retrying in 1 min   "
        lipc-set-prop com.lab126.cmd wirelessEnable 1
        sleep 60
    fi
done
EOF
chmod +x "$LOOP"

if command -v setsid >/dev/null 2>&1; then
    setsid sh "$LOOP" >/dev/null 2>&1 </dev/null &
else
    nohup sh "$LOOP" >/dev/null 2>&1 </dev/null &
fi
exit 0
