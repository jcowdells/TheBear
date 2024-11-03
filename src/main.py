import math
import time
import textwrap
from multiprocessing import Process, Pipe

from lxml.html.builder import CENTER

from src import util
from src.render import ConsoleGUI, ALIGN_LEFT, ALIGN_CENTER, ALIGN_TOP, ALIGN_RIGHT, ALIGN_BOTTOM, Sampler, \
    sampler_array
from src.geometry import X, Y, point_rotate, point_transform, line_gradient, line_perpendicular, line_intersect, \
    point_inside, line_square_length, point_subtract, vector_from_angle, vector_project, vector_subtract, point_add, \
    line_collision, point_collision, point_normal, vector_from_points, vector_normalise, vector_add, is_path_obstructed, \
    HALF_PI, point_multiply
from src.game import Level, Player, Menu, DisplayEntity, Path
import cProfile
from src.physics import send_message, recv_message, physics_thread, get_by_id, TIMESTEP, GameState
from src.util import Message

UP = "Up"
DOWN = "Down"
LEFT = "Left"
RIGHT = "Right"

debug_counter = 0

MAINMENU_ICON_RATIO = 4.72
MAINMENU_TEXT_DEPTH = 0.333
MAINMENU_MAX_DEPTH  = 0.922

class Main(ConsoleGUI):
    def __init__(self):
        super().__init__(480, 360, 100, 100)

        self.prev_time = time.perf_counter()
        self.cur_time  = time.perf_counter()

        self.prev_delta_time = time.perf_counter()
        self.delta = 1

        input_pipe, self.output_pipe = Pipe()
        self.input_pipe, output_pipe  = Pipe()
        self.physics = Process(target=physics_thread, args=(input_pipe, output_pipe))

        self.main_menu_sampler = Sampler("res/textures/mainmenu.tex")
        self.main_menu_icons = sampler_array("res/textures/mainmenu_icons")
        self.main_menu_num_icons = len(self.main_menu_icons)

        self.game_state = GameState.MAIN_MENU
        self.settings = {
            "MAIN_MENU_SELECTOR": 0,
            "DISPLAY_INFO": False,
            "TIME_REMAINING": 0,
            "COLLECTED_GOLD": 0
        }
        self.level = None
        self.entity_list = []
        self.menu_list = []
        self.text_box_list = []
        self.progress_bar_list = []
        self.focus_id = 0

    def on_begin(self):
        self.physics.start()

    def on_end(self):
        send_message(self.output_pipe, Message.EXIT, 0)
        self.physics.join()

    def main(self):
        global debug_counter
        debug_counter = 0
        def debug(msg):
            global debug_counter
            self.draw_text((0, debug_counter), msg, align_x=ALIGN_LEFT, align_y=ALIGN_TOP, justify=ALIGN_LEFT)
            debug_counter += 1

        self.cur_time = time.perf_counter()
        fps = 1 / (self.cur_time - self.prev_time)
        debug(f"FPS: {fps}")
        self.prev_time = self.cur_time

        while self.input_pipe.poll():
            try:
                message, data = recv_message(self.input_pipe)
                if message == Message.EXIT:
                    self.end()
                elif message == Message.LEVEL_CHANGED:
                    self.level = data
                elif message == Message.ENTITY_CREATED:
                    self.entity_list.append(data)
                elif message == Message.ENTITY_UPDATE:
                    entity_id, position, rotation = data
                    entity = get_by_id(entity_id, self.entity_list)
                    entity.set_position(position)
                    entity.set_rotation(rotation)
                elif message == Message.ENTITY_ANIMATE:
                    entity_id, sampler_index = data
                    entity = get_by_id(entity_id, self.entity_list)
                    entity.set_sampler_index(sampler_index)
                elif message == Message.ENTITY_VISIBLE:
                    entity_id, visible = data
                    entity = get_by_id(entity_id, self.entity_list)
                    entity.set_visible(visible)
                elif message == Message.ENTITY_KILL:
                    for entity in self.entity_list:
                        if entity.get_id() == data:
                            self.entity_list.remove(entity)
                            break
                elif message == Message.FOCUS_ID:
                    self.focus_id = data
                elif message == Message.DELTA:
                    self.prev_delta_time = time.perf_counter()
                    self.delta = data
                    for entity in self.entity_list:
                        entity.update()
                elif message == Message.MENU_CREATED:
                    self.menu_list.append(data)
                elif message == Message.MENU_ADD_ITEM:
                    menu_id, item = data
                    menu = get_by_id(menu_id, self.menu_list)
                    menu.add_item(*item)
                elif message == Message.MENU_CHANGE_INDEX:
                    menu_id, index = data
                    menu = get_by_id(menu_id, self.menu_list)
                    menu.set_active_index(index)
                elif message == Message.MENU_VISIBLE:
                    menu_id, visible = data
                    menu = get_by_id(menu_id, self.menu_list)
                    menu.set_visible(visible)
                elif message == Message.TEXT_BOX_CREATED:
                    self.text_box_list.append(data)
                elif message == Message.TEXT_BOX_VISIBLE:
                    text_box_id, visible = data
                    text_box = get_by_id(text_box_id, self.text_box_list)
                    text_box.set_visible(visible)
                elif message == Message.GAME_STATE_CHANGED:
                    self.game_state = data
                elif message == Message.UPDATE_SETTING:
                    key, value = data
                    self.settings[key] = value
                elif message == Message.PROGRESS_BAR_CREATED:
                    self.progress_bar_list.append(data)
                elif message == Message.PROGRESS_BAR_UPDATE:
                    progress_bar_id, position, progress = data
                    progress_bar = get_by_id(progress_bar_id, self.progress_bar_list)
                    progress_bar.set_position(position)
                    progress_bar.set_progress(progress)
                elif message == Message.PROGRESS_BAR_VISIBLE:
                    progress_bar_id, visible = data
                    progress_bar = get_by_id(progress_bar_id, self.progress_bar_list)
                    progress_bar.set_visible(visible)
            except EOFError:
                return

        curr_delta = self.cur_time - self.prev_delta_time
        alpha = curr_delta / self.delta
        alpha = max(0, min(1, alpha))
        debug(f"acct delta {self.delta}")
        debug(f"curr delta {curr_delta}")
        debug(f"     alpha {alpha}")
        debug(f"{self.get_width_chars()} {self.get_height_chars()}")

        focus_entity = get_by_id(self.focus_id, self.entity_list)
        if focus_entity is not None:
            focus_centre = focus_entity.get_position(alpha)
            focus_rotation = focus_entity.get_rotation(alpha)
        else:
            focus_centre = (0, 0)
            focus_rotation = 0
        if self.game_state == GameState.MAIN_MENU:
            self.draw_main_menu()
        elif self.game_state == GameState.GAME:
            if self.level is not None:
                self.draw_level(self.level, focus_centre, focus_rotation)

            for entity in self.entity_list:
                if entity.get_visible():
                    self.draw_entity(entity, focus_centre, focus_rotation, alpha)

        for progress_bar in self.progress_bar_list:
            if progress_bar.get_visible():
                self.draw_progress_bar(progress_bar, focus_centre, focus_rotation)

        for menu in self.menu_list:
            if menu.get_visible():
                self.draw_menu(menu)

        for text_box in self.text_box_list:
            if text_box.get_visible():
                self.draw_text_box(text_box)

        if self.settings["DISPLAY_INFO"]:
            width_chars = self.get_width_chars() - 1
            y = 0
            self.draw_text((width_chars, y), f"Time remaining: {self.settings["TIME_REMAINING"]}",
                           align_x=ALIGN_RIGHT, align_y=ALIGN_TOP, justify=ALIGN_RIGHT)
            y += 1
            self.draw_text((width_chars, y), f"Collected gold: {self.settings["COLLECTED_GOLD"]}",
                           align_x=ALIGN_RIGHT, align_y=ALIGN_TOP, justify=ALIGN_RIGHT)

        self.swap_buffers()

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

            entity_ar = point_rotate((entity_size, entity_size), entity_rotation + math.pi)
            entity_br = point_rotate((entity_size, entity_size), entity_rotation - HALF_PI)
            entity_cr = point_rotate((entity_size, entity_size), entity_rotation)
            entity_dr = point_rotate((entity_size, entity_size), entity_rotation + HALF_PI)

            entity_a = self.transform_point(point_add(entity_centre, entity_ar), centre, rotation)
            entity_b = self.transform_point(point_add(entity_centre, entity_br), centre, rotation)
            entity_c = self.transform_point(point_add(entity_centre, entity_cr), centre, rotation)
            entity_d = self.transform_point(point_add(entity_centre, entity_dr), centre, rotation)

            entity_sampler = entity.get_sampler()
            self.draw_sampler(entity_a, entity_b, entity_c, (0, 0), (1, 0), (1, 1), entity_sampler)
            self.draw_sampler(entity_a, entity_c, entity_d, (0, 0), (1, 1), (0, 1), entity_sampler)

    def draw_level(self, level, centre, rotation):
        centred_bounds = []
        for point in level.get_bounds():
            point = self.transform_point(point, centre, rotation)
            centred_bounds.append(point)

        outline = level.get_outline()
        len_bounds = len(centred_bounds)

        for i in range(level.get_num_textures()):
            sampler_index, c1, c2, c3, c4 = level.get_texture(i)
            sampler = level.get_sampler(sampler_index)
            a = centred_bounds[c1]
            b = centred_bounds[c2]
            c = centred_bounds[c3]
            d = centred_bounds[c4]
            self.draw_sampler(a, b, c, (0, 0), (1, 0), (1, 1), sampler)
            self.draw_sampler(a, c, d, (0, 0), (1, 1), (0, 1), sampler)

        exit_index = level.get_exit_index()
        for i in range(len_bounds):
            bound_a = centred_bounds[i]
            if i == len_bounds - 1:
                bound_b = centred_bounds[0]
            else:
                bound_b = centred_bounds[i + 1]

            if i == exit_index:
                exit_centre = point_add(bound_a, bound_b)
                exit_centre = exit_centre[X] // 2, exit_centre[Y] // 2
                self.draw_text(exit_centre, "EXIT", align_x=ALIGN_CENTER, align_y=ALIGN_CENTER, justify=ALIGN_CENTER)
            else:
                self.draw_line(bound_a, bound_b, fill=outline)

    def draw_box(self, menu_tl, menu_br):
        menu_tr = menu_br[X], menu_tl[Y]
        menu_bl = menu_tl[X], menu_br[Y]

        self.draw_rectangle(menu_tl, menu_br, fill=" ")

        self.draw_line(menu_tl, menu_tr, fill="-")
        self.draw_line(menu_bl, menu_br, fill="-")
        self.draw_line(menu_tl, menu_bl, fill="|")
        self.draw_line(menu_tr, menu_br, fill="|")

        self.draw_character(menu_tl, fill="+")
        self.draw_character(menu_tr, fill="+")
        self.draw_character(menu_br, fill="+")
        self.draw_character(menu_bl, fill="+")

    def draw_title_box(self, menu_tl, menu_br, title):
        menu_tr = menu_br[X], menu_tl[Y]
        self.draw_box(menu_tl, menu_br)
        self.draw_line((menu_tl[X], menu_tl[Y] + 2), (menu_tr[X], menu_tr[Y] + 2), fill="-")
        self.draw_character((menu_tl[X], menu_tl[Y] + 2), fill="+")
        self.draw_character((menu_tr[X], menu_tr[Y] + 2), fill="+")

        title_pos = (menu_tl[X] + menu_br[X]) // 2, menu_tl[Y] + 1
        self.draw_text(title_pos, title, align_x=ALIGN_CENTER, align_y=ALIGN_TOP, justify=ALIGN_CENTER)

    def draw_text_box(self, text_box):
        content = text_box.get_content()
        width = self.get_width_chars()
        height = self.get_height_chars()
        box_width = text_box.get_max_width()
        box_height = text_box.get_max_height()
        max_width = round(width * box_width)
        max_height = round(height * box_height)
        if max_width > 4 and max_height > 6:
            display = "\n".join(textwrap.wrap(content, max_width - 4)[:max_height - 6])
        else:
            display = ""
        text_width, text_height = util.find_string_size(display)

        if text_width > max_width - 4:
            box_width = max_width
        else:
            box_width = text_width + 3

        if text_height > max_height - 6:
            box_height = max_height
        else:
            box_height = text_height + 5

        if max_width > 0:
            half_box_width = box_width / width * 0.5
            half_box_height = box_height / height * 0.5
            box_tl = round(width * (0.5 - half_box_width)), round(height * (0.5 - half_box_height))
            box_br = round(box_tl[X] + box_width), round(box_tl[Y] + box_height)
            self.draw_title_box(box_tl, box_br, text_box.get_title())
            text_tl = box_tl[X] + 2, box_tl[Y] + 4
            self.draw_text(text_tl, display, align_x=ALIGN_LEFT, align_y=ALIGN_TOP, justify=ALIGN_LEFT)

    def draw_progress_bar(self, progress_bar, centre, rotation):
        width = round(self.get_width_chars() * progress_bar.get_width())
        num_chars = width - 2
        num_chars_filled = round(num_chars * progress_bar.get_progress())
        num_chars_blank = num_chars - num_chars_filled
        display = "[" + "#" * num_chars_filled + " " * num_chars_blank + "]"
        position = self.transform_point(progress_bar.get_position(), centre, rotation)
        self.draw_text(position, display, align_x=ALIGN_CENTER, align_y=ALIGN_CENTER, justify=ALIGN_CENTER)

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
            for i in range(menu.get_num_items()):
                title = menu.get_item_name(i)
                wrapped = textwrap.wrap(title, scroll_width)
                line_n += len(wrapped)
                wrapped_names.append(wrapped)
                needed_lines.append(line_n)
                if i != menu.get_num_items() - 1:
                    line_n += 1

            start_index = 0
            if needed_lines[active_index] > scroll_height:
                for i in range(len(needed_lines)):
                    if needed_lines[active_index] - needed_lines[i] < scroll_height - 2:
                        break
                    start_index = i

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
                    self.draw_text((scroll_min_x - 4, cur_y), text="-->")

                cur_y += len_wrap + 1

        if desc_width > 0:
            self.draw_text((split_a[X] + 2, split_a[Y] + 2),
                           "\n".join(textwrap.wrap(menu.get_item_description(active_index), desc_width)[:desc_height]),
                            align_x=ALIGN_LEFT, align_y=ALIGN_TOP, justify=ALIGN_LEFT)

    def draw_main_menu(self):
        width = self.get_width()
        width_chars = self.get_width_chars()
        height = self.get_height()
        height_chars = self.get_height_chars()
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
        self.draw_sprite(bg_tl, bg_br, self.main_menu_sampler)

        background_height = bg_br[Y] - bg_tl[Y]
        icons_start_y = bg_tl[Y] + background_height * MAINMENU_TEXT_DEPTH
        icons_end_y = bg_tl[Y] + background_height * MAINMENU_MAX_DEPTH
        icons_step_y = (icons_end_y - icons_start_y) * (1 / self.main_menu_num_icons)
        icons_width = round(icons_step_y * MAINMENU_ICON_RATIO)
        icons_start_x = (self.get_width_chars() - icons_width) // 2
        icons_curr_y = icons_start_y

        box_tl = None
        box_br = None

        points = []

        for i in range(self.main_menu_num_icons):
            point_a = icons_start_x, round(icons_curr_y)
            point_b = icons_start_x + icons_width, round(icons_curr_y + icons_step_y)
            points.append((point_a, point_b))
            if i == self.settings["MAIN_MENU_SELECTOR"]:
                box_tl = point_a[X] - 1, point_a[Y] - 1
                box_br = point_b[X] + 1, point_b[Y]
            icons_curr_y = round(icons_curr_y + icons_step_y)

        if box_tl is not None and box_br is not None:
            self.draw_box(box_tl, box_br)

        count = 0
        for icon in self.main_menu_icons:
            self.draw_sprite(*points[count], icon)
            count += 1

    def key_press_event(self, event):
        send_message(self.output_pipe, Message.KEY_PRESS, event.keysym)

    def key_release_event(self, event):
        send_message(self.output_pipe, Message.KEY_RELEASE, event.keysym)

    def transform_point(self, point, centre, rotation):
        return point_transform(point, centre, -rotation, 20.0,
                               self.get_width(), self.get_height(),
                               self.get_width_chars(), self.get_height_chars()
                               )

    def input_begin_event(self):
        send_message(self.output_pipe, Message.INPUT_BEGIN, 0)

    def input_end_event(self):
        send_message(self.output_pipe, Message.INPUT_END, 0)

    def return_event(self):
        send_message(self.output_pipe, Message.COMMAND, self.prev_input)

if __name__ == "__main__":
    main_game = Main()
    #cProfile.run("main_game.begin()")
    main_game.begin()
