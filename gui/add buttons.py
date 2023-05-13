import tkinter as tk

class InputFieldCreator:
    def __init__(self, master):
        self.master = master
        self.input_fields = []

        # Create a frame to hold the input fields
        self.frame = tk.Frame(self.master)
        self.frame.pack()

        # Create a button to add input fields
        self.add_button = tk.Button(self.master, text="Add Input Field", command=self.add_input_field)
        self.add_button.pack()

    def add_input_field(self):
        # Create a new input field and add it to the input_fields list
        input_field = tk.Entry(self.frame)
        input_field.pack()
        self.input_fields.append(input_field)

# Create a Tkinter window
root = tk.Tk()

# Create an instance of InputFieldCreator
input_field_creator = InputFieldCreator(root)

# Start the Tkinter event loop
root.mainloop()
