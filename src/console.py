import tkinter as tk
from tkinter import font

def tk_fixed_font_size(font_size):
    tkfixedfont = font.nametofont("TkFixedFont")
    tkfixedfont.configure(size=20)

class Console:
    def __init__(self, width, height, x, y, font_size):
        self.__root = tk.Tk()
        tk_fixed_font_size(font_size)

        self.__stdout = tk.StringVar()
        self.__stdin  = tk.StringVar()

        self.__tk_stdout = tk.Label(self.__root,
                                    textvariable=self.__stdout,
                                    bg="black", fg="white", font="TkFixedFont")
        self.__tk_stdin  = tk.Entry(self.__root,
                                    textvariable=self.__stdin,
                                    bg="black", fg="white", font="TkFixedFont")

        self.__tk_stdin.pack(side=tk.BOTTOM, fill=tk.X)
        self.__tk_stdout.pack(fill=tk.BOTH, expand=tk.TRUE)

        self.__running = True

    def main(self):
        while self.__running:
            self.__root.update()
            self.__root.update_idletasks()
