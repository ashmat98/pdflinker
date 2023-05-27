import sys
import logging

from tkinter import messagebox
from pdflinker.utils import remove_capturing_pattern, Alignment
from pdflinker import PdfLinker
import tkinter as tk
from tkinter.ttk import Combobox
from tkinter.filedialog import askopenfilename
import threading
from tqdm.tk import tqdm
from time import sleep
import shelve
import os
from collections import OrderedDict
from pdflinker.utils import choices_dict, process_pattern
import fitz
import tempfile
import shutil
import datetime


ROOT_DIR = os.path.dirname(os.path.abspath(__file__))


# messagebox.showinfo("Information","Informative message")
# messagebox.showerror("Error", "Error message")
# messagebox.showwarning("Warning","Warning message")




##########################
# Logging
root = logging.getLogger("stdlogger")
root.setLevel(logging.DEBUG)

handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
root.addHandler(handler)

# rootLogger = logging.getLogger()
logFormatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
fileHandler = logging.FileHandler("/Users/ashmat/pdflogger.log")
fileHandler.setFormatter(logFormatter)
root.addHandler(fileHandler)


####################


width = 400



PATTERNS = OrderedDict([
    ("(D)", Alignment.RIGHT),
    ("(D.D)", Alignment.RIGHT),
    ("(D,D)", Alignment.RIGHT),
    ("[D]", Alignment.LEFT_END),
    ("§D", Alignment.LEFT),
])


class PdfLinkerGui():
    SHELVE = os.path.join( ROOT_DIR, "resources", "history")
    PATTERN_WIDTH = 20
    ALIGN_WIDTH = 7
    INDEX_WIDTH = 4
    HISTORY_LENGTH = 10
    PAST_PATTERNS = 4
    logger = logging.getLogger("stdlogger")

    def __init__(self, root):
        self.logger.debug("__init__")
        self.logger.debug(f"root dir {ROOT_DIR}")

        # self.tmp_dir = os.path.join(tempfile.gettempdir(), "pdflinker")
        self.tmp_dir = os.path.join("/tmp", "pdflinker")

        if not os.path.exists(self.tmp_dir):
            os.mkdir(self.tmp_dir)

        self.file_path = None
        self.pdf_linker = {"state_hash":None, "pdf_linker": None, "doc": None}
        
        self.root = root
        self.root.title("PdfLinker")

        self.pattern_rows = []

        self.success = False

        self.unsaved_state = None
        self.current_state_index = None
        self.previous_saved_hash = None
        self._combobox_dict = None

        self.db_init()
        self._init_menubar()

        self._init_top_buttons()

        self._update_combobox_dict()

        self._init_pattern_input()

        self._init_bottom_buttons()

        # self.run_button = tk.Button(self.root, text="run", command=self.run)
        # self.run_button.pack()

        self.string_var = tk.StringVar()
        self.output = tk.Label(self.root,  textvariable=self.string_var)
        self.output.pack()

        # self.db_recalc_size()

        # self.root.bind('<Return>', (lambda e, b=self.save_button : b.invoke()))

        self.logger.debug(
            f"size: {self.db_size()}, index: {self.db_get('index',0)}")

    def _init_menubar(self):
        def not_implemented_window():
            filewin = tk.Toplevel(root)
            tk.Label(filewin,text="Not Implemented!").pack()
            self.logger.warning("Not implemented")

        menubar = tk.Menu(self.root)
        filemenu = tk.Menu(menubar, tearoff=0)
        # filemenu.add_command(label="New", command=donothing)
        filemenu.add_command(label="Open", command=self.open_file)
        filemenu.add_command(label="Save", command=lambda: self.save_pdf(copy=False))
        filemenu.add_command(label="Save a copy", command=lambda: self.save_pdf(copy=True))
        # filemenu.add_command(label="Close", command=not_implemented_window)

        filemenu.add_separator()

        filemenu.add_command(label="Open backups", command=self.open_temp_folder)
        # filemenu.add_command(label="Save a backup", command=self.store_temporary)

        filemenu.add_separator()

        filemenu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=filemenu)

        editmenu = tk.Menu(menubar, tearoff=0)
        editmenu.add_command(label="Undo", command=not_implemented_window)

        editmenu.add_separator()

        editmenu.add_command(label="Cut", command=not_implemented_window)
        editmenu.add_command(label="Copy", command=not_implemented_window)
        editmenu.add_command(label="Paste", command=not_implemented_window)
        editmenu.add_command(label="Delete", command=not_implemented_window)
        editmenu.add_command(label="Select All", command=not_implemented_window)
        # menubar.add_cascade(label="Edit", menu=editmenu)
        
        helpmenu = tk.Menu(menubar, tearoff=0)
        helpmenu.add_command(label="Help Index", command=not_implemented_window)
        helpmenu.add_command(label="About...", command=not_implemented_window)
        # menubar.add_cascade(label="Help", menu=helpmenu)

        self.root.config(menu=menubar)

    def open_file(self, filepath=None):
        """Open a file for editing."""
        if filepath is None:
            filepath = askopenfilename(
                filetypes=[("PDF Files", "*.pdf"), ("All Files", "*.*")]
            )
        if not filepath:
            return
        self.logger.debug(f"Selected {filepath}")
        self.file_path = filepath
        self.pdf_linker["state_hash"] = None
        
    def open_temp_folder(self):
        import subprocess
        subprocess.call(["open", "-R", self.tmp_dir])

    def load_pdf(self, file_path):
        self.file_path = file_path
        pl = PdfLinker(
            self.file_path,
            patterns,
            pages=args.pages,
            start=args.start,
            threads= -1 if args.parallel else 1,
            ocr= False if args.ocr is None else True,
            language=args.ocr
            )

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

        self.clear_button = tk.Button(self.top_frame, text="Clear", command=self._clear_links)
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
            self.button_frame, text="Link", command=lambda: self.process_pdf(find=True, create=True))
        self.link_button.pack(anchor="e", side=tk.RIGHT)

        self.scan_button = tk.Button(
            self.button_frame, text="Scan", command=lambda: self.process_pdf(find=True, create=False))
        self.scan_button.pack(anchor="e", side=tk.RIGHT)

        self.add_pattern_field()

    def _init_bottom_buttons(self):
        self.bottom_frame = tk.Frame(self.root)
        self.bottom_frame.pack(side=tk.TOP, fill=tk.X, expand=True)

        self.save_button = tk.Button(
            self.bottom_frame, text="Save", command=lambda: self.save_pdf(copy=False))
        # self.save_button.pack(anchor="e", side=tk.RIGHT)

        self.save_copy_button = tk.Button(
            self.bottom_frame, text="Save copy", command=lambda: self.save_pdf(copy=True))
        # self.save_copy_button.pack(anchor="e", side=tk.RIGHT)

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

        input_pattern = Combobox(self.frame, width=self.PATTERN_WIDTH, height=20)

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


        count_label = tk.Label(self.frame, text=f'')
        count_label.grid(column=3, row=i_pattern)
        

        self.pattern_rows.append((label, input_pattern, alignment_option, count_label))

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
        for _, pattern, _, _ in self.pattern_rows:
            pattern["values"] = data

    def _set_stop_event(self):
        self.stop_event.set()

    def scan_pdf(self):
        self.logger.debug("task is finished.")
        self.db_store_state(self.get_state())
        pass

    def process_pdf(self, find, create):
        self.link_button.config(state=tk.DISABLED)
        self.scan_button.config(state=tk.DISABLED)

        self.stop_event = threading.Event()
        self.success = False
        state = self.get_state()

        self.thread = threading.Thread(target=self._threaded_task, args=(state, find, create))
        self.thread.start()
        self.root.after(200, self._check_if_ready, find, create)

    def _threaded_task(self, state, find=False, create=False):

        patterns = []
        for row in state["patterns"]:
            if row["pattern"] == "":
                messagebox.showwarning(message="Empty pattern is given!")
                return 
            patterns.append((process_pattern(row["pattern"]), row["alignment"]))
        if self.pdf_linker["state_hash"] != state["hash"]:
            self.logger.info("PdfLinker going to be created.")
            try:
                self.pdf_linker["state_hash"] = state["hash"]
                self.pdf_linker["pdf_linker"] = PdfLinker(
                    self.file_path, 
                    patterns,
                    start=int(state["start"])-1,
                    ocr = state["ocr"] != "off",
                    threads=-1,
                    language=state["ocr"])
                self.pdf_linker["doc"] = None
            except Exception() as e:
                self.logger.error(str(e))
                self.logger.exception("Error")
                raise e
            self.logger.info("new PdfLinker created.")

        pl = self.pdf_linker["pdf_linker"]

        
        pbar = tqdm(iterable=range(pl.pages), total=pl.pages, tk_parent=self.root,
                    cancel_callback=self._set_stop_event)
        
        pwindow = pbar._tk_window
        pwindow.resizable(False, False)
        def on_closing():
            self.logger.debug("on_closing called.")
            self.stop_event.set()

        pwindow.protocol("WM_DELETE_WINDOW", on_closing)
        width, height, x, y = (
            self.root.winfo_width(), self.root.winfo_height(),
            self.root.winfo_x(), self.root.winfo_y()
        )
        pwindow.geometry(f"{width}x{80}+{x}+{y+18+height}")

        
        if find is True and pl.find_called is False:            
            n_item = pl.find(pbar, self.stop_event)
            self.logger.debug("find is called.")
            if self.stop_event.is_set():
                pwindow.destroy()
                return
            for n, row in zip(n_item, self.pattern_rows):
                _,_,_,count_label = row
                count_label.config(text=f"  {n} items")

        if create is True and self.pdf_linker["doc"] is None:
            pl.sort()
            self.logger.debug("sort is called.")
            doc, n_link = pl.create_links()
            self.logger.debug("create_links is called.")

            for n_link_, row in zip(n_link, self.pattern_rows):
                _,_,_,count_label = row

                count_label.config(text=count_label["text"] + f", {n_link_} links")

            self.pdf_linker["doc"] = doc

            # doc.save(args.output)
            pass

        # for i in range(pl.pages):
        #     sleep(10)
        #     pbar.update(1)
        self.success = True

        # pbar.close()  # intended usage, might be buggy
         # workaround
        pwindow.destroy()

    def _check_if_ready(self, find, create):
        if self.thread.is_alive():
            # not ready yet, run the check again soon
            self.root.after(200, self._check_if_ready, find, create)
        else:
            self.link_pdf_callback(find, create)

    def link_pdf_callback(self, find, create):
        self.logger.debug(f"task is finished. Sucsess = {self.success}")
        self.db_store_state(self.get_state())

        self.scan_button.config(state=tk.NORMAL)
        self.link_button.config(state=tk.NORMAL)
        if not self.success:
            return
        if create:
            self.save_button.pack(anchor="e", side=tk.RIGHT)
            self.save_copy_button.pack(anchor="e", side=tk.RIGHT)
            
        # tk.Label(self.root, text=str(self.success)).pack()

    def save_pdf(self, copy):
        if copy:
            name, ext= os.path.splitext(self.file_path)
            output = name + " (with links)" + ext
            doc = self.pdf_linker["doc"]
            doc.save(output)
        else:
            self.store_temporary()
            answer  = messagebox.askyesno("Question","Overwrite file?")
            self.logger.debug(f"prompt answered {answer}")
            if answer:
                doc = self.pdf_linker["doc"]
                doc.save(self.file_path, incremental=True, encryption=fitz.PDF_ENCRYPT_KEEP)

    def store_temporary(self):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S")
        filename = now + " " + os.path.split(self.file_path)[1]
        try:
            shutil.copy(self.file_path, os.path.join(self.tmp_dir, filename))
        except Exception as e:
            self.logger.error(str(e))



    def run(self):
        data = []
        for _, pattern, alignment, _ in self.pattern_rows:
            data.append("  ".join(pattern.get() + " " + alignment.var.get()))

        self.string_var.set("\n".join(data))

    def get_state(self):
        state = dict()
        state["ocr"] = self.ocr_var.get()
        state["start"] = self.start_spinbox.get()
        state["patterns"] = []
        for _, pattern, alignment, _ in self.pattern_rows:
            state["patterns"].append(
                {"pattern": pattern.get(),
                 "alignment": alignment.var.get()
                 }
            )
        state["hash"] = hash(repr(state.values()))
        return state

    def db_init(self):
        with shelve.open(self.SHELVE) as db:
            db["index"] = db.get("index", 0)
            db["size"] = db.get("size", 0)
            db["past_patterns"] = db.get("past_patterns", OrderedDict())

    def db_store_state(self, state):
        if state is None:
            raise Exception("Empty state is to be saved.")
        
        if self.previous_saved_hash == state["hash"]:
            return 
        with shelve.open(self.SHELVE) as db:
            index = db.get("index", 0)
            
            db[str(index)] = state
            self.previous_saved_hash = state["hash"]
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
        if state is None:
            self.logger.debug("state is None")
            return
        self.ocr_var.set(state["ocr"])
        # self.start_spinbox.set(state["start"])
        for i, pattern_dict in enumerate(state["patterns"]):
            if i == len(self.pattern_rows):
                self.add_pattern_field()
            _, pattern, alignment, _ = self.pattern_rows[i]
            pattern.set(pattern_dict["pattern"]),
            alignment.var.set(pattern_dict["alignment"])
        while len(self.pattern_rows) > len(state["patterns"]):
            self.del_pattern_field()

    def _clear_links(self):
        pl = PdfLinker(self.file_path, [])
        doc = pl.remove_links()
        self.store_temporary()
        doc.save(self.file_path, incremental=True, encryption=fitz.PDF_ENCRYPT_KEEP)




