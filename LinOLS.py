import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
from tkinter import ttk
import struct
import numpy as np
import time
import os
import tempfile
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import sys
import re


class DifferencesDialog(tk.Toplevel):
    def __init__(self, parent, differences, text_widget):
        super().__init__(parent)
        self.title("Differences")
        self.parent = parent
        self.geometry("600x300")
        self.differences = differences
        self.text_widget = text_widget

        self.create_widgets()


    def create_widgets(self):
        self.treeview = ttk.Treeview(self)
        self.treeview["columns"] = ("current_value", "temp_value")
        self.treeview.heading("#0", text="Row")
        self.treeview.heading("current_value", text="Original Value")
        self.treeview.heading("temp_value", text="New Value")

        for index, difference in enumerate(self.differences):
            self.treeview.insert("", index, text=str(difference[2] + 1), values=(difference[0], difference[1]))

        self.treeview.bind("<Double-1>", self.on_double_click)
        self.treeview.pack(expand=True, fill=tk.BOTH)

    def on_double_click(self, event):
        item = self.treeview.selection()[0]
        row_index = int(self.treeview.item(item, "text"))
        col_index = 0
        self.text_widget.mark_set("insert", f"{row_index}.{col_index}")
        self.text_widget.see(f"{row_index}.{col_index}")
        self.text_widget.focus_set()
        LinOLS.sync_2d_to_text()



class HighlightText(tk.Text):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.original_values = {}
        self.tag_configure("changed_red", foreground="#ed7d80")
        self.tag_configure("changed_blue", foreground="#65a1e6")
        self.bind("<Key>", self.validate_input)
        self.bind("<FocusOut>", self.focus_out_handler)

    def validate_input(self, event):
        char = event.char

        if char and not (char.isdigit() or ('a' <= char <= 'f') or ('A' <= char <= 'F')):
            if event.keysym in ['BackSpace', 'space', 'Delete']:
                return
            elif event.keysym in ['Left', 'Right', 'Up', 'Down']:
                return "break"
            else:
                self.exit_text_widget(event)
                return "break"

    def focus_out_handler(self, event):
        try:
            focused_widget = self.focus_get()
            if not focused_widget or str(focused_widget).endswith("__tk__messagebox"):
                self.exit_text_widget(event)
        except Exception as e:
            print(f"An error occurred in focus_out_handler: {e}")

    def exit_text_widget(self, event):
        if event.keysym in ['Left', 'Right', 'Up', 'Down']:
            return
        self.master.focus_set()

    def set_original_values(self, row_index, values):
        self.original_values[row_index] = values

    def highlight_changed_value(self, row_index, col_index, current_value, original_value):
        start_index = f"{row_index + 1}.{col_index * 6}"
        end_index = f"{row_index + 1}.{col_index * 6 + 5}"

        if original_value < current_value:
            self.tag_add("changed_red", start_index, end_index)
            self.tag_remove("changed_blue", start_index, end_index)
        elif original_value > current_value:
            self.tag_remove("changed_red", start_index, end_index)
            self.tag_add("changed_blue", start_index, end_index)
        else:
            self.tag_remove("changed_red", start_index, end_index)
            self.tag_remove("changed_blue", start_index, end_index)

    def batch_highlight_changed_values(self, changes):
        if not self.original_values:
            return

        for current_value, original_value, row_index, col_index in changes:
            self.highlight_changed_value(row_index, col_index, current_value, original_value)


class LinOLS:
    def __init__(self, root):
        self.root = root
        self.arrow_keys_enabled = True
        self.check_auto_skip_id = None
        self.arrow_key_state = None
        self.root.title("LinOLS")
        self.file_path = ""
        self.current_offset = 0
        self.num_columns = 15
        self.display_mode = 'dec16_lh'
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        root.width = 1453
        root.height = 600

        x = (screen_width / 2) - (root.width / 2)
        y = (screen_height / 2) - (root.height / 2)
        root.geometry(f"{root.width}x{root.height}+{int(x)}+{int(y)}")

        self.theme = {
            'bg': '#333',
            'fg': 'white',
            'entry_bg': '#555',
            'entry_fg': 'white',
            'btn_bg': '#444',
            'btn_fg': 'white'
        }

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        tab1 = tk.Frame(self.notebook, bg=self.theme['bg'])
        self.notebook.add(tab1, text="Text")

        menu_bar = tk.Menu(tab1)
        root.config(menu=menu_bar)

        file_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open", command=self.open_file)
        file_menu.add_command(label="Save", command=self.save_file)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=root.destroy)

        options_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="Options", menu=options_menu)
        options_menu.add_command(label="Differences", command=self.compare)
        options_menu.add_command(label="Import file", command=self.import_file)

        info_menu = tk.Menu(menu_bar, tearoff=0)
        menu_bar.add_cascade(label="Info", menu=info_menu)
        info_menu.add_command(label="About", command=self.show_about_info)

        frame_tab1 = tk.Frame(tab1)
        frame_tab1.grid(row=0, column=0, padx=10, pady=10, sticky=tk.NSEW)

        self.text_widget = HighlightText(frame_tab1, wrap=tk.NONE, height=31, width=125, bg=self.theme['bg'], fg=self.theme['fg'], bd=0, highlightthickness=0)
        self.text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.text_widget.configure(insertbackground='white', font=("Inconsolata", 10))
        self.text_widget.configure(undo=True)

        scrollbar = tk.Scrollbar(frame_tab1, orient=tk.VERTICAL, command=self.text_widget.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.text_widget.config(yscrollcommand=scrollbar.set)

        tab1.grid_rowconfigure(0, weight=1)
        tab1.grid_columnconfigure(0, weight=1)

        display_mode_buttons_frame = tk.Frame(tab1)
        display_mode_buttons_frame.grid(row=1, column=0, columnspan=6, sticky=tk.W, padx=5)
        tk.Button(display_mode_buttons_frame, text="8-bit Hex", command=lambda: self.set_display_mode('hex8'), bg=self.theme['btn_bg'], fg=self.theme['btn_fg']).grid(
            row=2, column=0, sticky=tk.W)
        tk.Button(display_mode_buttons_frame, text="8-bit Dec", command=lambda: self.set_display_mode('dec8'), bg=self.theme['btn_bg'], fg=self.theme['btn_fg']).grid(
            row=2, column=1, sticky=tk.W)
        tk.Button(display_mode_buttons_frame, text="16-bit Dec (Low-High)",
                  command=lambda: self.set_display_mode('dec16_lh'), bg=self.theme['btn_bg'], fg=self.theme['btn_fg']).grid(row=2, column=2, sticky=tk.W)
        tk.Button(display_mode_buttons_frame, text="16-bit Dec (High-Low)",
                  command=lambda: self.set_display_mode('dec16_hl'), bg=self.theme['btn_bg'], fg=self.theme['btn_fg']).grid(row=2, column=3, sticky=tk.W)
        tk.Button(display_mode_buttons_frame, text="16-bit Hex", command=lambda: self.set_display_mode('hex16'), bg=self.theme['btn_bg'], fg=self.theme['btn_fg']).grid(
            row=2, column=4, sticky=tk.W)

        tk.Label(display_mode_buttons_frame, text="Number of Columns:", bg=self.theme['btn_bg'], fg=self.theme['btn_fg']).grid(row=2, column=5, padx=5, sticky=tk.E)
        self.column_entry = tk.Entry(display_mode_buttons_frame, width=2)
        self.column_entry.grid(row=2, column=6, sticky=tk.W)
        self.column_entry.insert(0, str(self.num_columns))

        self.column_entry.bind("<FocusOut>", lambda event: self.apply_columns_auto())

        root.bind('m', lambda event: self.adjust_columns(1))
        root.bind('w', lambda event: self.adjust_columns(-1))

        tk.Button(display_mode_buttons_frame, text="33%", command=lambda: self.skip_to_percentage(33), bg=self.theme['btn_bg'], fg=self.theme['btn_fg']).grid(row=2, column=7, sticky=tk.W, padx=1)
        tk.Button(display_mode_buttons_frame, text="66%", command=lambda: self.skip_to_percentage(66), bg=self.theme['btn_bg'], fg=self.theme['btn_fg']).grid(row=2,
                                                                                                             column=8,
                                                                                                             sticky=tk.W,
                                                                                                             padx=1)
        tk.Button(display_mode_buttons_frame, text="End", command=lambda: self.skip_to_percentage(100), bg=self.theme['btn_bg'], fg=self.theme['btn_fg']).grid(row=2,
                                                                                                             column=9,
                                                                                                             sticky=tk.W,
                                                                                                             padx=1)
        tk.Button(display_mode_buttons_frame, text="Copy", command=lambda: LinOLS.copy_values(None), bg=self.theme['btn_bg'], fg=self.theme['btn_fg']).grid(row=2, column=10, pady=0, sticky=tk.W, ipadx=10)
        tk.Button(display_mode_buttons_frame, text="Paste", command=lambda: LinOLS.paste_values(None), bg=self.theme['btn_bg'], fg=self.theme['btn_fg']).grid(row=2, column=11, pady=0, sticky=tk.W, ipadx=10)

        tk.Button(display_mode_buttons_frame, text="Undo", command=self.undo,
                  bg=self.theme['btn_bg'], fg=self.theme['btn_fg']).grid(row=2, column=12, pady=0, sticky=tk.W,
                                                                         ipadx=10)
        tk.Button(display_mode_buttons_frame, text="Redo", command=self.redo,
                  bg=self.theme['btn_bg'], fg=self.theme['btn_fg']).grid(row=2, column=13, pady=0, sticky=tk.W,
                                                                         ipadx=10)
        self.selected_count_label = tk.Button(display_mode_buttons_frame, text="Selected: 0", bg=self.theme['btn_bg'], fg=self.theme['btn_fg'])
        self.selected_count_label.grid(row=2, column=14, sticky=tk.W)

        display_mode_buttons_frame.config(bg=self.theme['bg'])

        self.apply_theme(self.theme)

        tab2 = tk.Frame(self.notebook, bg=self.theme['bg'])
        self.notebook.add(tab2, text="2D")

        self.canvas_line = tk.Canvas(tab2, bg="#333333", height=400, width=400, relief=tk.SOLID, bd=0, highlightthickness=0)
        self.canvas_line.grid(row=0, column=0, rowspan=1, padx=10, sticky=tk.NSEW)

        self.navigation_buttons_frame = tk.Frame(tab2, bg=self.theme['bg'])
        self.navigation_buttons_frame.grid(row=1, column=0, columnspan=6, pady=5, sticky=tk.W)
        self.button_previous = tk.Button(self.navigation_buttons_frame, text="Previous", command=self.navigate_previous,
                                         state=tk.DISABLED, bg=self.theme['btn_bg'], fg=self.theme['btn_fg'])
        self.button_previous.grid(row=0, column=0, padx=5)
        self.button_next = tk.Button(self.navigation_buttons_frame, text="Next", command=self.navigate_next,
                                     state=tk.DISABLED, bg=self.theme['btn_bg'], fg=self.theme['btn_fg'])
        self.button_next.grid(row=0, column=1, padx=5)

        self.load_and_update = tk.Button(self.navigation_buttons_frame, text="Load and Update", command=self.load_and_update, bg=self.theme['btn_bg'], fg=self.theme['btn_fg'])
        self.load_and_update.grid(row=0, column=2, padx=5)
        root.update()
        self.value_label = tk.Label(self.navigation_buttons_frame, text="", font=("Arial", 12), bg=self.theme['bg'])
        self.value_label.grid(row=0, column=3, padx=root.winfo_width() / 2)

        tab2.grid_rowconfigure(0, weight=1)
        tab2.grid_columnconfigure(0, weight=1)

        tab3 = tk.Frame(self.notebook, bg=self.theme['bg'])
        self.notebook.add(tab3, text="3D")

        self.boxes = tk.Frame(tab3, bg=self.theme['bg'])
        self.boxes.grid(row=0, column=0, padx=10, pady=10, sticky='nw')
        tab3.grid_columnconfigure(0, weight=1)

        self.main_frame = tk.Frame(self.boxes)
        self.main_frame.grid(row=1, column=1, padx=10, sticky='nw')

        self.x_frame = tk.Frame(self.boxes)
        self.x_frame.grid(row=0, column=1, padx=10, pady=8, sticky='nw')

        self.y_frame = tk.Frame(self.boxes)
        self.y_frame.grid(row=1, column=0, sticky='nw')

        self.right_frame = tk.Frame(tab3)
        self.right_frame.grid(row=0, column=2, padx=10, pady=10, sticky='nsew')
        tab3.grid_columnconfigure(0, weight=1)

        self.columns = 10
        self.rows = 10

        self.entry_x_widgets = []
        self.original_X = []
        row_x = []
        original_row_x = []
        for j in range(self.columns):
            entry = tk.Entry(self.x_frame, width=5, font=("Comfortaa", 10))
            entry.grid(row=0, column=j)
            entry.insert(tk.END, "00000")
            entry.bind('<KeyRelease>', lambda event, j=j: self.check_difference_x(event, j))
            entry.bind("<ButtonPress-1>", lambda event, j=j: self.start_interaction_x(event, j))
            entry.bind("<B1-Motion>", self.drag_to_select)
            entry.bind("<ButtonRelease-1>", self.end_interaction)
            row_x.append(entry)
            original_row_x.append("00000")
        self.entry_x_widgets.append(row_x)
        self.original_X.append(original_row_x)

        self.entry_widgets = []
        self.original = []
        for i in range(self.rows):
            row = []
            original_row = []
            for j in range(self.columns):
                entry = tk.Entry(self.main_frame, width=5, font=("Comfortaa", 10))
                entry.grid(row=i, column=j)
                entry.insert(tk.END, "00000")
                entry.bind('<KeyRelease>', lambda event, i=i, j=j: (self.check_difference(event, i, j), self.check_difference_3d(i, j)))
                entry.bind("<ButtonPress-1>", lambda event, i=i, j=j: (self.start_interaction(event, i, j), self.check_difference_3d(i, j)))
                entry.bind("<B1-Motion>", self.drag_to_select)
                entry.bind("<ButtonRelease-1>", self.end_interaction)
                row.append(entry)
                original_row.append("00000")
            self.entry_widgets.append(row)
            self.original.append(original_row)

        self.entry_y_widgets = []
        self.original_Y = []
        for i in range(self.rows):
            entry = tk.Entry(self.y_frame, width=5, font=("Comfortaa", 10))
            entry.grid(row=i, column=0)
            entry.insert(tk.END, "00000")
            entry.bind('<KeyRelease>', lambda event, i=i: self.check_difference_y(event, i))
            entry.bind("<ButtonPress-1>", lambda event, i=i: self.start_interaction_y(event, i))
            entry.bind("<B1-Motion>", self.drag_to_select)
            entry.bind("<ButtonRelease-1>", self.end_interaction)
            self.entry_y_widgets.append(entry)
            self.original_Y.append("00000")


        self.fig = plt.figure()
        self.ax = self.fig.add_subplot(111, projection='3d')
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.right_frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.canvas_widget.pack(fill="both", expand=True)

        self.start_x = None
        self.start_y = None
        self.end_x = None
        self.end_y = None
        self.selected_cells = set()

        buttons_frame = tk.Frame(tab3, bg=self.theme['bg'])
        buttons_frame.grid(row=1, column=0, columnspan=6, pady=5, sticky=tk.W)

        tk.Label(buttons_frame, text="Number of Rows:", bg=self.theme['btn_bg'], fg=self.theme['btn_fg']).grid(row=0, column=0, padx=5)
        self.rows_entry = tk.Entry(buttons_frame, width=5)
        self.rows_entry.insert(0, str(self.rows))
        self.rows_entry.grid(row=0, column=1, padx=5)

        tk.Label(buttons_frame, text="Number of Columns:", bg=self.theme['btn_bg'], fg=self.theme['btn_fg']).grid(row=0, column=2, padx=5)
        self.columns_entry = tk.Entry(buttons_frame, width=5)
        self.columns_entry.insert(0, str(self.columns))
        self.columns_entry.grid(row=0, column=3, padx=5)

        self.update_button = tk.Button(buttons_frame, text="Update Columns and Rows", command=self.update_columns_rows, bg=self.theme['btn_bg'], fg=self.theme['btn_fg'])
        self.update_button.grid(row=0, column=4, padx=5)

        self.update_3d_button = tk.Button(buttons_frame, text="Update 3D", command=self.update_3d_view, bg=self.theme['btn_bg'], fg=self.theme['btn_fg'])
        self.update_3d_button.grid(row=0, column=5, padx=5)

        self.paste_button = tk.Button(buttons_frame, text="Paste", command=self.paste_data, bg=self.theme['btn_bg'], fg=self.theme['btn_fg'])
        self.paste_button.grid(row=0, column=6, padx=5)

        self.paste_x_button = tk.Button(buttons_frame, text="Paste X Axis", command=self.paste_x_data, bg=self.theme['btn_bg'], fg=self.theme['btn_fg'])
        self.paste_x_button.grid(row=0, column=7, padx=5)

        self.paste_y_button = tk.Button(buttons_frame, text="Paste Y Axis", command=self.paste_y_data, bg=self.theme['btn_bg'], fg=self.theme['btn_fg'])
        self.paste_y_button.grid(row=0, column=8, padx=5)

        self.copy_map_values_button = tk.Button(buttons_frame, text="Copy Map Values", command=self.copy_map_values, bg=self.theme['btn_bg'], fg=self.theme['btn_fg'])
        self.copy_map_values_button.grid(row=0, column=9, padx=5)

        self.copy_x_axis_button = tk.Button(buttons_frame, text="Copy X Axis", command=self.copy_x_axis, bg=self.theme['btn_bg'], fg=self.theme['btn_fg'])
        self.copy_x_axis_button.grid(row=0, column=10, padx=5)

        self.copy_y_axis_button = tk.Button(buttons_frame, text="Copy Y Axis", command=self.copy_y_axis, bg=self.theme['btn_bg'], fg=self.theme['btn_fg'])
        self.copy_y_axis_button.grid(row=0, column=11, padx=5)

        self.copy_selected_button = tk.Button(buttons_frame, text="Copy Selected", command=self.copy_selected_cells, bg=self.theme['btn_bg'], fg=self.theme['btn_fg'])
        self.copy_selected_button.grid(row=0, column=12, padx=5)

        self.increase_button = tk.Button(buttons_frame, text="+", command=self.increase_selected_text, bg=self.theme['btn_bg'], fg=self.theme['btn_fg'])
        self.increase_button.grid(row=1, column=0)

        self.increase_entry = tk.Entry(buttons_frame, width=5)
        self.increase_entry.grid(row=1, column=1)

        self.per_button = tk.Button(buttons_frame, text="%", command=self.increase_selected_text_per, bg=self.theme['btn_bg'], fg=self.theme['btn_fg'])
        self.per_button.grid(row=1, column=2)

        self.per_entry = tk.Entry(buttons_frame, width=5)
        self.per_entry.grid(row=1, column=3)

        self.set_button = tk.Button(buttons_frame, text="=", command=self.set_text, bg=self.theme['btn_bg'], fg=self.theme['btn_fg'])
        self.set_button.grid(row=1, column=4, pady=5)

        self.set_entry = tk.Entry(buttons_frame, width=5)
        self.set_entry.grid(row=1, column=5, pady=5)

        self.label_diff_3d = tk.Label(buttons_frame, text="Difference: ", bg=self.theme['bg'], fg=self.theme['fg'])
        self.label_diff_3d.grid(row=1, column=6, columnspan=2)

        self.extrapolate_button = tk.Button(buttons_frame, text="Extrapolate", command=self.extrapolate_values,
                                            bg=self.theme['btn_bg'], fg=self.theme['btn_fg'])
        self.extrapolate_button.grid(row=1, column=8, padx=5)

        self.percent_entry = tk.Entry(buttons_frame, width=5)
        self.percent_entry.grid(row=1, column=9)

        tab3.grid_rowconfigure(0, weight=1)
        tab3.grid_columnconfigure(0, weight=1)

        self.clickable_line = self.canvas_line.create_line(0, 0, 0, 0, fill="#bd090e", width=1, tags="clickable_line")

        self.clicked_line = None

        self.notebook.bind("<Configure>", lambda event: self.update_2d_canvas_size())

        self.auto_skip_interval = 10
        self.auto_skip_running = False
        self.auto_skip_start_time = 0
        self.check_auto_skip_id = None

        self.auto_skip_interval_previous = 10
        self.auto_skip_running_previous = False
        self.auto_skip_start_time_previous = 0
        self.check_auto_skip_id_previous = None

        self.button_next.bind("<Button-1>", self.start_auto_skip)
        self.button_next.bind("<ButtonRelease-1>", self.stop_auto_skip)

        self.button_previous.bind("<Button-1>", self.start_auto_skip_previous)
        self.button_previous.bind("<ButtonRelease-1>", self.stop_auto_skip_previous)

        root.bind('<Left>', self.navigate_2d)
        root.bind('<Right>', self.navigate_2d)

        self.text_widget.bind('<KeyRelease>', self.check_value_changes)

        self.arrow_key_state = None

        root.bind('<Left>', lambda event: self.set_arrow_key_state(event, 'left'))
        root.bind('<Right>', lambda event: self.set_arrow_key_state(event, 'right'))
        root.bind('<KeyRelease-Left>', lambda event: self.set_arrow_key_state(event, None))
        root.bind('<KeyRelease-Right>', lambda event: self.set_arrow_key_state(event, None))

        self.root.after(50, lambda: self.update_on_arrow_key())

        root.bind('<i>', self.toggle_arrow_keys)

        self.update_2d_canvas_size()

        root.protocol("WM_DELETE_WINDOW", self.exit_application)

        self.notebook.bind("<Enter>", self.on_tab_enter)
        self.notebook.bind("<Leave>", self.on_tab_leave)

        self.text_widget.bind('<ButtonRelease-1>', self.show_selected_number)
        self.text_widget.bind('<Motion>', self.update_selected_count)

        self.tabs_widgets = []
        for index in range(len(self.notebook.tabs())):
            frame = self.notebook.nametowidget(self.notebook.tabs()[index])
            text_widget = frame.winfo_children()[0]
            self.tabs_widgets.append(text_widget)

    def show_selected_number(self, event):
        if self.text_widget.tag_ranges("sel"):
            selected_text = self.text_widget.get("sel.first", "sel.last")


    def update_selected_count(self, event):
        if self.text_widget.tag_ranges("sel"):
            selected_text = self.text_widget.get("sel.first", "sel.last")
        else:
            selected_text = ""
        selected_count = len(selected_text.split())
        self.selected_count_label.config(text=f"Selected: {selected_count}")

    def extrapolate_values(self):
        try:
            percentage = float(self.percent_entry.get())
            selected_numbers = []
            for i in range(self.rows):
                for j in range(self.columns):
                    entry = self.entry_widgets[i][j]
                    if entry.cget('bg') == 'lightblue':
                        selected_numbers.append(int(entry.get()))

            if not selected_numbers:
                print("No selected numbers")
                return

            highest_value = max(selected_numbers)
            for i in range(self.rows):
                for j in range(self.columns):
                    entry = self.entry_widgets[i][j]
                    if entry.cget('bg') == 'lightblue':
                        current_value = int(entry.get())
                        new_value = current_value + (highest_value * percentage / 100)
                        new_value_str = '{:05d}'.format(int(new_value))
                        entry.delete(0, tk.END)
                        entry.insert(tk.END, new_value_str)
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid percentage.")

        self.update_3d_view()

    def check_difference_3d(self, i, j):
        current_value = int(self.entry_widgets[i][j].get())
        original_value = int(self.original[i][j])

        difference = current_value - original_value
        self.label_diff_3d.config(text=f"Difference: {difference}")

    def import_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Binary Files", "*.bin"), ("All Files", "**")])
        if file_path:
            self.compare_files_import(file_path)

    def compare_files_import(self, file_path):
        second_file_values = {}

        with open(file_path, 'rb') as file:
            row_index = 0
            while True:
                chunk = file.read(self.num_columns * 2)
                if not chunk:
                    break
                if len(chunk) % 2 != 0:
                    additional_byte = file.read(1)
                    if not additional_byte:
                        break
                    chunk += additional_byte

                line = ' '.join(f"{value:05}" for value in struct.unpack('<' + 'H' * (len(chunk) // 2), chunk))
                second_file_values[row_index] = line.split()
                row_index += 1

        self.text_widget.delete('1.0', tk.END)
        for row_index, values in second_file_values.items():
            self.text_widget.insert(tk.END, ' '.join(values) + '\n')

        differences = []
        for row_index, values in second_file_values.items():
            original_values = self.text_widget.original_values.get(row_index)
            if original_values:
                for col_index, (original_value, current_value) in enumerate(zip(original_values, values)):
                    if original_value != current_value:
                        differences.append((current_value, original_value, row_index, col_index))
        if differences:
            self.text_widget.batch_highlight_changed_values(differences)

    def compare(self):
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(self.text_widget.get(1.0, tk.END).encode())

        try:
            self.compare_files(temp_file.name)
        finally:
            os.unlink(temp_file.name)

    def compare_files(self, temp_file_path):
        temp_file_values = {}
        if temp_file_path:
            with open(temp_file_path, 'r') as temp_file:
                row_index = 0
                for line in temp_file:
                    values = line.strip().split()
                    temp_file_values[row_index] = values
                    row_index += 1
        else:
            messagebox.showerror('Error', 'File is not opened!')

        current_file_values = {}
        if self.file_path:
            with open(self.file_path, 'rb') as file:
                row_index = 0
                while True:
                    chunk = file.read(self.num_columns * 2)
                    if not chunk:
                        break
                    if len(chunk) % 2 != 0:
                        additional_byte = file.read(1)
                        if not additional_byte:
                            break
                        chunk += additional_byte

                    line_values = struct.unpack('<' + 'H' * (len(chunk) // 2), chunk)
                    current_file_values[row_index] = [f"{value:05}" for value in line_values]
                    row_index += 1

            differences = []
            for row_index, temp_values in temp_file_values.items():
                current_values = current_file_values.get(row_index, [])
                for col_index, (temp_value, current_value) in enumerate(zip(temp_values, current_values)):
                    if temp_value != current_value:
                        differences.append((current_value, temp_value, row_index, col_index))

            if differences:
                self.show_differences_dialog(differences)
            else:
                messagebox.showinfo("No Differences", "No differences found.")
        else:
            messagebox.showerror('Error', 'File is not opened!')

    def show_differences_dialog(self, differences):
        dialog = DifferencesDialog(self.root, differences, self.text_widget)
        dialog.transient(self.root)
        dialog.grab_set()
        self.root.wait_window(dialog)

    def on_tab_enter(self, event):
        current_tab_index = self.notebook.index(self.notebook.select())
        if current_tab_index < len(self.notebook.tabs()):
            self.tabs_widgets[current_tab_index].focus_set()

    def on_tab_leave(self, event):
        current_tab_index = self.notebook.index(self.notebook.select())
        if current_tab_index < len(self.notebook.tabs()):
            self.tabs_widgets[current_tab_index].focus_set()

    def exit_application(self):
        sys.exit()

    def copy_selected_cells(self):
        selected_content = ""
        for i in range(self.rows):
            row_content = ""
            for j in range(self.columns):
                entry = self.entry_widgets[i][j]
                if entry.cget('bg') == 'lightblue':
                    row_content += entry.get() + "\t"
            if row_content:
                selected_content += row_content.strip() + "\n"
        selected_content = selected_content.strip()
        self.root.clipboard_clear()
        self.root.clipboard_append(selected_content)
        self.root.update()

    def start_interaction(self, event, i, j):
        x, y = event.x_root, event.y_root
        self.start_x = x
        self.start_y = y
        self.end_x = x
        self.end_y = y
        self.selected_cells = {(i, j)}
        self.toggle_selection(i, j)
        self.highlight_cells()

    def start_interaction_x(self, event, j):
        x, y = event.x_root, event.y_root
        self.start_x = x
        self.start_y = y
        self.end_x = x
        self.end_y = y
        self.selected_cells = {(None, j)}
        self.highlight_cells()

    def start_interaction_y(self, event, i):
        x, y = event.x_root, event.y_root
        self.start_x = x
        self.start_y = y
        self.end_x = x
        self.end_y = y
        self.selected_cells = {(i, None)}
        self.highlight_cells()

    def end_interaction(self, event):
        self.start_x = None
        self.start_y = None
        self.end_x = None
        self.end_y = None

    def drag_to_select(self, event):
        self.end_x = event.x_root
        self.end_y = event.y_root
        self.highlight_cells()

        if self.start_x == self.end_x and self.start_y == self.end_y:
            i, j = self.get_cell_index(self.start_x, self.start_y)
            if i is not None and j is not None:
                self.toggle_selection(i, j)

    def highlight_cells(self):
        if self.start_x is not None and self.start_y is not None:
            start_i, start_j = self.get_cell_index(self.start_x, self.start_y)
            if start_i is not None and start_j is not None:
                end_i, end_j = self.get_cell_index(self.end_x, self.end_y)
                if end_i is not None and end_j is not None:
                    min_i = min(start_i, end_i)
                    max_i = max(start_i, end_i)
                    min_j = min(start_j, end_j)
                    max_j = max(start_j, end_j)

                    for i in range(self.rows):
                        for j in range(self.columns):
                            entry = self.entry_widgets[i][j]
                            entry_x = entry.winfo_rootx()
                            entry_y = entry.winfo_rooty()
                            entry_width = entry.winfo_width()
                            entry_height = entry.winfo_height()

                            if min_i <= i <= max_i and min_j <= j <= max_j:
                                if (i, j) not in self.selected_cells:
                                    entry.config(bg="lightblue")
                            else:
                                if (i, j) in self.selected_cells:
                                    entry.config(bg="lightblue")
                                else:
                                    entry.config(bg="white")

    def toggle_selection(self, i, j):
        if (i, j) in self.selected_cells:
            self.selected_cells.remove((i, j))
            self.entry_widgets[i][j].config(bg="white")
        else:
            self.selected_cells.add((i, j))
            self.entry_widgets[i][j].config(bg="lightblue")

    def get_cell_index(self, x, y):
        for i in range(self.rows):
            for j in range(self.columns):
                entry = self.entry_widgets[i][j]
                entry_x = entry.winfo_rootx()
                entry_y = entry.winfo_rooty()
                entry_width = entry.winfo_width()
                entry_height = entry.winfo_height()
                if entry_x <= x <= entry_x + entry_width and entry_y <= y <= entry_y + entry_height:
                    return i, j
        return None, None

    def increase_selected_text(self):
        try:
            increase_value = int(self.increase_entry.get())
            for i in range(self.rows):
                for j in range(self.columns):
                    entry = self.entry_widgets[i][j]
                    if entry.cget('bg') == 'lightblue':
                        current_value = int(entry.get())
                        new_value = current_value + increase_value
                        new_value_str = '{:05d}'.format(new_value)
                        entry.delete(0, tk.END)
                        entry.insert(tk.END, new_value_str)
                        self.check_difference(event=None, i=i, j=j)
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid number.")

        self.update_3d_view()

    def increase_selected_text_per(self):
        try:
            percentage_increase = float(self.per_entry.get()) / 100.0
            for i in range(self.rows):
                for j in range(self.columns):
                    entry = self.entry_widgets[i][j]
                    if entry.cget('bg') == 'lightblue':
                        current_value = int(entry.get())
                        increase_value = int(current_value * percentage_increase)
                        new_value = current_value + increase_value
                        new_value_str = '{:05d}'.format(new_value)
                        entry.delete(0, tk.END)
                        entry.insert(tk.END, new_value_str)
                        self.check_difference(event=None, i=i, j=j)
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid percentage.")
        self.update_3d_view()

    def set_text(self):
        try:
            set_text = int(self.set_entry.get())
            for i in range(self.rows):
                for j in range(self.columns):
                    entry = self.entry_widgets[i][j]
                    if entry.cget('bg') == 'lightblue':
                        new_value = set_text
                        new_value_str = '{:05d}'.format(new_value)
                        entry.delete(0, tk.END)
                        entry.insert(tk.END, new_value_str)
                        self.check_difference(event=None, i=i, j=j)
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid number.")
        self.update_3d_view()

    def update_columns_rows(self):
        try:
            new_columns = int(self.columns_entry.get())
            new_rows = int(self.rows_entry.get())
            self.resize_grid(new_columns, new_rows)
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers.")

    def resize_grid(self, new_columns, new_rows):
        if new_rows > len(self.entry_y_widgets):
            for i in range(len(self.entry_y_widgets), new_rows):
                entry = tk.Entry(self.y_frame, width=5, font=("Comfortaa", 10))
                entry.grid(row=i, column=0)
                entry.insert(tk.END, "00000")
                entry.bind('<KeyRelease>', lambda event, i=i: self.check_difference_y(event, i))
                entry.bind("<B1-Motion>", self.drag_to_select)
                entry.bind("<ButtonRelease-1>", self.end_interaction)
                self.entry_y_widgets.append(entry)
                self.original_Y.append("00000")
        elif new_rows < len(self.entry_y_widgets):
            for i in range(len(self.entry_y_widgets) - 1, new_rows - 1, -1):
                entry = self.entry_y_widgets.pop()
                entry.destroy()
                self.original_Y.pop()

        for i in range(new_rows):
            entry = self.entry_y_widgets[i]
            entry.grid(row=i, column=0)

        if new_columns > len(self.entry_x_widgets[0]):
            for j in range(len(self.entry_x_widgets[0]), new_columns):
                entry = tk.Entry(self.x_frame, width=5, font=("Comfortaa", 10))
                entry.grid(row=0, column=j)
                entry.insert(tk.END, "00000")
                entry.bind('<KeyRelease>', lambda event, j=j: self.check_difference_x(event, j))
                entry.bind("<ButtonPress-1>", lambda event, i=i: self.start_interaction_y(event, i))
                entry.bind("<B1-Motion>", self.drag_to_select)
                entry.bind("<ButtonRelease-1>", self.end_interaction)
                self.entry_x_widgets[0].append(entry)
                self.original_X[0].append("00000")
        elif new_columns < len(self.entry_x_widgets[0]):
            for j in range(len(self.entry_x_widgets[0]) - 1, new_columns - 1, -1):
                entry = self.entry_x_widgets[0].pop()
                entry.destroy()
                self.original_X[0].pop()

        if new_rows > len(self.entry_widgets):
            for i in range(len(self.entry_widgets), new_rows):
                row = []
                original_row = []
                for j in range(new_columns):
                    entry = tk.Entry(self.main_frame, width=5, font=("Comfortaa", 10))
                    entry.grid(row=i, column=j)
                    entry.insert(tk.END, "00000")
                    entry.bind('<KeyRelease>', lambda event, i=i, j=j: self.check_difference(event, i, j))
                    entry.bind("<ButtonPress-1>", lambda event, i=i, j=j: (
                    self.start_interaction(event, i, j), self.check_difference_3d(i, j)))
                    entry.bind("<B1-Motion>", self.drag_to_select)
                    entry.bind("<ButtonRelease-1>", self.end_interaction)
                    row.append(entry)
                    original_row.append("00000")
                self.entry_widgets.append(row)
                self.original.append(original_row)
        elif new_rows < len(self.entry_widgets):
            for i in range(len(self.entry_widgets) - 1, new_rows - 1, -1):
                row = self.entry_widgets.pop()
                for entry in row:
                    entry.destroy()
                self.original.pop()

        for i in range(len(self.entry_widgets)):
            row = self.entry_widgets[i]
            original_row = self.original[i]
            for j in range(len(row), new_columns):
                entry = tk.Entry(self.main_frame, width=5, font=("Comfortaa", 10))
                entry.grid(row=i, column=j)
                entry.insert(tk.END, "00000")
                entry.bind('<KeyRelease>', lambda event, i=i, j=j: self.check_difference(event, i, j))
                entry.bind("<ButtonPress-1>", lambda event, i=i, j=j: (self.start_interaction(event, i, j), self.check_difference_3d(i, j)))
                entry.bind("<B1-Motion>", self.drag_to_select)
                entry.bind("<ButtonRelease-1>", self.end_interaction)
                row.append(entry)
                original_row.append("00000")
            for j in range(len(row) - 1, new_columns - 1, -1):
                entry = row.pop()
                entry.destroy()
                original_row.pop()

        self.columns = new_columns
        self.rows = new_rows

    def update_3d_view(self):
        try:
            x_default = all(entry.get() == "00000" for entry in self.entry_x_widgets[0])
            y_default = all(entry.get() == "00000" for entry in self.entry_y_widgets)

            if x_default and y_default:
                x = np.arange(self.columns)
                y = np.arange(self.rows)
                x, y = np.meshgrid(x, y)

                values = np.zeros((self.rows, self.columns))
                for i in range(self.rows):
                    for j in range(self.columns):
                        value = float(self.entry_widgets[i][j].get())
                        values[i][j] = value

                self.ax.clear()
                surf = self.ax.plot_surface(x, y, values, cmap='viridis', edgecolor='none')
                self.ax.set_xlabel('X')
                self.ax.set_ylabel('Y')
                self.ax.set_zlabel('Value')

                self.ax.set_xticks([])
                self.ax.set_yticks([])

                self.canvas.draw()
            else:
                x = np.arange(self.columns)
                y = np.arange(self.rows)
                x, y = np.meshgrid(x, y)

                values = np.zeros((self.rows, self.columns))
                for i in range(self.rows):
                    for j in range(self.columns):
                        value = float(self.entry_widgets[i][j].get())
                        values[i][j] = value

                self.ax.clear()
                self.ax.plot_surface(x, y, values, cmap='viridis')
                self.ax.set_xlabel('X')
                self.ax.set_ylabel('Y')
                self.ax.set_zlabel('Value')

                self.ax.set_xticks(np.arange(0, self.columns, 1))
                self.ax.set_yticks(np.arange(0, self.rows, 1))

                self.canvas.draw()
        except ValueError:
            messagebox.showerror("Error", "Please enter valid numbers.")

    def paste_data(self):
        try:
            data = self.root.clipboard_get()
            lines = data.strip().split('\n')
            num_rows = len(lines)
            num_columns = max(len(line.strip().split('\t')) for line in lines)

            self.rows_entry.delete(0, tk.END)
            self.rows_entry.insert(0, str(num_rows))
            self.columns_entry.delete(0, tk.END)
            self.columns_entry.insert(0, str(num_columns))

            self.clear_highlighting()

            self.resize_grid(num_columns, num_rows)

            for i, line in enumerate(lines):
                numbers = line.strip().split('\t')
                for j, num in enumerate(numbers):
                    if i < self.rows and j < self.columns:
                        new_value = '{:05d}'.format(int(num))
                        self.entry_widgets[i][j].delete(0, tk.END)
                        self.entry_widgets[i][j].insert(0, new_value)
                        self.original[i][j] = new_value
                        self.entry_widgets[i][j].config(fg="black")

            last_row_values = [entry.get() for entry in self.entry_widgets[-1]]
            if not any(last_row_values) and self.rows > 1:
                last_row = self.entry_widgets.pop()
                last_row_original = self.original.pop()
                for entry in last_row:
                    entry.destroy()
                last_row_original.clear()
                num_rows -= 1
                self.rows_entry.delete(0, tk.END)
                self.rows_entry.insert(0, str(num_rows))

        except tk.TclError:
            messagebox.showerror("Error", "Clipboard operation failed. Please try again.")

        self.update_3d_view()

    def paste_x_data(self):
        try:
            data = self.root.clipboard_get()
            numbers = data.strip().split('\t')

            self.clear_highlighting()

            for j, num in enumerate(numbers):
                if j < self.columns:
                    new_value = '{:05d}'.format(int(num))
                    self.entry_x_widgets[0][j].delete(0, tk.END)
                    self.entry_x_widgets[0][j].insert(0, new_value)
                    self.original_X[0][j] = new_value

        except tk.TclError:
            messagebox.showerror("Error", "Clipboard operation failed. Please try again.")

        self.update_3d_view()

    def paste_y_data(self):
        try:
            data = self.root.clipboard_get()
            numbers = re.split(r'\s+', data.strip())

            self.clear_highlighting()

            for i, num in enumerate(numbers):
                if i < len(self.entry_y_widgets):
                    try:
                        new_value = '{:05d}'.format(int(num))
                        print(f"Inserting value '{new_value}' into entry widget {i}")
                        self.entry_y_widgets[i].delete(0, tk.END)
                        self.entry_y_widgets[i].insert(0, new_value)
                        if i < len(self.original_Y):
                            self.original_Y[i] = new_value
                    except ValueError:
                        messagebox.showerror("Error", f"Invalid value '{num}' found in clipboard data.")
                        continue
                else:
                    messagebox.showwarning("Warning", "More data in clipboard than available entry widgets.")

            self.update_3d_view()

        except tk.TclError:
            messagebox.showerror("Error", "Clipboard operation failed. Please try again.")

    def clear_highlighting(self):
        for i in range(self.rows):
            for j in range(self.columns):
                entry = self.entry_widgets[i][j]
                entry.config(bg="white")

    def check_difference(self, event, i, j):
        entry = self.entry_widgets[i][j]
        original_value = int(self.original[i][j])
        current_value = int(entry.get())
        if current_value > original_value:
            entry.config(fg="red")
        elif current_value < original_value:
            entry.config(fg="blue")
        else:
            entry.config(fg="black")

        if event is None:
            entry.config(bg="white")

    def check_difference_x(self, event, j):
        entry = self.entry_x_widgets[0][j]
        original_value = int(self.original_X[0][j])
        current_value = int(entry.get())
        if current_value > original_value:
            entry.config(fg="red")
        elif current_value < original_value:
            entry.config(fg="blue")
        else:
            entry.config(fg="black")

    def check_difference_y(self, event, i):
        entry = self.entry_y_widgets[i]
        original_value = int(self.original_Y[i])
        current_value = int(entry.get())
        if current_value > original_value:
            entry.config(fg="red")
        elif current_value < original_value:
            entry.config(fg="blue")
        else:
            entry.config(fg="black")

    def copy_map_values(self):
        map_values = ""
        for i in range(self.rows):
            for j in range(self.columns):
                map_values += self.entry_widgets[i][j].get() + "\t"
            map_values += "\n"
        self.root.clipboard_clear()
        self.root.clipboard_append(map_values)

    def copy_x_axis(self):
        x_axis_values = "\t".join(entry.get() for entry in self.entry_x_widgets[0])
        self.root.clipboard_clear()
        self.root.clipboard_append(x_axis_values)

    def copy_y_axis(self):
        y_axis_values = "\n".join(entry.get() for entry in self.entry_y_widgets)
        self.root.clipboard_clear()
        self.root.clipboard_append(y_axis_values)

    def toggle_arrow_keys(self, event):
        if event.char.lower() == 'i':
            if self.arrow_keys_enabled:
                self.root.unbind('<Left>')
                self.root.unbind('<Right>')
            else:
                self.root.bind('<Left>', self.navigate_2d_left)
                self.root.bind('<Right>', self.navigate_2d_right)

            self.arrow_keys_enabled = not self.arrow_keys_enabled


    def set_arrow_key_state(self, event, state):
        self.arrow_key_state = state

    def update_on_arrow_key(self):
        if self.arrow_key_state in ['left', 'right']:
            if self.arrow_key_state == 'left':
                self.navigate_2d_left(None)
            elif self.arrow_key_state == 'right':
                self.navigate_2d_right(None)

        self.root.after(50, self.update_on_arrow_key)

    def navigate_2d_left(self, event):
        if self.display_mode in ['hex16', 'dec16_lh', 'dec16_hl']:
            total_columns = self.num_columns * 16
            self.current_offset = max(0, self.current_offset - 2)
            self.handle_navigation_and_highlight()

    def navigate_2d_right(self, event):
        with open(self.file_path, 'rb') as file:
            file.seek(self.current_offset + 2)
            data = file.read(2)

        if data:
            self.current_offset += 2
            self.handle_navigation_and_highlight()

    def open_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Binary Files", "*.bin"), ("All Files", "**")])
        if file_path:
            self.file_path = file_path
            self.current_offset = 0
            self.display_file()
            self.display_line_plot()
            self.update_navigation_buttons()

    def show_about_info(self):
        about_text = "LinOLS\nCreated by: Blackdown124\nVersion: 1.0"
        messagebox.showinfo("About", about_text)

    def display_file(self):
        self.text_widget.delete(1.0, tk.END)
        self.original_values = {}
        with open(self.file_path, 'rb') as file:
            row_index = 0
            while True:
                chunk = file.read(self.num_columns * 2)
                if not chunk:
                    break
                if len(chunk) % 2 != 0:
                    additional_byte = file.read(1)
                    if not additional_byte:
                        break
                    chunk += additional_byte

                if self.display_mode == 'hex8':
                    line = ' '.join(f"{byte:02X}" for byte in chunk)
                elif self.display_mode == 'dec8':
                    line = ' '.join(f"{byte:03}" for byte in chunk)
                elif self.display_mode == 'hex16':
                    line = ' '.join(f"{value:04X}" for value in struct.unpack('<' + 'H' * (len(chunk) // 2), chunk))
                elif self.display_mode == 'dec16_lh':
                    values = struct.unpack('<' + 'H' * (len(chunk) // 2), chunk)
                    line = ' '.join(f"{value:05}" for value in values)
                elif self.display_mode == 'dec16_hl':
                    values = struct.unpack('>' + 'H' * (len(chunk) // 2), chunk)
                    line = ' '.join(f"{value:05}" for value in values)
                else:
                    messagebox.showerror("Error", "Invalid display mode.")
                    return

                self.original_values[row_index] = line.split()
                self.text_widget.insert(tk.END, f"{line.ljust(6 * self.num_columns)}\n")
                row_index += 1

        self.total_rows = row_index

        for row_index, values in self.original_values.items():
            self.text_widget.set_original_values(row_index, values)

    def set_display_mode(self, mode):
        if self.file_path and self.is_unsaved_changes():
            response = messagebox.askyesnocancel("Unsaved Changes",
                                                 "Do you want to save the file before changing the display mode?")

            if response is True:
                self.save_file()
                self.display_line_plot()
            elif response is False:
                self.display_mode = mode
                self.display_file()
                self.display_line_plot()
        else:
            self.display_mode = mode
            self.display_file()

    def is_unsaved_changes(self):
        return self.text_widget.get(1.0, tk.END) != self.get_original_content()

    def get_original_content(self):
        original_content = ""
        for row_index, values in self.original_values.items():
            original_content += f"{(' '.join(values)).ljust(6 * self.num_columns)}\n"
        return original_content

    def check_value_changes(self, event):
        first_visible_row = int(self.text_widget.yview()[0] * self.total_rows)
        last_visible_row = int(self.text_widget.yview()[1] * self.total_rows)

        total_columns_text_view = 0

        if self.total_rows > 0 and 0 in self.text_widget.original_values:
            total_columns_text_view = len(self.text_widget.original_values[0])

        for row_index in range(first_visible_row, last_visible_row + 1):
            changes = []
            for col_index in range(total_columns_text_view):
                try:
                    current_value = int(self.text_widget.get(f"{row_index + 1}.{col_index * 6}",
                                                             f"{row_index + 1}.{col_index * 6 + 5}").strip())
                    original_value = int(self.text_widget.original_values[row_index][col_index])
                    changes.append((current_value, original_value, row_index, col_index))
                except (IndexError, ValueError):
                    pass

            self.text_widget.batch_highlight_changed_values(changes)


    def update_color(self, start_index, end_index, color):
        self.text_widget.tag_remove("changed", start_index, end_index)
        self.text_widget.tag_add("changed", start_index, end_index)
        self.text_widget.tag_configure("changed", foreground=color)
        self.text_widget.update_idletasks()

    def apply_columns(self):
        try:
            new_columns = int(self.column_entry.get())
            if new_columns > 0:
                self.num_columns = new_columns
                self.update_2d_canvas_size()
                self.display_file()
                self.display_line_plot()
                self.update_navigation_buttons()
            else:
                raise ValueError("Number of columns should be a positive integer.")
        except ValueError as e:
            messagebox.showerror("Error", str(e))

    def apply_columns_auto(self):
        try:
            new_columns = int(self.column_entry.get())
            if new_columns > 0:
                self.num_columns = new_columns
                self.display_file()
                self.display_line_plot()
                self.update_navigation_buttons()
            else:
                raise ValueError("Number of columns should be a positive integer.")

        except ValueError as e:
            messagebox.showerror("Error", str(e))

    def adjust_columns(self, delta):
        try:
            new_columns = self.num_columns + delta
            if new_columns > 0:
                self.num_columns = new_columns
                self.column_entry.delete(0, tk.END)
                self.column_entry.insert(0, str(self.num_columns))
                self.display_file()
                self.display_line_plot()
                self.update_navigation_buttons()
            else:
                raise ValueError("Number of columns should be a positive integer.")
        except ValueError as e:
            messagebox.showerror("Error", str(e))

    def save_file(self, file_name=None):
        if not self.file_path:
            messagebox.showwarning("Warning", "No file is currently open. Please open a file first.")
            return

        manufacturer = simpledialog.askstring("Input", "Enter Manufacturer:")
        model = simpledialog.askstring("Input", "Enter Model:")
        modification = simpledialog.askstring("Input", "Enter Modification:")

        if not (manufacturer and model and modification):
            messagebox.showwarning("Warning", "Manufacturer, Model, and Modification are required.")
            return

        if not file_name:
            file_name = f"LinOLS_{manufacturer}_{model}_{modification}.bin"

        try:
            initial_dir = os.path.expanduser('~')
            file_path = filedialog.asksaveasfilename(initialdir=initial_dir, defaultextension=".bin",
                                                     filetypes=[("Binary Files", "*.bin")],
                                                     initialfile=file_name)

            if not file_path:
                messagebox.showinfo("Info", "File save canceled.")
                return

            with open(file_path, 'wb') as file:
                file.write(
                    b''.join([struct.pack('<H', int(value)) for value in self.text_widget.get(1.0, tk.END).split()]))

            messagebox.showinfo("Success", f"File saved successfully at {file_path}.")
        except Exception as e:
            messagebox.showerror("Error", f"Error saving file: {e}")

    def navigate_previous(self):
        while True:
            self.current_offset = max(0, self.current_offset - self.num_columns * 16 * 2)
            self.display_line_plot()
            if not self.check_all_zero_values():
                break
        self.update_navigation_buttons()

    def navigate_next(self):
        while True:
            with open(self.file_path, 'rb') as file:
                file.seek(self.current_offset + self.num_columns * 16 * 2)
                data = file.read(self.num_columns * 16 * 2)

            if data or self.current_offset == 0:
                self.current_offset += self.num_columns * 16 * 2
                self.display_line_plot()
                if not self.check_all_zero_values():
                    break
            else:
                break
        self.update_navigation_buttons()

    def check_all_zero_values(self):
        with open(self.file_path, 'rb') as file:
            file.seek(self.current_offset)
            data = file.read(self.num_columns * 16 * 2)

        values = struct.unpack('<' + 'H' * (len(data) // 2), data)
        return all(value == 0 for value in values)

    def update_2d_canvas_size(self):
        canvas_width = self.canvas_line.master.winfo_width()
        canvas_height = self.canvas_line.master.winfo_height()
        self.canvas_line.config(width=canvas_width, height=canvas_height)
        self.canvas_line.coords(self.clickable_line, 0, 0, 0, canvas_height)
        self.display_line_plot()

    def display_line_plot(self):
        canvas_width = self.notebook.winfo_width() - 70
        canvas_height = self.notebook.winfo_height() - 70

        total_columns = canvas_width // 20

        if not self.file_path:
            return

        with open(self.file_path, 'rb') as file:
            file.seek(self.current_offset)
            data = file.read(total_columns * 16 * 2)

        if data:
            if self.display_mode == 'dec16_lh':
                numbers = struct.unpack('<' + 'H' * (len(data) // 2), data)
            elif self.display_mode == 'dec16_hl':
                numbers = struct.unpack('>' + 'H' * (len(data) // 2), data)
            else:
                return

            x_values = np.arange(len(numbers))
            y_values = np.array(numbers)
            y_scaled = canvas_height * (y_values / max(y_values))

            self.canvas_line.delete("line")

            for i in range(len(x_values) - 1):
                x1 = i * (canvas_width / len(x_values))
                y1 = canvas_height - y_scaled[i]
                x2 = (i + 1) * (canvas_width / len(x_values))
                y2 = canvas_height - y_scaled[i + 1]

                self.canvas_line.create_line(x1, y1, x2, y2, fill="#bababa", tags="line")

    def update_navigation_buttons(self):
        with open(self.file_path, 'rb') as file:
            file.seek(self.current_offset + self.num_columns * 16 * 2)
            data = file.read(self.num_columns * 16 * 2)

        self.button_previous["state"] = tk.NORMAL if self.current_offset > 0 else tk.DISABLED
        self.button_next["state"] = tk.NORMAL if data else tk.DISABLED

    def highlight_clicked_value(self, value_index):
        content = self.text_widget.get(1.0, tk.END)
        lines = content.split("\n")

        total_columns_text_view = len(lines[0].split())

        row_index = value_index // total_columns_text_view
        column_index = value_index % total_columns_text_view

        if 0 <= row_index < len(lines):
            current_value = lines[row_index].strip().split()[column_index]

            start_index = f"{row_index + 1}.{column_index * 6}"
            end_index = f"{row_index + 1}.{column_index * 6 + 5}"

            if f"{start_index}-{end_index}" not in self.text_widget.tag_ranges("highlight"):
                prev_start_index = f"{row_index + 1}.{column_index * 6}"
                prev_end_index = f"{row_index + 1}.{column_index * 6 + 5}"

                prev_highlighted_value = self.text_widget.get(prev_start_index, prev_end_index).strip()

                if prev_highlighted_value != current_value:
                    self.text_widget.tag_remove("highlight", "1.0", tk.END)

                self.text_widget.tag_add("highlight", start_index, end_index)
                self.text_widget.tag_configure("highlight", background="gold2")

                self.text_widget.see(start_index)

    def reset_highlight(self):
        self.canvas_line.delete("clicked_line")
        self.text_widget.tag_remove("highlight", "1.0", tk.END)
        self.update_highlight()

    def update_highlight(self):
        total_columns = self.num_columns * 16
        value_index = self.current_offset // 2
        self.highlight_clicked_value(value_index)

    def start_auto_skip_previous(self, event):
        self.auto_skip_start_time_previous = time.time()
        self.auto_skip_running_previous = True
        self.check_auto_skip_previous()

    def stop_auto_skip_previous(self, event):
        self.auto_skip_running_previous = False
        self.root.after_cancel(self.check_auto_skip_id_previous)
        self.check_auto_skip_id_previous = None

    def check_auto_skip_previous(self):
        elapsed_time = time.time() - self.auto_skip_start_time_previous
        if elapsed_time >= 0.5 and self.auto_skip_running_previous:
            self.navigate_previous()
            if self.auto_skip_running_previous:
                self.check_auto_skip_id_previous = self.root.after(self.auto_skip_interval,
                                                                   self.check_auto_skip_previous)
        else:
            if self.auto_skip_running_previous:
                self.check_auto_skip_id_previous = self.root.after(20, self.check_auto_skip_previous)

    def start_auto_skip(self, event):
        self.auto_skip_start_time = time.time()
        self.auto_skip_running = True
        self.check_auto_skip()

    def stop_auto_skip(self, event):
        self.auto_skip_running = False
        self.root.after_cancel(self.check_auto_skip_id)
        self.check_auto_skip_id = None

    def check_auto_skip(self):
        elapsed_time = time.time() - self.auto_skip_start_time
        if elapsed_time >= 0.5 and self.auto_skip_running:
            with open(self.file_path, 'rb') as file:
                file_size = os.path.getsize(self.file_path)
                next_offset = self.current_offset + self.num_columns * 16 * 2
                while next_offset >= file_size:
                    next_offset -= self.num_columns * 16 * 2
                    self.auto_skip_running = False
                    break

                self.current_offset = next_offset
                self.display_line_plot()
                self.update_navigation_buttons()

            if self.auto_skip_running:
                self.check_auto_skip_id = self.root.after(self.auto_skip_interval, self.check_auto_skip)
        else:
            if self.auto_skip_running:
                self.check_auto_skip_id = self.root.after(20, self.check_auto_skip)

    def copy_values(self, event):
        selected_text = self.text_widget.selection_get()
        if not selected_text:
            messagebox.showwarning("Nothing Selected", "No values are selected to copy.")
            return

        selected_values = selected_text.strip().split()

        num_rows = len(selected_values) // self.num_columns
        if len(selected_values) % self.num_columns != 0:
            num_rows += 1

        copied_content = ""
        for i in range(num_rows):
            start_index = i * self.num_columns
            end_index = min((i + 1) * self.num_columns, len(selected_values))
            row_values = selected_values[start_index:end_index]
            copied_content += "\t".join(row_values) + "\n"

        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(copied_content)
        except Exception as e:
            messagebox.showerror("Copy Error", f"An error occurred while copying: {e}")

    def paste_values(self, event):
        selected_text = self.root.clipboard_get()
        cleaned_values = selected_text.strip().split()

        cursor_index = self.text_widget.index(tk.INSERT)
        cursor_row, cursor_col = map(int, cursor_index.split('.'))

        current_content = self.text_widget.get(1.0, tk.END)
        current_lines = current_content.strip().split('\n')

        row_index = cursor_row - 1
        col_index = cursor_col // 6

        differences = []

        for value in cleaned_values:
            if row_index >= len(current_lines):
                break

            current_line = current_lines[row_index]
            values = current_line.split()

            if col_index >= len(values):
                row_index += 1
                col_index = 0
                if row_index >= len(current_lines):
                    break
                current_line = current_lines[row_index]
                values = current_line.split()

            if values[col_index] != value:
                differences.append((values[col_index], value, row_index, col_index))

            values[col_index] = value

            current_lines[row_index] = ' '.join(values)

            col_index += 1

        updated_content = '\n'.join(current_lines)
        self.text_widget.delete(1.0, tk.END)
        self.text_widget.insert(tk.END, updated_content)

        self.check_value_changes(differences)

    def navigate_2d(self, event):
        if self.display_mode in ['hex16', 'dec16_lh', 'dec16_hl']:
            total_columns = self.num_columns * 16

            if event.keysym == 'Left':
                self.current_offset = max(0, self.current_offset - 2)
            elif event.keysym == 'Right':
                self.current_offset = min((self.total_rows * total_columns * 2) - 2, self.current_offset + 2)

            self.handle_navigation_and_highlight()

    def handle_navigation_and_highlight(self):
        total_columns = self.num_columns * 16
        total_bytes_per_row = total_columns * 2

        line_height = self.notebook.winfo_height()
        x_position = 0

        self.canvas_line.coords(self.clickable_line, x_position, 0, x_position, line_height)

        with open(self.file_path, 'rb') as file:
            file.seek(self.current_offset)
            data = file.read(2)

            if len(data) < 2:
                return

            clicked_value = struct.unpack('<H', data)[0]

        try:
            content = self.text_widget.get(1.0, tk.END)
            lines = content.split("\n")
            row_index = self.current_offset // (total_columns * 2)
            col_index = (self.current_offset % (total_columns * 2)) // 2
            clicked_value = int(lines[row_index].split()[col_index], 10)
        except (IndexError, ValueError):
            pass

        self.value_label.config(text=f"Value: {clicked_value:05}")

        line_width = 1
        self.clicked_line = self.canvas_line.create_line(
            x_position, 0, x_position, line_height, fill="black", width=line_width, tags="clicked_line"
        )

        self.highlight_clicked_value(self.current_offset // 2)

        self.display_line_plot()
        self.update_navigation_buttons()
        self.reset_highlight()

    def skip_to_percentage(self, percentage):
        if percentage == 100:
            with open(self.file_path, 'rb') as file:
                file_size = os.path.getsize(self.file_path)
                self.current_offset = file_size - (self.num_columns * 16 * 2)
        else:
            with open(self.file_path, 'rb') as file:
                file_size = os.path.getsize(self.file_path)
                self.current_offset = int(file_size * (percentage / 100))

        self.handle_navigation_and_highlight()
        self.update_navigation_buttons()

    def load_and_update(self):
        if self.is_unsaved_changes():
            temp_file_path = tempfile.mktemp(suffix=".bin", prefix="LinOLS_temp_")
            with open(temp_file_path, 'wb') as temp_file:
                temp_file.write(
                    b''.join([struct.pack('<H', int(value)) for value in self.text_widget.get(1.0, tk.END).split()]))

            self.file_path = temp_file_path
            self.update_2d_mode()
            self.navigate_2d_right(None)
            self.navigate_2d_left(None)
            self.update_navigation_buttons()

        else:
            file_path = filedialog.askopenfilename(filetypes=[("Binary Files", "*.bin")])
            if file_path:
                self.file_path = file_path
                self.update_2d_mode()
                self.navigate_2d_right(None)
                self.navigate_2d_left(None)
                self.update_navigation_buttons()

    def update_2d_mode(self):
        total_columns = self.num_columns * 16

        with open(self.file_path, 'rb') as file:
            file.seek(self.current_offset)
            data = file.read(total_columns * 2)

        if data:
            numbers = struct.unpack('<' + 'H' * (len(data) // 2), data)

            self.canvas_line.delete("line")
            x_values = np.arange(len(numbers))
            y_values = np.array(numbers)
            y_scaled = self.notebook.winfo_height() * (y_values / max(y_values))

            for i in range(len(x_values) - 1):
                x1 = i * (self.notebook.winfo_width() / len(x_values))
                y1 = self.notebook.winfo_height() - y_scaled[i]
                x2 = (i + 1) * (self.notebook.winfo_width() / len(x_values))
                y2 = self.notebook.winfo_height() - y_scaled[i + 1]

                self.canvas_line.create_line(x1, y1, x2, y2, fill="#bababa", tags="line")

    def apply_theme(self, theme):
        self.root.config(bg=theme['bg'])

        for widget in self.root.winfo_children():
            widget_type = widget.winfo_class()

            if widget_type == 'Label':
                widget.config(bg=theme['bg'], fg=theme['fg'])
            elif widget_type == 'Entry':
                widget.config(bg=theme['entry_bg'], fg=theme['entry_fg'], insertbackground=theme['fg'])
            elif widget_type == 'Button':
                widget.config(bg=theme['btn_bg'], fg=theme['btn_fg'])
            elif widget_type == 'Canvas':
                widget.config(bg=theme['canvas_bg'])

    def undo(self):
        self.text_widget.edit_undo()
        self.check_value_changes(None)

    def redo(self):
        self.text_widget.edit_redo()
        self.check_value_changes(None)

    def sync_2d_to_text(self):
        cursor_pos = self.text_widget.index(tk.INSERT)

        row, col = map(int, cursor_pos.split('.'))

        total_columns_text_view = self.num_columns
        current_offset = ((row - 1) * total_columns_text_view + (col // 6)) * 2

        self.current_offset = current_offset
        self.handle_navigation_and_highlight()

if __name__ == "__main__":
    root = tk.Tk(className='LinOLS')
    LinOLS = LinOLS(root)
    root.mainloop()