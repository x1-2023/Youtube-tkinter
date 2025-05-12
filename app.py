"""
YouTube Channel Downloader
- Downloads all videos and thumbnails from a YouTube channel
- Uses Selenium to handle authentication and save cookies automatically
- Simple GUI interface
"""

import os
import sys
import json
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import subprocess
import threading
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import pickle
import logging
import platform
import glob
import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("youtube_downloader.log"),
        logging.StreamHandler()
    ]
)

class YouTubeDownloader:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("YouTube Channel Downloader")
        self.root.geometry("800x600")
        self.root.minsize(800, 600)
        
        self.cookie_path = os.path.join(os.path.expanduser("~"), ".youtube_downloader_cookies.pkl")
        self.download_path = os.path.join(os.path.expanduser("~"), "Downloads", "YouTubeDownloads")
        self.browser = None
        self.cookies_loaded = False
        
        self.setup_ui()
        self.check_dependencies()
        
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="YouTube Channel Downloader", font=("Arial", 18, "bold"))
        title_label.pack(pady=10)
        
        # URL Input
        url_frame = ttk.Frame(main_frame)
        url_frame.pack(fill=tk.X, pady=10)
        
        url_label = ttk.Label(url_frame, text="YouTube Channel URL:")
        url_label.pack(side=tk.LEFT, padx=5)
        
        self.url_entry = ttk.Entry(url_frame, width=50)
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Download Location
        path_frame = ttk.Frame(main_frame)
        path_frame.pack(fill=tk.X, pady=10)
        
        path_label = ttk.Label(path_frame, text="Download Location:")
        path_label.pack(side=tk.LEFT, padx=5)
        
        self.path_entry = ttk.Entry(path_frame, width=50)
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.path_entry.insert(0, self.download_path)
        
        browse_button = ttk.Button(path_frame, text="Browse", command=self.browse_path)
        browse_button.pack(side=tk.RIGHT, padx=5)
        
        # Options Frame
        options_frame = ttk.LabelFrame(main_frame, text="Download Options", padding=10)
        options_frame.pack(fill=tk.X, pady=10)
        
        # Checkboxes for options
        self.download_thumbnails = tk.BooleanVar(value=True)
        thumbnail_check = ttk.Checkbutton(options_frame, text="Download Thumbnails", variable=self.download_thumbnails)
        thumbnail_check.grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        
        self.download_descriptions = tk.BooleanVar(value=True)
        desc_check = ttk.Checkbutton(options_frame, text="Download Descriptions", variable=self.download_descriptions)
        desc_check.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        self.download_subtitles = tk.BooleanVar(value=False)
        sub_check = ttk.Checkbutton(options_frame, text="Download Subtitles", variable=self.download_subtitles)
        sub_check.grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        
        self.best_quality = tk.BooleanVar(value=True)
        quality_check = ttk.Checkbutton(options_frame, text="Best Quality", variable=self.best_quality)
        quality_check.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Limit videos frame
        limit_frame = ttk.Frame(options_frame)
        limit_frame.grid(row=2, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
        
        limit_label = ttk.Label(limit_frame, text="Limit number of videos (0 = all):")
        limit_label.pack(side=tk.LEFT, padx=5)
        
        self.limit_entry = ttk.Entry(limit_frame, width=5)
        self.limit_entry.pack(side=tk.LEFT, padx=5)
        self.limit_entry.insert(0, "0")
        
        # Action buttons
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=10)
        
        self.login_button = ttk.Button(buttons_frame, text="Login to YouTube", command=self.handle_login)
        self.login_button.pack(side=tk.LEFT, padx=5)
        
        self.download_button = ttk.Button(buttons_frame, text="Download Channel", command=self.start_download)
        self.download_button.pack(side=tk.RIGHT, padx=5)
        
        clear_cookies_button = ttk.Button(buttons_frame, text="Clear Cookies", command=self.clear_cookies)
        clear_cookies_button.pack(side=tk.RIGHT, padx=5)
        
        # Nút Save Cookies luôn hiển thị
        self.save_button_frame = ttk.Frame(main_frame)
        self.save_button_frame.pack(fill=tk.X, pady=5)
        self.save_cookies_button = ttk.Button(self.save_button_frame, text="Save Cookies", command=self._save_cookies)
        self.save_cookies_button.pack(pady=5)
        
        # Progress indicators
        self.progress_var = tk.DoubleVar()
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=10)
        
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, length=100, mode="indeterminate")
        self.progress_bar.pack(fill=tk.X, padx=5, pady=5)
        
        self.status_label = ttk.Label(progress_frame, text="Ready")
        self.status_label.pack(anchor=tk.W, padx=5)
        
        # Output console (for messages)
        console_frame = ttk.LabelFrame(main_frame, text="Console Output", padding=10)
        console_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.console_text = tk.Text(console_frame, height=10, wrap=tk.WORD)
        self.console_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(console_frame, command=self.console_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.console_text.config(yscrollcommand=scrollbar.set)
        
        # Bảng danh sách video vừa tải
        video_list_frame = ttk.LabelFrame(main_frame, text="Danh sách video vừa tải", padding=10)
        video_list_frame.pack(fill=tk.BOTH, expand=False, pady=5)
        self.video_tree = ttk.Treeview(video_list_frame, columns=("#1", "#2"), show="headings", height=6)
        self.video_tree.heading("#1", text="Tên file")
        self.video_tree.heading("#2", text="Thời gian tải")
        self.video_tree.pack(fill=tk.BOTH, expand=True)
        
        # Set initial state
        self.update_login_status()
        
    def update_login_status(self):
        if os.path.exists(self.cookie_path):
            try:
                with open(self.cookie_path, 'rb') as f:
                    cookies = pickle.load(f)
                    if cookies:
                        self.cookies_loaded = True
                        self.login_button.config(text="Re-Login (Cookies Found)")
                        self.log("Login cookies found and loaded")
                        return
            except Exception as e:
                self.log(f"Error loading cookies: {e}", "error")
                
        self.login_button.config(text="Login to YouTube")
        self.cookies_loaded = False
        
    def check_dependencies(self):
        """Check if required dependencies are installed"""
        try:
            # Check yt-dlp
            result = subprocess.run(["yt-dlp", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                version = result.stdout.strip()
                self.log(f"yt-dlp version {version} found")
            else:
                self.log("yt-dlp not found! Please install it with: pip install yt-dlp", "error")
                messagebox.showerror("Dependency Error", "yt-dlp not found! Please install it with: pip install yt-dlp")
                
            # Check if Chrome is installed
            if platform.system() == "Windows":
                chrome_paths = [
                    os.path.expandvars("%ProgramFiles%\\Google\\Chrome\\Application\\chrome.exe"),
                    os.path.expandvars("%ProgramFiles(x86)%\\Google\\Chrome\\Application\\chrome.exe"),
                    os.path.expandvars("%LocalAppData%\\Google\\Chrome\\Application\\chrome.exe")
                ]
                chrome_found = any(os.path.exists(path) for path in chrome_paths)
            elif platform.system() == "Darwin":  # macOS
                chrome_paths = [
                    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                    os.path.expanduser("~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
                ]
                chrome_found = any(os.path.exists(path) for path in chrome_paths)
            else:  # Linux
                result = subprocess.run(["which", "google-chrome"], capture_output=True, text=True)
                chrome_found = result.returncode == 0
                
            if chrome_found:
                self.log("Google Chrome found")
            else:
                self.log("Google Chrome not found! The app will try to use Chromium or other compatible browsers.", "warning")
        except Exception as e:
            self.log(f"Error checking dependencies: {e}", "error")
            
    def browse_path(self):
        """Open dialog to choose download path"""
        path = filedialog.askdirectory()
        if path:
            self.download_path = path
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, path)
            self.log(f"Download path set to: {path}")
            
    def handle_login(self):
        """Open browser for YouTube login and save cookies"""
        self.log("Starting login process...")
        threading.Thread(target=self._login_process, daemon=True).start()
        
    def show_save_cookies_button(self):
        """Không cần làm gì nữa, nút luôn hiển thị"""
        self.log("Đã gọi show_save_cookies_button")
        
    def _login_process(self):
        """Handle the browser login process in a separate thread"""
        try:
            self.update_status("Opening browser for login...", start_progress=True)
            
            # Setup Chrome options
            chrome_options = Options()
            chrome_options.add_argument("--start-maximized")
            chrome_options.add_argument("--disable-infobars")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option("useAutomationExtension", False)
            chrome_options.add_experimental_option("detach", True)  # Detach browser from driver
            
            # Create and start browser
            self.browser = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
            self.browser.get("https://www.youtube.com/")
            
            self.update_status("Please login to YouTube in the opened browser...")
            self.log("Browser opened. Please login to your YouTube account.")
            self.log("IMPORTANT: After login, click the 'Save Cookies' button below BEFORE closing the browser.")
            
            # Thay vì tạo nút trực tiếp, gọi qua main thread
            self.root.after(0, self.show_save_cookies_button)
            
        except Exception as e:
            self.log(f"Error during login process: {e}", "error")
            self.update_status(f"Login failed: {str(e)}", stop_progress=True)
            
            # Remove the save cookies button if it exists
            if hasattr(self, 'save_cookies_button'):
                self.save_button_frame.destroy()
                del self.save_cookies_button
                del self.save_button_frame
                
            # Make sure the browser is closed on error
            if self.browser:
                try:
                    self.browser.quit()
                except:
                    pass
                    
    def _save_cookies(self):
        """Save cookies from the current browser session"""
        try:
            if not self.browser:
                self.log("Browser is not open. Cannot save cookies.", "error")
                messagebox.showerror("Error", "Browser is not open. Please login first.")
                return
            self.log("Saving cookies...")
            self.update_status("Saving cookies...", stop_progress=False)
            # Save cookies
            cookies = self.browser.get_cookies()
            os.makedirs(os.path.dirname(self.cookie_path), exist_ok=True)
            with open(self.cookie_path, 'wb') as f:
                pickle.dump(cookies, f)
            self.log("Cookies saved successfully!")
            self.cookies_loaded = True
            self.update_login_status()
            self.update_status("Login successful", stop_progress=True)
            # Show a confirmation message
            messagebox.showinfo("Success", "Cookies saved successfully! You can now close the browser.")
        except Exception as e:
            self.log(f"Error saving cookies: {e}", "error")
            self.update_status(f"Failed to save cookies: {str(e)}", stop_progress=True)
    
    def clear_cookies(self):
        """Clear saved cookies"""
        if os.path.exists(self.cookie_path):
            try:
                os.remove(self.cookie_path)
                self.log("Cookies cleared successfully")
                self.cookies_loaded = False
                self.update_login_status()
            except Exception as e:
                self.log(f"Error clearing cookies: {e}", "error")
        else:
            self.log("No cookies found to clear")
            
    def start_download(self):
        """Start the download process for the YouTube channel"""
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a YouTube channel URL")
            return
            
        if not self.cookies_loaded and not messagebox.askyesno(
            "No Login", 
            "You haven't logged in to YouTube. Some videos might not be available without login. Continue anyway?"
        ):
            return
            
        threading.Thread(target=self._download_process, args=(url,), daemon=True).start()
        
    def _download_process(self, url):
        """Execute the download process in a separate thread"""
        try:
            self.update_status("Preparing download...", start_progress=True)
            
            # Create download directory
            download_path = self.path_entry.get().strip()
            if not download_path:
                download_path = self.download_path
                
            os.makedirs(download_path, exist_ok=True)
            
            # Build the yt-dlp command
            cmd = ["yt-dlp"]
            
            # Add cookie file if available
            if self.cookies_loaded and os.path.exists(self.cookie_path):
                # Convert cookies to yt-dlp compatible format
                self.log("Converting cookies to yt-dlp format...")
                cookies_txt_path = os.path.join(os.path.dirname(self.cookie_path), "cookies.txt")
                self._convert_cookies_to_txt(self.cookie_path, cookies_txt_path)
                cmd.extend(["--cookies", cookies_txt_path])
            
            # Add output template
            output_template = os.path.join(download_path, "%(uploader)s/%(upload_date>%Y-%m-%d)s - %(title)s.%(ext)s")
            cmd.extend(["-o", output_template])
            
            # Add options
            if self.download_thumbnails.get():
                cmd.append("--write-thumbnail")
                
            if self.download_descriptions.get():
                cmd.append("--write-description")
                
            if self.download_subtitles.get():
                cmd.extend(["--write-sub", "--sub-lang", "en"])
                
            if self.best_quality.get():
                cmd.extend(["-f", "bestvideo[ext=mp4][vcodec!=none]+bestaudio[ext=m4a][acodec!=none]/best[ext=mp4][vcodec!=none][acodec!=none]"])
                
            # Add other useful options
            cmd.extend(["--ignore-errors", "--continue", "--no-overwrites"])
            
            # Add limit if specified
            try:
                limit = int(self.limit_entry.get())
                if limit > 0:
                    cmd.extend(["--playlist-end", str(limit)])
            except ValueError:
                pass
                
            # Add the URL
            cmd.append(url)
            
            # Log the command
            self.log(f"Executing command: {' '.join(cmd)}")
            
            # Start the download process
            self.update_status("Downloading videos...", stop_progress=False)
            
            # Create process
            process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Read output in real-time
            for line in process.stdout:
                line = line.strip()
                # Nếu có phần trăm, chỉ cập nhật status_label
                if "download" in line.lower() and "%" in line:
                    try:
                        percent_str = line.split("%", 1)[0].split()[-1]
                        percent = float(percent_str)
                        self.update_progress(percent)
                        self.root.after(0, lambda p=percent: self.status_label.config(text=f"Đang tải: {p:.1f}%"))
                    except:
                        pass
                else:
                    self.log(line)
                        
            # Wait for process to complete
            process.wait()
            
            if process.returncode == 0:
                self.update_status("Download completed successfully!", stop_progress=True)
                self.log("Download completed successfully!")
                # Hiển thị danh sách video vừa tải
                self.root.after(0, lambda: self.show_downloaded_videos(download_path))
            else:
                self.update_status(f"Download failed with exit code {process.returncode}", stop_progress=True)
                self.log(f"Download failed with exit code {process.returncode}", "error")
                
        except Exception as e:
            self.log(f"Error during download: {e}", "error")
            self.update_status(f"Download error: {str(e)}", stop_progress=True)
            
    def _convert_cookies_to_txt(self, pickle_file, txt_file):
        """Convert cookies from pickle format to Netscape format for yt-dlp"""
        try:
            # Load pickle cookies
            with open(pickle_file, 'rb') as f:
                cookies = pickle.load(f)
                
            # Convert to Netscape format
            with open(txt_file, 'w') as f:
                f.write("# Netscape HTTP Cookie File\n")
                
                for cookie in cookies:
                    secure = "TRUE" if cookie.get('secure', False) else "FALSE"
                    http_only = "TRUE" if cookie.get('httpOnly', False) else "FALSE"
                    expires = str(int(cookie.get('expiry', 0))) if 'expiry' in cookie else "0"
                    
                    # Format: domain, flag, path, secure, expires, name, value
                    cookie_line = f"{cookie.get('domain', '')}\t"
                    cookie_line += "TRUE\t"  # Include subdomains
                    cookie_line += f"{cookie.get('path', '/')}\t"
                    cookie_line += f"{secure}\t"
                    cookie_line += f"{expires}\t"
                    cookie_line += f"{cookie.get('name', '')}\t"
                    cookie_line += f"{cookie.get('value', '')}"
                    
                    f.write(cookie_line + "\n")
                    
            self.log(f"Cookies converted successfully to {txt_file}")
            return True
        except Exception as e:
            self.log(f"Error converting cookies: {e}", "error")
            return False
            
    def update_status(self, message, start_progress=False, stop_progress=True):
        """Update the status display"""
        def _update():
            self.status_label.config(text=message)
            
            if start_progress:
                self.progress_bar.start(10)
            elif stop_progress:
                self.progress_bar.stop()
                self.progress_var.set(100)  # Show as completed
                
        self.root.after(0, _update)
        
    def update_progress(self, value):
        """Update the progress bar with a percentage value"""
        def _update():
            self.progress_var.set(value)
            
        self.root.after(0, _update)
        
    def log(self, message, level="info"):
        """Add a message to the log"""
        def _log():
            self.console_text.insert(tk.END, message + "\n")
            self.console_text.see(tk.END)  # Scroll to end
            
            # Color coding by level
            if level == "error":
                self.console_text.tag_add("error", "end-1l linestart", "end-1l lineend")
                self.console_text.tag_config("error", foreground="red")
            elif level == "warning":
                self.console_text.tag_add("warning", "end-1l linestart", "end-1l lineend")
                self.console_text.tag_config("warning", foreground="orange")
                
        # Log to file as well
        if level == "error":
            logging.error(message)
        elif level == "warning":
            logging.warning(message)
        else:
            logging.info(message)
            
        self.root.after(0, _log)
        
    def show_downloaded_videos(self, download_path):
        """Quét thư mục download và hiển thị các file video vừa tải vào bảng"""
        self.video_tree.delete(*self.video_tree.get_children())
        # Lấy tất cả file mp4, mkv, webm trong thư mục con
        for ext in ("mp4", "mkv", "webm"):
            for file in glob.glob(os.path.join(download_path, "**", f"*.{ext}"), recursive=True):
                try:
                    mtime = os.path.getmtime(file)
                    timestr = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
                    self.video_tree.insert("", "end", values=(os.path.basename(file), timestr))
                except Exception as e:
                    pass
        
    def run(self):
        """Start the application"""
        self.root.mainloop()

def main():
    """Main entry point"""
    app = YouTubeDownloader()
    app.run()

if __name__ == "__main__":
    main()
