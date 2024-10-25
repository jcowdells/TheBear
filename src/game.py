import json
import math

import util
from src.render import Sampler
from src.geometry import X, Y

BOUNDS   = "BOUNDS"
TEXTURES = "TEXTURES"
OPTIONS  = "OPTIONS"

TEXTURE = "texture"
INDICES = "indices"

OUTLINE = "outline"

HALF_PI = math.pi * 0.5

class Entity:
    def __init__(self, position, rotation, hitbox_radius):
        self._position = position
        self._rotation = rotation
        self._hitbox_radius = hitbox_radius

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
        used_samplers = {}
        self.__samplers = []
        self.__textures = []
        self.__outline  = "#"

        try:
            for x, y in bounds:
                self.__bounds.append((x, y))
        except ValueError:
            raise SyntaxError("Coordinate must contain only two values")

        texture_file = "<None>"
        try:
            for texture in textures:
                texture_file = texture[TEXTURE]

                if texture_file in used_samplers.keys():
                    sampler_index = used_samplers[texture_file]
                else:
                    sampler_index = len(self.__samplers)
                    self.__samplers.append(Sampler(util.abspath(texture_file)))
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

    def get_num_textures(self):
        return len(self.__textures)

    def get_texture(self, texture_index):
        return self.__textures[texture_index]

    def get_outline(self):
        return self.__outline
