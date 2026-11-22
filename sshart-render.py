#!/usr/bin/env python3
"""Animate the "random art" picture of an SSH key, as OpenSSH draws it.

OpenSSH draws the picture with the "drunken bishop" algorithm. A bishop starts in the
middle of a board of 17 x 9 cells. It takes one diagonal step for every 2 bits of the
key's fingerprint hash, and it stays on the board at the walls. Each cell counts the
visits, and the count picks the character from " .o+=*BOX@%&#/^". The start cell shows
S and the end cell shows E.

This script runs the walk with a random hash and draws it step by step. Each board
types a fake ssh-keygen command and a fingerprint, then the bishop walks while the
cells fill in, colored from green (a few visits) through yellow to red (many visits).
The pane holds as many boards as fit, and each board runs on its own schedule.

The script exits with status 3 when the terminal size changes, so the caller can start
it again.

Usage: sshart-render.py
"""
import base64
import os
import random
import signal
import sys
import time

OUT = sys.stdout.fileno()
FIELD_W, FIELD_H = 17, 9
SYMBOLS = " .o+=*BOX@%&#/^SE"
MAX_COUNT = len(SYMBOLS) - 3  # a cell counts up to this, then stays
START, END = len(SYMBOLS) - 2, len(SYMBOLS) - 1
TITLE = "ED25519 256"
COMMAND = "$ ssh-keygen -lv"
WIDTH = FIELD_W + 2  # the board with its borders
GAP = 2
TICKS_PER_SECOND = 30
HOLD_TICKS = 2 * TICKS_PER_SECOND
TYPE_FINGERPRINT = 2  # characters per tick
RESET = "\x1b[0m"
# Color for a count of 1 to 14, from dim green to yellow to red.
PALETTE = (22, 28, 34, 40, 46, 82, 118, 154, 190, 226, 220, 208, 202, 196)


def walk(digest):
    """Return the position of the bishop after each of its steps."""
    x, y = FIELD_W // 2, FIELD_H // 2
    path = []
    for byte in digest:
        for _ in range(4):
            x = min(FIELD_W - 1, max(0, x + (1 if byte & 1 else -1)))
            y = min(FIELD_H - 1, max(0, y + (1 if byte & 2 else -1)))
            byte >>= 2
            path.append((x, y))
    return path


def border(title):
    left = (FIELD_W - len(title) - 2) // 2
    return "+" + "-" * left + "[" + title + "]" + "-" * (FIELD_W - len(title) - 2 - left) + "+"


def fingerprint_lines(text, count):
    """Split the first COUNT characters of TEXT into lines that fit the board."""
    text = text[:count]
    return [text[i : i + WIDTH] for i in range(0, len(text), WIDTH)]


class Board:
    def __init__(self, left, top, with_text):
        self.left, self.top, self.with_text = left, top, with_text
        self.height = 15 if with_text else 11
        self.start(random.randint(0, 2 * TICKS_PER_SECOND))

    def start(self, delay):
        self.digest = os.urandom(32)
        self.fingerprint = "SHA256:" + base64.b64encode(self.digest).decode().rstrip("=")
        self.path = walk(self.digest)
        self.counts = [[0] * FIELD_W for _ in range(FIELD_H)]
        self.phase = "wait"
        self.timer = delay
        self.typed = 0
        self.steps = 0
        self.dirty = False

    def tick(self):
        """Advance one tick. Return the text to draw, or b"" if nothing changed."""
        if self.phase == "wait":
            self.timer -= 1
            if self.timer > 0:
                return b""
            self.phase = "command" if self.with_text else "walk"
        elif self.phase == "command":
            self.typed += 1
            if self.typed >= len(COMMAND):
                self.phase, self.typed = "fingerprint", 0
        elif self.phase == "fingerprint":
            self.typed += TYPE_FINGERPRINT
            if self.typed >= len(self.fingerprint):
                self.phase = "walk"
        elif self.phase == "walk":
            x, y = self.path[self.steps]
            if self.counts[y][x] < MAX_COUNT:
                self.counts[y][x] += 1
            self.steps += 1
            if self.steps == len(self.path):
                self.phase, self.timer = "hold", HOLD_TICKS
        elif self.phase == "hold":
            self.timer -= 1
            if self.timer > 0:
                return b""
            blank = self.blank()
            self.start(10)
            return blank
        return self.draw()

    def blank(self):
        return "".join(
            "\x1b[%d;%dH%s" % (self.top + i + 1, self.left + 1, " " * WIDTH) for i in range(self.height)
        ).encode()

    def cell(self, x, y):
        """Return the text of one board cell, with its color."""
        count = self.counts[y][x]
        finished = self.phase == "hold"
        bishop = self.phase == "walk" and self.steps > 0 and self.path[self.steps - 1] == (x, y)
        if (x, y) == (FIELD_W // 2, FIELD_H // 2) and self.phase in ("walk", "hold"):
            return "\x1b[1;36m" + SYMBOLS[START] + RESET
        if finished and (x, y) == self.path[-1]:
            return "\x1b[1;35m" + SYMBOLS[END] + RESET
        if bishop:
            return "\x1b[1;7;97m" + SYMBOLS[count] + RESET
        if count == 0:
            return " "
        return "\x1b[38;5;%dm%s%s" % (PALETTE[count - 1], SYMBOLS[count], RESET)

    def draw(self):
        lines = []
        if self.with_text:
            if self.phase != "wait":
                lines.append("\x1b[32m" + COMMAND[: self.typed if self.phase == "command" else len(COMMAND)] + RESET)
            count = len(self.fingerprint) if self.phase in ("walk", "hold") else self.typed
            if self.phase in ("fingerprint", "walk", "hold"):
                lines.extend("\x1b[36m" + line + RESET for line in fingerprint_lines(self.fingerprint, count))
            lines += [""] * (4 - len(lines))
        if self.phase in ("walk", "hold"):
            lines.append("\x1b[90m" + border(TITLE) + RESET)
            for y in range(FIELD_H):
                lines.append(
                    "\x1b[90m|" + RESET + "".join(self.cell(x, y) for x in range(FIELD_W)) + "\x1b[90m|" + RESET
                )
            lines.append("\x1b[90m" + border("SHA256") + RESET)
        parts = []
        for i, line in enumerate(lines):
            # Blank the line inside the board first, so a shorter line leaves no old
            # characters behind and the neighbor boards stay untouched.
            at = "\x1b[%d;%dH" % (self.top + i + 1, self.left + 1)
            parts.append(at + " " * WIDTH + at + line)
        return "".join(parts).encode()


def layout(cols, rows):
    """Return the boards that fit the pane, centered."""
    with_text = rows >= 15
    height = 15 if with_text else 11
    across = max(1, (cols + GAP) // (WIDTH + GAP))
    down = max(1, (rows + 1) // (height + 1))
    left = (cols - (across * WIDTH + (across - 1) * GAP)) // 2
    top = (rows - (down * height + (down - 1))) // 2
    return [
        Board(left + i * (WIDTH + GAP), top + j * (height + 1), with_text)
        for j in range(down)
        for i in range(across)
    ]


def terminal_size():
    size = os.get_terminal_size(OUT)
    return size.columns, size.lines


def stop(signum, frame):
    os.write(OUT, (RESET + "\x1b[?25h").encode())
    sys.exit(0)


def main():
    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        signal.signal(sig, stop)
    cols, rows = terminal_size()
    boards = layout(cols, rows)
    os.write(OUT, b"\x1b[?25l\x1b[0m\x1b[2J")
    interval = 1 / TICKS_PER_SECOND
    next_tick = time.monotonic()
    ticks = 0
    while True:
        frame = b"".join(board.tick() for board in boards)
        if frame:
            os.write(OUT, frame)
        ticks += 1
        if ticks % 15 == 0 and terminal_size() != (cols, rows):
            os.write(OUT, (RESET + "\x1b[?25h").encode())
            return 3
        next_tick += interval
        pause = next_tick - time.monotonic()
        if pause > 0:
            time.sleep(pause)
        else:
            next_tick = time.monotonic()


if __name__ == "__main__":
    sys.exit(main())
