import logging
from tkinter import messagebox
from pdflinker.utils import remove_capturing_pattern, Alignment
import tkinter as tk
from tkinter.ttk import Combobox
import threading
from tqdm.tk import tqdm
from time import sleep
import shelve
import os
from collections import OrderedDict


import sys
sys.path.append("/Users/ashmat/Desktop/Projects/pdflinker/")


##########################
# Logging
root = logging.getLogger("stdout")
root.setLevel(logging.DEBUG)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
root.addHandler(handler)
####################


# Create a Tkinter window
root = tk.Tk()

width = 400


# root.geometry('{}x{}'.format(root.winfo_width(), root.winfo_height()))

# root.config(width=width)
root.resizable(False, False)


def dropdown_callback(event=None):
    print('Currently selected value is:\t%s' % event)


PATTERNS = OrderedDict([
    ("(D)", Alignment.RIGHT),
    ("(D.D)", Alignment.RIGHT),
    ("(D,D)", Alignment.RIGHT),
    ("[D]", Alignment.LEFT_END),
    ("§D", Alignment.LEFT),
])


class PdfLinkerGui():
    SHELVE = os.path.join("gui", "resources", "history")
    PATTERN_WIDTH = 20
    ALIGN_WIDTH = 7
    INDEX_WIDTH = 4
    HISTORY_LENGTH = 10
    PAST_PATTERNS = 4
    logger = logging.getLogger("stdout")

    def __init__(self, root):
        self.logger.debug("__init__")
        self.root = root
        self.pattern_rows = []

        self.success = False

        self.unsaved_state = None
        self.current_state_index = None
        self._combobox_dict = None

        self.db_init()

        self._init_top_buttons()

        self._update_combobox_dict()

        self._init_pattern_input()

        self.run_button = tk.Button(self.root, text="run", command=self.run)
        self.run_button.pack()

        self.string_var = tk.StringVar()
        self.output = tk.Label(self.root,  textvariable=self.string_var)
        self.output.pack()

        self.db_recalc_size()

        self.logger.debug(
            f"size: {self.db_size()}, index: {self.db_get('index',0)}")

    def db_recalc_size(self):
        size = 0
        for i in range(self.db_get("index")+1):
            print(i, self.db_get_state(i))
            if self.db_get_state(i) is not None:
                size += 1
        self._db_set("size", size)

    def _init_top_buttons(self):
        self.top_frame = tk.Frame(self.root)
        self.top_frame.pack(fill=tk.X, expand=True)
        self.top_left_button = tk.Button(
            self.top_frame, text="<", command=self._prev_state)
        self.top_left_button.pack(side=tk.LEFT)
        self.top_right_button = tk.Button(
            self.top_frame, text=">", command=self._next_state)
        self.top_right_button.pack(side=tk.LEFT)
        self._update_button_state()

        # current_value = tk.StringVar()
        # current_value.set("1")
        tk.Label(self.top_frame, text='start:').pack(side=tk.LEFT)
        self.start_spinbox = tk.ttk.Spinbox(
            self.top_frame,
            from_=1,
            to=50,
            wrap=False,
            width=2)
        self.start_spinbox.pack(side=tk.LEFT)
        self.start_spinbox.delete(0, "end")
        self.start_spinbox.insert(0, 1)

        tk.Label(self.top_frame, text='ocr:').pack(side=tk.LEFT)

        choices = ['off', 'eng', 'rus']
        self.ocr_var = tk.StringVar(self.top_frame)
        self.ocr_var.set('off')

        self.ocr_options = tk.OptionMenu(
            self.top_frame, self.ocr_var, *choices)
        self.ocr_options.config(width=2)
        self.ocr_options.pack(side=tk.LEFT)

        self.clear_button = tk.Button(self.top_frame, text="Clear")
        self.clear_button.pack(anchor="e")

    def _update_button_state(self):
        left_state = tk.NORMAL
        right_state = tk.NORMAL

        if self.db_size() == 0:
            left_state = tk.DISABLED

        if self.current_state_index is None:
            right_state = tk.DISABLED
        elif self.db_get_state(self.current_state_index - 1) is None:
            left_state = tk.DISABLED

        self.top_left_button.config(state=left_state)
        self.top_right_button.config(state=right_state)

    def _prev_state(self):
        if self.current_state_index is None:
            self.unsaved_state = self.get_state()
            self.current_state_index = self.db_get("index")-1
        else:
            self.current_state_index -= 1
        self.set_state(self.db_get_state(self.current_state_index))
        self._update_button_state()

    def _next_state(self):
        next_state = self.db_get_state(self.current_state_index + 1)
        if next_state is None:
            self.current_state_index = None
            self.set_state(self.unsaved_state)
        else:
            self.current_state_index += 1
            self.set_state(next_state)
        self._update_button_state()

    def _init_pattern_input(self):
        # Create a frame to hold the input fields
        self.frame = tk.Frame(self.root, width=width)
        # highlightbackground="blue", highlightthickness=2)
        self.frame.pack(fill=tk.X, expand=True)

        # header
        # tk.Label(self.frame, text="", width=self.INDEX_WIDTH).grid(column=0, row=0)
        tk.Label(self.frame, text="regex",
                 width=self.PATTERN_WIDTH).grid(column=1, row=0)
        tk.Label(self.frame, text="align",
                 width=self.ALIGN_WIDTH).grid(column=2, row=0)

        # self.dummy_frame = tk.Frame(self.frame)
        # self.dummy_frame.pack()

        self.button_frame = tk.Frame(self.root,)
        # highlightbackground="blue", highlightthickness=2)
        self.button_frame.pack(side=tk.TOP, fill=tk.X, expand=True)

        # Create a button to add input fields
        self.add_button = tk.Button(
            self.button_frame, text="+", command=self.add_pattern_field)
        self.add_button.pack(side=tk.LEFT)

        self.del_button = tk.Button(
            self.button_frame, text="-", command=self.del_pattern_field, state=tk.DISABLED)
        self.del_button.pack(side=tk.LEFT)
        self.clear_fields_button = tk.Button(
            self.button_frame, text="clear", command=self.clear_fields, state=tk.NORMAL)
        self.clear_fields_button.pack(side=tk.LEFT)

        self.link_button = tk.Button(
            self.button_frame, text="Link", command=self.link_pdf)
        self.link_button.pack(anchor="e")

        self.add_pattern_field()

    def clear_fields(self):
        while len(self.pattern_rows) > 0:
            self.del_pattern_field()
        self.add_pattern_field()
        self.current_state_index = None
        self._update_button_state()

    def del_pattern_field(self):
        if len(self.pattern_rows) > 0:
            # Remove the most recent input field from the list and the GUI
            pattern_row = self.pattern_rows.pop()
            [x.destroy() for x in pattern_row]

            # # Move the Add button back above the input fields
            # self.frame.pack_forget()
            # self.frame.pack()
        if len(self.pattern_rows) == 1:
            self.del_button.config(state=tk.DISABLED)

    def add_pattern_field(self):

        # Create a new input field and add it to the input_fields list
        # frame = tk.Frame(self.frame)

        i_pattern = len(self.pattern_rows)+1

        label = tk.Label(self.frame, text=f'{i_pattern}:')
        label.grid(column=0, row=i_pattern, sticky="e")

        data = list(Alignment)
        alignment_option_var = tk.StringVar(self.frame)
        alignment_option_var.set(str(Alignment.NONE))

        alignment_option = tk.OptionMenu(
            self.frame, alignment_option_var, *data)
        # alignment_option = tk.OptionMenu(self.frame, None, *data)
        alignment_option.config(width=self.ALIGN_WIDTH)
        alignment_option.grid(column=2, row=i_pattern)

        alignment_option.var = alignment_option_var

        # input_alignment = Combobox(self.frame, state="readonly", values=data, width=self.ALIGN_WIDTH)
        # input_alignment.grid(column=2,row=i_pattern)

        input_pattern = Combobox(self.frame, width=self.PATTERN_WIDTH)

        def _update_combobox_values():
            input_pattern["values"] = list(self._combobox_dict.keys())
            self.logger.debug("combobox updated")

        def after_selection(event):
            selection = input_pattern.get()
            self.logger.debug(f"Item selected. Value {selection}")

            alignment = self._combobox_dict.get(selection)
            if alignment is not None:
                alignment_option_var.set(str(alignment))

        input_pattern["postcommand"] = _update_combobox_values
        input_pattern.bind('<<ComboboxSelected>>', after_selection)

        input_pattern.grid(column=1, row=i_pattern)

        self.pattern_rows.append((label, input_pattern, alignment_option))

        if len(self.pattern_rows) > 1:
            self.del_button.config(state=tk.NORMAL)

    def _update_combobox_dict(self):
        self._combobox_dict = OrderedDict(
            list(PATTERNS.items())
            + [("----", None)]
            + list(self.db_get("past_patterns").items())
        )

    def _update_combobox(self):
        data = self._get_combobox_data()
        for _, pattern, _ in self.pattern_rows:
            pattern["values"] = data

    def _set_stop_event(self):
        self.stop_event.set()

    def link_pdf(self):
        self.link_button.config(state=tk.DISABLED)

        self.stop_event = threading.Event()
        self.success = False
        self.thread = threading.Thread(target=self._threaded_task)
        self.thread.start()
        self.root.after(200, self._check_if_ready)

    def _threaded_task(self):
        pbar = tqdm(iterable=range(9000), total=9000, tk_parent=self.root,
                    cancel_callback=self._set_stop_event)
        pwindow = pbar._tk_window
        pwindow.resizable(False, False)

        def on_closing():
            self.stop_event.set()

        pwindow.protocol("WM_DELETE_WINDOW", on_closing)

        width, height, x, y = (
            self.root.winfo_width(), self.root.winfo_height(),
            self.root.winfo_x(), self.root.winfo_y()
        )
        pwindow.geometry(f"{width}x{80}+{x}+{y+18+height}")

        for _ in pbar:
            if self.stop_event.is_set():
                break

            sleep(0.0001)
        else:
            self.success = True

            # pbar.update(1)
        # pbar.close()  # intended usage, might be buggy
         # workaround
        pwindow.destroy()

    def _check_if_ready(self):
        if self.thread.is_alive():
            # not ready yet, run the check again soon
            self.root.after(200, self._check_if_ready)
        else:
            self.link_pdf_callback()

    def link_pdf_callback(self):
        self.logger.debug("task is finished.")
        self.db_store_state(self.get_state())

        self.link_button.config(state=tk.NORMAL)
        tk.Label(self.root, text=str(self.success)).pack()

    def run(self):
        data = []
        for _, pattern, alignment in self.pattern_rows:
            data.append("  ".join(pattern.get() + " " + alignment.var.get()))

        self.string_var.set("\n".join(data))

    def get_state(self):
        state = dict()
        state["ocr"] = self.ocr_var.get()
        state["start"] = self.start_spinbox.get()
        state["patterns"] = []
        for _, pattern, alignment in self.pattern_rows:
            state["patterns"].append(
                {"pattern": pattern.get(),
                 "alignment": alignment.var.get()
                 }
            )
        return state

    def db_init(self):
        with shelve.open(self.SHELVE) as db:
            db["index"] = db.get("index", 0)
            db["size"] = db.get("size", 0)
            db["past_patterns"] = db.get("past_patterns", OrderedDict())

    def db_store_state(self, state):
        if state is None:
            raise Exception("Empty state is to be saved.")
        with shelve.open(self.SHELVE) as db:
            index = db.get("index", 0)
            db[str(index)] = state
            self.logger.debug(f"state is stored at index {index}.")
            db["index"] = index + 1
            db["size"] = db.get("size", 0) + 1

            forget_index_str = str(index - 10)
            if db.get(forget_index_str) is not None:
                del db[forget_index_str]
                db["size"] = db.get("size", 0) - 1

            past_patterns = db["past_patterns"]

            for pattern in state["patterns"]:
                regex = pattern["pattern"]
                alignment = Alignment(pattern["alignment"])

                if regex not in PATTERNS:
                    if regex in past_patterns:
                        past_patterns.pop(regex)
                    elif len(past_patterns) > self.PAST_PATTERNS:
                        first_key = next(iter(past_patterns))
                        past_patterns.pop(first_key)
                    past_patterns[regex] = alignment

            db["past_patterns"] = past_patterns

        self._update_combobox_dict()

    def db_get_state(self, index):
        return self.db_get(str(index))

    def db_size(self):
        return self.db_get("size", 0)

    def db_get(self, key, default=None):
        with shelve.open(self.SHELVE) as db:
            return db.get(key, default)

    def _db_set(self, key, value):
        with shelve.open(self.SHELVE) as db:
            db[key] = value

    def set_state(self, state):
        self.logger.debug("setting state")
        print(state)
        if state is None:
            self.logger.debug("state is None")
            return
        self.ocr_var.set(state["ocr"])
        # self.start_spinbox.set(state["start"])
        for i, pattern_dict in enumerate(state["patterns"]):
            if i == len(self.pattern_rows):
                self.add_pattern_field()
            _, pattern, alignment = self.pattern_rows[i]
            pattern.set(pattern_dict["pattern"]),
            alignment.var.set(pattern_dict["alignment"])
        while len(self.pattern_rows) > len(state["patterns"]):
            self.del_pattern_field()


PdfLinkerGui(root)

# Set the size of the window
# width, height = root.winfo_width(), root.winfo_height()
# screen_height = screen_width = 100
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()

# Calculate the x and y coordinates for the window to appear in the center
x = (screen_width // 3)
y = (screen_height // 3)

# Set the window size and position
root.geometry('+{}+{}'.format(x, y))

# Start the Tkinter event loop
root.mainloop()
