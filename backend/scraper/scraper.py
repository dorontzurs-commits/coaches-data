import requests
from bs4 import BeautifulSoup
import time
import re
from urllib.parse import urljoin, urlparse

class TransfermarktScraper:
    def __init__(self, callback=None, delay=2):
        """
        Initialize the scraper
        
        Args:
            callback: Function to call with progress updates (current, total, current_club, status)
            delay: Delay between requests in seconds
        """
        self.callback = callback
        self.delay = delay
        self.base_url = 'https://www.transfermarkt.com'
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        self.should_stop = False
    
    def _update_progress(self, current, total, current_club, status):
        """Update progress via callback"""
        if self.callback:
            self.callback(current, total, current_club, status)
    
    def _get_page(self, url):
        """Fetch a page with error handling"""
        try:
            time.sleep(self.delay)
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None
    
    def scrape_leagues_from_continent(self, continent='europa'):
        """
        Scrape leagues from a continent's leagues page (first page only)
        
        Args:
            continent: Continent name ('europa', 'amerika', 'afrika', 'asien')
        
        Returns:
            List of dicts with 'name', 'url', and 'country' keys
        """
        url = f'{self.base_url}/wettbewerbe/{continent}'
        soup = self._get_page(url)
        
        if not soup:
            return []
        
        leagues = []
        # Find the table with leagues
        table = soup.find('table', class_='items')
        if not table:
            table = soup.find('table')
        
        if table:
            rows = table.find_all('tr')[1:]  # Skip header row
            print(f"Found {len(rows)} rows in table")
            for row in rows:
                cells = row.find_all('td')
                if len(cells) < 1:
                    continue
                
                # First cell usually contains league name and link
                league_cell = cells[0]
                
                # Try multiple patterns for league links
                league_link = league_cell.find('a', href=re.compile(r'/startseite/wettbewerb/'))
                if not league_link:
                    # Try alternative: look for any link with wettbewerb
                    league_link = league_cell.find('a', href=re.compile(r'/wettbewerb/'))
                
                if league_link:
                    league_name = league_link.text.strip()
                    if not league_name:
                        # Try getting text from parent or nearby elements
                        league_name = league_cell.get_text().strip()
                    
                    if league_name:
                        league_url = urljoin(self.base_url, league_link['href'])
                        
                        # First, clean league name - remove any country info in parentheses if it's a duplicate
                        # Check if league name ends with parentheses containing the same name
                        match = re.search(r'^(.+?)\s*\((.+?)\)$', league_name)
                        if match:
                            base_name = match.group(1).strip()
                            paren_content = match.group(2).strip()
                            # If content in parentheses is same as base name, remove it
                            if base_name.lower() == paren_content.lower():
                                league_name = base_name
                        
                        # Extract country - try multiple strategies
                        country = ''
                        
                        # Strategy 1: Look for flag image with alt text (most reliable)
                        # Check all cells for flag images
                        for cell_idx, cell in enumerate(cells):
                            flag_imgs = cell.find_all('img', alt=True)
                            for flag_img in flag_imgs:
                                alt_text = flag_img.get('alt', '').strip()
                                # Make sure it's not the league name, not empty, and looks like a country name
                                if alt_text and alt_text.lower() != league_name.lower() and len(alt_text) < 50:
                                    # Additional check: country names usually don't contain "League" or "Liga"
                                    if 'league' not in alt_text.lower() and 'liga' not in alt_text.lower():
                                        country = alt_text
                                        break
                            if country:
                                break
                        
                        # Strategy 2: Look in second cell specifically (usually has country flag)
                        if not country and len(cells) > 1:
                            country_cell = cells[1]
                            # Get all images in this cell
                            flag_imgs = country_cell.find_all('img', alt=True)
                            for img in flag_imgs:
                                alt_text = img.get('alt', '').strip()
                                if alt_text and alt_text.lower() != league_name.lower():
                                    # Additional check: country names usually don't contain "League" or "Liga"
                                    if 'league' not in alt_text.lower() and 'liga' not in alt_text.lower():
                                        country = alt_text
                                        break
                            
                            # If no flag found, try text but make sure it's not the league name
                            if not country:
                                country_text = country_cell.get_text().strip()
                                # Clean up the text - remove common prefixes/suffixes
                                country_text = re.sub(r'^\s*[-•]\s*', '', country_text)
                                # Make sure it's not the league name and doesn't contain "League"
                                if (country_text and 
                                    country_text.lower() != league_name.lower() and 
                                    len(country_text) < 50 and
                                    'league' not in country_text.lower() and
                                    'liga' not in country_text.lower()):
                                    country = country_text
                        
                        # Strategy 3: Check if league name has country in parentheses (different from league name)
                        if not country:
                            match = re.search(r'\(([^)]+)\)$', league_name)
                            if match:
                                potential_country = match.group(1).strip()
                                # Only use if it's different from league name and doesn't contain "League"
                                if (potential_country.lower() != league_name.lower() and
                                    'league' not in potential_country.lower() and
                                    'liga' not in potential_country.lower()):
                                    # Remove the country from league name
                                    league_name = re.sub(r'\s*\([^)]+\)$', '', league_name).strip()
                                    country = potential_country
                        
                        leagues.append({
                            'name': league_name,
                            'url': league_url,
                            'country': country
                        })
                        print(f"  -> Added league: {league_name} (Country: {country if country else 'N/A'})")
        else:
            print(f"No table found on {continent} page")
        
        print(f"Scraped {len(leagues)} leagues from {continent} page")
        return leagues
    
    def scrape_leagues_from_europa(self):
        """
        Scrape leagues from the European leagues page (first page only)
        DEPRECATED: Use scrape_leagues_from_continent('europa') instead
        
        Returns:
            List of dicts with 'name', 'url', and 'country' keys
        """
        return self.scrape_leagues_from_continent('europa')
    
    def scrape_clubs_from_league(self, league_url):
        """
        Scrape all clubs from a league page
        Looks for the table under "Clubs - [League Name] [Season]" heading
        
        Args:
            league_url: URL of the league page
            
        Returns:
            List of dicts with 'name' and 'url' keys
        """
        print(f"Scraping clubs from league: {league_url}")
        soup = self._get_page(league_url)
        
        if not soup:
            print("Failed to fetch league page")
            return []
        
        clubs = []
        seen_clubs = set()  # Avoid duplicates
        table = None
        
        # Strategy 1: Look for heading "Clubs - [League] [Season]" and find table after it
        # Try different heading tags and text patterns
        headings = soup.find_all(['h2', 'h3', 'h4'], string=re.compile(r'Clubs\s*-', re.I))
        if not headings:
            # Also try finding by text content
            headings = soup.find_all(string=re.compile(r'Clubs\s*-', re.I))
            headings = [h.find_parent(['h2', 'h3', 'h4', 'div']) for h in headings if h.find_parent(['h2', 'h3', 'h4', 'div'])]
        
        if headings:
            print(f"Found {len(headings)} 'Clubs' headings")
            for heading in headings:
                # Find the table after this heading - search in parent and siblings
                current = heading
                for _ in range(10):  # Search up to 10 siblings ahead
                    current = current.find_next_sibling()
                    if not current:
                        break
                    if current.name == 'table':
                        table = current
                        break
                    # Also check if table is inside a div after the heading
                    if current.name in ['div', 'section']:
                        nested_table = current.find('table', class_='items')
                        if nested_table:
                            table = nested_table
                            break
                
                if table:
                    print(f"Found table after 'Clubs' heading")
                    break
        
        # Strategy 2: Look for table with class 'items' that contains club links
        if not table:
            all_tables = soup.find_all('table', class_='items')
            for t in all_tables:
                # Check if this table has club links
                club_links = t.find_all('a', href=re.compile(r'/startseite/verein/'))
                if club_links:
                    table = t
                    print(f"Found table with {len(club_links)} club links")
                    break
        
        # Strategy 3: Fallback - any table
        if not table:
            table = soup.find('table')
        
        if table:
            rows = table.find_all('tr')[1:]  # Skip header row
            print(f"Found {len(rows)} rows in league table")
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) < 1:
                    continue
                
                # Skip summary row (first row usually has no links or different structure)
                # Check if this row has any club links at all
                all_links_in_row = row.find_all('a', href=re.compile(r'/startseite/verein/'))
                if not all_links_in_row:
                    continue  # Skip rows without club links
                
                # Look for club link - check all cells, but prioritize second cell (usually has club name)
                club_link = None
                
                # Strategy 1: Check second cell first (usually contains club name with link)
                if len(cells) > 1:
                    club_link = cells[1].find('a', href=re.compile(r'/startseite/verein/'))
                
                # Strategy 2: If not found, check first cell
                if not club_link:
                    club_link = cells[0].find('a', href=re.compile(r'/startseite/verein/'))
                
                # Strategy 3: Search all cells
                if not club_link:
                    for cell in cells:
                        link = cell.find('a', href=re.compile(r'/startseite/verein/'))
                        if link:
                            club_link = link
                            break
                
                if club_link:
                    club_name = club_link.text.strip()
                    if not club_name:
                        # Try getting text from the cell
                        club_name = club_link.find_parent('td').get_text().strip() if club_link.find_parent('td') else ''
                    
                    if club_name:
                        club_url = urljoin(self.base_url, club_link['href'])
                        
                        # Normalize URL - remove season parameter
                        if '/saison_id/' in club_url:
                            club_url = club_url.split('/saison_id/')[0]
                        
                        # Ensure we have the correct format
                        if '/startseite/verein/' not in club_url:
                            # Extract verein ID and slug from URL
                            verein_match = re.search(r'/verein/(\d+)', club_url)
                            slug_match = re.search(r'/([^/]+)/verein/', club_url)
                            if verein_match:
                                verein_id = verein_match.group(1)
                                if slug_match:
                                    club_slug = slug_match.group(1)
                                    club_url = f'{self.base_url}/{club_slug}/startseite/verein/{verein_id}'
                                else:
                                    club_url = f'{self.base_url}/startseite/verein/{verein_id}'
                        
                        if club_name not in seen_clubs and 'verein' in club_url:
                            seen_clubs.add(club_name)
                            clubs.append({
                                'name': club_name,
                                'url': club_url
                            })
                            print(f"  -> Added club: {club_name} ({club_url})")
        else:
            print("No table found on league page")
        
        print(f"Scraped {len(clubs)} clubs from league")
        return clubs
    
    def scrape_top_clubs(self):
        """
        Scrape the first page of top 100 valuable teams (DEPRECATED - use scrape_leagues_from_europa instead)
        
        Returns:
            List of dicts with 'name' and 'url' keys
        """
        url = f'{self.base_url}/spieler-statistik/wertvollstemannschaften/marktwertetop'
        soup = self._get_page(url)
        
        if not soup:
            return []
        
        clubs = []
        # Find the table with clubs - look for table rows with club links
        table = soup.find('table', class_='items')
        if not table:
            # Try alternative table selectors
            table = soup.find('table')
        
        if table:
            rows = table.find_all('tr')[1:]  # Skip header row
            seen_clubs = set()  # Avoid duplicates
            for row in rows:
                # Find club name link - usually in second column (hauptlink)
                club_cell = row.find('td', class_='hauptlink')
                if not club_cell:
                    # Try first few cells
                    cells = row.find_all('td')[:3]
                    for cell in cells:
                        link = cell.find('a', href=True)
                        if link and 'verein' in link.get('href', ''):
                            club_cell = cell
                            break
                
                if club_cell:
                    link = club_cell.find('a', href=True)
                    if link:
                        club_name = link.text.strip()
                        if not club_name:
                            continue
                        club_url = urljoin(self.base_url, link['href'])
                        # Normalize URL to club page
                        if '/saison_id/' in club_url:
                            # Remove season parameter
                            club_url = club_url.split('/saison_id/')[0]
                        if club_name not in seen_clubs and 'verein' in club_url:
                            seen_clubs.add(club_name)
                            clubs.append({
                                'name': club_name,
                                'url': club_url
                            })
        
        print(f"Scraped {len(clubs)} clubs from table")
        return clubs
    
    def get_current_manager(self, club_url, include_caretaker=True):
        """
        Get the current manager(s) from club's staff section (mitarbeiter page)
        Includes both Manager and Caretaker Manager if include_caretaker is True
        
        Args:
            club_url: URL of the club page
            include_caretaker: If True, also return Caretaker Manager if found
            
        Returns:
            List of dicts with 'name', 'profile_url', 'id', and 'role' (Manager/Caretaker Manager)
            Returns empty list if no managers found
        """
        # Extract club ID and slug from URL
        club_id_match = re.search(r'/verein/(\d+)', club_url)
        if not club_id_match:
            return []
        
        club_id = club_id_match.group(1)
        
        # Extract club slug from URL
        slug_match = re.search(r'/([^/]+)/startseite/verein/', club_url)
        club_slug = slug_match.group(1) if slug_match else ''
        
        managers = []
        
        # Strategy 1: Access staff page (mitarbeiter) - this is the most reliable method
        # URL format: /{club-slug}/mitarbeiter/verein/{club_id}
        staff_urls = []
        if club_slug:
            staff_urls.append(f'{self.base_url}/{club_slug}/mitarbeiter/verein/{club_id}')
        staff_urls.append(f'{self.base_url}/mitarbeiter/verein/{club_id}')
        
        for staff_url in staff_urls:
            print(f"  -> Trying staff page: {staff_url}")
            staff_soup = self._get_page(staff_url)
            if staff_soup:
                # Look for "COACHING STAFF" table or any table with staff info
                # The table might have class 'items' or be in a specific section
                tables = staff_soup.find_all('table', class_='items')
                if not tables:
                    tables = staff_soup.find_all('table')
                
                for table in tables:
                    # Check if this table contains coaching staff
                    table_text = table.get_text().lower()
                    if 'coaching staff' in table_text or 'manager' in table_text or 'trainer' in table_text:
                        rows = table.find_all('tr')[1:]  # Skip header row
                        
                        for row in rows:
                            cells = row.find_all('td')
                            if len(cells) < 1:
                                continue
                            
                            # First cell usually contains name/position
                            name_cell = cells[0]
                            
                            # Get all text from the row to check for role
                            row_text = row.get_text().lower()
                            name_cell_text = name_cell.get_text().lower()
                            
                            # Check for Manager (ONLY Manager, not Caretaker Manager, not Loan Player Manager, etc.)
                            role = None
                            is_manager = False
                            
                            # Get text from the row to check for role
                            row_text_lower = row_text.lower()
                            
                            # DEBUG: Log the full row text to understand what we're checking
                            print(f"    [DEBUG] Checking row text: {row_text_lower[:200]}...")
                            
                            # Simple check: look for "manager" as a standalone word
                            manager_pattern = r'\bmanager\b'
                            has_manager_word = re.search(manager_pattern, row_text_lower)
                            
                            if has_manager_word:
                                print(f"    [DEBUG] Found 'manager' word in text")
                                
                                # Exclude specific compound roles that contain "manager"
                                excluded_compound_roles = [
                                    'loan player manager', 'player manager', 'team manager',
                                    'caretaker manager', 'assistant manager', 'general manager',
                                    'sporting manager', 'technical manager', 'youth manager',
                                    'academy manager', 'development manager', 'operations manager',
                                    'business manager', 'commercial manager', 'marketing manager',
                                    'kit manager', 'performance manager', 'team official',
                                    'goalkeeping coach', 'fitness manager', 'scout manager',
                                    'data manager', 'analyst manager', 'video manager',
                                    'equipment manager', 'stadium manager', 'facilities manager'
                                ]
                                
                                # Check if any excluded compound role appears in the text
                                has_excluded_role = any(excluded_role in row_text_lower for excluded_role in excluded_compound_roles)
                                
                                if has_excluded_role:
                                    # Find which excluded role matched
                                    matched_role = next((r for r in excluded_compound_roles if r in row_text_lower), None)
                                    print(f"    [DEBUG] EXCLUDED - Found compound role: '{matched_role}'")
                                else:
                                    # Additional check: if the text contains "manager" but also contains other role indicators
                                    # that suggest it's not the main Manager role
                                    # Check if these indicators appear NEAR "manager" (within 15 characters)
                                    other_role_indicators = ['coach', 'official', 'staff', 'analyst', 'scout', 'kit', 'performance', 'goalkeeping', 'fitness', 'equipment', 'stadium', 'facilities']
                                    
                                    # Find position of "manager" in text
                                    manager_match = re.search(r'\bmanager\b', row_text_lower)
                                    has_other_indicator_near = False
                                    
                                    if manager_match:
                                        manager_start = manager_match.start()
                                        manager_end = manager_match.end()
                                        
                                        # Check a window of 15 characters before and after "manager"
                                        context_start = max(0, manager_start - 15)
                                        context_end = min(len(row_text_lower), manager_end + 15)
                                        context_text = row_text_lower[context_start:context_end]
                                        
                                        print(f"    [DEBUG] Context around 'manager': '{context_text}'")
                                        
                                        # Check if any other role indicator appears in this context
                                        for indicator in other_role_indicators:
                                            if indicator in context_text and indicator != 'manager':
                                                has_other_indicator_near = True
                                                print(f"    [DEBUG] EXCLUDED - Found '{indicator}' near 'manager' in context")
                                                break
                                    
                                    if has_other_indicator_near:
                                        print(f"    [DEBUG] EXCLUDED - Found other role indicator near 'manager'")
                                    else:
                                        # Final check: make sure "manager" appears as a standalone word, not part of another word
                                        # Check if "manager" is preceded by a space or is at the start, and followed by a space or end
                                        standalone_manager_pattern = r'(^|\s)manager(\s|$|[^a-z])'
                                        is_standalone = re.search(standalone_manager_pattern, row_text_lower)
                                        
                                        if is_standalone:
                                            is_manager = True
                                            role = 'Manager'
                                            print(f"    [DEBUG] ACCEPTED - Valid Manager role found")
                                        else:
                                            print(f"    [DEBUG] EXCLUDED - 'manager' is not standalone")
                            else:
                                print(f"    [DEBUG] No 'manager' word found in text")
                            
                            # Only return Manager (not Caretaker Manager, not Coach, not any other role)
                            if is_manager:
                                # Find trainer link in this row
                                trainer_link = row.find('a', href=re.compile(r'/trainer/\d+'))
                                if trainer_link:
                                    name = trainer_link.text.strip()
                                    if name:
                                        profile_url = urljoin(self.base_url, trainer_link['href'])
                                        manager_id = self._extract_manager_id(profile_url)
                                        if manager_id:
                                            print(f"  -> Found {role}: {name} (ID: {manager_id})")
                                            managers.append({
                                                'name': name,
                                                'profile_url': profile_url,
                                                'id': manager_id,
                                                'role': role
                                            })
                                
                                # Alternative: look for any trainer link in the row
                                if not trainer_link:
                                    all_links = row.find_all('a', href=re.compile(r'/trainer/\d+'))
                                    if all_links:
                                        link = all_links[0]
                                        name = link.text.strip()
                                        if name:
                                            profile_url = urljoin(self.base_url, link['href'])
                                            manager_id = self._extract_manager_id(profile_url)
                                            if manager_id:
                                                print(f"  -> Found {role} (alternative): {name} (ID: {manager_id})")
                                                managers.append({
                                                    'name': name,
                                                    'profile_url': profile_url,
                                                    'id': manager_id,
                                                    'role': role
                                                })
                
                # If we found managers, return them
                if managers:
                    return managers
                
                # Fallback: look for any trainer link on the staff page (ONLY Manager)
                trainer_links = staff_soup.find_all('a', href=re.compile(r'/trainer/\d+'))
                if trainer_links:
                    print(f"  -> [DEBUG] Found {len(trainer_links)} trainer links in fallback search")
                    # Check context around each link to find ONLY Manager
                    excluded_compound_roles = [
                        'loan player manager', 'player manager', 'team manager',
                        'caretaker manager', 'assistant manager', 'general manager',
                        'sporting manager', 'technical manager', 'youth manager',
                        'academy manager', 'development manager', 'operations manager',
                        'business manager', 'commercial manager', 'marketing manager',
                        'kit manager', 'performance manager', 'team official',
                        'goalkeeping coach', 'fitness manager', 'scout manager',
                        'data manager', 'analyst manager', 'video manager',
                        'equipment manager', 'stadium manager', 'facilities manager'
                    ]
                    
                    for link in trainer_links:
                        parent = link.find_parent(['tr', 'td', 'div'])
                        if parent:
                            parent_text = parent.get_text().lower()
                            name = link.text.strip()
                            
                            print(f"  -> [DEBUG] Checking trainer link: {name}")
                            print(f"  -> [DEBUG] Parent text: {parent_text[:200]}...")
                            
                            # Check if "manager" appears as a standalone word
                            manager_pattern = r'\bmanager\b'
                            has_manager = re.search(manager_pattern, parent_text)
                            
                            if has_manager:
                                # Check if any excluded compound role appears
                                has_excluded_role = any(excluded_role in parent_text for excluded_role in excluded_compound_roles)
                                
                                if has_excluded_role:
                                    matched_role = next((r for r in excluded_compound_roles if r in parent_text), None)
                                    print(f"  -> [DEBUG] EXCLUDED - Found compound role: '{matched_role}' for {name}")
                                else:
                                    # Additional check: if the text contains "manager" but also contains other role indicators
                                    # that suggest it's not the main Manager role
                                    # Check if these indicators appear NEAR "manager" (within 15 characters)
                                    other_role_indicators = ['coach', 'official', 'staff', 'analyst', 'scout', 'kit', 'performance', 'goalkeeping', 'fitness', 'equipment', 'stadium', 'facilities']
                                    
                                    # Find position of "manager" in text
                                    manager_match = re.search(r'\bmanager\b', parent_text)
                                    has_other_indicator_near = False
                                    
                                    if manager_match:
                                        manager_start = manager_match.start()
                                        manager_end = manager_match.end()
                                        
                                        # Check a window of 15 characters before and after "manager"
                                        context_start = max(0, manager_start - 15)
                                        context_end = min(len(parent_text), manager_end + 15)
                                        context_text = parent_text[context_start:context_end]
                                        
                                        print(f"  -> [DEBUG] Context around 'manager' for {name}: '{context_text}'")
                                        
                                        # Check if any other role indicator appears in this context
                                        for indicator in other_role_indicators:
                                            if indicator in context_text and indicator != 'manager':
                                                has_other_indicator_near = True
                                                print(f"  -> [DEBUG] EXCLUDED - Found '{indicator}' near 'manager' for {name}")
                                        break
                                
                                    if has_other_indicator_near:
                                        print(f"  -> [DEBUG] EXCLUDED - Found other role indicator near 'manager' for {name}")
                                    else:
                                        # Final standalone check
                                        standalone_manager_pattern = r'(^|\s)manager(\s|$|[^a-z])'
                                        is_standalone = re.search(standalone_manager_pattern, parent_text)
                                        
                                        if is_standalone:
                                            if name:
                                                profile_url = urljoin(self.base_url, link['href'])
                                                manager_id = self._extract_manager_id(profile_url)
                                                if manager_id:
                                                    print(f"  -> [DEBUG] ACCEPTED - Found Manager (fallback): {name} (ID: {manager_id})")
                                                    managers.append({
                                                        'name': name,
                                                        'profile_url': profile_url,
                                                        'id': manager_id,
                                                        'role': 'Manager'
                                                    })
                                        else:
                                            print(f"  -> [DEBUG] EXCLUDED - 'manager' is not standalone for {name}")
                            else:
                                print(f"  -> [DEBUG] EXCLUDED - No 'manager' word found for {name}")
        
        return managers
    
    def _extract_manager_id(self, profile_url):
        """Extract manager ID from profile URL"""
        match = re.search(r'/trainer/(\d+)', profile_url)
        if match:
            return match.group(1)
        
        # Try to extract from achievements URL pattern
        match = re.search(r'/(\d+)$', profile_url)
        if match:
            return match.group(1)
        
        return None
    
    def scrape_manager_profile_info(self, profile_url):
        """
        Scrape additional information from manager's profile page
        
        Args:
            profile_url: URL of the manager's profile page
            
        Returns:
            Dict with 'date_of_birth' and 'preferred_formation' keys
        """
        if not profile_url:
            return {'date_of_birth': '', 'preferred_formation': ''}
        
        print(f"  -> Fetching manager profile info from: {profile_url}")
        soup = self._get_page(profile_url)
        if not soup:
            print(f"  -> Failed to fetch manager profile page")
            return {'date_of_birth': '', 'preferred_formation': ''}
        
        info = {
            'date_of_birth': '',
            'preferred_formation': ''
        }
        
        # Extract Date of Birth
        # Look for date of birth in the profile info section
        # Usually appears as "Date of birth: DD/MM/YYYY" or in a table row
        dob_patterns = [
            r'date\s+of\s+birth[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{4})',
            r'geburtstag[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{4})',
            r'geboren[:\s]+(\d{1,2}[/-]\d{1,2}[/-]\d{4})',
            r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})'  # Generic date pattern
        ]
        
        # Look in info table or text content
        info_table = soup.find('table', class_='auflistung')
        if not info_table:
            info_table = soup.find('table')
        
        if info_table:
            rows = info_table.find_all('tr')
            for row in rows:
                row_text = row.get_text().lower()
                # Check if this row contains date of birth info
                if 'date of birth' in row_text or 'geburtstag' in row_text or 'geboren' in row_text:
                    # Extract date from this row
                    for pattern in dob_patterns:
                        match = re.search(pattern, row_text, re.I)
                        if match:
                            date_str = match.group(1)
                            # Format: DD/MM/YYYY or DD-MM-YYYY
                            info['date_of_birth'] = date_str
                            print(f"    -> Found date of birth: {date_str}")
                            break
                    if info['date_of_birth']:
                        break
        
        # If not found in table, search in all text
        if not info['date_of_birth']:
            page_text = soup.get_text().lower()
            for pattern in dob_patterns:
                match = re.search(pattern, page_text, re.I)
                if match:
                    date_str = match.group(1)
                    info['date_of_birth'] = date_str
                    print(f"    -> Found date of birth (in page text): {date_str}")
                    break
        
        # Extract Preferred Formation
        # Look for formation info - usually appears as "Preferred formation: 4-3-3" or similar
        formation_patterns = [
            r'preferred\s+formation[:\s]+([\d-]+)',
            r'lieblingsformation[:\s]+([\d-]+)',
            r'formation[:\s]+([\d-]+)',
            r'(\d+[-]\d+[-]\d+)',  # Pattern like 4-3-3, 4-4-2, etc.
            r'(\d+[-]\d+)'  # Pattern like 4-3, 3-5-2, etc.
        ]
        
        # Look in info table
        if info_table:
            rows = info_table.find_all('tr')
            for row in rows:
                row_text = row.get_text().lower()
                # Check if this row contains formation info
                if 'formation' in row_text or 'lieblingsformation' in row_text:
                    # Extract formation from this row
                    for pattern in formation_patterns:
                        match = re.search(pattern, row_text, re.I)
                        if match:
                            formation_str = match.group(1)
                            info['preferred_formation'] = formation_str
                            print(f"    -> Found preferred formation: {formation_str}")
                            break
                    if info['preferred_formation']:
                        break
        
        # If not found in table, search in all text
        if not info['preferred_formation']:
            page_text = soup.get_text().lower()
            for pattern in formation_patterns:
                match = re.search(pattern, page_text, re.I)
                if match:
                    formation_str = match.group(1)
                    info['preferred_formation'] = formation_str
                    print(f"    -> Found preferred formation (in page text): {formation_str}")
                    break
        
        return info
    
    def scrape_coach_history(self, coach_name, coach_id):
        """
        Scrape coach career history from coach's history page
        
        Args:
            coach_name: Name of the coach (used for URL slug)
            coach_id: ID of the coach
            
        Returns:
            List of dicts with club, dates, and statistics
        """
        if not coach_id:
            return []
        
        # Build history URL - format: /{coach-slug}/stationen/trainer/{id}/plus/1
        name_slug = self._slugify(coach_name)
        history_url = f'{self.base_url}/{name_slug}/stationen/trainer/{coach_id}/plus/1'
        
        print(f"  -> Fetching career history from: {history_url}")
        soup = self._get_page(history_url)
        if not soup:
            print(f"  -> Failed to fetch history page")
            return []
        
        career_entries = []
        
        # Look for the main history table
        table = soup.find('table', class_='items')
        if not table:
            table = soup.find('table')
        
        if table:
            rows = table.find_all('tr')[1:]  # Skip header row
            for row in rows:
                cells = row.find_all('td')
                if len(cells) < 5:
                    continue
                
                entry = {}
                
                # Extract club name and role
                club_cell = cells[1]  # "Club & role" column
                club_link = club_cell.find('a', href=re.compile(r'/verein/'))
                if club_link:
                    entry['club'] = club_link.get_text().strip()
                    entry['club_url'] = urljoin(self.base_url, club_link['href'])
                
                # Extract role (ONLY Manager - not Coach, not Head Coach, etc.)
                # Check the entire row text for role information
                row_text = row.get_text()
                role_text = club_cell.get_text()
                
                # Combine both texts to search for role (case insensitive)
                combined_text = (role_text + ' ' + row_text).lower()
                
                # DEBUG: Log the combined text to understand what we're checking
                print(f"    [DEBUG] Checking role text for {entry.get('club', 'Unknown Club')}: {combined_text[:300]}...")
                
                # Only match "Manager" - can be standalone or attached to club name (e.g., "Real MadridManager")
                # Pattern: "manager" that is either:
                # 1. At word boundary: \bmanager\b (with space before)
                # 2. Attached to a word (like "MadridManager"): [a-z]manager\b (letter before + manager + word boundary after)
                # This handles both "Manager" and "MadridManager" cases
                manager_pattern = r'(\b|(?<=[a-z]))manager\b'
                has_manager = re.search(manager_pattern, combined_text, re.I)
                
                if has_manager:
                    print(f"    [DEBUG] Found 'manager' word in combined text")
                    
                    # Check that it's not a compound role like "Assistant Manager" or "Caretaker Manager"
                    excluded_compound_roles = [
                        'loan player manager', 'player manager', 'team manager',
                        'caretaker manager', 'assistant manager', 'general manager',
                        'sporting manager', 'technical manager', 'youth manager',
                        'academy manager', 'development manager', 'operations manager',
                        'business manager', 'commercial manager', 'marketing manager',
                        'kit manager', 'performance manager', 'team official',
                        'goalkeeping coach', 'fitness manager', 'scout manager',
                        'data manager', 'analyst manager', 'video manager',
                        'equipment manager', 'stadium manager', 'facilities manager'
                    ]
                    
                    # Also check for compound roles without spaces (e.g., "assistantmanager")
                    excluded_compound_no_space = [
                        'loanplayermanager', 'playermanager', 'teammanager',
                        'caretakermanager', 'assistantmanager', 'generalmanager',
                        'sportingmanager', 'technicalmanager', 'youthmanager',
                        'academymanager', 'developmentmanager', 'operationsmanager',
                        'businessmanager', 'commercialmanager', 'marketingmanager',
                        'kitmanager', 'performancemanager', 'teamofficial',
                        'goalkeepingcoach', 'fitnessmanager', 'scoutmanager',
                        'datamanager', 'analystmanager', 'videomanager',
                        'equipmentmanager', 'stadiummanager', 'facilitiesmanager'
                    ]
                    
                    # Remove spaces for no-space check
                    combined_no_space = combined_text.replace(' ', '')
                    
                    has_excluded_role = any(excluded_role in combined_text for excluded_role in excluded_compound_roles)
                    has_excluded_no_space = any(excluded_role in combined_no_space for excluded_role in excluded_compound_no_space)
                    
                    if has_excluded_role:
                        matched_role = next((r for r in excluded_compound_roles if r in combined_text), None)
                        print(f"    [DEBUG] EXCLUDED - Found compound role: '{matched_role}' for {entry.get('club', 'Unknown Club')}")
                    elif has_excluded_no_space:
                        matched_role = next((r for r in excluded_compound_no_space if r in combined_no_space), None)
                        print(f"    [DEBUG] EXCLUDED - Found compound role (no space): '{matched_role}' for {entry.get('club', 'Unknown Club')}")
                    else:
                        # Additional check: if the text contains "manager" but also contains other role indicators
                        # that suggest it's not the main Manager role
                        # Check if these indicators appear NEAR "manager" (within 15 characters)
                        other_role_indicators = ['coach', 'official', 'staff', 'analyst', 'scout', 'kit', 'performance', 'goalkeeping', 'fitness', 'equipment', 'stadium', 'facilities']
                        
                        # Find position of "manager" in text
                        manager_match = re.search(r'(\b|(?<=[a-z]))manager\b', combined_text, re.I)
                        has_other_indicator_near = False
                        
                        if manager_match:
                            manager_start = manager_match.start()
                            manager_end = manager_match.end()
                            
                            # Check a window of 15 characters before and after "manager"
                            context_start = max(0, manager_start - 15)
                            context_end = min(len(combined_text), manager_end + 15)
                            context_text = combined_text[context_start:context_end]
                            
                            print(f"    [DEBUG] Context around 'manager' for {entry.get('club', 'Unknown Club')}: '{context_text}'")
                            
                            # Check if any other role indicator appears in this context
                            for indicator in other_role_indicators:
                                if indicator in context_text and indicator != 'manager':
                                    has_other_indicator_near = True
                                    print(f"    [DEBUG] EXCLUDED - Found '{indicator}' near 'manager' for {entry.get('club', 'Unknown Club')}")
                                    break
                        
                        if has_other_indicator_near:
                            print(f"    [DEBUG] EXCLUDED - Found other role indicator near 'manager' for {entry.get('club', 'Unknown Club')}")
                        else:
                            entry['role'] = 'Manager'
                            print(f"    [DEBUG] ACCEPTED - Found Manager role for {entry.get('club', 'Unknown Club')}")
                else:
                    print(f"    [DEBUG] No 'manager' word found in combined text for {entry.get('club', 'Unknown Club')}")
                
                # Extract dates - "Appointed" column (usually column 2)
                if len(cells) > 2:
                    appointed_text = cells[2].get_text()
                    # Format: "16/17 (01/07/2016)"
                    date_match = re.search(r'(\d{2}/\d{2})\s*\((\d{2}/\d{2}/\d{4})\)', appointed_text)
                    if date_match:
                        entry['appointed_season'] = date_match.group(1)
                        entry['appointed_date'] = date_match.group(2)
                
                # Extract "In charge until" - column 3
                if len(cells) > 3:
                    until_text = cells[3].get_text().strip()
                    if until_text and until_text != '-':
                        date_match = re.search(r'(\d{2}/\d{2})\s*\((\d{2}/\d{2}/\d{4})\)', until_text)
                        if date_match:
                            entry['until_season'] = date_match.group(1)
                            entry['until_date'] = date_match.group(2)
                        else:
                            entry['until_date'] = until_text
                    else:
                        entry['until_date'] = 'Current'
                
                # Extract "from / until" - column 4
                if len(cells) > 4:
                    period_text = cells[4].get_text()
                    period_match = re.search(r'(\d{2}/\d{2})\s*\([^)]+\)\s*/\s*([\-]|(\d{2}/\d{2})\([^)]+\))', period_text)
                    if period_match:
                        entry['period_from'] = period_match.group(1)
                        if period_match.group(2) != '-':
                            entry['period_until'] = period_match.group(3)
                        else:
                            entry['period_until'] = 'Current'
                
                # Extract "Days in charge" - column 5
                if len(cells) > 5:
                    days_text = cells[5].get_text().strip()
                    days_match = re.search(r'(\d+)', days_text)
                    if days_match:
                        entry['days_in_charge'] = int(days_match.group(1))
                
                # Extract Matches, W, D, L - columns 6-9
                if len(cells) > 9:
                    matches_text = cells[6].get_text().strip()
                    matches_match = re.search(r'(\d+)', matches_text)
                    if matches_match:
                        entry['matches'] = int(matches_match.group(1))
                    
                    entry['wins'] = self._extract_number(cells[7].get_text())
                    entry['draws'] = self._extract_number(cells[8].get_text())
                    entry['losses'] = self._extract_number(cells[9].get_text())
                
                # Extract "Players used" - column 10
                if len(cells) > 10:
                    entry['players_used'] = self._extract_number(cells[10].get_text())
                
                # Extract "Ø-Goals" - column 11 (format: "2.49 : 0.94")
                if len(cells) > 11:
                    goals_text = cells[11].get_text().strip()
                    goals_match = re.search(r'([\d.]+)\s*:\s*([\d.]+)', goals_text)
                    if goals_match:
                        entry['avg_goals_for'] = float(goals_match.group(1))
                        entry['avg_goals_against'] = float(goals_match.group(2))
                
                # Extract "PPM" (Points Per Match) - column 12
                if len(cells) > 12:
                    entry['points_per_match'] = self._extract_number(cells[12].get_text(), is_float=True)
                
                # Only add if we have club info AND the role is exactly "Manager"
                if 'club' in entry:
                    if entry.get('role') == 'Manager':
                        career_entries.append(entry)
                    else:
                        # Debug: log entries that were filtered out
                        print(f"    -> Filtered out entry for {entry.get('club', 'Unknown')} - role: {entry.get('role', 'None')}")
                else:
                    print(f"    -> Skipped entry - no club found")
        
        print(f"  -> Extracted {len(career_entries)} career entries (only Manager roles)")
        return career_entries
    
    def _extract_number(self, text, is_float=False):
        """Extract number from text"""
        text = text.strip()
        if text == '-' or not text:
            return None
        
        match = re.search(r'([\d.]+)', text)
        if match:
            if is_float:
                try:
                    return float(match.group(1))
                except ValueError:
                    return None
            else:
                try:
                    return int(match.group(1))
                except ValueError:
                    return None
        return None
    
    def _slugify(self, name):
        """Convert name to URL-friendly slug"""
        # Simple slugification - Transfermarkt uses lowercase with hyphens
        slug = name.lower()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[-\s]+', '-', slug)
        return slug.strip('-')
    
    def scrape_manager_by_id(self, manager_id):
        """
        Scrape all data for a specific manager by ID
        
        Args:
            manager_id: Manager ID
            
        Returns:
            List of dicts with manager profile info and career history
        """
        if not manager_id:
            return []
        
        print(f"Scraping manager with ID: {manager_id}")
        
        # Try to access manager profile page directly by ID
        # Transfermarkt URL format: /trainer/{id} or /profil/trainer/{id}
        profile_urls = [
            f'{self.base_url}/trainer/{manager_id}',
            f'{self.base_url}/profil/trainer/{manager_id}',
            f'{self.base_url}/trainer/profil/trainer/{manager_id}'
        ]
        
        manager_name = None
        profile_url = None
        
        # Try to find the manager's profile page and extract name
        for url in profile_urls:
            print(f"  -> Trying profile URL: {url}")
            soup = self._get_page(url)
            if soup:
                # Try to extract manager name from the page
                # Usually in h1 or in a specific div
                name_elements = [
                    soup.find('h1'),
                    soup.find('div', class_='data-header__headline-wrapper'),
                    soup.find('span', class_='data-header__headline'),
                    soup.find('div', class_='data-header__headline'),
                    soup.find('h1', class_='data-header__headline'),
                    soup.find('div', {'class': re.compile(r'.*headline.*', re.I)}),
                    soup.find('span', {'class': re.compile(r'.*headline.*', re.I)})
                ]
                
                for elem in name_elements:
                    if elem:
                        name_text = elem.get_text().strip()
                        # Clean up the name - remove extra whitespace and newlines
                        name_text = ' '.join(name_text.split())
                        if name_text and len(name_text) > 2:  # Make sure it's a valid name
                            manager_name = name_text
                            profile_url = url
                            print(f"  -> Found manager name: {manager_name}")
                            break
                
                # If still not found, try to find any link with trainer in it
                if not manager_name:
                    trainer_links = soup.find_all('a', href=re.compile(r'/trainer/'))
                    for link in trainer_links:
                        link_text = link.get_text().strip()
                        if link_text and len(link_text) > 2:
                            manager_name = link_text
                            profile_url = url
                            print(f"  -> Found manager name from link: {manager_name}")
                            break
                
                if manager_name:
                    break
        
        if not manager_name:
            print(f"  -> Could not find manager name for ID: {manager_id}")
            return []
        
        # Get manager profile info (date of birth, preferred formation)
        profile_info = self.scrape_manager_profile_info(profile_url)
        
        # Get career history
        career_history = self.scrape_coach_history(manager_name, manager_id)
        
        # Build results in the same format as other scrapers
        results = []
        for entry in career_history:
            # Skip entries that don't have role "Manager" exactly
            if entry.get('role') != 'Manager':
                continue
            
            results.append({
                'league': '',  # Not available when scraping by manager ID
                'league_country': '',
                'current_club': '',  # Not available when scraping by manager ID
                'current_club_url': '',
                'manager': manager_name,
                'manager_id': manager_id,
                'manager_role': 'Manager',
                'date_of_birth': profile_info.get('date_of_birth', ''),
                'preferred_formation': profile_info.get('preferred_formation', ''),
                'history_club': entry.get('club', ''),
                'history_club_url': entry.get('club_url', ''),
                'role': entry.get('role', ''),
                'appointed_season': entry.get('appointed_season', ''),
                'appointed_date': entry.get('appointed_date', ''),
                'until_season': entry.get('until_season', ''),
                'until_date': entry.get('until_date', ''),
                'period_from': entry.get('period_from', ''),
                'period_until': entry.get('period_until', ''),
                'days_in_charge': entry.get('days_in_charge', ''),
                'matches': entry.get('matches', ''),
                'wins': entry.get('wins', ''),
                'draws': entry.get('draws', ''),
                'losses': entry.get('losses', ''),
                'players_used': entry.get('players_used', ''),
                'avg_goals_for': entry.get('avg_goals_for', ''),
                'avg_goals_against': entry.get('avg_goals_against', ''),
                'points_per_match': entry.get('points_per_match', '')
            })
        
        print(f"Scraped {len(results)} career entries for manager {manager_name} (ID: {manager_id})")
        return results
    
    def scrape_all_clubs(self):
        """
        Main method: Scrape all clubs from European leagues, get managers (including Caretaker),
        and their career history
        
        Returns:
            List of dicts with league, club, manager, and career history data
        """
        self.should_stop = False
        
        # Step 1: Get all leagues from Europa page (first page only)
        self._update_progress(0, 0, '', 'Fetching leagues list...')
        leagues = self.scrape_leagues_from_continent('europa')
        
        print(f"Found {len(leagues)} leagues")
        if not leagues:
            self._update_progress(0, 0, '', 'No leagues found')
            return []
        
        # Step 2: Get all clubs from all leagues
        all_clubs = []
        for league in leagues:
            print(f"Fetching clubs from {league['name']}...")
            clubs = self.scrape_clubs_from_league(league['url'])
            for club in clubs:
                club['league'] = league['name']
                club['league_country'] = league.get('country', '')
            all_clubs.extend(clubs)
        
        print(f"Found {len(all_clubs)} clubs from {len(leagues)} leagues")
        if not all_clubs:
            self._update_progress(0, 0, '', 'No clubs found')
            return []
        
        total = len(all_clubs)
        results = []
        
        # Step 3: For each club, get managers (including Caretaker) and career history
        for idx, club in enumerate(all_clubs):
            if self.should_stop:
                self._update_progress(idx, total, club['name'], 'stopped')
                break
            
            self._update_progress(idx + 1, total, club['name'], f'Processing {club["name"]}...')
            print(f"Processing club {idx + 1}/{total}: {club['name']} ({club.get('league', 'Unknown League')})")
            
            # Get current managers (including Caretaker Manager)
            print(f"  -> Attempting to find managers for {club['name']}...")
            managers = self.get_current_manager(club['url'], include_caretaker=False)
            
            if not managers:
                print(f"  -> No managers found for {club['name']}")
                # Skip if no manager
                continue
            
            # Process each manager (Manager and/or Caretaker Manager)
            for manager in managers:
                print(f"  -> Found {manager.get('role', 'Manager')}: {manager['name']} (ID: {manager['id']})")
                
                # Get manager profile info (date of birth, preferred formation)
                profile_info = self.scrape_manager_profile_info(manager.get('profile_url', ''))
                
                # Get career history
                career_history = self.scrape_coach_history(manager['name'], manager['id'])
                
                print(f"  -> Found {len(career_history)} career entries")
                
                # Add to results - ONLY entries with role "Manager"
                for entry in career_history:
                    # Skip entries that don't have role "Manager" exactly
                    if entry.get('role') != 'Manager':
                        continue
                    
                    results.append({
                        'league': club.get('league', ''),
                        'league_country': club.get('league_country', ''),
                        'current_club': club['name'],
                        'current_club_url': club['url'],
                        'manager': manager['name'],
                        'manager_id': manager['id'],
                        'manager_role': manager.get('role', 'Manager'),  # Manager or Caretaker Manager
                        'date_of_birth': profile_info.get('date_of_birth', ''),
                        'preferred_formation': profile_info.get('preferred_formation', ''),
                        'history_club': entry.get('club', ''),
                        'history_club_url': entry.get('club_url', ''),
                        'role': entry.get('role', ''),
                        'appointed_season': entry.get('appointed_season', ''),
                        'appointed_date': entry.get('appointed_date', ''),
                        'until_season': entry.get('until_season', ''),
                        'until_date': entry.get('until_date', ''),
                        'period_from': entry.get('period_from', ''),
                        'period_until': entry.get('period_until', ''),
                        'days_in_charge': entry.get('days_in_charge', ''),
                        'matches': entry.get('matches', ''),
                        'wins': entry.get('wins', ''),
                        'draws': entry.get('draws', ''),
                        'losses': entry.get('losses', ''),
                        'players_used': entry.get('players_used', ''),
                        'avg_goals_for': entry.get('avg_goals_for', ''),
                        'avg_goals_against': entry.get('avg_goals_against', ''),
                        'points_per_match': entry.get('points_per_match', '')
                    })
                    print(f"    - {entry.get('club', '')}: {entry.get('appointed_date', '')} to {entry.get('until_date', '')}")
        
        print(f"Total results: {len(results)}")
        self._update_progress(total, total, '', 'completed')
        return results
    
    def get_current_players(self, club_url):
        """
        Get all current players from club's squad page
        
        Args:
            club_url: URL of the club page
            
        Returns:
            List of dicts with 'name', 'profile_url', 'id', and 'position'
        """
        # Extract club ID and slug from URL
        club_id_match = re.search(r'/verein/(\d+)', club_url)
        if not club_id_match:
            return []
        
        club_id = club_id_match.group(1)
        
        # Extract club slug from URL
        slug_match = re.search(r'/([^/]+)/startseite/verein/', club_url)
        club_slug = slug_match.group(1) if slug_match else ''
        
        players = []
        
        # Access squad page - URL format: /{club-slug}/kader/verein/{club_id}
        squad_urls = []
        if club_slug:
            squad_urls.append(f'{self.base_url}/{club_slug}/kader/verein/{club_id}')
        squad_urls.append(f'{self.base_url}/kader/verein/{club_id}')
        
        for squad_url in squad_urls:
            print(f"  -> Trying squad page: {squad_url}")
            squad_soup = self._get_page(squad_url)
            if squad_soup:
                # Look for player links - format: /profil/spieler/{id}
                player_links = squad_soup.find_all('a', href=re.compile(r'/profil/spieler/\d+'))
                
                seen_players = set()
                for link in player_links:
                    player_id_match = re.search(r'/profil/spieler/(\d+)', link.get('href', ''))
                    if not player_id_match:
                        continue
                    
                    player_id = player_id_match.group(1)
                    if player_id in seen_players:
                        continue
                    seen_players.add(player_id)
                    
                    name = link.text.strip()
                    if not name:
                        # Try to get name from parent elements
                        parent = link.find_parent(['td', 'div', 'span'])
                        if parent:
                            name = parent.get_text().strip()
                    
                    if name:
                        profile_url = urljoin(self.base_url, link['href'])
                        
                        # Extract jersey number from name (format: "#1 Thibaut Courtois" or "1 Thibaut Courtois")
                        jersey_number = ''
                        player_name = name
                        
                        # Check if name starts with # followed by number
                        jersey_match = re.match(r'^#?(\d+)\s+(.+)$', name)
                        if jersey_match:
                            jersey_number = jersey_match.group(1)
                            player_name = jersey_match.group(2).strip()
                        else:
                            # Try alternative pattern: number at the start
                            jersey_match = re.match(r'^(\d+)\s+(.+)$', name)
                            if jersey_match:
                                jersey_number = jersey_match.group(1)
                                player_name = jersey_match.group(2).strip()
                        
                        # Try to extract position from the row
                        position = ''
                        row = link.find_parent('tr')
                        if row:
                            cells = row.find_all('td')
                            # Position is usually in one of the cells
                            for cell in cells:
                                cell_text = cell.get_text().strip().lower()
                                # Common positions
                                if any(pos in cell_text for pos in ['goalkeeper', 'defender', 'midfielder', 'forward', 'attacker', 
                                                                     'torwart', 'verteidiger', 'mittelfeld', 'stürmer', 'angreifer']):
                                    position = cell.get_text().strip()
                                    break
                                # Or look for position abbreviations
                                if cell_text in ['gk', 'df', 'mf', 'fw', 'att']:
                                    position = cell_text.upper()
                                    break
                        
                        players.append({
                            'name': player_name,  # Store clean name without jersey number
                            'jersey_number': jersey_number,  # Store jersey number separately
                            'profile_url': profile_url,
                            'id': player_id,
                            'position': position
                        })
                        print(f"  -> Found player: {player_name} (ID: {player_id}, Jersey: {jersey_number if jersey_number else 'N/A'})")
                
                if players:
                    return players
        
        return players
    
    def scrape_player_profile_info(self, profile_url):
        """
        Scrape player information from player's profile page
        
        Args:
            profile_url: URL of the player's profile page
            
        Returns:
            Dict with player information fields
        """
        if not profile_url:
            return {
                'player_name': '',
                'jersey_number': '',
                'nationality': '',
                'date_of_birth': '',
                'caps': '',
                'goals': '',
                'position': '',
                'height': '',
                'foot': '',
                'current_market_value': ''
            }
        
        print(f"  -> Fetching player profile info from: {profile_url}")
        soup = self._get_page(profile_url)
        if not soup:
            print(f"  -> Failed to fetch player profile page")
            return {
                'player_name': '',
                'jersey_number': '',
                'nationality': '',
                'date_of_birth': '',
                'caps': '',
                'goals': '',
                'position': '',
                'height': '',
                'foot': '',
                'current_market_value': ''
            }
        
        info = {
            'player_name': '',
            'jersey_number': '',
            'nationality': '',
            'date_of_birth': '',
            'caps': '',
            'goals': '',
            'position': '',
            'height': '',
            'foot': '',
            'current_market_value': ''
        }
        
        # Extract Player Name
        name_elements = [
            soup.find('h1', class_='data-header__headline-wrapper'),
            soup.find('h1'),
            soup.find('div', class_='data-header__headline-wrapper'),
            soup.find('span', class_='data-header__headline')
        ]
        for elem in name_elements:
            if elem:
                name_text = elem.get_text().strip()
                if name_text:
                    # Remove jersey number from name if present (format: "#1 Thibaut Courtois" or "1 Thibaut Courtois")
                    jersey_match = re.match(r'^#?(\d+)\s+(.+)$', name_text)
                    if jersey_match:
                        # If jersey number not already set, extract it
                        if not info['jersey_number']:
                            info['jersey_number'] = jersey_match.group(1)
                        info['player_name'] = jersey_match.group(2).strip()
                    else:
                        # Try alternative pattern: number at the start
                        jersey_match = re.match(r'^(\d+)\s+(.+)$', name_text)
                        if jersey_match:
                            if not info['jersey_number']:
                                info['jersey_number'] = jersey_match.group(1)
                            info['player_name'] = jersey_match.group(2).strip()
                        else:
                            info['player_name'] = name_text
                    print(f"    -> Found player name: {info['player_name']}")
                    break
        
        # Extract info from the page - Transfermarkt uses spans/divs, not tables
        # Look for labels and their following values
        
        # Nationality - look for Citizenship label
        citizenship_elem = soup.find(string=re.compile(r'Citizenship', re.I))
        if citizenship_elem:
            parent = citizenship_elem.find_parent(['div', 'span', 'li'])
            if parent:
                # Look for flag image
                flag_img = parent.find('img', alt=True)
                if flag_img:
                    info['nationality'] = flag_img.get('alt', '').strip()
                    print(f"    -> Found nationality: {info['nationality']}")
                else:
                    # Extract text after "Citizenship:"
                    text = parent.get_text()
                    # Remove "Citizenship:" and get the country name
                    country_match = re.search(r'Citizenship:\s*([^\n]+)', text, re.I)
                    if country_match:
                        info['nationality'] = country_match.group(1).strip()
                        print(f"    -> Found nationality: {info['nationality']}")
        
        # Date of Birth
        dob_elem = soup.find(string=re.compile(r'Date of birth', re.I))
        if not dob_elem:
            dob_elem = soup.find(string=re.compile(r'Geburtstag', re.I))
        if dob_elem:
            parent = dob_elem.find_parent(['div', 'span', 'li'])
            if parent:
                text = parent.get_text()
                # Extract date (format: DD/MM/YYYY or DD-MM-YYYY)
                date_match = re.search(r'(\d{1,2}[/-]\d{1,2}[/-]\d{4})', text)
                if date_match:
                    info['date_of_birth'] = date_match.group(1)
                    print(f"    -> Found date of birth: {info['date_of_birth']}")
        
        # Position - look for "Main position"
        # First try to find dt/dd structure
        dt_elem = soup.find('dt', string=re.compile(r'Main position', re.I))
        if dt_elem:
            dd_elem = dt_elem.find_next_sibling('dd')
            if dd_elem:
                position_text = dd_elem.get_text().strip()
                if position_text:
                    info['position'] = position_text
                    print(f"    -> Found position: {info['position']}")
        
        # If not found, try other methods
        if not info['position']:
            position_elem = soup.find(string=re.compile(r'Main position', re.I))
            if not position_elem:
                position_elem = soup.find(string=re.compile(r'Hauptposition', re.I))
            if position_elem:
                parent = position_elem.find_parent(['div', 'span', 'li', 'dt'])
                if parent:
                    # Look for info-table__content span (common structure)
                    content_span = parent.find_next('span', class_=re.compile(r'info-table__content', re.I))
                    if content_span:
                        position_text = content_span.get_text().strip()
                        if position_text and position_text.lower() not in ['main position', 'hauptposition']:
                            info['position'] = position_text
                            print(f"    -> Found position: {info['position']}")
                    else:
                        # Look for dd element
                        dd_elem = parent.find_next('dd')
                        if dd_elem:
                            position_text = dd_elem.get_text().strip()
                            if position_text:
                                info['position'] = position_text
                                print(f"    -> Found position: {info['position']}")
                        else:
                            # Look for any span/div after
                            next_elem = parent.find_next(['span', 'div', 'a'])
                            if next_elem:
                                position_text = next_elem.get_text().strip()
                                # Clean up
                                position_text = re.sub(r'^Main position[:\s]+', '', position_text, flags=re.I).strip()
                                position_text = position_text.split('\n')[0].strip()
                                if position_text and position_text.lower() not in ['main position', 'hauptposition']:
                                    info['position'] = position_text
                                    print(f"    -> Found position: {info['position']}")
        
        # Height
        height_elem = soup.find(string=re.compile(r'Height', re.I))
        if not height_elem:
            height_elem = soup.find(string=re.compile(r'Größe|Grösse', re.I))
        if height_elem:
            parent = height_elem.find_parent(['div', 'span', 'li'])
            if parent:
                text = parent.get_text()
                # Extract height (format: X,XX m or X.XX m)
                height_match = re.search(r'([\d.,]+)\s*m', text)
                if height_match:
                    height_val = height_match.group(1).replace(',', '.')
                    info['height'] = height_val + ' m'
                    print(f"    -> Found height: {info['height']}")
        
        # Foot
        foot_elem = soup.find(string=re.compile(r'Foot', re.I))
        if not foot_elem:
            foot_elem = soup.find(string=re.compile(r'Fuß|Fuss', re.I))
        if foot_elem:
            parent = foot_elem.find_parent(['div', 'span', 'li'])
            if parent:
                # Look for next sibling with the foot value
                next_elem = parent.find_next(['span', 'div', 'a'])
                if next_elem:
                    foot_text = next_elem.get_text().strip()
                    if foot_text and foot_text.lower() not in ['foot', 'fuß', 'fuss']:
                        info['foot'] = foot_text
                        print(f"    -> Found foot: {info['foot']}")
                else:
                    # Extract from text
                    text = parent.get_text()
                    foot_match = re.search(r'Foot[:\s]+([^\n]+)', text, re.I)
                    if foot_match:
                        foot_text = foot_match.group(1).strip()
                        # Get first line only
                        foot_text = foot_text.split('\n')[0].strip()
                        info['foot'] = foot_text
                        print(f"    -> Found foot: {info['foot']}")
        
        # Caps/Goals - usually together
        caps_goals_elem = soup.find(string=re.compile(r'Caps/Goals', re.I))
        if not caps_goals_elem:
            caps_goals_elem = soup.find(string=re.compile(r'Länderspiele', re.I))
        if caps_goals_elem:
            parent = caps_goals_elem.find_parent(['div', 'span', 'li'])
            if parent:
                text = parent.get_text()
                # Extract caps and goals (format: "107 / 0" or "107/0")
                caps_goals_match = re.search(r'(\d+)\s*/\s*(\d+)', text)
                if caps_goals_match:
                    info['caps'] = caps_goals_match.group(1)
                    info['goals'] = caps_goals_match.group(2)
                    print(f"    -> Found caps: {info['caps']}, goals: {info['goals']}")
                else:
                    # Try to find just caps
                    caps_match = re.search(r'(\d+)', text)
                    if caps_match:
                        info['caps'] = caps_match.group(1)
                        print(f"    -> Found caps: {info['caps']}")
        
        # Extract Current Market Value (usually in a separate section)
        market_value_elements = soup.find_all(string=re.compile(r'€|Market value|Marktwert', re.I))
        for elem in market_value_elements:
            parent = elem.find_parent(['div', 'span', 'td'])
            if parent:
                text = parent.get_text()
                # Look for value like "€18.00m" or "€18,000,000"
                value_match = re.search(r'€\s*([\d.,]+)\s*[mM]', text)
                if value_match:
                    info['current_market_value'] = '€' + value_match.group(1) + 'm'
                    print(f"    -> Found market value: {info['current_market_value']}")
                    break
        
        # Alternative: Look for market value in specific divs
        if not info['current_market_value']:
            market_value_divs = soup.find_all(['div', 'span'], class_=re.compile(r'value|marktwert', re.I))
            for div in market_value_divs:
                text = div.get_text()
                value_match = re.search(r'€\s*([\d.,]+)\s*[mM]', text)
                if value_match:
                    info['current_market_value'] = '€' + value_match.group(1) + 'm'
                    print(f"    -> Found market value (alternative): {info['current_market_value']}")
                    break
        
        return info
    
    def scrape_all_players(self):
        """
        Main method: Scrape all players from European leagues
        
        Returns:
            List of dicts with league, club, and player data
        """
        self.should_stop = False
        
        # Step 1: Get all leagues from Europa page
        self._update_progress(0, 0, '', 'Fetching leagues list...')
        leagues = self.scrape_leagues_from_continent('europa')
        
        print(f"Found {len(leagues)} leagues")
        if not leagues:
            self._update_progress(0, 0, '', 'No leagues found')
            return []
        
        # Step 2: Get all clubs from all leagues
        all_clubs = []
        for league in leagues:
            print(f"Fetching clubs from {league['name']}...")
            clubs = self.scrape_clubs_from_league(league['url'])
            for club in clubs:
                club['league'] = league['name']
                club['league_country'] = league.get('country', '')
            all_clubs.extend(clubs)
        
        print(f"Found {len(all_clubs)} clubs from {len(leagues)} leagues")
        if not all_clubs:
            self._update_progress(0, 0, '', 'No clubs found')
            return []
        
        total = len(all_clubs)
        results = []
        
        # Step 3: For each club, get players and their info
        for idx, club in enumerate(all_clubs):
            if self.should_stop:
                self._update_progress(idx, total, club['name'], 'stopped')
                break
            
            self._update_progress(idx + 1, total, club['name'], f'Processing {club["name"]}...')
            print(f"Processing club {idx + 1}/{total}: {club['name']} ({club.get('league', 'Unknown League')})")
            
            print(f"  -> Attempting to find players for {club['name']}...")
            players = self.get_current_players(club['url'])
            
            if not players:
                print(f"  -> No players found for {club['name']}")
                continue
            
            # Process each player
            for player in players:
                print(f"  -> Found player: {player['name']} (ID: {player['id']})")
                
                # Get player profile info
                profile_info = self.scrape_player_profile_info(player.get('profile_url', ''))
                
                results.append({
                    'league': club.get('league', ''),
                    'league_country': club.get('league_country', ''),
                    'current_club': club['name'],
                    'current_club_url': club['url'],
                    'player_name': profile_info.get('player_name', player.get('name', '')),
                    'player_id': player['id'],
                    'jersey_number': profile_info.get('jersey_number', player.get('jersey_number', '')),
                    'nationality': profile_info.get('nationality', ''),
                    'date_of_birth': profile_info.get('date_of_birth', ''),
                    'caps': profile_info.get('caps', ''),
                    'goals': profile_info.get('goals', ''),
                    'position': profile_info.get('position', player.get('position', '')),
                    'height': profile_info.get('height', ''),
                    'foot': profile_info.get('foot', ''),
                    'current_market_value': profile_info.get('current_market_value', '')
                })
        
        print(f"Total results: {len(results)}")
        self._update_progress(total, total, '', 'completed')
        return results