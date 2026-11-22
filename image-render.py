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
import io
import os
import sys

from PIL import Image

sys.path.insert(0, "/usr/local/lib/hollywood")
import hollywood_kitty as kitty

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


KITTY = os.environ.get("HOLLYWOOD_IMAGES") == "kitty"


def draw_kitty(path):
    cols, rows = os.get_terminal_size(OUT)
    cols, rows = min(cols, len(kitty.DIACRITICS)), min(rows, len(kitty.DIACRITICS))
    cell_w, cell_h = kitty.cell_pixels(OUT)
    picture = Image.open(path).convert("RGB")
    scale = min(cols * cell_w / picture.width, rows * cell_h / picture.height)
    width = max(1, min(cols, round(picture.width * scale / cell_w)))
    height = max(1, min(rows, round(picture.height * scale / cell_h)))
    shrink = min(1.0, kitty.MAX_PIXELS / max(width * cell_w, height * cell_h))
    picture = picture.resize(
        (max(1, round(width * cell_w * shrink)), max(1, round(height * cell_h * shrink))),
        Image.LANCZOS,
    )
    png = io.BytesIO()
    picture.save(png, "PNG", compress_level=1)
    number = kitty.image_id()
    os.write(
        OUT,
        b"\x1b[?25l"
        + kitty.delete(number)
        + kitty.transmit(png.getvalue(), number, width, height)
        + kitty.placeholders(number, width, height, (rows - height) // 2, (cols - width) // 2, rows),
    )


def clear_kitty():
    if KITTY:
        os.write(OUT, kitty.delete(kitty.image_id()))



def main():
    if len(sys.argv) == 2 and sys.argv[1] == "--detect":
        kitty.detect()
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
