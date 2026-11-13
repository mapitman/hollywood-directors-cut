#!/bin/bash
# Hollywood "mtr" widget: show mtr, a live trace of the route to a host with the delay at each hop.
#
#   HOLLYWOOD_MTR_HOSTS  hosts to trace, separated by spaces (default: a list of well-known sites).
#                        The widget picks one at random each time it starts.
#
# This widget was written for hollywood-directors-cut and is licensed under the MIT
# license. It follows the pattern of the widgets in Hollywood. See LICENSE and
# THIRD-PARTY.md.

command -v mtr >/dev/null 2>&1 || exit 1

hosts=${HOLLYWOOD_MTR_HOSTS:-google.com cloudflare.com github.com wikipedia.org amazon.com 1.1.1.1 8.8.8.8}
# Leave $hosts unquoted on purpose, so each host is a separate word.
# shellcheck disable=SC2086
host=$(printf '%s\n' $hosts | sort -R | head -n1)

# mtr does not clean up when it is stopped with TERM, which is how the widget guard
# stops a widget. Put the terminal back the way it was: leave the alternate screen,
# show the cursor, reset the colors.
restore_terminal() {
	printf '\033[?1049l\033[?25h\033[0m'
}

trap "pkill -f -9 lib/hollywood/ >/dev/null 2>&1; exit" INT
trap 'kill "$pid" 2>/dev/null; wait "$pid" 2>/dev/null; restore_terminal; exit 0' TERM HUP

# "<&0" keeps the terminal as stdin; bash would otherwise use /dev/null.
mtr --curses "$host" <&0 &
pid=$!
wait "$pid"
