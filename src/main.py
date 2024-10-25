from src.render import ConsoleGUI
from src.geometry import X, Y, point_rotate
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

    def main(self):
        delta = 0

        if self.key_pressed(LEFT):
            self.player.rotate(-0.01)
        if self.key_pressed(RIGHT):
            self.player.rotate(0.01)

        if self.key_pressed(UP):
            self.player.move(-0.05)
        if self.key_pressed(DOWN):
            self.player.move(0.05)

        self.draw_level(self.level0, self.player.get_position(), self.player.get_rotation())
        self.swap_buffers()

    def draw_level(self, level, centre, rotation):
        centred_bounds = []
        for x, y in level.get_bounds():
            point = round(x - centre[X]), round(y - centre[Y])
            point = point_rotate(point, centre, -rotation)
            point = (point[X] + self.get_width_chars() // 2, point[Y] + self.get_height_chars() // 2)
            centred_bounds.append(point)

        print("")

        outline = level.get_outline()

        len_bounds = len(centred_bounds)
        for i in range(len_bounds):
            bound_a = centred_bounds[i]
            if i == len_bounds - 1:
                bound_b = centred_bounds[0]
            else:
                bound_b = centred_bounds[i + 1]

            print(bound_a, bound_b)

            self.draw_line(bound_a, bound_b, fill=outline)

    def key_press_event(self, event):
        if event.keysym in self.__inputs:
            self.__inputs[event.keysym] = True

    def key_release_event(self, event):
        if event.keysym in self.__inputs:
            self.__inputs[event.keysym] = False

    def key_pressed(self, key):
        return self.__inputs[key]


if __name__ == "__main__":
    main_game = Main()
    main_game.begin()
