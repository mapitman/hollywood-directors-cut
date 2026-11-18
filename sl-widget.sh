#!/bin/bash
# Hollywood "sl" widget: show sl, a steam locomotive that drives across the screen. sl
# stops after one trip, so the widget starts it again with a random style (normal, a
# little train, an accident, or a flying train) after a short pause.
#
# This widget was written for hollywood-directors-cut and is licensed under the MIT
# license. It follows the pattern of the widgets in Hollywood. See LICENSE and
# THIRD-PARTY.md.

# Debian installs the program in /usr/games, which is not in PATH.
[ -x /usr/games/sl ] || exit 1

restore_terminal() {
	printf '\033[?1049l\033[?25h\033[0m'
}

trap "pkill -f -9 lib/hollywood/ >/dev/null 2>&1; exit" INT
trap 'kill "$pid" 2>/dev/null; wait "$pid" 2>/dev/null; restore_terminal; exit 0' TERM HUP

styles=("" -l -a -F)
while true; do
	# -e lets ctrl-c stop sl. "<&0" keeps the terminal as stdin.
	/usr/games/sl -e ${styles[RANDOM % ${#styles[@]}]} <&0 &
	pid=$!
	wait "$pid"
	sleep 2
done
