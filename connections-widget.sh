#!/bin/bash
# Hollywood "connections" widget: show a live table of the network connections of the
# container, with ss and watch. An idle container has no connections, so the widget opens
# its own: every 1.5 seconds it opens a TCP connection to port 443 of a random host, and
# it keeps at most 8 connections open. The oldest connection closes first.
#
#   HOLLYWOOD_CONNECTIONS_HOSTS  hosts to connect to, separated by spaces
#                                (default: the same list as the gping widget)
#
# This widget was written for hollywood-directors-cut and is licensed under the MIT
# license. It follows the pattern of the widgets in Hollywood. See LICENSE and
# THIRD-PARTY.md.

command -v ss >/dev/null 2>&1 && command -v watch >/dev/null 2>&1 || exit 1

hosts=${HOLLYWOOD_CONNECTIONS_HOSTS:-google.com cloudflare.com github.com wikipedia.org amazon.com 1.1.1.1 8.8.8.8}

# Hold the connections in one process, so that stopping this process closes them all.
open_connections() {
	local -a fds=()
	local host fd old
	while true; do
		# Leave $hosts unquoted on purpose, so each host is a separate word.
		# shellcheck disable=SC2086
		host=$(printf '%s\n' $hosts | sort -R | head -n1)
		if { exec {fd}<>"/dev/tcp/$host/443"; } 2>/dev/null; then
			fds+=("$fd")
		fi
		if [ "${#fds[@]}" -gt 8 ]; then
			old=${fds[0]}
			exec {old}>&-
			fds=("${fds[@]:1}")
		fi
		sleep 1.5
	done
}

# watch does not clean up when it is stopped with TERM, which is how the widget guard
# stops a widget. Put the terminal back the way it was: leave the alternate screen,
# show the cursor, reset the colors.
restore_terminal() {
	printf '\033[?1049l\033[?25h\033[0m'
}

open_connections &
opener=$!

trap "kill $opener 2>/dev/null; pkill -f -9 lib/hollywood/ >/dev/null 2>&1; exit" INT
trap 'kill "$opener" "$pid" 2>/dev/null; wait "$pid" 2>/dev/null; restore_terminal; exit 0' TERM HUP

# -t hides the title, -d highlights what changed between two updates.
# "<&0" keeps the terminal as stdin; bash would otherwise use /dev/null.
watch -t -d -n 1 ss -tn <&0 &
pid=$!
wait "$pid"
kill "$opener" 2>/dev/null
