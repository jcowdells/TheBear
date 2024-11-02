import math
import time
import textwrap
from multiprocessing import Process, Pipe

from src.render import ConsoleGUI, ALIGN_LEFT, ALIGN_CENTER, ALIGN_TOP, ALIGN_RIGHT, ALIGN_BOTTOM, Sampler
from src.geometry import X, Y, point_rotate, point_transform, line_gradient, line_perpendicular, line_intersect, \
    point_inside, line_square_length, point_subtract, vector_from_angle, vector_project, vector_subtract, point_add, \
    line_collision, point_collision, point_normal, vector_from_points, vector_normalise, vector_add, is_path_obstructed, \
    HALF_PI
from src.game import Level, Player, Menu, DisplayEntity, Path
import cProfile
from src.physics import send_message, recv_message, physics_thread, get_entity, TIMESTEP
from src.util import Message

UP = "Up"
DOWN = "Down"
LEFT = "Left"
RIGHT = "Right"

debug_counter = 0

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

        self.level = None
        self.entity_list = []
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
                if message == Message.LEVEL_CHANGED:
                    self.level = data
                if message == Message.ENTITY_CREATED:
                    self.entity_list.append(data)
                if message == Message.ENTITY_UPDATE:
                    entity_id, position, rotation = data
                    entity = get_entity(entity_id, self.entity_list)
                    entity.set_position(position)
                    entity.set_rotation(rotation)
                if message == Message.ENTITY_ANIMATE:
                    entity_id, sampler_index = data
                    entity = get_entity(entity_id, self.entity_list)
                    entity.set_sampler_index(sampler_index)
                if message == Message.FOCUS_ID:
                    self.focus_id = data
                if message == Message.DELTA:
                    self.prev_delta_time = time.perf_counter()
                    self.delta = data
                    for entity in self.entity_list:
                        entity.update()
            except EOFError:
                return

        curr_delta = self.cur_time - self.prev_delta_time
        alpha = curr_delta / self.delta
        alpha = max(0, min(1, alpha))
        debug(f"acct delta {self.delta}")
        debug(f"curr delta {curr_delta}")
        debug(f"     alpha {alpha}")
        debug(f"{self.get_width_chars()} {self.get_height_chars()}")

        focus_entity = get_entity(self.focus_id, self.entity_list)
        if focus_entity is not None:
            focus_centre = focus_entity.get_position(alpha)
            focus_rotation = focus_entity.get_rotation(alpha)
        else:
            focus_centre = (0, 0)
            focus_rotation = 0

        if self.level is not None:
            self.draw_level(self.level, focus_centre, focus_rotation)


        test_point = self.transform_point((-5, -5), focus_centre, focus_rotation)
        self.draw_character(test_point, "Y")

        for entity in self.entity_list:
            self.draw_entity(entity, focus_centre, focus_rotation, alpha)

        self.swap_buffers()

    def draw_entity(self, entity, centre, rotation, alpha):
        if entity.get_display_type() == DisplayEntity.SPRITE:
            entity_centre = entity.get_position(alpha)
            entity_size   = entity.get_size()
            entity_tlr = point_rotate((entity_size, entity_size), rotation + math.pi)
            entity_brr = point_rotate((entity_size, entity_size), rotation)
            entity_tl = self.transform_point(point_add(entity_centre, entity_tlr), centre, rotation)
            entity_br = self.transform_point(point_add(entity_centre, entity_brr), centre, rotation)
            entity_sampler = entity.get_sampler()
            self.draw_sprite(entity_tl, entity_br, entity_sampler)
        elif entity.get_display_type() == DisplayEntity.TEXTURE:
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

        for i in range(len_bounds):
            bound_a = centred_bounds[i]
            if i == len_bounds - 1:
                bound_b = centred_bounds[0]
            else:
                bound_b = centred_bounds[i + 1]

            self.draw_line(bound_a, bound_b, fill=outline)

    def draw_menu(self, menu, active_index):
        width = self.get_width_chars()
        height = self.get_height_chars()
        menu_tl = round(width * 0.1), round(height * 0.1)
        menu_br = round(width * 0.9), round(height * 0.9)
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

        self.draw_line((menu_tl[X], menu_tl[Y] + 2), (menu_tr[X], menu_tr[Y] + 2), fill="-")
        self.draw_character((menu_tl[X], menu_tl[Y] + 2), fill="+")
        self.draw_character((menu_tr[X], menu_tr[Y] + 2), fill="+")

        self.draw_text((width // 2, menu_tl[Y] + 1), text=menu.title)
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

        self.draw_text((split_a[X] + 2, split_a[Y] + 2),
                       "\n".join(textwrap.wrap(menu.get_item_description(active_index), desc_width)[:desc_height]),
                        align_x=ALIGN_LEFT, align_y=ALIGN_TOP, justify=ALIGN_LEFT)


    def key_press_event(self, event):
        send_message(self.output_pipe, Message.KEY_PRESS, event.keysym)

    def key_release_event(self, event):
        send_message(self.output_pipe, Message.KEY_RELEASE, event.keysym)

    def transform_point(self, point, centre, rotation):
        return point_transform(point, centre, -rotation, 20.0,
                               self.get_width(), self.get_height(),
                               self.get_width_chars(), self.get_height_chars()
                               )

    def return_event(self):
        send_message(self.output_pipe, Message.COMMAND, self.prev_input)

if __name__ == "__main__":
    main_game = Main()
    #cProfile.run("main_game.begin()")
    main_game.begin()
