#!/usr/bin/env python3
"""Draw a picture on the terminal with half-block characters.

Each terminal cell shows two vertical pixels: the top pixel is the text color of
the upper half block and the bottom pixel is the background color. The picture
keeps its shape, is centered, and the rest of the pane is black. Colors come from
the xterm 256-color palette, which has a 6x6x6 color cube and 24 grays.

When HOLLYWOOD_IMAGES is "kitty", the picture is drawn with the Kitty graphics
protocol instead, as real pixels. The picture is sent once as a virtual placement,
and the pane holds Unicode placeholder characters (U+10EEEE with a row and a column
mark), so a terminal multiplexer such as tmux clips and redraws it like text. Inside
tmux each graphics command is wrapped in a passthrough sequence. If the Kitty draw
fails, the half-block draw runs instead.

Usage: image-render.py FILE
       image-render.py --detect   print "kitty" (and the cell size) if the terminal
                                  draws Kitty graphics, otherwise print nothing
       image-render.py --clear    delete this pane's Kitty picture
"""
import base64
import fcntl
import io
import os
import re
import select
import struct
import subprocess
import sys
import termios
import time
import tty

from PIL import Image

OUT = sys.stdout.fileno()
BLACK = 16  # xterm-256 color 16 is black
CUBE = (0, 95, 135, 175, 215, 255)


def cube_level(v):
    return 0 if v < 48 else 1 if v < 115 else (v - 35) // 40


def nearest(r, g, b, cache={}):
    """Return the xterm-256 color index closest to (r, g, b)."""
    key = (r << 16) | (g << 8) | b
    index = cache.get(key)
    if index is None:
        ri, gi, bi = cube_level(r), cube_level(g), cube_level(b)
        cr, cg, cb = CUBE[ri], CUBE[gi], CUBE[bi]
        cube_error = (r - cr) ** 2 + (g - cg) ** 2 + (b - cb) ** 2
        average = (r + g + b) // 3
        step = min(23, max(0, (average - 3) // 10))
        gray = 8 + 10 * step
        gray_error = (r - gray) ** 2 + (g - gray) ** 2 + (b - gray) ** 2
        index = 232 + step if gray_error < cube_error else 16 + 36 * ri + 6 * gi + bi
        if index == 232 and r + g + b < 24:
            index = BLACK
        cache[key] = index
    return index


# Kitty row and column marks (gen/rowcolumn-diacritics.txt in the Kitty source).
# Mark number N means row or column N. A picture can have at most this many of each.
DIACRITICS = (
    0x0305, 0x030D, 0x030E, 0x0310, 0x0312, 0x033D, 0x033E, 0x033F, 0x0346, 0x034A, 0x034B, 0x034C,
    0x0350, 0x0351, 0x0352, 0x0357, 0x035B, 0x0363, 0x0364, 0x0365, 0x0366, 0x0367, 0x0368, 0x0369,
    0x036A, 0x036B, 0x036C, 0x036D, 0x036E, 0x036F, 0x0483, 0x0484, 0x0485, 0x0486, 0x0487, 0x0592,
    0x0593, 0x0594, 0x0595, 0x0597, 0x0598, 0x0599, 0x059C, 0x059D, 0x059E, 0x059F, 0x05A0, 0x05A1,
    0x05A8, 0x05A9, 0x05AB, 0x05AC, 0x05AF, 0x05C4, 0x0610, 0x0611, 0x0612, 0x0613, 0x0614, 0x0615,
    0x0616, 0x0617, 0x0657, 0x0658, 0x0659, 0x065A, 0x065B, 0x065D, 0x065E, 0x06D6, 0x06D7, 0x06D8,
    0x06D9, 0x06DA, 0x06DB, 0x06DC, 0x06DF, 0x06E0, 0x06E1, 0x06E2, 0x06E4, 0x06E7, 0x06E8, 0x06EB,
    0x06EC, 0x0730, 0x0732, 0x0733, 0x0735, 0x0736, 0x073A, 0x073D, 0x073F, 0x0740, 0x0741, 0x0743,
    0x0745, 0x0747, 0x0749, 0x074A, 0x07EB, 0x07EC, 0x07ED, 0x07EE, 0x07EF, 0x07F0, 0x07F1, 0x07F3,
    0x0816, 0x0817, 0x0818, 0x0819, 0x081B, 0x081C, 0x081D, 0x081E, 0x081F, 0x0820, 0x0821, 0x0822,
    0x0823, 0x0825, 0x0826, 0x0827, 0x0829, 0x082A, 0x082B, 0x082C, 0x082D, 0x0951, 0x0953, 0x0954,
    0x0F82, 0x0F83, 0x0F86, 0x0F87, 0x135D, 0x135E, 0x135F, 0x17DD, 0x193A, 0x1A17, 0x1A75, 0x1A76,
    0x1A77, 0x1A78, 0x1A79, 0x1A7A, 0x1A7B, 0x1A7C, 0x1B6B, 0x1B6D, 0x1B6E, 0x1B6F, 0x1B70, 0x1B71,
    0x1B72, 0x1B73, 0x1CD0, 0x1CD1, 0x1CD2, 0x1CDA, 0x1CDB, 0x1CE0, 0x1DC0, 0x1DC1, 0x1DC3, 0x1DC4,
    0x1DC5, 0x1DC6, 0x1DC7, 0x1DC8, 0x1DC9, 0x1DCB, 0x1DCC, 0x1DD1, 0x1DD2, 0x1DD3, 0x1DD4, 0x1DD5,
    0x1DD6, 0x1DD7, 0x1DD8, 0x1DD9, 0x1DDA, 0x1DDB, 0x1DDC, 0x1DDD, 0x1DDE, 0x1DDF, 0x1DE0, 0x1DE1,
    0x1DE2, 0x1DE3, 0x1DE4, 0x1DE5, 0x1DE6, 0x1DFE, 0x20D0, 0x20D1, 0x20D4, 0x20D5, 0x20D6, 0x20D7,
    0x20DB, 0x20DC, 0x20E1, 0x20E7, 0x20E9, 0x20F0, 0x2CEF, 0x2CF0, 0x2CF1, 0x2DE0, 0x2DE1, 0x2DE2,
    0x2DE3, 0x2DE4, 0x2DE5, 0x2DE6, 0x2DE7, 0x2DE8, 0x2DE9, 0x2DEA, 0x2DEB, 0x2DEC, 0x2DED, 0x2DEE,
    0x2DEF, 0x2DF0, 0x2DF1, 0x2DF2, 0x2DF3, 0x2DF4, 0x2DF5, 0x2DF6, 0x2DF7, 0x2DF8, 0x2DF9, 0x2DFA,
    0x2DFB, 0x2DFC, 0x2DFD, 0x2DFE, 0x2DFF, 0xA66F, 0xA67C, 0xA67D, 0xA6F0, 0xA6F1, 0xA8E0, 0xA8E1,
    0xA8E2, 0xA8E3, 0xA8E4, 0xA8E5, 0xA8E6, 0xA8E7, 0xA8E8, 0xA8E9, 0xA8EA, 0xA8EB, 0xA8EC, 0xA8ED,
    0xA8EE, 0xA8EF, 0xA8F0, 0xA8F1, 0xAAB0, 0xAAB2, 0xAAB3, 0xAAB7, 0xAAB8, 0xAABE, 0xAABF, 0xAAC1,
    0xFE20, 0xFE21, 0xFE22, 0xFE23, 0xFE24, 0xFE25, 0xFE26, 0x10A0F, 0x10A38, 0x1D185, 0x1D186,
    0x1D187, 0x1D188, 0x1D189, 0x1D1AA, 0x1D1AB, 0x1D1AC, 0x1D1AD, 0x1D242, 0x1D243, 0x1D244,
)
PLACEHOLDER = "\U0010EEEE"
KITTY = os.environ.get("HOLLYWOOD_IMAGES") == "kitty"
CHUNK = 4096
MAX_PIXELS = 1600  # longest side of the picture that is sent


def wrap(sequence):
    """Wrap a command so tmux passes it to the outer terminal."""
    if os.environ.get("TMUX"):
        return b"\x1bPtmux;" + sequence.replace(b"\x1b", b"\x1b\x1b") + b"\x1b\\"
    return sequence


def image_id():
    """Return this pane's picture number, from 1 to 255.

    The number is the foreground color of the placeholders, so it must fit the
    256-color palette. That survives tmux, which converts true colors if the outer
    terminal does not report them.
    """
    try:
        number = int(os.environ.get("TMUX_PANE", "").lstrip("%"))
    except ValueError:
        number = os.getpid()
    return 1 + number % 255


def allow_passthrough():
    pane = os.environ.get("TMUX_PANE")
    if os.environ.get("TMUX") and pane:
        subprocess.run(
            ["tmux", "set-option", "-p", "-t", pane, "allow-passthrough", "on"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )


def cell_pixels():
    """Return the size of one cell in pixels, as floats."""
    try:
        rows, cols, x, y = struct.unpack("HHHH", fcntl.ioctl(OUT, termios.TIOCGWINSZ, b"\0" * 8))
        if x and y and rows and cols:
            return x / cols, y / rows
    except OSError:
        pass
    match = re.fullmatch(r"(\d+)x(\d+)", os.environ.get("HOLLYWOOD_CELL_PX", ""))
    if match and int(match[1]) and int(match[2]):
        return float(match[1]), float(match[2])
    return 10.0, 20.0


def draw_kitty(path):
    cols, rows = os.get_terminal_size(OUT)
    cols, rows = min(cols, len(DIACRITICS)), min(rows, len(DIACRITICS))
    cell_w, cell_h = cell_pixels()
    picture = Image.open(path).convert("RGB")
    scale = min(cols * cell_w / picture.width, rows * cell_h / picture.height)
    width = max(1, min(cols, round(picture.width * scale / cell_w)))
    height = max(1, min(rows, round(picture.height * scale / cell_h)))
    shrink = min(1.0, MAX_PIXELS / max(width * cell_w, height * cell_h))
    picture = picture.resize(
        (max(1, round(width * cell_w * shrink)), max(1, round(height * cell_h * shrink))),
        Image.LANCZOS,
    )
    png = io.BytesIO()
    picture.save(png, "PNG", compress_level=1)
    data = base64.standard_b64encode(png.getvalue())

    allow_passthrough()
    number = image_id()
    parts = [b"\x1b[?25l", wrap(b"\x1b_Ga=d,d=I,i=%d,q=2\x1b\\" % number)]
    for start in range(0, len(data), CHUNK):
        more = 1 if start + CHUNK < len(data) else 0
        head = b"a=T,f=100,t=d,i=%d,U=1,c=%d,r=%d,q=2,m=%d" % (number, width, height, more) if start == 0 else b"m=%d" % more
        parts.append(wrap(b"\x1b_G" + head + b";" + data[start : start + CHUNK] + b"\x1b\\"))

    top, left = (rows - height) // 2, (cols - width) // 2
    for row in range(rows):
        parts.append(b"\x1b[%d;1H\x1b[2K" % (row + 1))
        if top <= row < top + height:
            marks = chr(DIACRITICS[row - top])
            cells = "".join(PLACEHOLDER + marks + chr(DIACRITICS[x]) for x in range(width))
            parts.append(b"\x1b[%d;%dH\x1b[38;5;%dm" % (row + 1, left + 1, number))
            parts.append(cells.encode() + b"\x1b[0m")
    os.write(OUT, b"".join(parts))


def clear_kitty():
    if KITTY:
        os.write(OUT, wrap(b"\x1b_Ga=d,d=I,i=%d,q=2\x1b\\" % image_id()))


def detect():
    """Ask the terminal if it draws Kitty graphics and how big a cell is.

    The terminal answers the graphics query first only if it supports it, and always
    answers the device attributes query (the last one asked) after the others.
    """
    try:
        fd = os.open("/dev/tty", os.O_RDWR)
    except OSError:
        return
    saved = termios.tcgetattr(fd)
    reply = b""
    try:
        tty.setcbreak(fd)
        os.write(fd, b"\x1b_Gi=31,s=1,v=1,a=q,t=d,f=24;AAAA\x1b\\\x1b[16t\x1b[c")
        deadline = time.monotonic() + 1.0
        while not re.search(rb"\x1b\[\?[0-9;]*c", reply):
            wait = deadline - time.monotonic()
            if wait <= 0 or not select.select([fd], [], [], wait)[0]:
                break
            reply += os.read(fd, 256)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, saved)
        os.close(fd)
    if b"\x1b_Gi=31;OK" in reply:
        size = re.search(rb"\x1b\[6;(\d+);(\d+)t", reply)
        print("kitty" + (" %sx%s" % (size[2].decode(), size[1].decode()) if size else ""))


def main():
    if len(sys.argv) == 2 and sys.argv[1] == "--detect":
        detect()
        return 0
    if len(sys.argv) == 2 and sys.argv[1] == "--clear":
        clear_kitty()
        return 0
    if len(sys.argv) != 2:
        return 2
    if KITTY:
        try:
            draw_kitty(sys.argv[1])
            return 0
        except Exception:
            pass
    cols, rows = os.get_terminal_size(OUT)
    width, height = cols, 2 * rows
    try:
        picture = Image.open(sys.argv[1]).convert("RGB")
    except Exception:
        return 1
    scale = min(width / picture.width, height / picture.height)
    new_width = max(1, min(width, round(picture.width * scale)))
    new_height = max(1, min(height, round(picture.height * scale)))
    picture = picture.resize((new_width, new_height), Image.LANCZOS)
    canvas = Image.new("RGB", (width, height), (0, 0, 0))
    canvas.paste(picture, ((width - new_width) // 2, (height - new_height) // 2))
    pixels = canvas.load()

    parts = [b"\x1b[?25l"]
    for row in range(rows):
        parts.append(b"\x1b[%d;1H" % (row + 1))
        state = None
        for x in range(width):
            fg = nearest(*pixels[x, 2 * row])
            bg = nearest(*pixels[x, 2 * row + 1])
            if fg == BLACK and bg == BLACK:
                if state is not None:
                    parts.append(b"\x1b[0m")
                    state = None
                parts.append(b" ")
            else:
                if state != (fg, bg):
                    parts.append(b"\x1b[38;5;%d;48;5;%dm" % (fg, bg))
                    state = (fg, bg)
                parts.append("▀".encode())
        if state is not None:
            parts.append(b"\x1b[0m")
    os.write(OUT, b"".join(parts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
