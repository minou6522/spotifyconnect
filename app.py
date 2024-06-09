from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import requests
import tensorflow as tf
import numpy as np
import os
import json

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "default_secret_key")  # Use a default value if the key is not found

# Spotify API credentials
SPOTIPY_CLIENT_ID = os.getenv('SPOTIPY_CLIENT_ID')
SPOTIPY_CLIENT_SECRET = os.getenv('SPOTIPY_CLIENT_SECRET')
SPOTIPY_REDIRECT_URI = os.getenv('SPOTIPY_REDIRECT_URI')

# Spotify Auth URL
SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SCOPE = 'user-top-read'
auth_query_parameters = {
    "response_type": "code",
    "redirect_uri": SPOTIPY_REDIRECT_URI,
    "scope": SCOPE,
    "client_id": SPOTIPY_CLIENT_ID
}

# Load user data from JSON files
def load_user_data():
    users_data = {}
    for filename in os.listdir('data'):
        if filename.endswith('.json'):
            with open(os.path.join('data', filename)) as f:
                data = json.load(f)
                # Check if data is a list, and if so, iterate through it
                if isinstance(data, list):
                    for user in data:
                        users_data[user['username']] = user
                elif isinstance(data, dict):
                    users_data[data['username']] = data
    return users_data

users_data = load_user_data()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login')
def login():
    auth_url = f"{SPOTIFY_AUTH_URL}?response_type=code&client_id={SPOTIPY_CLIENT_ID}&scope={SCOPE}&redirect_uri={SPOTIPY_REDIRECT_URI}"
    return redirect(auth_url)

@app.route('/callback')
def callback():
    auth_token = request.args['code']
    auth_response = requests.post(SPOTIFY_TOKEN_URL, data={
        'grant_type': 'authorization_code',
        'code': auth_token,
        'redirect_uri': SPOTIPY_REDIRECT_URI,
        'client_id': SPOTIPY_CLIENT_ID,
        'client_secret': SPOTIPY_CLIENT_SECRET
    }).json()

    session['token_info'] = auth_response
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    token_info = session.get('token_info')
    if not token_info:
        return redirect(url_for('index'))

    headers = {
        'Authorization': f"Bearer {token_info['access_token']}"
    }

    # Fetch user data from Spotify
    user_profile = requests.get('https://api.spotify.com/v1/me', headers=headers).json()
    username = user_profile['id']

    top_artists = requests.get('https://api.spotify.com/v1/me/top/artists', headers=headers).json()
    top_songs = requests.get('https://api.spotify.com/v1/me/top/tracks', headers=headers).json()
    
    user_data = {
        'username': username,
        'top_artists': [artist['name'] for artist in top_artists['items']],
        'top_songs': [song['name'] for song in top_songs['items']],
        'genres': list(set([genre for artist in top_artists['items'] for genre in artist['genres']]))
    }

    users_data[username] = user_data

    similar_users = find_similar_users(user_data, username)

    return render_template('dashboard.html', user_data=user_data, similar_users=similar_users, enumerate=enumerate)



@app.route('/user/<username>')
def user_stats(username):
    if username not in users_data:
        return "User not found", 404

    user_data = users_data[username]
    return render_template('user_stats.html', user_data=user_data)

# Create a model to calculate similarity scores (placeholder)
def build_model():
    model = tf.keras.Sequential([
        tf.keras.layers.Dense(64, activation='relu', input_shape=(15,)),  # Assuming 5 top artists, 5 top songs, 5 genres
        tf.keras.layers.Dense(64, activation='relu'),
        tf.keras.layers.Dense(1, activation='sigmoid')  # For similarity score
    ])
    
    model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
    return model

# Create mappings for artists, songs, and genres
def create_mappings(users_data):
    all_artists = set()
    all_songs = set()
    all_genres = set()

    for user_data in users_data.values():
        all_artists.update(user_data['top_artists'])
        all_songs.update(user_data['top_songs'])
        all_genres.update(user_data['genres'])

    artist_to_index = {artist: idx for idx, artist in enumerate(all_artists)}
    song_to_index = {song: idx for idx, song in enumerate(all_songs)}
    genre_to_index = {genre: idx for idx, genre in enumerate(all_genres)}

    return artist_to_index, song_to_index, genre_to_index

# Pad the list with pad_value to ensure it has the given length
def pad_list(input_list, length, pad_value=0):
    return input_list[:length] + [pad_value] * (length - len(input_list))

# Create a numerical vector for a user's data
def create_vector(data, artist_to_index, song_to_index, genre_to_index, num_top_artists, num_top_songs, num_genres):
    artist_vector = pad_list([artist_to_index[artist] for artist in data['top_artists']], num_top_artists)
    song_vector = pad_list([song_to_index[song] for song in data['top_songs']], num_top_songs)
    genre_vector = pad_list([genre_to_index[genre] for genre in data['genres']], num_genres)
    return np.array(artist_vector + song_vector + genre_vector)

# Find similar users based on user data
# Find similar users based on user data
def find_similar_users(user_data, current_username):
    num_top_artists = 5
    num_top_songs = 5
    num_genres = 5

    artist_to_index, song_to_index, genre_to_index = create_mappings(users_data)
    
    user_vector = create_vector(user_data, artist_to_index, song_to_index, genre_to_index, num_top_artists, num_top_songs, num_genres)

    similarities = {}

    for username, data in users_data.items():
        if username == current_username:
            continue
        data_vector = create_vector(data, artist_to_index, song_to_index, genre_to_index, num_top_artists, num_top_songs, num_genres)
        
        # Calculate similarity as dot product
        similarity = np.dot(user_vector, data_vector) / (np.linalg.norm(user_vector) * np.linalg.norm(data_vector))
        similarities[username] = similarity
    
    sorted_users = sorted(similarities.items(), key=lambda x: x[1], reverse=True)
    return [(user, sim * 100) for user, sim in sorted_users if sim > 0.5][:5]


if __name__ == '__main__':
    app.run(debug=True)
