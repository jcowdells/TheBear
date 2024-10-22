import random

from src.console import Console

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

    def get_width(self):
        return self.__width

    def get_height(self):
        return self.__height

    def as_string(self):
        string = ""
        count = 0
        for byte in self.__buffer:
            string += chr(byte)
            count += 1
            if count == self.__width:
                string += "\n"
                count = 0
        return string

class ConsoleGUI(Console):
    def __init__(self, width, height, x, y):
        super().__init__(width, height, x, y, 10, fg="#22BB00")
        self.buffer = Buffer(self.get_width_chars(), self.get_height_chars())

    def configure_event(self, event):
        self.buffer.resize(self.get_width_chars(), self.get_height_chars())

    def main(self):
        for x in range(self.buffer.get_width()):
            for y in range(self.buffer.get_height()):
                self.buffer.set(x, y, random.randint(65, 75))
        self.stdout_w(self.buffer.as_string())
