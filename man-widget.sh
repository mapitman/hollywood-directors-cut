#!/bin/bash
# Hollywood "man" widget: show the manual pages, one after another.
#
# This script replaces the widget that comes with Hollywood, which prints a whole page
# at once, so the pane scrolls so fast that nobody can read it. Here each page prints one
# line at a time, with a short pause after every line.
#
#   HOLLYWOOD_MAN_DELAY  seconds to wait after each line (default 0.04; 0 prints a page
#                        at once, as Hollywood does)
#
# Based on the widget of the same name in Hollywood
# (https://github.com/dustinkirkland/hollywood), Copyright 2014 Dustin Kirkland,
# licensed under the Apache License 2.0. The changes are by the hollywood-directors-cut
# project and are licensed under the MIT license. See LICENSE and THIRD-PARTY.md.

command -v man >/dev/null 2>&1 || exit 1
command -v ccze >/dev/null 2>&1 || exit 1
trap "pkill -f -9 lib/hollywood/ >/dev/null 2>&1; exit" INT

delay=${HOLLYWOOD_MAN_DELAY:-0.04}
case "$delay" in '' | *[!0-9.]*) delay=0.04 ;; esac

while true; do
	FILES=$(ls /usr/share/man/man1/ | sort -R | sed "s/\.1\.gz.*$//" | head -n 4096)
	for f in $FILES; do
		man "$f" | ccze -A | while IFS= read -r line; do
			printf '%s\n' "$line"
			sleep "$delay"
		done
		sleep 1
	done
done
