import os
import json
from collections import defaultdict, Counter

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

# Dictionary to count artist popularity and store users who listen to each artist
artist_user_map = defaultdict(list)

for username, user_data in users_data.items():
    for artist in user_data.get('top_artists', []):
        artist_user_map[artist].append(username)

# Rank artists by their popularity
artist_counts = Counter({artist: len(users) for artist, users in artist_user_map.items()})
top_artists = artist_counts.most_common(5)

# Output the top 5 artists and their top 5 listeners
result = []
for artist, count in top_artists:
    top_users = artist_user_map[artist][:5]  # Get top 5 users for this artist
    result.append({
        'artist': artist,
        'count': count,
        'top_users': top_users
    })

# Print the result
for entry in result:
    print(f"Artist: {entry['artist']} (Listened by {entry['count']} users)")
    for i, user in enumerate(entry['top_users'], start=1):
        print(f"  {i}. {user}")
