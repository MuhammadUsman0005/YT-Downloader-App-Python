# pip install --upgrade yt-dlp (For future users: Ensure you have the latest version of yt-dlp for best performance and compatibility with YouTube's changing infrastructure.)


import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import yt_dlp
import threading
from tkinter import font as tkfont
import os

class YouTubeDownloaderApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("YouTube Downloader Pro (Playlist Edition)")
        self.geometry("650x550")
        # Allow the main window to be resizable by the user
        self.resizable(True, True)

        # Style Configuration
        self.style = ttk.Style()
        self.style.theme_use('clam')

        # Font Configuration (change these values to another font/size)
        font_family = "Verdana 11"
        font_size = 10

        # Update named Tk fonts so both tk and ttk widgets inherit the change
        for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont",
                     "TkCaptionFont", "TkSmallCaptionFont", "TkIconFont", "TkTooltipFont"):
            try:
                tkfont.nametofont(name).configure(family=font_family, size=font_size)
            except tk.TclError:
                pass

        # Apply font to common ttk widget styles
        self.style.configure('TLabel', font=(font_family, font_size))
        self.style.configure('TButton', font=(font_family, font_size))
        self.style.configure('TEntry', font=(font_family, font_size))
        self.style.configure('TCombobox', font=(font_family, font_size))

        # Also set default font for classic tk widgets
        self.option_add("*Font", (font_family, font_size))
        
        # Container for all frames
        self.container = tk.Frame(self)
        self.container.pack(fill="both", expand=True)
        # Make the single grid cell inside the container expand when window is resized
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        # Navigation Menu (Top)
        self.create_menu()

        # State variables
        self.current_url = tk.StringVar()
        self.download_folder = tk.StringVar(value=os.path.expanduser("~/Downloads"))
        self.status_var = tk.StringVar(value="Ready")
        self.progress_var = tk.DoubleVar(value=0)
        self.video_formats = {}  # Store format_id: description

        # Initialize Frames
        self.frames = {}
        # Added PlaylistFrame to the list
        for F in (VideoFrame, PlaylistFrame, ThumbnailFrame, TitleFrame, AudioFrame):
            page_name = F.__name__
            frame = F(parent=self.container, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("VideoFrame")

    def create_menu(self):
        menu_bar = tk.Menu(self)
        
        # File Menu
        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="Exit", command=self.quit)
        menu_bar.add_cascade(label="File", menu=file_menu)

        # Mode Menu
        mode_menu = tk.Menu(menu_bar, tearoff=0)
        mode_menu.add_command(label="Video Download", command=lambda: self.show_frame("VideoFrame"))
        mode_menu.add_command(label="Playlist Download", command=lambda: self.show_frame("PlaylistFrame"))  # New Option
        mode_menu.add_separator()
        mode_menu.add_command(label="Audio Download (MP3)", command=lambda: self.show_frame("AudioFrame"))
        mode_menu.add_command(label="Get Thumbnail", command=lambda: self.show_frame("ThumbnailFrame"))
        mode_menu.add_command(label="See Title", command=lambda: self.show_frame("TitleFrame"))
        menu_bar.add_cascade(label="Mode", menu=mode_menu)

        self.config(menu=menu_bar)

    def show_frame(self, page_name):
        """Switch to the requested frame."""
        frame = self.frames[page_name]
        frame.tkraise()
        self.title(f"YouTube Downloader - {frame.display_name}")
        self.status_var.set("Ready")
        self.progress_var.set(0)
        self.current_url.set("") # Clear URL on switch

    def browse_folder(self):
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.download_folder.set(folder_selected)

    # --- Backend Logic (Threaded) ---
    
    def fetch_video_info(self, url, callback_success):
        """Fetches formats in a separate thread to prevent GUI freezing."""
        def _worker():
            try:
                self.status_var.set("Fetching metadata...")
                ydl_opts = {'quiet': True, 'noplaylist': True} # Ensure we only look at single video logic here
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    
                formats = info.get('formats', [])
                unique_resolutions = {}
                
                for f in formats:
                    if f.get('vcodec') != 'none' and f.get('height'):
                        h = f['height']
                        ext = f['ext']
                        label = f"{h}p ({ext})"
                        unique_resolutions[label] = f['format_id']

                sorted_keys = sorted(unique_resolutions.keys(), key=lambda x: int(x.split('p')[0]), reverse=True)
                self.video_formats = {k: unique_resolutions[k] for k in sorted_keys}
                
                self.after(0, callback_success)
                self.status_var.set("Select a resolution.")
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", "Could not fetch info. Ensure this is a Single Video URL, not a Playlist."))
                self.status_var.set("Error fetching info.")

        threading.Thread(target=_worker, daemon=True).start()

    def run_download(self, ydl_opts, url):
        """Generic download runner with smart playlist progress hook."""
        def _hook(d):
            if d['status'] == 'downloading':
                try:
                    # Progress Calculation
                    p = d.get('_percent_str', '0%').replace('%','')
                    self.progress_var.set(float(p))
                    
                    # Playlist Awareness
                    prefix = ""
                    if 'playlist_index' in d and 'n_entries' in d:
                        current = d.get('playlist_index')
                        total = d.get('n_entries')
                        prefix = f"[Video {current}/{total}] "
                    
                    self.status_var.set(f"{prefix}Downloading: {d.get('_percent_str')} | Speed: {d.get('_speed_str')}")
                except:
                    pass
            elif d['status'] == 'finished':
                self.status_var.set("Processing/Merging...")

        ydl_opts['progress_hooks'] = [_hook]
        # Default output template
        if 'outtmpl' not in ydl_opts:
            ydl_opts['outtmpl'] = os.path.join(self.download_folder.get(), '%(title)s.%(ext)s')

        def _worker():
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
                self.status_var.set("Task Completed Successfully!")
                self.progress_var.set(100)
                self.after(0, lambda: messagebox.showinfo("Success", "Operation Complete!"))
            except Exception as e:
                self.status_var.set(f"Error: {str(e)}")
                self.after(0, lambda: messagebox.showerror("Download Error", str(e)))

        threading.Thread(target=_worker, daemon=True).start()


# --- GUI Frames ---

class VideoFrame(tk.Frame):
    display_name = "Single Video Download"
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        tk.Label(self, text="Video URL:", font=("Arial", 20, "bold")).pack(pady=(20, 5))
        tk.Entry(self, textvariable=controller.current_url, width=50).pack(pady=5)
        
        self.btn_fetch = tk.Button(self, text="1. Fetch Resolutions", command=self.fetch_resolutions)
        self.btn_fetch.pack(pady=15)
        
        tk.Label(self, text="Select Quality:").pack(pady=(15, 5))
        self.res_combo = ttk.Combobox(self, state="readonly", width=30)
        self.res_combo.pack(pady=5)
        
        frame_folder = tk.Frame(self)
        frame_folder.pack(pady=10)
        tk.Label(frame_folder, text="Save to: ").pack(side="left")
        tk.Label(frame_folder, textvariable=controller.download_folder, fg="blue").pack(side="left")
        tk.Button(frame_folder, text="Browse", command=controller.browse_folder).pack(side="left", padx=10)

        ttk.Progressbar(self, variable=controller.progress_var, length=400).pack(pady=20)
        tk.Label(self, textvariable=controller.status_var, fg="green").pack(pady=5)
        
        self.btn_download = tk.Button(self, text="2. Download Video", command=self.start_download, state="disabled", bg="#dddddd")
        self.btn_download.pack(pady=10)

    def fetch_resolutions(self):
        url = self.controller.current_url.get()
        if not url: return
        self.controller.fetch_video_info(url, self.enable_download)

    def enable_download(self):
        options = list(self.controller.video_formats.keys())
        if options:
            self.res_combo['values'] = options
            self.res_combo.current(0)
            self.btn_download['state'] = "normal"
            self.btn_download['bg'] = "#4CAF50"
            self.btn_download['fg'] = "white"

    def start_download(self):
        selected_label = self.res_combo.get()
        if not selected_label: return
        video_id = self.controller.video_formats[selected_label]
        
        opts = {
            'format': f'{video_id}+bestaudio/best',
            'merge_output_format': 'mp4',
        }
        self.controller.run_download(opts, self.controller.current_url.get())


class PlaylistFrame(tk.Frame):
    display_name = "Full Playlist Download"
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        tk.Label(self, text="Playlist URL:", font=("Arial", 20, "bold")).pack(pady=(20, 5))
        tk.Entry(self, textvariable=controller.current_url, width=50).pack(pady=5)
        
        tk.Label(self, text="Max Resolution Limit:", font=("Arial", 10)).pack(pady=(15, 5))
        
        # General Quality Options for Playlist (safer than fetching per video)
        self.quality_combo = ttk.Combobox(self, state="readonly", width=30)
        self.quality_combo['values'] = [
            "Best Available (Max)",
            "Limit to 1080p", 
            "Limit to 720p", 
            "Limit to 480p",
            "Audio Only (MP3)"
        ]
        self.quality_combo.current(1) # Default to 1080p
        self.quality_combo.pack(pady=5)
        
        frame_folder = tk.Frame(self)
        frame_folder.pack(pady=15)
        tk.Label(frame_folder, text="Save to: ").pack(side="left")
        tk.Label(frame_folder, textvariable=controller.download_folder, fg="blue").pack(side="left")
        tk.Button(frame_folder, text="Change Folder", command=controller.browse_folder).pack(side="left", padx=10)

        # Info Label
        tk.Label(self, text="Note: This will download ALL videos in the playlist.", font=("Arial", 9, "italic"), fg="gray").pack(pady=5)

        ttk.Progressbar(self, variable=controller.progress_var, length=400).pack(pady=20)
        tk.Label(self, textvariable=controller.status_var, fg="green", font=("Arial", 10, "bold")).pack(pady=5)
        
        self.btn_download = tk.Button(self, text="Download Full Playlist", bg="#9C27B0", fg="white", command=self.start_download)
        self.btn_download.pack(pady=10)

    def start_download(self):
        url = self.controller.current_url.get()
        if not url: 
            messagebox.showwarning("Input", "Please enter a URL")
            return

        selection = self.quality_combo.get()
        
        # Construct Generic Format String based on selection
        if "Audio Only" in selection:
            opts = {
                'format': 'bestaudio/best',
                'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'}],
                'outtmpl': os.path.join(self.controller.download_folder.get(), '%(playlist_title)s/%(playlist_index)s - %(title)s.%(ext)s')
            }
        else:
            # Video Logic
            if "Best Available" in selection:
                fmt = "bestvideo+bestaudio/best"
            elif "1080p" in selection:
                fmt = "bestvideo[height<=1080]+bestaudio/best[height<=1080]"
            elif "720p" in selection:
                fmt = "bestvideo[height<=720]+bestaudio/best[height<=720]"
            elif "480p" in selection:
                fmt = "bestvideo[height<=480]+bestaudio/best[height<=480]"
            
            opts = {
                'format': fmt,
                'merge_output_format': 'mp4',
                # Create a subfolder for the playlist name automatically
                'outtmpl': os.path.join(self.controller.download_folder.get(), '%(playlist_title)s/%(playlist_index)s - %(title)s.%(ext)s'),
                'ignoreerrors': True, # Skip deleted/private videos without crashing
            }

        self.controller.run_download(opts, url)


class AudioFrame(tk.Frame):
    display_name = "Audio Download"
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        tk.Label(self, text="Audio/Video URL:", font=("Arial", 20, "bold")).pack(pady=(20, 5))
        tk.Entry(self, textvariable=controller.current_url, width=50).pack(pady=5)
        
        tk.Label(self, text="Audio Quality:").pack(pady=(15, 5))
        self.quality_combo = ttk.Combobox(self, state="readonly", width=20)
        self.quality_combo['values'] = ["Best Quality (MP3)", "192 kbps (MP3)", "128 kbps (MP3)"]
        self.quality_combo.current(0)
        self.quality_combo.pack(pady=5)

        frame_folder = tk.Frame(self)
        frame_folder.pack(pady=10)
        tk.Label(frame_folder, textvariable=controller.download_folder, fg="blue").pack(side="left")
        tk.Button(frame_folder, text="Change Folder", command=controller.browse_folder).pack(side="left", padx=10)

        ttk.Progressbar(self, variable=controller.progress_var, length=400).pack(pady=20)
        tk.Label(self, textvariable=controller.status_var, fg="green").pack(pady=5)
        
        tk.Button(self, text="Download Audio", bg="#2196F3", fg="white", command=self.start_download).pack(pady=10)

    def start_download(self):
        url = self.controller.current_url.get()
        if not url: return
        
        quality_map = {"Best Quality (MP3)": "0", "192 kbps (MP3)": "192", "128 kbps (MP3)": "128"}
        q_key = self.quality_combo.get()
        bitrate = quality_map.get(q_key, "192")
        
        opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': bitrate}],
            'noplaylist': True 
        }
        self.controller.run_download(opts, url)


class ThumbnailFrame(tk.Frame):
    display_name = "Download Thumbnail"
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        tk.Label(self, text="Video URL:", font=("Arial", 20, "bold")).pack(pady=(30, 5))
        tk.Entry(self, textvariable=controller.current_url, width=50).pack(pady=5)
        
        frame_folder = tk.Frame(self)
        frame_folder.pack(pady=20)
        tk.Label(frame_folder, text="Save to: ").pack(side="left")
        tk.Label(frame_folder, textvariable=controller.download_folder, fg="blue").pack(side="left")
        tk.Button(frame_folder, text="Browse", command=controller.browse_folder).pack(side="left", padx=10)
        
        tk.Label(self, textvariable=controller.status_var, fg="green").pack(pady=5)
        tk.Button(self, text="Save Thumbnail", bg="#FF9800", fg="white", command=self.download_thumb).pack(pady=10)

    def download_thumb(self):
        url = self.controller.current_url.get()
        if not url: return
        
        opts = {
            'skip_download': True,
            'writethumbnail': True,
            'outtmpl': os.path.join(self.controller.download_folder.get(), '%(title)s.%(ext)s'),
            'postprocessors': [{'key': 'FFmpegThumbnailsConvertor','format': 'jpg'}],
        }
        self.controller.run_download(opts, url)


class TitleFrame(tk.Frame):
    display_name = "Get Video Title"
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        tk.Label(self, text="Video URL:", font=("Arial", 20, "bold")).pack(pady=(40, 5))
        tk.Entry(self, textvariable=controller.current_url, width=50).pack(pady=5)
        
        self.title_label = tk.Label(self, text="...", font=("Helvetica", 14, "bold"), wraplength=500)
        self.title_label.pack(pady=40)
        
        tk.Button(self, text="Get Title", command=self.get_title).pack(pady=10)

    def get_title(self):
        url = self.controller.current_url.get()
        if not url: return
        
        self.title_label.config(text="Fetching...")
        
        def _worker():
            try:
                with yt_dlp.YoutubeDL({'quiet':True}) as ydl:
                    info = ydl.extract_info(url, download=False)
                    title = info.get('title', 'Unknown Title')
                    self.after(0, lambda: self.title_label.config(text=title))
            except Exception as e:
                self.after(0, lambda: self.title_label.config(text="Error fetching title"))
        
        threading.Thread(target=_worker, daemon=True).start()


if __name__ == "__main__":
    app = YouTubeDownloaderApp()
    app.mainloop()
