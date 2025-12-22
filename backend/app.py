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
        scraper_state['progress']['status'] = f'error: {str(e)}'
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
            scraper_state['progress']['current_club'] = club['name']
            scraper_state['progress']['status'] = f'Processing {club["name"]}...'
            
            print(f"Processing club {idx + 1}/{total}: {club['name']}")
            
            # Get managers
            managers = scraper_instance.get_current_manager(club['url'], include_caretaker=False)
            
            if not managers:
                print(f"  -> No managers found for {club['name']}")
                continue
            
            # Process each manager
            for manager in managers:
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
        scraper_state['progress']['status'] = f'error: {str(e)}'
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
            scraper_state['progress']['current_club'] = club['name']
            scraper_state['progress']['status'] = f'Processing {club["name"]}...'
            
            print(f"Processing club {idx + 1}/{total}: {club['name']} ({club.get('league', 'Unknown League')})")
            
            # Get managers
            managers = scraper_instance.get_current_manager(club['url'], include_caretaker=False)
            
            if not managers:
                print(f"  -> No managers found for {club['name']}")
                continue
            
            # Process each manager
            for manager in managers:
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
        scraper_state['progress']['status'] = f'error: {str(e)}'
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
            scraper_state['progress']['current_club'] = club['name']
            scraper_state['progress']['status'] = f'Processing {club["name"]}...'
            
            print(f"Processing club {idx + 1}/{total}: {club['name']} ({club.get('league', 'Unknown League')})")
            
            # Get managers
            managers = scraper_instance.get_current_manager(club['url'], include_caretaker=False)
            
            if not managers:
                print(f"  -> No managers found for {club['name']}")
                continue
            
            # Process each manager
            for manager in managers:
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
        scraper_state['progress']['status'] = f'error: {str(e)}'
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
        scraper_state['progress']['current_club'] = club_name
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
        scraper_state['progress']['status'] = f'error: {str(e)}'
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
            scraper_state['progress']['current_club'] = club_name
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
        scraper_state['progress']['status'] = f'error: {str(e)}'
    finally:
        scraper_state['running'] = False
        print("Multiple clubs scraper finished")

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)

