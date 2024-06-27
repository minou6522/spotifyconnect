import requests

def get_recommendations(token, seed_artists=None, seed_tracks=None, seed_genres=None, limit=10):
    """
    Fetches music recommendations from Spotify based on seed artists, tracks, or genres.
    
    Args:
        token (str): Spotify API access token.
        seed_artists (list, optional): List of Spotify artist IDs to base recommendations on. Defaults to None.
        seed_tracks (list, optional): List of Spotify track IDs to base recommendations on. Defaults to None.
        seed_genres (list, optional): List of Spotify genre names to base recommendations on. Defaults to None.
        limit (int, optional): Number of recommendations to return. Defaults to 10.
    
    Returns:
        dict: Dictionary containing recommendations from Spotify API or an error message.
    """
    if not token:
        return {'error': 'Access token is required'}

    headers = {
        'Authorization': f"Bearer {token}"
    }

    params = {
        'seed_artists': ','.join(seed_artists) if seed_artists else '',
        'seed_tracks': ','.join(seed_tracks) if seed_tracks else '',
        'seed_genres': ','.join(seed_genres) if seed_genres else '',
        'limit': limit
    }

    # Remove empty parameters
    params = {k: v for k, v in params.items() if v}

    try:
        response = requests.get(
            'https://api.spotify.com/v1/recommendations',
            headers=headers,
            params=params
        )
        response.raise_for_status()  # Raises an HTTPError if the response was unsuccessful
    except requests.exceptions.RequestException as e:
        return {'error': f"Request failed: {e}"}

    try:
        recommendations = response.json()
    except ValueError:
        return {'error': 'Failed to parse response as JSON'}

    if 'tracks' not in recommendations:
        return {'error': 'No recommendations found'}

    return recommendations
