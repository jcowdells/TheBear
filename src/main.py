import time
import textwrap

from src.render import ConsoleGUI, ALIGN_LEFT, ALIGN_CENTER, ALIGN_TOP, ALIGN_RIGHT, ALIGN_BOTTOM
from src.geometry import X, Y, point_rotate, point_transform, line_gradient, line_perpendicular, line_intersect, \
    point_inside, line_square_length
from src.game import Level, Player, Menu
import cProfile

UP = "Up"
DOWN = "Down"
LEFT = "Left"
RIGHT = "Right"

debug_counter = 0

class Main(ConsoleGUI):
    def __init__(self):
        super().__init__(480, 360, 100, 100)
        self.level0 = Level("res/level/level0.json")
        self.player = Player((0, 0), 0)

        self.__inputs = {
            DOWN:  False,
            UP:    False,
            RIGHT: False,
            LEFT:  False
        }

        self.prev_time = time.perf_counter()
        self.cur_time  = time.perf_counter()

        self.menu = Menu("INVENTORY")
        self.menu.add_item("Hunting Knife", "This may come in handy if you encounter any bears.")
        self.menu.add_item("Bandage", "Used to quickly repair wounds.")
        self.menu.add_item("Honey", "A good distraction for any bears around.")
        self.menu.add_item("Gold", "Keep it safe.")
        self.menu_index = 0
        self.in_menu = False

    def main(self):
        global debug_counter
        debug_counter = 0
        def debug(msg):
            global debug_counter
            self.draw_text((0, debug_counter), msg, align_x=ALIGN_LEFT, align_y=ALIGN_TOP, justify=ALIGN_LEFT)
            debug_counter += 1

        self.cur_time = time.perf_counter()
        # print(f"FPS: {1 / (self.cur_time - self.prev_time)}")
        self.prev_time = self.cur_time

        if self.key_pressed(LEFT):
            self.player.rotate(-0.003)
        if self.key_pressed(RIGHT):
            self.player.rotate(0.003)

        if self.key_pressed(UP):
            self.player.move(-0.05)
        if self.key_pressed(DOWN):
            self.player.move(0.05)

        position = self.player.get_position()
        debug(f"position: {round(position[X], 3)}, {round(position[Y], 3)}")

        centre = self.transform_point((0, 0), (0, 0), 0)
        self.draw_level(self.level0, self.player.get_position(), self.player.get_rotation())

        if self.in_menu:
            self.draw_menu(self.menu, self.menu_index)

        #print("XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX")

        collided = False

        bounds = self.level0.get_bounds()
        len_bounds = len(bounds)
        for i in range(len_bounds):
            a = bounds[i]
            if i == len_bounds - 1:
                b = bounds[0]
            else:
                b = bounds[i + 1]

            debug(f"l1: {a} -> {b}")

            mx1, my1, c1 = line_gradient(a, b)

            debug(f"l1: {round(mx1, 3)}x + {round(my1, 3)}y + {round(c1, 3)} = 0")

            mx2, my2, c2 = line_perpendicular(mx1, my1, self.player.get_position())

            debug(f"l2: {round(mx2, 3)}x + {round(my2, 3)}y + {round(c2, 3)} = 0")

            p = line_intersect(mx2, my2, c2, mx1, my1, c1)

            screen_pos = self.transform_point(p, self.player.get_position(), self.player.get_rotation())
            self.draw_character(screen_pos, fill="X")

            if point_inside(a, b, p):
                if line_square_length(p, self.player.get_position()) < self.player.get_hitbox_radius()**2:
                    collided = True

        fill = "O"
        if collided:
            fill = "X"
        self.draw_circle(self.transform_point((-1, -1), (0, 0), 0), self.transform_point((1, 1), (0, 0), 0), fill=fill)

        self.swap_buffers()

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
        if self.in_menu:
            if event.keysym == "Down":
                if self.menu_index < self.menu.get_num_items() - 1:
                    self.menu_index += 1
            if event.keysym == "Up":
                if self.menu_index > 0:
                    self.menu_index -= 1
        else:
            if event.keysym in self.__inputs:
                self.__inputs[event.keysym] = True

    def key_release_event(self, event):
        if event.keysym in self.__inputs:
            self.__inputs[event.keysym] = False

    def key_pressed(self, key):
        return self.__inputs[key]

    def transform_point(self, point, centre, rotation):
        return point_transform(point, centre, -rotation, 20.0,
                               self.get_width(), self.get_height(),
                               self.get_width_chars(), self.get_height_chars()
                               )

    def return_event(self):
        if self.prev_input == "open":
            self.in_menu = True
        elif self.prev_input == "close":
            self.in_menu = False

if __name__ == "__main__":
    main_game = Main()
    #cProfile.run("main_game.begin()")
    main_game.begin()
