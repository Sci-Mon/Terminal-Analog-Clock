#! /usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
#
# Terminal analog clock - A simple text basedanalog clock
# Copyright (C) 2026 Simon Widmer - sery(at)solnet.ch

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# =============================================================================
# IMPORTS
# =============================================================================
import math
import time
import datetime
import os
import sys
import select

# -------------------------
# Platform-specific imports
# -------------------------
if os.name == "nt":
    import ctypes
    import signal
    import msvcrt
    
    # Enable ANSI escape codes on Windows
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.GetStdHandle(-11)
    mode = ctypes.c_uint()
    kernel32.GetConsoleMode(handle, ctypes.byref(mode))
    ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
    kernel32.SetConsoleMode(handle, mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING)

    # Ignore CTRL-C on Windows
    signal.signal(signal.SIGINT, signal.SIG_IGN)

else:
    import tty
    import termios

# =============================================================================
# APP METADATA
# =============================================================================

APPNAME      = "Terminal Analog Clock"
VERSION      = "v0.3"
MANUFACTURED = "SWISS MADE"
AUTHOR       = "Simon Widmer"
EMAIL        = "sery\x40solnet.ch"

# =============================================================================
# CONFIGURATION
# =============================================================================
BACKGROUNDCOLOR      = "\033[40m"       # black
APPNAMECOLOR         = "\033[38;5;236m" # darkgrey
VERSIONCOLOR         = "\033[38;5;236m" # darkgrey
DATECOLOR            = "\033[90m"       # lightgrey
DATEFRAMECOLOR       = "\033[38;5;236m" # darkgrey
MANUFACTUREDCOLOR    = "\033[38;5;236m" # darkgrey
AMPMCOLOR            = "\033[90m"       # lightgrey
WEEKDAYCOLOR         = "\033[90m"       # lightgrey
WEEKCOLOR            = "\033[90m"       # lightgrey
SECONDHANDCOLOR      = "\033[31m"       # red
MINUTEHANDCOLOR      = "\033[92m"       # green
HOURHANDCOLOR        = "\033[92m"       # green
CLOCKFACECENTER      = "\033[1m"        # bold white
CLOCKFACENUMBERCOLOR = "\033[1m"        # bold white
QUITINSTRUCTIONCOLOR = "\033[90m"       # lightgrey

DATEFORMAT           = "%d.%m.%Y"       # US: use "%m/%d/%Y"
AMPMFORMAT           = "%p"             # show am/pm: %p, hide: use ""
WEEKFORMAT           = "%V"             # ISO: use %V, US: use %U,  hide: ""
WEEKDAYFORMAT        = "%A"             # long: %A,  shortform: %a,  hide: ""

# =============================================================================
# VT100 ESCAPE SEQUENCES and CONSTANTS
# =============================================================================

terminal_size = os.get_terminal_size() # get terminal dimensions
terminal_width = terminal_size.columns
terminal_height = terminal_size.lines
CLEARSCREEN = "\033[2J"
CLEARSCROLLBACK = "\033[3J"
CURSORHOME = "\033[H"
HIDECURSOR = "\033[?25l"
RESET = "\033[39m"     #RESET = "\033[0m"
RESET_TERMINAL = "\033c"

# =============================================================================
# INPUT HELPERS
# =============================================================================
def _is_tty():
    return sys.stdin.isatty()

if os.name == "nt":

    def enable_raw_input():
        return None

    def restore_input(old_settings):
        pass

    def input_ready():
        return msvcrt.kbhit()

    def read_char():
        return msvcrt.getwch()

else:

    def enable_raw_input():
        if not _is_tty():
            return None

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)

        tty.setcbreak(fd)

        return old_settings

    def restore_input(old_settings):
        if not _is_tty() or old_settings is None:
            return

        termios.tcsetattr(
            sys.stdin.fileno(),
            termios.TCSADRAIN,
            old_settings
        )

    def input_ready():
        if not _is_tty():
            return False
        return select.select([sys.stdin], [], [], 0)[0]

    def read_char():
        return sys.stdin.read(1)

# =============================================================================
# DRAWING
# =============================================================================
def draw_clock(radius=max(5, (terminal_height - 1) // 2)):
    old_settings = enable_raw_input()
    try:
        # Clear the terminal using ANSI escape codes
        print(CLEARSCREEN, end="")
        print(BACKGROUNDCOLOR, end="")
        # Clear scrollback buffer to prevent old clock faces from being visible when scrolling up
        print(CLEARSCROLLBACK, end="")
        # Move cursor to home position
        print(CURSORHOME, end="")
        # Hide cursor
        print(HIDECURSOR, end="")

        while True:
            now = datetime.datetime.now()
            # Calculate hand angles in radians
            hr_a = math.radians((now.hour % 12 + now.minute / 60) * 30 - 90)
            min_a = math.radians(now.minute * 6 - 90)
            sec_a = math.radians(now.second * 6 - 90)

            # Create an empty character buffer for the clock face using terminal size.
            height = terminal_height
            width = terminal_width
            center_y = height // 2
            center_x = width // 2
            max_radius_h = min(center_y, height - center_y - 1)
            max_radius_w = (width - 1) // 4
            draw_radius = min(radius, max_radius_h, max_radius_w)
            grid = [[" " for _ in range(width)] for _ in range(height)]


            # Optional: draw tick marks every 6 degrees around the dial
            #for i in range(0, 360, 6):
            #    a = math.radians(i)
            #    y = int(radius + radius * math.sin(a))
            #    x = int(radius * 2 + radius * 2 * math.cos(a))
            #    grid[y][x] = "▪"

            # --- Draw date (at three o'clock position) ---
            date_str = now.strftime(DATEFORMAT)
            x0 = int(center_x + draw_radius * 1.5 - (len(date_str) // 2))
            for i, ch in enumerate(date_str):
                if 0 <= x0 + i < width:
                    grid[center_y][x0 + i] = DATECOLOR + ch  + RESET

            # --- Draw Calendar Week (below date) ---
            if WEEKFORMAT != "":
                week_str = "week " + now.strftime(WEEKFORMAT)
                x0 = int(center_x + draw_radius * 1.5 - (len(week_str) // 2))
                for i, ch in enumerate(week_str):
                    if 0 <= x0 + i < width:
                        grid[center_y + 1 ][x0 + i] = WEEKCOLOR + ch  + RESET

            # --- Draw AM/PM indicator (below 12 o'clock position) ---
            ampm_str = now.strftime(AMPMFORMAT)
            x0 = center_x - 1
            y0 = int(center_y - draw_radius / 1.5)
            for i, ch in enumerate(ampm_str):
                if 0 <= y0 < height and 0 <= x0 + i < width:
                    grid[y0][x0 + i] = AMPMCOLOR + ch  + RESET

            # --- Draw Weekday (between 9 o'clock position and clockface-center) ---
            weekday_str = now.strftime(WEEKDAYFORMAT)
            x0 = center_x - int(draw_radius * 1.5) - len(weekday_str) // 2
            y0 = center_y
            for i, ch in enumerate(weekday_str):
                if 0 <= y0 < height and 0 <= x0 + i < width:
                    grid[y0][x0 + i] = WEEKDAYCOLOR + ch  + RESET

            # --- Draw APPNAME (between 6 o'clock position and clockface-center) ---
            x0 = center_x - len(APPNAME) // 2
            y0 = center_y + int(draw_radius / 1.5)
            for i, ch in enumerate(APPNAME):
                if 0 <= y0 < height and 0 <= x0 + i < width:
                    grid[y0][x0 + i] = APPNAMECOLOR + ch  + RESET

            # --- Draw VERSION one line below
            x0 = center_x - len(VERSION) // 2
            y0 = center_y + int(draw_radius / 1.5) + 1
            for i, ch in enumerate(VERSION):
                if 0 <= y0 < height and 0 <= x0 + i < width:
                    grid[y0][x0 + i] = VERSIONCOLOR + ch  + RESET

            # --- Draw MANUFACTURED one line below
            x0 = center_x - len(MANUFACTURED) // 2
            y0 = center_y + int(draw_radius / 1.5) + 2
            for i, ch in enumerate(MANUFACTURED):
                if 0 <= y0 < height and 0 <= x0 + i < width:
                    grid[y0][x0 + i] = MANUFACTUREDCOLOR + ch  + RESET

            # --- Put Quit instructions at the bottom left corner ---
            quit_str = "Press CTRL-X or Q to quit"
            for i, ch in enumerate(quit_str):
                if 0 <= i < width:
                    grid[height - 1][i] = QUITINSTRUCTIONCOLOR + ch  + RESET

            # --- Draw clock numbers ---
            for i in range(1, 13):
                a = math.radians(i * 30 - 90)
                y = int(center_y + draw_radius * math.sin(a))
                x = int(center_x + draw_radius * 2 * math.cos(a))
                s = str(i)
                # center multi-digit numbers on the computed position
                x0 = x - (len(s) - 1) // 2
                for j, ch in enumerate(s):
                    xx = x0 + j
                    if 0 <= y < len(grid) and 0 <= xx < len(grid[0]):
                        grid[y][xx] = CLOCKFACENUMBERCOLOR + ch  + RESET


            # Bresenham line algorithm used to draw each hand
            def draw_line(x0, y0, x1, y1, char):
                dx = abs(x1 - x0)
                sx = 1 if x0 < x1 else -1
                dy = -abs(y1 - y0)
                sy = 1 if y0 < y1 else -1
                err = dx + dy
                while True:
                    if 0 <= y0 < len(grid) and 0 <= x0 < len(grid[0]):
                        grid[y0][x0] = char
                    if x0 == x1 and y0 == y1:
                        break
                    e2 = 2 * err
                    if e2 >= dy:
                        err += dy
                        x0 += sx
                    if e2 <= dx:
                        err += dx
                        y0 += sy

            # Helper to draw a clock hand from the center to the target point
            def draw_hand(angle, length, char):
                x1 = int(center_x + length * 2 * math.cos(angle))
                y1 = int(center_y + length * math.sin(angle))
                draw_line(center_x, center_y, x1, y1, char)

            # --- Draw clock hands ---
            draw_hand(hr_a, int(draw_radius * 0.55), HOURHANDCOLOR + "█" + RESET) # hour hand
            draw_hand(min_a, int(draw_radius * 0.95), MINUTEHANDCOLOR + "█" + RESET) # minute hand
            draw_hand(sec_a, int(draw_radius * 0.98), SECONDHANDCOLOR + "█" + RESET) # second hand

            # --- Draw center of clockface ---
            if 0 <= center_y < len(grid) and 0 <= center_x < len(grid[0]):
                grid[center_y][center_x] = CLOCKFACECENTER + "■" + RESET

            # Move cursor to the screen top and print the buffer
            print(HIDECURSOR + CURSORHOME, end="")  # hide cursor and move home
            for row in grid[:-1]:
                print("".join(row))
            sys.stdout.write("".join(grid[-1]))
            sys.stdout.flush()

            if input_ready():
                ch = read_char()
                if ch in ("q", "Q", "\x18"):
                    return

            time.sleep(1)
    finally:
        restore_input(old_settings)


# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    try:
        draw_clock()
    except KeyboardInterrupt:
        print("\nStopped by CTRL-C.")
    finally:
        print(RESET_TERMINAL + "\033[?25h")
