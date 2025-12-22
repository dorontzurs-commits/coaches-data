#!/usr/bin/env python3
"""Debug script to see what's in the table"""

import sys
sys.path.insert(0, '.')

from scraper.scraper import TransfermarktScraper
from bs4 import BeautifulSoup

def debug_table():
    """Debug what's in the table"""
    
    scraper = TransfermarktScraper(delay=1)
    
    league_url = "https://www.transfermarkt.com/premier-league/startseite/wettbewerb/GB1"
    
    print(f"Fetching: {league_url}")
    soup = scraper._get_page(league_url)
    
    if not soup:
        print("Failed")
        return
    
    # Find table
    table = soup.find('table', class_='items')
    if not table:
        table = soup.find('table')
    
    if table:
        rows = table.find_all('tr')[1:]  # Skip header
        print(f"\nFound {len(rows)} rows")
        
        # Check first few rows
        for i, row in enumerate(rows[:5], 1):
            print(f"\n--- Row {i} ---")
            cells = row.find_all('td')
            print(f"Cells: {len(cells)}")
            
            for j, cell in enumerate(cells[:3], 1):
                print(f"  Cell {j}:")
                # Get all links
                links = cell.find_all('a', href=True)
                print(f"    Links: {len(links)}")
                for link in links:
                    href = link.get('href', '')
                    text = link.text.strip()
                    print(f"      - '{text}' -> {href[:80]}")
                
                # Check if has verein
                verein_links = cell.find_all('a', href=re.compile(r'/verein/'))
                if verein_links:
                    print(f"    Found {len(verein_links)} verein links!")
                    for link in verein_links:
                        print(f"      -> {link.get('href', '')[:80]}")
    else:
        print("No table found")

if __name__ == '__main__':
    import re
    debug_table()

