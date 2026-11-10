#!/bin/sh
# Quick check from KUAL: can the Kindle download the image from the Pi?
# Shows the result as a line of text on screen without leaving the Kindle UI.
[ -t 1 ] || exec >/dev/null 2>&1

DIR="$(cd "$(dirname "$0")" && pwd)"
. "$DIR/settings.sh"

if curl -sf -m 15 -o /tmp/kindle-dashboard-test.png "$PI_URL" && [ -s /tmp/kindle-dashboard-test.png ]; then
    SIZE=$(wc -c < /tmp/kindle-dashboard-test.png)
    eips 1 37 "OK: got dashboard.png from $PI_IP ($SIZE bytes)        "
else
    eips 1 37 "FAILED: can't reach $PI_URL                "
fi
rm -f /tmp/kindle-dashboard-test.png
