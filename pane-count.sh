#!/bin/bash
# Print the number of panes for the next Hollywood layout.
#
# The entrypoint runs this script at the start, and the Hollywood launcher runs it
# again for every layout rebuild. The maximum is the number of terminal cells
# divided by HOLLYWOOD_CELLS_PER_PANE, limited to two panes per CPU and to the
# number of widgets. The script picks a random count from the minimum up to that
# maximum, unless HOLLYWOOD_RANDOM_PANES is 0. The minimum is HOLLYWOOD_MIN_PANES
# (default 3). It wins over the maximum, so a small terminal or a machine with one
# CPU still gets the minimum.
#
# With a tmux session name as the first argument, the script measures the tmux
# window. Without it, the script measures the terminal.

CELLS_PER_PANE=${HOLLYWOOD_CELLS_PER_PANE:-1400}
MIN_PANES=${HOLLYWOOD_MIN_PANES:-3}
case "$MIN_PANES" in '' | *[!0-9]*) MIN_PANES=3 ;; esac
# The launcher always creates at least 2 panes, even with -s 1.
[ "$MIN_PANES" -lt 2 ] && MIN_PANES=2
WIDGET_DIR=/usr/lib/hollywood

terminal_cells() {
	local rows cols
	if [ -n "$1" ]; then
		read -r cols rows < <(tmux display -p -t "$1" '#{window_width} #{window_height}' 2>/dev/null)
	fi
	if [ -z "$rows" ]; then
		read -r rows cols < <(stty size 2>/dev/null)
	fi
	rows=${rows:-${LINES:-24}}
	cols=${cols:-${COLUMNS:-80}}
	echo $((rows * cols))
}

panes=$(($(terminal_cells "$1") / CELLS_PER_PANE))
cpu_cap=$(($(nproc 2>/dev/null || echo 2) * 2))
widget_cap=$(ls "$WIDGET_DIR" | wc -l)
[ "$panes" -gt "$cpu_cap" ] && panes=$cpu_cap
[ "$panes" -gt "$widget_cap" ] && panes=$widget_cap
[ "$panes" -lt "$MIN_PANES" ] && panes=$MIN_PANES
if [ "${HOLLYWOOD_RANDOM_PANES:-1}" != 0 ]; then
	panes=$((MIN_PANES + RANDOM % (panes - MIN_PANES + 1)))
fi
echo "$panes"
