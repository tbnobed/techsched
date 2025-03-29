from datetime import datetime, timedelta

from flask import Blueprint, render_template, request, jsonify, current_app
from flask_login import login_required

import trafilatura
import logging

mlb = Blueprint('mlb', __name__, url_prefix='/mlb')

def get_team_logo(team_name):
    """Convert team name to logo URL."""
    # Dictionary of MLB team names to their logo URLs
    # This would ideally be expanded with actual logo URLs
    logos = {
        "Arizona Diamondbacks": "https://www.mlbstatic.com/team-logos/team-cap-on-light/109.svg",
        "Atlanta Braves": "https://www.mlbstatic.com/team-logos/team-cap-on-light/144.svg",
        "Baltimore Orioles": "https://www.mlbstatic.com/team-logos/team-cap-on-light/110.svg",
        "Boston Red Sox": "https://www.mlbstatic.com/team-logos/team-cap-on-light/111.svg",
        "Chicago Cubs": "https://www.mlbstatic.com/team-logos/team-cap-on-light/112.svg",
        "Chicago White Sox": "https://www.mlbstatic.com/team-logos/team-cap-on-light/145.svg",
        "Cincinnati Reds": "https://www.mlbstatic.com/team-logos/team-cap-on-light/113.svg",
        "Cleveland Guardians": "https://www.mlbstatic.com/team-logos/team-cap-on-light/114.svg",
        "Colorado Rockies": "https://www.mlbstatic.com/team-logos/team-cap-on-light/115.svg",
        "Detroit Tigers": "https://www.mlbstatic.com/team-logos/team-cap-on-light/116.svg",
        "Houston Astros": "https://www.mlbstatic.com/team-logos/team-cap-on-light/117.svg",
        "Kansas City Royals": "https://www.mlbstatic.com/team-logos/team-cap-on-light/118.svg",
        "Los Angeles Angels": "https://www.mlbstatic.com/team-logos/team-cap-on-light/108.svg",
        "Los Angeles Dodgers": "https://www.mlbstatic.com/team-logos/team-cap-on-light/119.svg",
        "Miami Marlins": "https://www.mlbstatic.com/team-logos/team-cap-on-light/146.svg",
        "Milwaukee Brewers": "https://www.mlbstatic.com/team-logos/team-cap-on-light/158.svg",
        "Minnesota Twins": "https://www.mlbstatic.com/team-logos/team-cap-on-light/142.svg",
        "New York Mets": "https://www.mlbstatic.com/team-logos/team-cap-on-light/121.svg",
        "New York Yankees": "https://www.mlbstatic.com/team-logos/team-cap-on-light/147.svg",
        "Oakland Athletics": "https://www.mlbstatic.com/team-logos/team-cap-on-light/133.svg",
        "Philadelphia Phillies": "https://www.mlbstatic.com/team-logos/team-cap-on-light/143.svg",
        "Pittsburgh Pirates": "https://www.mlbstatic.com/team-logos/team-cap-on-light/134.svg",
        "San Diego Padres": "https://www.mlbstatic.com/team-logos/team-cap-on-light/135.svg",
        "San Francisco Giants": "https://www.mlbstatic.com/team-logos/team-cap-on-light/137.svg",
        "Seattle Mariners": "https://www.mlbstatic.com/team-logos/team-cap-on-light/136.svg",
        "St. Louis Cardinals": "https://www.mlbstatic.com/team-logos/team-cap-on-light/138.svg",
        "Tampa Bay Rays": "https://www.mlbstatic.com/team-logos/team-cap-on-light/139.svg",
        "Texas Rangers": "https://www.mlbstatic.com/team-logos/team-cap-on-light/140.svg",
        "Toronto Blue Jays": "https://www.mlbstatic.com/team-logos/team-cap-on-light/141.svg",
        "Washington Nationals": "https://www.mlbstatic.com/team-logos/team-cap-on-light/120.svg"
    }
    
    # Default logo if team not found
    default_logo = "https://www.mlbstatic.com/mlb.com/images/share/mlb-logo-share.jpg"
    
    return logos.get(team_name, default_logo)


def parse_mlb_scores(content):
    """
    Parse MLB scores from the scraped content.
    This is a basic implementation and would need to be adjusted based on the actual structure of the MLB website.
    """
    if not content:
        logging.error("No content to parse")
        return []
    
    # Log the first 200 characters of content for debugging
    logging.debug(f"Content sample: {content[:200]}...")
    
    try:
        # This is a very simple parsing example
        # In a real implementation, this would need to be much more sophisticated
        # using regex, BeautifulSoup, or other parsing techniques to extract game data
        games = []
        
        # Split content by game sections (this is hypothetical and depends on actual HTML structure)
        game_sections = content.split("Final")
        
        for i, section in enumerate(game_sections):
            if i == 0:  # Skip first section which is usually header content
                continue
                
            # Extract team names and scores (very simplified example)
            lines = section.strip().split('\n')
            teams = []
            scores = []
            
            for line in lines[:6]:  # Look at first few lines for team info
                if any(team in line for team in ["Yankees", "Red Sox", "Dodgers", "Cubs", "Cardinals"]):
                    teams.append(line.strip())
                if any(c.isdigit() for c in line):
                    for word in line.split():
                        if word.isdigit():
                            scores.append(int(word))
            
            if len(teams) >= 2 and len(scores) >= 2:
                game = {
                    'away_team': teams[0],
                    'home_team': teams[1],
                    'away_score': scores[0],
                    'home_score': scores[1],
                    'status': 'Final',
                    'away_team_logo': get_team_logo(teams[0]),
                    'home_team_logo': get_team_logo(teams[1]),
                }
                games.append(game)
        
        return games
    except Exception as e:
        logging.error(f"Error parsing MLB scores: {e}")
        return []


def get_mlb_scores(date_str):
    """
    Get MLB scores for a given date.
    Date should be in YYYY-MM-DD format.
    """
    url = f"https://www.mlb.com/scores/{date_str}"
    logging.debug(f"Fetching MLB scores from: {url}")
    
    try:
        # Download the webpage
        downloaded = trafilatura.fetch_url(url)
        
        # Extract main content
        content = trafilatura.extract(downloaded)
        
        if not content:
            logging.error("Failed to extract content from MLB website")
            return []
            
        # Parse the scores
        games = parse_mlb_scores(content)
        
        if not games:
            # If unable to parse games or none found, return sample data for testing
            logging.warning("No games parsed, would return empty list in production")
            return []
            
        return games
    except Exception as e:
        logging.error(f"Error fetching MLB scores: {e}")
        return []


@mlb.route('/scores')
@login_required
def scores():
    """Display MLB scores for a given date."""
    # Get date parameter from request, default to today
    date_str = request.args.get('date')
    
    try:
        if date_str:
            selected_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            selected_date = datetime.now().date()
    except ValueError:
        current_app.logger.error(f"Invalid date format: {date_str}")
        selected_date = datetime.now().date()
    
    # Fetch scores with a small delay to simulate loading
    # In a real app, this would be an async call or a separate API endpoint
    games = get_mlb_scores(selected_date.strftime('%Y-%m-%d'))
    
    return render_template('mlb/scores.html', 
                          selected_date=selected_date,
                          games=games,
                          loading=False,
                          timedelta=timedelta)  # Pass timedelta to the template


@mlb.route('/api/scores/<date_str>')
@login_required
def api_scores(date_str):
    """API endpoint to get MLB scores for a given date."""
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
    
    games = get_mlb_scores(date_str)
    return jsonify({'games': games})