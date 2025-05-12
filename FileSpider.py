import tkinter as tk
from tkinter import ttk, filedialog, Menu, scrolledtext
import os
import math
import threading
import random
import time
from collections import deque

class RetroButton(tk.Canvas):
    def __init__(self, master, text, command, **kwargs):
        super().__init__(master, **kwargs)
        self.command = command
        self.text = text
        self.config(bg='#001100', highlightthickness=0)
        self.width = 100
        self.height = 30
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.bind("<Button-1>", self.on_click)
        self.draw_button()
        
    def draw_button(self, hover=False, pressed=False):
        self.delete("all")
        # Retro CRT grid effect
        for _ in range(25):
            x = random.randint(2, self.width-2)
            y = random.randint(2, self.height-2)
            self.create_rectangle(x, y, x+1, y+1, fill='#003300', outline='')
        
        # Button border
        self.create_rectangle(4, 4, self.width-4, self.height-4,
                            outline='#00FF00' if not pressed else '#005500',
                            width=2)
        
        # Button text with shadow
        text_color = '#88FF88' if hover else '#00FF00'
        self.create_text(self.width/2+2, self.height/2+2, text=self.text,
                        fill='#002200', font=('Courier New', 10, 'bold'))
        self.create_text(self.width/2, self.height/2, text=self.text,
                        fill=text_color, font=('Courier New', 10, 'bold'))
        
    def on_enter(self, event):
        self.draw_button(hover=True)
        
    def on_leave(self, event):
        self.draw_button()
        
    def on_click(self, event):
        self.draw_button(pressed=True)
        self.update()
        time.sleep(0.1)
        self.command()
        self.draw_button(hover=True)

class Node:
    def __init__(self, name, path, is_folder, depth):
        self.name = name
        self.path = path
        self.is_folder = is_folder
        self.depth = depth
        self.children = []
        self.x = 0
        self.y = 0

class RetroSpiderWebApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("RETRO SPIDER v3.0")
        self.geometry("1280x720")
        self.configure(bg='#001100')
        self.radius_step = 120
        self.current_root = None
        self.history = []
        self.glitch_active = False
        self.scanlines = []
        self.tree_lines = []
        
        # Configuration
        self.level_var = tk.IntVar(value=3)
        self.max_files_var = tk.IntVar(value=10)
        self.colors = {
            'bg': '#001100',
            'text': '#00FF00',
            'scanline': '#002200',
            'file_text': '#FFFF00',
            'folder_text': '#88FF88'
        }
        
        # UI Setup
        self.create_widgets()
        self.create_context_menu()
        self.bind("<KeyPress>", self.glitch_effect)
        self.after(100, self.crt_flicker)
        
    def create_widgets(self):
        # Main paned window
        self.paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True)
        
        # Left panel - Visualization
        left_frame = ttk.Frame(self.paned)
        control_frame = ttk.Frame(left_frame)
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Navigation controls
        RetroButton(control_frame, text="◄ BACK", command=self.navigate_back,
                  width=80, height=30).grid(row=0, column=0, padx=5)
        
        ttk.Label(control_frame, text="PATH:", foreground='#00FF00', 
                 background='#001100').grid(row=0, column=1, padx=5)
        self.path_entry = ttk.Entry(control_frame, width=40, 
                                  font=('Courier New', 10))
        self.path_entry.grid(row=0, column=2, padx=5)
        
        RetroButton(control_frame, text="BROWSE", command=self.select_directory,
                  width=100, height=30).grid(row=0, column=3, padx=5)
        
        ttk.Label(control_frame, text="DEPTH:", foreground='#00FF00',
                 background='#001100').grid(row=0, column=4, padx=5)
        self.level_spin = ttk.Spinbox(control_frame, from_=1, to=10, 
                                    textvariable=self.level_var, width=5)
        self.level_spin.grid(row=0, column=5, padx=5)
        
        ttk.Label(control_frame, text="MAX FILES:", foreground='#00FF00',
                 background='#001100').grid(row=0, column=6, padx=5)
        self.max_spin = ttk.Spinbox(control_frame, from_=1, to=100, 
                                  textvariable=self.max_files_var, width=5)
        self.max_spin.grid(row=0, column=7, padx=5)
        
        RetroButton(control_frame, text="SCAN", command=self.start_scan,
                  width=80, height=30).grid(row=0, column=8, padx=5)
        
        # Canvas
        self.canvas = tk.Canvas(left_frame, bg='black', highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.paned.add(left_frame, weight=2)
        
        # Right panel - Tree view
        right_frame = ttk.Frame(self.paned)
        self.tree_text = scrolledtext.ScrolledText(
            right_frame, bg='black', fg='#00FF00', 
            font=('Courier New', 10), insertbackground='#00FF00',
            relief='sunken', borderwidth=5, state='disabled'
        )
        self.tree_text.pack(fill=tk.BOTH, expand=True)
        self.tree_text.bind("<Button-1>", self.on_tree_click)
        self.paned.add(right_frame, weight=1)
        
        # Status bar
        self.status = ttk.Label(self, text="READY", foreground='#00FF00',
                              background='#001100', anchor=tk.W)
        self.status.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Initial effects
        self.draw_scanlines()
        
    def navigate_back(self):
        if self.history:
            self.current_root = self.history.pop()
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, self.current_root.path)
            self.start_scan()
        
    def on_tree_click(self, event):
        self.tree_text.config(state='normal')
        index = self.tree_text.index(f"@{event.x},{event.y}")
        line_num = int(index.split('.')[0])
        self.tree_text.config(state='disabled')
        
        if line_num - 1 < len(self.tree_lines):
            node = self.tree_lines[line_num - 1]
            if node.is_folder:
                self.history.append(self.current_root)
                self.on_node_click(node)
            else:
                self.center_on_node(node)
                
    def center_on_node(self, node):
        self.canvas.xview_moveto((node.x - self.canvas.winfo_width()/2) / self.canvas.winfo_width())
        self.canvas.yview_moveto((node.y - self.canvas.winfo_height()/2) / self.canvas.winfo_height())
        
    def draw_scanlines(self):
        for line in self.scanlines:
            self.canvas.delete(line)
        self.scanlines = []
        width = self.canvas.winfo_width()
        height = self.canvas.winfo_height()
        
        for y in range(0, height, 3):
            self.scanlines.append(
                self.canvas.create_line(0, y, width, y, fill=self.colors['scanline'])
            )
            
        for _ in range(random.randint(3, 7)):
            x = random.randint(0, width)
            self.scanlines.append(
                self.canvas.create_line(x, 0, x + random.randint(-10,10), height,
                                      fill=self.colors['scanline'], width=random.choice([1,2]))
            )
            
    def glitch_effect(self, event=None):
        if not self.glitch_active:
            self.glitch_active = True
            orig_geometry = self.geometry()
            for _ in range(8):
                self.geometry(f"1280x720+{random.randint(-3,3)}+{random.randint(-3,3)}")
                self.update()
                time.sleep(0.05)
            self.geometry(orig_geometry)
            self.glitch_active = False
            
    def crt_flicker(self):
        if random.random() > 0.85:
            self.canvas.configure(bg='#001100')
            self.after(50, lambda: self.canvas.configure(bg='black'))
        self.after(1000, self.crt_flicker)
        
    def select_directory(self):
        path = filedialog.askdirectory()
        if path:
            self.history.clear()
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, path)
            self.start_scan()
            
    def start_scan(self):
        path = self.path_entry.get()
        if not os.path.isdir(path):
            self.status.config(text="INVALID DIRECTORY!")
            return
            
        self.current_root = Node(os.path.basename(path), path, True, 0)
        threading.Thread(target=self.scan_directory, 
                        args=(self.current_root, self.level_var.get()),
                        daemon=True).start()
        
    def scan_directory(self, node, max_depth):
        try:
            if node.depth >= max_depth:
                return
                
            entries = []
            try: entries = os.listdir(node.path)
            except PermissionError: return
                
            folders = [e for e in entries if os.path.isdir(os.path.join(node.path, e))]
            files = [e for e in entries if not os.path.isdir(os.path.join(node.path, e))]
            entries = folders + files[:self.max_files_var.get()]
            
            for entry in entries:
                entry_path = os.path.join(node.path, entry)
                is_folder = os.path.isdir(entry_path)
                child = Node(entry, entry_path, is_folder, node.depth + 1)
                node.children.append(child)
                if is_folder:
                    self.scan_directory(child, max_depth)
                    
            self.after(0, self.update_displays)
        except Exception as e:
            self.after(0, lambda: self.status.config(text=f"ERROR: {str(e)}"))
            
    def update_displays(self):
        self.draw_spider_web()
        self.draw_tree_view()
        
    def draw_spider_web(self):
        self.canvas.delete("all")
        self.draw_scanlines()
        if not self.current_root: return
            
        center_x = self.canvas.winfo_width() / 2
        center_y = self.canvas.winfo_height() / 2
        
        self.calculate_positions(self.current_root, center_x, center_y)
        self.draw_connections(self.current_root)
        self.draw_nodes(self.current_root)
        self.status.config(text=f"DISPLAYING: {self.current_root.path}")
        
    def calculate_positions(self, node, parent_x, parent_y):
        node.x = parent_x
        node.y = parent_y
        num_children = len(node.children)
        
        for i, child in enumerate(node.children):
            angle = (2 * math.pi * i) / num_children if num_children > 0 else 0
            radius = self.radius_step * (child.depth)
            
            child.x = parent_x + radius * math.cos(angle)
            child.y = parent_y + radius * math.sin(angle)
            
            if child.is_folder and child.depth < self.level_var.get():
                self.calculate_positions(child, child.x, child.y)
                
    def draw_connections(self, node):
        for child in node.children:
            self.canvas.create_line(node.x, node.y, child.x, child.y, 
                                  fill=self.colors['text'], width=1, dash=(4,2))
            self.draw_connections(child)
            
    def draw_nodes(self, node):
        if node.is_folder:
            text = f"[{node.name}]"
            self.canvas.create_text(node.x+2, node.y+2, text=text,
                                  fill='#002200', font=('Courier New', 10))
            text_id = self.canvas.create_text(node.x, node.y, text=text,
                                            fill=self.colors['folder_text'], 
                                            font=('Courier New', 10))
            self.canvas.tag_bind(text_id, '<Button-1>', 
                               lambda e, n=node: self.on_node_click(n))
            self.canvas.tag_bind(text_id, '<Button-3>', 
                               lambda e, n=node: self.show_context_menu(e, n))
        else:
            self.canvas.create_text(node.x+2, node.y+2, text=node.name,
                                  fill='#552200', font=('Courier New', 9))
            text_id = self.canvas.create_text(node.x, node.y, text=node.name,
                                            fill=self.colors['file_text'], 
                                            font=('Courier New', 9))
            
        for child in node.children:
            self.draw_nodes(child)
            
    def draw_tree_view(self):
        self.tree_text.config(state='normal')
        self.tree_text.delete(1.0, tk.END)
        self.tree_lines = []
        if not self.current_root: 
            self.tree_text.config(state='disabled')
            return
            
        tree_lines = []
        queue = deque([(self.current_root, 0, True, [])])
        
        while queue:
            node, level, is_last, parent_prefix = queue.pop()
            connector = "└── " if is_last else "├── "
            prefix = "".join(parent_prefix)
            suffix = "/" if node.is_folder else ""
            tree_lines.append(f"{prefix}{connector}{node.name}{suffix}")
            self.tree_lines.append(node)
            
            if node.is_folder and node.depth < self.level_var.get():
                new_prefix = parent_prefix + ["    " if is_last else "│   "]
                children = sorted(node.children, key=lambda x: not x.is_folder)
                children = children[:self.max_files_var.get() + len([c for c in children if c.is_folder])]
                last_index = len(children) - 1
                
                for i, child in enumerate(reversed(children)):
                    queue.append((child, level + 1, i == last_index, new_prefix))
        
        # Colorized output
        for line in tree_lines:
            if "/" in line:
                self.tree_text.insert(tk.END, line.split("/")[0], 'folder')
                self.tree_text.insert(tk.END, "/\n", 'folder_symbol')
            else:
                parts = line.split("── ")
                self.tree_text.insert(tk.END, parts[0] + "── ", 'tree_lines')
                self.tree_text.insert(tk.END, parts[1] + "\n", 'file')
                
        self.tree_text.tag_config('folder', foreground='#00FF00')
        self.tree_text.tag_config('folder_symbol', foreground='#005500')
        self.tree_text.tag_config('file', foreground='#FFFF00')
        self.tree_text.tag_config('tree_lines', foreground='#555555')
        self.tree_text.config(state='disabled')
        
    def on_node_click(self, node):
        self.history.append(self.current_root)
        self.current_root = node
        self.path_entry.delete(0, tk.END)
        self.path_entry.insert(0, node.path)
        self.start_scan()
        
    def create_context_menu(self):
        self.context_menu = Menu(self, tearoff=0, bg='#001100', 
                               fg='#00FF00', font=('Courier New', 9))
        self.context_menu.add_command(label="OPEN IN EXPLORER", command=self.open_in_explorer)
        self.context_menu.add_command(label="COPY PATH", command=self.copy_path)
        self.context_menu.add_command(label="SET AS ROOT", command=self.set_as_root)
        
    def show_context_menu(self, event, node):
        self.selected_node = node
        self.context_menu.tk_popup(event.x_root, event.y_root)
        
    def open_in_explorer(self):
        os.startfile(self.selected_node.path)
        
    def copy_path(self):
        self.clipboard_clear()
        self.clipboard_append(self.selected_node.path)
        
    def set_as_root(self):
        self.on_node_click(self.selected_node)

if __name__ == "__main__":
    app = RetroSpiderWebApp()
    app.mainloop()