import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import requests
from datetime import datetime
import pygame
import os
import sys
import threading
import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class PrayerTimeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("International Prayer Times")
        self.root.geometry("380x650")
        self.root.configure(bg="#2c3e50")
        self.root.resizable(False, False)

        # SET ICON FOR WINDOW (Title bar)
        icon_path = resource_path("pary.ico")
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except Exception:
                pass # Fail silently if icon has issues

        self.root.protocol('WM_DELETE_WINDOW', self.minimize_to_tray)

        pygame.mixer.init()
        self.athan_file = None
        self.prayer_times = {}
        self.next_prayer_name = "Loading..."
        self.tray_icon = None

        # --- GUI COMPONENTS ---
        header_frame = tk.Frame(root, bg="#34495e", pady=15)
        header_frame.pack(fill="x")
        
        title_lbl = tk.Label(header_frame, text="Prayer Times Pro", font=("Segoe UI", 18, "bold"), fg="#ecf0f1", bg="#34495e")
        title_lbl.pack()
        
        subtitle_lbl = tk.Label(header_frame, text="Runs in background", font=("Segoe UI", 10), fg="#bdc3c7", bg="#34495e")
        subtitle_lbl.pack()

        settings_frame = tk.LabelFrame(root, text="Location Settings", bg="#2c3e50", fg="white", padx=10, pady=10)
        settings_frame.pack(fill="x", padx=20, pady=10)

        tk.Label(settings_frame, text="City:", bg="#2c3e50", fg="white").grid(row=0, column=0, sticky="w")
        self.city_entry = tk.Entry(settings_frame, width=15)
        self.city_entry.insert(0, "Jeddah") 
        self.city_entry.grid(row=0, column=1, padx=5)

        tk.Label(settings_frame, text="Country:", bg="#2c3e50", fg="white").grid(row=0, column=2, sticky="w")
        self.country_entry = tk.Entry(settings_frame, width=15)
        self.country_entry.insert(0, "Saudi Arabia") 
        self.country_entry.grid(row=0, column=3, padx=5)

        update_btn = tk.Button(settings_frame, text="Update & Save", command=self.fetch_prayer_times, bg="#27ae60", fg="white", relief="flat")
        update_btn.grid(row=1, column=0, columnspan=4, pady=10, sticky="we")

        audio_frame = tk.Frame(root, bg="#2c3e50", pady=5)
        audio_frame.pack(fill="x", padx=20)
        
        self.audio_lbl = tk.Label(audio_frame, text="Sound: Default Beep", bg="#2c3e50", fg="#bdc3c7", font=("Arial", 9))
        self.audio_lbl.pack(side="left")
        
        select_audio_btn = tk.Button(audio_frame, text="Browse MP3", command=self.select_audio_file, bg="#2980b9", fg="white", font=("Arial", 8))
        select_audio_btn.pack(side="right")

        ttk.Separator(root, orient='horizontal').pack(fill='x', pady=10)
        self.next_prayer_lbl = tk.Label(root, text="Next: --", font=("Segoe UI", 14), bg="#2c3e50", fg="#f1c40f")
        self.next_prayer_lbl.pack(pady=5)
        
        self.countdown_lbl = tk.Label(root, text="00:00:00", font=("Segoe UI", 28, "bold"), bg="#2c3e50", fg="#e74c3c")
        self.countdown_lbl.pack(pady=5)

        self.list_frame = tk.Frame(root, bg="#2c3e50")
        self.list_frame.pack(fill="both", expand=True, padx=30, pady=5)

        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = tk.Label(root, textvariable=self.status_var, bd=1, relief=tk.SUNKEN, anchor=tk.W, bg="#34495e", fg="white")
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.fetch_prayer_times()
        self.update_clock()

    def create_tray_icon(self):
        # USE ICON FOR TRAY
        icon_path = resource_path("pary.ico")
        if os.path.exists(icon_path):
            return Image.open(icon_path)
        else:
            # Fallback if file missing (Red Circle)
            width = 64
            height = 64
            image = Image.new('RGB', (width, height), "#2c3e50")
            dc = ImageDraw.Draw(image)
            dc.ellipse((10, 10, 54, 54), fill="#c0392b")
            return image

    def minimize_to_tray(self):
        self.root.withdraw()
        image = self.create_tray_icon()
        menu = (item('Show', self.show_window), item('Quit', self.quit_app))
        self.tray_icon = pystray.Icon("name", image, "Prayer Time App", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def show_window(self, icon, item):
        self.tray_icon.stop()
        self.root.after(0, self.root.deiconify)

    def quit_app(self, icon, item):
        self.tray_icon.stop()
        self.root.quit()

    def select_audio_file(self):
        file_path = filedialog.askopenfilename(filetypes=[("Audio Files", "*.mp3 *.wav")])
        if file_path:
            self.athan_file = file_path
            self.audio_lbl.config(text=f"Sound: {os.path.basename(file_path)}")

    def play_athan(self, prayer_name):
        self.root.after(0, lambda: messagebox.showinfo("Prayer Time", f"It is time for {prayer_name}"))
        if self.athan_file:
            try:
                pygame.mixer.music.load(self.athan_file)
                pygame.mixer.music.play()
                self.status_var.set(f"Playing Athan for {prayer_name}...")
            except Exception as e:
                self.status_var.set("Audio Error")
        else:
            print('\a') 
            self.status_var.set("Beep! (No MP3 selected)")

    def fetch_prayer_times(self):
        city = self.city_entry.get()
        country = self.country_entry.get()
        self.status_var.set(f"Fetching data for {city}...")
        url = f"http://api.aladhan.com/v1/timingsByCity?city={city}&country={country}&method=2"
        
        def api_call():
            try:
                response = requests.get(url, timeout=10)
                data = response.json()
                if data['code'] == 200:
                    timings = data['data']['timings']
                    target_prayers = ['Fajr', 'Sunrise', 'Dhuhr', 'Asr', 'Maghrib', 'Isha']
                    self.root.after(0, lambda: self.update_prayer_data(timings, target_prayers))
                else:
                    self.root.after(0, lambda: messagebox.showerror("Error", "Could not find city."))
            except Exception as e:
                self.root.after(0, lambda: self.status_var.set("Connection failed. Retrying..."))

        threading.Thread(target=api_call, daemon=True).start()

    def update_prayer_data(self, timings, target_prayers):
        self.prayer_times = {k: timings[k] for k in target_prayers if k in timings}
        for widget in self.list_frame.winfo_children():
            widget.destroy()
        row = 0
        for prayer, time_str in self.prayer_times.items():
            p_lbl = tk.Label(self.list_frame, text=prayer, font=("Segoe UI", 12), bg="#2c3e50", fg="white")
            p_lbl.grid(row=row, column=0, sticky="w", pady=5)
            t_lbl = tk.Label(self.list_frame, text=time_str, font=("Segoe UI", 12, "bold"), bg="#2c3e50", fg="#ecf0f1")
            t_lbl.grid(row=row, column=1, sticky="e", padx=(180, 0), pady=5)
            row += 1
        self.status_var.set("Schedule Updated.")

    def update_clock(self):
        now = datetime.now()
        if self.prayer_times:
            upcoming = None
            min_diff = float('inf')
            for prayer, time_str in self.prayer_times.items():
                try:
                    p_time = datetime.strptime(f"{now.date()} {time_str}", "%Y-%m-%d %H:%M")
                    diff = (p_time - now).total_seconds()
                    if 0 < diff < min_diff:
                        min_diff = diff
                        upcoming = (prayer, p_time)
                except ValueError:
                    continue
            if upcoming:
                name, p_time = upcoming
                self.next_prayer_lbl.config(text=f"Next: {name}")
                m, s = divmod(min_diff, 60)
                h, m = divmod(m, 60)
                self.countdown_lbl.config(text=f"{int(h):02}:{int(m):02}:{int(s):02}")
                if int(min_diff) == 0:
                    self.play_athan(name)
            else:
                self.next_prayer_lbl.config(text="Next: Fajr (Tomorrow)")
                self.countdown_lbl.config(text="--:--:--")
        self.root.after(1000, self.update_clock)

if __name__ == "__main__":
    root = tk.Tk()
    app = PrayerTimeApp(root)
    root.mainloop()