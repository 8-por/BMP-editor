import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from BMPParser import BMPParser
from PIL import Image, ImageTk   # pip install pillow

class BMPApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("BMP Inspector")
        self.geometry("540x420")
        self._build_widgets()

    def _build_widgets(self):
        ttk.Button(self, text="Open BMP…", command=self.open_file).pack(pady=6)
        self.tree = ttk.Treeview(self, columns=("f", "v"), show="headings")
        for c, w in [("Field", 160), ("Value", 320)]:
            self.tree.heading(c[0].lower(), text=c)
            self.tree.column(c[0].lower(), width=w, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=10, pady=(0,10))

        self.thumb = ttk.Label(self)
        self.thumb.pack()

    def open_file(self):
        path = filedialog.askopenfilename(
            title="Choose a BMP",
            filetypes=[("Bitmap Images", "*.bmp;*.dib"), ("All files", "*.*")]
        )
        if not path:
            return
        try:
            p = BMPParser(path)
            p.parse()
            self.populate_table(p.get_summary())
            self.show_thumbnail(path)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def populate_table(self, data):
        self.tree.delete(*self.tree.get_children())
        for k, v in data.items():
            self.tree.insert("", "end", values=(k, v))

    def show_thumbnail(self, path):
        img = Image.open(path)
        img.thumbnail((256, 256))
        self.photo = ImageTk.PhotoImage(img)
        self.thumb.configure(image=self.photo)

if __name__ == "__main__":
    BMPApp().mainloop()
