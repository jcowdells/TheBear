import os

from src.console import Console
from src.geometry import *
import util

ALIGN_LEFT   = 0
ALIGN_TOP    = 0
ALIGN_RIGHT  = 1
ALIGN_BOTTOM = 1
ALIGN_CENTER = 2

class Sampler:
    def __init__(self, filepath, trust_path=False):
        self.__width = 0
        self.__height = 0
        self.__data = None
        if not trust_path:
            filepath = util.abspath(filepath)
        with open(filepath, 'rb') as file:
            index = -2
            while byte := file.read(1):
                if index == 0:
                    self.__data = bytearray(self.__width * self.__height * 8)
                if index == -2:
                    self.__width = int.from_bytes(byte, 'little')
                elif index == -1:
                    self.__height = int.from_bytes(byte, 'little')
                else:
                    self.__data[index] = int.from_bytes(byte, 'little')
                index += 1

    def get_pixel(self, x, y):
        if x <= 0:
            x = 0
        if x >= self.__width:
            x = self.__height - 1
        if y <= 0:
            y = 0
        if y >= self.__height:
            y = self.__height - 1
        return self.__data[y * self.__width + x]

    def sample(self, x, y):
        sx = round(x * self.__width)
        sy = round(y * self.__height)
        return self.get_pixel(sx, sy)

def sampler_array(directory):
    directory = util.abspath(directory)
    samplers = []
    for file in sorted(os.listdir(directory)):
        print(file)
        samplers.append(Sampler(os.path.join(directory, file), trust_path=True))
    return samplers

class Buffer:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.__buffer = bytearray(width * height)

    def resize(self, width, height):
        if width < 0: width = 0
        if height < 0: height = 0
        self.width = width
        self.height = height
        self.__buffer = bytearray(width * height)

    def swap(self):
        self.__buffer = bytearray(self.width * self.height)

    def get(self, x, y):
        index = y * self.width + x
        return self.__buffer[index]

    def set(self, x, y, value):
        index = y * self.width + x
        self.__buffer[index] = value

    def try_set(self, x, y, value):
        if (0 <= x < self.width) and (0 <= y < self.height):
            self.set(x, y, value)

    def as_string(self):
        string = ""
        count = 0
        for byte in self.__buffer:
            if byte == 0:
                string += " "
            else:
                string += chr(byte)
            count += 1
            if count == self.width:
                string += "\n"
                count = 0
        return string

    def __len__(self):
        return len(self.__buffer)

class ConsoleGUI(Console):
    def __init__(self, width, height, x, y):
        super().__init__(width, height, x, y, 10, fg="#22BB00")
        self.buffer = Buffer(self.get_width_chars(), self.get_height_chars())

    def configure_event(self, event):
        self.buffer.resize(self.get_width_chars(), self.get_height_chars())

    def draw_line(self, a, b, fill="#"):
        fill = ord(fill)
        for x, y in line_iter_points(a, b):
            self.buffer.try_set(x, y, fill)

    def draw_triangle(self, a, b, c, fill="#"):
        min_x, min_y, max_x, max_y = triangle_bbox(a, b, c)
        fill = ord(fill)
        for x in range(min_x, max_x + 1):
            for y in range(min_y, max_y + 1):
                if triangle_contains(a, b, c, (x, y)):
                    self.buffer.try_set(x, y, fill)

    def draw_sampler(self, a, b, c, uv_a, uv_b, uv_c, sampler):
        min_x, min_y, max_x, max_y = triangle_bbox(a, b, c)
        for x in range(min_x, max_x + 1):
            for y in range(min_y, max_y + 1):
                if triangle_contains(a, b, c, (x, y)):
                    u, v = triangle_uv(a, b, c, uv_a, uv_b, uv_c, (x, y))
                    fill = sampler.sample(u, v)
                    if fill != ord(" "):
                        self.buffer.try_set(x, y, fill)

    def draw_character(self, a, fill="#"):
        self.buffer.try_set(a[X], a[Y], ord(fill))

    def draw_text(self, a, text, align_x=ALIGN_CENTER, align_y=ALIGN_CENTER, justify=ALIGN_CENTER):
        lines = text.split("\n")
        max_width = 0
        max_height = len(lines)
        for i in range(max_height):
            len_line = len(lines[i])
            if len_line > max_width:
                max_width = len_line

        for i in range(max_height):
            if justify == ALIGN_LEFT:
                lines[i] = lines[i].ljust(max_width, "\0")
            elif justify == ALIGN_RIGHT:
                lines[i] = lines[i].rjust(max_width, "\0")
            elif justify == ALIGN_CENTER:
                lines[i] = lines[i].center(max_width, "\0")

        mod_x = a[X]
        mod_y = a[Y]

        if align_x == ALIGN_RIGHT:
            mod_x = a[X] - max_width + 1
        elif align_x == ALIGN_CENTER:
            mod_x = a[X] - max_width // 2 + 1

        if align_y == ALIGN_BOTTOM:
            mod_y = a[Y] - max_height + 1
        elif align_y == ALIGN_CENTER:
            mod_y = a[Y] - max_height // 2

        for y in range(max_height):
            for x in range(max_width):
                draw_x = x + mod_x
                draw_y = y + mod_y
                draw_c = lines[y][x]
                if draw_c != "\0":
                    self.buffer.try_set(draw_x, draw_y, ord(draw_c))

    def draw_sprite(self, a, b, sampler):
        width = b[X] - a[X]
        height = b[Y] - a[Y]
        if width == 0 or height == 0:
            return

        for y in range(height + 1):
            v = y / height
            for x in range(width + 1):
                u = x / width
                fill = sampler.sample(u, v)
                if fill != ord(" "):
                    self.buffer.try_set(x + a[X], y + a[Y], fill)

    def draw_rectangle(self, a, b, fill="#"):
        width = b[X] - a[X]
        height = b[Y] - a[Y]
        fill = ord(fill)
        for y in range(height + 1):
            for x in range(width + 1):
                self.buffer.try_set(x + a[X], y + a[Y], fill)

    def draw_circle(self, a, b, fill="#"):
        width = b[X] - a[X]
        height = b[Y] - a[Y]

        if width == 0 or height == 0:
            return

        fill = ord(fill)
        for y in range(height + 1):
            for x in range(width + 1):
                u = x / width * 2 - 1
                v = y / height * 2 - 1
                if (u * u) + (v * v) <= 1:
                    self.buffer.try_set(x + a[X], y + a[Y], fill)

    def swap_buffers(self):
        self.stdout_w(self.buffer.as_string())
        self.buffer.swap()
