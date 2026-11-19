#!/bin/bash
# Hollywood "hexyl" widget: show a colored hex dump, with hexyl. The widget dumps one
# screen of bytes from a random place in a random program from /usr/bin, waits 2 seconds
# and does it again with another program. hexyl always prints 16 bytes in a row, which is
# 78 columns wide, so the widget needs a pane that wide.
#
# This widget was written for hollywood-directors-cut and is licensed under the MIT
# license. It follows the pattern of the widgets in Hollywood. See LICENSE and
# THIRD-PARTY.md.

command -v hexyl >/dev/null 2>&1 || exit 1

restore_terminal() {
	printf '\033[?25h\033[0m'
}

trap "pkill -f -9 lib/hollywood/ >/dev/null 2>&1; exit" INT
trap 'kill "$pid" 2>/dev/null; wait "$pid" 2>/dev/null; restore_terminal; exit 0' TERM HUP

while true; do
	rows=$(tput lines)
	file=$(find /usr/bin -type f -size +64k -readable 2>/dev/null | sort -R | head -n1)
	size=$(stat -c %s "$file" 2>/dev/null || echo 0)
	# Read enough bytes for the rows of the pane: 16 bytes in each row.
	bytes=$((rows * 16))
	[ "$size" -gt "$bytes" ] || { sleep 1; continue; }
	# Start between 10% and 60% of the file, where most programs keep their code.
	skip=$(((size / 10 + (RANDOM * 32768 + RANDOM) % (size / 2)) / 16 * 16))
	[ "$skip" -gt $((size - bytes)) ] && skip=$((size - bytes))
	clear
	# Cut the last line, so the pane does not scroll.
	hexyl -v -n "$bytes" -s "$skip" "$file" | head -n "$((rows - 1))" &
	pid=$!
	wait "$pid"
	sleep 2
done
