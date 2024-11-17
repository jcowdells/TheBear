import math
import time
import textwrap
from multiprocessing import Process, Pipe

import util
from src.geometry import Z, mat4_multiply, mat4_projection, W, \
    mat4_translation, mat4_rotation_z, point_to_screen, INVISIBLE, CLIP, line_clip, \
    point_perspective_divide, p_scale_point, line_clip_to_screen, lerp_v, point_transform_3d, vector_from_angle, \
    vector_dot, vector_perpendicular, vector_normalise, vector_from_points, vector_angle, vector_multiply
from util import Message
from render import ConsoleGUI, ALIGN_LEFT, ALIGN_CENTER, ALIGN_TOP, ALIGN_RIGHT, Sampler, sampler_array
from geometry import X, Y, point_rotate, point_transform, point_add, HALF_PI, point_subtract, line_gradient, line_solve_y
from game import DisplayEntity, PlayerData, ProgressBar
from physics import send_message, recv_message, physics_thread, get_by_id, GameState

import cProfile

MAINMENU_ICON_RATIO = 4.72
MAINMENU_TEXT_DEPTH = 0.333
MAINMENU_MAX_DEPTH  = 0.922

CROSSHAIR_SIZE = 0.02

GUI_MIN = 0.06
GUI_MAX = 0.12
GUI_RAISED_WIDTH = 0.33
GUI_HEALTH_WIDTH = 0.25

# The main class, contains game renderer and window functions etc
class Main(ConsoleGUI):
    # Initialise the main window
    def __init__(self):
        super().__init__(480, 360, 100, 100)

        self.__prev_time = time.perf_counter()
        self.__cur_time  = time.perf_counter()

        self.__prev_delta_time = time.perf_counter()
        self.__delta = 1

        # Allows for communication between the main class and the physics thread
        input_pipe, self.__output_pipe = Pipe(duplex=False)
        self.__input_pipe, output_pipe = Pipe(duplex=False)
        self.__physics = Process(target=physics_thread, args=(input_pipe, output_pipe))

        self.__main_menu_sampler = Sampler("res/textures/mainmenu.tex")
        self.__main_menu_icons = sampler_array("res/textures/mainmenu_icons")
        self.__main_menu_num_icons = len(self.__main_menu_icons)

        self.__easter_egg_sampler = Sampler("res/textures/me.tex")

        self.__game_state = GameState.MAIN_MENU
        self.__settings = {
            "MAIN_MENU_SELECTOR": 0,
            "DISPLAY_INFO": False,
            "TIME_REMAINING": 0,
            "COLLECTED_GOLD": 0,
            "DISPLAY_FPS": False,
            "TEXT_COLOUR": "22BB00",
            "BACKGROUND_COLOUR": "000000",
            "FONT_SIZE": 10,
            "EASTER_EGG": False,
            "FOV": math.pi / 2,
            "NEAR_CLIP": 0.01,
            "FAR_CLIP": 50,
            "WALL_TOP": 2,
            "WALL_BOTTOM": -2,
            "CAMERA_HEIGHT": 0
        }
        self.__level = None
        self.__player_data = PlayerData(0, 0, 0, "")
        self.__health_bar = ProgressBar((0, 0), GUI_HEALTH_WIDTH)
        self.__entity_list = []
        self.__menu_list = []
        self.__text_box_list = []
        self.__progress_bar_list = []
        self.__focus_id = 0

    # Update settings and make any necessary changes to the window
    def update_settings(self, key, value):
        if key == "TEXT_COLOUR":
            self.set_text_colour(value)
        if key == "BACKGROUND_COLOUR":
            self.set_background_colour(value)
        if key == "FONT_SIZE":
            self.set_font_size(value)
        self.__settings[key] = value

    # On begin callback, when window loads
    def on_begin(self):
        self.__physics.start()

    # On end callback, when X is pressed
    def on_end(self):
        send_message(self.__output_pipe, Message.EXIT, 0)
        self.__physics.join()

    # The main loop, is called every frame
    def main(self):
        self.__cur_time = time.perf_counter()
        fps = 1 / (self.__cur_time - self.__prev_time)
        self.__prev_time = self.__cur_time

        # See if physics thread has given any updates
        while self.__input_pipe.poll():
            try:
                message, data = recv_message(self.__input_pipe)
                if message == Message.EXIT:
                    self.end()
                elif message == Message.LEVEL_CHANGED:
                    self.__level = data
                elif message == Message.ENTITY_CREATED:
                    self.__entity_list.append(data)
                elif message == Message.ENTITY_UPDATE:
                    entity_id, position, rotation = data
                    entity = get_by_id(entity_id, self.__entity_list)
                    entity.set_position(position)
                    entity.set_rotation(rotation)
                elif message == Message.ENTITY_ANIMATE:
                    entity_id, sampler_index = data
                    entity = get_by_id(entity_id, self.__entity_list)
                    entity.set_sampler_index(sampler_index)
                elif message == Message.ENTITY_VISIBLE:
                    entity_id, visible = data
                    entity = get_by_id(entity_id, self.__entity_list)
                    entity.set_visible(visible)
                elif message == Message.ENTITY_KILL:
                    for entity in self.__entity_list:
                        if entity.get_id() == data:
                            self.__entity_list.remove(entity)
                            break
                elif message == Message.FOCUS_ID:
                    self.__focus_id = data
                elif message == Message.DELTA:
                    self.__prev_delta_time = time.perf_counter()
                    self.__delta = data
                    for entity in self.__entity_list:
                        entity.update()
                elif message == Message.MENU_CREATED:
                    self.__menu_list.append(data)
                elif message == Message.MENU_ADD_ITEM:
                    menu_id, item = data
                    menu = get_by_id(menu_id, self.__menu_list)
                    menu.add_item(*item)
                elif message == Message.MENU_REMOVE_ITEM:
                    menu_id, index = data
                    menu = get_by_id(menu_id, self.__menu_list)
                    menu.remove_item(index)
                elif message == Message.MENU_CHANGE_INDEX:
                    menu_id, index = data
                    menu = get_by_id(menu_id, self.__menu_list)
                    menu.set_active_index(index)
                elif message == Message.MENU_VISIBLE:
                    menu_id, visible = data
                    menu = get_by_id(menu_id, self.__menu_list)
                    menu.set_visible(visible)
                elif message == Message.MENU_SET_FORMATTING:
                    menu_id, format_index, formatting = data
                    menu = get_by_id(menu_id, self.__menu_list)
                    menu.set_formatting(format_index, formatting)
                elif message == Message.TEXT_BOX_CREATED:
                    self.__text_box_list.append(data)
                elif message == Message.TEXT_BOX_VISIBLE:
                    text_box_id, visible = data
                    text_box = get_by_id(text_box_id, self.__text_box_list)
                    text_box.set_visible(visible)
                elif message == Message.TEXT_BOX_DELETED:
                    for text_box in self.__text_box_list:
                        if text_box.get_id() == data:
                            self.__text_box_list.remove(text_box)
                elif message == Message.GAME_STATE_CHANGED:
                    self.__game_state = data
                elif message == Message.UPDATE_SETTING:
                    key, value = data
                    self.update_settings(key, value)
                elif message == Message.PROGRESS_BAR_CREATED:
                    self.__progress_bar_list.append(data)
                elif message == Message.PROGRESS_BAR_UPDATE:
                    progress_bar_id, position, progress = data
                    progress_bar = get_by_id(progress_bar_id, self.__progress_bar_list)
                    progress_bar.set_position(position)
                    progress_bar.set_progress(progress)
                elif message == Message.PROGRESS_BAR_VISIBLE:
                    progress_bar_id, visible = data
                    progress_bar = get_by_id(progress_bar_id, self.__progress_bar_list)
                    progress_bar.set_visible(visible)
                elif message == Message.UPDATE_PLAYER_DATA:
                    time_remaining, gold_collected, health, held_item = data
                    self.__player_data.set_time_remaining(time_remaining)
                    self.__player_data.set_gold_collected(gold_collected)
                    self.__player_data.set_health(health)
                    self.__player_data.set_held_item(held_item)
            except EOFError:
                # Only happens when X is pressed, and physics thread closes before main
                return

        # Delta time, allows to interpolate between physics states if screen FPS is higher than physics refresh rate
        curr_delta = self.__cur_time - self.__prev_delta_time
        alpha = curr_delta / self.__delta
        alpha = max(0, min(1, alpha))

        # The camera will be focused on the focus entity
        focus_entity = get_by_id(self.__focus_id, self.__entity_list)
        if focus_entity is not None:
            focus_centre = focus_entity.get_position(alpha)
            focus_rotation = focus_entity.get_rotation(alpha)
        else:
            focus_centre = (0, 0)
            focus_rotation = 0
        if self.__game_state == GameState.MAIN_MENU:
            self.draw_main_menu()
        elif self.__game_state == GameState.GAME:
            fov          = self.__settings["FOV"]
            near_clip    = self.__settings["NEAR_CLIP"]
            far_clip     = self.__settings["FAR_CLIP"]
            aspect_ratio = self.get_width_chars() / self.get_height_chars()

            z_buffer = [far_clip for _ in range(self.get_width_chars() + 1)]

            translation_matrix = mat4_translation(-focus_centre[X], 0, -focus_centre[Y])
            rotation_matrix    = mat4_rotation_z(focus_rotation)
            projection_matrix  = mat4_projection(fov, aspect_ratio, near_clip, far_clip)

            if self.__level is not None:
                #self.draw_level(self.__level, focus_centre, focus_rotation)
                self.draw_3d_level(self.__level, translation_matrix, rotation_matrix, projection_matrix, z_buffer)

            for entity in self.__entity_list:
                if entity.get_id() != self.__focus_id and entity.get_visible():
                    self.draw_3d_entity(entity, focus_centre, alpha,
                                        translation_matrix, rotation_matrix, projection_matrix, z_buffer)

            self.draw_crosshair()
            self.draw_game_gui()

        for progress_bar in self.__progress_bar_list:
            if progress_bar.get_visible():
                self.draw_progress_bar(progress_bar, focus_centre, focus_rotation)

        for menu in self.__menu_list:
            if menu.get_visible():
                self.draw_menu(menu)

        for text_box in self.__text_box_list:
            if text_box.get_visible():
                self.draw_text_box(text_box)

        # Some optional stats to display in the top right
        y = 0
        width_chars = self.get_width_chars() - 1
        if self.__settings["DISPLAY_FPS"]:
            self.draw_text((width_chars, y), f"FPS: {round(fps)}",
                           align_x=ALIGN_RIGHT, align_y=ALIGN_TOP, justify=ALIGN_RIGHT)

        self.swap_buffers()

    # Draw an entity to the screen
    def draw_entity(self, entity, centre, rotation, alpha):
        display_type = entity.get_display_type()
        if display_type == DisplayEntity.SPRITE or display_type == DisplayEntity.TAGGED_SPRITE:
            entity_centre = entity.get_position(alpha)
            entity_size   = entity.get_size()
            entity_tlr = point_rotate((entity_size, entity_size), rotation + math.pi)
            entity_brr = point_rotate((entity_size, entity_size), rotation)
            entity_tl = self.transform_point(point_add(entity_centre, entity_tlr), centre, rotation)
            entity_br = self.transform_point(point_add(entity_centre, entity_brr), centre, rotation)
            entity_sampler = entity.get_sampler()
            self.draw_sprite(entity_tl, entity_br, entity_sampler)
            if display_type == DisplayEntity.TAGGED_SPRITE:
                entity_c = (entity_tl[X] + entity_br[X]) // 2, (entity_tl[Y] + entity_br[Y]) // 2
                self.draw_text(entity_c, entity.get_display_name(),
                               align_x=ALIGN_CENTER, align_y=ALIGN_CENTER, justify=ALIGN_CENTER)
        elif display_type == DisplayEntity.TEXTURE:
            entity_centre = entity.get_position(alpha)
            entity_rotation = entity.get_rotation(alpha)
            entity_size = entity.get_size()

            # Grab the four corners of the image
            entity_ar = point_rotate((entity_size, entity_size), entity_rotation + math.pi)
            entity_br = point_rotate((entity_size, entity_size), entity_rotation - HALF_PI)
            entity_cr = point_rotate((entity_size, entity_size), entity_rotation)
            entity_dr = point_rotate((entity_size, entity_size), entity_rotation + HALF_PI)

            entity_a = self.transform_point(point_add(entity_centre, entity_ar), centre, rotation)
            entity_b = self.transform_point(point_add(entity_centre, entity_br), centre, rotation)
            entity_c = self.transform_point(point_add(entity_centre, entity_cr), centre, rotation)
            entity_d = self.transform_point(point_add(entity_centre, entity_dr), centre, rotation)

            # the uv coordinates are for the image so:
            #  (0, 0) ----- (1, 0)
            #     |     \      |
            #     |      \     |
            #  (0, 1) ----- (1, 1)
            # A rectangle made of two clockwise triangles
            entity_sampler = entity.get_sampler()
            self.draw_sampler(entity_a, entity_b, entity_c, (0, 0), (1, 0), (1, 1), entity_sampler)
            self.draw_sampler(entity_a, entity_c, entity_d, (0, 0), (1, 1), (0, 1), entity_sampler)

    # Draw a level to the screen
    def draw_level(self, level, centre, rotation):
        centred_bounds = []
        for point in level.get_bounds():
            point = self.transform_point(point, centre, rotation)
            centred_bounds.append(point)

        centred_texture_bounds = []
        # For each point in the level, transform it to screen space
        for point in level.get_texture_bounds():
            point = self.transform_point(point, centre, rotation)
            centred_texture_bounds.append(point)

        outline = level.get_outline()
        len_bounds = len(centred_bounds)

        for i in range(level.get_num_textures()):
            sampler_index, c1, c2, c3, c4 = level.get_texture(i)
            if self.__settings["EASTER_EGG"]:
                # The Easter egg xD
                sampler = self.__easter_egg_sampler
            else:
                sampler = level.get_sampler(sampler_index)
            a = centred_texture_bounds[c1]
            b = centred_texture_bounds[c2]
            c = centred_texture_bounds[c3]
            d = centred_texture_bounds[c4]
            #self.draw_sampler(a, b, c, (0, 0), (1, 0), (1, 1), sampler)
            #self.draw_sampler(a, c, d, (0, 0), (1, 1), (0, 1), sampler)

        exit_index = level.get_exit_index()
        # Loop through each line
        for i in range(len_bounds):
            bound_a = centred_bounds[i]
            if i == len_bounds - 1:
                bound_b = centred_bounds[0]
            else:
                bound_b = centred_bounds[i + 1]

            if i == exit_index:
                # If is the exit line, don't draw it so it looks like you can go through
                exit_centre = point_add(bound_a, bound_b)
                exit_centre = exit_centre[X] // 2, exit_centre[Y] // 2
                self.draw_text(exit_centre, "EXIT", align_x=ALIGN_CENTER, align_y=ALIGN_CENTER, justify=ALIGN_CENTER)
            else:
                outline="#"
                self.draw_line(bound_a, bound_b, fill=outline)

    def draw_3d_level(self, level, translation_matrix, rotation_matrix, projection_matrix, z_buffer):
        far_clip = self.__settings["FAR_CLIP"]
        wall_top = self.__settings["WALL_TOP"]
        wall_bottom = self.__settings["WALL_BOTTOM"]

        screen_width = self.get_width_chars()
        screen_height = self.get_height_chars()

        vertex_buffer = []
        index_group_buffer = []
        line_buffer = []
        normal_buffer = []
        y_buffer = [(0, -1) for _ in range(screen_width + 1)]

        matrices = (translation_matrix, rotation_matrix, projection_matrix)

        camera_vector = vector_normalise((1, 3))

        i = 0
        for point in level.get_bounds():
            for height in [wall_bottom, 0, wall_top]:
                vertex_buffer.append(point_transform_3d((point[X], height, point[Y]), *matrices))
            j = 3 * i
            index_group_buffer.append((j, j + 1, j + 2, i))
            i += 1

        len_indices = len(index_group_buffer)
        for i in range(len_indices):
            index_g_a = index_group_buffer[i - 1]
            index_g_b = index_group_buffer[i]
            point_ab = vertex_buffer[index_g_a[0]]
            point_am = vertex_buffer[index_g_a[1]]
            point_at = vertex_buffer[index_g_a[2]]
            point_bb = vertex_buffer[index_g_b[0]]
            point_bm = vertex_buffer[index_g_b[1]]
            point_bt = vertex_buffer[index_g_b[2]]

            mid_line = line_clip(point_am, point_bm)
            if mid_line is None: continue
            top_line = line_clip(point_at, point_bt)
            bottom_line = line_clip(point_ab, point_bb)

            mid_line_s = line_clip_to_screen(*mid_line, screen_width, screen_height)
            mid_line_a = (mid_line_s[0][X], point_am[Z])
            mid_line_b = (mid_line_s[1][X], point_bm[Z])
            mid_line_g = line_gradient(mid_line_a, mid_line_b)

            if top_line is None:
                top_line_g = None
            else:
                top_line_s = line_clip_to_screen(*top_line, screen_width, screen_height)
                top_line_g = line_gradient(*top_line_s)

            if bottom_line is None:
                bottom_line_g = None
            else:
                bottom_line_s = line_clip_to_screen(*bottom_line, screen_width, screen_height)
                bottom_line_g = line_gradient(*bottom_line_s)

            min_x = min(mid_line_s[0][X], mid_line_s[1][X])
            max_x = max(mid_line_s[0][X], mid_line_s[1][X])

            for x in range(min_x, max_x + 1):
                if top_line_g is None:
                    y1 = screen_height + 1
                else:
                    y1 = line_solve_y(x, *top_line_g)
                if bottom_line_g is None:
                    y2 = 0
                else:
                    y2 = line_solve_y(x, *bottom_line_g)
                delta_y = math.fabs(y1 - y2)

                z = line_solve_y(x, *mid_line_g)

                if delta_y > y_buffer[x][0]:
                    y_buffer[x] = (delta_y, len(line_buffer))
                    z_buffer[x] = z

            line_buffer.append((top_line_g, bottom_line_g))
            normal = self.__level.get_normal(i - 1)
            normal = vector_perpendicular(normal)
            normal_buffer.append(normal)

        for x in range(self.get_width_chars()):
            line_index = y_buffer[x][1]
            if line_index == -1:
                continue
            top_line, bottom_line = line_buffer[line_index]
            normal = normal_buffer[line_index]

            diffuse = max(math.fabs(vector_dot(normal, camera_vector)), 0)

            if top_line is None or top_line[1] == 0:
                top_y = screen_height + 1
            else:
                top_y = round(line_solve_y(x, *top_line))
            if bottom_line is None or bottom_line[1] == 0:
                bottom_y = 0
            else:
                bottom_y = round(line_solve_y(x, *bottom_line))
            index = max(1, round(5 * diffuse))
            if index < 10:
                fill = " .-:=+*%#@"[index]
            else:
                fill = " "
            self.draw_column(x, bottom_y, top_y, fill=fill)

    def draw_3d_entity(self, entity, centre, alpha, translation_matrix, rotation_matrix, projection_matrix, z_buffer):
        entity_centre  = entity.get_position(alpha)
        entity_size    = entity.get_size()
        if self.__settings["EASTER_EGG"]:
            entity_sampler = self.__easter_egg_sampler
        else:
            entity_sampler = entity.get_sampler()

        rotation_vector = vector_from_points(entity_centre, centre)
        rotation_vector = vector_normalise(rotation_vector)
        rotation_vector = vector_perpendicular(rotation_vector)

        entity_l = vector_multiply(rotation_vector, entity_size)
        entity_l = point_add(entity_centre, entity_l)

        entity_r = vector_multiply(rotation_vector, -entity_size)
        entity_r = point_add(entity_centre, entity_r)

        entity_tl = (entity_l[X], entity_size, entity_l[Y])
        entity_tl = point_transform_3d(entity_tl, translation_matrix, rotation_matrix, projection_matrix)

        entity_tr = (entity_r[X], entity_size, entity_r[Y])
        entity_tr = point_transform_3d(entity_tr, translation_matrix, rotation_matrix, projection_matrix)

        entity_ml = (entity_l[X], 0, entity_l[Y])
        entity_ml = point_transform_3d(entity_ml, translation_matrix, rotation_matrix, projection_matrix)

        entity_mr = (entity_r[X], 0, entity_r[Y])
        entity_mr = point_transform_3d(entity_mr, translation_matrix, rotation_matrix, projection_matrix)

        entity_bl = (entity_l[X], -entity_size, entity_l[Y])
        entity_bl = point_transform_3d(entity_bl, translation_matrix, rotation_matrix, projection_matrix)

        entity_br = (entity_r[X], -entity_size, entity_r[Y])
        entity_br = point_transform_3d(entity_br, translation_matrix, rotation_matrix, projection_matrix)

        mid_line = line_clip(entity_ml, entity_mr)
        if mid_line is None: return

        top_line = line_clip(entity_tl, entity_tr)
        bottom_line = line_clip(entity_bl, entity_br)

        screen_width = self.get_width_chars()
        screen_height = self.get_height_chars()

        mid_line = line_clip_to_screen(*mid_line, screen_width, screen_height)

        if top_line is None:
            top_line_g = None
        else:
            top_line = line_clip_to_screen(*top_line, screen_width, screen_height)
            top_line_g = line_gradient(*top_line)

        if bottom_line is None:
            bottom_line_g = None
        else:
            bottom_line = line_clip_to_screen(*bottom_line, screen_width, screen_height)
            bottom_line_g = line_gradient(*bottom_line)

        min_x = round(min(mid_line[0][X], mid_line[1][X]))
        max_x = round(max(mid_line[0][X], mid_line[1][X]))

        mid_line_g = line_gradient((mid_line[0][X], entity_ml[Z]), (mid_line[1][X], entity_mr[Z]))

        for x in range(min_x, max_x + 1):
            z = line_solve_y(x, *mid_line_g)

            if z_buffer[x] < z:
                continue

            if top_line_g is None:
                top_y = screen_height + 1
            else:
                top_y = round(line_solve_y(x, *top_line_g))

            if bottom_line_g is None:
                bottom_y = 0
            else:
                bottom_y = round(line_solve_y(x, *bottom_line_g))

            self.draw_sampler_column(x, min_x, max_x, bottom_y, top_y, entity_sampler)

    def draw_crosshair(self):
        screen_width = self.get_width_chars()
        screen_height = self.get_height_chars()

        aspect_ratio = self.get_width() / self.get_height()

        crosshair_size_x = round(screen_width * CROSSHAIR_SIZE / aspect_ratio)
        crosshair_size_y = round(screen_height * CROSSHAIR_SIZE)

        mid_x = screen_width // 2
        mid_y = screen_height // 2
        for x in range(mid_x - crosshair_size_x, mid_x + crosshair_size_x + 1):
            self.draw_character((x, mid_y), fill="-")
        for y in range(mid_y - crosshair_size_y, mid_y + crosshair_size_y + 1):
            self.draw_character((mid_x, y), fill="|")
        self.draw_character((mid_x, mid_y), fill="+")

    def draw_3d_line(self, a, b, fill="#"):
        line = line_clip(a, b)
        if line is not None:
            a, b = line_clip_to_screen(*line, self.get_width_chars(), self.get_height_chars())
            self.draw_line(a, b, fill=fill)

    def draw_game_gui(self):
        screen_width = self.get_width_chars()
        screen_height = self.get_height_chars()

        gui_min_y = round(screen_height * (1 - GUI_MIN))
        gui_max_y = round(screen_height * (1 - GUI_MAX))

        x_diff = screen_width * ((1 - GUI_RAISED_WIDTH) / 2)
        gui_min_x = round(x_diff)
        gui_max_x = round(screen_width - x_diff)

        self.draw_rectangle((0, gui_min_y), (screen_width, screen_height), fill=" ")
        self.draw_line((0, gui_min_y), (screen_width, gui_min_y), fill="_")
        self.draw_rectangle((gui_min_x, gui_max_y), (gui_max_x, gui_min_y), fill=" ")
        self.draw_line((gui_min_x, gui_max_y), (gui_max_x, gui_max_y), fill="_")

        delta_y = gui_min_y - gui_max_y
        for i in range(delta_y):
            self.draw_column(gui_min_x - i, gui_max_y + i + 1, gui_min_y, fill=" ")
            self.draw_column(gui_max_x + i, gui_max_y + i + 1, gui_min_y, fill=" ")
            self.draw_character((gui_min_x - i, gui_max_y + i + 1), fill="/")
            self.draw_character((gui_max_x + i, gui_max_y + i + 1), fill="\\")

        self.__health_bar.set_position((screen_width // 2 - 1, (gui_min_y + gui_max_y) // 2 + 1))
        self.__health_bar.set_progress(self.__player_data.get_health())
        self.__health_bar.set_visible(True)
        self.draw_progress_bar_raw(self.__health_bar)

        text_height = (gui_min_y + screen_height) // 2

        game_info = f"TIME LEFT: {self.__player_data.get_time_remaining()} | GOLD: {self.__player_data.get_gold_collected()}"
        self.draw_text((1, text_height), game_info,
                       align_x=ALIGN_LEFT, align_y=ALIGN_TOP, justify=ALIGN_LEFT)

        player_info = f"HOLDING: {self.__player_data.get_held_item()}"
        self.draw_text((screen_width - 1, text_height), player_info,
                       align_x=ALIGN_RIGHT, align_y=ALIGN_TOP, justify=ALIGN_RIGHT)

    # Draw a box to the screen
    def draw_box(self, menu_tl, menu_br):
        menu_tr = menu_br[X], menu_tl[Y]
        menu_bl = menu_tl[X], menu_br[Y]

        # Background
        self.draw_rectangle(menu_tl, menu_br, fill=" ")

        # Edges
        self.draw_line(menu_tl, menu_tr, fill="-")
        self.draw_line(menu_bl, menu_br, fill="-")
        self.draw_line(menu_tl, menu_bl, fill="|")
        self.draw_line(menu_tr, menu_br, fill="|")

        # Corners
        self.draw_character(menu_tl, fill="+")
        self.draw_character(menu_tr, fill="+")
        self.draw_character(menu_br, fill="+")
        self.draw_character(menu_bl, fill="+")

    # Draw a box with a title
    def draw_title_box(self, menu_tl, menu_br, title):
        menu_tr = menu_br[X], menu_tl[Y]
        self.draw_box(menu_tl, menu_br)
        self.draw_line((menu_tl[X], menu_tl[Y] + 2), (menu_tr[X], menu_tr[Y] + 2), fill="-")
        self.draw_character((menu_tl[X], menu_tl[Y] + 2), fill="+")
        self.draw_character((menu_tr[X], menu_tr[Y] + 2), fill="+")

        title_pos = (menu_tl[X] + menu_br[X]) // 2, menu_tl[Y] + 1
        self.draw_text(title_pos, title, align_x=ALIGN_CENTER, align_y=ALIGN_TOP, justify=ALIGN_CENTER)

    # Draw a box with a title and some content
    def draw_text_box(self, text_box):
        content = text_box.get_content()
        width = self.get_width_chars()
        height = self.get_height_chars()
        box_width = text_box.get_max_width()
        box_height = text_box.get_max_height()
        max_width = round(width * box_width)
        max_height = round(height * box_height)

        # Wrap the text to the maximum width
        if max_width > 4 and max_height > 6:
            display = "\n".join(textwrap.wrap(content, max_width - 4)[:max_height - 6])
        else:
            display = ""
        text_width, text_height = util.find_string_size(display)

        # Find the maximum size that the box needs to be or can be
        if text_width > max_width - 4:
            box_width = max_width
        else:
            box_width = text_width + 3

        if text_height > max_height - 6:
            box_height = max_height
        else:
            box_height = text_height + 5

        # Draw the text box
        if max_width > 0:
            half_box_width = box_width / width * 0.5
            half_box_height = box_height / height * 0.5
            box_tl = round(width * (0.5 - half_box_width)), round(height * (0.5 - half_box_height))
            box_br = round(box_tl[X] + box_width), round(box_tl[Y] + box_height)
            self.draw_title_box(box_tl, box_br, text_box.get_title())
            text_tl = box_tl[X] + 2, box_tl[Y] + 4
            self.draw_text(text_tl, display, align_x=ALIGN_LEFT, align_y=ALIGN_TOP, justify=ALIGN_LEFT)

    def __progress_bar_text(self, progress_bar):
        width = round(self.get_width_chars() * progress_bar.get_width())
        num_chars = width - 2
        num_chars_filled = round(num_chars * progress_bar.get_progress())
        num_chars_blank = num_chars - num_chars_filled
        return "[" + "#" * num_chars_filled + " " * num_chars_blank + "]"

    # Draw a progress bar
    def draw_progress_bar(self, progress_bar, centre, rotation):
        display = self.__progress_bar_text(progress_bar)
        position = self.transform_point(progress_bar.get_position(), centre, rotation)
        self.draw_text(position, display, align_x=ALIGN_CENTER, align_y=ALIGN_CENTER, justify=ALIGN_CENTER)

    def draw_progress_bar_raw(self, progress_bar):
        display = self.__progress_bar_text(progress_bar)
        self.draw_text(progress_bar.get_position(), display, align_x=ALIGN_CENTER, align_y=ALIGN_CENTER, justify=ALIGN_CENTER)

    # Draw a menu
    def draw_menu(self, menu):
        active_index = menu.get_active_index()
        width = self.get_width_chars()
        height = self.get_height_chars()
        menu_tl = round(width * 0.1), round(height * 0.1)
        menu_br = round(width * 0.9), round(height * 0.9)
        menu_tr = menu_br[X], menu_tl[Y]

        self.draw_title_box(menu_tl, menu_br, menu.get_title())
        self.draw_text((menu_tr[X] - 1, menu_tr[Y] + 1), text=f"{active_index + 1}/{menu.get_num_items()}",
                       align_x=ALIGN_RIGHT, justify=ALIGN_RIGHT)

        scroll_min_x = menu_tl[X] + 6
        scroll_min_y = menu_tl[Y] + 4

        # Depending on the width, the text box description either appears at the side or the bottom
        if self.get_width() < self.get_height():
            split_x = round(width * 0.66)
            split_a = split_x, menu_tl[Y] + 2
            split_b = split_x, menu_br[Y]
            split_f = "|"
            scroll_width = split_x - scroll_min_x - 1
            scroll_height = menu_br[Y] - 1 - scroll_min_y
            desc_width = menu_tr[X] - split_x - 3
            desc_height = scroll_height
        else:
            split_y = round(height * 0.66)
            split_a = menu_tl[X], split_y
            split_b = menu_br[X], split_y
            split_f = "-"
            scroll_width = menu_br[X] - scroll_min_x - 1
            scroll_height = split_y - 1 - scroll_min_y
            desc_width = scroll_width
            desc_height = menu_br[Y] - split_y - 3

        self.draw_line(split_a, split_b, fill=split_f)
        self.draw_character(split_a, fill="+")
        self.draw_character(split_b, fill="+")

        cur_y = scroll_min_y
        line_n = 0
        if scroll_width > 0:
            wrapped_names = []
            needed_lines = []
            # Find out, once each menu item has been wrapped, how many lines will be taken up
            for i in range(menu.get_num_items()):
                title = menu.get_item_name(i)
                wrapped = textwrap.wrap(title, scroll_width)
                line_n += len(wrapped)
                wrapped_names.append(wrapped)
                needed_lines.append(line_n)
                if i != menu.get_num_items() - 1:
                    line_n += 1

            # Find out, if the selected item will not fit onto the screen, which item to start drawing at to fit it in
            start_index = 0
            if needed_lines[active_index] > scroll_height:
                for i in range(len(needed_lines)):
                    if needed_lines[active_index] - needed_lines[i] < scroll_height - 2:
                        break
                    start_index = i

            # Draw each item name
            for i in range(start_index, menu.get_num_items()):
                wrapped = wrapped_names[i]
                len_wrap = len(wrapped)
                max_wrap = scroll_height - cur_y + scroll_min_y
                if len_wrap < max_wrap:
                    max_wrap = len_wrap
                if max_wrap <= 0:
                    break

                self.draw_text((scroll_min_x, cur_y), text="\n".join(wrapped[:max_wrap]),
                               align_x=ALIGN_LEFT, align_y=ALIGN_TOP, justify=ALIGN_LEFT)
                if i == active_index:
                    # If this item is selected, draw the selector arrow
                    self.draw_text((scroll_min_x - 4, cur_y), text="-->")

                cur_y += len_wrap + 1

        # If the width is 0, textwrap will throw an exception
        if desc_width > 0:
            self.draw_text((split_a[X] + 2, split_a[Y] + 2),
                           "\n".join(textwrap.wrap(menu.get_item_description(active_index), desc_width)[:desc_height]),
                            align_x=ALIGN_LEFT, align_y=ALIGN_TOP, justify=ALIGN_LEFT)

    # Draw the main menu screen
    def draw_main_menu(self):
        width = self.get_width()
        width_chars = self.get_width_chars()
        height = self.get_height()
        height_chars = self.get_height_chars()
        # Centre the background picture, depending on the aspect ratio
        if self.get_width() > self.get_height():
            ratio = height / width
            offset = (width_chars - width_chars * ratio) * 0.5
            bg_tl = round(offset), 0
            bg_br = round(width_chars - offset), height_chars
        else:
            ratio = width / height
            offset = (height_chars - height_chars * ratio) * 0.5
            bg_tl = 0, round(offset)
            bg_br = width_chars, round(height_chars - offset)
        self.draw_sprite(bg_tl, bg_br, self.__main_menu_sampler)

        background_height = bg_br[Y] - bg_tl[Y]
        icons_start_y = bg_tl[Y] + background_height * MAINMENU_TEXT_DEPTH
        icons_end_y = bg_tl[Y] + background_height * MAINMENU_MAX_DEPTH
        icons_step_y = (icons_end_y - icons_start_y) * (1 / self.__main_menu_num_icons)
        icons_width = round(icons_step_y * MAINMENU_ICON_RATIO)
        icons_start_x = (self.get_width_chars() - icons_width) // 2
        icons_curr_y = icons_start_y

        box_tl = None
        box_br = None

        points = []

        # Draw the main menu buttons
        for i in range(self.__main_menu_num_icons):
            point_a = icons_start_x, round(icons_curr_y)
            point_b = icons_start_x + icons_width, round(icons_curr_y + icons_step_y)
            points.append((point_a, point_b))
            if i == self.__settings["MAIN_MENU_SELECTOR"]:
                # Find where to highlight the selected button
                box_tl = point_a[X] - 1, point_a[Y] - 1
                box_br = point_b[X] + 1, point_b[Y]
            icons_curr_y = round(icons_curr_y + icons_step_y)

        if box_tl is not None and box_br is not None:
            # The selector
            self.draw_box(box_tl, box_br)

        count = 0
        for icon in self.__main_menu_icons:
            self.draw_sprite(*points[count], icon)
            count += 1

    # Called every time a key is pressed
    def key_press_event(self, event):
        send_message(self.__output_pipe, Message.KEY_PRESS, event.keysym)

    # Called every time a key is released
    def key_release_event(self, event):
        send_message(self.__output_pipe, Message.KEY_RELEASE, event.keysym)

    # Convert a point to screen space, depending on the size of the screen
    def transform_point(self, point, centre, rotation):
        return point_transform(point, centre, -rotation, 20.0,
                               self.get_width(), self.get_height(),
                               self.get_width_chars(), self.get_height_chars()
                               )

    # Called when input begins/ input box is no longer empty
    def input_begin_event(self):
        send_message(self.__output_pipe, Message.INPUT_BEGIN, 0)

    # Called when input ends / input box becomes empty
    def input_end_event(self):
        send_message(self.__output_pipe, Message.INPUT_END, 0)

    # Called when the enter key is pressed
    def return_event(self):
        send_message(self.__output_pipe, Message.COMMAND, self.prev_input)

if __name__ == "__main__":
    main_game = Main()
    #cProfile.run("main_game.begin()")
    main_game.begin()