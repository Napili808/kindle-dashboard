#!/bin/sh
# Stop the dashboard loop and bring the normal Kindle UI back.
[ -t 1 ] || exec >/dev/null 2>&1

if [ -f /tmp/kindle-dashboard.pid ]; then
    kill "$(cat /tmp/kindle-dashboard.pid)" 2>/dev/null
    rm -f /tmp/kindle-dashboard.pid
fi
pkill -f kindle-dashboard/dashboard.sh 2>/dev/null

lipc-set-prop com.lab126.powerd preventScreenSaver 0
eips -c
/etc/init.d/framework start 2>/dev/null || {
    start lab126_gui 2>/dev/null || start framework 2>/dev/null
}
