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
import os
import logging

logger = logging.getLogger(__name__)

def scrape_pdf_links(url: str) -> list:
    """
    Scrape PDF links from a webpage.
    
    Args:
        url (str): The URL to scrape PDF links from
    
    Returns:
        list: List of dictionaries with PDF URLs and names or None if unsuccessful
    """
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

        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "a")))
        logger.info("Page loaded successfully with Selenium")
        
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