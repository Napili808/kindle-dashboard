#!/bin/sh
# Runs ON THE KINDLE (after it's jailbroken). Downloads the dashboard image
# from the Pi and shows it full-screen, refreshing every 15 minutes.
#
# EXPERIMENTAL: not yet tested on Minh's Paperwhite 5. Stop it by holding the
# power button until the Kindle restarts.

PI_URL="http://192.168.1.50:8080/dashboard.png"   # <-- change to your Pi's IP
REFRESH_SECONDS=900
IMG=/tmp/dashboard.png

# Keep the Kindle awake and stop the normal reading UI from drawing over us.
lipc-set-prop com.lab126.powerd preventScreenSaver 1
stop framework 2>/dev/null || true

i=0
while true; do
    if wget -q -O "$IMG.new" "$PI_URL"; then
        mv "$IMG.new" "$IMG"
        # Full black/white flash every 4th refresh clears e-ink ghosting.
        if [ $((i % 4)) -eq 0 ]; then
            eips -c
            eips -f -g "$IMG"
        else
            eips -g "$IMG"
        fi
    else
        eips 1 1 "Can't reach the Pi - retrying"
    fi
    i=$((i + 1))
    sleep "$REFRESH_SECONDS"
done
