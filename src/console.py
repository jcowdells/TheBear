from src.gui import *

def tk_fixed_font_size(font_size):
    tk_fixed_font = font.nametofont("TkFixedFont")
    tk_fixed_font.configure(size=font_size)

def tk_get_fixed_font_width():
    tk_fixed_font = font.nametofont("TkFixedFont")
    return tk_fixed_font.measure("_")

def tk_get_fixed_font_height():
    tk_fixed_font = font.nametofont("TkFixedFont")
    return tk_fixed_font.metrics("linespace")

class Console(Window):
    def __init__(self, width, height, x, y, font_size, bg="#000000", fg="#FFFFFF"):
        super().__init__(x, y, width, height, "Console window")
        tk_fixed_font_size(font_size)

        self.__stdout = Text(self, bg=bg, fg=fg, font_name="TkFixedFont")
        self.__stdin = Input(self, bg=bg, fg=fg, font_name="TkFixedFont")

        self.__stdin.pack(side=tk.BOTTOM, fill=tk.X)
        self.__stdout.pack(fill=tk.BOTH, expand=tk.TRUE)

        self.__running = True

    def key_release_event(self, event):
        if event.keysym == "Return":
            self.return_event()

    def return_event(self):
        stdin = self.__stdin.get_display()
        self.__stdin.set_display("")
        self.stdout_a("You said: " + stdin)

    def stdout_a(self, output):
        display = self.__stdout.get_display()
        display += output + "\n"
        self.__stdout.set_display(display)

    def stdout_w(self, output):
        self.__stdout.set_display(output)

    def get_width_chars(self):
        return self.__stdout.winfo_width() // tk_get_fixed_font_width()

    def get_height_chars(self):
        return self.__stdout.winfo_height() // tk_get_fixed_font_height()

    def main(self):
        pass
