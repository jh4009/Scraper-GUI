import customtkinter as ctk
import requests
from bs4 import BeautifulSoup
import os
import zipfile
import io
from urllib.parse import urljoin, urlparse
import re
from PIL import Image, ImageTk
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import List, Tuple, Dict
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import logging
import platform
import json
import csv
import PyPDF2
import pyperclip

# Import CTkToolTip from the correct package
from CTkToolTip import CTkToolTip

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("green")

class WebScraperApp:
    def __init__(self, root: ctk.CTk):
        self.root = root
        self.root.title("Web Scraper")
        self.root.geometry("1200x800")
        
        self.image_data: Dict[str, bytes] = {}
        self.gallery_images: List[Tuple[ImageTk.PhotoImage, str, Tuple[int, int]]] = []
        self.all_image_urls: List[str] = []
        self.text_content: str = ""
        self.table_data: List[List[List[str]]] = []
        self.movie_details: Dict = {}
        self.book_details: Dict = {}
        self.video_urls: Tuple[str, ...] = ()
        self.ebay_products: List[Dict] = []
        self.news_headlines: Tuple[str, ...] = ()
        self.pdf_links: List[Dict] = []
        
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        self.image_formats = ["all", "png", "jpg"]
        self.video_formats = ["all", "mp4", "avi", "mkv", "mov", "webm"]
        
        self.scraping_thread = None
        self.cancel_event = threading.Event()
        self.progress_value = 0
        
        self.ebay_scrollable_frame_visible = False
        
        self.setup_ui()
        self.root.after(100, self.update_content)

    def setup_ui(self):
        self.main_frame = ctk.CTkFrame(master=self.root)
        self.main_frame.pack(pady=20, padx=20, fill="both", expand=True)

        self.header_label = ctk.CTkLabel(master=self.main_frame, text="Web Scraper", font=("Helvetica", 24, "bold"))
        self.header_label.pack(pady=10)
        CTkToolTip(self.header_label, message="Web Scraper Application")

        self.url_label = ctk.CTkLabel(master=self.main_frame, text="Enter URL or Search Term:", font=("Helvetica", 14))
        self.url_label.pack(pady=5)
        CTkToolTip(self.url_label, message="Enter website URL or search term for movies/books")
        self.url_entry = ctk.CTkEntry(master=self.main_frame, placeholder_text="e.g., https://brainstation-23.com or movie/book name", width=600)
        self.url_entry.pack(pady=5)
        CTkToolTip(self.url_entry, message="Type URL or search query here")

        self.data_type_frame = ctk.CTkFrame(master=self.main_frame)
        self.data_type_frame.pack(pady=5)
        self.data_type_label = ctk.CTkLabel(master=self.data_type_frame, text="Select Data Type:", font=("Helvetica", 14))
        self.data_type_label.pack(side="left", padx=5)
        CTkToolTip(self.data_type_label, message="Choose what to scrape")
        self.data_type_var = ctk.StringVar(value="Images")
        self.data_type_dropdown = ctk.CTkOptionMenu(master=self.data_type_frame, 
                                                  values=["Images", "Text", "Tables", "Movie Details", "Book Details", "Videos", "eBay Products", "News Headlines", "PDF Links"], 
                                                  variable=self.data_type_var, 
                                                  command=self.update_content)
        self.data_type_dropdown.pack(side="left", padx=5)
        CTkToolTip(self.data_type_dropdown, message="Select data type to extract")
        
        self.scrape_button = ctk.CTkButton(master=self.data_type_frame, text="Scrape Now", command=self.scrape_data, fg_color="#1e40af", hover_color="#1e3a8a")
        self.scrape_button.pack(side="left", padx=5)
        CTkToolTip(self.scrape_button, message="Start scraping process")
        
        self.cancel_button = ctk.CTkButton(master=self.data_type_frame, text="Cancel", command=self.cancel_scrape, fg_color="#dc2626", hover_color="#b91c1c", state="disabled")
        self.cancel_button.pack(side="left", padx=5)
        CTkToolTip(self.cancel_button, message="Cancel ongoing scrape")

        self.loading_label = ctk.CTkLabel(master=self.main_frame, text="", font=("Helvetica", 14))
        self.loading_label.pack(pady=5)
        
        self.progress_bar = ctk.CTkProgressBar(master=self.main_frame, width=400)
        self.progress_bar.pack(pady=5)
        self.progress_bar.set(0)
        self.progress_bar.pack_forget()
        CTkToolTip(self.progress_bar, message="Scraping progress")
        
        self.result_label = ctk.CTkLabel(master=self.main_frame, text="", font=("Helvetica", 14))
        self.result_label.pack(pady=10)

        self.main_content_frame = ctk.CTkFrame(master=self.main_frame)
        self.main_content_frame.pack(fill="both", expand=True)

        self.content_frame = ctk.CTkFrame(master=self.main_content_frame)
        self.content_frame.pack(fill="both", expand=True, pady=(0, 0))

        self.canvas = ctk.CTkCanvas(self.content_frame, bg="#ffffff")
        self.scrollbar = ctk.CTkScrollbar(self.content_frame, orientation="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.image_label = ctk.CTkLabel(self.content_frame, text="", width=200, height=300)
        self.text_box = ctk.CTkTextbox(self.content_frame, width=900, height=400, state="disabled")
        
        # Initialize ebay_scrollable_frame
        self.ebay_scrollable_frame = ctk.CTkScrollableFrame(self.content_frame, width=1100)
        self.ebay_scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.ebay_scrollable_frame_visible = True
        self.ebay_scrollable_frame.pack_forget()
        self.ebay_scrollable_frame_visible = False

        self.filter_frame = ctk.CTkFrame(master=self.main_content_frame, height=80)
        self.filter_frame.pack(side="bottom", fill="x", pady=(10, 0))
        self.filter_frame.pack_propagate(False)
        self.inner_filter_frame = ctk.CTkFrame(master=self.filter_frame)
        self.inner_filter_frame.pack(expand=True)

        self.num_tables_frame = ctk.CTkFrame(master=self.inner_filter_frame)
        self.num_tables_frame.pack(side="left", padx=5)
        self.num_tables_label = ctk.CTkLabel(master=self.num_tables_frame, text="Number of tables:", font=("Helvetica", 14))
        self.num_tables_label.pack(side="left", padx=5)
        CTkToolTip(self.num_tables_label, message="Limit number of tables displayed")
        self.num_tables_entry = ctk.CTkEntry(master=self.num_tables_frame, width=100, placeholder_text="All")
        self.num_tables_entry.pack(side="left", padx=5)
        CTkToolTip(self.num_tables_entry, message="Enter number or leave for all")

        self.num_items_frame = ctk.CTkFrame(master=self.inner_filter_frame)
        self.num_items_frame.pack(side="left", padx=5)
        self.num_items_label = ctk.CTkLabel(master=self.num_items_frame, text="Number of items:", font=("Helvetica", 14))
        self.num_items_label.pack(side="left", padx=5)
        CTkToolTip(self.num_items_label, message="Limit number of items displayed")
        self.num_items_entry = ctk.CTkEntry(master=self.num_items_frame, width=100, placeholder_text="All")
        self.num_items_entry.pack(side="left", padx=5)
        CTkToolTip(self.num_items_entry, message="Enter number or leave for all")

        self.format_frame = ctk.CTkFrame(master=self.inner_filter_frame)
        self.format_frame.pack(side="left", padx=5)
        self.format_label = ctk.CTkLabel(master=self.format_frame, text="Format:", font=("Helvetica", 14))
        self.format_label.pack(side="left", padx=5)
        CTkToolTip(self.format_label, message="Select file format filter")
        self.format_var = ctk.StringVar(value="all")
        self.format_dropdown = ctk.CTkOptionMenu(master=self.format_frame, values=self.image_formats, variable=self.format_var)
        self.format_dropdown.pack(side="left", padx=5)
        CTkToolTip(self.format_dropdown, message="Choose specific format or all")

        self.export_format_frame = ctk.CTkFrame(master=self.inner_filter_frame)
        self.export_format_frame.pack(side="left", padx=5)
        self.export_format_label = ctk.CTkLabel(master=self.export_format_frame, text="Export Format:", font=("Helvetica", 14))
        self.export_format_label.pack(side="left", padx=5)
        CTkToolTip(self.export_format_label, message="Select export file format")
        self.export_format_var = ctk.StringVar(value="zip")
        self.export_format_dropdown = ctk.CTkOptionMenu(master=self.export_format_frame, 
                                                        values=["csv", "json", "zip"], 
                                                        variable=self.export_format_var, 
                                                        command=self.update_export_format)
        self.export_format_dropdown.pack(side="left", padx=5)
        CTkToolTip(self.export_format_dropdown, message="Choose export format")

        self.button_frame_bottom = ctk.CTkFrame(master=self.inner_filter_frame)
        self.button_frame_bottom.pack(side="left", padx=5)
        self.update_button = ctk.CTkButton(master=self.button_frame_bottom, text="Update Display", command=self.update_content, fg_color="#1e40af", hover_color="#1e3a8a")
        self.update_button.pack(side="left", padx=5)
        CTkToolTip(self.update_button, message="Refresh display with current filters")
        self.export_button = ctk.CTkButton(master=self.button_frame_bottom, text="Export", command=self.export_data, fg_color="#16a34a", hover_color="#15803d")
        self.export_button.pack(side="left", padx=5)
        CTkToolTip(self.export_button, message="Export scraped data to file")

        self.mode_frame = ctk.CTkFrame(master=self.inner_filter_frame)
        self.mode_frame.pack(side="left", padx=5)
        self.dark_mode_button = ctk.CTkButton(master=self.mode_frame, text="Dark Mode", command=self.toggle_dark_mode)
        self.dark_mode_button.pack(side="left", padx=5)
        CTkToolTip(self.dark_mode_button, message="Toggle between light/dark mode")

        self.status_frame = ctk.CTkFrame(master=self.root, height=30)
        self.status_frame.pack(side="bottom", fill="x", pady=(0, 10), padx=20)
        self.status_frame.pack_propagate(False)
        self.status_label = ctk.CTkLabel(master=self.status_frame, text="Ready", font=("Helvetica", 12), anchor="w")
        self.status_label.pack(side="left", padx=5)
        self.status_detail = ctk.CTkLabel(master=self.status_frame, text="", font=("Helvetica", 12), anchor="e")
        self.status_detail.pack(side="right", padx=5)

        self.canvas.bind("<Configure>", self.on_canvas_resize)

    def update_status(self, message, color="black"):
        self.status_label.configure(text=message, text_color=color)
        self.status_detail.configure(text=f"Last operation: {self.result_label.cget('text')}")

    def update_export_format(self, *args):
        data_type = self.data_type_var.get()
        if data_type == "Images":
            self.export_format_dropdown.configure(values=["csv", "json", "zip"])
            self.export_format_var.set("zip")
        else:
            self.export_format_dropdown.configure(values=["csv", "json"])
            self.export_format_var.set("csv")
        self.update_status("Export format updated")

    def ensure_ebay_scrollable_frame(self):
        """Ensure ebay_scrollable_frame exists and is properly initialized."""
        if not hasattr(self, 'ebay_scrollable_frame') or not self.ebay_scrollable_frame.winfo_exists():
            self.ebay_scrollable_frame = ctk.CTkScrollableFrame(self.content_frame, width=1100)
            self.ebay_scrollable_frame_visible = False
        if not self.ebay_scrollable_frame_visible:
            self.ebay_scrollable_frame.pack(fill="both", expand=True, padx=10, pady=10)
            self.ebay_scrollable_frame_visible = True

    def update_content(self, data_type=None) -> None:
        data_type = data_type or self.data_type_var.get()
        
        # Clear content frame widgets except for specific ones
        for widget in self.content_frame.winfo_children():
            if widget not in (self.text_box, self.image_label, self.canvas, self.scrollbar, self.ebay_scrollable_frame):
                widget.destroy()

        # Hide all main display widgets
        self.canvas.pack_forget()
        self.scrollbar.pack_forget()
        self.image_label.pack_forget()
        self.text_box.pack_forget()
        if self.ebay_scrollable_frame_visible and self.ebay_scrollable_frame.winfo_exists():
            self.ebay_scrollable_frame.pack_forget()
            self.ebay_scrollable_frame_visible = False
    
        self.update_export_format()
    
        # Update display based on data type
        if data_type == "Images":
            self.update_image_list()
        elif data_type == "Text":
            self.update_text_display()
        elif data_type == "Tables":
            self.update_table_display()
        elif data_type == "Movie Details":
            self.update_movie_display()
        elif data_type == "Book Details":
            self.update_book_display()
        elif data_type == "Videos":
            self.update_video_display()
        elif data_type == "eBay Products":
            self.update_ebay_display()
        elif data_type == "News Headlines":
            self.update_news_display()
        elif data_type == "PDF Links":
            self.update_pdf_display()
        self.update_status(f"Displaying {data_type}")

    def scrape_data(self) -> None:
        url = self.url_entry.get().strip()
        if not url:
            self.result_label.configure(text="Please enter a URL or search term!", text_color="red")
            self.update_status("URL missing", "red")
            return
        if self.data_type_var.get() in ["Movie Details", "Book Details"] and not url.replace(" ", "").isalnum():
            self.result_label.configure(text="Please enter a valid movie or book name!", text_color="red")
            self.update_status("Invalid movie/book name", "red")
            return
        if not self.is_valid_url(url) and self.data_type_var.get() not in ["Movie Details", "Book Details", "eBay Products"]:
            url = "https://" + url if not url.startswith(("http://", "https://")) else url
            if not self.is_valid_url(url):
                self.result_label.configure(text="Invalid URL format!", text_color="red")
                self.update_status("Invalid URL", "red")
                return
        
        self.show_loading(True)
        self.progress_bar.pack(pady=5)
        self.progress_bar.set(0)
        self.cancel_event.clear()
        self.scrape_button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.update_status("Scraping started")
        
        self.scraping_thread = threading.Thread(target=lambda: self.perform_scrape(url), daemon=True)
        self.scraping_thread.start()
        self.root.after(100, self.update_progress)

    def update_progress(self):
        if self.scraping_thread and self.scraping_thread.is_alive():
            self.progress_value = min(self.progress_value + 0.05, 0.95)
            self.progress_bar.set(self.progress_value)
            self.update_status(f"Scraping in progress ({int(self.progress_value * 100)}%)")
            self.root.after(100, self.update_progress)
        else:
            self.progress_bar.set(1.0)
            self.update_status("Scraping completed", "green")
            self.root.after(500, self.hide_progress)

    def hide_progress(self):
        self.progress_bar.pack_forget()
        self.scrape_button.configure(state="normal")
        self.cancel_button.configure(state="disabled")
        self.update_status("Ready")

    def cancel_scrape(self):
        if self.scraping_thread and self.scraping_thread.is_alive():
            self.cancel_event.set()
            self.result_label.configure(text="Scraping cancelled!", text_color="orange")
            self.show_loading(False)
            self.hide_progress()
            self.update_status("Scraping cancelled", "orange")

    def is_valid_url(self, url: str) -> bool:
        return bool(re.match(r'^https?://[^\s/$.?#].[^\s]*$', url))

    def perform_scrape(self, url: str) -> None:
        self.image_data.clear()
        self.gallery_images.clear()
        self.all_image_urls.clear()
        self.text_content = ""
        self.table_data.clear()
        self.movie_details.clear()
        self.book_details.clear()
        self.video_urls = ()
        self.ebay_products.clear()
        self.news_headlines = ()
        self.pdf_links.clear()

        data_type = self.data_type_var.get()
        try:
            if data_type == "Images":
                self.result_label.configure(text="Scraping images...")
                self.all_image_urls = self.scrape_images(url, self.format_var.get()) or []
                if not self.all_image_urls:
                    self.result_label.configure(text="No images found!", text_color="red")
                    self.update_status("No images found", "red")
                else:
                    self.update_content()
            elif data_type == "Text":
                self.result_label.configure(text="Scraping text...")
                response = requests.get(url, headers=self.headers, timeout=10)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                self.text_content = soup.get_text(separator="\n", strip=True)
                if not self.text_content:
                    self.result_label.configure(text="No text found!", text_color="red")
                    self.update_status("No text found", "red")
                else:
                    self.update_content()
            elif data_type == "Tables":
                self.result_label.configure(text="Scraping tables...")
                self.table_data = self.scrape_tables(url) or []
                if not self.table_data:
                    self.result_label.configure(text="No tables found!", text_color="red")
                    self.update_status("No tables found", "red")
                else:
                    self.update_content()
            elif data_type == "Movie Details":
                self.result_label.configure(text="Scraping movie details...")
                self.movie_details = self.scrape_movie_details(url) or {"error": "No data found!"}
                self.update_content()
            elif data_type == "Book Details":
                self.result_label.configure(text="Scraping book details...")
                self.book_details = self.scrape_book_details(url) or {"error": "No data found!"}
                self.update_content()
            elif data_type == "Videos":
                self.result_label.configure(text="Scraping videos...")
                self.video_urls = self.scrape_videos(url, self.format_var.get()) or ()
                if not self.video_urls:
                    self.result_label.configure(text="No videos found!", text_color="red")
                    self.update_status("No videos found", "red")
                else:
                    self.update_content()
            elif data_type == "eBay Products":
                self.result_label.configure(text="Scraping eBay products...")
                self.ebay_products = self.scrape_ebay_product(url) or []
                if not self.ebay_products:
                    self.result_label.configure(text="No eBay products found!", text_color="red")
                    self.update_status("No eBay products found", "red")
                else:
                    self.update_content()
            elif data_type == "News Headlines":
                self.result_label.configure(text="Scraping news headlines...")
                self.news_headlines = self.scrape_news_headlines(url) or ()
                if not self.news_headlines:
                    self.result_label.configure(text="No news headlines found!", text_color="red")
                    self.update_status("No news headlines found", "red")
                else:
                    self.update_content()
            elif data_type == "PDF Links":
                self.result_label.configure(text="Scraping PDF links...")
                self.pdf_links = self.scrape_pdf_links(url) or []
                if not self.pdf_links:
                    self.result_label.configure(text="No PDF links found!", text_color="red")
                    self.update_status("No PDF links found", "red")
                else:
                    self.update_content()
        except Exception as e:
            self.result_label.configure(text=f"Failed to scrape: {str(e)}", text_color="red")
            self.update_status(f"Scraping failed: {str(e)}", "red")
        finally:
            self.show_loading(False)

    def scrape_tables(self, url):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            tables = soup.find_all('table')
            table_data = []
            for table in tables:
                headers = table.find_all('th')
                header_row = [header.text.strip() for header in headers] if headers else []
                rows = table.find_all('tr')
                table_rows = []
                start_idx = 1 if header_row else 0
                for row in rows[start_idx:]:
                    cols = row.find_all('td')
                    if cols:
                        table_rows.append([col.text.strip() for col in cols])
                if header_row:
                    table_rows.insert(0, header_row)
                if table_rows:
                    table_data.append(table_rows)
            return table_data
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
            return None

    def scrape_images(self, url, image_format):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            images = soup.find_all(['img', 'image'])
            image_urls = []
            for img in images:
                img_url = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
                if img_url:
                    full_url = urljoin(url, img_url)
                    image_urls.append(full_url)
            if not image_urls:
                logger.info(f"No images found with BS4 at {url}, trying Selenium")
                chrome_options = Options()
                chrome_options.add_argument("--headless")
                driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
                driver.get(url)
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "img")))
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                images = soup.find_all(['img', 'image'])
                for img in images:
                    img_url = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
                    if img_url:
                        full_url = urljoin(url, img_url)
                        image_urls.append(full_url)
                driver.quit()
            return image_urls if image_urls else None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
            return None

    def scrape_movie_details(self, movie_name):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        }
        try:
            search_url = f"https://www.imdb.com/find?q={movie_name.replace(' ', '+')}&ref_=nv_sr_sm"
            search_response = requests.get(search_url, headers=headers, timeout=10)
            search_response.raise_for_status()
            search_soup = BeautifulSoup(search_response.content, 'html.parser')
            first_result = search_soup.select_one('.ipc-metadata-list-summary-item a')
            if not first_result:
                return {"error": "No movie found with that name."}
            movie_url = "https://www.imdb.com" + first_result.get('href', '')
            movie_response = requests.get(movie_url, headers=headers, timeout=10)
            movie_response.raise_for_status()
            soup = BeautifulSoup(movie_response.content, 'html.parser')
            title_elem = soup.select_one('h1')
            title = title_elem.text.strip() if title_elem else "N/A"
            poster_elem = soup.select_one('img.ipc-image')
            poster_url = poster_elem.get('src', "N/A") if poster_elem else "N/A"
            year_elem = soup.select_one('a[href*="/releaseinfo"]')
            year = year_elem.text.strip() if year_elem else "N/A"
            rating_elem = soup.select_one('div[data-testid="hero-rating-bar__aggregate-rating__score"] span')
            rating = f"{rating_elem.text.strip()}/10" if rating_elem else "N/A"
            plot_elem = soup.select_one('span[data-testid="plot-xl"]')
            plot = plot_elem.text.strip() if plot_elem else "N/A"
            genre_elems = soup.select('.ipc-chip__text')
            genres = [genre.text.strip() for genre in genre_elems] if genre_elems else ["N/A"]
            movie_details = {
                "name": title,
                "poster_url": poster_url,
                "year": year,
                "rating": rating,
                "plot": plot,
                "genre": ', '.join(genres),
                "movie_link": movie_url
            }
            logger.info(f"Scraped movie details for '{movie_name}': {movie_details}")
            return movie_details
        except requests.exceptions.RequestException as e:
            error_msg = {"error": f"Network error: {e}"}
            logger.error(f"Network error in scrape_movie_details: {error_msg}")
            return error_msg
        except Exception as e:
            error_msg = {"error": f"An unexpected error occurred: {e}"}
            logger.error(f"Unexpected error in scrape_movie_details: {error_msg}")
            return error_msg
        
    def scrape_book_details(self, book_name):
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124"}
        try:
            search_url = f"https://openlibrary.org/search?q={book_name.replace(' ', '+')}&mode=everything"
            search_response = requests.get(search_url, headers=headers, timeout=10)
            search_response.raise_for_status()
            search_soup = BeautifulSoup(search_response.content, 'html.parser')
            first_result = search_soup.select_one('li.searchResultItem')
            if not first_result:
                return {"error": "No book found with that name."}
            title_elem = first_result.select_one('h3.booktitle a')
            title = title_elem.text.strip() if title_elem else "N/A"
            cover_elem = first_result.select_one('span.bookcover img')
            cover_url = "https:" + cover_elem['src'] if cover_elem else "N/A"
            author_elem = first_result.select_one('span.bookauthor a')
            author = author_elem.text.strip() if author_elem else "N/A"
            year_elem = first_result.select_one('span.resultDetails span')
            year = year_elem.text.strip().replace("First published in ", "") if year_elem else "N/A"
            rating_elem = first_result.select_one('span.ratingsByline span[itemprop="ratingValue"]')
            rating = rating_elem.text.strip() if rating_elem else "N/A"
            book_link = first_result.select_one('h3.booktitle a')['href'] if first_result.select_one('h3.booktitle a') else "N/A"
            detail_url = f"https://openlibrary.org{book_link}" if book_link != "N/A" else "N/A"
            description = "N/A"
            if detail_url != "N/A":
                detail_response = requests.get(detail_url, headers=headers, timeout=10)
                detail_response.raise_for_status()
                detail_soup = BeautifulSoup(detail_response.content, 'html.parser')
                description_elem = detail_soup.select_one('div.read-more__content')
                description = " ".join([p.text.strip() for p in description_elem.find_all('p') if not p.find('a')]) if description_elem else "N/A"
            book_details = {
                "name": title,
                "cover_url": cover_url,
                "author": author,
                "year": year,
                "rating": rating,
                "description": description,
                "book_link": detail_url
            }
            return book_details
        except requests.exceptions.RequestException as e:
            return {"error": f"Network error: {e}"}
        except Exception as e:
            return {"error": f"An error occurred: {e}"}

    def scrape_videos(self, url, video_format):
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            videos = soup.find_all('video')
            video_urls = []
            for video in videos:
                video_sources = video.find_all('source')
                for source in video_sources:
                    video_url = source.get('src')
                    if video_url:
                        parsed_url = urlparse(video_url)
                        clean_url = parsed_url.scheme + "://" + parsed_url.netloc + parsed_url.path
                        extension = os.path.splitext(clean_url)[1].lower()
                        extension = extension[1:] if extension else ""
                        if video_format != 'all' and extension != video_format.lower():
                            continue
                        if not video_url.startswith(('http://', 'https://')):
                            video_url = urljoin(url, video_url)
                        video_urls.append(video_url)
            if not video_urls:
                logger.info(f"No videos found with BS4 at {url}, trying Selenium")
                chrome_options = Options()
                chrome_options.add_argument("--headless")
                driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
                driver.get(url)
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "video")))
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                videos = soup.find_all('video')
                for video in videos:
                    video_sources = video.find_all('source')
                    for source in video_sources:
                        video_url = source.get('src')
                        if video_url:
                            parsed_url = urlparse(video_url)
                            clean_url = parsed_url.scheme + "://" + parsed_url.netloc + parsed_url.path
                            extension = os.path.splitext(clean_url)[1].lower()
                            extension = extension[1:] if extension else ""
                            if video_format != 'all' and extension != video_format.lower():
                                continue
                            if not video_url.startswith(('http://', 'https://')):
                                video_url = urljoin(url, video_url)
                            video_urls.append(video_url)
                driver.quit()
            return tuple(video_urls) if video_urls else ()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error in scrape_videos: {e}")
            return None

    def scrape_ebay_product(self, product_name):
        search_url = f"https://www.ebay.com/sch/i.html?_nkw={product_name.replace(' ', '+')}&_sop=12"
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        try:
            driver.get(search_url)
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'li.s-item')))
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            product_details = []
            product_listings = soup.select('li.s-item.s-item__pl-on-bottom')
            if not product_listings:
                logger.warning("No product listings found with standard selector, trying fallback.")
                product_listings = soup.select('li[data-viewport]')

            for product in product_listings:
                try:
                    title_elem = product.select_one('.s-item__title')
                    title = title_elem.text.strip() if title_elem else "N/A"
                    link_elem = product.select_one('a.s-item__link')
                    link = link_elem['href'] if link_elem else "N/A"
                    image_elem = product.select_one('img')
                    image_url = None
                    if image_elem:
                        image_url = image_elem.get('data-src') or image_elem.get('src')
                    image_url = image_url if image_url else "https://via.placeholder.com/150?text=No+Image"
                    price_elem = product.select_one('.s-item__price')
                    price = price_elem.text.strip() if price_elem else "N/A"
                    rating_elem = product.select_one('.s-item__reviews')
                    rating = rating_elem.text.strip() if rating_elem else "N/A"
                    if title != "N/A" and link != "N/A":
                        product_details.append({
                            "title": title,
                            "link": link,
                            "image_url": image_url,
                            "price": price,
                            "rating": rating
                        })
                except AttributeError as e:
                    logger.error(f"Error parsing product: {e}")
                    continue
            if not product_details:
                logger.error("No valid products parsed from eBay.")
                return None
            logger.info(f"Scraped {len(product_details)} products from eBay for '{product_name}'")
            return product_details
        except Exception as e:
            logger.error(f"Error fetching eBay with Selenium: {e}")
            return None
        finally:
            driver.quit()

    def scrape_news_headlines(self, url):
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124"}
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            headlines = soup.find_all(['h1', 'h2', 'h3'])
            if not headlines:
                headlines = soup.find_all('a', class_=lambda x: x and ('excerpt' in x.lower() or 'title' in x.lower() or 'headline' in x.lower()))
            if not headlines:
                headlines = soup.find_all('a')
            def is_valid_headline(text):
                if len(text) < 15 or any(phrase.lower() in text.lower() for phrase in ['home', 'about', 'contact', 'login', 'register']):
                    return False
                return True
            headline_texts = []
            for headline in headlines:
                text = headline.get_text().strip()
                if text and is_valid_headline(text) and text not in headline_texts:
                    headline_texts.append(text)
            return tuple(headline_texts) if headline_texts else None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching {url}: {e}")
            return None

    def scrape_pdf_links(self, url):
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124"}
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            pdf_links = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                if href.lower().endswith('.pdf') and href.startswith(('http://', 'https://')):
                    pdf_name = href.split('/')[-1].split('?')[0]
                    pdf_links.append({'url': href, 'name': pdf_name})
            if pdf_links:
                seen_urls = set()
                unique_pdf_links = [link for link in pdf_links if not (link['url'] in seen_urls or seen_urls.add(link['url']))]
                return unique_pdf_links
        except requests.exceptions.RequestException as e:
            logger.error(f"BS4 request failed: {e}")

        logger.info("No PDFs found with BS4, falling back to Selenium")
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

        driver = None
        try:
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
            driver.set_page_load_timeout(30)
            logger.info(f"Navigating to URL: {url}")
            driver.get(url)

            try:
                potential_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Documents') or contains(text(), 'Resources') or contains(text(), 'Show More')]")
                for button in potential_buttons:
                    try:
                        logger.info(f"Clicking button with text: {button.text}")
                        button.click()
                        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "a")))
                        break
                    except Exception as e:
                        logger.warning(f"Could not click button '{button.text}': {e}")
            except Exception as e:
                logger.warning(f"No relevant buttons found to click: {e}")

            try:
                WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "a")))
                logger.info("Page loaded successfully with Selenium")
            except Exception as e:
                logger.error(f"Failed to load page with Selenium: {e}")
                return None

            soup = BeautifulSoup(driver.page_source, 'html.parser')
            pdf_links = []
            for link in soup.find_all('a', href=True):
                href = link['href']
                if href.lower().endswith('.pdf'):
                    if not href.startswith(('http://', 'https://')):
                        base_url = url.rsplit('/', 1)[0]
                        href = os.path.join(base_url, href)
                    pdf_name = href.split('/')[-1].split('?')[0]
                    pdf_links.append({'url': href, 'name': pdf_name})

            seen_urls = set()
            unique_pdf_links = [link for link in pdf_links if not (link['url'] in seen_urls or seen_urls.add(link['url']))]
            return unique_pdf_links if unique_pdf_links else None
        except Exception as e:
            logger.error(f"Error fetching PDFs with Selenium: {e}")
            return None
        finally:
            if driver:
                driver.quit()

    def download_image(self, img_url: str) -> Tuple[str, bytes]:
        try:
            img_response = requests.get(img_url, headers=self.headers, timeout=5)
            img_response.raise_for_status()
            return img_url, img_response.content
        except Exception:
            return img_url, None

    def update_image_list(self) -> None:
        self.image_data.clear()
        self.gallery_images.clear()
        
        allowed_formats = {
            'png': ['.png'],
            'jpg': ['.jpg', '.jpeg'],
            'webp': ['.webp'],
            'gif': ['.gif'],
            'all': ['.png', '.jpg', '.jpeg', '.webp', '.gif']
        }
        selected_format = self.format_var.get()
        
        filtered_urls = [
            url for url in self.all_image_urls
            if any(url.lower().endswith(ext) for ext in allowed_formats[selected_format])
        ]
        
        num_items = self.num_items_entry.get().strip()
        num_items = int(num_items) if num_items.isdigit() and int(num_items) > 0 else len(filtered_urls)
        filtered_urls = filtered_urls[:min(num_items, len(filtered_urls))]
        
        if not filtered_urls:
            self.result_label.configure(text="No images match the updated criteria!", text_color="red")
            self.update_status("No images match criteria", "red")
            self.root.after(0, self.update_gallery)
            return
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            results = list(executor.map(self.download_image, filtered_urls))
        
        for img_url, content in results:
            if content:
                self.image_data[img_url] = content
                img = Image.open(io.BytesIO(content))
                img.thumbnail((400, 400), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.gallery_images.append((photo, img_url, img.size))
        
        self.root.after(0, self.update_gallery)

    def update_gallery(self) -> None:
        self.text_box.pack_forget()
        self.image_label.pack_forget()
        if self.ebay_scrollable_frame_visible and self.ebay_scrollable_frame.winfo_exists():
            self.ebay_scrollable_frame.pack_forget()
            self.ebay_scrollable_frame_visible = False
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        self.canvas.delete("all")
        if not self.gallery_images:
            self.result_label.configure(text="No images match the criteria!", text_color="red")
            self.update_status("No images to display", "red")
            return
        
        canvas_width = self.canvas.winfo_width() or 1100
        img_width = 400
        spacing = 20
        img_width_with_spacing = img_width + spacing
        
        num_columns = max(1, canvas_width // img_width_with_spacing)
        num_images = len(self.gallery_images)
        num_rows = (num_images + num_columns - 1) // num_columns
        
        y = 20
        max_row_height = 0
        for row in range(num_rows):
            start_idx = row * num_columns
            end_idx = min(start_idx + num_columns, num_images)
            images_in_row = end_idx - start_idx
            
            row_width = images_in_row * img_width_with_spacing - spacing
            start_x = (canvas_width - row_width) // 2
            
            x = start_x
            row_height = 0
            for i in range(start_idx, end_idx):
                photo, img_url, original_size = self.gallery_images[i]
                img_label = ctk.CTkLabel(self.canvas, image=photo, text="", cursor="hand2")
                img_label.image = photo
                img_label.bind("<Button-1>", lambda e, url=img_url: self.show_image_in_popup(url))
                self.canvas.create_window(x, y, anchor="nw", window=img_label)
                x += img_width_with_spacing
                row_height = max(row_height, original_size[1])
            
            y += max(220, row_height + 20)
            max_row_height = max(max_row_height, row_height)
        
        canvas_height = y
        self.canvas.configure(scrollregion=(0, 0, canvas_width, canvas_height))
        self.result_label.configure(text=f"Found {len(self.gallery_images)} images", text_color="black" if ctk.get_appearance_mode() == "Light" else "white")
        self.update_status(f"Displaying {len(self.gallery_images)} images")

    def update_text_display(self) -> None:
        self.image_label.pack_forget()
        if self.ebay_scrollable_frame_visible and self.ebay_scrollable_frame.winfo_exists():
            self.ebay_scrollable_frame.pack_forget()
            self.ebay_scrollable_frame_visible = False
        self.text_box.pack(fill="both", expand=True)
        
        self.text_box.configure(state="normal")
        self.text_box.delete("1.0", "end")
        self.text_box.insert("1.0", self.text_content)
        self.text_box.configure(state="disabled")
        self.result_label.configure(text=f"Text scraped ({len(self.text_content)} characters)", text_color="black" if ctk.get_appearance_mode() == "Light" else "white")
        self.update_status(f"Text displayed ({len(self.text_content)} characters)")

    def update_table_display(self) -> None:
        self.image_label.pack_forget()
        if self.ebay_scrollable_frame_visible and self.ebay_scrollable_frame.winfo_exists():
            self.ebay_scrollable_frame.pack_forget()
            self.ebay_scrollable_frame_visible = False
        self.text_box.pack(fill="both", expand=True)
        
        self.text_box.configure(state="normal")
        self.text_box.delete("1.0", "end")
        
        if not self.table_data:
            self.result_label.configure(text="No tables to display!", text_color="red")
            self.update_status("No tables to display", "red")
            return
        
        num_tables = self.num_tables_entry.get().strip()
        num_tables = int(num_tables) if num_tables.isdigit() and int(num_tables) > 0 else len(self.table_data)
        filtered_tables = self.table_data[:min(num_tables, len(self.table_data))]
        
        for table_idx, table in enumerate(filtered_tables, 1):
            self.text_box.insert("end", f"Table #{table_idx}:\n")
            for row in table:
                self.text_box.insert("end", "\t".join(row) + "\n")
            self.text_box.insert("end", "\n")
        
        self.text_box.configure(state="disabled")
        self.result_label.configure(text=f"Found {len(self.table_data)} tables (Displaying {len(filtered_tables)})", text_color="black" if ctk.get_appearance_mode() == "Light" else "white")
        self.update_status(f"Displaying {len(filtered_tables)} of {len(self.table_data)} tables")

    def update_movie_display(self) -> None:
        if self.ebay_scrollable_frame_visible and self.ebay_scrollable_frame.winfo_exists():
            self.ebay_scrollable_frame.pack_forget()
            self.ebay_scrollable_frame_visible = False
        self.image_label.pack_forget()
        self.text_box.pack_forget()
        
        details_frame = ctk.CTkFrame(self.content_frame)
        details_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        
        logger.info(f"Movie details in update_movie_display: {self.movie_details}")
        
        if "error" in self.movie_details:
            self.result_label.configure(text=self.movie_details["error"], text_color="red")
            self.update_status("Movie display error", "red")
            return
        
        if self.movie_details.get("poster_url", "N/A") != "N/A":
            try:
                img_response = requests.get(self.movie_details["poster_url"], headers=self.headers, timeout=5)
                img_response.raise_for_status()
                img = Image.open(io.BytesIO(img_response.content))
                img.thumbnail((400, 600), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.image_label.configure(image=photo)
                self.image_label.image = photo
                self.image_label.pack(side="left", padx=10, pady=10, fill="y")
            except Exception as e:
                logger.error(f"Failed to load poster: {str(e)}")
        
        details_text = ""
        for key, value in self.movie_details.items():
            if key not in ("poster_url", "movie_link"):
                details_text += f"{key.capitalize()}: {value}\n"
        
        logger.info(f"Details text to display: {details_text}")
        
        if not details_text.strip():
            details_text = "No details available.\n"
        
        details_label = ctk.CTkLabel(details_frame, text=details_text, font=("Helvetica", 18), wraplength=900, anchor="w", justify="left")
        details_label.pack(side="top", fill="both", expand=True)
        
        if self.movie_details.get("movie_link", "N/A") != "N/A":
            copy_link_button = ctk.CTkButton(details_frame, text="Copy Link", 
                                            command=lambda: self.copy_to_clipboard(self.movie_details["movie_link"]),
                                            fg_color="#1e40af", hover_color="#1e3a8a", width=80)
            copy_link_button.pack(side="top", pady=5)
        
        self.result_label.configure(text="Movie details scraped", text_color="black" if ctk.get_appearance_mode() == "Light" else "white")  
        self.update_status("Movie details displayed")

    def update_book_display(self) -> None:
        if self.ebay_scrollable_frame_visible and self.ebay_scrollable_frame.winfo_exists():
            self.ebay_scrollable_frame.pack_forget()
            self.ebay_scrollable_frame_visible = False
        self.image_label.pack_forget()
        self.text_box.pack_forget()
        
        details_frame = ctk.CTkFrame(self.content_frame)
        details_frame.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        logger.info(f"Book details in update_book_display: {self.book_details}")
        
        if "error" in self.book_details:
            self.result_label.configure(text=self.book_details["error"], text_color="red")
            self.update_status("Book display error", "red")
            return
        
        if self.book_details.get("cover_url", "N/A") != "N/A":
            try:
                img_response = requests.get(self.book_details["cover_url"], headers=self.headers, timeout=5)
                img_response.raise_for_status()
                img = Image.open(io.BytesIO(img_response.content))
                img.thumbnail((400, 600), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                self.image_label.configure(image=photo)
                self.image_label.image = photo
                self.image_label.pack(side="left", padx=10, pady=10, fill="y")
            except Exception as e:
                logger.error(f"Failed to load cover: {str(e)}")
        
        details_text = ""
        for key in ["name", "author", "year", "rating", "description"]:
            value = self.book_details.get(key, "N/A")
            details_text += f"{key.capitalize()}: {value}\n"
        
        logger.info(f"Details text for book: {details_text}")
        
        if not details_text.strip():
            details_text = "No details available.\n"
        
        details_label = ctk.CTkLabel(details_frame, text=details_text, font=("Helvetica", 18), wraplength=900, anchor="w", justify="left")
        details_label.pack(side="top", fill="both", expand=True)
        
        if self.book_details.get("book_link", "N/A") != "N/A":
            copy_link_button = ctk.CTkButton(details_frame, text="Copy Link", 
                                            command=lambda: self.copy_to_clipboard(self.book_details["book_link"]),
                                            fg_color="#1e40af", hover_color="#1e3a8a", width=80)
            copy_link_button.pack(side="top", pady=5)
        else:
            logger.warning("No book_link found; 'Copy Link' button not displayed")
        
        self.root.update()
        
        self.result_label.configure(text="Book details scraped", text_color="black" if ctk.get_appearance_mode() == "Light" else "white")  
        self.update_status("Book details displayed")

    def update_video_display(self) -> None:
        self.image_label.pack_forget()
        if self.ebay_scrollable_frame_visible and self.ebay_scrollable_frame.winfo_exists():
            self.ebay_scrollable_frame.pack_forget()
            self.ebay_scrollable_frame_visible = False
        self.text_box.pack(fill="both", expand=True)
        
        self.text_box.configure(state="normal")
        self.text_box.delete("1.0", "end")
        num_items = self.num_items_entry.get().strip()
        num_items = int(num_items) if num_items.isdigit() and int(num_items) > 0 else len(self.video_urls)
        video_urls_to_display = list(self.video_urls)[:num_items]
        for i, video_url in enumerate(video_urls_to_display, 1):
            self.text_box.insert("end", f"Video {i}: {video_url}\n")
        self.text_box.configure(state="disabled")
        self.result_label.configure(text=f"Found {len(self.video_urls)} videos (Displaying {len(video_urls_to_display)})", text_color="black" if ctk.get_appearance_mode() == "Light" else "white")
        self.update_status(f"Displaying {len(video_urls_to_display)} of {len(self.video_urls)} videos")

    def update_ebay_display(self) -> None:
        self.image_label.pack_forget()
        self.text_box.pack_forget()

        # Ensure UI updates happen on the main thread
        def update_ui():
            # Ensure the ebay_scrollable_frame exists
            self.ensure_ebay_scrollable_frame()

            # Clear existing widgets safely
            for widget in self.ebay_scrollable_frame.winfo_children():
                widget.destroy()

            logger.info(f"eBay items in update_ebay_display: {self.ebay_products}")

            if not self.ebay_products or "error" in self.ebay_products[0]:
                error_msg = self.ebay_products[0].get("error", "No items found.")
                self.result_label.configure(text=f"Failed to scrape: {error_msg}", text_color="red")
                self.update_status("eBay display error", "red")
                return

            for item in self.ebay_products:
                item_frame = ctk.CTkFrame(self.ebay_scrollable_frame)
                item_frame.pack(fill="x", padx=5, pady=5)

                if item.get("image_url", "N/A") != "N/A":
                    try:
                        img_response = requests.get(item["image_url"], headers=self.headers, timeout=5)
                        img_response.raise_for_status()
                        img = Image.open(io.BytesIO(img_response.content))
                        img.thumbnail((100, 100), Image.Resampling.LANCZOS)
                        photo = ImageTk.PhotoImage(img)
                        img_label = ctk.CTkLabel(item_frame, image=photo, text="")
                        img_label.image = photo
                        img_label.pack(side="left", padx=5, pady=5)
                    except Exception as e:
                        logger.error(f"Failed to load eBay item image: {str(e)}")

                details_text = f"Title: {item.get('title', 'N/A')}\nPrice: {item.get('price', 'N/A')}\nRating: {item.get('rating', 'N/A')}\n"
                details_label = ctk.CTkLabel(item_frame, text=details_text, font=("Helvetica", 12), wraplength=900, anchor="w", justify="left")
                details_label.pack(side="left", fill="both", expand=True, padx=5, pady=5)

                if item.get("link", "N/A") != "N/A":
                    copy_link_button = ctk.CTkButton(item_frame, text="Copy Link", 
                                                    command=lambda link=item["link"]: self.copy_to_clipboard(link),
                                                    fg_color="#1e40af", hover_color="#1e3a8a", width=80)
                    copy_link_button.pack(side="right", padx=5, pady=5)
                else:
                    logger.warning(f"No link found for eBay item: {item.get('title', 'N/A')}")

            self.root.update()
            self.result_label.configure(text="eBay products scraped", text_color="black" if ctk.get_appearance_mode() == "Light" else "white")
            self.update_status(f"Displaying {len(self.ebay_products)} eBay products")

        # Schedule the UI update on the main thread
        self.root.after(0, update_ui)

    def update_news_display(self) -> None:
        self.image_label.pack_forget()
        if self.ebay_scrollable_frame_visible and self.ebay_scrollable_frame.winfo_exists():
            self.ebay_scrollable_frame.pack_forget()
            self.ebay_scrollable_frame_visible = False
        self.text_box.pack(fill="both", expand=True)
        
        self.text_box.configure(state="normal")
        self.text_box.delete("1.0", "end")
        num_items = self.num_items_entry.get().strip()
        num_items = int(num_items) if num_items.isdigit() and int(num_items) > 0 else len(self.news_headlines)
        headlines_to_display = list(self.news_headlines)[:num_items]
        for i, headline in enumerate(headlines_to_display, 1):
            self.text_box.insert("end", f"Headline {i}: {headline}\n")
        self.text_box.configure(state="disabled")
        self.result_label.configure(text=f"Found {len(self.news_headlines)} headlines (Displaying {len(headlines_to_display)})", text_color="black" if ctk.get_appearance_mode() == "Light" else "white")
        self.update_status(f"Displaying {len(headlines_to_display)} of {len(self.news_headlines)} headlines")

    def update_pdf_display(self) -> None:
        self.image_label.pack_forget()
        self.text_box.pack_forget()

        # Ensure UI updates happen on the main thread
        def update_ui():
            # Ensure the ebay_scrollable_frame exists
            self.ensure_ebay_scrollable_frame()

            # Clear existing widgets safely
            for widget in self.ebay_scrollable_frame.winfo_children():
                widget.destroy()

            if not self.pdf_links:
                error_label = ctk.CTkLabel(self.ebay_scrollable_frame, text="No PDF links to display!", font=("Helvetica", 14))
                error_label.pack(pady=10)
                self.result_label.configure(text="No PDF links found!", text_color="red")
                self.update_status("No PDF links to display", "red")
                return

            num_items = self.num_items_entry.get().strip()
            num_items = int(num_items) if num_items.isdigit() and int(num_items) > 0 else len(self.pdf_links)
            filtered_pdfs = self.pdf_links[:min(num_items, len(self.pdf_links))]

            for i, pdf in enumerate(filtered_pdfs, 1):
                pdf_frame = ctk.CTkFrame(self.ebay_scrollable_frame)
                pdf_frame.pack(fill="x", padx=10, pady=5)

                pdf_name_label = ctk.CTkLabel(pdf_frame, text=pdf['name'], font=("Helvetica", 12), wraplength=700, anchor="w")
                pdf_name_label.grid(row=0, column=0, sticky="w", padx=(10, 10), pady=5)

                button_frame = ctk.CTkFrame(pdf_frame)
                button_frame.grid(row=0, column=1, sticky="e", padx=(0, 10), pady=5)

                download_button = ctk.CTkButton(button_frame, text="Download", 
                                               command=lambda url=pdf['url'], name=pdf['name']: self.download_pdf(url, name),
                                               fg_color="#1e40af", hover_color="#1e3a8a", width=80)
                download_button.pack(side="left", padx=(0, 5))

                extract_button = ctk.CTkButton(button_frame, text="Extract Info", 
                                               command=lambda url=pdf['url']: self.extract_pdf_info(url),
                                               fg_color="#1e40af", hover_color="#1e3a8a", width=80)
                extract_button.pack(side="left", padx=(0, 5))

                copy_link_button = ctk.CTkButton(button_frame, text="Copy Link", 
                                                command=lambda url=pdf['url']: self.copy_to_clipboard(url),
                                                fg_color="#1e40af", hover_color="#1e3a8a", width=80)
                copy_link_button.pack(side="left", padx=(0, 0))

            self.result_label.configure(text=f"Found {len(self.pdf_links)} PDF links (Displaying {len(filtered_pdfs)})", 
                                        text_color="black" if ctk.get_appearance_mode() == "Light" else "white")
            self.update_status(f"Displaying {len(filtered_pdfs)} of {len(self.pdf_links)} PDF links")

        # Schedule the UI update on the main thread
        self.root.after(0, update_ui)

    def show_image_in_popup(self, img_url: str) -> None:
        popup = ctk.CTkToplevel(self.root)
        popup.title("Image Preview")
        popup.geometry("600x600")
        popup.transient(self.root)
        popup.grab_set()
        
        img_data = self.image_data.get(img_url)
        if not img_data:
            try:
                img_response = requests.get(img_url, headers=self.headers, timeout=5)
                img_response.raise_for_status()
                img_data = img_response.content
                self.image_data[img_url] = img_data
            except Exception as e:
                logger.error(f"Failed to load image for popup: {str(e)}")
                popup.destroy()
                return
        
        img = Image.open(io.BytesIO(img_data))
        img.thumbnail((500, 500), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(img)
        
        img_label = ctk.CTkLabel(popup, image=photo, text="")
        img_label.image = photo
        img_label.pack(pady=10)
        
        copy_button = ctk.CTkButton(popup, text="Copy URL", command=lambda: self.copy_to_clipboard(img_url))
        copy_button.pack(pady=5)

    def download_pdf(self, url: str, name: str) -> None:
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
            os.makedirs(downloads_dir, exist_ok=True)
            file_path = os.path.join(downloads_dir, name)
            with open(file_path, 'wb') as f:
                f.write(response.content)
            self.update_status(f"PDF downloaded: {name}", "green")
        except Exception as e:
            self.update_status(f"Failed to download PDF: {str(e)}", "red")

    def extract_pdf_info(self, url: str) -> None:
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            pdf_file = io.BytesIO(response.content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            popup = ctk.CTkToplevel(self.root)
            popup.title("PDF Information")
            popup.geometry("600x400")
            popup.transient(self.root)
            popup.grab_set()
            
            num_pages = len(pdf_reader.pages)
            info_text = f"Number of Pages: {num_pages}\n\nExtracted Text (First Page):\n"
            
            if num_pages > 0:
                first_page = pdf_reader.pages[0]
                text = first_page.extract_text()
                info_text += text[:500] + "..." if len(text) > 500 else text
            else:
                info_text += "No text available."
            
            info_label = ctk.CTkLabel(popup, text=info_text, font=("Helvetica", 12), wraplength=550, anchor="w", justify="left")
            info_label.pack(pady=10, padx=10, fill="both", expand=True)
            
            copy_text_button = ctk.CTkButton(popup, text="Copy Text", 
                                            command=lambda: self.copy_to_clipboard(text if num_pages > 0 else ""),
                                            fg_color="#1e40af", hover_color="#1e3a8a")
            copy_text_button.pack(pady=5)
            
            self.update_status("PDF info extracted", "green")
        except Exception as e:
            self.update_status(f"Failed to extract PDF info: {str(e)}", "red")

    def copy_to_clipboard(self, text: str) -> None:
        pyperclip.copy(text)
        self.update_status("Link copied to clipboard", "green")

    def export_data(self) -> None:
        data_type = self.data_type_var.get()
        export_format = self.export_format_var.get()
        downloads_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        os.makedirs(downloads_dir, exist_ok=True)
        
        try:
            if data_type == "Images" and export_format == "zip":
                file_path = os.path.join(downloads_dir, "scraped_images.zip")
                with zipfile.ZipFile(file_path, 'w') as zipf:
                    for img_url, img_data in self.image_data.items():
                        if img_data:
                            img_name = img_url.split('/')[-1]
                            zipf.writestr(img_name, img_data)
                self.update_status(f"Images exported to {file_path}", "green")
            elif export_format == "csv":
                file_path = os.path.join(downloads_dir, f"scraped_{data_type.lower().replace(' ', '_')}.csv")
                with open(file_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    if data_type == "Images":
                        writer.writerow(["Image URL"])
                        for url in self.all_image_urls:
                            writer.writerow([url])
                    elif data_type == "Text":
                        writer.writerow(["Text Content"])
                        writer.writerow([self.text_content])
                    elif data_type == "Tables":
                        writer.writerow(["Table Index", "Row Data"])
                        for idx, table in enumerate(self.table_data, 1):
                            for row in table:
                                writer.writerow([idx, " | ".join(row)])
                    elif data_type == "Movie Details":
                        writer.writerow(self.movie_details.keys())
                        writer.writerow(self.movie_details.values())
                    elif data_type == "Book Details":
                        writer.writerow(self.book_details.keys())
                        writer.writerow(self.book_details.values())
                    elif data_type == "Videos":
                        writer.writerow(["Video URL"])
                        for url in self.video_urls:
                            writer.writerow([url])
                    elif data_type == "eBay Products":
                        writer.writerow(["Title", "Link", "Image URL", "Price", "Rating"])
                        for item in self.ebay_products:
                            writer.writerow([item.get("title", "N/A"), item.get("link", "N/A"), 
                                            item.get("image_url", "N/A"), item.get("price", "N/A"), 
                                            item.get("rating", "N/A")])
                    elif data_type == "News Headlines":
                        writer.writerow(["Headline"])
                        for headline in self.news_headlines:
                            writer.writerow([headline])
                    elif data_type == "PDF Links":
                        writer.writerow(["PDF Name", "URL"])
                        for pdf in self.pdf_links:
                            writer.writerow([pdf["name"], pdf["url"]])
                self.update_status(f"Data exported to {file_path}", "green")
            elif export_format == "json":
                file_path = os.path.join(downloads_dir, f"scraped_{data_type.lower().replace(' ', '_')}.json")
                with open(file_path, 'w', encoding='utf-8') as f:
                    if data_type == "Images":
                        json.dump({"images": self.all_image_urls}, f, indent=4)
                    elif data_type == "Text":
                        json.dump({"text": self.text_content}, f, indent=4)
                    elif data_type == "Tables":
                        json.dump({"tables": self.table_data}, f, indent=4)
                    elif data_type == "Movie Details":
                        json.dump(self.movie_details, f, indent=4)
                    elif data_type == "Book Details":
                        json.dump(self.book_details, f, indent=4)
                    elif data_type == "Videos":
                        json.dump({"videos": list(self.video_urls)}, f, indent=4)
                    elif data_type == "eBay Products":
                        json.dump({"products": self.ebay_products}, f, indent=4)
                    elif data_type == "News Headlines":
                        json.dump({"headlines": list(self.news_headlines)}, f, indent=4)
                    elif data_type == "PDF Links":
                        json.dump({"pdf_links": self.pdf_links}, f, indent=4)
                self.update_status(f"Data exported to {file_path}", "green")
        except Exception as e:
            self.update_status(f"Export failed: {str(e)}", "red")

    def toggle_dark_mode(self) -> None:
        current_mode = ctk.get_appearance_mode()
        new_mode = "Dark" if current_mode == "Light" else "Light"
        ctk.set_appearance_mode(new_mode)
        self.dark_mode_button.configure(text=f"{'Light' if new_mode == 'Dark' else 'Dark'} Mode")
        self.update_status(f"{new_mode} mode activated")

    def show_loading(self, show: bool) -> None:
        if show:
            self.loading_label.configure(text="Loading...")
        else:
            self.loading_label.configure(text="")

    def on_canvas_resize(self, event) -> None:
        self.update_gallery()

if __name__ == "__main__":
    root = ctk.CTk()
    app = WebScraperApp(root)
    root.mainloop()