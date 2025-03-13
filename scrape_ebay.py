from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import logging

logger = logging.getLogger(__name__)

def scrape_ebay_product(product_name: str) -> list:
    """
    Scrape eBay product listings for a given search term.
    
    Args:
        product_name (str): Product name to search for on eBay
    
    Returns:
        list: List of product dictionaries or None if unsuccessful
    """
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
                image_url = image_elem.get('data-src') or image_elem.get('src') if image_elem else "https://via.placeholder.com/150?text=No+Image"
                
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