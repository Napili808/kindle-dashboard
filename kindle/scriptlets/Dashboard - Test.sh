#!/bin/sh
# Name: Dashboard - Test
# Author: Napili808
#
# Kindle scriptlet: checks that the Kindle can download the dashboard image
# from the Pi, and prints OK or FAILED near the bottom of the screen.
# Turn Wi-Fi on first. Doesn't change anything.

# ---------- EDIT THIS: same IP as in "Dashboard - Start.sh" ----------
PI_IP="192.168.1.50"
# ----------------------------------------------------------------------

PI_URL="http://${PI_IP}:8080/dashboard.png"
OUT=/tmp/kindle-dashboard-test.png

if curl -sf -m 15 -o "$OUT" "$PI_URL" && [ -s "$OUT" ]; then
    eips 1 37 "OK: got dashboard from $PI_IP ($(wc -c < "$OUT") bytes)       "
else
    eips 1 37 "FAILED: can't reach $PI_URL               "
fi
rm -f "$OUT"
exit 0
