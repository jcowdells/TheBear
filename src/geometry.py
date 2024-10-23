from enum import Enum, auto

class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y

class GradientMode(Enum):
    F_X = auto()
    F_Y = auto()

class Line:
    def __init__(self, point_a, point_b):
        x1 = point_a.x
        x2 = point_b.x
        if x1 > x2:
            self.__min_x = x2
            self.__max_x = x1
        else:
            self.__min_x = x1
            self.__max_x = x2

        y1 = point_a.y
        y2 = point_b.y
        if y1 > y2:
            self.__min_y = y2
            self.__max_y = y1
        else:
            self.__min_y = y1
            self.__max_y = y2

        delta_x = x1 - x2
        delta_y = y1 - y2

        if (delta_x == 0) and (delta_y == 0):
            self.__grad_mode = GradientMode.F_X
            self.__gradient  = 1
            self.__intercept = y1 - self.__gradient * x1
        elif delta_x > delta_y:
            self.__grad_mode = GradientMode.F_X
            self.__gradient  = delta_y / delta_x
            self.__intercept = y1 - self.__gradient * x1
        else:
            self.__grad_mode = GradientMode.F_Y
            self.__gradient  = delta_x / delta_y
            self.__intercept = x1 - self.__gradient * y1

    def get_points(self):
        if self.__grad_mode == GradientMode.F_X:
            min_i = self.__min_x
            max_i = self.__max_x
            min_o = self.__min_y
            max_o = self.__max_y
        else:
            min_i = self.__min_y
            max_i = self.__max_y
            min_o = self.__min_x
            max_o = self.__max_x

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
