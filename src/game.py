import json
import math

import util
from src.render import Sampler
from src.geometry import X, Y, line_gradient, line_perpendicular, line_intersect, point_inside, line_square_length, \
    HALF_PI, vector_from_points, vector_perpendicular, vector_normalise, line_collision, vector_add

BOUNDS   = "BOUNDS"
TEXTURES = "TEXTURES"
OPTIONS  = "OPTIONS"

TEXTURE = "texture"
INDICES = "indices"

OUTLINE = "outline"

class Entity:
    def __init__(self, position, rotation, hitbox_radius):
        self._position = position
        self._rotation = rotation
        self._hitbox_radius = hitbox_radius
        self.__square_radius = hitbox_radius * hitbox_radius

    def get_position(self):
        return self._position

    def set_position(self, position):
        self._position = position

    def get_rotation(self):
        return self._rotation

    def set_rotation(self, rotation):
        self._rotation = rotation

    def rotate(self, rotation):
        self._rotation += rotation

    def get_hitbox_radius(self):
        return self._hitbox_radius

    def set_hitbox_radius(self, hitbox_radius):
        self._hitbox_radius = hitbox_radius
        self.__square_radius = hitbox_radius * hitbox_radius

    def line_collision(self, a, b):
        return line_collision(a, b, self._position, self.__square_radius)

class Player(Entity):
    def __init__(self, position, rotation):
        super().__init__(position, rotation, 1)

    def get_angle(self):
        return math.atan2(self._position[Y], self._position[X])

    def get_distance(self):
        return math.sqrt(self._position[X]**2 + self._position[Y]**2)

    def move(self, distance):
        delta_x = distance * math.cos(self._rotation + HALF_PI)
        delta_y = distance * math.sin(self._rotation + HALF_PI)
        self._position = (self._position[X] + delta_x, self._position[Y] + delta_y)

class Level:
    def __init__(self, filepath):
        filepath = util.abspath(filepath)
        with open(filepath, "r") as file:
            raw_json = json.load(file)

        bounds = raw_json[BOUNDS]
        textures = raw_json[TEXTURES]
        options = {}
        if OPTIONS in raw_json.keys():
            options = raw_json[OPTIONS]

        self.__bounds = []
        self.__connected_lines = []
        self.__normals = []
        used_samplers = {}
        self.__samplers = []
        self.__textures = []
        self.__outline  = "#"

        try:
            for x, y in bounds:
                self.__bounds.append((x, y))
        except ValueError:
            raise SyntaxError("Coordinate must contain only two values")

        self.__num_bounds = len(self.__bounds)

        for a, b in self.iter_lines():
            v = vector_from_points(b, a)
            v = vector_normalise(v)
            self.__normals.append(v)

        texture_file = "<None>"
        try:
            for texture in textures:
                texture_file = texture[TEXTURE]

                if texture_file in used_samplers.keys():
                    sampler_index = used_samplers[texture_file]
                else:
                    sampler_index = len(self.__samplers)
                    self.__samplers.append(Sampler(texture_file))
                    used_samplers[texture_file] = sampler_index

                c1, c2, c3, c4 = texture[INDICES]
                self.__textures.append((sampler_index, c1, c2, c3, c4))
        except KeyError:
            raise SyntaxError("Malformed level file!")
        except FileNotFoundError:
            raise SyntaxError(f"Unknown texture file '{texture_file}'!")

        for option, value in options.items():
            if option == OUTLINE:
                self.__outline = value[0]

    def get_bounds(self):
        return self.__bounds

    def iter_lines(self):
        for i in range(self.__num_bounds):
            a = self.__bounds[i]
            if i == self.__num_bounds - 1:
                b = self.__bounds[0]
            else:
                b = self.__bounds[i + 1]
            yield a, b

    def get_connected_lines(self, bound_index):
        i_b = bound_index
        if bound_index == 0:
            i_a = self.__num_bounds - 1
        else:
            i_a = bound_index - 1
        return i_a, i_b

    def get_bound(self, bound_index):
        return self.__bounds[bound_index]

    def get_normal(self, normal_index):
        return self.__normals[normal_index]

    def get_num_textures(self):
        return len(self.__textures)

    def get_texture(self, texture_index):
        return self.__textures[texture_index]

    def get_sampler(self, sampler_index):
        return self.__samplers[sampler_index]

    def get_outline(self):
        return self.__outline

class Menu:
    def __init__(self, title, default_description=""):
        self.title = title
        self.__default_description = default_description
        self.__items = []

    def add_item(self, item_name, item_description=None):
        self.__items.append((item_name, item_description))

    def remove_item(self, item_name):
        index = self.get_item_index_by_name(item_name)
        self.__items.pop(index)

    def get_item_name(self, index):
        return self.__items[index][0]

    def get_item_description(self, index):
        description = self.__items[index][1]
        if description is None:
            return self.__default_description
        else:
            return description

    def get_num_items(self):
        return len(self.__items)

    def get_item_index_by_name(self, item_name):
        for i in range(len(self.__items)):
            item = self.__items[i]
            if item_name == item[0]:
                return i