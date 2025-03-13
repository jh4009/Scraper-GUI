import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import logging

logger = logging.getLogger(__name__)

def scrape_videos(url: str, video_format: str, headers: dict) -> tuple:
    """
    Scrape video URLs from a webpage.
    
    Args:
        url (str): The URL to scrape videos from
        video_format (str): Filter for specific video format ("all", "mp4", etc.)
        headers (dict): HTTP headers for requests
    
    Returns:
        tuple: Tuple of video URLs or None if unsuccessful
    """
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        videos = soup.find_all('video')
        video_urls = []
        
        allowed_formats = {
            "all": ["mp4", "avi", "mkv", "mov", "webm"],
            "mp4": ["mp4"],
            "avi": ["avi"],
            "mkv": ["mkv"],
            "mov": ["mov"],
            "webm": ["webm"]
        }.get(video_format.lower(), ["mp4"])
        
        for video in videos:
            video_sources = video.find_all('source')
            for source in video_sources:
                video_url = source.get('src')
                if video_url:
                    parsed_url = urlparse(video_url)
                    clean_url = parsed_url.scheme + "://" + parsed_url.netloc + parsed_url.path
                    extension = os.path.splitext(clean_url)[1].lower()[1:] if os.path.splitext(clean_url)[1] else ""
                    if extension in allowed_formats:
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
                        extension = os.path.splitext(clean_url)[1].lower()[1:] if os.path.splitext(clean_url)[1] else ""
                        if extension in allowed_formats:
                            if not video_url.startswith(('http://', 'https://')):
                                video_url = urljoin(url, video_url)
                            video_urls.append(video_url)
            driver.quit()
        
        return tuple(video_urls) if video_urls else None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in scrape_videos: {e}")
        return None