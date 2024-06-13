from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, jsonify, render_template, redirect, url_for, session
import requests
import tensorflow as tf
import numpy as np
import os
import json
from collections import defaultdict, Counter

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
                if isinstance(data, list):
                    for user in data:
                        users_data[user['username']] = user
                elif isinstance(data, dict):
                    users_data[data['username']] = data
    return users_data

users_data = load_user_data()

# In-memory store for following relationships and messages
following = {}
messages = {}

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

    headers = {
        'Authorization': f"Bearer {auth_response['access_token']}"
    }

    user_profile = requests.get('https://api.spotify.com/v1/me', headers=headers).json()
    session['user_id'] = user_profile['id']

    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    token_info = session.get('token_info')
    if not token_info:
        return redirect(url_for('index'))

    headers = {
        'Authorization': f"Bearer {token_info['access_token']}"
    }

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

    if username in similarities:
        similar_users = similarities[username]
    else:
        similar_users = find_similar_users(user_data, username, artist_to_index, song_to_index, genre_to_index)
        update_similarities(username, similar_users)

    return render_template('dashboard.html', user_data=user_data, similar_users=similar_users, enumerate=enumerate)

@app.route('/top_artists')
def top_artists():
    current_user = session.get('user_id')
    if not current_user:
        return redirect(url_for('index'))

    token_info = session.get('token_info')
    if not token_info:
        return redirect(url_for('index'))

    headers = {
        'Authorization': f"Bearer {token_info['access_token']}"
    }

    top_artists = requests.get('https://api.spotify.com/v1/me/top/artists', headers=headers).json()
    
    return render_template('top_artists.html', top_artists=top_artists)


@app.route('/follow/<username>')
def follow_user(username):
    current_user = session.get('user_id')
    if not current_user:
        return redirect(url_for('index'))

    if username not in users_data or username == current_user:
        return "User not found or invalid operation", 404

    if current_user not in following:
        following[current_user] = set()

    following[current_user].add(username)
    return redirect(url_for('user_stats', username=username))

@app.route('/unfollow/<username>')
def unfollow_user(username):
    current_user = session.get('user_id')
    if not current_user:
        return redirect(url_for('index'))

    if username not in users_data or username == current_user:
        return "User not found or invalid operation", 404

    if current_user in following and username in following[current_user]:
        following[current_user].remove(username)
    return redirect(url_for('user_stats', username=username))

@app.route('/messages')
def view_messages():
    current_user = session.get('user_id')
    if not current_user:
        return redirect(url_for('index'))

    user_messages = messages.get(current_user, [])
    return render_template('messages.html', messages=user_messages)

@app.route('/message/<username>', methods=['GET', 'POST'])
def send_message(username):
    current_user = session.get('user_id')
    if not current_user:
        return redirect(url_for('index'))

    if request.method == 'POST':
        message_content = request.form['message']
        if username not in messages:
            messages[username] = []
        messages[username].append({'from': current_user, 'content': message_content})
        return redirect(url_for('user_stats', username=username))
    return render_template('send_message.html', recipient=username)

@app.route('/user/<username>')
def user_stats(username):
    current_user = session.get('user_id')
    if not current_user:
        return redirect(url_for('index'))

    if username not in users_data:
        return "User not found", 404

    user_data = users_data[username]
    is_following = username in following.get(current_user, set())
    return render_template('user_stats.html', user_data=user_data, is_following=is_following)

def build_similarity_model(input_dim):
    model = tf.keras.Sequential([
        tf.keras.layers.Dense(128, activation='relu', input_shape=(input_dim,)),
        tf.keras.layers.Dense(64, activation='relu'),
        tf.keras.layers.Dense(1, activation='sigmoid')  # Output a similarity score between 0 and 1
    ])
    model.compile(optimizer='adam', loss='binary_crossentropy', metrics=['accuracy'])
    return model

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

def create_vector(data, artist_to_index, song_to_index, genre_to_index):
    artist_vector = np.zeros(len(artist_to_index))
    song_vector = np.zeros(len(song_to_index))
    genre_vector = np.zeros(len(genre_to_index))

    for artist in data['top_artists']:
        if artist in artist_to_index:
            artist_vector[artist_to_index[artist]] = 1
    
    for song in data['top_songs']:
        if song in song_to_index:
            song_vector[song_to_index[song]] = 1

    for genre in data['genres']:
        if genre in genre_to_index:
            genre_vector[genre_to_index[genre]] = 1

    return np.concatenate([artist_vector, song_vector, genre_vector])

def train_similarity_model(users_data, artist_to_index, song_to_index, genre_to_index):
    user_vectors = []
    labels = []

    usernames = list(users_data.keys())
    for i in range(len(usernames)):
        for j in range(i + 1, len(usernames)):
            user_vector_i = create_vector(users_data[usernames[i]], artist_to_index, song_to_index, genre_to_index)
            user_vector_j = create_vector(users_data[usernames[j]], artist_to_index, song_to_index, genre_to_index)
            combined_vector = np.abs(user_vector_i - user_vector_j)
            user_vectors.append(combined_vector)
            labels.append(1 if combined_vector.sum() == 0 else 0)  # Simple label assignment for similar and different users

    user_vectors = np.array(user_vectors)
    labels = np.array(labels)

    model = build_similarity_model(user_vectors.shape[1])
    model.fit(user_vectors, labels, epochs=10, batch_size=32)  # Adjust epochs and batch_size as needed

    return model
from sklearn.metrics.pairwise import cosine_similarity

def calculate_similarity(vector1, vector2):
    return cosine_similarity([vector1], [vector2])[0][0]

def find_similar_users(user_data, current_username, artist_to_index, song_to_index, genre_to_index):
    user_vector = create_vector(user_data, artist_to_index, song_to_index, genre_to_index)
    similarities = {}

    for username, data in users_data.items():
        if username == current_username:
            continue
        data_vector = create_vector(data, artist_to_index, song_to_index, genre_to_index)
        similarity = calculate_similarity(user_vector, data_vector)
        similarities[username] = similarity

    sorted_users = sorted(similarities.items(), key=lambda x: x[1], reverse=True)
    return [(user, sim * 100) for user, sim in sorted_users][:10]

import pickle

def save_similarities(similarities, filename='similarities.pkl'):
    with open(filename, 'wb') as f:
        pickle.dump(similarities, f)

def load_similarities(filename='similarities.pkl'):
    if os.path.exists(filename):
        with open(filename, 'rb') as f:
            return pickle.load(f)
    return {}

similarities = load_similarities()

def update_similarities(username, similar_users):
    similarities[username] = similar_users
    save_similarities(similarities)

# Add this global flag
model_loaded = False

@app.before_request
def load_model():
    global artist_to_index, song_to_index, genre_to_index, model, model_loaded
    if not model_loaded:
        artist_to_index, song_to_index, genre_to_index = create_mappings(users_data)
        model = train_similarity_model(users_data, artist_to_index, song_to_index, genre_to_index)
        model_loaded = True

# In-memory store for comments
comments = defaultdict(lambda: defaultdict(list))  # {username: {entity_id: [comments]}}

@app.route('/comment/<entity_type>/<entity_id>', methods=['GET', 'POST'])
def comment(entity_type, entity_id):
    current_user = session.get('user_id')
    if not current_user:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        comment_content = request.form['comment']
        comments[current_user][entity_id].append({
            'from': current_user,
            'content': comment_content,
            'entity_type': entity_type
        })
        return redirect(url_for('view_entity', entity_type=entity_type, entity_id=entity_id))
    
    return render_template('comment.html', entity_type=entity_type, entity_id=entity_id)

@app.route('/view_entity/<entity_type>/<entity_id>')
def view_entity(entity_type, entity_id):
    current_user = session.get('user_id')
    if not current_user:
        return redirect(url_for('index'))
    
    entity_comments = []
    for user, entities in comments.items():
        entity_comments.extend(entities.get(entity_id, []))
    
    return render_template('view_entity.html', entity_type=entity_type, entity_id=entity_id, comments=entity_comments)

# In-memory store for likes
likes = defaultdict(lambda: defaultdict(int))  # {entity_id: {username: count}}

@app.route('/like/<entity_type>/<entity_id>')
def like(entity_type, entity_id):
    current_user = session.get('user_id')
    if not current_user:
        return redirect(url_for('index'))

    likes[entity_id][current_user] += 1
    return redirect(url_for('view_entity', entity_type=entity_type, entity_id=entity_id))

# In-memory store for ratings
ratings = defaultdict(lambda: defaultdict(list))  # {entity_id: {username: [ratings]}}

@app.route('/rate/<entity_type>/<entity_id>', methods=['GET', 'POST'])
def rate(entity_type, entity_id):
    current_user = session.get('user_id')
    if not current_user:
        return redirect(url_for('index'))

    if request.method == 'POST':
        rating = int(request.form['rating'])
        if 1 <= rating <= 5:
            ratings[entity_id][current_user].append(rating)
        return redirect(url_for('view_entity', entity_type=entity_type, entity_id=entity_id))
    
    return render_template('rate.html', entity_type=entity_type, entity_id=entity_id)

if __name__ == '__main__':
    app.run(debug=True)
