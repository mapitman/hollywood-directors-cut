#!/bin/bash
# Hollywood "sshart" widget: draw the random art of SSH keys as the "drunken bishop"
# walks across the board.
#
# This script replaces the widget that comes with Hollywood, which runs ssh-keygen,
# prints its text and its small picture in the top corner, and clears the pane every
# few seconds. Here sshart-render.py draws as many boards as fit in the pane. Each board
# types a command and a fingerprint, then the bishop walks step by step and the cells
# fill in with color, and then a new key starts.
#
# Based on the widget of the same name in Hollywood
# (https://github.com/dustinkirkland/hollywood), Copyright 2014 Dustin Kirkland,
# licensed under the Apache License 2.0. The changes are by the hollywood-directors-cut
# project and are licensed under the MIT license. See LICENSE and THIRD-PARTY.md.

command -v python3 >/dev/null 2>&1 || exit 1
trap "pkill -f -9 lib/hollywood/ >/dev/null 2>&1; exit" INT

# Run the renderer as a child that this script waits for, so the TERM trap runs at once.
child=
trap 'kill -TERM "$child" 2>/dev/null; wait "$child" 2>/dev/null; printf "\033[0m\033[?25h"; exit 0' TERM HUP

while true; do
	started=$SECONDS
	/usr/local/bin/hollywood-sshart-render &
	child=$!
	wait "$child"
	status=$?
	# Status 3 means the pane changed size: start again at the new size. Wait a second
	# when a run ends at once, so a failure cannot use up the CPU.
	[ "$status" = 3 ] && [ $((SECONDS - started)) -ge 1 ] || sleep 1
done
