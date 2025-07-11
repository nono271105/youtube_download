import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import yt_dlp
import threading
import os
from pathlib import Path
import re

# Configuration du thème
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class YouTubeDownloader:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("YouTube Video Downloader")
        self.root.geometry("800x600")
        self.root.resizable(False, False)
        
        # Variables
        self.download_path = tk.StringVar(value=str(Path.home() / "Downloads"))
        self.url_var = tk.StringVar()
        self.progress_var = tk.DoubleVar()
        self.status_var = tk.StringVar(value="Prêt à télécharger")
        self.quality_var = tk.StringVar(value="720p")
        
        self.create_widgets()
        
    def create_widgets(self):
        # Titre principal
        title_label = ctk.CTkLabel(
            self.root, 
            text="YouTube Video Downloader",
            font=ctk.CTkFont(size=28, weight="bold")
        )
        title_label.pack(pady=30)
        
        # Frame principale
        main_frame = ctk.CTkFrame(self.root)
        main_frame.pack(padx=40, pady=20, fill="both", expand=True)
        
        # Section URL
        url_frame = ctk.CTkFrame(main_frame)
        url_frame.pack(padx=20, pady=20, fill="x")
        
        url_label = ctk.CTkLabel(
            url_frame, 
            text="Lien de la vidéo YouTube:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        url_label.pack(pady=(15, 5))
        
        self.url_entry = ctk.CTkEntry(
            url_frame,
            textvariable=self.url_var,
            placeholder_text="https://www.youtube.com/watch?v=...",
            width=400,
            height=40,
            font=ctk.CTkFont(size=12)
        )
        self.url_entry.pack(pady=(0, 15))
        
        # Section qualité et dossier
        options_frame = ctk.CTkFrame(main_frame)
        options_frame.pack(padx=20, pady=10, fill="x")
        
        # Qualité
        quality_label = ctk.CTkLabel(
            options_frame, 
            text="Qualité:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        quality_label.pack(pady=(15, 5))
        
        self.quality_menu = ctk.CTkOptionMenu(
            options_frame,
            values=["1080p", "720p", "480p", "360p", "Audio uniquement"],
            variable=self.quality_var,
            width=200,
            height=35
        )
        self.quality_menu.pack(pady=(0, 15))
        
        # Dossier de destination
        path_label = ctk.CTkLabel(
            options_frame, 
            text="Dossier de destination:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        path_label.pack(pady=(5, 5))
        
        path_frame = ctk.CTkFrame(options_frame)
        path_frame.pack(pady=(0, 15), padx=20, fill="x")
        
        self.path_entry = ctk.CTkEntry(
            path_frame,
            textvariable=self.download_path,
            width=300,
            height=35
        )
        self.path_entry.pack(side="left", padx=(10, 5), pady=10)
        
        self.browse_button = ctk.CTkButton(
            path_frame,
            text="Parcourir",
            command=self.browse_folder,
            width=100,
            height=35
        )
        self.browse_button.pack(side="right", padx=(5, 10), pady=10)
        
        # Bouton de téléchargement
        self.download_button = ctk.CTkButton(
            main_frame,
            text="Télécharger",
            command=self.start_download,
            width=200,
            height=50,
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.download_button.pack(pady=20)
        
        # Section barre de téléchargement
        download_frame = ctk.CTkFrame(main_frame)
        download_frame.pack(padx=20, pady=15, fill="x")
        
        download_title = ctk.CTkLabel(
            download_frame,
            text="Téléchargements",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        download_title.pack(pady=(15, 10))
        
        # Zone de téléchargement avec scrollbar
        self.download_scrollable = ctk.CTkScrollableFrame(
            download_frame,
            width=520,
            height=150,
            label_text="Téléchargements en cours et terminés"
        )
        self.download_scrollable.pack(pady=(0, 15), padx=20, fill="both", expand=True)
        
        # Message initial
        self.initial_message = ctk.CTkLabel(
            self.download_scrollable,
            text="Aucun téléchargement en cours.\nLes téléchargements apparaîtront ici avec leur progression.",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.initial_message.pack(pady=30)
        
        # Liste pour stocker les téléchargements
        self.download_items = []
        
        # Statut
        self.status_label = ctk.CTkLabel(
            main_frame,
            textvariable=self.status_var,
            font=ctk.CTkFont(size=12)
        )
        self.status_label.pack(pady=10)
        
        # Informations de la vidéo
        self.info_frame = ctk.CTkFrame(main_frame)
        self.info_frame.pack(padx=20, pady=10, fill="x")
        
        self.info_label = ctk.CTkLabel(
            self.info_frame,
            text="Collez un lien pour voir les informations de la vidéo",
            font=ctk.CTkFont(size=11),
            wraplength=400
        )
        self.info_label.pack(pady=15)
        
        # Bouton pour obtenir les infos
        self.info_button = ctk.CTkButton(
            main_frame,
            text="Obtenir les informations",
            command=self.get_video_info,
            width=150,
            height=35
        )
        self.info_button.pack(pady=5)
        
    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.download_path.set(folder)
            
    def is_valid_youtube_url(self, url):
        youtube_regex = re.compile(
            r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/'
            r'(watch\?v=|embed/|v/|.+\?v=)?([^&=%\?]{11})'
        )
        return youtube_regex.match(url) is not None
        
    def get_video_info(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showerror("Erreur", "Veuillez entrer un lien YouTube.")
            return
            
        if not self.is_valid_youtube_url(url):
            messagebox.showerror("Erreur", "Lien YouTube invalide.")
            return
            
        self.status_var.set("Récupération des informations...")
        self.info_button.configure(state="disabled")
        
        def fetch_info():
            try:
                ydl_opts = {
                    'quiet': True,
                    'no_warnings': True,
                }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    title = info.get('title', 'Titre non disponible')
                    duration = info.get('duration', 0)
                    uploader = info.get('uploader', 'Inconnu')
                    
                    # Formatage de la durée
                    if duration:
                        mins, secs = divmod(duration, 60)
                        duration_str = f"{mins}:{secs:02d}"
                    else:
                        duration_str = "Inconnue"
                    
                    info_text = f"Titre: {title}\nDurée: {duration_str}\nAuteur: {uploader}"
                    
                self.root.after(0, lambda: self.update_info(info_text))
                    
            except Exception as e:
                error_msg = f"Erreur lors de la récupération des informations: {str(e)}"
                self.root.after(0, lambda: self.update_info(error_msg))
                
        threading.Thread(target=fetch_info, daemon=True).start()

    def create_download_item(self, video_title, video_url):
        """Crée un nouvel élément de téléchargement dans la barre"""
        # Masquer le message initial s'il existe
        if hasattr(self, 'initial_message') and self.initial_message.winfo_exists():
            self.initial_message.destroy()
        
        # Frame pour cet élément de téléchargement
        item_frame = ctk.CTkFrame(self.download_scrollable)
        item_frame.pack(fill="x", padx=5, pady=5)
        
        # Titre de la vidéo (tronqué si trop long)
        title_display = video_title[:60] + "..." if len(video_title) > 60 else video_title
        title_label = ctk.CTkLabel(
            item_frame,
            text=title_display,
            font=ctk.CTkFont(size=12, weight="bold"),
            anchor="w"
        )
        title_label.pack(fill="x", padx=10, pady=(10, 5))
        
        # Barre de progression
        progress_bar = ctk.CTkProgressBar(
            item_frame,
            width=400,
            height=20
        )
        progress_bar.pack(fill="x", padx=10, pady=5)
        progress_bar.set(0)
        
        # Informations (pourcentage, vitesse, statut)
        info_frame = ctk.CTkFrame(item_frame)
        info_frame.pack(fill="x", padx=10, pady=5)
        
        percentage_label = ctk.CTkLabel(
            info_frame,
            text="0%",
            font=ctk.CTkFont(size=10, weight="bold")
        )
        percentage_label.pack(side="left", padx=(5, 0))
        
        speed_label = ctk.CTkLabel(
            info_frame,
            text="Préparation...",
            font=ctk.CTkFont(size=10)
        )
        speed_label.pack(side="right", padx=(0, 5))
        
        # Statut
        status_label = ctk.CTkLabel(
            item_frame,
            text="En attente",
            font=ctk.CTkFont(size=10),
            text_color="orange"
        )
        status_label.pack(padx=10, pady=(0, 10))
        
        # Stocker les références
        download_item = {
            'frame': item_frame,
            'title': video_title,
            'url': video_url,
            'progress_bar': progress_bar,
            'percentage_label': percentage_label,
            'speed_label': speed_label,
            'status_label': status_label
        }
        
        self.download_items.append(download_item)
        return download_item
                    
    def update_info(self, info_text):
        self.info_label.configure(text=info_text)
        self.status_var.set("Informations récupérées")
        self.info_button.configure(state="normal")
        
    def progress_hook(self, d):
        if not hasattr(self, 'current_download_item'):
            return
            
        item = self.current_download_item
        
        if d['status'] == 'downloading':
            if 'total_bytes' in d:
                percent = (d['downloaded_bytes'] / d['total_bytes']) * 100
                self.root.after(0, lambda: item['progress_bar'].set(percent / 100))
                self.root.after(0, lambda: item['percentage_label'].configure(text=f"{percent:.1f}%"))
                self.root.after(0, lambda: item['status_label'].configure(text="Téléchargement...", text_color="green"))
                
                # Calcul de la vitesse
                if 'speed' in d and d['speed']:
                    speed = d['speed']
                    if speed > 1024 * 1024:  # MB/s
                        speed_text = f"{speed / (1024 * 1024):.1f} MB/s"
                    else:  # KB/s
                        speed_text = f"{speed / 1024:.1f} KB/s"
                    self.root.after(0, lambda: item['speed_label'].configure(text=speed_text))
                
            elif 'downloaded_bytes' in d:
                # Affichage des bytes téléchargés même sans total
                downloaded = d['downloaded_bytes']
                if downloaded > 1024 * 1024:  # MB
                    size_text = f"{downloaded / (1024 * 1024):.1f} MB"
                else:  # KB
                    size_text = f"{downloaded / 1024:.1f} KB"
                self.root.after(0, lambda: item['speed_label'].configure(text=size_text))
                
        elif d['status'] == 'finished':
            self.root.after(0, lambda: item['progress_bar'].set(1.0))
            self.root.after(0, lambda: item['percentage_label'].configure(text="100%"))
            self.root.after(0, lambda: item['speed_label'].configure(text="Terminé !"))
            self.root.after(0, lambda: item['status_label'].configure(text="✓ Terminé", text_color="green"))
            
        elif d['status'] == 'error':
            self.root.after(0, lambda: item['status_label'].configure(text="❌ Erreur", text_color="red"))
            
    def start_download(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showerror("Erreur", "Veuillez entrer un lien YouTube.")
            return
            
        if not self.is_valid_youtube_url(url):
            messagebox.showerror("Erreur", "Lien YouTube invalide.")
            return
            
        if not os.path.exists(self.download_path.get()):
            messagebox.showerror("Erreur", "Le dossier de destination n'existe pas.")
            return
            
        self.download_button.configure(state="disabled")
        self.status_var.set("Préparation du téléchargement...")
        
        def download():
            try:
                # Obtenir les informations de la vidéo d'abord
                ydl_opts_info = {
                    'quiet': True,
                    'no_warnings': True,
                }
                
                video_title = "Vidéo YouTube"
                with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
                    info = ydl.extract_info(url, download=False)
                    video_title = info.get('title', 'Vidéo YouTube')
                
                # Créer l'élément de téléchargement dans la barre
                # self.current_download_item = self.root.after(0, lambda: self.create_download_item(video_title, url))
                # The above line was incorrect. You cannot assign the result of after() directly to current_download_item
                # if you intend to use it as the item itself. The actual item is returned by create_download_item.
                self.current_download_item = self.create_download_item(video_title, url)
                
                # Attendre que l'élément soit créé - not needed with direct assignment
                # import time
                # time.sleep(0.1)
                
                # Trouver l'élément créé - not needed with direct assignment
                # if self.download_items:
                #     self.current_download_item = self.download_items[-1]
                    
                # Mettre à jour le statut
                self.root.after(0, lambda: self.current_download_item['status_label'].configure(text="Téléchargement...", text_color="orange"))
                
                # Configuration selon la qualité choisie
                quality = self.quality_var.get()
                
                if quality == "Audio uniquement":
                    ydl_opts = {
                        'format': 'bestaudio/best',
                        'outtmpl': os.path.join(self.download_path.get(), '%(title)s.%(ext)s'),
                        'progress_hooks': [self.progress_hook],
                        'postprocessors': [{
                            'key': 'FFmpegExtractAudio',
                            'preferredcodec': 'mp3',
                            'preferredquality': '192',
                        }],
                    }
                else:
                    # Mapping des qualités
                    quality_map = {
                        "1080p": "best[height<=1080]",
                        "720p": "best[height<=720]",
                        "480p": "best[height<=480]",
                        "360p": "best[height<=360]"
                    }
                    
                    ydl_opts = {
                        'format': quality_map.get(quality, 'best[height<=720]'),
                        'outtmpl': os.path.join(self.download_path.get(), '%(title)s.%(ext)s'),
                        'progress_hooks': [self.progress_hook],
                    }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                    
                self.root.after(0, lambda: messagebox.showinfo("Succès", f"Téléchargement terminé !\n{video_title}"))
                self.root.after(0, lambda: self.status_var.set("Téléchargement terminé avec succès !"))
                
            except Exception as e:
                error_msg = f"Erreur lors du téléchargement: {str(e)}"
                self.root.after(0, lambda: messagebox.showerror("Erreur", error_msg))
                self.root.after(0, lambda: self.status_var.set("Erreur lors du téléchargement"))
                
                # Mettre à jour le statut de l'élément en cas d'erreur
                if hasattr(self, 'current_download_item') and self.current_download_item:
                    self.root.after(0, lambda: self.current_download_item['status_label'].configure(text="❌ Erreur", text_color="red"))
                
            finally:
                self.root.after(0, lambda: self.download_button.configure(state="normal"))
                
        threading.Thread(target=download, daemon=True).start()
        
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = YouTubeDownloader()
    app.run()