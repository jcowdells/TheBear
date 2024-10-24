import math
from enum import Enum, auto

class Point:
    @property
    def x(self):
        self.__update_rotated_point()
        return self.__rx

    @x.setter
    def x(self, value):
        self.__x = value
        self.__update_rotated_point(force=True)

    @property
    def y(self):
        self.__update_rotated_point()
        return self.__ry

    @y.setter
    def y(self, value):
        self.__y = value
        self.__update_rotated_point(force=True)

    def __init__(self, x, y):
        self.__x = x
        self.__y = y

        self.__rx = x
        self.__ry = y

        self.rotated = False
        self.rotation = 0
        self.rotation_centre = None

        self.__prev_rotation = 0
        self.__prev_rotation_centre = None

    def __update_rotated_point(self, force=False):
        if self.rotation != self.__prev_rotation or self.rotation_centre != self.__prev_rotation_centre or force:
            if self.rotation_centre is None:
                self.__rx = self.__x
                self.__ry = self.__y
                return

            c_x = self.__x - self.rotation_centre.x
            c_y = self.__y - self.rotation_centre.y
            r_x = c_x * math.cos(self.rotation) - c_y * math.sin(self.rotation)
            r_y = c_x * math.sin(self.rotation) + c_y * math.cos(self.rotation)
            self.__rx = round(r_x + self.rotation_centre.x)
            self.__ry = round(r_y + self.rotation_centre.y)

            self.__prev_rotation = self.rotation
            self.__prev_rotation_centre = self.rotation_centre

    def __sub__(self, other):
        return Point(self.x - other.x, self.y - other.y)

    def __eq__(self, other):
        if other is None:
            return False
        return self.x == other.x and self.y == other.y

    def __str__(self):
        return f"({self.x}, {self.y})"

class AccessorRegion(Enum):
    X = auto()
    Y = auto()

class AccessorMode(Enum):
    MIN = auto()
    MAX = auto()

class AccessorType(Enum):
    MIN_X = AccessorMode.MIN, AccessorRegion.X
    MAX_X = AccessorMode.MAX, AccessorRegion.X
    MIN_Y = AccessorMode.MIN, AccessorRegion.Y
    MAX_Y = AccessorMode.MAX, AccessorRegion.Y

class Accessor(int):
    def __new__(cls, point_a=None, point_b=None, accessor=None):
        if point_a is None or point_b is None or accessor is None:
            raise ValueError("Arguments 'point_a' 'point_b' and 'accessor' must not be None!")

        i = int.__new__(cls, 0)
        i.__point_a = point_a
        i.__point_b = point_b
        i.__accessor = accessor

        i.__accessor_mode = accessor.value[0]
        i.__accessor_region = accessor.value[1]

        return i

    def __int__(self):
        if self.__accessor_region == AccessorRegion.X:
            c_a = self.__point_a.x
            c_b = self.__point_b.x
        else:
            c_a = self.__point_a.y
            c_b = self.__point_b.y

        if self.__accessor_mode == AccessorMode.MIN:
            if c_a < c_b:
                return c_a
            else:
                return c_b
        else:
            if c_a > c_b:
                return c_a
            else:
                return c_b

class GradientMode(Enum):
    F_X = auto()
    F_Y = auto()

class Line:
    @property
    def __gradient(self):
        return self.__calculate_gradient()

    def __init__(self, point_a, point_b):
        self.__point_a = point_a
        self.__point_b = point_b

        self.__min_x = Accessor(point_a=point_a, point_b=point_b, accessor=AccessorType.MIN_X)
        self.__max_x = Accessor(point_a=point_a, point_b=point_b, accessor=AccessorType.MAX_X)
        self.__min_y = Accessor(point_a=point_a, point_b=point_b, accessor=AccessorType.MIN_Y)
        self.__max_y = Accessor(point_a=point_a, point_b=point_b, accessor=AccessorType.MAX_Y)

        self.__cached_gradient = None
        self.__prev_delta = None
        self.__calculate_gradient()

    def __calculate_gradient(self):
        delta = self.__point_a - self.__point_b
        if delta == self.__prev_delta:
            return self.__cached_gradient

        self.__prev_delta = delta

        if (delta.x == 0) and (delta.y == 0):
            self.__grad_mode = GradientMode.F_X
            gradient = 1
            self.__intercept = self.__point_a.y - gradient * self.__point_a.x
        elif math.fabs(delta.x) > math.fabs(delta.y):
            self.__grad_mode = GradientMode.F_X
            gradient = delta.y / delta.x
            self.__intercept = self.__point_a.y - gradient * self.__point_a.x
        else:
            self.__grad_mode = GradientMode.F_Y
            gradient = delta.x / delta.y
            self.__intercept = self.__point_a.x - gradient * self.__point_a.y

        self.__cached_gradient = gradient
        return gradient

    def get_points(self):
        if self.__grad_mode == GradientMode.F_X:
            min_i = int(self.__min_x)
            max_i = int(self.__max_x)
            min_o = int(self.__min_y)
            max_o = int(self.__max_y)
        else:
            min_i = int(self.__min_y)
            max_i = int(self.__max_y)
            min_o = int(self.__min_x)
            max_o = int(self.__max_x)

        for i in range(min_i, max_i + 1):
            f_out = round(self.__grad_func(i))
            if not (min_o <= f_out <= max_o):
                continue
            if self.__grad_mode == GradientMode.F_X:
                yield i, f_out
            else:
                yield f_out, i

    def __grad_func(self, i):
        return self.__gradient * i + self.__intercept

    def __str__(self):
        if self.__grad_mode == GradientMode.F_X:
            fstr = "y = {}x + {}"
        else:
            fstr = "x = {}y + {}"
        return fstr.format(self.__gradient, self.__intercept)
