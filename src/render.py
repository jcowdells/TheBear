import os

from console import Console
from geometry import *
import util

ALIGN_LEFT   = 0
ALIGN_TOP    = 0
ALIGN_RIGHT  = 1
ALIGN_BOTTOM = 1
ALIGN_CENTER = 2

SPACE_CHAR = ord(" ")

# An image sampler, allows .tex files to be accessed by direct pixel, or by a range 0-1
class Sampler:
    # Initialise class using a filepath as the source data
    def __init__(self, filepath, trust_path=False):
        self.__width = 0
        self.__height = 0
        self.__data = None
        if not trust_path:
            filepath = util.abspath(filepath)
        with open(filepath, 'rb') as file:
            index = -2
            while byte := file.read(1):
                # First two bytes represent the width and height of the texture
                if index == 0:
                    self.__data = bytearray(self.__width * self.__height * 8)
                if index == -2:
                    self.__width = int.from_bytes(byte, 'little')
                elif index == -1:
                    self.__height = int.from_bytes(byte, 'little')
                else:
                    self.__data[index] = int.from_bytes(byte, 'little')
                index += 1
        while len(self.__data) < self.__width * self.__height:
            self.__data.append(ord(" "))

    # Get a pixel at a certain coordinate
    def get_pixel(self, x, y):
        # Clamp values between 0 and size - 1
        if x <= 0:
            x = 0
        if x >= self.__width:
            x = self.__height - 1
        if y <= 0:
            y = 0
        if y >= self.__height:
            y = self.__height - 1
        return self.__data[y * self.__width + x]

    # Get value by using floats between 0 and 1
    def sample(self, x, y):
        sx = round(x * self.__width)
        sy = round(y * self.__height)
        return self.get_pixel(sx, sy)

# Create an array of samplers - uses all files in a directory
def sampler_array(directory):
    directory = util.abspath(directory)
    samplers = []
    for file in sorted(os.listdir(directory)):
        samplers.append(Sampler(os.path.join(directory, file), trust_path=True))
    return samplers

# Buffer class, makes an array of bytes that can be converted to a string to be rendered
class Buffer:
    # Initialise the buffer with a width and height
    def __init__(self, width, height):
        self.__width = width
        self.__height = height
        self.__buffer = bytearray(width * height)

    # Change the size of the buffer, necessary if the window is resized
    def resize(self, width, height):
        if width < 0: width = 0
        if height < 0: height = 0
        self.__width = width
        self.__height = height
        self.__buffer = bytearray(width * height)

    # Clear the data contained in the buffer
    def swap(self):
        self.__buffer = bytearray(self.__width * self.__height)

    # Get the data contained at a position in the buffer
    def get(self, x, y):
        index = y * self.__width + x
        return self.__buffer[index]

    # Set the data at a position in the buffer
    def set(self, x, y, value):
        index = y * self.__width + x
        self.__buffer[index] = value

    # Try and set the data, and fail gracefully if the coordinate is outside the buffer
    def try_set(self, x, y, value):
        if (0 <= x < self.__width) and (0 <= y < self.__height):
            self.set(x, y, value)

    # Return the buffer data as a string
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

    # Return the length of the buffer
    def __len__(self):
        return len(self.__buffer)

# Console GUI class, allows console to render lines, triangles, samplers or rectangles
class ConsoleGUI(Console):
    # Initialise with a width, height and an x, y coordinate
    def __init__(self, width, height, x, y):
        super().__init__(width, height, x, y, 5, fg="#22BB00")
        self._buffer = Buffer(self.get_width_chars(), self.get_height_chars())

    # Called when the window changes size, meaning the buffer needs to be resized
    def configure_event(self, event):
        self._buffer.resize(self.get_width_chars(), self.get_height_chars())

    # Draw a line between two points
    def draw_line(self, a, b, fill="#"):
        fill = ord(fill)
        for x, y in line_iter_points(a, b):
            self._buffer.try_set(x, y, fill)

    # Draw a triangle using barycentric coordinates
    def draw_triangle(self, a, b, c, fill="#"):
        min_x, min_y, max_x, max_y = triangle_bbox(a, b, c)
        fill = ord(fill)
        for x in range(min_x, max_x + 1):
            for y in range(min_y, max_y + 1):
                if triangle_contains(a, b, c, (x, y)):
                    self._buffer.try_set(x, y, fill)

    # Draw a sampler triangle
    def draw_sampler(self, a, b, c, uv_a, uv_b, uv_c, sampler):
        min_x, min_y, max_x, max_y = triangle_bbox(a, b, c)
        width_chars = self.get_width_chars()
        height_chars = self.get_height_chars()
        min_x = max(0, min_x)
        min_y = max(0, min_y)
        max_x = min(width_chars - 1, max_x)
        max_y = min(height_chars - 1, max_y)
        # It is wasteful to calculate pixels that will not be visible, so they are clipped
        for x in range(min_x, max_x + 1):
            for y in range(min_y, max_y + 1):
                if triangle_contains(a, b, c, (x, y)):
                    u, v = triangle_uv(a, b, c, uv_a, uv_b, uv_c, (x, y))
                    fill = sampler.sample(u, v)
                    if fill != SPACE_CHAR:
                        self._buffer.try_set(x, y, fill)

    # Draw a single character to the screen
    def draw_character(self, a, fill="#"):
        self._buffer.try_set(a[X], a[Y], ord(fill))

    # Draw text to the screen, with some options of where it should be drawn
    def draw_text(self, a, text, align_x=ALIGN_CENTER, align_y=ALIGN_CENTER, justify=ALIGN_CENTER):
        lines = text.split("\n")
        max_width = 0
        max_height = len(lines)
        for i in range(max_height):
            len_line = len(lines[i])
            if len_line > max_width:
                max_width = len_line

        for i in range(max_height):
            # Pad the string depending on the justify option
            # Spaces are NOT used to pad, as then it cannot be distinguished from actual spaces in the string
            if justify == ALIGN_LEFT:
                lines[i] = lines[i].ljust(max_width, "\0")
            elif justify == ALIGN_RIGHT:
                lines[i] = lines[i].rjust(max_width, "\0")
            elif justify == ALIGN_CENTER:
                lines[i] = lines[i].center(max_width, "\0")

        mod_x = a[X]
        mod_y = a[Y]

        # Adjust start coordinates based on the alignment
        if align_x == ALIGN_RIGHT:
            mod_x = a[X] - max_width + 1
        elif align_x == ALIGN_CENTER:
            mod_x = a[X] - max_width // 2 + 1

        if align_y == ALIGN_BOTTOM:
            mod_y = a[Y] - max_height + 1
        elif align_y == ALIGN_CENTER:
            mod_y = a[Y] - max_height // 2

        # Draw character by character, line by line
        for y in range(max_height):
            for x in range(max_width):
                draw_x = x + mod_x
                draw_y = y + mod_y
                draw_c = lines[y][x]
                if draw_c != "\0":
                    self._buffer.try_set(draw_x, draw_y, ord(draw_c))

    # Draw a sprite, essentially a non-rotating texture
    def draw_sprite(self, a, b, sampler):
        width = b[X] - a[X]
        height = b[Y] - a[Y]
        if width == 0 or height == 0:
            return

        # Saves processing power, do not need to check if point lies within a triangle etc.
        for y in range(height + 1):
            v = y / height
            for x in range(width + 1):
                u = x / width
                fill = sampler.sample(u, v)
                if fill != SPACE_CHAR:
                    self._buffer.try_set(x + a[X], y + a[Y], fill)

    # Draw a rectangle
    def draw_rectangle(self, a, b, fill="#"):
        width = b[X] - a[X]
        height = b[Y] - a[Y]
        fill = ord(fill)
        for y in range(height + 1):
            for x in range(width + 1):
                self._buffer.try_set(x + a[X], y + a[Y], fill)

    # Draw a circle
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
                    # If distance from centre to point is within the radius of the circle
                    self._buffer.try_set(x + a[X], y + a[Y], fill)

    # 'Swap buffers' actually just prints the buffer to the screen, and clears the buffer for writing
    # The name is borrowed from 3D graphics APIs such as OpenGL and DirectX
    def swap_buffers(self):
        self.stdout_w(self._buffer.as_string())
        self._buffer.swap()
