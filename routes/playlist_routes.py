from flask import Blueprint, request, jsonify, session, redirect, url_for, render_template
import requests

playlist_routes = Blueprint('playlist_routes', __name__)

@playlist_routes.route('/<playlist_id>')
def view_playlist(playlist_id):
    token_info = session.get('token_info')
    if not token_info:
        return redirect(url_for('index'))

    headers = {
        'Authorization': f"Bearer {token_info['access_token']}"
    }

    response = requests.get(f'https://api.spotify.com/v1/playlists/{playlist_id}', headers=headers)
    playlist = response.json()

    return render_template('view_playlist.html', playlist=playlist)

@playlist_routes.route('/create', methods=['GET', 'POST'])
def create_playlist():
    current_user = session.get('user_id')
    token_info = session.get('token_info')
    if not current_user or not token_info:
        return redirect(url_for('index'))

    if request.method == 'POST':
        playlist_name = request.form['name']
        headers = {
            'Authorization': f"Bearer {token_info['access_token']}",
            'Content-Type': 'application/json'
        }
        payload = json.dumps({
            'name': playlist_name,
            'description': 'New playlist created through app',
            'public': False
        })
        response = requests.post(
            f'https://api.spotify.com/v1/users/{current_user}/playlists',
            headers=headers,
            data=payload
        )
        if response.status_code == 201:
            return redirect(url_for('playlist_routes.view_playlist', playlist_id=response.json()['id']))
        else:
            return response.text, response.status_code

    return render_template('create_playlist.html')

@playlist_routes.route('/<playlist_id>/add', methods=['GET', 'POST'])
def add_to_playlist(playlist_id):
    token_info = session.get('token_info')
    if not token_info:
        return redirect(url_for('index'))

    if request.method == 'POST':
        track_uri = request.form['track_uri']
        headers = {
            'Authorization': f"Bearer {token_info['access_token']}",
            'Content-Type': 'application/json'
        }
        payload = json.dumps({
            'uris': [track_uri]
        })
        response = requests.post(
            f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks',
            headers=headers,
            data=payload
        )
        if response.status_code == 201:
            return redirect(url_for('playlist_routes.view_playlist', playlist_id=playlist_id))
        else:
            return response.text, response.status_code

    return render_template('add_to_playlist.html', playlist_id=playlist_id)

@playlist_routes.route('/<playlist_id>/remove', methods=['POST'])
def remove_from_playlist(playlist_id):
    token_info = session.get('token_info')
    if not token_info:
        return redirect(url_for('index'))

    track_uri = request.form['track_uri']
    headers = {
        'Authorization': f"Bearer {token_info['access_token']}",
        'Content-Type': 'application/json'
    }
    payload = json.dumps({
        'tracks': [{'uri': track_uri}]
    })
    response = requests.delete(
        f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks',
        headers=headers,
        data=payload
    )
    if response.status_code == 200:
        return redirect(url_for('playlist_routes.view_playlist', playlist_id=playlist_id))
    else:
        return response.text, response.status_code
