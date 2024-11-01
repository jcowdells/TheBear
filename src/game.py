import json
import math

import util
from src.render import Sampler, sampler_array
from src.geometry import X, Y, line_gradient, line_perpendicular, line_intersect, point_inside, line_square_length, \
    HALF_PI, vector_from_points, vector_perpendicular, vector_normalise, line_collision, vector_add, vector_from_angle, \
    point_add, point_collision, vector_project, vector_subtract, lerp_v, lerp_p

BOUNDS   = "BOUNDS"
TEXTURES = "TEXTURES"
OPTIONS  = "OPTIONS"

TEXTURE = "texture"
INDICES = "indices"

OUTLINE = "outline"

ANIMATION = "animation"

DURATION = "duration"
SAMPLER_INDEX = "sampler_index"

class EmptyAnimation:
    def tick(self):
        pass

    def reset(self):
        pass

    def get_current_state(self):
        return 0

class Animation(EmptyAnimation):
    def __init__(self, filepath):
        filepath = util.abspath(filepath)
        with open(filepath, "r") as file:
            raw_json = json.load(file)

        self._animation = {}
        self._cur_ticks = 0

        animation_steps = raw_json[ANIMATION]
        self._total_ticks = 0
        for step in animation_steps:
            duration = step[DURATION]
            sampler_index = step[SAMPLER_INDEX]
            self._animation[self._total_ticks] = sampler_index
            self._total_ticks += duration


    def tick(self):
        self._cur_ticks += 1
        if self._cur_ticks >= self._total_ticks:
            self._cur_ticks = 0

    def reset(self):
        self._cur_ticks = 0

    def get_current_state(self):
        keys = list(self._animation.keys())
        for key in keys:
            if key >= self._cur_ticks:
                return self._animation[key]
        return 0

class Entity:
    _id_counter = 0
    SAMPLERS = None
    DISPLAY_TYPE = None
    ANIMATION_PATH = None

    def __init__(self, position, rotation, hitbox_radius):
        self._id = Entity._id_counter
        Entity._id_counter += 1
        self._position = position
        self._rotation = rotation
        self._hitbox_radius = hitbox_radius
        self.__square_radius = hitbox_radius * hitbox_radius
        if self.ANIMATION_PATH is None:
            self._animation = EmptyAnimation()
        else:
            self._animation = Animation(self.ANIMATION_PATH)

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

    def get_id(self):
        return self._id

    def get_animation(self):
        return self._animation

class DisplayEntity:
    SPRITE  = 0
    TEXTURE = 1

    def __init__(self, position, rotation, size, samplers, entity_id, display_type):
        self._prev_position = position
        self._curr_position = position
        self._next_position = position

        self._prev_rotation = rotation
        self._curr_rotation = rotation
        self._next_rotation = rotation

        self._size = size
        self._samplers = samplers
        self._sampler_index = 0
        self._id = entity_id
        self._display_type = display_type

    def get_position(self, alpha):
        return lerp_p(self._prev_position, self._curr_position, alpha)

    def set_position(self, position):
        self._next_position = position

    def get_rotation(self, alpha):
        return lerp_v(self._prev_rotation, self._curr_rotation, alpha)

    def set_rotation(self, rotation):
        self._next_rotation = rotation

    def get_size(self):
        return self._size

    def get_sampler(self):
        return self._samplers[self._sampler_index]

    def set_sampler_index(self, sampler_index):
        self._sampler_index = sampler_index

    def get_id(self):
        return self._id

    def get_display_type(self):
        return self._display_type

    def update(self):
        self._prev_position = self._curr_position
        self._curr_position = self._next_position

        self._prev_rotation = self._curr_rotation
        self._curr_rotation = self._next_rotation

class Player(Entity):
    ROTATION_SPEED = 0.025
    MOVEMENT_SPEED = 0.15

    DISPLAY_TYPE = DisplayEntity.SPRITE
    SAMPLERS = sampler_array("res/textures/player")
    ANIMATION_PATH = "res/animations/player.json"

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

    def move_within_level(self, distance, level):
        force = vector_from_angle(self._rotation, distance)
        new_position = point_add(self._position, force)
        collided_lines = []

        count = 0
        for a, b in level.iter_lines():
            if line_collision(a, b, new_position, 1):
                normal = level.get_normal(count)
                projected_force = vector_project(force, normal)
                force = vector_subtract(force, projected_force)
                collided_lines.append(count)
            count += 1

        count = 0
        for a in level.get_bounds():
            if point_collision(a, new_position, 1):
                i_a, i_b = level.get_connected_lines(count)
                if i_a in collided_lines or i_b in collided_lines:
                    continue
                cur_dist = vector_from_points(a, new_position)
                escape_force = vector_normalise(cur_dist) * 1
                projected_force = vector_subtract(escape_force, cur_dist)
                force = vector_add(force, projected_force)
            count += 1

        if len(collided_lines) >= 2:
            force = (0, 0)

        self._position = point_add(self._position, force)

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