import json
import math
import os

import util
from render import Sampler, sampler_array
from geometry import X, Y, A, B, line_gradient,  line_intersect, line_square_length, \
    HALF_PI, vector_from_points, vector_perpendicular, vector_normalise, line_collision, vector_add, vector_from_angle, \
    point_add, point_collision, vector_project, vector_subtract, lerp_v, lerp_p, vector_angle, vector_multiply, \
    is_path_obstructed, line_angle, line_length

# Define some strings to avoid spelling mistakes
BOUNDS   = "BOUNDS"
TEXTURE_BOUNDS = "TEXTURE_BOUNDS"
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

# An empty animation, represents no animation, but avoids using None as the methods still return
class EmptyAnimation:
    def tick(self):
        pass

    def reset(self):
        pass

    def get_current_state(self):
        return 0 # Return 0, so that the first (and only) texture in the animation sequence is used for un-animated entities

# An animation, based on an empty animation so it can override the empty methods
class Animation(EmptyAnimation):
    # Initialise from a filepath
    def __init__(self, filepath, trust_path=False):
        if not trust_path:
            filepath = util.abspath(filepath)

        with open(filepath, "r") as file:
            raw_json = json.load(file)

        self.__animation = {}
        self.__cur_ticks = 0

        animation_steps = raw_json[ANIMATION]
        self.__total_ticks = 0
        for step in animation_steps: # Find the cumulative time of the animation
            duration = step[DURATION]
            sampler_index = step[SAMPLER_INDEX]
            self.__animation[self.__total_ticks] = sampler_index
            self.__total_ticks += duration

    # Move the animation forward one physics timestep
    def tick(self):
        self.__cur_ticks += 1
        if self.__cur_ticks >= self.__total_ticks:
            self.__cur_ticks = 0

    # Set the animation back to 0
    def reset(self):
        self.__cur_ticks = 0

    # Return the animation index based on the current tick
    def get_current_state(self):
        keys = list(self.__animation.keys())
        for key in keys:
            if key >= self.__cur_ticks:
                return self.__animation[key]
        return self.__animation[keys[0]]

class Entity:
    # Create an entity based on a string, useful for storing entities in files
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

    CAN_DIE = False
    MAX_HEALTH = 0

    # Initialise a base entity class from a position, rotation and size
    # Protected variables used so that it's easier to make subclasses
    def __init__(self, position, rotation, hitbox_radius):
        self._id = Entity._id_counter
        Entity._id_counter += 1
        self._position = position
        self._rotation = rotation
        self._hitbox_radius = hitbox_radius
        self._square_radius = hitbox_radius * hitbox_radius
        self._health = self.MAX_HEALTH

        if self.ANIMATION_PATH is None:
            self._animation = EmptyAnimation()
        else:
            self._animation = Animation(self.ANIMATION_PATH)

    # Get the entity's position
    def get_position(self):
        return self._position

    # Set the entity's position
    def set_position(self, position):
        self._position = position

    # Get the entity's rotation
    def get_rotation(self):
        return self._rotation

    # Set the entity's rotation
    def set_rotation(self, rotation):
        self._rotation = rotation

    # Change the entity's rotation by a certain amount
    def rotate(self, rotation):
        self._rotation += rotation

    # Rotate to look at a position
    def look_at(self, position):
        self._rotation = line_angle(self._position, position)

    # Pathfind to a location
    def move_towards_target(self, target, level):
        path = level.find_shortest_path(self._position, target, self._hitbox_radius)
        if path:
            next_target = path[1]
            self.look_at(next_target)
        else:
            self.look_at(target)
        self.move_within_level(-self.MOVEMENT_SPEED, level)

    # Move forwards, but stop if a wall is encountered
    def move_within_level(self, distance, level):
        force = vector_from_angle(self._rotation, distance)
        new_position = point_add(self._position, force)
        collided_lines = []

        # Check for any direct collisions with walls
        count = 0
        for a, b in level.iter_lines():
            if line_collision(a, b, new_position, self._square_radius):
                normal = level.get_normal(count)
                projected_force = vector_project(force, normal)
                force = vector_subtract(force, projected_force)
                collided_lines.append(count)
            count += 1

        # Check if the entity hit the very edge of a wall
        count = 0
        for a in level.get_bounds():
            if point_collision(a, new_position, self._square_radius):
                i_a, i_b = level.get_connected_lines(count)
                if i_a in collided_lines or i_b in collided_lines:
                    continue
                cur_dist = vector_from_points(a, new_position)
                escape_force = vector_normalise(cur_dist) * self._square_radius # Push away from the edge
                projected_force = vector_subtract(escape_force, cur_dist)
                force = vector_add(force, projected_force)
            count += 1

        # If hitting two walls, the entity cannot move at all
        if len(collided_lines) >= 2:
            force = (0, 0)

        # Update position
        self._position = point_add(self._position, force)

    # Move based on the current rotation
    def move(self, distance):
        delta_x = distance * math.cos(self._rotation + HALF_PI)
        delta_y = distance * math.sin(self._rotation + HALF_PI)
        self._position = (self._position[X] + delta_x, self._position[Y] + delta_y)

    # Check if touching the exit of a level
    def at_exit(self, level):
        return level.is_touching_exit(self._position, self._square_radius * 1.5)

    # Check if touching another entity based on hitbox sizes
    def is_touching(self, entity):
        distance = line_length(self._position, entity.get_position())
        return distance < self._hitbox_radius + entity.get_hitbox_radius()

    # Get the hitbox radius
    def get_hitbox_radius(self):
        return self._hitbox_radius

    # Set the hitbox radius
    def set_hitbox_radius(self, hitbox_radius):
        self._hitbox_radius = hitbox_radius
        self._square_radius = hitbox_radius * hitbox_radius

    # Get the entity id
    def get_id(self):
        return self._id

    # Get the entity's animation
    def get_animation(self):
        return self._animation

    def is_dead(self):
        return self.CAN_DIE and self._health <= 0

    def damage(self, damage):
        self._health -= damage

    def heal(self, health):
        self._health += health

    def restore_health(self):
        self._health = self.MAX_HEALTH

    def get_health_scalar(self):
        return self._health / self.MAX_HEALTH

    def get_health(self):
        return self._health

# A container for data about an entity, that is stored outside the physics thread
class DisplayEntity:
    SPRITE        = 0
    TEXTURE       = 1
    TAGGED_SPRITE = 2

    # Create a display entity with data from the original entity
    def __init__(self, position, rotation, size, samplers, entity_id, display_type, visible, display_name):
        # Store the past present and future so that the renderer can interpolate between them
        self.__prev_position = position
        self.__curr_position = position
        self.__next_position = position

        self.__prev_rotation = rotation
        self.__curr_rotation = rotation
        self.__next_rotation = rotation

        self.__size = size
        self.__samplers = samplers
        self.__sampler_index = 0
        self.__id = entity_id
        self.__display_type = display_type
        self.__visible = visible
        self.__display_name = display_name

    # Get the display entity's position
    def get_position(self, alpha):
        return lerp_p(self.__prev_position, self.__curr_position, alpha)

    # Set the display entity's position
    def set_position(self, position):
        self.__next_position = position

    # Get the display entity's rotation
    def get_rotation(self, alpha):
        return lerp_v(self.__prev_rotation, self.__curr_rotation, alpha)

    # Set the display entity's rotation
    def set_rotation(self, rotation):
        self.__next_rotation = rotation

    # Get the display entity's size
    def get_size(self):
        return self.__size

    # Get the current sampler of the display entity
    def get_sampler(self):
        return self.__samplers[self.__sampler_index]

    # Set the sampler index of the display entity
    def set_sampler_index(self, sampler_index):
        self.__sampler_index = sampler_index

    # Get the display entity's id
    def get_id(self):
        return self.__id

    # Get the display type: sprite, tagged_sprite or texture
    def get_display_type(self):
        return self.__display_type

    # Get the display name of this display entity
    def get_display_name(self):
        return self.__display_name

    # Get the visibility of the display entity
    def get_visible(self):
        return self.__visible

    # Set the visibility of this display entity
    def set_visible(self, visible):
        self.__visible = visible

    # Update the positions of this display entity
    def update(self):
        self.__prev_position = self.__curr_position
        self.__curr_position = self.__next_position

        self.__prev_rotation = self.__curr_rotation
        self.__curr_rotation = self.__next_rotation

# A subclass of entity that represents the player
class Player(Entity):
    ROTATION_SPEED = 0.025
    MOVEMENT_SPEED = 0.15

    REACH = 4.0

    DISPLAY_TYPE = DisplayEntity.SPRITE
    SAMPLERS = sampler_array("res/textures/player")
    ANIMATION_PATH = "res/animations/player.json"

    # Initialise the player from a position and rotation
    def __init__(self, position, rotation):
        super().__init__(position, rotation, 1)

    # Move an entity above the player's head
    def hold_entity(self, entity):
        vector = vector_from_angle(self._rotation + math.pi, self._hitbox_radius + entity.get_hitbox_radius())
        entity.set_position(point_add(self._position, vector))

class PlayerData:
    def __init__(self, time_remaining, gold_collected, health, held_item):
        self.__time_remaining = time_remaining
        self.__gold_collected = gold_collected
        self.__health = health
        self.__held_item = held_item

    def get_time_remaining(self):
        return self.__time_remaining

    def set_time_remaining(self, time_remaining):
        self.__time_remaining = time_remaining

    def get_gold_collected(self):
        return self.__gold_collected

    def set_gold_collected(self, gold_collected):
        self.__gold_collected = gold_collected

    def get_health(self):
        return self.__health

    def set_health(self, health):
        self.__health = health

    def get_held_item(self):
        return self.__held_item

    def set_held_item(self, held_item):
        self.__held_item = held_item

# A subclass of entity that represents a bear
class Bear(Entity):
    MOVEMENT_SPEED = 0.075

    DISPLAY_TYPE = DisplayEntity.TEXTURE
    SAMPLERS = sampler_array("res/textures/bear")
    ANIMATION_PATH = "res/animations/bear.json"

    # Initialise a bear from a position and rotation
    def __init__(self, position, rotation):
        super().__init__(position, rotation, 1)

# A subclass of entity that represents a honey jar
class HoneyJar(Entity):
    DISPLAY_TYPE = DisplayEntity.TAGGED_SPRITE

    SAMPLERS = [Sampler("res/textures/honeyjar.tex")]

    GRABBABLE = True

    # Initialise a honey jar from position and rotation
    def __init__(self, position, rotation):
        super().__init__(position, rotation, 0.5)

    # Used when drawing a tagged sprite
    def __str__(self):
        return "Honey Jar"

# A subclass of entity that represents a honey spill
class HoneySpill(Entity):
    DISPLAY_TYPE = DisplayEntity.TAGGED_SPRITE

    SAMPLERS = [Sampler("res/textures/honeyspill.tex")]

    # Initialise a honey spill
    def __init__(self, position, rotation):
        super().__init__(position, rotation, 0.5)

    # Used when drawing tagged sprites
    def __str__(self):
        return "Honey Spill"

# A class that represents a level
class Level:
    # Initialise a level from a json file
    def __init__(self, filepath, trust_path=False):
        if not trust_path:
            filepath = util.abspath(filepath)
        with open(filepath, "r") as file:
            raw_json = json.load(file)

        bounds = raw_json[BOUNDS]
        texture_bounds = []
        if TEXTURE_BOUNDS in raw_json.keys():
            texture_bounds = raw_json[TEXTURE_BOUNDS]
        textures = []
        if TEXTURES in raw_json.keys():
            textures = raw_json[TEXTURES]
        options = {}
        if OPTIONS in raw_json.keys():
            options = raw_json[OPTIONS]
        entities = []
        if ENTITIES in raw_json.keys():
            entities = raw_json[ENTITIES]

        # Create fields
        self.__bounds = []
        self.__pathfind_point_indices = []
        self.__pathfind_normals = []
        self.__pathfind_angles = []
        self.__connected_lines = []
        self.__normals = []
        used_samplers = {}
        self.__samplers = []
        self.__textures = []
        self.__texture_bounds = []
        self.__entities = []
        self.__outline  = "#"
        self.__spawnpoint = (0, 0)
        self.__exit_index = None

        try:
            for x, y in bounds:
                self.__bounds.append((x, y))
        except ValueError:
            raise SyntaxError("Coordinate must contain only two values")

        try:
            for x, y in texture_bounds:
                self.__texture_bounds.append((x, y))
        except ValueError:
            raise SyntaxError("Coordinate must contain only two values")

        self.__num_bounds = len(self.__bounds)

        # Create the line normals for collision detection
        for a, b in self.iter_lines():
            v = vector_from_points(b, a)
            v = vector_normalise(v)
            self.__normals.append(v)

        # Create the corner normals
        lines = list(self.iter_lines())
        for i in range(self.__num_bounds):
            line_a = lines[i - 1]
            line_b = lines[i]

            vec_a = vector_from_points(line_a[A], line_a[B])
            vec_b = vector_from_points(line_b[A], line_b[B])

            angle = vector_angle(vec_a, vec_b)
            if angle < 0: # Create normals only for points that jut out into the level
                self.__pathfind_point_indices.append(i)
                vec_a = vector_perpendicular(self.get_normal(i - 1))
                vec_b = vector_perpendicular(self.get_normal(i))

                line_ea = point_add(line_a[A], vec_a), point_add(line_a[B], vec_a)
                line_eb = point_add(line_b[A], vec_b), point_add(line_b[B], vec_b)

                # Ensure that point is far enough away from the level boundaries
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

    # Get the bounds of the level
    def get_bounds(self):
        return self.__bounds

    # Get the bounds of the displayed textures
    def get_texture_bounds(self):
        return self.__texture_bounds

    # Iterate over the level's lines
    def iter_lines(self):
        for i in range(self.__num_bounds):
            a = self.__bounds[i]
            if i == self.__num_bounds - 1:
                b = self.__bounds[0]
            else:
                b = self.__bounds[i + 1]
            yield a, b

    # Get a pathfinding waypoint by index
    def get_pathfind_point(self, pathfind_index, hitbox_radius):
        point_index = self.__pathfind_point_indices[pathfind_index]
        point = self.get_bound(point_index)
        normal = self.__pathfind_normals[pathfind_index]
        normal = vector_multiply(normal, hitbox_radius)
        point = point_add(point, normal)
        return point

    # Iterate over all pathfinding points
    def iter_pathfind_points(self, hitbox_radius):
        for i in range(self.__num_pathfinders):
            yield self.get_pathfind_point(i, hitbox_radius)

    # Find the shortest path between two points inside the level
    def find_shortest_path(self, start, end, hitbox_radius, visited_indices=None, path=None, depth=0):
        depth += 1

        if depth >= 5: # Stop searching is the path takes longer than 5 points - the algorithm is too slow otherwise
            return None

        if visited_indices is None:
            visited_indices = []

        if path is None:
            path = []

        points = self.find_closest_points(start, end, hitbox_radius, visited_indices)
        for index in points:
            if index in visited_indices:
                # Don't check points that have already been visited
                return None
            if index == -1:
                # If closest point is the end
                return [start, end]
            else:
                # Find the next point that is visible and closer to the destination
                point = self.get_pathfind_point(index, hitbox_radius)
                new_path = list(path)
                new_indices = list(visited_indices)
                new_indices.append(index)
                final_path = self.find_shortest_path(point, end, hitbox_radius, new_indices, new_path, depth)
                if final_path is not None and end in final_path:
                    # If the end has been found, return this path
                    final_path.insert(0, point)
                    return final_path

        # Return None if no path was found
        return None

    # Return a list of point indices, sorted by distance to the target
    def find_closest_points(self, start, end, hitbox_radius, visited_indices):
        order = []
        if not self.is_path_obstructed(start, end, hitbox_radius): # If there's a clear shot to the target
            return [-1]
        for i in range(self.__num_pathfinders):
            if i in visited_indices:
                continue
            target = self.get_pathfind_point(i, hitbox_radius)
            if not self.is_path_obstructed(start, target, hitbox_radius):
                # Get distance to all visible points
                distance = line_length(target, end)
                order.append((i, distance))

        order.sort(key=lambda x: x[1]) # Sort by distance
        return [p[0] for p in order]

    # Check if the direct path between two points is obstructed by a wall
    def is_path_obstructed(self, start, end, hitbox_radius):
        obstructed = False
        for line in self.iter_lines():
            if is_path_obstructed(start, end, line, hitbox_radius):
                obstructed = True
                break
        return obstructed

    # Get the two lines that are joined to a point in the level
    def get_connected_lines(self, bound_index):
        i_b = bound_index
        if bound_index == 0:
            i_a = self.__num_bounds - 1
        else:
            i_a = bound_index - 1
        return i_a, i_b

    # Check if a point is within a radius of the exit wall
    def is_touching_exit(self, point, hitbox_radius):
        line = list(self.iter_lines())[self.get_exit_index()]
        return line_collision(*line, point, hitbox_radius)

    # Iterate over entities in the level
    def iter_entities(self):
        for entity in self.__entities:
            yield entity

    # Get a level bound by index
    def get_bound(self, bound_index):
        return self.__bounds[bound_index]

    # Get a line normal by index
    def get_normal(self, normal_index):
        return self.__normals[normal_index]

    # Get the number of textures
    def get_num_textures(self):
        return len(self.__textures)

    # Get texture by index, a texture is a sampler plus four bound indices
    def get_texture(self, texture_index):
        return self.__textures[texture_index]

    # Get a sampler by index
    def get_sampler(self, sampler_index):
        return self.__samplers[sampler_index]

    # Get the outline fill character
    def get_outline(self):
        return self.__outline

    # Get the line index of the exit
    def get_exit_index(self):
        return self.__exit_index

    # Get the coordinates of the spawnpoint
    def get_spawnpoint(self):
        return self.__spawnpoint

# Get an array of level objects, based on all json files in a directory
def level_array(directory):
    directory = util.abspath(directory)
    levels = []
    for file in sorted(os.listdir(directory)):
        levels.append(Level(os.path.join(directory, file), trust_path=True))
    return levels

# A text box, storing a title, text, and a size
class TextBox:
    _id_counter = 0

    # Initialise a text box based on title, content, visibility and size
    def __init__(self, title, content, visible=True, max_width=0.5, max_height=0.5):
        self.__title = title
        self.__content = content
        self.__max_width = max_width
        self.__max_height = max_height
        self.__id = TextBox._id_counter
        self.__visible = visible
        TextBox._id_counter += 1

    # Get the text box's title
    def get_title(self):
        return self.__title

    # Get the text box's content
    def get_content(self):
        return self.__content

    # Get the max width of the text box
    def get_max_width(self):
        return self.__max_width

    # Get the max height of the text box
    def get_max_height(self):
        return self.__max_height

    # Get the id of the text box
    def get_id(self):
        return self.__id

    # Get the visibility of the text box
    def get_visible(self):
        return self.__visible

    # Set the visibility of the text box
    def set_visible(self, visible):
        self.__visible = visible

# A menu class, storing item names and item descriptions
class Menu:
    _id_counter = 0

    # Creates a menu based on a file containing titles and descriptions
    @classmethod
    def from_file(cls, filepath, visible=True):
        filepath = util.abspath(filepath)
        with open(filepath, "r") as file:
            raw_json = json.load(file)

        # Check if a default description was specified
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

    # Create a menu based on a title, a default description and a visibility
    def __init__(self, title, default_description="", visible=True):
        self.__title = title
        self.__active_index = 0
        self.__id = Menu._id_counter
        Menu._id_counter += 1
        self.__default_description = default_description
        self.__items = []
        self.__visible = visible
        self.__formatting = {}

    # Get the menu's title
    def get_title(self):
        return self.__title

    # Add an item, which is a name and a description
    def add_item(self, item_name, item_description=None):
        self.__items.append((item_name, item_description))

    # Remove an item by index
    def remove_item(self, item_index):
        self.__items.pop(item_index)

    # Get an item's name by index
    def get_item_name(self, index):
        return self.__items[index][0]

    # Get an item's description by index
    def get_item_description(self, index):
        description = self.__items[index][1]
        if description is None:
            return self.__default_description
        else:
            if index in self.__formatting.keys():
                return description.format(*self.__formatting[index])
            else:
                return description

    # Get the number of items in a menu
    def get_num_items(self):
        return len(self.__items)

    # Get the index of an item by its name
    def get_item_index_by_name(self, item_name):
        for i in range(len(self.__items)):
            item = self.__items[i]
            if item_name == item[0]:
                return i

    # Get the id of the menu
    def get_id(self):
        return self.__id

    # Get the visibility of the menu
    def get_visible(self):
        return self.__visible

    # Set the visibility of the menu
    def set_visible(self, visible):
        self.__visible = visible

    # Get the active index of the menu
    def get_active_index(self):
        return self.__active_index

    # Set the active index of the menu
    def set_active_index(self, index):
        self.__active_index = index

    # Set the formatting of the menu, will replace any '{}' in the menu with the formatting
    def set_formatting(self, index, formatting):
        self.__formatting[index] = formatting

# A menu interface class, stores only the necessary data to operate the menu from the physics thread
class MenuInterface:
    # Create a menu interface based on menu data
    def __init__(self, num_items, active_index, menu_id):
        self.__num_items = num_items
        self.__active_index = active_index
        self.__id = menu_id

    # Get the number of items
    def get_num_items(self):
        return self.__num_items

    # Set the number of items
    def set_num_items(self, num_items):
        self.__num_items = num_items

    # Get the active index
    def get_active_index(self):
        return self.__active_index

    # Set the active index
    def set_active_index(self, index):
        self.__active_index = index

    # Get the menu id
    def get_id(self):
        return self.__id

# A class that stores data about progress bars
class ProgressBar:
    _id_counter = 0

    # Create a progress bar
    def __init__(self, position, width, visible=True):
        self.__position = position
        self.__width = width
        self.__id = ProgressBar._id_counter
        ProgressBar._id_counter += 1
        self.__progress = 0
        self.__visible = visible

    # Get the progress
    def get_progress(self):
        return self.__progress

    # Set the progress
    def set_progress(self, progress):
        self.__progress = progress

    # Get the position
    def get_position(self):
        return self.__position

    # Set the position
    def set_position(self, position):
        self.__position = position

    # Get the width
    def get_width(self):
        return self.__width

    # Get the id
    def get_id(self):
        return self.__id

    # Get the visibility
    def get_visible(self):
        return self.__visible

    # Set the visibility
    def set_visible(self, visible):
        self.__visible = visible

# A class that handles saving games
class Save:
    _id_counter = 0

    PLAYING = "playing"
    LOST = "lost"
    WON = "won"

    # Load a save from a json file
    @classmethod
    def from_file(cls, filepath, trust_path=False):
        if not trust_path:
            filepath = util.abspath(filepath)
        with open(filepath, "r") as file:
            raw_json = json.load(file)

        # Collect data from json file
        save_id = raw_json[SAVE_ID]
        save_name = raw_json[SAVE_NAME]
        level_index = raw_json[LEVEL_INDEX]
        collected_gold = raw_json[COLLECTED_GOLD]
        condition = raw_json[CONDITION]
        return cls(save_name, level_index, collected_gold, condition, save_id)

    # Create a new save
    def __init__(self, save_name, level_index, collected_gold, condition=PLAYING, save_id=None):
        if save_id is None:
            self.__id = Save._id_counter
            Save._id_counter += 1
        else:
            self.__id = save_id
            if save_id >= Save._id_counter:
                Save._id_counter = save_id + 1
        self.__save_name = save_name
        self.__level_index = level_index
        self.__collected_gold = collected_gold
        self.__condition = condition

    # Get the id of the save
    def get_id(self):
        return self.__id

    # Get the name of the save
    def get_save_name(self):
        return self.__save_name

    # Get the level number that is saved
    def get_level_index(self):
        return self.__level_index

    # Set the level to save as
    def set_level_index(self, level_index):
        self.__level_index = level_index

    # Get the gold collected in the save
    def get_collected_gold(self):
        return self.__collected_gold

    # Set the gold collected in the save
    def set_collected_gold(self, collected_gold):
        self.__collected_gold = collected_gold

    # Get the condition the save is in: won, lost, still playing
    def get_condition(self):
        return self.__condition

    # Set the condition of the save: won, lost, still playing
    def set_condition(self, condition):
        self.__condition = condition

    # Save the save in a directory
    def save(self, directory, trust_path=False):
        if not trust_path:
            directory = util.abspath(directory)

        # Create the save folder if it doesn't exist
        if not os.path.exists(directory):
            os.makedirs(directory)

        raw_json = {
            SAVE_ID: self.__id,
            SAVE_NAME: self.__save_name,
            LEVEL_INDEX: self.__level_index,
            COLLECTED_GOLD: self.__collected_gold,
            CONDITION: self.__condition
        }

        filepath = os.path.join(directory, f"save_{self.__id}.json")

        with open(filepath, "w", encoding="utf-8") as file:
            json.dump(raw_json, file, ensure_ascii=False)

    # Delete a save file
    def delete(self, directory, trust_path=False):
        if not trust_path:
            directory = util.abspath(directory)

        filepath = os.path.join(directory, f"save_{self.__id}.json")

        if os.path.exists(filepath):
            os.remove(filepath)

# Create an array of saves based on json files in a directory
def saves_array(directory):
    directory = util.abspath(directory)

    # Create the save folder if it doesn't exist
    if not os.path.exists(directory):
        os.makedirs(directory)

    saves = []
    for file in sorted(os.listdir(directory)):
        saves.append(Save.from_file(os.path.join(directory, file), trust_path=True))
    return saves
