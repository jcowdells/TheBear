import random

from src.console import Console
from src.geometry import *

class Buffer:
    def __init__(self, width, height):
        self.__width = width
        self.__height = height
        self.__buffer = bytearray(width * height)

    def resize(self, width, height):
        self.__width = width
        self.__height = height
        self.__buffer = bytearray(width * height)

    def get(self, x, y):
        index = y * self.__width + x
        return self.__buffer[index]

    def set(self, x, y, value):
        index = y * self.__width + x
        self.__buffer[index] = value

    def try_set(self, x, y, value):
        index = y * self.__width + x
        if index < len(self):
            self.__buffer[index] = value

    def get_width(self):
        return self.__width

    def get_height(self):
        return self.__height

    def as_string(self):
        string = ""
        count = 0
        for byte in self.__buffer:
            if byte == 0:
                string += " "
            else:
                string += chr(byte)
            count += 1
            if count == self.__width:
                string += "\n"
                count = 0
        return string

    def __len__(self):
        return len(self.__buffer)

class ConsoleGUI(Console):
    def __init__(self, width, height, x, y):
        super().__init__(width, height, x, y, 10, fg="#22BB00")
        self.buffer = Buffer(self.get_width_chars(), self.get_height_chars())

        self.test_x = 0
        self.test_y = 0

    def configure_event(self, event):
        self.buffer.resize(self.get_width_chars(), self.get_height_chars())

    def draw_square(self):
        pass

    def main(self):
        max_size = self.buffer.get_width() * self.buffer.get_height()
        max_index = 256

        self.test_x += 0.1
        self.test_y += 0.01

        point_a = Point(0, 0)
        point_b = Point(int(self.test_x), int(self.test_y))

        line = Line(point_a, point_b)

        for x, y in line.get_points():
            print(x, y)
            self.buffer.try_set(x, y, ord("#"))

        print(self.buffer.as_string())
        self.stdout_w(self.buffer.as_string())
