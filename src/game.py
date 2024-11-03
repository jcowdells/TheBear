import json
import math
import os

import util
from src.render import Sampler, sampler_array
from src.geometry import X, Y, A, B, line_gradient, line_perpendicular, line_intersect, point_inside, \
    line_square_length, \
    HALF_PI, vector_from_points, vector_perpendicular, vector_normalise, line_collision, vector_add, vector_from_angle, \
    point_add, point_collision, vector_project, vector_subtract, lerp_v, lerp_p, vector_angle, vector_multiply, \
    is_path_obstructed, line_angle, line_length

BOUNDS   = "BOUNDS"
TEXTURES = "TEXTURES"
ENTITIES = "ENTITIES"
OPTIONS  = "OPTIONS"

TEXTURE = "texture"
INDICES = "indices"

TYPE     = "type"
POSITION = "position"

OUTLINE = "outline"
EXIT    = "exit"
SPAWNPOINT = "spawnpoint"

ANIMATION = "animation"

DURATION = "duration"
SAMPLER_INDEX = "sampler_index"

MENU_TITLE = "MENU_TITLE"
DEFAULT_DESCRIPTION = "DEFAULT_DESCRIPTION"
MENU_ITEMS = "MENU_ITEMS"

TITLE = "title"
DESCRIPTION = "description"

SAVE_ID = "SAVE_ID"
SAVE_NAME = "SAVE_NAME"
LEVEL_INDEX = "LEVEL_INDEX"
COLLECTED_GOLD = "COLLECTED_GOLD"
CONDITION = "CONDITION"

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
        return self._animation[keys[-1]]

class Entity:
    @staticmethod
    def from_string(entity_type, *args):
        if entity_type == "Entity":
            return Entity(*args)
        elif entity_type == "Player":
            return Player(*args)
        elif entity_type == "Bear":
            return Bear(*args)
        elif entity_type == "HoneyJar":
            return HoneyJar(*args)

    MOVEMENT_SPEED = 0.15

    _id_counter = 0
    SAMPLERS = None
    DISPLAY_TYPE = None
    ANIMATION_PATH = None

    GRABBABLE = False

    def __init__(self, position, rotation, hitbox_radius):
        self._id = Entity._id_counter
        Entity._id_counter += 1
        self._position = position
        self._rotation = rotation
        self._hitbox_radius = hitbox_radius
        self._square_radius = hitbox_radius * hitbox_radius
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

    def look_at(self, position):
        self._rotation = line_angle(self._position, position)

    def move_towards(self, target, level):
        route = level.find_shortest_path(self._position, target, 1)
        if route:
            next_target = route[1].point
            self.look_at(next_target)
            self.move(-self.MOVEMENT_SPEED)

    def move(self, distance):
        delta_x = distance * math.cos(self._rotation + HALF_PI)
        delta_y = distance * math.sin(self._rotation + HALF_PI)
        self._position = (self._position[X] + delta_x, self._position[Y] + delta_y)

    def at_exit(self, level):
        return level.is_touching_exit(self._position, self._square_radius * 1.5)

    def is_touching(self, entity):
        distance = line_length(self._position, entity.get_position())
        return distance < self._hitbox_radius + entity.get_hitbox_radius()

    def get_hitbox_radius(self):
        return self._hitbox_radius

    def set_hitbox_radius(self, hitbox_radius):
        self._hitbox_radius = hitbox_radius
        self._square_radius = hitbox_radius * hitbox_radius

    def get_id(self):
        return self._id

    def get_animation(self):
        return self._animation

class DisplayEntity:
    SPRITE        = 0
    TEXTURE       = 1
    TAGGED_SPRITE = 2

    def __init__(self, position, rotation, size, samplers, entity_id, display_type, visible, display_name):
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
        self._visible = visible
        self._display_name = display_name

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

    def get_display_name(self):
        return self._display_name

    def get_visible(self):
        return self._visible

    def set_visible(self, visible):
        self._visible = visible

    def update(self):
        self._prev_position = self._curr_position
        self._curr_position = self._next_position

        self._prev_rotation = self._curr_rotation
        self._curr_rotation = self._next_rotation

class Player(Entity):
    ROTATION_SPEED = 0.025
    MOVEMENT_SPEED = 0.15

    REACH = 4.0

    DISPLAY_TYPE = DisplayEntity.SPRITE
    SAMPLERS = sampler_array("res/textures/player")
    ANIMATION_PATH = "res/animations/player.json"

    def __init__(self, position, rotation):
        super().__init__(position, rotation, 1)

    def get_angle(self):
        return math.atan2(self._position[Y], self._position[X])

    def get_distance(self):
        return math.sqrt(self._position[X]**2 + self._position[Y]**2)

    def hold_entity(self, entity):
        vector = vector_from_angle(self._rotation + math.pi, self._hitbox_radius + entity.get_hitbox_radius())
        entity.set_position(point_add(self._position, vector))

    def get_head_position(self):
        vector = vector_from_angle(self._rotation + math.pi, self._hitbox_radius)
        return point_add(self._position, vector)

    def move_within_level(self, distance, level):
        force = vector_from_angle(self._rotation, distance)
        new_position = point_add(self._position, force)
        collided_lines = []

        count = 0
        for a, b in level.iter_lines():
            if line_collision(a, b, new_position, self._square_radius):
                normal = level.get_normal(count)
                projected_force = vector_project(force, normal)
                force = vector_subtract(force, projected_force)
                collided_lines.append(count)
            count += 1

        count = 0
        for a in level.get_bounds():
            if point_collision(a, new_position, self._square_radius):
                i_a, i_b = level.get_connected_lines(count)
                if i_a in collided_lines or i_b in collided_lines:
                    continue
                cur_dist = vector_from_points(a, new_position)
                escape_force = vector_normalise(cur_dist) * self._square_radius
                projected_force = vector_subtract(escape_force, cur_dist)
                force = vector_add(force, projected_force)
            count += 1

        if len(collided_lines) >= 2:
            force = (0, 0)

        self._position = point_add(self._position, force)

class Bear(Entity):
    MOVEMENT_SPEED = 0.075

    DISPLAY_TYPE = DisplayEntity.TEXTURE
    SAMPLERS = sampler_array("res/textures/bear")
    ANIMATION_PATH = "res/animations/bear.json"

    def __init__(self, position, rotation):
        super().__init__(position, rotation, 1)

class HoneyJar(Entity):
    DISPLAY_TYPE = DisplayEntity.TAGGED_SPRITE

    SAMPLERS = [Sampler("res/textures/player/player0.tex")]

    GRABBABLE = True

    def __init__(self, position, rotation):
        super().__init__(position, rotation, 0.5)

    def __str__(self):
        return "Honey Jar"

class HoneySpill(Entity):
    DISPLAY_TYPE = DisplayEntity.TAGGED_SPRITE

    SAMPLERS = [Sampler("res/textures/mainmenu.tex")]

    def __init__(self, position, rotation):
        super().__init__(position, rotation, 0.5)

    def __str__(self):
        return "Honey Spill"

class Path:
    def __init__(self, point):
        self.point = point
        self._paths = []

    def add_path(self, path):
        self._paths.append(path)
        return self

    def find_shortest_path(self, end):
        shortest_distance = math.inf
        shortest_path = None
        for route in self.find_routes(end):
            current_distance = 0
            current_point = self.point
            for path in route:
                current_distance += line_square_length(current_point, path.point)
                current_point = path.point
            if current_distance < shortest_distance:
                shortest_distance = current_distance
                shortest_path = route
        return shortest_path

    def find_routes(self, end):
        for route in self.iter_routes(end):
            yield tuple(util.flatten(route))

    def iter_routes(self, end):
        if self.point == end:
            yield self
        for path in self._paths:
            for route in path.iter_routes(end):
                yield self, route

    def string(self, depth):
        out = (" " * depth) + str(self.point) + "\n"
        for path in self._paths:
            out += path.string(depth + 1)
        return out

    def __str__(self):
        return self.string(0)

class Level:
    def __init__(self, filepath, trust_path=False):
        if not trust_path:
            filepath = util.abspath(filepath)
        with open(filepath, "r") as file:
            raw_json = json.load(file)

        bounds = raw_json[BOUNDS]
        textures = []
        if TEXTURES in raw_json.keys():
            textures = raw_json[TEXTURES]
        options = {}
        if OPTIONS in raw_json.keys():
            options = raw_json[OPTIONS]
        entities = []
        if ENTITIES in raw_json.keys():
            entities = raw_json[ENTITIES]

        self.__bounds = []
        self.__pathfind_point_indices = []
        self.__pathfind_normals = []
        self.__pathfind_angles = []
        self.__connected_lines = []
        self.__normals = []
        used_samplers = {}
        self.__samplers = []
        self.__textures = []
        self.__entities = []
        self.__outline  = "#"
        self.__spawnpoint = (0, 0)
        self.__exit_index = None

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

        lines = list(self.iter_lines())
        for i in range(self.__num_bounds):
            line_a = lines[i - 1]
            line_b = lines[i]

            vec_a = vector_from_points(line_a[A], line_a[B])
            vec_b = vector_from_points(line_b[A], line_b[B])

            angle = vector_angle(vec_a, vec_b)
            if angle < 0:
                self.__pathfind_point_indices.append(i)
                vec_a = vector_perpendicular(self.get_normal(i - 1))
                vec_b = vector_perpendicular(self.get_normal(i))

                line_ea = point_add(line_a[A], vec_a), point_add(line_a[B], vec_a)
                line_eb = point_add(line_b[A], vec_b), point_add(line_b[B], vec_b)

                mx1, my1, c1 = line_gradient(line_ea[A], line_ea[B])
                mx2, my2, c2 = line_gradient(line_eb[A], line_eb[B])
                intersect = line_intersect(mx1, my1, c1, mx2, my2, c2)
                point = self.get_bound(i)
                normal = vector_from_points(point, intersect)

                self.__pathfind_normals.append(normal)
                self.__pathfind_angles.append((math.pi - angle) / 2)

        self.__num_pathfinders = len(self.__pathfind_point_indices)

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

        for entity in entities:
            entity_type = entity[TYPE]
            position = entity[POSITION][0], entity[POSITION][1]
            self.__entities.append((entity_type, position))

        for option, value in options.items():
            if option == OUTLINE:
                self.__outline = value[0]
            elif option == EXIT:
                self.__exit_index = value
            elif option == SPAWNPOINT:
                self.__spawnpoint = value[0], value[1]

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

    def get_pathfind_point(self, pathfind_index, hitbox_radius):
        point_index = self.__pathfind_point_indices[pathfind_index]
        point = self.get_bound(point_index)
        normal = self.__pathfind_normals[pathfind_index]
        normal = vector_multiply(normal, hitbox_radius)
        point = point_add(point, normal)
        return point

    def iter_pathfind_points(self, hitbox_radius):
        for i in range(self.__num_pathfinders):
            yield self.get_pathfind_point(i, hitbox_radius)

    def find_shortest_path(self, start, end, hitbox_radius):
        path = Path(start)
        self.find_paths(start, end, hitbox_radius, path)
        return path.find_shortest_path(end)

    def find_paths(self, start, end, hitbox_radius, path, visited_indices=None):
        if not self.is_path_obstructed(start, end, hitbox_radius):
            return path.add_path(Path(end))

        if visited_indices is None:
            visited_indices = []

        for i in range(self.__num_pathfinders):
            if i in visited_indices:
                continue
            point = self.get_pathfind_point(i, hitbox_radius)
            if not self.is_path_obstructed(start, point, hitbox_radius):
                updated_indices = list(visited_indices)
                updated_indices.append(i)
                sub_path = Path(point)
                sub_path = self.find_paths(point, end, hitbox_radius, sub_path, updated_indices)
                path.add_path(sub_path)

        return path

    def is_path_obstructed(self, start, end, hitbox_radius):
        obstructed = False
        for line in self.iter_lines():
            if is_path_obstructed(start, end, line, hitbox_radius):
                obstructed = True
                break
        return obstructed

    def get_connected_lines(self, bound_index):
        i_b = bound_index
        if bound_index == 0:
            i_a = self.__num_bounds - 1
        else:
            i_a = bound_index - 1
        return i_a, i_b

    def is_touching_exit(self, point, hitbox_radius):
        line = list(self.iter_lines())[self.get_exit_index()]
        return line_collision(*line, point, hitbox_radius)

    def iter_entities(self):
        for entity in self.__entities:
            yield entity

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

    def get_exit_index(self):
        return self.__exit_index

    def get_spawnpoint(self):
        return self.__spawnpoint

def level_array(directory):
    directory = util.abspath(directory)
    levels = []
    for file in sorted(os.listdir(directory)):
        levels.append(Level(os.path.join(directory, file), trust_path=True))
    return levels

class TextBox:
    _id_counter = 0

    def __init__(self, title, content, visible=True, max_width=0.5, max_height=0.5):
        self._title = title
        self._content = content
        self._max_width = max_width
        self._max_height = max_height
        self._id = TextBox._id_counter
        self._visible = visible
        TextBox._id_counter += 1

    def get_title(self):
        return self._title

    def get_content(self):
        return self._content

    def get_max_width(self):
        return self._max_width

    def get_max_height(self):
        return self._max_height

    def get_id(self):
        return self._id

    def get_visible(self):
        return self._visible

    def set_visible(self, visible):
        self._visible = visible

class Menu:
    _id_counter = 0

    @classmethod
    def from_file(cls, filepath, visible=True):
        filepath = util.abspath(filepath)
        with open(filepath, "r") as file:
            raw_json = json.load(file)

        menu_title = raw_json[MENU_TITLE]
        if DEFAULT_DESCRIPTION in raw_json.keys():
            default_description = raw_json[DEFAULT_DESCRIPTION]
        else:
            default_description = ""

        menu_items = raw_json[MENU_ITEMS]
        menu = cls(menu_title, default_description, visible)
        for item in menu_items:
            title = item[TITLE]
            if DESCRIPTION in item.keys():
                description = item[DESCRIPTION]
            else:
                description = None
            menu.add_item(title, description)
        return menu

    def __init__(self, title, default_description="", visible=True):
        self._title = title
        self._active_index = 0
        self._id = Menu._id_counter
        Menu._id_counter += 1
        self.__default_description = default_description
        self.__items = []
        self._visible = visible
        self._formatting = {}

    def get_title(self):
        return self._title

    def add_item(self, item_name, item_description=None):
        self.__items.append((item_name, item_description))

    def remove_item(self, item_index):
        self.__items.pop(item_index)

    def get_item_name(self, index):
        return self.__items[index][0]

    def get_item_description(self, index):
        description = self.__items[index][1]
        if description is None:
            return self.__default_description
        else:
            if index in self._formatting.keys():
                return description.format(*self._formatting[index])
            else:
                return description

    def get_num_items(self):
        return len(self.__items)

    def get_item_index_by_name(self, item_name):
        for i in range(len(self.__items)):
            item = self.__items[i]
            if item_name == item[0]:
                return i

    def get_id(self):
        return self._id

    def get_visible(self):
        return self._visible

    def set_visible(self, visible):
        self._visible = visible

    def get_active_index(self):
        return self._active_index

    def set_active_index(self, index):
        self._active_index = index

    def set_formatting(self, index, formatting):
        self._formatting[index] = formatting

class MenuInterface:
    def __init__(self, num_items, active_index, menu_id):
        self.num_items = num_items
        self.active_index = active_index
        self._menu_id = menu_id

    def get_id(self):
        return self._menu_id

class ProgressBar:
    _id_counter = 0

    def __init__(self, position, width, visible=True):
        self._position = position
        self._width = width
        self._id = ProgressBar._id_counter
        ProgressBar._id_counter += 1
        self._progress = 0
        self._visible = visible

    def get_progress(self):
        return self._progress

    def set_progress(self, progress):
        self._progress = progress

    def get_position(self):
        return self._position

    def set_position(self, position):
        self._position = position

    def get_width(self):
        return self._width

    def get_id(self):
        return self._id

    def get_visible(self):
        return self._visible

    def set_visible(self, visible):
        self._visible = visible

class Save:
    _id_counter = 0

    PLAYING = "playing"
    LOST = "lost"
    WON = "won"

    @classmethod
    def from_file(cls, filepath, trust_path=False):
        if not trust_path:
            filepath = util.abspath(filepath)
        with open(filepath, "r") as file:
            raw_json = json.load(file)

        save_id = raw_json[SAVE_ID]
        save_name = raw_json[SAVE_NAME]
        level_index = raw_json[LEVEL_INDEX]
        collected_gold = raw_json[COLLECTED_GOLD]
        condition = raw_json[CONDITION]
        return cls(save_name, level_index, collected_gold, condition, save_id)

    def __init__(self, save_name, level_index, collected_gold, condition=PLAYING, save_id=None):
        if save_id is None:
            self._id = Save._id_counter
            Save._id_counter += 1
        else:
            self._id = save_id
            if save_id >= Save._id_counter:
                Save._id_counter = save_id + 1
        self._save_name = save_name
        self._level_index = level_index
        self._collected_gold = collected_gold
        self._condition = condition

    def get_id(self):
        return self._id

    def get_save_name(self):
        return self._save_name

    def get_level_index(self):
        return self._level_index

    def set_level_index(self, level_index):
        self._level_index = level_index

    def get_collected_gold(self):
        return self._collected_gold

    def set_collected_gold(self, collected_gold):
        self._collected_gold = collected_gold

    def get_condition(self):
        return self._condition

    def set_condition(self, condition):
        self._condition = condition

    def save(self, directory, trust_path=False):
        if not trust_path:
            directory = util.abspath(directory)

        raw_json = {
            SAVE_ID: self._id,
            SAVE_NAME: self._save_name,
            LEVEL_INDEX: self._level_index,
            COLLECTED_GOLD: self._collected_gold,
            CONDITION: self._condition
        }

        filepath = os.path.join(directory, f"save_{self._id}.json")

        with open(filepath, "w", encoding="utf-8") as file:
            json.dump(raw_json, file, ensure_ascii=False)

    def delete(self, directory, trust_path=False):
        if not trust_path:
            directory = util.abspath(directory)

        filepath = os.path.join(directory, f"save_{self._id}.json")

        if os.path.exists(filepath):
            os.remove(filepath)

def saves_array(directory):
    directory = util.abspath(directory)
    saves = []
    for file in sorted(os.listdir(directory)):
        saves.append(Save.from_file(os.path.join(directory, file), trust_path=True))
    return saves

def save_all(saves, directory):
    directory = util.abspath(directory)
    for save in saves:
        save.save(directory, trust_path=True)