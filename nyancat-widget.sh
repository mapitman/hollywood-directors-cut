#!/bin/bash
# Hollywood "nyancat" widget: show nyancat, the rainbow cat that flies across the screen.
#
# This widget was written for hollywood-directors-cut and is licensed under the MIT
# license. It follows the pattern of the widgets in Hollywood. See LICENSE and
# THIRD-PARTY.md.

# Debian installs the program in /usr/games, which is not in PATH.
[ -x /usr/bin/nyancat ] || exit 1

# The program may not clean up when it is stopped with TERM, which is how the widget
# guard stops a widget. Put the terminal back the way it was: leave the alternate
# screen, show the cursor, reset the colors.
restore_terminal() {
	printf '\033[?1049l\033[?25h\033[0m'
}

trap "pkill -f -9 lib/hollywood/ >/dev/null 2>&1; exit" INT
trap 'kill "$pid" 2>/dev/null; wait "$pid" 2>/dev/null; restore_terminal; exit 0' TERM HUP

# "<&0" keeps the terminal as stdin; bash would otherwise use /dev/null.
/usr/bin/nyancat -n -s <&0 &
pid=$!
wait "$pid"
