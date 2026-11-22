#!/bin/bash
# Stand-in for the tree command in the image: color the tree with lolcat.
#
# The Hollywood tree widget runs "tree" and prints its plain text. This script is
# installed as /usr/local/bin/tree, which comes before /usr/bin in PATH, so the widget
# gets a rainbow. The output goes through lolcat only when it goes to a terminal.
#
#   HOLLYWOOD_RAINBOW  0 runs the real tree (default 1)

if [ "${HOLLYWOOD_RAINBOW:-1}" = 0 ] || [ ! -t 1 ] || [ ! -x /usr/games/lolcat ]; then
	exec /usr/bin/tree "$@"
fi
/usr/bin/tree "$@" | /usr/games/lolcat -f
