"""QR Code Generator with a centered logo.

Style follows Reference Images/: rounded modules, rounded finder eyes,
black on white, and a rounded-square plate holding the logo in the middle.
"""

import math
import os
import re
import sys
import tkinter as tk
from tkinter import filedialog, ttk

import qrcode
from PIL import Image, ImageDraw, ImageTk
from qrcode.constants import ERROR_CORRECT_H
from qrcode.image.styledpil import StyledPilImage
from qrcode.image.styles.colormasks import SolidFillColorMask
from qrcode.image.styles.moduledrawers.pil import RoundedModuleDrawer

# ---------------------------------------------------------------- rendering

TARGET_PX = 3000          # approximate edge length of the saved PNG
LOGO_RATIO = 0.22         # default logo plate width, as a fraction of the QR width
LOGO_MIN = 0.10           # slider floor
LOGO_MAX = 0.30           # slider ceiling
LOGO_SAFE = 0.28          # past this, short URLs start failing to scan
PLATE_PADDING = 0.09      # white margin inside the plate, as a fraction of it
PLATE_RADIUS = 0.22       # plate corner radius, as a fraction of the plate


def _rounded_mask(size, radius):
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size - 1, size - 1), radius, fill=255)
    return mask


def _fit(image, box):
    """Scale an image to fit inside a box*box square, preserving aspect ratio."""
    w, h = image.size
    scale = box / max(w, h)
    return image.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.LANCZOS)


def build_qr(data, logo_path=None, logo_ratio=LOGO_RATIO):
    qr = qrcode.QRCode(error_correction=ERROR_CORRECT_H, border=4)
    qr.add_data(data)
    qr.make(fit=True)

    modules = qr.modules_count + qr.border * 2
    qr.box_size = max(8, math.ceil(TARGET_PX / modules))

    img = qr.make_image(
        image_factory=StyledPilImage,
        module_drawer=RoundedModuleDrawer(radius_ratio=1),
        color_mask=SolidFillColorMask(back_color=(255, 255, 255), front_color=(0, 0, 0)),
    ).convert("RGBA")

    if logo_path:
        img = _place_logo(img, logo_path, logo_ratio)
    return img


def _place_logo(qr_img, logo_path, logo_ratio=LOGO_RATIO):
    logo = Image.open(logo_path).convert("RGBA")

    plate_size = int(round(qr_img.width * logo_ratio))
    radius = int(round(plate_size * PLATE_RADIUS))
    inner = int(round(plate_size * (1 - PLATE_PADDING * 2)))

    plate = Image.new("RGBA", (plate_size, plate_size), (255, 255, 255, 255))
    plate.putalpha(_rounded_mask(plate_size, radius))

    logo = _fit(logo, inner)
    plate.alpha_composite(
        logo,
        ((plate_size - logo.width) // 2, (plate_size - logo.height) // 2),
    )

    offset = (qr_img.width - plate_size) // 2
    qr_img.alpha_composite(plate, (offset, offset))
    return qr_img


def suggest_filename(url):
    """https://thequing.github.io/Portfolio/ -> https_thequing_github_io_Portfolio_.png"""
    name = re.sub(r"[^A-Za-z0-9]+", "_", url.strip()).strip("_")
    return (name[:80] or "qrcode") + ".png"


# ---------------------------------------------------------------------- UI

BG = "#14161a"
CARD = "#1d2026"
FG = "#e8eaed"
MUTED = "#8b919b"
ACCENT = "#f08a3c"
DANGER = "#ff7a6b"
CAUTION = "#e8b23c"
PREVIEW_PX = 300


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("QR Code Generator")
        self.configure(bg=BG)
        self.resizable(False, False)

        self.qr_image = None        # full-resolution PIL image
        self._preview_ref = None    # keep a reference so Tk does not drop it
        self._rerender_job = None   # pending debounced re-render from the slider

        self._build_styles()
        self._build_widgets()
        self._center()

    # -- chrome ----------------------------------------------------------
    def _build_styles(self):
        s = ttk.Style(self)
        s.theme_use("clam")
        s.configure("TFrame", background=BG)
        s.configure("TLabel", background=BG, foreground=FG, font=("Segoe UI", 10))
        s.configure("Title.TLabel", font=("Segoe UI Semibold", 17), foreground=FG)
        s.configure("Muted.TLabel", foreground=MUTED, font=("Segoe UI", 9))
        s.configure(
            "TEntry",
            fieldbackground=CARD, background=CARD, foreground=FG,
            insertcolor=FG, bordercolor="#2c313a", lightcolor="#2c313a",
            darkcolor="#2c313a", padding=7,
        )
        s.map("TEntry", bordercolor=[("focus", ACCENT)], lightcolor=[("focus", ACCENT)])
        s.configure(
            "Accent.TButton",
            background=ACCENT, foreground="#1a1005", font=("Segoe UI Semibold", 11),
            borderwidth=0, focuscolor=ACCENT, padding=(18, 10),
        )
        s.map("Accent.TButton", background=[("active", "#ffa159")])
        s.configure(
            "Ghost.TButton",
            background=CARD, foreground=FG, font=("Segoe UI", 10),
            borderwidth=0, focuscolor=CARD, padding=(16, 9),
        )
        s.map("Ghost.TButton", background=[("active", "#2a2f38")])
        s.configure(
            "Horizontal.TScale",
            background=ACCENT, troughcolor=CARD, bordercolor="#2c313a",
            lightcolor="#2c313a", darkcolor="#2c313a",
            sliderthickness=18, sliderlength=24, troughrelief="flat",
        )
        s.map("Horizontal.TScale",
              background=[("disabled", "#3a3f48"), ("active", "#ffa159")])

    def _build_widgets(self):
        pad = ttk.Frame(self, padding=(26, 22, 26, 22))
        pad.grid(sticky="nsew")

        ttk.Label(pad, text="QR Code Generator", style="Title.TLabel").grid(
            row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(pad, text="Paste a link, pick a logo, hit Make.", style="Muted.TLabel").grid(
            row=1, column=0, columnspan=3, sticky="w", pady=(2, 18))

        ttk.Label(pad, text="URL or text").grid(row=2, column=0, columnspan=3, sticky="w")
        self.url_var = tk.StringVar()
        url_entry = ttk.Entry(pad, textvariable=self.url_var, width=46)
        url_entry.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(5, 14))
        url_entry.focus_set()
        url_entry.bind("<Return>", lambda _e: self.on_make())

        ttk.Label(pad, text="Logo  (optional)").grid(row=4, column=0, columnspan=3, sticky="w")
        self.logo_var = tk.StringVar()
        self.logo_var.trace_add("write", lambda *_: self._sync_slider_state())
        ttk.Entry(pad, textvariable=self.logo_var, width=32).grid(
            row=5, column=0, columnspan=2, sticky="ew", pady=(5, 14))
        ttk.Button(pad, text="Browse...", style="Ghost.TButton", command=self.on_browse).grid(
            row=5, column=2, sticky="ew", padx=(8, 0), pady=(5, 14))

        # -- logo size slider --
        head = ttk.Frame(pad)
        head.grid(row=6, column=0, columnspan=3, sticky="ew")
        self.size_caption = ttk.Label(head, text="Logo size")
        self.size_caption.grid(row=0, column=0, sticky="w")
        self.size_value = ttk.Label(head, text="", style="Muted.TLabel")
        self.size_value.grid(row=0, column=1, sticky="e")
        head.columnconfigure(0, weight=1)

        self.ratio_var = tk.DoubleVar(value=LOGO_RATIO)
        self.slider = ttk.Scale(pad, from_=LOGO_MIN, to=LOGO_MAX,
                                variable=self.ratio_var, command=self.on_ratio_change)
        self.slider.grid(row=7, column=0, columnspan=3, sticky="ew", pady=(6, 16))

        ttk.Button(pad, text="Make QR Code", style="Accent.TButton", command=self.on_make).grid(
            row=8, column=0, columnspan=3, sticky="ew")

        self.status = ttk.Label(pad, text="", style="Muted.TLabel", wraplength=420)
        self.status.grid(row=9, column=0, columnspan=3, sticky="w", pady=(12, 0))

        # -- preview area, hidden until a code exists --
        self.result = ttk.Frame(pad)
        self.result.grid(row=10, column=0, columnspan=3, sticky="ew")
        self.result.grid_remove()

        self.canvas = tk.Canvas(self.result, width=PREVIEW_PX, height=PREVIEW_PX,
                                bg=CARD, highlightthickness=0)
        self.canvas.grid(row=0, column=0, columnspan=2, pady=(14, 14))

        ttk.Button(self.result, text="Retry", style="Ghost.TButton",
                   command=self.on_retry).grid(row=1, column=0, sticky="ew", padx=(0, 5))
        ttk.Button(self.result, text="Save PNG", style="Accent.TButton",
                   command=self.on_save).grid(row=1, column=1, sticky="ew", padx=(5, 0))

        self.result.columnconfigure(0, weight=1)
        self.result.columnconfigure(1, weight=1)
        pad.columnconfigure(0, weight=1)
        pad.columnconfigure(1, weight=1)

        self._sync_slider_state()

    def _center(self):
        self.update_idletasks()
        x = (self.winfo_screenwidth() - self.winfo_width()) // 2
        y = (self.winfo_screenheight() - self.winfo_height()) // 3
        self.geometry(f"+{max(0, x)}+{max(0, y)}")

    def _say(self, text, error=False):
        self.status.configure(text=text, foreground=DANGER if error else MUTED)

    # -- logo size slider ------------------------------------------------
    def _sync_slider_state(self):
        """The slider only means anything once a logo is chosen."""
        has_logo = bool(self.logo_var.get().strip())
        self.slider.state(["!disabled"] if has_logo else ["disabled"])
        self.size_caption.configure(foreground=FG if has_logo else "#4e545e")
        self.on_ratio_change()
        if not has_logo:
            self.size_value.configure(text="no logo", foreground="#4e545e")

    def on_ratio_change(self, _event=None):
        ratio = self.ratio_var.get()
        risky = ratio > LOGO_SAFE
        self.size_value.configure(
            text=f"{ratio * 100:.0f}% of the code" + ("  -  may not scan" if risky else ""),
            foreground=CAUTION if risky else MUTED,
        )

        if self._rerender_job is not None:
            self.after_cancel(self._rerender_job)
            self._rerender_job = None
        if self.qr_image is not None and self.logo_var.get().strip():
            self._rerender_job = self.after(120, lambda: self._generate(quiet=True))

    # -- actions ---------------------------------------------------------
    def on_browse(self):
        start = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Reference Images")
        path = filedialog.askopenfilename(
            title="Choose a logo",
            initialdir=start if os.path.isdir(start) else os.path.expanduser("~"),
            filetypes=[("Images", "*.png *.jpg *.jpeg *.webp *.bmp *.gif"), ("All files", "*.*")],
        )
        if path:
            self.logo_var.set(path)

    def on_make(self):
        self._generate()

    def _generate(self, quiet=False):
        """quiet=True is the slider re-render: no status chatter, no window jump."""
        self._rerender_job = None
        data = self.url_var.get().strip()
        if not data:
            self._say("Enter a URL or some text first.", error=True)
            return

        logo = self.logo_var.get().strip().strip('"')
        if logo and not os.path.isfile(logo):
            self._say("Logo not found: " + logo, error=True)
            return

        if not quiet:
            self._say("Generating...")
            self.update_idletasks()
        try:
            self.qr_image = build_qr(data, logo or None, self.ratio_var.get())
        except Exception as exc:                  # noqa: BLE001 - surfaced in the UI
            self.qr_image = None
            self.result.grid_remove()
            self._say("Could not generate: " + str(exc), error=True)
            self._center()
            return

        preview = self.qr_image.convert("RGB").resize((PREVIEW_PX, PREVIEW_PX), Image.LANCZOS)
        self._preview_ref = ImageTk.PhotoImage(preview)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor="nw", image=self._preview_ref)

        was_hidden = not self.result.winfo_ismapped()
        self.result.grid()
        self._say(f"Ready - {self.qr_image.width} x {self.qr_image.height} px.")
        if was_hidden or not quiet:
            self._center()

    def on_retry(self):
        if self._rerender_job is not None:
            self.after_cancel(self._rerender_job)
            self._rerender_job = None
        self.qr_image = None
        self._preview_ref = None
        self.canvas.delete("all")
        self.result.grid_remove()
        self._say("")
        self._center()

    def on_save(self):
        if self.qr_image is None:
            return
        path = filedialog.asksaveasfilename(
            title="Save QR code",
            defaultextension=".png",
            initialfile=suggest_filename(self.url_var.get()),
            filetypes=[("PNG image", "*.png")],
        )
        if not path:
            return
        try:
            self.qr_image.convert("RGB").save(path, "PNG")
        except Exception as exc:                  # noqa: BLE001 - surfaced in the UI
            self._say("Could not save: " + str(exc), error=True)
            return
        self._say("Saved to " + path)


def main():
    App().mainloop()


if __name__ == "__main__":
    sys.exit(main())
