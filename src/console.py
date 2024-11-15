from src.gui import *
from tkinter import font

# Change the TkFixedFont size
def tk_fixed_font_size(font_size):
    tk_fixed_font = font.nametofont("TkFixedFont")
    tk_fixed_font.configure(size=font_size)

# Get the width of a fixed font character
def tk_get_fixed_font_width():
    tk_fixed_font = font.nametofont("TkFixedFont")
    return tk_fixed_font.measure("_")

# Get the height of a fixed font character
def tk_get_fixed_font_height():
    tk_fixed_font = font.nametofont("TkFixedFont")
    return tk_fixed_font.metrics("linespace")

# A console window, uses the Window class, and adds the output and input areas
class Console(Window):
    MONO   = 0
    COLOUR = 1
    # Create the console with a width, height, and x, y position
    # The font size and colours can also be set.
    def __init__(self, width, height, x, y, font_size, bg="#000000", fg="#FFFFFF", mode=MONO):
        super().__init__(x, y, width, height, "Console window")
        tk_fixed_font_size(font_size)

        if mode == Console.COLOUR:
            self.__stdout = ColourText(self, bg=bg, fg=fg, font_name="TkFixedFont")
            self.__stdout.tag_configure("test", foreground="red")
            self.__stdout.tag_add("test", "1.1", "1.10")
        else:
            self.__stdout = Text(self, bg=bg, fg=fg, font_name="TkFixedFont")

        self.__mode = mode

        self.__stdin = Input(self, bg=bg, fg=fg, font_name="TkFixedFont")

        self.__inputting = False
        self.prev_input = ""

        self.add_key_release_listener(self.__key_release_listener)
        self.add_configure_listener(self.__configure_listener)

        self.__stdin.focus()
        self.__stdin.pack(side=tk.BOTTOM, fill=tk.X)
        self.__stdout.pack(fill=tk.BOTH, expand=tk.TRUE)

        self._font_width = tk_get_fixed_font_width()
        self._font_height = tk_get_fixed_font_height()

    # Called every time a key is released
    def __key_release_listener(self, event):
        # keysym is used as it works the same on linux and windows
        if event.keysym == "Return":
            self.__return_event()
        if self.__stdin.get_display() != "":
            if not self.__inputting:
                self.input_begin_event()
                self.__inputting = True
        else:
            if self.__inputting:
                self.input_end_event()
                self.__inputting = False

    def __configure_listener(self, _):
        self._font_width = tk_get_fixed_font_width()
        self._font_height = tk_get_fixed_font_height()

    # Called when an input begins
    def input_begin_event(self):
        pass

    # Called when an input ends
    def input_end_event(self):
        pass

    # Runs every time the return key is pressed, and then calls the exposed return event method that can be overridden
    def __return_event(self):
        stdin = self.__stdin.get_display()
        self.__stdin.set_display("")
        self.prev_input = stdin
        self.return_event()

    # Overrideable method
    def return_event(self):
        pass

    # Append data to the output box
    def stdout_a(self, output):
        display = self.__stdout.get_display()
        display += output + "\n"
        self.__stdout.set_display(display)

    # Overwrite data already in the output box
    def stdout_w(self, output):
        self.__stdout.set_display(output)

    def set_colour(self, x, y, colour):
        if hasattr(self.__stdout, "set_colour"):
            self.__stdout.set_colour(x, y, colour)

    # Get the width, in characters, of the output
    def get_width_chars(self):
        return self._width // self._font_width - 1

    # Get the height, in characters, of the output
    def get_height_chars(self):
        return self._height // self._font_height

    # Get the width, in pixels, of the window
    def get_width(self):
        return self._width

    # Get the height, in pixels, of the window
    def get_height(self):
        return self._height

    # Set the text colour of the console
    def set_text_colour(self, colour):
        self.__stdout.configure(foreground=f"#{colour}")
        self.__stdin.configure(foreground=f"#{colour}")

    # Set the background colour of the console
    def set_background_colour(self, colour):
        self.__stdout.configure(background=f"#{colour}")
        self.__stdin.configure(background=f"#{colour}")

    # Set the font size of the console
    def set_font_size(self, font_size):
        self._font_width = tk_get_fixed_font_width()
        self._font_height = tk_get_fixed_font_height()
        tk_fixed_font_size(font_size)
