#!/bin/sh
# Runs ON THE KINDLE, launched from KUAL. Downloads the dashboard image from
# the Pi and shows it full-screen, refreshing on a timer.
#
# Assumes the Kindle stays plugged in (Wi-Fi stays on, no deep sleep).
# Firmware notes for Paperwhite 5 on 5.19.x borrowed from TRMNL's MIT-licensed
# Kindle client: github.com/usetrmnl/trmnl-kindle

# KUAL gives us a stdout nobody reads; writing to it can hang the script.
[ -t 1 ] || exec >/dev/null 2>&1

DIR="$(cd "$(dirname "$0")" && pwd)"
. "$DIR/settings.sh"
IMG=/tmp/kindle-dashboard.png
echo $$ > /tmp/kindle-dashboard.pid

# Hide the normal Kindle UI so its status bar isn't drawn over the dashboard.
# Older firmware uses an init.d script; 5.19.x runs the UI as upstart jobs.
/etc/init.d/framework stop 2>/dev/null || {
    stop framework 2>/dev/null || initctl stop framework 2>/dev/null
    stop lab126_gui 2>/dev/null
}
initctl stop webreader 2>/dev/null
lipc-set-prop com.lab126.powerd preventScreenSaver 1
lipc-set-prop com.lab126.cmd wirelessEnable 1

i=0
while true; do
    if curl -sf -m 30 -o "$IMG.new" "$PI_URL" && [ -s "$IMG.new" ]; then
        mv "$IMG.new" "$IMG"
        if [ $((i % FULL_FLASH_EVERY)) -eq 0 ]; then
            eips -c
            sleep 1
            eips -f -g "$IMG"
        else
            eips -g "$IMG"
        fi
        i=$((i + 1))
        sleep "$REFRESH_SECONDS"
    else
        # Leave the last good image up; print a small note at the bottom and retry soon.
        eips 1 38 "Can't reach Pi at $PI_IP - retrying in 1 min   "
        lipc-set-prop com.lab126.cmd wirelessEnable 1
        sleep 60
    fi
done
