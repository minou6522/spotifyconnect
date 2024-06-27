from flask import Blueprint, request, jsonify, session, redirect, url_for, render_template
import requests

recommendation_routes = Blueprint('recommendation_routes', __name__)

@recommendation_routes.route('/')
def recommend():
    token_info = session.get('token_info')
    if not token_info:
        return redirect(url_for('index'))

    headers = {
        'Authorization': f"Bearer {token_info['access_token']}"
    }

    seed_artists = request.args.getlist('seed_artists')
    seed_tracks = request.args.getlist('seed_tracks')
    seed_genres = request.args.getlist('seed_genres')

    params = {
        'seed_artists': ','.join(seed_artists),
        'seed_tracks': ','.join(seed_tracks),
        'seed_genres': ','.join(seed_genres),
        'limit': 10
    }

    response = requests.get('https://api.spotify.com/v1/recommendations', headers=headers, params=params)
    recommendations = response.json()

    return render_template('recommendations.html', recommendations=recommendations)

@recommendation_routes.route('/based_on_top')
def recommend_based_on_top():
    current_user = session.get('user_id')
    token_info = session.get('token_info')
    if not current_user or not token_info:
        return redirect(url_for('index'))

    headers = {
        'Authorization': f"Bearer {token_info['access_token']}"
    }

    top_artists_response = requests.get('https://api.spotify.com/v1/me/top/artists', headers=headers)
    top_tracks_response = requests.get('https://api.spotify.com/v1/me/top/tracks', headers=headers)

    top_artists = top_artists_response.json().get('items', [])
    top_tracks = top_tracks_response.json().get('items', [])

    seed_artists = [artist['id'] for artist in top_artists[:5]]
    seed_tracks = [track['id'] for track in top_tracks[:5]]
    seed_genres = list(set(genre for artist in top_artists for genre in artist.get('genres', [])))[:5]

    params = {
        'seed_artists': ','.join(seed_artists),
        'seed_tracks': ','.join(seed_tracks),
        'seed_genres': ','.join(seed_genres),
        'limit': 10
    }

    response = requests.get('https://api.spotify.com/v1/recommendations', headers=headers, params=params)
    recommendations = response.json()

    return render_template('recommendations.html', recommendations=recommendations)
