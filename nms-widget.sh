#!/bin/bash
# Hollywood "nms" widget: show text that decrypts on the screen, with nms (no-more-secrets).
# The effect comes from the film Sneakers. The widget decrypts the text of a random file
# from /etc, /usr/share/doc or /var/log, then waits and does it again with another file.
#
#   HOLLYWOOD_NMS_COLOR  color of the decrypted text: white, yellow, black, magenta, blue,
#                        green, or red (default green)
#
# This widget was written for hollywood-directors-cut and is licensed under the MIT
# license. It follows the pattern of the widgets in Hollywood. See LICENSE and
# THIRD-PARTY.md.

command -v nms >/dev/null 2>&1 || exit 1

color=${HOLLYWOOD_NMS_COLOR:-green}

# nms hides the cursor while it runs and does not restore it when it is stopped with TERM,
# which is how the widget guard stops a widget.
restore_terminal() {
	printf '\033[?25h\033[0m'
}

trap "pkill -f -9 lib/hollywood/ >/dev/null 2>&1; exit" INT
trap 'kill "$pid" 2>/dev/null; wait "$pid" 2>/dev/null; restore_terminal; exit 0' TERM HUP

while true; do
	rows=$(tput lines)
	cols=$(tput cols)
	file=$(find /etc /usr/share/doc /var/log -type f -size +1k -size -64k -readable 2>/dev/null | sort -R | head -n1)
	# -a decrypts without waiting for a key. -c clears the screen first. The pipe is the
	# input of nms, so do not redirect its input from the terminal.
	# Cut each line to the pane width, so no line wraps and breaks the effect.
	{ [ -n "$file" ] && tr -d '\000-\010\013-\037' <"$file" | grep -a -v '^[[:space:]]*$' | cut -c "1-$((cols - 1))" | head -n "$((rows - 1))"; } \
		| nms -a -c -f "$color" &
	pid=$!
	wait "$pid"
	sleep 3
done
