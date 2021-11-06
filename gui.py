from tkinter import Tk, Button, Frame, Label, messagebox, StringVar
from main import *
import random


class GUI(Frame):
    WIDTH = config.TABLE_SIZE
    HEIGHT = config.TABLE_SIZE
    FONT_SIZE = 25

    def __init__(self, master=None):
        if master is None:
            master = Tk()
        super().__init__(master)
        master.title("Renju")
        self.master = master

        self.buttons = [[None] * self.WIDTH for _ in range(self.HEIGHT)]
        self.text = [[None] * self.WIDTH for _ in range(self.HEIGHT)]
        self.labels = []

        self.create_widgets()

        self.table = Table([])
        self.is_cpu_first = bool(random.randint(0, 1))
        self.state = 1  # 1: playing, 2: end
        if self.is_cpu_first:
            self.cpu_move()

    def create_widgets(self):
        for i in range(self.HEIGHT):
            self.labels.append(Label(self, text=str(i + 1)).grid(column=0, row=i + 1))
            self.labels.append(Label(self, text=str(i + 1)).grid(column=i + 1, row=0))

        for y in range(self.HEIGHT):
            for x in range(self.WIDTH):
                self.text[y][x] = StringVar()
                self.text[y][x].set('')
                self.buttons[y][x] = Button(self, textvariable=self.text[y][x], width=2, height=1, relief='groove',
                                            command=self.push(y, x)).grid(column=x + 1, row=y + 1)
        self.grid(column=0, row=0)

    def push(self, y, x):
        def wrapper():
            print('Player chose [y: {}, x: {}]'.format(y + 1, x + 1))
            if self.state == 2:
                return
            if Point(y, x) in self.table.table:
                print("already placed")
                messagebox.showinfo("already placed", "already placed")
                return

            me = self.table.me
            self.text[y][x].set(' ●○'[me])
            res = self.table.compute_move(Move(me, Point(y, x)))
            if res:
                print("CPU Win(foul move)")
                messagebox.showinfo("CPU Win(foul move)", "CPU Win(foul move)")
                self.state = 2

            if self.table.is_win(me):
                print("You Win")
                messagebox.showinfo("You Win", "You Win")
                self.state = 2

            if self.state != 2:
                self.cpu_move()

        return wrapper

    def cpu_move(self):
        move, op = self.table.choose_next_move(self.table.me, depth=2, best=3)
        print('CPU chose [y: {}, x: {}]'.format(move.point.y + 1, move.point.x + 1))
        self.text[move.point.y][move.point.x].set(' ●○'[move.program_number])
        self.table.compute_move(move)
        if self.table.is_win(move.program_number):
            print("CPU Win")
            messagebox.showinfo("CPU Win", "CPU Win")
            self.state = 2


if __name__ == '__main__':
    gui = GUI()
    gui.mainloop()
