#!/bin/bash
# Hollywood "lolcat" widget: show text in animated rainbow colors, with lolcat. The widget
# colors the first lines of a random file from /etc, /usr/share/doc or /var/log, waits,
# and does it again with another file.
#
# This widget was written for hollywood-directors-cut and is licensed under the MIT
# license. It follows the pattern of the widgets in Hollywood. See LICENSE and
# THIRD-PARTY.md.

# Debian installs the program in /usr/games, which is not in PATH.
[ -x /usr/games/lolcat ] || exit 1

restore_terminal() {
	printf '\033[?25h\033[0m'
}

trap "pkill -f -9 lib/hollywood/ >/dev/null 2>&1; exit" INT
trap 'kill "$pid" 2>/dev/null; wait "$pid" 2>/dev/null; restore_terminal; exit 0' TERM HUP

while true; do
	rows=$(tput lines)
	cols=$(tput cols)
	file=$(find /etc /usr/share/doc /var/log -type f -size +1k -size -64k -readable 2>/dev/null | sort -R | head -n1)
	# -a animates the colors line by line, -d is the number of animation steps for each line
	# and -s is the speed. Cut each line to the pane width so that no line wraps. The pipe
	# is the input of lolcat, so do not redirect its input from the terminal.
	{ [ -n "$file" ] && tr -d '\000-\010\013-\037' <"$file" | grep -a -v '^[[:space:]]*$' | cut -c "1-$((cols - 1))" | head -n "$((rows - 1))"; } \
		| /usr/games/lolcat -a -d 4 -s 40 &
	pid=$!
	wait "$pid"
	sleep 3
done
