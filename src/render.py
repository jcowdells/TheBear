import random
from argparse import ArgumentError

from pyatspi import pointToList

from src.console import Console
from src.geometry import *

class Image:
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

    def get_width(self):
        return self.__width

    def get_height(self):
        return self.__height

    def get_pixel(self, x, y):
        return self.__data[y * self.__width + x]

class Drawable:
    def draw(self, console_gui):
        pass

class Polygon(Drawable):
    def __init__(self, *args, fill="#"):
        len_args = len(args)
        if len_args < 3:
            raise ArgumentError(None, "A polygon must have at least 3 vertices!")
        self.__points = args
        self.__lines = []
        self.__fill = fill
        for i in range(len_args):
            point_a = args[i]
            if i + 1 == len_args:
                point_b = args[0]
            else:
                point_b = args[i + 1]
            self.__lines.append(Line(point_a, point_b))

    def draw(self, console_gui):
        for line in self.__lines:
            console_gui.draw_line(line)

    def rotate(self, angle, centre):
        for point in self.__points:
            point.rotation = angle
            point.rotation_centre = centre


class Buffer:
    def __init__(self, width, height):
        self.__width = width
        self.__height = height
        self.__buffer = bytearray(width * height)

    def resize(self, width, height):
        self.__width = width
        self.__height = height
        self.__buffer = bytearray(width * height)

    def swap(self):
        self.__buffer = bytearray(self.__width * self.__height)

    def get(self, x, y):
        index = y * self.__width + x
        return self.__buffer[index]

    def set(self, x, y, value):
        index = y * self.__width + x
        self.__buffer[index] = value

    def try_set(self, x, y, value):
        if (0 <= x < self.__width) and (0 <= y < self.__height):
            self.set(x, y, value)

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
        #self.image = Image("res/helloworld.bin")
        self.point_a = Point(10, 10)
        self.point_b = Point(20, 10)
        self.point_c = Point(20, 20)
        self.point_d = Point(10, 20)
        self.point_e = Point(5, 15)
        self.rotation = 0
        self.poly = Polygon(self.point_a, self.point_b, self.point_c, self.point_d, self.point_e)

    def configure_event(self, event):
        self.buffer.resize(self.get_width_chars(), self.get_height_chars())

    def draw_line(self, line, fill="#"):
        for x, y in line.get_points():
            self.buffer.try_set(x, y, ord(fill))

    def draw_image(self, image, fill="#"):
        for x in range(image.get_width()):
            for y in range(image.get_height()):
                self.buffer.try_set(x, y, image.get_pixel(x, y))

    def draw(self, drawable):
        drawable.draw(self)

    def main(self):
        #self.draw_image(self.image)

        #print(self.buffer.as_string())
        self.rotation += 0.001

        self.poly.rotate(self.rotation, Point(30, 30))

        self.draw(self.poly)
        self.stdout_w(self.buffer.as_string())
        self.buffer.swap()
