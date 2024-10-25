import time

from src.render import ConsoleGUI
from src.geometry import X, Y, point_rotate, point_transform
from src.game import Level, Player
import cProfile

UP = "Up"
DOWN = "Down"
LEFT = "Left"
RIGHT = "Right"

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

    def main(self):
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

        centre = self.transform_point((0, 0), (0, 0), 0)
        self.draw_character(centre, fill="I")
        self.draw_level(self.level0, self.player.get_position(), self.player.get_rotation())
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

    def key_press_event(self, event):
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


if __name__ == "__main__":
    main_game = Main()
    main_game.begin()
