#!/bin/bash
# Hollywood "portscan" widget: show the probes of a port scan, with nmap. The widget scans
# 200 ports of the local host (127.0.0.1) only, 20 ports a second, and prints each probe
# and its answer. It then waits 2 seconds and scans another range of ports. Nothing in
# the container listens on those ports, so every probe is refused.
#
# This widget was written for hollywood-directors-cut and is licensed under the MIT
# license. It follows the pattern of the widgets in Hollywood. See LICENSE and
# THIRD-PARTY.md.

command -v nmap >/dev/null 2>&1 || exit 1

restore_terminal() {
	printf '\033[?25h\033[0m'
}

trap "pkill -f -9 lib/hollywood/ >/dev/null 2>&1; exit" INT
trap 'kill "$pid" 2>/dev/null; wait "$pid" 2>/dev/null; restore_terminal; exit 0' TERM HUP

while true; do
	first=$((1 + (RANDOM * 2 + RANDOM % 2) % 65000))
	clear
	# -sT scans with normal connections, so it needs no special privileges. --packet-trace
	# prints a line for each probe. -n skips the name lookups.
	nmap -sT -n --packet-trace --max-rate 20 -p "$first-$((first + 199))" 127.0.0.1 &
	pid=$!
	wait "$pid"
	sleep 2
done
