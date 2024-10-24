import random
import time

from src.console import Console
from src.geometry import *
from ext.converter import get_gradient_color

def triangle_signed_area(point_a, point_b, point_c):
    return (point_b.x - point_a.x) * (point_c.y - point_a.y) - (point_b.y - point_a.y) * (point_c.x - point_a.x)

def triangle_uvw(a, b, c, f):
    signed_area = triangle_signed_area(a, b, c)

    d = (b.y - c.y) * (a.x - c.x) + (c.x - b.x) * (a.y - c.y)
    u = ((b.y - c.y) * (f.x - c.x) + (c.x - b.x) * (f.y - c.y)) / d
    v = ((c.y - a.y) * (f.x - c.x) + (a.x - c.x) * (f.y - c.y)) / d
    w = 1 - u - v

    return u, v, w

class Texture:
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
        if x <= 0: x = 0
        if x >= self.get_width(): x = self.get_width() - 1
        if y <= 0: y = 0
        if y >= self.get_height(): y = self.get_height() - 1
        return self.__data[y * self.__width + x]

    def sample(self, x, y):
        sx = round(x * self.get_width())
        sy = round(y * self.get_height())

        return self.get_pixel(sx, sy)

class Drawable:
    def draw(self, console_gui):
        pass

class Polygon(Drawable):
    def __init__(self, *args, fill="#"):
        len_args = len(args)
        if len_args < 3:
            raise ValueError("A polygon must have at least 3 vertices!")
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

class Triangle:
    @property
    def __points(self):
        return self.__point_a, self.__point_b, self.__point_c

    def __init__(self, point_a, point_b, point_c, uv_a, uv_b, uv_c):
        self.__point_a = point_a
        self.__point_b = point_b
        self.__point_c = point_c
        self.__uv_a = uv_a
        self.__uv_b = uv_b
        self.__uv_c = uv_c

    def iter_x(self):
        for point in self.__points:
            yield point.x

    def iter_y(self):
        for point in self.__points:
            yield point.y

    def get_bbox(self):
        min_x = None
        max_x = None
        for x in self.iter_x():
            if min_x is None or x < min_x:
                min_x = x
            if max_x is None or x > max_x:
                max_x = x

        min_y = None
        max_y = None
        for y in self.iter_y():
            if min_y is None or y < min_y:
                min_y = y
            if max_y is None or y > max_y:
                max_y = y

        return Point(min_x, min_y), Point(max_x, max_y)

    def contains_point(self, point_p):
        check_a = triangle_signed_area(self.__point_a, self.__point_b, point_p)
        check_b = triangle_signed_area(self.__point_b, self.__point_c, point_p)
        check_c = triangle_signed_area(self.__point_c, self.__point_a, point_p)

        return check_a >= 0 and check_b >= 0 and check_c >= 0

    def get_uv(self, point_p):
        uf, vf, wf = triangle_uvw(*self.__points, point_p)

        u = self.__uv_a[0] * uf + self.__uv_b[0] * vf + self.__uv_c[0] * wf
        v = self.__uv_a[1] * uf + self.__uv_b[1] * vf + self.__uv_c[1] * wf

        return Point(u, v)

    def rotate(self, centre, angle):
        for point in self.__points:
            point.rotation = angle
            point.rotation_centre = centre

class Image(Drawable):
    def __init__(self, point_a, point_b, point_c, point_d, texture):
        self.__point_a = point_a
        self.__point_b = point_b
        self.__point_c = point_c
        self.__point_d = point_d

        self.__triangle_a = Triangle(point_a, point_b, point_c, (0, 0), (1, 0), (1, 1))
        self.__triangle_b = Triangle(point_a, point_c, point_d, (0, 0), (1, 1), (0, 1))

        self.__texture = texture

    def draw(self, console_gui):
        console_gui.draw_sampler(self.__triangle_a, self.__texture)
        console_gui.draw_sampler(self.__triangle_b, self.__texture)

    def rotate(self, centre, angle):
        self.__triangle_a.rotate(centre, angle)
        self.__triangle_b.rotate(centre, angle)

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
        self.point_a = Point(10, 10)
        self.point_b = Point(110, 10)
        self.point_c = Point(110, 80)
        self.point_d = Point(10, 80)

        self.centre = Point(55, 45)

        #self.triangle = Triangle(self.point_b, self.point_a, self.point_c)

        self.count = 0

        self.sampler = Texture("res/me.bin")
        self.image = Image(self.point_a, self.point_b, self.point_c, self.point_d, self.sampler)


    def configure_event(self, event):
        self.buffer.resize(self.get_width_chars(), self.get_height_chars())

    def draw_line(self, line, fill="#"):
        for x, y in line.get_points():
            self.buffer.try_set(x, y, ord(fill))

    def draw_image(self, image):
        for x in range(image.get_width()):
            for y in range(image.get_height()):
                self.buffer.try_set(x, y, image.get_pixel(x, y))

    def draw_triangle(self, triangle, fill="#"):
        bbox = triangle.get_bbox()
        min_x = bbox[0].x
        min_y = bbox[0].y
        max_x = bbox[1].x
        max_y = bbox[1].y

        for x in range(min_x, max_x + 1):
            for y in range(min_y, max_y + 1):
                if triangle.contains_point(Point(x, y)):
                    self.buffer.try_set(x, y, ord(fill))

    def draw_sampler(self, triangle, image):
        bbox = triangle.get_bbox()
        min_x = bbox[0].x
        min_y = bbox[0].y
        max_x = bbox[1].x
        max_y = bbox[1].y

        for x in range(min_x, max_x + 1):
            for y in range(min_y, max_y + 1):
                point = Point(x, y)
                if triangle.contains_point(Point(x, y)):
                    uv = triangle.get_uv(point)
                    char = image.sample(uv.x, uv.y)
                    self.buffer.try_set(x, y, char)

    def draw(self, drawable):
        drawable.draw(self)

    def main(self):
        self.count += 0.05
        #self.point_c.x = round(self.count)

        self.image.rotate(self.centre, self.count)
        self.draw(self.image)

        #self.draw_image(self.sampler)
        self.stdout_w(self.buffer.as_string())
        self.buffer.swap()
