#!/bin/bash
# Stand-in for the ccze command in the image: color text with lolcat.
#
# Several Hollywood widgets (apg, errno, hexdump, logs, man and stat) pipe their text
# through "ccze -A" to give it colors. This script is installed as /usr/local/bin/ccze,
# which comes before /usr/bin in PATH, so those widgets get a rainbow from lolcat
# instead, and no widget script changes. The ccze options are ignored.
#
#   HOLLYWOOD_RAINBOW  0 runs the real ccze (default 1)

if [ "${HOLLYWOOD_RAINBOW:-1}" = 0 ] || [ ! -x /usr/games/lolcat ]; then
	exec /usr/bin/ccze "$@"
fi
# -f colors the text even though it may go to a pipe, not a terminal.
exec /usr/games/lolcat -f
