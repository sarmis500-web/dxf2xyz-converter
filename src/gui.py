import os
import sys
import json
import logging
import threading
import queue
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

if sys.platform == 'darwin':
    # Tcl 9.0 on macOS Homebrew causes a fatal ABI segmentation fault 
    # when attempting to load the tkdnd C-extension compiled for Tcl 8.x.
    HAS_DND = False
else:
    try:
        from tkinterdnd2 import TkinterDnD, DND_FILES
        HAS_DND = True
    except ImportError:
        HAS_DND = False

from reader import read_dxf, ReaderOptions
from processor import process, ProcessOptions
from writer import write_pointcloud, WriterOptions
from version import __version__

LOG_PATH = os.path.expanduser("~/.dxf2xyz.log")
SETTINGS_PATH = os.path.expanduser("~/.dxf2xyz_settings.json")

# Configure logging
logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

class ConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title(f"DXF to XYZ Converter v{__version__}")
        self.root.geometry("720x650")
        self.root.minsize(720, 650)
        
        # Force window to the foreground on macOS
        self.root.lift()
        self.root.attributes('-topmost', True)
        self.root.after_idle(self.root.attributes, '-topmost', False)
        
        self.queue = queue.Queue()
        
        # Variables
        self.input_path = tk.StringVar(master=self.root)
        self.output_path = tk.StringVar(master=self.root)
        self.format_var = tk.StringVar(master=self.root, value="xyz")
        
        # Presets
        self.preset_var = tk.StringVar(master=self.root, value="green")
        
        # Advanced Variables
        self.curve_sagitta = tk.DoubleVar(master=self.root, value=0.05)
        self.sample_faces = tk.BooleanVar(master=self.root, value=False)
        self.face_density = tk.DoubleVar(master=self.root, value=0.1)
        self.expand_blocks = tk.BooleanVar(master=self.root, value=True)
        self.dedupe = tk.BooleanVar(master=self.root, value=True)
        
        self.voxel_size = tk.DoubleVar(master=self.root, value=0.06)
        self.voxel_mode = tk.StringVar(master=self.root, value="first")
        self.scale_factor = tk.DoubleVar(master=self.root, value=1.0)
        self.center_origin = tk.BooleanVar(master=self.root, value=False)
        
        self.flip_x = tk.BooleanVar(master=self.root, value=False)
        self.flip_y = tk.BooleanVar(master=self.root, value=False)
        self.flip_z = tk.BooleanVar(master=self.root, value=False)
        self.swap_yz = tk.BooleanVar(master=self.root, value=False)
        
        self.delimiter = tk.StringVar(master=self.root, value=" ")
        self.precision = tk.IntVar(master=self.root, value=4)
        self.header = tk.StringVar(master=self.root, value="none")
        self.header_text = tk.StringVar(master=self.root, value="")
        self.intensity = tk.StringVar(master=self.root, value="none")
        self.rgb_var = tk.StringVar(master=self.root, value="none")
        
        self.rgb_r = tk.IntVar(master=self.root, value=255)
        self.rgb_g = tk.IntVar(master=self.root, value=255)
        self.rgb_b = tk.IntVar(master=self.root, value=255)
        
        self.build_ui()
        self.load_settings()
        
        if HAS_DND:
            self.root.drop_target_register(DND_FILES)
            self.root.dnd_bind('<<Drop>>', self.on_drop)

    def on_drop(self, event):
        path = event.data
        if path.startswith("{") and path.endswith("}"):
            path = path[1:-1]
        self.input_path.set(path)
        self.update_default_output()

    def build_ui(self):
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Input row
        row1 = ttk.Frame(main_frame)
        row1.pack(fill=tk.X, pady=2)
        ttk.Label(row1, text="Input DXF:", width=10).pack(side=tk.LEFT)
        ttk.Entry(row1, textvariable=self.input_path, state="readonly").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Button(row1, text="Browse...", command=self.browse_input).pack(side=tk.LEFT)
        
        # Output row
        row2 = ttk.Frame(main_frame)
        row2.pack(fill=tk.X, pady=2)
        ttk.Label(row2, text="Output:", width=10).pack(side=tk.LEFT)
        ttk.Entry(row2, textvariable=self.output_path, state="readonly").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        ttk.Combobox(row2, textvariable=self.format_var, values=["xyz", "pts"], state="readonly", width=5).pack(side=tk.LEFT, padx=5)
        self.format_var.trace_add("write", lambda *args: self.update_default_output())
        ttk.Button(row2, text="Save As...", command=self.browse_output).pack(side=tk.LEFT)

        # Presets row
        row3 = ttk.Frame(main_frame)
        row3.pack(fill=tk.X, pady=10)
        ttk.Radiobutton(row3, text="UV laser (0.06 mm)", variable=self.preset_var, value="uv", command=self.apply_preset).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(row3, text="Green laser (0.07 mm)", variable=self.preset_var, value="green", command=self.apply_preset).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(row3, text="No thinning", variable=self.preset_var, value="none", command=self.apply_preset).pack(side=tk.LEFT, padx=5)
        
        self.adv_btn = ttk.Button(row3, text="Advanced...", command=self.toggle_advanced)
        self.adv_btn.pack(side=tk.RIGHT)

        # Advanced options (collapsible)
        self.adv_frame = ttk.LabelFrame(main_frame, text="Advanced Options", padding=10)
        
        # Grid layout for advanced
        ttk.Label(self.adv_frame, text="Curve sagitta (mm):").grid(row=0, column=0, sticky=tk.W)
        ttk.Spinbox(self.adv_frame, from_=0.001, to=10.0, increment=0.01, textvariable=self.curve_sagitta, width=8).grid(row=0, column=1, sticky=tk.W)
        
        ttk.Checkbutton(self.adv_frame, text="Sample face interiors", variable=self.sample_faces).grid(row=1, column=0, sticky=tk.W)
        ttk.Spinbox(self.adv_frame, from_=0.01, to=10.0, increment=0.01, textvariable=self.face_density, width=8).grid(row=1, column=1, sticky=tk.W)
        
        ttk.Checkbutton(self.adv_frame, text="Expand blocks", variable=self.expand_blocks).grid(row=2, column=0, sticky=tk.W)
        ttk.Checkbutton(self.adv_frame, text="Dedupe duplicates", variable=self.dedupe).grid(row=3, column=0, sticky=tk.W)
        
        ttk.Label(self.adv_frame, text="Voxel size (mm):").grid(row=4, column=0, sticky=tk.W)
        ttk.Spinbox(self.adv_frame, from_=0.0, to=100.0, increment=0.01, textvariable=self.voxel_size, width=8).grid(row=4, column=1, sticky=tk.W)
        
        vmode_frame = ttk.Frame(self.adv_frame)
        vmode_frame.grid(row=4, column=2, sticky=tk.W, padx=10)
        ttk.Radiobutton(vmode_frame, text="Keep first", variable=self.voxel_mode, value="first").pack(side=tk.LEFT)
        ttk.Radiobutton(vmode_frame, text="Centroid", variable=self.voxel_mode, value="centroid").pack(side=tk.LEFT)

        ttk.Label(self.adv_frame, text="Scale factor:").grid(row=5, column=0, sticky=tk.W)
        ttk.Spinbox(self.adv_frame, from_=0.0001, to=10000.0, increment=0.1, textvariable=self.scale_factor, width=8).grid(row=5, column=1, sticky=tk.W)
        scale_btns = ttk.Frame(self.adv_frame)
        scale_btns.grid(row=5, column=2, sticky=tk.W, padx=10)
        ttk.Button(scale_btns, text="in→mm", command=lambda: self.scale_factor.set(25.4)).pack(side=tk.LEFT)
        ttk.Button(scale_btns, text="µm→mm", command=lambda: self.scale_factor.set(0.001)).pack(side=tk.LEFT)
        ttk.Button(scale_btns, text="m→mm", command=lambda: self.scale_factor.set(1000.0)).pack(side=tk.LEFT)
        
        ttk.Checkbutton(self.adv_frame, text="Center on origin", variable=self.center_origin).grid(row=6, column=0, sticky=tk.W)
        
        axes_frame = ttk.Frame(self.adv_frame)
        axes_frame.grid(row=6, column=1, columnspan=2, sticky=tk.W)
        ttk.Checkbutton(axes_frame, text="Flip X", variable=self.flip_x).pack(side=tk.LEFT)
        ttk.Checkbutton(axes_frame, text="Flip Y", variable=self.flip_y).pack(side=tk.LEFT)
        ttk.Checkbutton(axes_frame, text="Flip Z", variable=self.flip_z).pack(side=tk.LEFT)
        ttk.Checkbutton(axes_frame, text="Swap Y/Z", variable=self.swap_yz).pack(side=tk.LEFT, padx=10)

        # Output formatting
        ttk.Label(self.adv_frame, text="Delimiter:").grid(row=7, column=0, sticky=tk.W)
        ttk.Combobox(self.adv_frame, textvariable=self.delimiter, values=[" ", "\\t", ","], state="readonly", width=5).grid(row=7, column=1, sticky=tk.W)
        
        ttk.Label(self.adv_frame, text="Precision:").grid(row=8, column=0, sticky=tk.W)
        ttk.Spinbox(self.adv_frame, from_=2, to=8, increment=1, textvariable=self.precision, width=5).grid(row=8, column=1, sticky=tk.W)
        
        ttk.Label(self.adv_frame, text="Header:").grid(row=9, column=0, sticky=tk.W)
        ttk.Combobox(self.adv_frame, textvariable=self.header, values=["none", "count", "comment", "custom"], state="readonly", width=10).grid(row=9, column=1, sticky=tk.W)
        ttk.Entry(self.adv_frame, textvariable=self.header_text).grid(row=9, column=2, sticky=tk.W)

        ttk.Label(self.adv_frame, text="Intensity:").grid(row=10, column=0, sticky=tk.W)
        ttk.Combobox(self.adv_frame, textvariable=self.intensity, values=["none", "1.0 constant", "from Z"], state="readonly", width=15).grid(row=10, column=1, sticky=tk.W)

        ttk.Label(self.adv_frame, text="RGB:").grid(row=11, column=0, sticky=tk.W)
        ttk.Combobox(self.adv_frame, textvariable=self.rgb_var, values=["none", "white", "custom"], state="readonly", width=10).grid(row=11, column=1, sticky=tk.W)
        rgb_frame = ttk.Frame(self.adv_frame)
        rgb_frame.grid(row=11, column=2, sticky=tk.W)
        ttk.Spinbox(rgb_frame, from_=0, to=255, textvariable=self.rgb_r, width=4).pack(side=tk.LEFT)
        ttk.Spinbox(rgb_frame, from_=0, to=255, textvariable=self.rgb_g, width=4).pack(side=tk.LEFT)
        ttk.Spinbox(rgb_frame, from_=0, to=255, textvariable=self.rgb_b, width=4).pack(side=tk.LEFT)

        # Convert button
        self.convert_btn = ttk.Button(main_frame, text="Convert", command=self.start_conversion)
        self.convert_btn.pack(fill=tk.X, pady=10)
        
        self.progress = ttk.Progressbar(main_frame, mode="indeterminate")
        self.progress.pack(fill=tk.X, pady=5)
        
        # Stats panel
        self.stats = tk.Text(main_frame, height=12, state=tk.DISABLED, bg="#f0f0f0")
        self.stats.pack(fill=tk.BOTH, expand=True, pady=5)
        self.stats.tag_configure("red", foreground="red")
        
        # Preview panel
        ttk.Label(main_frame, text="Output Preview:").pack(anchor=tk.W)
        self.preview = tk.Text(main_frame, height=6, state=tk.DISABLED, bg="#f8f8f8")
        self.preview.pack(fill=tk.BOTH, expand=False, pady=5)
        
        # Status
        status_frame = ttk.Frame(self.root)
        status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        ttk.Label(status_frame, text=f"v{__version__}").pack(side=tk.LEFT, padx=5)
        self.status_lbl = ttk.Label(status_frame, text="Ready.")
        self.status_lbl.pack(side=tk.RIGHT, padx=5)
        
        # Menu
        menubar = tk.Menu(self.root)
        helpmenu = tk.Menu(menubar, tearoff=0)
        helpmenu.add_command(label="About", command=self.show_about)
        menubar.add_cascade(label="Help", menu=helpmenu)
        self.root.config(menu=menubar)
        
        # Check queue
        self.root.after(50, self.poll_queue)
        
        self.adv_visible = False

    def toggle_advanced(self):
        if self.adv_visible:
            self.adv_frame.pack_forget()
            self.adv_visible = False
        else:
            self.adv_frame.pack(fill=tk.X, pady=5, before=self.convert_btn)
            self.adv_visible = True

    def apply_preset(self):
        p = self.preset_var.get()
        if p == "uv":
            self.voxel_size.set(0.06)
        elif p == "green":
            self.voxel_size.set(0.07)
        elif p == "none":
            self.voxel_size.set(0.0)

    def browse_input(self):
        try:
            path = filedialog.askopenfilename(filetypes=[("DXF Files", "*.dxf"), ("All Files", "*.*")])
            logging.info(f"File dialog returned: {repr(path)}")
            if path:
                self.input_path.set(path)
                self.update_default_output()
        except Exception as e:
            logging.error(f"Error in file dialog: {e}")

    def update_default_output(self):
        ipath = self.input_path.get()
        if ipath:
            base, _ = os.path.splitext(ipath)
            ext = self.format_var.get()
            self.output_path.set(f"{base}.{ext}")

    def browse_output(self):
        ext = self.format_var.get()
        path = filedialog.asksaveasfilename(defaultextension=f".{ext}", filetypes=[(f"{ext.upper()} Files", f"*.{ext}")])
        if path:
            self.output_path.set(path)

    def show_about(self):
        import ezdxf
        msg = f"DXF to XYZ Converter\nVersion: {__version__}\nPython: {sys.version.split()[0]}\nezdxf: {ezdxf.__version__}\nBuilt for my friend."
        messagebox.showinfo("About", msg)

    def log_stats(self, msg, tag=None):
        self.stats.config(state=tk.NORMAL)
        if tag:
            self.stats.insert(tk.END, msg + "\n", tag)
        else:
            self.stats.insert(tk.END, msg + "\n")
        self.stats.config(state=tk.DISABLED)
        self.stats.see(tk.END)

    def start_conversion(self):
        if not self.input_path.get() or not self.output_path.get():
            messagebox.showwarning("Missing Input/Output", "Please select input and output files.")
            return
            
        self.convert_btn.config(state=tk.DISABLED)
        self.progress.start()
        self.stats.config(state=tk.NORMAL)
        self.stats.delete("1.0", tk.END)
        self.stats.config(state=tk.DISABLED)
        
        self.status_lbl.config(text="Converting...")
        self.save_settings()
        
        # Snap options
        ropts = ReaderOptions(
            spline_distance=self.curve_sagitta.get(),
            arc_distance=self.curve_sagitta.get(),
            sample_face_interior=self.sample_faces.get(),
            face_sample_density=self.face_density.get(),
            expand_blocks=self.expand_blocks.get()
        )
        popts = ProcessOptions(
            dedupe=self.dedupe.get(),
            voxel_size=self.voxel_size.get() if self.voxel_size.get() > 0 else None,
            voxel_mode=self.voxel_mode.get(),
            scale=self.scale_factor.get(),
            center_on_origin=self.center_origin.get(),
            swap_yz=self.swap_yz.get(),
            flip_x=self.flip_x.get(),
            flip_y=self.flip_y.get(),
            flip_z=self.flip_z.get()
        )
        
        wdelim = self.delimiter.get()
        if wdelim == "\\t":
            wdelim = "\t"
            
        wopts = WriterOptions(
            format=self.format_var.get(),
            delimiter=wdelim,
            precision=self.precision.get(),
            header=self.header.get(),
            header_text=self.header_text.get()
        )
        
        int_val = self.intensity.get()
        if int_val == "1.0 constant":
            wopts.intensity = 1.0
        elif int_val == "from Z":
            wopts.intensity_from_z = True
            
        rgb_v = self.rgb_var.get()
        if rgb_v == "white":
            wopts.rgb = (255, 255, 255)
        elif rgb_v == "custom":
            wopts.rgb = (self.rgb_r.get(), self.rgb_g.get(), self.rgb_b.get())
            
        inpath = self.input_path.get()
        outpath = self.output_path.get()
        
        logging.info(f"Starting conversion: {inpath} -> {outpath}")
        logging.info(f"Reader options: {ropts}")
        logging.info(f"Process options: {popts}")
        logging.info(f"Writer options: {wopts}")
        
        thread = threading.Thread(target=self.run_conversion, args=(inpath, outpath, ropts, popts, wopts))
        thread.daemon = True
        thread.start()

    def run_conversion(self, inpath, outpath, ropts, popts, wopts):
        try:
            rres = read_dxf(inpath, ropts)
            if rres.warnings:
                for w in rres.warnings:
                    logging.warning(w)
            
            pres = process(rres.points, popts)
            write_pointcloud(outpath, pres.points, wopts)
            
            self.queue.put(("success", (rres, pres, outpath)))
        except Exception as e:
            logging.exception("Conversion failed")
            self.queue.put(("error", str(e)))

    def poll_queue(self):
        try:
            msg_type, data = self.queue.get_nowait()
            if msg_type == "success":
                self.handle_success(*data)
            elif msg_type == "error":
                self.handle_error(data)
        except queue.Empty:
            pass
        self.root.after(50, self.poll_queue)

    def handle_error(self, err_msg):
        self.progress.stop()
        self.convert_btn.config(state=tk.NORMAL)
        self.status_lbl.config(text="Failed.")
        messagebox.showerror("Error", f"Conversion failed:\n{err_msg}\n\nSee log for details.")

    def handle_success(self, rres, pres, outpath):
        self.progress.stop()
        self.convert_btn.config(state=tk.NORMAL)
        self.status_lbl.config(text="Done.")
        
        # Format stats
        e_counts = "  ".join([f"{k}: {v}" for k, v in rres.entity_counts.items()])
        self.log_stats(f"Entities found: {e_counts}")
        if rres.skipped_counts:
            s_counts = "  ".join([f"{k}: {v}" for k, v in rres.skipped_counts.items()])
            self.log_stats(f"Entities skipped: {s_counts}")
            
        bmin, bmax = rres.bounds
        for i, axis in enumerate(["X", "Y", "Z"]):
            span = bmax[i] - bmin[i]
            self.log_stats(f"Bounds {axis}: {bmin[i]:.2f}  →  {bmax[i]:.2f}   span {span:.2f} (file units)")
            
        diag = ((bmax[0]-bmin[0])**2 + (bmax[1]-bmin[1])**2 + (bmax[2]-bmin[2])**2)**0.5
        self.log_stats(f"Diagonal: {diag:.2f} (file units)")
        
        for w in rres.units_warnings:
            self.log_stats(w, "red")
            
        self.log_stats(f"Points in:         {pres.count_in:,}")
        self.log_stats(f"After dedupe:      {pres.count_after_dedupe:,}")
        self.log_stats(f"After voxel thin:  {pres.count_out:,}")
        
        try:
            size = os.path.getsize(outpath)
            size_str = f"{size / 1024:.0f} KB" if size < 1024*1024 else f"{size / 1024 / 1024:.1f} MB"
            self.log_stats(f"Output written: {outpath} ({pres.count_out:,} lines, {size_str})")
        except:
            pass
            
        # Update preview
        self.preview.config(state=tk.NORMAL)
        self.preview.delete("1.0", tk.END)
        try:
            with open(outpath, "r") as f:
                lines = [next(f) for _ in range(10)]
                self.preview.insert(tk.END, "".join(lines))
        except StopIteration:
            pass
        except Exception:
            self.preview.insert(tk.END, "Failed to read preview.")
        self.preview.config(state=tk.DISABLED)

    def load_settings(self):
        if os.path.exists(SETTINGS_PATH):
            try:
                with open(SETTINGS_PATH, "r") as f:
                    s = json.load(f)
                self.preset_var.set(s.get("preset", "green"))
                self.curve_sagitta.set(s.get("curve_sagitta", 0.05))
                self.sample_faces.set(s.get("sample_faces", False))
                self.expand_blocks.set(s.get("expand_blocks", True))
                self.dedupe.set(s.get("dedupe", True))
                self.voxel_size.set(s.get("voxel_size", 0.06))
                self.voxel_mode.set(s.get("voxel_mode", "first"))
                self.scale_factor.set(s.get("scale_factor", 1.0))
                self.center_origin.set(s.get("center_origin", False))
                self.delimiter.set(s.get("delimiter", " "))
                self.precision.set(s.get("precision", 4))
                self.header.set(s.get("header", "none"))
                self.intensity.set(s.get("intensity", "none"))
            except Exception:
                pass

    def save_settings(self):
        s = {
            "preset": self.preset_var.get(),
            "curve_sagitta": self.curve_sagitta.get(),
            "sample_faces": self.sample_faces.get(),
            "expand_blocks": self.expand_blocks.get(),
            "dedupe": self.dedupe.get(),
            "voxel_size": self.voxel_size.get(),
            "voxel_mode": self.voxel_mode.get(),
            "scale_factor": self.scale_factor.get(),
            "center_origin": self.center_origin.get(),
            "delimiter": self.delimiter.get(),
            "precision": self.precision.get(),
            "header": self.header.get(),
            "intensity": self.intensity.get()
        }
        try:
            with open(SETTINGS_PATH, "w") as f:
                json.dump(s, f)
        except Exception:
            pass

def launch_gui():
    global HAS_DND
    root = None
    if HAS_DND:
        try:
            root = TkinterDnD.Tk()
        except Exception as e:
            logging.warning(f"Failed to initialize TkinterDnD: {e}. Falling back to standard Tk.")
            HAS_DND = False
            # Clean up the broken default root if it was partially created
            try:
                if tk._default_root:
                    tk._default_root.destroy()
            except Exception:
                pass
    
    if root is None:
        root = tk.Tk()
        HAS_DND = False
        
    app = ConverterApp(root)
    root.mainloop()

if __name__ == "__main__":
    launch_gui()
