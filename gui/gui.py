import tkinter as tk

def button_clicked():
    print("Button clicked!")
    print("Input value:", input_box.get())
    print("Checkbox 1 value:", var1.get())
    print("Checkbox 2 value:", var2.get())

# Create the window
window = tk.Tk()
window.title("Python GUI")

# Create an input box
input_box = tk.Entry(window)
input_box.pack()

# Create two checkboxes
var1 = tk.BooleanVar()
checkbox1 = tk.Checkbutton(window, text="Checkbox 1", variable=var1)
checkbox1.pack()

var2 = tk.BooleanVar()
checkbox2 = tk.Checkbutton(window, text="Checkbox 2", variable=var2)
checkbox2.pack()

# Create a button
button = tk.Button(window, text="Click Me!", command=button_clicked)
button.pack()

# Run the GUI
window.mainloop()
