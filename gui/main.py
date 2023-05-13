import tkinter as tk
from tkinter.ttk import Combobox

# Create a Tkinter window
root = tk.Tk()

# Set the size of the window
width = 400
height = 300
# screen_height = screen_width = 100
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()

# Calculate the x and y coordinates for the window to appear in the center
x = (screen_width // 2) - (width // 2)
y = (screen_height // 2) - (height // 2)

# Set the window size and position
root.geometry('{}x{}+{}+{}'.format(width, height, x, y))


class PdfLinkerGui():
    def __init__(self, root):
        self.root = root
        self.pattern_frames = []

        # Create a frame to hold the input fields
        self.frame = tk.Frame(self.root)
        self.frame.pack()

        # Create a button to add input fields
        self.add_button = tk.Button(self.root, text="+", command=self.add_pattern_field)
        self.add_button.pack()

    def add_pattern_field(self):
        # Create a new input field and add it to the input_fields list
        frame = tk.Frame(self.frame)
        frame.pack()
        label = tk.Label(frame, text='pattern')
        label.pack()

        input_pattern = tk.Entry(frame)
        input_pattern.pack()

        data=("one", "two", "three", "four")
        input_alignment = Combobox(frame, state="readonly", values=data)
        input_alignment.pack()
        
        self.pattern_frames.append(frame)


PdfLinkerGui(root)

# Start the Tkinter event loop
root.mainloop()
