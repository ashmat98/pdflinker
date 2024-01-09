from tqdm import tqdm
import tkinter as tk
from tkinter.ttk import Progressbar
import threading

class PBar:
    def __init__(self, parent, iterable, total):
        self.tqdm_pbar = tqdm(iterable=iterable, total=total)


        self.pwindow= tk.Toplevel(parent)
        pwindow = self.pwindow

        pwindow.protocol("WM_DELETE_WINDOW", self.on_stopping)

        
        self.stop_event = threading.Event()

        pwindow.title("Running...")
        pwindow.resizable(False, False)

        width, height, x, y = (
            parent.winfo_width(), parent.winfo_height(),
            parent.winfo_x(), parent.winfo_y()
        )
        pwindow.geometry(f"{width}x{80}+{x}+{y+18+height}")
       
        top_frame = tk.Frame(pwindow)
        top_frame.pack(fill=tk.X, expand=True, padx=20)

        self.pb = Progressbar(
            top_frame,
            orient='horizontal',
            mode='determinate'
        )
        self.pb_perc = tk.Label(top_frame, text="0 %")
        # pb.pack(fill=tk.X, side=tk.LEFT)
        self.pb.pack(fill=tk.X, side=tk.LEFT, expand=True, padx=20)
        self.pb_perc.pack(side=tk.RIGHT)
        
        bottom_frame = tk.Frame(pwindow)
        bottom_frame.pack(fill=tk.X, expand=True, padx=20)
        self.pb_label = tk.Label(bottom_frame, text=" ")
        pb_stop_btn = tk.Button(bottom_frame, text="stop", 
                                command=self.on_stopping)
        self.pb_label.pack(side=tk.LEFT, fill=tk.X)
        pb_stop_btn.pack(side=tk.RIGHT)

    def update(self, i):
        pbar = self.tqdm_pbar
        pbar.update(i)

        self.pb['value'] = (100* pbar.format_dict["n"] / pbar.format_dict["total"])
        self.pb_perc["text"] = "{:.1f} %".format(self.pb['value'])
        elapsed = pbar.format_interval(pbar.format_dict["elapsed"])
        rate = pbar.format_dict["rate"]
        remaining = pbar.format_interval(
            (pbar.total - pbar.n) / rate if rate and pbar.total else 0)

        self.pb_label["text"] = f"{elapsed}  ({remaining} remaining)"
    
    def close(self):
        self.pwindow.destroy()
        self.pwindow.update()
    
    def on_stopping(self):
        self.stop_event.set()
        pass

    def set_label(self, text):
        self.pb_label["text"] = text