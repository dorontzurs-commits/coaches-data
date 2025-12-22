#!/usr/bin/env python3
"""Test script to debug club scraping"""

import sys
sys.path.insert(0, '.')

from scraper.scraper import TransfermarktScraper

def test_club_scraping():
    """Test scraping clubs from Premier League"""
    
    scraper = TransfermarktScraper(delay=1)
    
    league_url = "https://www.transfermarkt.com/premier-league/startseite/wettbewerb/GB1"
    
    print(f"Testing club scraping from: {league_url}")
    print("="*60)
    
    clubs = scraper.scrape_clubs_from_league(league_url)
    
    print(f"\nResult: Found {len(clubs)} clubs")
    if clubs:
        print("\nFirst 5 clubs:")
        for club in clubs[:5]:
            print(f"  - {club['name']}: {club['url']}")
    else:
        print("\nNo clubs found. Check the debug output above.")

if __name__ == '__main__':
    test_club_scraping()

