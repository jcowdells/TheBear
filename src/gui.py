import tkinter as tk
from tkinter import font

class Window(tk.Tk):
    def __init__(self, x, y, width, height, name):
        super().__init__()
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.title(name)
        self.key_press_listeners = []
        self.key_release_listeners = []
        self.bind("<KeyPress>", self.key_press_event)
        self.bind("<KeyRelease>", self.key_release_event)
        self.protocol("WM_DELETE_WINDOW", self.end)
        self.running = False

    def add_key_listener(self, listener):
        self.key_press_listeners.append(listener)

    def add_key_release_listener(self, listener):
        self.key_release_listeners.append(listener)

    def __key_press_event(self, event):
        self.key_press_event(event)
        for listener in self.key_press_listeners:
            listener(event)

    def __key_release_event(self, event):
        self.key_release_event(event)
        for listener in self.key_release_listeners:
            listener(event)

    def key_press_event(self, event):
        pass

    def key_release_event(self, event):
        pass

    def begin(self):
        self.running = True
        while self.running:
            self.main()
            self.update()
            self.update_idletasks()

    def end(self):
        self.running = False

    def main(self):
        pass

class Displayable:
    def __init__(self, *args, **kwargs):
        self.__display = tk.StringVar()

    def set_display(self, display):
        self.__display.set(display)

    def get_display(self):
        return self.__display.get()

    def get_display_obj(self):
        return self.__display

class Text(Displayable, tk.Label):
    def __init__(self, root, bg="white", fg="black", font_name="TkFixedFont"):
        Displayable.__init__(self)
        tk.Label.__init__(self, root, textvariable=self.get_display_obj(), bg=bg, fg=fg, font=font_name,
                          anchor=tk.NW, justify=tk.LEFT)

class Input(Displayable, tk.Entry):
    def __init__(self, root, bg="white", fg="black", font_name="TkFixedFont"):
        Displayable.__init__(self)
        tk.Entry.__init__(self, root, textvariable=self.get_display_obj(), bg=bg, fg=fg, font=font_name)
