import tkinter as tk

root = tk.Tk()

root.geometry('300x75')

root.title("Hello, World!")

def command():
    print("Hello, World!")

label = tk.Button(
    root,
    text="Hello, World!",
    font=("Consolas", 20),
    command=command
)
label.pack()

root.mainloop()

