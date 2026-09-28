import tkinter as tk
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox, ttk
from xml.sax.saxutils import escape


class NotepadApp(tk.Tk):
    COLORS = ("#202124", "#d93025", "#e37400", "#f9ab00", "#188038", "#1a73e8", "#a142f4")

    def __init__(self):
        super().__init__()
        self.title("Notepad Studio")
        self.geometry("1040x720")
        self.minsize(720, 480)
        self.configure(bg="#f4f6f7")

        self.text_path = None
        self.text_dirty = False
        self.draw_ops = []
        self.active_stroke = None
        self.preview_item = None
        self.tool = tk.StringVar(value="pen")
        self.color = tk.StringVar(value=self.COLORS[0])
        self.brush_size = tk.IntVar(value=4)
        self.word_wrap = tk.BooleanVar(value=True)
        self.show_status = tk.BooleanVar(value=True)
        self.font_size = 12

        self._configure_style()
        self._build_ui()
        self._build_menu()
        self._bind_shortcuts()
        self.protocol("WM_DELETE_WINDOW", self._close)
        self._update_title()

    def _configure_style(self):
        style = ttk.Style(self)
        style.configure("App.TFrame", background="#f4f6f7")
        style.configure("Header.TFrame", background="#163c3a")
        style.configure("HeaderTitle.TLabel", background="#163c3a", foreground="#ffffff", font=("Segoe UI", 17, "bold"))
        style.configure("HeaderHint.TLabel", background="#163c3a", foreground="#c8dfda", font=("Segoe UI", 9))
        style.configure("Toolbar.TFrame", background="#ffffff")
        style.configure("Toolbar.TButton", padding=(12, 7))
        style.configure("Status.TLabel", background="#e8eded", foreground="#435250", padding=(10, 5), font=("Segoe UI", 9))
        style.configure("TNotebook", background="#f4f6f7", borderwidth=0)
        style.configure("TNotebook.Tab", padding=(18, 9), font=("Segoe UI", 10))

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        header = ttk.Frame(self, style="Header.TFrame", padding=(22, 16))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="Notepad Studio", style="HeaderTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(header, text="Write a note or sketch an idea", style="HeaderHint.TLabel").grid(row=1, column=0, sticky="w", pady=(3, 0))

        toolbar = ttk.Frame(self, style="Toolbar.TFrame", padding=(14, 9))
        toolbar.grid(row=1, column=0, sticky="ew")
        ttk.Button(toolbar, text="New", style="Toolbar.TButton", command=self.new_note).pack(side="left", padx=(0, 6))
        ttk.Button(toolbar, text="Open", style="Toolbar.TButton", command=self.open_note).pack(side="left", padx=6)
        ttk.Button(toolbar, text="Save", style="Toolbar.TButton", command=self.save_current).pack(side="left", padx=6)
        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=12)
        ttk.Label(toolbar, text="Text files save as .txt  |  Drawings export as .svg", foreground="#586764").pack(side="left")

        self.pages = ttk.Notebook(self)
        self.pages.grid(row=2, column=0, sticky="nsew", padx=16, pady=(7, 12))
        self.text_page = ttk.Frame(self.pages, style="App.TFrame", padding=1)
        self.draw_page = ttk.Frame(self.pages, style="App.TFrame")
        self.pages.add(self.text_page, text="Note")
        self.pages.add(self.draw_page, text="Drawing")
        self._build_text_page()
        self._build_draw_page()

        self.status = ttk.Label(self, text="Ready", style="Status.TLabel", anchor="w")
        self.status.grid(row=3, column=0, sticky="ew")

    def _build_text_page(self):
        self.text_page.rowconfigure(0, weight=1)
        self.text_page.columnconfigure(0, weight=1)
        text_frame = ttk.Frame(self.text_page)
        text_frame.grid(row=0, column=0, sticky="nsew")
        text_frame.rowconfigure(0, weight=1)
        text_frame.columnconfigure(0, weight=1)

        self.editor = tk.Text(
            text_frame,
            wrap="word",
            undo=True,
            font=("Segoe UI", 12),
            padx=22,
            pady=18,
            relief="flat",
            bg="#ffffff",
            fg="#202b29",
            insertbackground="#163c3a",
            selectbackground="#cbe5de",
            selectforeground="#163c3a",
        )
        self.editor.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.editor.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.horizontal_scrollbar = ttk.Scrollbar(text_frame, orient="horizontal", command=self.editor.xview)
        self.editor.configure(yscrollcommand=scrollbar.set, xscrollcommand=self.horizontal_scrollbar.set)
        self.horizontal_scrollbar.grid(row=1, column=0, sticky="ew")
        self.horizontal_scrollbar.grid_remove()
        self.editor.bind("<<Modified>>", self._on_text_modified)
        self.editor.bind("<KeyRelease>", self._update_text_status)
        self.editor.bind("<ButtonRelease-1>", self._update_text_status)

    def _build_menu(self):
        menubar = tk.Menu(self)

        file_menu = tk.Menu(menubar, tearoff=False)
        file_menu.add_command(label="New", accelerator="Ctrl+N", command=self.new_note)
        file_menu.add_command(label="Open...", accelerator="Ctrl+O", command=self.open_note)
        file_menu.add_separator()
        file_menu.add_command(label="Save", accelerator="Ctrl+S", command=self.save_current)
        file_menu.add_command(label="Save As...", accelerator="Ctrl+Shift+S", command=self._save_as_current)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._close)
        menubar.add_cascade(label="File", menu=file_menu)

        edit_menu = tk.Menu(menubar, tearoff=False)
        edit_menu.add_command(label="Undo", accelerator="Ctrl+Z", command=self._undo_shortcut)
        edit_menu.add_command(label="Redo", accelerator="Ctrl+Y", command=self._redo)
        edit_menu.add_separator()
        edit_menu.add_command(label="Cut", accelerator="Ctrl+X", command=lambda: self._edit_action("cut"))
        edit_menu.add_command(label="Copy", accelerator="Ctrl+C", command=lambda: self._edit_action("copy"))
        edit_menu.add_command(label="Paste", accelerator="Ctrl+V", command=lambda: self._edit_action("paste"))
        edit_menu.add_command(label="Delete", command=self._delete_selection)
        edit_menu.add_separator()
        edit_menu.add_command(label="Select All", accelerator="Ctrl+A", command=self._select_all)
        edit_menu.add_command(label="Time/Date", accelerator="F5", command=self._insert_time_date)
        menubar.add_cascade(label="Edit", menu=edit_menu)

        view_menu = tk.Menu(menubar, tearoff=False)
        view_menu.add_checkbutton(label="Word Wrap", variable=self.word_wrap, command=self._toggle_word_wrap)
        view_menu.add_checkbutton(label="Status Bar", variable=self.show_status, command=self._toggle_status_bar)
        view_menu.add_separator()
        view_menu.add_command(label="Zoom In", accelerator="Ctrl++", command=self._zoom_in)
        view_menu.add_command(label="Zoom Out", accelerator="Ctrl+-", command=self._zoom_out)
        view_menu.add_command(label="Restore Default Zoom", accelerator="Ctrl+0", command=self._reset_zoom)
        menubar.add_cascade(label="View", menu=view_menu)

        self.configure(menu=menubar)

    def _build_draw_page(self):
        self.draw_page.rowconfigure(1, weight=1)
        self.draw_page.columnconfigure(0, weight=1)
        tools = ttk.Frame(self.draw_page, padding=(12, 10))
        tools.grid(row=0, column=0, sticky="ew")

        for label, value in (("Pen", "pen"), ("Eraser", "eraser"), ("Line", "line"), ("Rectangle", "rectangle"), ("Ellipse", "ellipse")):
            ttk.Radiobutton(tools, text=label, value=value, variable=self.tool).pack(side="left", padx=(0, 8))
        ttk.Separator(tools, orient="vertical").pack(side="left", fill="y", padx=8)

        for swatch in self.COLORS:
            button = tk.Button(
                tools,
                bg=swatch,
                activebackground=swatch,
                width=2,
                height=1,
                relief="solid",
                bd=1,
                command=lambda value=swatch: self.color.set(value),
            )
            button.pack(side="left", padx=2)
        ttk.Button(tools, text="More colors", command=self._choose_color).pack(side="left", padx=(6, 12))
        ttk.Label(tools, text="Size").pack(side="left", padx=(0, 5))
        ttk.Spinbox(tools, from_=1, to=32, width=4, textvariable=self.brush_size).pack(side="left")
        ttk.Button(tools, text="Undo", command=self.undo_drawing).pack(side="right", padx=(6, 0))
        ttk.Button(tools, text="Clear", command=self.clear_drawing).pack(side="right")

        canvas_frame = ttk.Frame(self.draw_page, padding=(12, 0, 12, 12))
        canvas_frame.grid(row=1, column=0, sticky="nsew")
        canvas_frame.rowconfigure(0, weight=1)
        canvas_frame.columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(canvas_frame, bg="#ffffff", highlightthickness=1, highlightbackground="#d5ddda", cursor="crosshair")
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.canvas.bind("<ButtonPress-1>", self._start_drawing)
        self.canvas.bind("<B1-Motion>", self._continue_drawing)
        self.canvas.bind("<ButtonRelease-1>", self._finish_drawing)
        self.canvas.bind("<Motion>", self._update_draw_status)

    def _bind_shortcuts(self):
        self.bind("<Control-n>", lambda _event: self._run_shortcut(self.new_note))
        self.bind("<Control-o>", lambda _event: self._run_shortcut(self.open_note))
        self.bind("<Control-s>", lambda _event: self._run_shortcut(self.save_current))
        self.bind("<Control-Shift-S>", lambda _event: self._run_shortcut(self._save_as_current))
        self.bind("<Control-z>", self._undo_shortcut)
        self.bind("<Control-y>", lambda _event: self._run_shortcut(self._redo))
        self.bind("<Control-x>", lambda _event: self._run_shortcut(lambda: self._edit_action("cut")))
        self.bind("<Control-c>", lambda _event: self._run_shortcut(lambda: self._edit_action("copy")))
        self.bind("<Control-v>", lambda _event: self._run_shortcut(lambda: self._edit_action("paste")))
        self.bind("<Control-a>", lambda _event: self._run_shortcut(self._select_all))
        self.bind("<F5>", lambda _event: self._run_shortcut(self._insert_time_date))
        self.bind("<Control-plus>", lambda _event: self._run_shortcut(self._zoom_in))
        self.bind("<Control-equal>", lambda _event: self._run_shortcut(self._zoom_in))
        self.bind("<Control-minus>", lambda _event: self._run_shortcut(self._zoom_out))
        self.bind("<Control-0>", lambda _event: self._run_shortcut(self._reset_zoom))

    def _run_shortcut(self, command):
        command()
        return "break"

    def _undo_shortcut(self, _event=None):
        if self.pages.index(self.pages.select()) == 1:
            self.undo_drawing()
        else:
            try:
                self.editor.edit_undo()
            except tk.TclError:
                pass
        return "break"

    def _redo(self):
        try:
            self.editor.edit_redo()
        except tk.TclError:
            pass

    def _save_as_current(self):
        if self.pages.index(self.pages.select()) == 1:
            self.save_drawing()
        else:
            self.save_as()

    def _edit_action(self, action):
        self.editor.focus_set()
        self.editor.event_generate(f"<<{action.title()}>>")

    def _delete_selection(self):
        try:
            self.editor.delete("sel.first", "sel.last")
        except tk.TclError:
            pass

    def _select_all(self):
        self.editor.tag_add("sel", "1.0", "end-1c")
        self.editor.mark_set("insert", "1.0")
        self.editor.see("insert")
        self.editor.focus_set()

    def _insert_time_date(self):
        from datetime import datetime

        self.editor.insert("insert", datetime.now().strftime("%H:%M %m/%d/%Y"))

    def _toggle_word_wrap(self):
        if self.word_wrap.get():
            self.editor.configure(wrap="word")
            self.horizontal_scrollbar.grid_remove()
        else:
            self.editor.configure(wrap="none")
            self.horizontal_scrollbar.grid(row=1, column=0, sticky="ew")

    def _toggle_status_bar(self):
        if self.show_status.get():
            self.status.grid(row=3, column=0, sticky="ew")
        else:
            self.status.grid_remove()

    def _zoom_in(self):
        self._set_zoom(self.font_size + 1)

    def _zoom_out(self):
        self._set_zoom(self.font_size - 1)

    def _reset_zoom(self):
        self._set_zoom(12)

    def _set_zoom(self, size):
        self.font_size = max(6, min(48, size))
        self.editor.configure(font=("Segoe UI", self.font_size))

    def _on_text_modified(self, _event=None):
        if self.editor.edit_modified():
            self.text_dirty = True
            self.editor.edit_modified(False)
            self._update_title()
            self._update_text_status()

    def _update_text_status(self, _event=None):
        content = self.editor.get("1.0", "end-1c")
        line, column = self.editor.index("insert").split(".")
        self.status.configure(text=f"Line {line}, column {int(column) + 1}    {len(content)} characters")

    def _update_draw_status(self, event):
        self.status.configure(text=f"Drawing    x: {event.x}  y: {event.y}    {len(self.draw_ops)} marks")

    def _update_title(self):
        name = self.text_path.name if self.text_path else "Untitled"
        marker = " *" if self.text_dirty else ""
        self.title(f"{name}{marker} - Notepad Studio")

    def _confirm_discard(self):
        if not self.text_dirty:
            return True
        answer = messagebox.askyesnocancel("Unsaved note", "Save changes to your note before continuing?", parent=self)
        if answer is None:
            return False
        if answer:
            return self.save_note()
        return True

    def new_note(self):
        if not self._confirm_discard():
            return
        self.editor.delete("1.0", "end")
        self.text_path = None
        self.text_dirty = False
        self.editor.edit_reset()
        self.editor.edit_modified(False)
        self._update_title()
        self.pages.select(self.text_page)
        self.status.configure(text="New note")

    def open_note(self):
        if not self._confirm_discard():
            return
        selected = filedialog.askopenfilename(
            parent=self,
            title="Open note",
            filetypes=(("Text files", "*.txt"), ("All files", "*.*")),
        )
        if not selected:
            return
        try:
            content = Path(selected).read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            messagebox.showerror("Open failed", str(error), parent=self)
            return
        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", content)
        self.editor.edit_reset()
        self.editor.edit_modified(False)
        self.text_path = Path(selected)
        self.text_dirty = False
        self._update_title()
        self.pages.select(self.text_page)
        self._update_text_status()

    def save_current(self):
        if self.pages.index(self.pages.select()) == 1:
            self.save_drawing()
        else:
            self.save_note()

    def save_note(self):
        if self.text_path is None:
            return self.save_as()
        try:
            self.text_path.write_text(self.editor.get("1.0", "end-1c"), encoding="utf-8")
        except OSError as error:
            messagebox.showerror("Save failed", str(error), parent=self)
            return False
        self.text_dirty = False
        self._update_title()
        self.status.configure(text=f"Saved {self.text_path.name}")
        return True

    def save_as(self):
        selected = filedialog.asksaveasfilename(
            parent=self,
            title="Save note as",
            defaultextension=".txt",
            filetypes=(("Text files", "*.txt"), ("All files", "*.*")),
            initialfile=self.text_path.name if self.text_path else "Untitled.txt",
        )
        if not selected:
            return False
        self.text_path = Path(selected)
        return self.save_note()

    def _choose_color(self):
        result = colorchooser.askcolor(color=self.color.get(), parent=self)
        if result and result[1]:
            self.color.set(result[1])

    def _start_drawing(self, event):
        self.canvas.focus_set()
        active_tool = self.tool.get()
        color = "#ffffff" if active_tool == "eraser" else self.color.get()
        width = max(1, min(32, int(self.brush_size.get())))
        self.active_stroke = {"tool": active_tool, "color": color, "width": width, "points": [event.x, event.y]}
        if active_tool in ("pen", "eraser"):
            self.active_stroke["item"] = self.canvas.create_line(
                event.x, event.y, event.x + 1, event.y + 1,
                fill=color, width=width, capstyle=tk.ROUND, joinstyle=tk.ROUND, smooth=True,
            )

    def _continue_drawing(self, event):
        if self.active_stroke is None:
            return
        operation = self.active_stroke
        if operation["tool"] in ("pen", "eraser"):
            operation["points"].extend((event.x, event.y))
            self.canvas.coords(operation["item"], *operation["points"])
            return
        operation["points"] = [*operation["points"][:2], event.x, event.y]
        if self.preview_item is not None:
            self.canvas.delete(self.preview_item)
        x1, y1 = operation["points"][:2]
        color, width = operation["color"], operation["width"]
        if operation["tool"] == "line":
            self.preview_item = self.canvas.create_line(x1, y1, event.x, event.y, fill=color, width=width)
        elif operation["tool"] == "rectangle":
            self.preview_item = self.canvas.create_rectangle(x1, y1, event.x, event.y, outline=color, width=width)
        else:
            self.preview_item = self.canvas.create_oval(x1, y1, event.x, event.y, outline=color, width=width)

    def _finish_drawing(self, event):
        if self.active_stroke is None:
            return
        operation = self.active_stroke
        if operation["tool"] not in ("pen", "eraser"):
            operation["points"] = [*operation["points"][:2], event.x, event.y]
            if self.preview_item is not None:
                self.canvas.delete(self.preview_item)
                self.preview_item = None
            self._draw_shape(operation)
        operation.pop("item", None)
        self.draw_ops.append(operation)
        self.active_stroke = None
        self.status.configure(text=f"Drawing    {len(self.draw_ops)} marks")

    def _draw_shape(self, operation):
        x1, y1, x2, y2 = operation["points"][:4]
        options = {"outline": operation["color"], "width": operation["width"]}
        if operation["tool"] == "line":
            self.canvas.create_line(x1, y1, x2, y2, fill=operation["color"], width=operation["width"])
        elif operation["tool"] == "rectangle":
            self.canvas.create_rectangle(x1, y1, x2, y2, **options)
        else:
            self.canvas.create_oval(x1, y1, x2, y2, **options)

    def _redraw(self):
        self.canvas.delete("all")
        for operation in self.draw_ops:
            if operation["tool"] in ("pen", "eraser"):
                self.canvas.create_line(
                    *operation["points"], fill=operation["color"], width=operation["width"],
                    capstyle=tk.ROUND, joinstyle=tk.ROUND, smooth=True,
                )
            else:
                self._draw_shape(operation)

    def undo_drawing(self):
        if self.draw_ops:
            self.draw_ops.pop()
            self._redraw()
            self.status.configure(text=f"Drawing    {len(self.draw_ops)} marks")

    def clear_drawing(self):
        if not self.draw_ops:
            return
        if messagebox.askyesno("Clear drawing", "Remove all marks from this drawing?", parent=self):
            self.draw_ops.clear()
            self._redraw()
            self.status.configure(text="Drawing cleared")

    def save_drawing(self):
        selected = filedialog.asksaveasfilename(
            parent=self,
            title="Export drawing",
            defaultextension=".svg",
            filetypes=(("SVG image", "*.svg"),),
            initialfile="Drawing.svg",
        )
        if not selected:
            return False
        width = max(1, self.canvas.winfo_width())
        height = max(1, self.canvas.winfo_height())
        elements = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
                    f'<rect width="{width}" height="{height}" fill="#ffffff"/>']
        for operation in self.draw_ops:
            color = escape(operation["color"], {'"': "&quot;"})
            stroke_width = operation["width"]
            points = operation["points"]
            tool = operation["tool"]
            if tool in ("pen", "eraser"):
                path = " ".join(("M" if index == 0 else "L") + f"{points[index]},{points[index + 1]}" for index in range(0, len(points), 2))
                elements.append(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="{stroke_width}" stroke-linecap="round" stroke-linejoin="round"/>')
            elif tool == "line":
                elements.append(f'<line x1="{points[0]}" y1="{points[1]}" x2="{points[2]}" y2="{points[3]}" stroke="{color}" stroke-width="{stroke_width}"/>')
            elif tool == "rectangle":
                x, y = min(points[0], points[2]), min(points[1], points[3])
                shape_width, shape_height = abs(points[2] - points[0]), abs(points[3] - points[1])
                elements.append(f'<rect x="{x}" y="{y}" width="{shape_width}" height="{shape_height}" fill="none" stroke="{color}" stroke-width="{stroke_width}"/>')
            else:
                x, y = min(points[0], points[2]), min(points[1], points[3])
                radius_x, radius_y = abs(points[2] - points[0]) / 2, abs(points[3] - points[1]) / 2
                elements.append(f'<ellipse cx="{x + radius_x}" cy="{y + radius_y}" rx="{radius_x}" ry="{radius_y}" fill="none" stroke="{color}" stroke-width="{stroke_width}"/>')
        elements.append("</svg>")
        try:
            Path(selected).write_text("\n".join(elements), encoding="utf-8")
        except OSError as error:
            messagebox.showerror("Export failed", str(error), parent=self)
            return False
        self.status.configure(text=f"Exported {Path(selected).name}")
        return True

    def _close(self):
        if self._confirm_discard():
            self.destroy()


if __name__ == "__main__":
    NotepadApp().mainloop()