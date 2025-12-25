# Fix encoding for Windows console
import sys

def safe_str(s):
    """Convert string to safe ASCII string for Windows console"""
    if isinstance(s, str):
        try:
            # Try to encode as UTF-8 first, then fallback to ASCII with replacement
            return s.encode('utf-8', 'replace').decode('utf-8', 'replace')
        except:
            try:
                return s.encode('ascii', 'replace').decode('ascii')
            except:
                return str(s).encode('ascii', 'replace').decode('ascii')
    try:
        return str(s).encode('utf-8', 'replace').decode('utf-8', 'replace')
    except:
        return str(s).encode('ascii', 'replace').decode('ascii')

from flask import Flask, jsonify, request
from flask_cors import CORS
import threading
import time
import re
from scraper.scraper import TransfermarktScraper

app = Flask(__name__)
CORS(app)

# Global scraper instance and state
scraper_instance = None
scraper_thread = None
scraper_state = {
    'running': False,
    'progress': {
        'current': 0,
        'total': 0,
        'current_club': '',
        'status': 'idle'
    },
    'results': []
}

# Global player scraper instance and state (separate from coach scraper)
player_scraper_instance = None
player_scraper_thread = None
player_scraper_state = {
    'running': False,
    'progress': {
        'current': 0,
        'total': 0,
        'current_club': '',
        'status': 'idle'
    },
    'results': []
}

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get current scraper status and progress"""
    try:
        return jsonify(scraper_state)
    except Exception as e:
        import traceback
        print(f"Error in get_status: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/start', methods=['POST'])
def start_scraper():
    """Start the scraper for all clubs from all leagues, or from a specific league"""
    global scraper_instance, scraper_thread, scraper_state
    
    if scraper_state['running']:
        return jsonify({'error': 'Scraper is already running'}), 400
    
    try:
        data = request.json or {}
        league_url = data.get('league_url')
        league_name = data.get('league_name')
        league_urls = data.get('league_urls')  # Array of {url, name} objects
        continent = data.get('continent')
        
        scraper_state['running'] = True
        scraper_state['progress']['status'] = 'starting'
        scraper_state['results'] = []
        
        scraper_instance = TransfermarktScraper(callback=update_progress)
        
        if league_urls and len(league_urls) > 0:
            # Run scraper for multiple leagues
            scraper_thread = threading.Thread(target=run_multiple_leagues_scraper, args=(league_urls,))
        elif league_url:
            # Run scraper for specific league only
            scraper_thread = threading.Thread(target=run_league_scraper, args=(league_url, league_name))
        elif continent:
            # Run scraper for all leagues from a continent
            scraper_thread = threading.Thread(target=run_continent_scraper, args=(continent,))
        else:
            # Run scraper for all leagues (default: Europa)
            scraper_thread = threading.Thread(target=run_scraper)
        
        scraper_thread.daemon = True
        scraper_thread.start()
        
        return jsonify({'message': 'Scraper started'})
    except Exception as e:
        import traceback
        print(f"Error in start_scraper: {e}")
        print(traceback.format_exc())
        scraper_state['running'] = False
        return jsonify({'error': str(e)}), 500

@app.route('/api/stop', methods=['POST'])
def stop_scraper():
    """Stop the scraper"""
    global scraper_state, scraper_instance
    
    if not scraper_state['running']:
        return jsonify({'error': 'Scraper is not running'}), 400
    
    scraper_state['running'] = False
    scraper_state['progress']['status'] = 'stopping'
    
    # Signal scraper to stop
    if scraper_instance:
        scraper_instance.should_stop = True
    
    return jsonify({'message': 'Scraper stop requested'})

@app.route('/api/results', methods=['GET'])
def get_results():
    """Get scraper results"""
    return jsonify(scraper_state['results'])

@app.route('/api/reset', methods=['POST'])
def reset_scraper():
    """Reset scraper state"""
    global scraper_state
    
    if scraper_state['running']:
        return jsonify({'error': 'Cannot reset while scraper is running'}), 400
    
    scraper_state = {
        'running': False,
        'progress': {
            'current': 0,
            'total': 0,
            'current_club': '',
            'status': 'idle'
        },
        'results': []
    }
    
    return jsonify({'message': 'Scraper reset'})

@app.route('/api/leagues', methods=['GET'])
def get_leagues():
    """Get list of all leagues from a continent page"""
    try:
        continent = request.args.get('continent', 'europa')
        
        # Validate continent
        valid_continents = ['europa', 'amerika', 'afrika', 'asien']
        if continent not in valid_continents:
            return jsonify({'error': f'Invalid continent. Must be one of: {", ".join(valid_continents)}'}), 400
        
        # Use continent-specific cache key
        cache_key = f'leagues_{continent}'
        if not hasattr(get_leagues, 'cache'):
            get_leagues.cache = {}
        
        if cache_key not in get_leagues.cache:
            scraper = TransfermarktScraper()
            leagues = scraper.scrape_leagues_from_continent(continent)
            # Add an ID to each league (using index or URL hash)
            for idx, league in enumerate(leagues):
                # Extract league ID from URL if possible, otherwise use index
                match = re.search(r'/wettbewerb/([A-Z0-9]+)', league['url'])
                if match:
                    league['id'] = match.group(1)
                else:
                    league['id'] = str(idx)
            get_leagues.cache[cache_key] = leagues
        
        return jsonify(get_leagues.cache[cache_key])
    except Exception as e:
        import traceback
        print(f"Error in get_leagues: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/clubs', methods=['POST'])
def get_clubs():
    """Get list of clubs from a specific league"""
    try:
        data = request.json
        league_url = data.get('league_url')
        
        if not league_url:
            return jsonify({'error': 'league_url is required'}), 400
        
        print(f"Fetching clubs for league: {league_url}")
        scraper = TransfermarktScraper()
        clubs = scraper.scrape_clubs_from_league(league_url)
        print(f"Returning {len(clubs)} clubs")
        return jsonify(clubs)
    except Exception as e:
        import traceback
        print(f"Error in get_clubs: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/start-club', methods=['POST'])
def start_club_scraper():
    """Start scraper for a specific club"""
    global scraper_instance, scraper_thread, scraper_state
    
    if scraper_state['running']:
        return jsonify({'error': 'Scraper is already running'}), 400
    
    try:
        data = request.json
        club_url = data.get('club_url')
        club_name = data.get('club_name', 'Unknown Club')
        
        if not club_url:
            return jsonify({'error': 'club_url is required'}), 400
        
        scraper_state['running'] = True
        scraper_state['progress']['status'] = 'starting'
        scraper_state['results'] = []
        
        scraper_instance = TransfermarktScraper(callback=update_progress)
        
        scraper_thread = threading.Thread(target=run_single_club_scraper, args=(club_url, club_name))
        scraper_thread.daemon = True
        scraper_thread.start()
        
        return jsonify({'message': f'Scraper started for {club_name}'})
    except Exception as e:
        import traceback
        print(f"Error in start_club_scraper: {e}")
        print(traceback.format_exc())
        scraper_state['running'] = False
        return jsonify({'error': str(e)}), 500

@app.route('/api/start-clubs', methods=['POST'])
def start_clubs_scraper():
    """Start scraper for multiple clubs"""
    global scraper_instance, scraper_thread, scraper_state
    
    if scraper_state['running']:
        return jsonify({'error': 'Scraper is already running'}), 400
    
    try:
        data = request.json
        clubs = data.get('clubs', [])
        
        if not clubs or len(clubs) == 0:
            return jsonify({'error': 'clubs array is required'}), 400
        
        scraper_state['running'] = True
        scraper_state['progress']['status'] = 'starting'
        scraper_state['results'] = []
        
        scraper_instance = TransfermarktScraper(callback=update_progress)
        
        scraper_thread = threading.Thread(target=run_multiple_clubs_scraper, args=(clubs,))
        scraper_thread.daemon = True
        scraper_thread.start()
        
        return jsonify({'message': f'Scraper started for {len(clubs)} club(s)'})
    except Exception as e:
        import traceback
        print(f"Error in start_clubs_scraper: {e}")
        print(traceback.format_exc())
        scraper_state['running'] = False
        return jsonify({'error': str(e)}), 500

@app.route('/api/start-manager', methods=['POST'])
def start_manager_scraper():
    """Start scraper for a specific manager by ID"""
    global scraper_instance, scraper_thread, scraper_state
    
    if scraper_state['running']:
        return jsonify({'error': 'Scraper is already running'}), 400
    
    try:
        data = request.json
        manager_id = data.get('manager_id')
        
        if not manager_id:
            return jsonify({'error': 'manager_id is required'}), 400
        
        # Validate that manager_id is a number
        try:
            manager_id = str(int(manager_id))  # Convert to string and validate it's a number
        except (ValueError, TypeError):
            return jsonify({'error': 'manager_id must be a valid number'}), 400
        
        scraper_state['running'] = True
        scraper_state['progress']['status'] = 'starting'
        scraper_state['results'] = []
        
        scraper_instance = TransfermarktScraper(callback=update_progress)
        
        scraper_thread = threading.Thread(target=run_manager_scraper, args=(manager_id,))
        scraper_thread.daemon = True
        scraper_thread.start()
        
        return jsonify({'message': f'Scraper started for manager ID: {manager_id}'})
    except Exception as e:
        import traceback
        print(f"Error in start_manager_scraper: {e}")
        print(traceback.format_exc())
        scraper_state['running'] = False
        return jsonify({'error': str(e)}), 500

def update_progress(current, total, current_club, status):
    """Callback to update progress"""
    scraper_state['progress'] = {
        'current': current,
        'total': total,
        'current_club': current_club,
        'status': status
    }

def run_scraper():
    """Run the scraper in a separate thread"""
    global scraper_state, scraper_instance
    
    try:
        print("Starting scraper...")
        results = scraper_instance.scrape_all_clubs()
        print(f"Scraper finished with {len(results)} results")
        scraper_state['results'] = results
        if scraper_instance.should_stop:
            scraper_state['progress']['status'] = 'stopped'
        else:
            scraper_state['progress']['status'] = 'completed'
    except Exception as e:
        import traceback
        print(f"Error in scraper: {str(e)}")
        print(traceback.format_exc())
        scraper_state['progress']['status'] = f'error: {safe_str(e)}'
    finally:
        scraper_state['running'] = False
        print("Scraper finished")

def run_league_scraper(league_url, league_name=None):
    """Run scraper for all clubs from a specific league"""
    global scraper_state, scraper_instance
    
    try:
        print(f"Starting scraper for league: {league_url}")
        scraper_state['progress']['status'] = 'Fetching clubs from league...'
        
        # Get clubs from the league
        clubs = scraper_instance.scrape_clubs_from_league(league_url)
        
        if not clubs:
            print("No clubs found in league")
            scraper_state['results'] = []
            scraper_state['progress']['status'] = 'No clubs found'
            scraper_state['running'] = False
            return
        
        # Use provided league name, or extract from URL as fallback
        if not league_name:
            import re
            league_match = re.search(r'/([^/]+)/startseite/wettbewerb/', league_url)
            league_name = league_match.group(1).replace('-', ' ').title() if league_match else 'Unknown League'
        
        total = len(clubs)
        results = []
        
        # Process each club
        for idx, club in enumerate(clubs):
            if scraper_instance.should_stop:
                scraper_state['progress']['status'] = 'stopped'
                break
            
            scraper_state['progress']['current'] = idx + 1
            scraper_state['progress']['total'] = total
            scraper_state['progress']['current_club'] = safe_str(club['name'])
            scraper_state['progress']['status'] = f'Processing {club["name"]}...'
            
            print(f"Processing club {idx + 1}/{total}: {club['name']}")
            
            # Get managers
            managers = scraper_instance.get_current_manager(club['url'], include_caretaker=False)
            
            if not managers:
                print(f"  -> No managers found for {club['name']}")
                continue
            
            # Process each manager
            for manager in managers:
                # Get manager profile info (date of birth, preferred formation)
                profile_info = scraper_instance.scrape_manager_profile_info(manager.get('profile_url', ''))
                
                career_history = scraper_instance.scrape_coach_history(manager['name'], manager['id'])
                
                for entry in career_history:
                    results.append({
                        'league': league_name,
                        'league_country': '',
                        'current_club': club['name'],
                        'current_club_url': club['url'],
                        'manager': manager['name'],
                        'manager_id': manager['id'],
                        'manager_role': manager.get('role', 'Manager'),
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
        
        print(f"Scraper finished with {len(results)} results")
        scraper_state['results'] = results
        scraper_state['progress']['current'] = total
        scraper_state['progress']['status'] = 'completed'
        
    except Exception as e:
        import traceback
        print(f"Error in league scraper: {str(e)}")
        print(traceback.format_exc())
        scraper_state['progress']['status'] = f'error: {safe_str(e)}'
    finally:
        scraper_state['running'] = False
        print("League scraper finished")

def run_multiple_leagues_scraper(league_urls):
    """Run scraper for multiple leagues"""
    global scraper_state, scraper_instance
    
    try:
        print(f"Starting scraper for {len(league_urls)} leagues")
        scraper_state['progress']['status'] = 'Fetching clubs from leagues...'
        
        # Get all clubs from all selected leagues
        all_clubs = []
        for league_info in league_urls:
            league_url = league_info.get('url')
            league_name = league_info.get('name', 'Unknown League')
            
            print(f"Fetching clubs from {league_name}...")
            clubs = scraper_instance.scrape_clubs_from_league(league_url)
            for club in clubs:
                club['league'] = league_name
                club['league_country'] = ''
            all_clubs.extend(clubs)
        
        if not all_clubs:
            print("No clubs found in selected leagues")
            scraper_state['results'] = []
            scraper_state['progress']['status'] = 'No clubs found'
            scraper_state['running'] = False
            return
        
        total = len(all_clubs)
        results = []
        
        # Process each club
        for idx, club in enumerate(all_clubs):
            if scraper_instance.should_stop:
                scraper_state['progress']['status'] = 'stopped'
                break
            
            scraper_state['progress']['current'] = idx + 1
            scraper_state['progress']['total'] = total
            scraper_state['progress']['current_club'] = safe_str(club['name'])
            scraper_state['progress']['status'] = f'Processing {club["name"]}...'
            
            print(f"Processing club {idx + 1}/{total}: {club['name']} ({club.get('league', 'Unknown League')})")
            
            # Get managers
            managers = scraper_instance.get_current_manager(club['url'], include_caretaker=False)
            
            if not managers:
                print(f"  -> No managers found for {club['name']}")
                continue
            
            # Process each manager
            for manager in managers:
                # Get manager profile info (date of birth, preferred formation)
                profile_info = scraper_instance.scrape_manager_profile_info(manager.get('profile_url', ''))
                
                career_history = scraper_instance.scrape_coach_history(manager['name'], manager['id'])
                
                for entry in career_history:
                    results.append({
                        'league': club.get('league', ''),
                        'league_country': club.get('league_country', ''),
                        'current_club': club['name'],
                        'current_club_url': club['url'],
                        'manager': manager['name'],
                        'manager_id': manager['id'],
                        'manager_role': manager.get('role', 'Manager'),
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
        
        print(f"Scraper finished with {len(results)} results")
        scraper_state['results'] = results
        scraper_state['progress']['current'] = total
        scraper_state['progress']['status'] = 'completed'
        
    except Exception as e:
        import traceback
        print(f"Error in multiple leagues scraper: {str(e)}")
        print(traceback.format_exc())
        scraper_state['progress']['status'] = f'error: {safe_str(e)}'
    finally:
        scraper_state['running'] = False
        print("Multiple leagues scraper finished")

def run_continent_scraper(continent):
    """Run scraper for all leagues from a continent"""
    global scraper_state, scraper_instance
    
    try:
        print(f"Starting scraper for continent: {continent}")
        scraper_state['progress']['status'] = f'Fetching leagues from {continent}...'
        
        # Get all leagues from the continent
        leagues = scraper_instance.scrape_leagues_from_continent(continent)
        
        if not leagues:
            print("No leagues found in continent")
            scraper_state['results'] = []
            scraper_state['progress']['status'] = 'No leagues found'
            scraper_state['running'] = False
            return
        
        # Get all clubs from all leagues
        all_clubs = []
        for league in leagues:
            print(f"Fetching clubs from {league['name']}...")
            clubs = scraper_instance.scrape_clubs_from_league(league['url'])
            for club in clubs:
                club['league'] = league['name']
                club['league_country'] = league.get('country', '')
            all_clubs.extend(clubs)
        
        if not all_clubs:
            print("No clubs found")
            scraper_state['results'] = []
            scraper_state['progress']['status'] = 'No clubs found'
            scraper_state['running'] = False
            return
        
        total = len(all_clubs)
        results = []
        
        # Process each club
        for idx, club in enumerate(all_clubs):
            if scraper_instance.should_stop:
                scraper_state['progress']['status'] = 'stopped'
                break
            
            scraper_state['progress']['current'] = idx + 1
            scraper_state['progress']['total'] = total
            scraper_state['progress']['current_club'] = safe_str(club['name'])
            scraper_state['progress']['status'] = f'Processing {club["name"]}...'
            
            print(f"Processing club {idx + 1}/{total}: {club['name']} ({club.get('league', 'Unknown League')})")
            
            # Get managers
            managers = scraper_instance.get_current_manager(club['url'], include_caretaker=False)
            
            if not managers:
                print(f"  -> No managers found for {club['name']}")
                continue
            
            # Process each manager
            for manager in managers:
                # Get manager profile info (date of birth, preferred formation)
                profile_info = scraper_instance.scrape_manager_profile_info(manager.get('profile_url', ''))
                
                career_history = scraper_instance.scrape_coach_history(manager['name'], manager['id'])
                
                for entry in career_history:
                    results.append({
                        'league': club.get('league', ''),
                        'league_country': club.get('league_country', ''),
                        'current_club': club['name'],
                        'current_club_url': club['url'],
                        'manager': manager['name'],
                        'manager_id': manager['id'],
                        'manager_role': manager.get('role', 'Manager'),
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
        
        print(f"Scraper finished with {len(results)} results")
        scraper_state['results'] = results
        scraper_state['progress']['current'] = total
        scraper_state['progress']['status'] = 'completed'
        
    except Exception as e:
        import traceback
        print(f"Error in continent scraper: {str(e)}")
        print(traceback.format_exc())
        scraper_state['progress']['status'] = f'error: {safe_str(e)}'
    finally:
        scraper_state['running'] = False
        print("Continent scraper finished")

def run_single_club_scraper(club_url, club_name):
    """Run scraper for a single club"""
    global scraper_state, scraper_instance
    
    try:
        print(f"Starting scraper for single club: {club_name}")
        scraper_state['progress']['total'] = 1
        scraper_state['progress']['current'] = 0
        scraper_state['progress']['current_club'] = safe_str(club_name)
        scraper_state['progress']['status'] = f'Processing {club_name}...'
        
        # Get managers for the club
        managers = scraper_instance.get_current_manager(club_url, include_caretaker=False)
        
        if not managers:
            print(f"No managers found for {club_name}")
            scraper_state['results'] = []
            scraper_state['progress']['status'] = f'No managers found for {club_name}'
            scraper_state['running'] = False
            return
        
        results = []
        # Extract league info from club URL if possible, or leave empty
        league = ''
        league_country = ''
        
        # Process each manager
        for manager in managers:
            print(f"  -> Processing {manager.get('role', 'Manager')}: {manager['name']}")
            
            # Get manager profile info (date of birth, preferred formation)
            profile_info = scraper_instance.scrape_manager_profile_info(manager.get('profile_url', ''))
            
            # Get career history
            career_history = scraper_instance.scrape_coach_history(manager['name'], manager['id'])
            
            # Add to results
            for entry in career_history:
                results.append({
                    'league': league,
                    'league_country': league_country,
                    'current_club': club_name,
                    'current_club_url': club_url,
                    'manager': manager['name'],
                    'manager_id': manager['id'],
                    'manager_role': manager.get('role', 'Manager'),
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
        
        print(f"Scraper finished with {len(results)} results for {club_name}")
        scraper_state['results'] = results
        scraper_state['progress']['current'] = 1
        scraper_state['progress']['status'] = 'completed'
        
    except Exception as e:
        import traceback
        print(f"Error in single club scraper: {str(e)}")
        print(traceback.format_exc())
        scraper_state['progress']['status'] = f'error: {safe_str(e)}'
    finally:
        scraper_state['running'] = False
        print("Single club scraper finished")

def run_multiple_clubs_scraper(clubs):
    """Run scraper for multiple clubs"""
    global scraper_state, scraper_instance
    
    try:
        print(f"Starting scraper for {len(clubs)} clubs")
        scraper_state['progress']['total'] = len(clubs)
        scraper_state['progress']['current'] = 0
        scraper_state['progress']['status'] = 'Processing clubs...'
        
        results = []
        
        # Process each club
        for idx, club_info in enumerate(clubs):
            if scraper_instance.should_stop:
                scraper_state['progress']['status'] = 'stopped'
                break
            
            club_url = club_info.get('url')
            club_name = club_info.get('name', 'Unknown Club')
            
            scraper_state['progress']['current'] = idx + 1
            scraper_state['progress']['current_club'] = safe_str(club_name)
            scraper_state['progress']['status'] = f'Processing {club_name}...'
            
            print(f"Processing club {idx + 1}/{len(clubs)}: {club_name}")
            
            # Get managers for the club
            managers = scraper_instance.get_current_manager(club_url, include_caretaker=False)
            
            if not managers:
                print(f"  -> No managers found for {club_name}")
                continue
            
            # Extract league info from club URL if possible, or leave empty
            league = ''
            league_country = ''
            
            # Process each manager
            for manager in managers:
                print(f"  -> Processing {manager.get('role', 'Manager')}: {manager['name']}")
                
                # Get manager profile info (date of birth, preferred formation)
                profile_info = scraper_instance.scrape_manager_profile_info(manager.get('profile_url', ''))
                
                # Get career history
                career_history = scraper_instance.scrape_coach_history(manager['name'], manager['id'])
                
                # Add to results
                for entry in career_history:
                    results.append({
                        'league': league,
                        'league_country': league_country,
                        'current_club': club_name,
                        'current_club_url': club_url,
                        'manager': manager['name'],
                        'manager_id': manager['id'],
                        'manager_role': manager.get('role', 'Manager'),
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
        
        print(f"Scraper finished with {len(results)} results for {len(clubs)} clubs")
        scraper_state['results'] = results
        scraper_state['progress']['current'] = len(clubs)
        scraper_state['progress']['status'] = 'completed'
        
    except Exception as e:
        import traceback
        print(f"Error in multiple clubs scraper: {str(e)}")
        print(traceback.format_exc())
        scraper_state['progress']['status'] = f'error: {safe_str(e)}'
    finally:
        scraper_state['running'] = False
        print("Multiple clubs scraper finished")

def run_manager_scraper(manager_id):
    """Run scraper for a specific manager by ID"""
    global scraper_state, scraper_instance
    
    try:
        print(f"Starting scraper for manager ID: {manager_id}")
        scraper_state['progress']['status'] = f'Scraping manager ID: {manager_id}...'
        scraper_state['progress']['current'] = 0
        scraper_state['progress']['total'] = 1
        
        results = scraper_instance.scrape_manager_by_id(manager_id)
        
        print(f"Scraper finished with {len(results)} results for manager ID: {manager_id}")
        scraper_state['results'] = results
        scraper_state['progress']['current'] = 1
        scraper_state['progress']['status'] = 'completed'
        
    except Exception as e:
        import traceback
        print(f"Error in manager scraper: {str(e)}")
        print(traceback.format_exc())
        scraper_state['progress']['status'] = f'error: {safe_str(e)}'
    finally:
        scraper_state['running'] = False
        print("Manager scraper finished")

@app.route('/api/start-league-by-id', methods=['POST'])
def start_league_by_id_scraper():
    """Start scraper for a specific league by ID (for coaches)"""
    global scraper_instance, scraper_thread, scraper_state
    
    if scraper_state['running']:
        return jsonify({'error': 'Scraper is already running'}), 400
    
    try:
        data = request.json
        league_id = data.get('league_id')
        
        if not league_id:
            return jsonify({'error': 'league_id is required'}), 400
        
        # Validate that league_id is alphanumeric
        if not re.match(r'^[A-Z0-9]+$', str(league_id)):
            return jsonify({'error': 'league_id must be alphanumeric (e.g., GB1, ES1)'}), 400
        
        scraper_state['running'] = True
        scraper_state['progress']['status'] = 'starting'
        scraper_state['results'] = []
        
        scraper_instance = TransfermarktScraper(callback=update_progress)
        
        scraper_thread = threading.Thread(target=run_league_by_id_scraper, args=(league_id,))
        scraper_thread.daemon = True
        scraper_thread.start()
        
        return jsonify({'message': f'Scraper started for league ID: {league_id}'})
    except Exception as e:
        import traceback
        print(f"Error in start_league_by_id_scraper: {e}")
        print(traceback.format_exc())
        scraper_state['running'] = False
        return jsonify({'error': str(e)}), 500

# Player scraper endpoints
@app.route('/api/player-status', methods=['GET'])
def get_player_status():
    """Get current player scraper status and progress"""
    try:
        return jsonify(player_scraper_state)
    except Exception as e:
        import traceback
        print(f"Error in get_player_status: {e}")
        print(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/api/player-start', methods=['POST'])
def start_player_scraper():
    """Start the player scraper"""
    global player_scraper_instance, player_scraper_thread, player_scraper_state
    
    if player_scraper_state['running']:
        return jsonify({'error': 'Player scraper is already running'}), 400
    
    try:
        data = request.json or {}
        league_url = data.get('league_url')
        league_name = data.get('league_name')
        league_urls = data.get('league_urls')
        continent = data.get('continent')
        
        player_scraper_state['running'] = True
        player_scraper_state['progress']['status'] = 'starting'
        player_scraper_state['results'] = []
        
        player_scraper_instance = TransfermarktScraper(callback=update_player_progress)
        
        if league_urls and len(league_urls) > 0:
            player_scraper_thread = threading.Thread(target=run_multiple_leagues_player_scraper, args=(league_urls,))
        elif league_url:
            player_scraper_thread = threading.Thread(target=run_league_player_scraper, args=(league_url, league_name))
        elif continent:
            player_scraper_thread = threading.Thread(target=run_continent_player_scraper, args=(continent,))
        else:
            player_scraper_thread = threading.Thread(target=run_player_scraper)
        
        player_scraper_thread.daemon = True
        player_scraper_thread.start()
        
        return jsonify({'message': 'Player scraper started'})
    except Exception as e:
        import traceback
        print(f"Error in start_player_scraper: {e}")
        print(traceback.format_exc())
        player_scraper_state['running'] = False
        return jsonify({'error': str(e)}), 500

@app.route('/api/player-stop', methods=['POST'])
def stop_player_scraper():
    """Stop the player scraper"""
    global player_scraper_state, player_scraper_instance
    
    if not player_scraper_state['running']:
        return jsonify({'error': 'Player scraper is not running'}), 400
    
    player_scraper_state['running'] = False
    player_scraper_state['progress']['status'] = 'stopping'
    
    if player_scraper_instance:
        player_scraper_instance.should_stop = True
    
    return jsonify({'message': 'Player scraper stop requested'})

@app.route('/api/player-results', methods=['GET'])
def get_player_results():
    """Get player scraper results"""
    return jsonify(player_scraper_state['results'])

@app.route('/api/player-reset', methods=['POST'])
def reset_player_scraper():
    """Reset player scraper state"""
    global player_scraper_state
    
    if player_scraper_state['running']:
        return jsonify({'error': 'Cannot reset while player scraper is running'}), 400
    
    player_scraper_state = {
        'running': False,
        'progress': {
            'current': 0,
            'total': 0,
            'current_club': '',
            'status': 'idle'
        },
        'results': []
    }
    
    return jsonify({'message': 'Player scraper reset'})

@app.route('/api/player-start-club', methods=['POST'])
def start_player_club_scraper():
    """Start player scraper for a specific club"""
    global player_scraper_instance, player_scraper_thread, player_scraper_state
    
    if player_scraper_state['running']:
        return jsonify({'error': 'Player scraper is already running'}), 400
    
    try:
        data = request.json
        club_url = data.get('club_url')
        club_name = data.get('club_name', 'Unknown Club')
        
        if not club_url:
            return jsonify({'error': 'club_url is required'}), 400
        
        # Extract club name from URL if not provided or is placeholder
        if not club_name or club_name == 'Unknown Club' or club_name == 'Club from URL':
            try:
                soup = TransfermarktScraper()._get_page(club_url)
                if soup:
                    name_elem = soup.find('h1')
                    if name_elem:
                        club_name = name_elem.get_text().strip()
            except:
                pass  # Keep default name if extraction fails
        
        player_scraper_state['running'] = True
        player_scraper_state['progress']['status'] = 'starting'
        player_scraper_state['results'] = []
        
        player_scraper_instance = TransfermarktScraper(callback=update_player_progress)
        
        player_scraper_thread = threading.Thread(target=run_single_club_player_scraper, args=(club_url, club_name))
        player_scraper_thread.daemon = True
        player_scraper_thread.start()
        
        return jsonify({'message': f'Player scraper started for {club_name}'})
    except Exception as e:
        import traceback
        print(f"Error in start_player_club_scraper: {e}")
        print(traceback.format_exc())
        player_scraper_state['running'] = False
        return jsonify({'error': str(e)}), 500

@app.route('/api/player-start-clubs', methods=['POST'])
def start_player_clubs_scraper():
    """Start player scraper for multiple clubs"""
    global player_scraper_instance, player_scraper_thread, player_scraper_state
    
    if player_scraper_state['running']:
        return jsonify({'error': 'Player scraper is already running'}), 400
    
    try:
        data = request.json
        clubs = data.get('clubs', [])
        
        if not clubs or len(clubs) == 0:
            return jsonify({'error': 'clubs array is required'}), 400
        
        player_scraper_state['running'] = True
        player_scraper_state['progress']['status'] = 'starting'
        player_scraper_state['results'] = []
        
        player_scraper_instance = TransfermarktScraper(callback=update_player_progress)
        
        player_scraper_thread = threading.Thread(target=run_multiple_clubs_player_scraper, args=(clubs,))
        player_scraper_thread.daemon = True
        player_scraper_thread.start()
        
        return jsonify({'message': f'Player scraper started for {len(clubs)} club(s)'})
    except Exception as e:
        import traceback
        print(f"Error in start_player_clubs_scraper: {e}")
        print(traceback.format_exc())
        player_scraper_state['running'] = False
        return jsonify({'error': str(e)}), 500

@app.route('/api/player-start-league-by-id', methods=['POST'])
def start_player_league_by_id_scraper():
    """Start player scraper for a specific league by ID"""
    global player_scraper_instance, player_scraper_thread, player_scraper_state
    
    if player_scraper_state['running']:
        return jsonify({'error': 'Player scraper is already running'}), 400
    
    try:
        data = request.json
        league_id = data.get('league_id')
        
        if not league_id:
            return jsonify({'error': 'league_id is required'}), 400
        
        # Validate that league_id is alphanumeric
        if not re.match(r'^[A-Z0-9]+$', str(league_id)):
            return jsonify({'error': 'league_id must be alphanumeric (e.g., GB1, ES1)'}), 400
        
        player_scraper_state['running'] = True
        player_scraper_state['progress']['status'] = 'starting'
        player_scraper_state['results'] = []
        
        player_scraper_instance = TransfermarktScraper(callback=update_player_progress)
        
        player_scraper_thread = threading.Thread(target=run_league_by_id_player_scraper, args=(league_id,))
        player_scraper_thread.daemon = True
        player_scraper_thread.start()
        
        return jsonify({'message': f'Player scraper started for league ID: {league_id}'})
    except Exception as e:
        import traceback
        print(f"Error in start_player_league_by_id_scraper: {e}")
        print(traceback.format_exc())
        player_scraper_state['running'] = False
        return jsonify({'error': str(e)}), 500

@app.route('/api/player-start-club-by-id', methods=['POST'])
def start_player_club_by_id_scraper():
    """Start player scraper for a specific club by ID"""
    global player_scraper_instance, player_scraper_thread, player_scraper_state
    
    if player_scraper_state['running']:
        return jsonify({'error': 'Player scraper is already running'}), 400
    
    try:
        data = request.json
        club_id = data.get('club_id')
        
        if not club_id:
            return jsonify({'error': 'club_id is required'}), 400
        
        # Validate that club_id is a number
        try:
            club_id = str(int(club_id))  # Convert to string and validate it's a number
        except (ValueError, TypeError):
            return jsonify({'error': 'club_id must be a valid number'}), 400
        
        player_scraper_state['running'] = True
        player_scraper_state['progress']['status'] = 'starting'
        player_scraper_state['results'] = []
        
        player_scraper_instance = TransfermarktScraper(callback=update_player_progress)
        
        player_scraper_thread = threading.Thread(target=run_club_by_id_player_scraper, args=(club_id,))
        player_scraper_thread.daemon = True
        player_scraper_thread.start()
        
        return jsonify({'message': f'Player scraper started for club ID: {club_id}'})
    except Exception as e:
        import traceback
        print(f"Error in start_player_club_by_id_scraper: {e}")
        print(traceback.format_exc())
        player_scraper_state['running'] = False
        return jsonify({'error': str(e)}), 500

def update_player_progress(current, total, current_club, status):
    """Callback to update player scraper progress"""
    player_scraper_state['progress'] = {
        'current': current,
        'total': total,
        'current_club': current_club,
        'status': status
    }

def run_player_scraper():
    """Run the player scraper in a separate thread"""
    global player_scraper_state, player_scraper_instance
    
    try:
        print("Starting player scraper...")
        results = player_scraper_instance.scrape_all_players()
        print(f"Player scraper finished with {len(results)} results")
        player_scraper_state['results'] = results
        if player_scraper_instance.should_stop:
            player_scraper_state['progress']['status'] = 'stopped'
        else:
            player_scraper_state['progress']['status'] = 'completed'
    except Exception as e:
        import traceback
        print(f"Error in player scraper: {str(e)}")
        print(traceback.format_exc())
        player_scraper_state['progress']['status'] = f'error: {safe_str(e)}'
    finally:
        player_scraper_state['running'] = False
        print("Player scraper finished")

def run_league_player_scraper(league_url, league_name=None):
    """Run player scraper for all clubs from a specific league"""
    global player_scraper_state, player_scraper_instance
    
    try:
        print(f"Starting player scraper for league: {league_url}")
        player_scraper_state['progress']['status'] = 'Fetching clubs from league...'
        
        clubs = player_scraper_instance.scrape_clubs_from_league(league_url)
        
        if not clubs:
            print("No clubs found in league")
            player_scraper_state['results'] = []
            player_scraper_state['progress']['status'] = 'No clubs found'
            player_scraper_state['running'] = False
            return
        
        if not league_name:
            import re
            league_match = re.search(r'/([^/]+)/startseite/wettbewerb/', league_url)
            league_name = league_match.group(1).replace('-', ' ').title() if league_match else 'Unknown League'
        
        total = len(clubs)
        results = []
        
        for idx, club in enumerate(clubs):
            if player_scraper_instance.should_stop:
                player_scraper_state['progress']['status'] = 'stopped'
                break
            
            player_scraper_state['progress']['current'] = idx + 1
            player_scraper_state['progress']['total'] = total
            player_scraper_state['progress']['current_club'] = safe_str(club['name'])
            player_scraper_state['progress']['status'] = f'Processing {club["name"]}...'
            
            print(f"Processing club {idx + 1}/{total}: {club['name']}")
            
            players = player_scraper_instance.get_current_players(club['url'])
            
            if not players:
                print(f"  -> No players found for {club['name']}")
                continue
            
            for player in players:
                profile_info = player_scraper_instance.scrape_player_profile_info(player.get('profile_url', ''))
                
                results.append({
                    'league': league_name,
                    'league_country': '',
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
        
        print(f"Player scraper finished with {len(results)} results")
        player_scraper_state['results'] = results
        player_scraper_state['progress']['current'] = total
        player_scraper_state['progress']['status'] = 'completed'
        
    except Exception as e:
        import traceback
        print(f"Error in league player scraper: {str(e)}")
        print(traceback.format_exc())
        player_scraper_state['progress']['status'] = f'error: {safe_str(e)}'
    finally:
        player_scraper_state['running'] = False
        print("League player scraper finished")

def run_multiple_leagues_player_scraper(league_urls):
    """Run player scraper for multiple leagues"""
    global player_scraper_state, player_scraper_instance
    
    try:
        print(f"Starting player scraper for {len(league_urls)} leagues")
        player_scraper_state['progress']['status'] = 'Fetching clubs from leagues...'
        
        all_clubs = []
        for league_info in league_urls:
            league_url = league_info.get('url')
            league_name = league_info.get('name', 'Unknown League')
            
            print(f"Fetching clubs from {league_name}...")
            clubs = player_scraper_instance.scrape_clubs_from_league(league_url)
            for club in clubs:
                club['league'] = league_name
                club['league_country'] = ''
            all_clubs.extend(clubs)
        
        if not all_clubs:
            print("No clubs found in selected leagues")
            player_scraper_state['results'] = []
            player_scraper_state['progress']['status'] = 'No clubs found'
            player_scraper_state['running'] = False
            return
        
        total = len(all_clubs)
        results = []
        
        for idx, club in enumerate(all_clubs):
            if player_scraper_instance.should_stop:
                player_scraper_state['progress']['status'] = 'stopped'
                break
            
            player_scraper_state['progress']['current'] = idx + 1
            player_scraper_state['progress']['total'] = total
            player_scraper_state['progress']['current_club'] = safe_str(club['name'])
            player_scraper_state['progress']['status'] = f'Processing {club["name"]}...'
            
            print(f"Processing club {idx + 1}/{total}: {club['name']} ({club.get('league', 'Unknown League')})")
            
            players = player_scraper_instance.get_current_players(club['url'])
            
            if not players:
                print(f"  -> No players found for {club['name']}")
                continue
            
            for player in players:
                profile_info = player_scraper_instance.scrape_player_profile_info(player.get('profile_url', ''))
                
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
        
        print(f"Player scraper finished with {len(results)} results")
        player_scraper_state['results'] = results
        player_scraper_state['progress']['current'] = total
        player_scraper_state['progress']['status'] = 'completed'
        
    except Exception as e:
        import traceback
        print(f"Error in multiple leagues player scraper: {str(e)}")
        print(traceback.format_exc())
        player_scraper_state['progress']['status'] = f'error: {safe_str(e)}'
    finally:
        player_scraper_state['running'] = False
        print("Multiple leagues player scraper finished")

def run_continent_player_scraper(continent):
    """Run player scraper for all leagues from a continent"""
    global player_scraper_state, player_scraper_instance
    
    try:
        print(f"Starting player scraper for continent: {continent}")
        player_scraper_state['progress']['status'] = f'Fetching leagues from {continent}...'
        
        leagues = player_scraper_instance.scrape_leagues_from_continent(continent)
        
        if not leagues:
            print("No leagues found in continent")
            player_scraper_state['results'] = []
            player_scraper_state['progress']['status'] = 'No leagues found'
            player_scraper_state['running'] = False
            return
        
        all_clubs = []
        for league in leagues:
            print(f"Fetching clubs from {league['name']}...")
            clubs = player_scraper_instance.scrape_clubs_from_league(league['url'])
            for club in clubs:
                club['league'] = league['name']
                club['league_country'] = league.get('country', '')
            all_clubs.extend(clubs)
        
        if not all_clubs:
            print("No clubs found")
            player_scraper_state['results'] = []
            player_scraper_state['progress']['status'] = 'No clubs found'
            player_scraper_state['running'] = False
            return
        
        total = len(all_clubs)
        results = []
        
        for idx, club in enumerate(all_clubs):
            if player_scraper_instance.should_stop:
                player_scraper_state['progress']['status'] = 'stopped'
                break
            
            player_scraper_state['progress']['current'] = idx + 1
            player_scraper_state['progress']['total'] = total
            player_scraper_state['progress']['current_club'] = safe_str(club['name'])
            player_scraper_state['progress']['status'] = f'Processing {club["name"]}...'
            
            print(f"Processing club {idx + 1}/{total}: {club['name']} ({club.get('league', 'Unknown League')})")
            
            players = player_scraper_instance.get_current_players(club['url'])
            
            if not players:
                print(f"  -> No players found for {club['name']}")
                continue
            
            for player in players:
                profile_info = player_scraper_instance.scrape_player_profile_info(player.get('profile_url', ''))
                
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
        
        print(f"Player scraper finished with {len(results)} results")
        player_scraper_state['results'] = results
        player_scraper_state['progress']['current'] = total
        player_scraper_state['progress']['status'] = 'completed'
        
    except Exception as e:
        import traceback
        print(f"Error in continent player scraper: {str(e)}")
        print(traceback.format_exc())
        player_scraper_state['progress']['status'] = f'error: {safe_str(e)}'
    finally:
        player_scraper_state['running'] = False
        print("Continent player scraper finished")

def run_single_club_player_scraper(club_url, club_name):
    """Run player scraper for a single club"""
    global player_scraper_state, player_scraper_instance
    
    try:
        print(f"Starting player scraper for single club: {club_name}")
        print(f"  -> Club URL: {club_url}")
        player_scraper_state['progress']['total'] = 1
        player_scraper_state['progress']['current'] = 0
        player_scraper_state['progress']['current_club'] = safe_str(club_name)
        player_scraper_state['progress']['status'] = f'Processing {club_name}...'
        
        players = player_scraper_instance.get_current_players(club_url)
        print(f"  -> get_current_players returned {len(players)} players")
        
        if not players:
            print(f"No players found for {club_name} (URL: {club_url})")
            player_scraper_state['results'] = []
            player_scraper_state['progress']['status'] = f'No players found for {club_name}'
            player_scraper_state['running'] = False
            return
        
        results = []
        league = ''
        league_country = ''
        
        for player in players:
            print(f"  -> Processing player: {player['name']}")
            
            profile_info = player_scraper_instance.scrape_player_profile_info(player.get('profile_url', ''))
            
            results.append({
                'league': league,
                'league_country': league_country,
                'current_club': club_name,
                'current_club_url': club_url,
                'player_name': profile_info.get('player_name', player['name']),
                'player_id': player['id'],
                'jersey_number': profile_info.get('jersey_number', ''),
                'nationality': profile_info.get('nationality', ''),
                'date_of_birth': profile_info.get('date_of_birth', ''),
                'caps': profile_info.get('caps', ''),
                'goals': profile_info.get('goals', ''),
                'position': profile_info.get('position', player.get('position', '')),
                'height': profile_info.get('height', ''),
                'foot': profile_info.get('foot', ''),
                'current_market_value': profile_info.get('current_market_value', '')
            })
        
        print(f"Player scraper finished with {len(results)} results for {club_name}")
        player_scraper_state['results'] = results
        player_scraper_state['progress']['current'] = 1
        player_scraper_state['progress']['status'] = 'completed'
        
    except Exception as e:
        import traceback
        error_msg = safe_str(str(e))
        print(f"Error in single club player scraper: {error_msg}")
        traceback_str = safe_str(traceback.format_exc())
        print(traceback_str)
        player_scraper_state['progress']['status'] = f'error: {error_msg}'
    finally:
        player_scraper_state['running'] = False
        print("Single club player scraper finished")

def run_multiple_clubs_player_scraper(clubs):
    """Run player scraper for multiple clubs"""
    global player_scraper_state, player_scraper_instance
    
    try:
        print(f"Starting player scraper for {len(clubs)} clubs")
        player_scraper_state['progress']['total'] = len(clubs)
        player_scraper_state['progress']['current'] = 0
        player_scraper_state['progress']['status'] = 'Processing clubs...'
        
        results = []
        
        for idx, club_info in enumerate(clubs):
            if player_scraper_instance.should_stop:
                player_scraper_state['progress']['status'] = 'stopped'
                break
            
            club_url = club_info.get('url')
            club_name = club_info.get('name', 'Unknown Club')
            
            player_scraper_state['progress']['current'] = idx + 1
            player_scraper_state['progress']['current_club'] = safe_str(club_name)
            player_scraper_state['progress']['status'] = f'Processing {club_name}...'
            
            print(f"Processing club {idx + 1}/{len(clubs)}: {club_name}")
            
            players = player_scraper_instance.get_current_players(club_url)
            
            if not players:
                print(f"  -> No players found for {club_name}")
                continue
            
            league = ''
            league_country = ''
            
            for player in players:
                print(f"  -> Processing player: {player['name']}")
                
                profile_info = player_scraper_instance.scrape_player_profile_info(player.get('profile_url', ''))
                
                results.append({
                    'league': league,
                    'league_country': league_country,
                    'current_club': club_name,
                    'current_club_url': club_url,
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
        
        print(f"Player scraper finished with {len(results)} results for {len(clubs)} clubs")
        player_scraper_state['results'] = results
        player_scraper_state['progress']['current'] = len(clubs)
        player_scraper_state['progress']['status'] = 'completed'
        
    except Exception as e:
        import traceback
        print(f"Error in multiple clubs player scraper: {str(e)}")
        print(traceback.format_exc())
        player_scraper_state['progress']['status'] = f'error: {safe_str(e)}'
    finally:
        player_scraper_state['running'] = False
        print("Multiple clubs player scraper finished")

def run_league_by_id_scraper(league_id):
    """Run scraper for a specific league by ID (for coaches)"""
    global scraper_state, scraper_instance
    
    try:
        print(f"Starting scraper for league ID: {league_id}")
        scraper_state['progress']['status'] = f'Fetching league URL for ID: {league_id}...'
        
        # Get league URL from ID
        league_url = scraper_instance.get_league_url_by_id(league_id)
        
        if not league_url:
            print(f"Could not find league URL for ID: {league_id}")
            scraper_state['results'] = []
            scraper_state['progress']['status'] = f'League ID {league_id} not found'
            scraper_state['running'] = False
            return
        
        # Extract league name from URL or use ID
        league_name = None
        soup = scraper_instance._get_page(league_url)
        if soup:
            # Try to extract league name
            name_elem = soup.find('h1')
            if name_elem:
                league_name = name_elem.get_text().strip()
        
        if not league_name:
            league_name = f'League {league_id}'
        
        # Use existing league scraper function
        run_league_scraper(league_url, league_name)
        
    except Exception as e:
        import traceback
        print(f"Error in league by ID scraper: {str(e)}")
        print(traceback.format_exc())
        scraper_state['progress']['status'] = f'error: {safe_str(e)}'
        scraper_state['running'] = False
        print("League by ID scraper finished")

def run_league_by_id_player_scraper(league_id):
    """Run player scraper for a specific league by ID"""
    global player_scraper_state, player_scraper_instance
    
    try:
        print(f"Starting player scraper for league ID: {league_id}")
        player_scraper_state['progress']['status'] = f'Fetching league URL for ID: {league_id}...'
        
        # Get league URL from ID
        league_url = player_scraper_instance.get_league_url_by_id(league_id)
        
        if not league_url:
            print(f"Could not find league URL for ID: {league_id}")
            player_scraper_state['results'] = []
            player_scraper_state['progress']['status'] = f'League ID {league_id} not found'
            player_scraper_state['running'] = False
            return
        
        # Extract league name from URL or use ID
        league_name = None
        soup = player_scraper_instance._get_page(league_url)
        if soup:
            # Try to extract league name
            name_elem = soup.find('h1')
            if name_elem:
                league_name = name_elem.get_text().strip()
        
        if not league_name:
            league_name = f'League {league_id}'
        
        # Use existing league player scraper function
        run_league_player_scraper(league_url, league_name)
        
    except Exception as e:
        import traceback
        print(f"Error in league by ID player scraper: {str(e)}")
        print(traceback.format_exc())
        player_scraper_state['progress']['status'] = f'error: {safe_str(e)}'
        player_scraper_state['running'] = False
        print("League by ID player scraper finished")

def run_club_by_id_player_scraper(club_id):
    """Run player scraper for a specific club by ID"""
    global player_scraper_state, player_scraper_instance
    
    try:
        print(f"Starting player scraper for club ID: {club_id}")
        player_scraper_state['progress']['status'] = f'Fetching club URL for ID: {club_id}...'
        
        # Get club URL from ID
        club_url = player_scraper_instance.get_club_url_by_id(club_id)
        
        if not club_url:
            print(f"Could not find club URL for ID: {club_id}")
            player_scraper_state['results'] = []
            player_scraper_state['progress']['status'] = f'Club ID {club_id} not found'
            player_scraper_state['running'] = False
            return
        
        # Extract club name from URL or use ID
        club_name = None
        soup = player_scraper_instance._get_page(club_url)
        if soup:
            # Try to extract club name
            name_elem = soup.find('h1')
            if name_elem:
                club_name = name_elem.get_text().strip()
        
        if not club_name:
            club_name = f'Club {club_id}'
        
        # Use existing single club player scraper function
        run_single_club_player_scraper(club_url, club_name)
        
    except Exception as e:
        import traceback
        print(f"Error in club by ID player scraper: {str(e)}")
        print(traceback.format_exc())
        player_scraper_state['progress']['status'] = f'error: {safe_str(e)}'
        player_scraper_state['running'] = False
        print("Club by ID player scraper finished")

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)

