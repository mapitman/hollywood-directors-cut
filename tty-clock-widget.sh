#!/bin/bash
# Hollywood "tty-clock" widget: show tty-clock, a large digital clock with seconds.
#
#   HOLLYWOOD_CLOCK_COLOR  color of the clock, 0 to 7 (default: a random color at each start)
#
# This widget was written for hollywood-directors-cut and is licensed under the MIT
# license. It follows the pattern of the widgets in Hollywood. See LICENSE and
# THIRD-PARTY.md.

command -v tty-clock >/dev/null 2>&1 || exit 1

color=${HOLLYWOOD_CLOCK_COLOR:-$((RANDOM % 7 + 1))}
case "$color" in [0-7]) ;; *) color=2 ;; esac

# tty-clock does not clean up when it is stopped with TERM, which is how the widget
# guard stops a widget. Put the terminal back the way it was: leave the alternate
# screen, show the cursor, reset the colors.
restore_terminal() {
	printf '\033[?1049l\033[?25h\033[0m'
}

trap "pkill -f -9 lib/hollywood/ >/dev/null 2>&1; exit" INT
trap 'kill "$pid" 2>/dev/null; wait "$pid" 2>/dev/null; restore_terminal; exit 0' TERM HUP

# -s shows seconds, -c centers the clock, -b uses bold colors, -B blinks the colon and
# -n keeps the clock running when a key is pressed.
# "<&0" keeps the terminal as stdin; bash would otherwise use /dev/null.
tty-clock -s -c -b -B -n -C "$color" <&0 &
pid=$!
wait "$pid"
