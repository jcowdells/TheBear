import tkinter as tk

# A subclass of Tkinter window, trying to make as many layers of abstraction from tkinter as possible
class Window(tk.Tk):
    # An initialise method for the window, runs a lot of tkinter methods
    def __init__(self, x, y, width, height, name):
        super().__init__()
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.title(name)
        self.__key_press_listeners = []
        self.__key_release_listeners = []
        self.__configure_listeners = []
        self.bind("<KeyPress>", self.__key_press_event)
        self.bind("<KeyRelease>", self.__key_release_event)
        self.protocol("WM_DELETE_WINDOW", self.end)
        self.bind("<Configure>", self.__configure_event)
        self.__running = False
        self._width = width
        self._height = height

    # Add a key press listener
    def add_key_press_listener(self, listener):
        self.__key_press_listeners.append(listener)

    # Add a key release listener
    def add_key_release_listener(self, listener):
        self.__key_release_listeners.append(listener)

    # Add a configure listener
    def add_configure_listener(self, listener):
        self.__configure_listeners.append(listener)

    # Private method to handle tkinter key press event
    def __key_press_event(self, event):
        self.key_press_event(event)
        for listener in self.__key_press_listeners:
            listener(event)

    # Private method to handle tkinter key release event
    def __key_release_event(self, event):
        self.key_release_event(event)
        for listener in self.__key_release_listeners:
            listener(event)

    # Private method to handle tkinter configure
    def __configure_event(self, event):
        self._width = event.width
        self._height = event.height
        self.configure_event(event)
        for listener in self.__configure_listeners:
            listener(event)

    # Overrideable method for key presses
    def key_press_event(self, event):
        pass

    # Overrideable method for key releases
    def key_release_event(self, event):
        pass

    # Overrideable method for configure events
    def configure_event(self, event):
        pass

    # Starts the main loop for the window
    def begin(self):
        self.on_begin()
        self.__running = True
        while self.__running:
            self.update()
            self.update_idletasks()
            self.main()

    # Overrideable method for when window begins loop
    def on_begin(self):
        pass

    # Ends the main loop
    def end(self):
        self.__running = False
        self.on_end()

    # Called when the window stops running
    def on_end(self):
        pass

    # Overrideable method, called every frame
    def main(self):
        pass

class Displayable:
    def set_display(sel, display):
        pass

    def get_display(self):
        return None

    def get_display_obj(self):
        return None

# Class that handles tkinter objects that require a StringVar, and allows them to be accessed directory
# Basically avoids Class.get_string_var().set_value() or something
class StringVarDisplayable(Displayable):
    # Init method, create the string var
    def __init__(self, *args, **kwargs):
        self.__display = tk.StringVar()

    # Set the stored value
    def set_display(self, display):
        self.__display.set(display)

    # Get the stored value
    def get_display(self):
        return self.__display.get()

    # Get the actual string var object
    def get_display_obj(self):
        return self.__display

# Wrapper class for tkinter labels
class Text(StringVarDisplayable, tk.Label):
    def __init__(self, root, bg="black", fg="white", font_name="TkFixedFont"):
        StringVarDisplayable.__init__(self)
        tk.Label.__init__(self, root, textvariable=self.get_display_obj(), bg=bg, fg=fg, font=font_name,
                          anchor=tk.NW, justify=tk.LEFT)

# Wrapper class for tkinter entries
class Input(StringVarDisplayable, tk.Entry):
    def __init__(self, root, bg="black", fg="white", font_name="TkFixedFont"):
        StringVarDisplayable.__init__(self)
        tk.Entry.__init__(self, root, textvariable=self.get_display_obj(), bg=bg, fg=fg, font=font_name,
                          borderwidth=0, highlightthickness=0)

class ColourText(Displayable, tk.Text):
    def __init__(self, root, bg="black", fg="white", font_name="TkFixedFont"):
        tk.Text.__init__(self, root, bg=bg, fg=fg, font=font_name, borderwidth=0, highlightthickness=0)
        self.config(state=tk.NORMAL)
        self.__length = 0
        self.__display = ""

    def clear_display(self):
        if self.__length > 0:
            self.delete(1.0, tk.END)

    def set_display(self, display):
        self.clear_display()
        self.insert(tk.INSERT, display)
        self.__length = len(display)
        self.__display = display

    def get_display(self):
        return self.__display

    def create_tag(self, index):
        tag_name = str(index)
        self.tag_delete(tag_name)
        self.tag_add(tag_name, f"1.{index}", f"1.{index + 1}")
        return tag_name

    def set_colour(self, index, colour):
        tag_name = self.create_tag(index)
        self.tag_configure(tag_name, foreground=colour)