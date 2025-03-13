import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import logging

logger = logging.getLogger(__name__)

def scrape_images(url: str, image_format: str, headers: dict) -> list:
    """
    Scrape image URLs from a webpage.
    
    Args:
        url (str): The URL to scrape images from
        image_format (str): Filter for specific image format ("all", "png", "jpg")
        headers (dict): HTTP headers for requests
    
    Returns:
        list: List of image URLs or None if unsuccessful
    """
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        images = soup.find_all(['img', 'image'])
        image_urls = []
        
        # Define allowed extensions based on format
        allowed_extensions = {
            "all": ['.png', '.jpg', '.jpeg', '.webp', '.gif'],
            "png": ['.png'],
            "jpg": ['.jpg', '.jpeg']
        }.get(image_format, ['.png', '.jpg', '.jpeg'])

        for img in images:
            img_url = img.get('src') or img.get('data-src') or img.get('data-lazy-src')
            if img_url:
                full_url = urljoin(url, img_url)
                if any(full_url.lower().endswith(ext) for ext in allowed_extensions):
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
                    if any(full_url.lower().endswith(ext) for ext in allowed_extensions):
                        image_urls.append(full_url)
            driver.quit()
        
        return image_urls if image_urls else None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in scrape_images: {e}")
        return None