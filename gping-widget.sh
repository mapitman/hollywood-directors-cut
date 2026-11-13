#!/bin/bash
# Hollywood "gping" widget: show gping, a graph of the ping time to several well-known sites.
#
#   HOLLYWOOD_GPING_HOSTS  hosts to ping, separated by spaces (default: a list of well-known sites)
#
# This widget was written for hollywood-directors-cut and is licensed under the MIT
# license. It follows the pattern of the widgets in Hollywood. See LICENSE and
# THIRD-PARTY.md.

command -v gping >/dev/null 2>&1 || exit 1

hosts=${HOLLYWOOD_GPING_HOSTS:-google.com cloudflare.com github.com wikipedia.org amazon.com 1.1.1.1 8.8.8.8}

# gping does not clean up when it is stopped with TERM, which is how the widget guard
# stops a widget. Put the terminal back the way it was: leave the alternate screen,
# show the cursor, reset the colors.
restore_terminal() {
	printf '\033[?1049l\033[?25h\033[0m'
}

trap "pkill -f -9 lib/hollywood/ >/dev/null 2>&1; exit" INT
trap 'kill "$pid" 2>/dev/null; wait "$pid" 2>/dev/null; restore_terminal; exit 0' TERM HUP

# Leave $hosts unquoted on purpose, so each host is a separate argument.
# "<&0" keeps the terminal as stdin; bash would otherwise use /dev/null.
# shellcheck disable=SC2086
gping $hosts <&0 &
pid=$!
wait "$pid"
