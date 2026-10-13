import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
import yt_dlp
import threading
import os
import sys
import re
import subprocess
import urllib.request
from pathlib import Path
from io import BytesIO
from PIL import Image


def resource_path(relative: str) -> str:
    """Return the absolute path to a bundled resource (works with PyInstaller)."""
    base = getattr(sys, "_MEIPASS", Path(__file__).parent)
    return str(Path(base) / relative)

# ─── Thème ────────────────────────────────────────────────────────────────────
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ─── Palette ──────────────────────────────────────────────────────────────────
BG_DARK     = "#0f1117"
CARD_BG     = "#16181f"
CARD_BG2    = "#1c1f2b"
BORDER      = "#252836"
ACCENT      = "#4f7ef8"
ACCENT_HVR  = "#3d6ae0"
MUTED       = "#4b5263"
TEXT_DIM    = "#8b92a5"
SUCCESS     = "#34d399"
ERROR       = "#f87171"
WARN        = "#fbbf24"
INFO        = "#60a5fa"

BTN_SEC_FG  = ("#dde3f0", "#252836")
BTN_SEC_TXT = ("#0f1117", "#c8cdd8")
BTN_SEC_HVR = ("#c8cdd8", "#2e3347")

THUMB_W, THUMB_H = 160, 90

# ─── Constantes ───────────────────────────────────────────────────────────────
QUALITY_MAP = {
    "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
    "720p":  "bestvideo[height<=720]+bestaudio/best[height<=720]",
    "480p":  "bestvideo[height<=480]+bestaudio/best[height<=480]",
    "360p":  "bestvideo[height<=360]+bestaudio/best[height<=360]",
}

YOUTUBE_RE = re.compile(
    r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/'
    r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
)


# ─── Helpers ──────────────────────────────────────────────────────────────────
def fmt_speed(b: float) -> str:
    if b >= 1 << 20:
        return f"{b / (1 << 20):.1f} MB/s"
    return f"{b / 1024:.1f} KB/s"


def fmt_duration(sec: int) -> str:
    sec = int(sec)
    h, rem = divmod(sec, 3600)
    m, s   = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def fmt_eta(sec) -> str:
    if sec is None:
        return ""
    sec = int(sec)
    if sec >= 3600:
        return f"ETA {sec // 3600}h{(sec % 3600) // 60:02d}m"
    if sec >= 60:
        return f"ETA {sec // 60}m{sec % 60:02d}s"
    return f"ETA {sec}s"


def is_valid_url(url: str) -> bool:
    return bool(YOUTUBE_RE.match(url.strip()))


def open_folder(path: str):
    subprocess.run(["open", path], check=False)


def load_thumbnail(url: str) -> ctk.CTkImage | None:
    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = resp.read()
        img = Image.open(BytesIO(data)).convert("RGB")
        img = img.resize((THUMB_W, THUMB_H), Image.LANCZOS)
        return ctk.CTkImage(light_image=img, dark_image=img, size=(THUMB_W, THUMB_H))
    except Exception:
        return None


def bind_mousewheel(widget):
    """Bind la molette souris sur un CTkScrollableFrame (macOS + Linux/Win)."""
    canvas = getattr(widget, "_parent_canvas", None)
    if canvas is None:
        return

    def _scroll(event):
        if sys.platform == "darwin":
            # macOS : delta = petites valeurs (1, 2, 3...), pas de multiples de 120
            canvas.yview_scroll(int(-event.delta), "units")
        elif event.delta:
            # Windows
            canvas.yview_scroll(int(-event.delta / 120), "units")
        elif event.num == 4:
            canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            canvas.yview_scroll(1, "units")

    canvas.bind_all("<MouseWheel>", _scroll, add="+")
    # Linux
    canvas.bind_all("<Button-4>", _scroll, add="+")
    canvas.bind_all("<Button-5>", _scroll, add="+")


# ─── Application ──────────────────────────────────────────────────────────────
class YouTubeDownloader:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("YT Downloader")
        self.root.geometry("860x700")
        self.root.minsize(760, 600)
        self.root.resizable(True, True)
        self.root.configure(fg_color=BG_DARK)

        # Icône de la fenêtre
        _icon = resource_path("logo.ico")
        if os.path.exists(_icon):
            try:
                self.root.iconbitmap(_icon)
            except Exception:
                pass

        # Variables
        self.url_var       = tk.StringVar()
        self.download_path = tk.StringVar(value=str(Path.home() / "Downloads"))
        self.format_var    = tk.StringVar(value="Vidéo MP4")
        self.quality_var   = tk.StringVar(value="720p")

        # État interne
        self._debounce_id  = None
        self._current_info = None
        self._thumb_image  = None
        self.download_items = []

        self._build_ui()
        self.url_var.trace_add("write", self._on_url_change)
        self.root.bind("<Return>", lambda _: self.start_download())
        self.root.bind("<Command-d>", lambda _: self.start_download())

    # ─────────────────────────────────────────────────────────────────────────
    #  Construction UI
    # ─────────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=1)

        # En-tête
        self._build_header()

        # Zone scrollable principale
        self.scroll = ctk.CTkScrollableFrame(
            self.root,
            fg_color="transparent",
            scrollbar_button_color=MUTED,
            scrollbar_button_hover_color=ACCENT,
        )
        self.scroll.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        self.scroll.grid_columnconfigure(0, weight=1)

        # Activer la molette
        bind_mousewheel(self.scroll)

        # Sections
        self._build_url_section(self.scroll)
        self._build_options_section(self.scroll)
        self._build_download_btn(self.scroll)
        self._build_queue_section(self.scroll)

    # ─ En-tête ───────────────────────────────────────────────────────────────

    def _build_header(self):
        header = ctk.CTkFrame(self.root, fg_color=CARD_BG, corner_radius=0, height=64)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        header.grid_propagate(False)

        inner = ctk.CTkFrame(header, fg_color="transparent")
        inner.place(relx=0, rely=0.5, anchor="w", x=32)

        ctk.CTkLabel(
            inner,
            text="YT Downloader",
            font=ctk.CTkFont(family="SF Pro Display", size=18, weight="bold"),
            text_color="#f0f2f8",
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            inner,
            text="Téléchargez des vidéos et de la musique",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_DIM,
        ).grid(row=1, column=0, sticky="w")

        # Séparateur bas du header
        sep = tk.Frame(self.root, height=1, bg=BORDER)
        sep.grid(row=0, column=0, sticky="sew")

    # ─ Section URL + prévisualisation ─────────────────────────────────────────

    def _build_url_section(self, parent):
        self._section_label(parent, 0, "Lien YouTube")

        card = self._card(parent, 1)

        # Champ URL
        row_url = ctk.CTkFrame(card, fg_color="transparent")
        row_url.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 6))
        row_url.grid_columnconfigure(0, weight=1)

        self.url_entry = ctk.CTkEntry(
            row_url,
            textvariable=self.url_var,
            placeholder_text="https://www.youtube.com/watch?v=...",
            height=40,
            font=ctk.CTkFont(size=13),
            corner_radius=8,
            border_color=BORDER,
            fg_color=CARD_BG2,
            text_color="#e2e6f0",
        )
        self.url_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self._sec_btn(row_url, "Coller", self._paste_url, width=80).grid(
            row=0, column=1, padx=(0, 6)
        )
        self._sec_btn(row_url, "Effacer", self._clear_url, width=72).grid(
            row=0, column=2
        )

        # Erreur inline
        self.error_label = ctk.CTkLabel(
            card,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=ERROR,
            anchor="w",
        )
        self.error_label.grid(row=1, column=0, sticky="ew", padx=22, pady=(0, 4))

        # Preview
        preview = ctk.CTkFrame(card, fg_color=CARD_BG2, corner_radius=8)
        preview.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 18))
        preview.grid_columnconfigure(1, weight=1)

        # Placeholder miniature
        self.thumb_label = ctk.CTkLabel(
            preview,
            text="",
            width=THUMB_W,
            height=THUMB_H,
            fg_color=BORDER,
            corner_radius=6,
        )
        self.thumb_label.grid(row=0, column=0, rowspan=3, padx=(14, 16), pady=14)

        self.preview_title = ctk.CTkLabel(
            preview,
            text="Collez un lien pour afficher un aperçu",
            font=ctk.CTkFont(size=13, weight="bold"),
            wraplength=380,
            anchor="w",
            justify="left",
            text_color="#dde3f0",
        )
        self.preview_title.grid(row=0, column=1, sticky="w", pady=(16, 2))

        self.preview_meta = ctk.CTkLabel(
            preview,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=TEXT_DIM,
            anchor="w",
        )
        self.preview_meta.grid(row=1, column=1, sticky="w")

        self.preview_spinner = ctk.CTkLabel(
            preview,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=INFO,
            anchor="w",
        )
        self.preview_spinner.grid(row=2, column=1, sticky="w", pady=(0, 14))

    # ─ Section options ────────────────────────────────────────────────────────

    def _build_options_section(self, parent):
        self._section_label(parent, 2, "Options")

        card = self._card(parent, 3)
        card.grid_columnconfigure((0, 1), weight=1)

        # Format
        ctk.CTkLabel(
            card, text="Format",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=TEXT_DIM,
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(18, 4))

        self.format_seg = ctk.CTkSegmentedButton(
            card,
            values=["Vidéo MP4", "Audio MP3"],
            variable=self.format_var,
            command=self._on_format_change,
            font=ctk.CTkFont(size=12),
            selected_color=ACCENT,
            selected_hover_color=ACCENT_HVR,
            unselected_color=CARD_BG2,
            unselected_hover_color=BORDER,
            fg_color=CARD_BG2,
            border_width=1,
        )
        self.format_seg.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 18))

        # Qualité
        self.quality_label = ctk.CTkLabel(
            card, text="Qualité vidéo",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=TEXT_DIM,
        )
        self.quality_label.grid(row=0, column=1, sticky="w", padx=20, pady=(18, 4))

        self.quality_seg = ctk.CTkSegmentedButton(
            card,
            values=["1080p", "720p", "480p", "360p"],
            variable=self.quality_var,
            font=ctk.CTkFont(size=12),
            selected_color=ACCENT,
            selected_hover_color=ACCENT_HVR,
            unselected_color=CARD_BG2,
            unselected_hover_color=BORDER,
            fg_color=CARD_BG2,
            border_width=1,
        )
        self.quality_seg.grid(row=1, column=1, sticky="ew", padx=20, pady=(0, 18))

        # Séparateur
        sep = tk.Frame(card, height=1, bg=BORDER)
        sep.grid(row=2, column=0, columnspan=2, sticky="ew", padx=20)

        # Dossier
        ctk.CTkLabel(
            card, text="Dossier de destination",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=TEXT_DIM,
        ).grid(row=3, column=0, columnspan=2, sticky="w", padx=20, pady=(14, 4))

        path_row = ctk.CTkFrame(card, fg_color="transparent")
        path_row.grid(row=4, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 18))
        path_row.grid_columnconfigure(0, weight=1)

        self.path_entry = ctk.CTkEntry(
            path_row,
            textvariable=self.download_path,
            height=38,
            font=ctk.CTkFont(size=12),
            corner_radius=8,
            border_color=BORDER,
            fg_color=CARD_BG2,
            text_color="#e2e6f0",
        )
        self.path_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self._sec_btn(path_row, "Parcourir", self._browse_folder, width=100).grid(
            row=0, column=1
        )

    # ─ Bouton principal ───────────────────────────────────────────────────────

    def _build_download_btn(self, parent):
        self.download_btn = ctk.CTkButton(
            parent,
            text="Télécharger",
            command=self.start_download,
            height=48,
            font=ctk.CTkFont(size=15, weight="bold"),
            corner_radius=10,
            fg_color=ACCENT,
            hover_color=ACCENT_HVR,
            text_color="white",
        )
        self.download_btn.grid(row=4, column=0, sticky="ew", padx=28, pady=(14, 6))

    # ─ Section file de téléchargements ───────────────────────────────────────

    def _build_queue_section(self, parent):
        self._section_label(parent, 5, "Téléchargements")

        card = self._card(parent, 6)
        card.configure(fg_color="transparent")

        self.queue_frame = card
        self.queue_frame.grid_columnconfigure(0, weight=1)

        self.queue_placeholder = ctk.CTkLabel(
            self.queue_frame,
            text="Aucun téléchargement — les éléments apparaîtront ici",
            font=ctk.CTkFont(size=12),
            text_color=MUTED,
        )
        self.queue_placeholder.grid(row=0, column=0, pady=24)

    # ─────────────────────────────────────────────────────────────────────────
    #  Composants réutilisables
    # ─────────────────────────────────────────────────────────────────────────

    def _section_label(self, parent, row: int, text: str):
        ctk.CTkLabel(
            parent,
            text=text.upper(),
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color=MUTED,
        ).grid(row=row, column=0, sticky="w", padx=30, pady=(20, 4))

    def _card(self, parent, row: int) -> ctk.CTkFrame:
        card = ctk.CTkFrame(
            parent,
            fg_color=CARD_BG,
            corner_radius=12,
            border_width=1,
            border_color=BORDER,
        )
        card.grid(row=row, column=0, sticky="ew", padx=20, pady=(0, 2))
        card.grid_columnconfigure(0, weight=1)
        return card

    def _sec_btn(self, parent, text: str, cmd, width: int = 90) -> ctk.CTkButton:
        return ctk.CTkButton(
            parent,
            text=text,
            command=cmd,
            width=width,
            height=40,
            corner_radius=8,
            fg_color=BTN_SEC_FG,
            text_color=BTN_SEC_TXT,
            hover_color=BTN_SEC_HVR,
            font=ctk.CTkFont(size=12),
        )

    # ─────────────────────────────────────────────────────────────────────────
    #  Logique URL / debounce
    # ─────────────────────────────────────────────────────────────────────────

    def _on_url_change(self, *_):
        if self._debounce_id:
            self.root.after_cancel(self._debounce_id)
        url = self.url_var.get().strip()
        self._set_error("")
        if not url:
            self._reset_preview()
            return
        if not is_valid_url(url):
            self._set_error("URL non reconnue — vérifiez le lien.")
            self._reset_preview()
            return
        self._debounce_id = self.root.after(800, lambda: self._fetch_info(url))

    def _fetch_info(self, url: str):
        self.preview_spinner.configure(text="Récupération en cours...")
        self._current_info = None

        def worker():
            try:
                opts = {"quiet": True, "no_warnings": True}
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                self.root.after(0, lambda: self._apply_info(info, url))
            except Exception as exc:
                # `exc` est supprimée à la sortie du bloc except :
                # on fige le message dans une variable normale.
                msg = str(exc)
                self.root.after(0, lambda m=msg: self._apply_info_error(m))

        threading.Thread(target=worker, daemon=True).start()

    def _apply_info(self, info: dict, url: str):
        if url != self.url_var.get().strip():
            return
        self._current_info = info
        title    = info.get("title", "Titre inconnu")
        duration = fmt_duration(info.get("duration", 0)) if info.get("duration") else "—"
        uploader = info.get("uploader") or info.get("channel") or "Inconnu"

        self.preview_title.configure(text=title)
        self.preview_meta.configure(text=f"{duration}  ·  {uploader}")
        self.preview_spinner.configure(text="")
        self._set_error("")

        thumb_url = (
            info.get("thumbnail")
            or (info.get("thumbnails") or [{}])[-1].get("url")
        )
        if thumb_url:
            threading.Thread(
                target=self._load_and_set_thumb, args=(thumb_url,), daemon=True
            ).start()

    def _apply_info_error(self, msg: str):
        self.preview_spinner.configure(text="")
        self._set_error(f"Impossible de récupérer les infos : {msg[:80]}")

    def _load_and_set_thumb(self, url: str):
        img = load_thumbnail(url)
        if img:
            self._thumb_image = img
            self.root.after(0, lambda: self.thumb_label.configure(
                image=img, text="", fg_color="transparent"
            ))

    # ─────────────────────────────────────────────────────────────────────────
    #  Helpers UI
    # ─────────────────────────────────────────────────────────────────────────

    def _reset_preview(self):
        self._current_info = None
        self._thumb_image  = None
        self.thumb_label.configure(image=None, text="", fg_color=BORDER)
        self.preview_title.configure(text="Collez un lien pour afficher un aperçu")
        self.preview_meta.configure(text="")
        self.preview_spinner.configure(text="")

    def _set_error(self, msg: str):
        self.error_label.configure(text=msg)

    def _paste_url(self):
        try:
            self.url_var.set(self.root.clipboard_get().strip())
        except tk.TclError:
            pass

    def _clear_url(self):
        self.url_var.set("")

    def _browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.download_path.set(folder)

    def _on_format_change(self, value: str):
        is_video = value == "Vidéo MP4"
        self.quality_seg.configure(state="normal" if is_video else "disabled")
        self.quality_label.configure(
            text_color=TEXT_DIM if is_video else MUTED
        )

    # ─────────────────────────────────────────────────────────────────────────
    #  Téléchargement
    # ─────────────────────────────────────────────────────────────────────────

    def start_download(self):
        url = self.url_var.get().strip()
        if not url:
            self._set_error("Veuillez entrer un lien YouTube.")
            return
        if not is_valid_url(url):
            self._set_error("URL invalide — vérifiez le lien.")
            return
        if not os.path.exists(self.download_path.get()):
            self._set_error("Le dossier de destination n'existe pas.")
            return

        self._set_error("")
        self.download_btn.configure(state="disabled", text="Préparation...")

        title = (self._current_info or {}).get("title", "Chargement...")
        item  = self._create_queue_item(title, url)

        # Lecture des variables Tk dans le thread principal (pas dans le worker)
        dest        = self.download_path.get()
        is_audio    = self.format_var.get() == "Audio MP3"
        quality     = self.quality_var.get()
        known_info  = self._current_info

        def run():
            try:
                if not known_info:
                    opts = {"quiet": True, "no_warnings": True}
                    with yt_dlp.YoutubeDL(opts) as ydl:
                        info = ydl.extract_info(url, download=False)
                    real_title = info.get("title", "Vidéo YouTube")
                    self.root.after(0, lambda t=real_title: self._update_item_title(item, t))

                self.root.after(0, lambda: self._item_set_status(item, "En cours...", WARN))

                ydl_opts = {
                    "quiet":          True,
                    "no_warnings":    True,
                    "outtmpl":        os.path.join(dest, "%(title)s.%(ext)s"),
                    "progress_hooks": [lambda d: self._progress_hook(d, item)],
                }

                if is_audio:
                    ydl_opts["format"] = "bestaudio/best"
                    ydl_opts["postprocessors"] = [{
                        "key":              "FFmpegExtractAudio",
                        "preferredcodec":   "mp3",
                        "preferredquality": "192",
                    }]
                else:
                    ydl_opts["format"] = QUALITY_MAP.get(quality, QUALITY_MAP["720p"])
                    ydl_opts["merge_output_format"] = "mp4"
                    ydl_opts["postprocessors"] = [{
                        "key":             "FFmpegVideoRemuxer",
                        "preferedformat":  "mp4",
                    }]

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])

                self.root.after(0, lambda: self._item_finished(item, dest))

            except Exception as exc:
                # `exc` n'existe plus après le bloc except : on copie le message.
                msg = str(exc)[:120]
                self.root.after(0, lambda m=msg: self._item_error(item, m))

            finally:
                self.root.after(0, lambda: self.download_btn.configure(
                    state="normal", text="Télécharger"
                ))

        threading.Thread(target=run, daemon=True).start()

    # ─────────────────────────────────────────────────────────────────────────
    #  Gestion de la file
    # ─────────────────────────────────────────────────────────────────────────

    def _create_queue_item(self, title: str, url: str) -> dict:
        if self.queue_placeholder.winfo_exists():
            self.queue_placeholder.grid_remove()

        row = len(self.download_items)

        frame = ctk.CTkFrame(
            self.queue_frame,
            fg_color=CARD_BG,
            corner_radius=10,
            border_width=1,
            border_color=BORDER,
        )
        frame.grid(row=row, column=0, sticky="ew", padx=20, pady=(0, 6))
        frame.grid_columnconfigure(0, weight=1)

        # Titre + bouton supprimer
        short = title[:72] + "..." if len(title) > 72 else title
        title_lbl = ctk.CTkLabel(
            frame,
            text=short,
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w",
            text_color="#dde3f0",
        )
        title_lbl.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 4))

        remove_btn = ctk.CTkButton(
            frame,
            text="x",
            width=24,
            height=24,
            corner_radius=6,
            fg_color="transparent",
            text_color=MUTED,
            hover_color=BORDER,
            font=ctk.CTkFont(size=11),
            command=lambda f=frame: self._remove_item(f),
        )
        remove_btn.grid(row=0, column=1, sticky="e", padx=(0, 10), pady=(12, 0))

        # Barre de progression
        bar = ctk.CTkProgressBar(
            frame,
            height=6,
            corner_radius=3,
            fg_color=BORDER,
            progress_color=ACCENT,
        )
        bar.grid(row=1, column=0, columnspan=2, sticky="ew", padx=14, pady=(2, 4))
        bar.set(0)

        # Ligne infos
        info_row = ctk.CTkFrame(frame, fg_color="transparent")
        info_row.grid(row=2, column=0, columnspan=2, sticky="ew", padx=14, pady=(0, 4))
        info_row.grid_columnconfigure(0, weight=1)

        pct_lbl = ctk.CTkLabel(
            info_row,
            text="0%",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=TEXT_DIM,
        )
        pct_lbl.grid(row=0, column=0, sticky="w")

        speed_lbl = ctk.CTkLabel(
            info_row,
            text="Préparation...",
            font=ctk.CTkFont(size=11),
            text_color=MUTED,
        )
        speed_lbl.grid(row=0, column=1, sticky="e")

        # Statut + bouton Ouvrir
        status_lbl = ctk.CTkLabel(
            frame,
            text="En attente",
            font=ctk.CTkFont(size=11),
            text_color=WARN,
            anchor="w",
        )
        status_lbl.grid(row=3, column=0, sticky="w", padx=14, pady=(0, 10))

        open_btn = ctk.CTkButton(
            frame,
            text="Ouvrir le dossier",
            width=120,
            height=26,
            corner_radius=6,
            font=ctk.CTkFont(size=11),
            fg_color=BTN_SEC_FG,
            text_color=BTN_SEC_TXT,
            hover_color=BTN_SEC_HVR,
            command=lambda: open_folder(self.download_path.get()),
        )
        open_btn.grid(row=3, column=1, sticky="e", padx=(0, 14), pady=(0, 10))
        open_btn.grid_remove()

        item = {
            "frame":      frame,
            "title_lbl":  title_lbl,
            "bar":        bar,
            "pct_lbl":    pct_lbl,
            "speed_lbl":  speed_lbl,
            "status_lbl": status_lbl,
            "open_btn":   open_btn,
        }
        self.download_items.append(item)
        return item

    def _update_item_title(self, item: dict, title: str):
        short = title[:72] + "..." if len(title) > 72 else title
        item["title_lbl"].configure(text=short)

    def _item_set_status(self, item: dict, text: str, color: str):
        item["status_lbl"].configure(text=text, text_color=color)

    def _progress_hook(self, d: dict, item: dict):
        status = d.get("status")

        if status == "downloading":
            total      = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            downloaded = d.get("downloaded_bytes", 0)
            speed      = d.get("speed") or 0
            eta        = d.get("eta")

            pct       = (downloaded / total * 100) if total else 0
            speed_str = fmt_speed(speed) if speed else "..."
            eta_str   = fmt_eta(eta)
            right     = f"{speed_str}  {eta_str}".strip()

            self.root.after(0, lambda p=pct: item["bar"].set(min(p / 100, 1.0)))
            self.root.after(0, lambda p=pct: item["pct_lbl"].configure(text=f"{p:.1f}%"))
            self.root.after(0, lambda s=right: item["speed_lbl"].configure(text=s))
            self.root.after(0, lambda: self._item_set_status(item, "Téléchargement en cours", SUCCESS))

        elif status == "postprocessing":
            self.root.after(0, lambda: item["bar"].set(0.97))
            self.root.after(0, lambda: item["pct_lbl"].configure(text="97%"))
            self.root.after(0, lambda: item["speed_lbl"].configure(text="Conversion..."))
            self.root.after(0, lambda: self._item_set_status(item, "Conversion en cours", INFO))

        elif status == "finished":
            self.root.after(0, lambda: item["bar"].set(1.0))
            self.root.after(0, lambda: item["pct_lbl"].configure(text="100%"))
            self.root.after(0, lambda: item["speed_lbl"].configure(text=""))

    def _item_finished(self, item: dict, dest: str):
        item["bar"].set(1.0)
        item["bar"].configure(progress_color=SUCCESS)
        item["pct_lbl"].configure(text="100%", text_color=SUCCESS)
        item["speed_lbl"].configure(text="")
        item["status_lbl"].configure(text="Terminé", text_color=SUCCESS)
        item["open_btn"].grid()

    def _item_error(self, item: dict, msg: str):
        item["bar"].configure(progress_color=ERROR)
        item["status_lbl"].configure(text=f"Erreur : {msg}", text_color=ERROR)
        item["speed_lbl"].configure(text="")

    def _remove_item(self, frame):
        frame.destroy()

    # ─────────────────────────────────────────────────────────────────────────

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = YouTubeDownloader()
    app.run()