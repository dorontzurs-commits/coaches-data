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
                            
                            # Check for Manager (ONLY Manager, not Caretaker Manager, not Coach, etc.)
                            role = None
                            is_manager = False
                            
                            # Look for "Manager" position - must be exactly "Manager" not other roles
                            # Check the position text - it should contain "Manager" but NOT other roles
                            position_text = name_cell.get_text().lower()
                            row_text_lower = row_text.lower()
                            
                            # First, check if "manager" appears as a standalone word
                            manager_pattern = r'\bmanager\b'
                            has_manager_word = re.search(manager_pattern, position_text) or re.search(manager_pattern, row_text_lower)
                            
                            if has_manager_word:
                                # Exclude all other roles that contain "manager" - must be ONLY "Manager"
                                excluded_roles = [
                                    'loan player manager', 'player manager', 'team manager',
                                    'caretaker manager', 'assistant manager', 'general manager',
                                    'sporting manager', 'technical manager', 'youth manager',
                                    'academy manager', 'development manager', 'operations manager',
                                    'business manager', 'commercial manager', 'marketing manager'
                                ]
                                
                                # Exclude other terms that indicate non-manager roles
                                excluded_terms = [
                                    'caretaker', 'assistant', 'goalkeeping', 'fitness', 
                                    'co-trainer', 'coach', 'trainer', 'performance', 
                                    'physiotherapist', 'medical', 'nutritionist', 'dietitian',
                                    'scientist', 'analyst', 'coordinator', 'academy', 'youth',
                                    'loan', 'player', 'team', 'general', 'sporting', 'technical',
                                    'development', 'operations', 'business', 'commercial', 'marketing'
                                ]
                                
                                # Check if any excluded role appears in the text
                                has_excluded_role = any(excluded_role in row_text_lower for excluded_role in excluded_roles)
                                
                                # Check if any excluded term appears as a standalone word
                                excluded_as_words = False
                                for term in excluded_terms:
                                    term_pattern = r'\b' + re.escape(term) + r'\b'
                                    if re.search(term_pattern, position_text) or re.search(term_pattern, row_text_lower):
                                        excluded_as_words = True
                                        break
                                
                                # Only accept if it's exactly "Manager" and no excluded roles/terms found
                                if not has_excluded_role and not excluded_as_words:
                                    # Additional check: make sure "manager" is not part of a compound role
                                    # Look for patterns like "X Manager" where X indicates a different role
                                    compound_pattern = r'\b(\w+)\s+manager\b'
                                    matches = re.findall(compound_pattern, row_text_lower)
                                    
                                    # Valid prefixes that are acceptable (Head Manager, First Manager, etc.)
                                    valid_prefixes = ['head', 'first', 'first-team']
                                    
                                    # If we found compound roles, check if they're valid
                                    is_valid_manager = True
                                    if matches:
                                        for prefix in matches:
                                            if prefix not in valid_prefixes:
                                                # Found an invalid compound role (e.g., "loan player manager")
                                                is_valid_manager = False
                                                break
                                    
                                    if is_valid_manager:
                                        is_manager = True
                                        role = 'Manager'
                            
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
                    # Check context around each link to find ONLY Manager
                    excluded_roles = [
                        'loan player manager', 'player manager', 'team manager',
                        'caretaker manager', 'assistant manager', 'general manager',
                        'sporting manager', 'technical manager', 'youth manager',
                        'academy manager', 'development manager', 'operations manager',
                        'business manager', 'commercial manager', 'marketing manager'
                    ]
                    
                    excluded_terms = [
                        'caretaker', 'assistant', 'goalkeeping', 'fitness', 
                        'co-trainer', 'coach', 'trainer', 'performance', 
                        'physiotherapist', 'medical', 'nutritionist', 'dietitian',
                        'scientist', 'analyst', 'coordinator', 'academy', 'youth',
                        'loan', 'player', 'team', 'general', 'sporting', 'technical',
                        'development', 'operations', 'business', 'commercial', 'marketing'
                    ]
                    
                    for link in trainer_links:
                        parent = link.find_parent(['tr', 'td', 'div'])
                        if parent:
                            parent_text = parent.get_text().lower()
                            
                            # Check if "manager" appears as a standalone word
                            manager_pattern = r'\bmanager\b'
                            has_manager = re.search(manager_pattern, parent_text)
                            
                            if has_manager:
                                # Check if any excluded role appears
                                has_excluded_role = any(excluded_role in parent_text for excluded_role in excluded_roles)
                                
                                # Check if any excluded term appears as a standalone word
                                has_excluded_term = False
                                for term in excluded_terms:
                                    term_pattern = r'\b' + re.escape(term) + r'\b'
                                    if re.search(term_pattern, parent_text):
                                        has_excluded_term = True
                                        break
                                
                                # Only accept if it's exactly "Manager" and no excluded roles/terms found
                                if not has_excluded_role and not has_excluded_term:
                                    name = link.text.strip()
                                    if name:
                                        profile_url = urljoin(self.base_url, link['href'])
                                        manager_id = self._extract_manager_id(profile_url)
                                        if manager_id:
                                            print(f"  -> Found Manager (fallback): {name} (ID: {manager_id})")
                                            managers.append({
                                                'name': name,
                                                'profile_url': profile_url,
                                                'id': manager_id,
                                                'role': 'Manager'
                                            })
        
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
                
                # Extract role (Manager/Coach etc.)
                role_text = club_cell.get_text()
                role_match = re.search(r'(Manager|Coach|Head Coach)', role_text, re.I)
                if role_match:
                    entry['role'] = role_match.group(1)
                
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
                
                # Only add if we have at least club info
                if 'club' in entry:
                    career_entries.append(entry)
        
        print(f"  -> Extracted {len(career_entries)} career entries")
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
                
                # Get career history
                career_history = self.scrape_coach_history(manager['name'], manager['id'])
                
                print(f"  -> Found {len(career_history)} career entries")
                
                # Add to results
                for entry in career_history:
                    results.append({
                        'league': club.get('league', ''),
                        'league_country': club.get('league_country', ''),
                        'current_club': club['name'],
                        'current_club_url': club['url'],
                        'manager': manager['name'],
                        'manager_id': manager['id'],
                        'manager_role': manager.get('role', 'Manager'),  # Manager or Caretaker Manager
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
