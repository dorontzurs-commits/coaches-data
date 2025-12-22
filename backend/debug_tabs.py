#!/usr/bin/env python3
"""Check navigation tabs on club page"""

import sys
sys.path.insert(0, '.')

from scraper.scraper import TransfermarktScraper
import re

def check_navigation_tabs():
    """Check what tabs/navigation exist on club page"""
    
    scraper = TransfermarktScraper(delay=1)
    
    club_url = "https://www.transfermarkt.com/real-madrid/startseite/verein/418"
    
    print(f"Fetching: {club_url}")
    soup = scraper._get_page(club_url)
    
    if not soup:
        print("Failed")
        return
    
    # Look for tab navigation or menu items
    print("\nLooking for tabs/navigation items:")
    
    # Look for data-viewport attributes (Transfermarkt uses these)
    viewports = soup.find_all(['div', 'a'], {'data-viewport': True})
    print(f"\nFound {len(viewports)} elements with data-viewport:")
    for vp in viewports[:10]:
        viewport = vp.get('data-viewport', '')
        text = vp.get_text().strip()[:50]
        href = vp.get('href', '')
        print(f"  '{viewport}' -> '{text}' | href: {href[:60]}")
    
    # Look for any links that might be tabs
    tab_patterns = ['profil', 'startseite', 'kader', 'transfers', 'personal', 'stationen', 'wettbewerb']
    all_links = soup.find_all('a', href=True)
    
    print("\n\nLinks that might be relevant tabs:")
    for link in all_links:
        href = link.get('href', '')
        text = link.get_text().strip().lower()
        
        if any(pattern in href.lower() or pattern in text for pattern in tab_patterns):
            if 'verein' in href and club_id in href:
                print(f"  '{text[:40]:40s}' -> {href[:80]}")

if __name__ == '__main__':
    import re
    club_id = "418"
    check_navigation_tabs()


