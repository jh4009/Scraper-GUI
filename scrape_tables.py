import requests
from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

def scrape_tables(url: str) -> list:
    """
    Scrape table data from a webpage.
    
    Args:
        url (str): The URL to scrape tables from
    
    Returns:
        list: List of tables (each table as a list of rows) or None if unsuccessful
    """
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
        
        return table_data if table_data else None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching {url}: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error in scrape_tables: {e}")
        return None