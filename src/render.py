from src.console import Console
from src.geometry import *

class Sampler:
    def __init__(self, filepath):
        self.__width = 0
        self.__height = 0
        self.__data = None
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

class Buffer:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.__buffer = bytearray(width * height)

    def resize(self, width, height):
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
        self.count = 0
        self.sampler = Sampler("../res/me.bin")

    def configure_event(self, event):
        self.buffer.resize(self.get_width_chars(), self.get_height_chars())

    def draw_line(self, a, b, fill="#"):
        for x, y in line_iter_points(a, b):
            self.buffer.try_set(x, y, ord(fill))

    def draw_triangle(self, a, b, c, fill="#"):
        min_x, min_y, max_x, max_y = triangle_bbox(a, b, c)
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
                    self.buffer.try_set(x, y, fill)

    def swap_buffers(self):
        self.stdout_w(self.buffer.as_string())
        self.buffer.swap()
