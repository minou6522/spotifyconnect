from flask import Blueprint, request, jsonify, session, redirect, url_for, render_template
import os
import requests
from collections import defaultdict
import json

user_routes = Blueprint('user_routes', __name__)
users_data = {}

# Load user data from JSON files
def load_user_data():
    global users_data
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

load_user_data()

# In-memory store for following relationships and messages
following = defaultdict(set)
messages = defaultdict(list)

@user_routes.route('/<username>')
def user_stats(username):
    current_user = session.get('user_id')
    if not current_user:
        return redirect(url_for('index'))

    if username not in users_data:
        return "User not found", 404

    user_data = users_data[username]
    is_following = username in following[current_user]
    return render_template('user_stats.html', user_data=user_data, is_following=is_following)

@user_routes.route('/follow/<username>')
def follow_user(username):
    current_user = session.get('user_id')
    if not current_user:
        return redirect(url_for('index'))

    if username not in users_data or username == current_user:
        return "User not found or invalid operation", 404

    following[current_user].add(username)
    return redirect(url_for('user_routes.user_stats', username=username))

@user_routes.route('/unfollow/<username>')
def unfollow_user(username):
    current_user = session.get('user_id')
    if not current_user:
        return redirect(url_for('index'))

    if username not in users_data or username == current_user:
        return "User not found or invalid operation", 404

    if username in following[current_user]:
        following[current_user].remove(username)
    return redirect(url_for('user_routes.user_stats', username=username))

@user_routes.route('/messages')
def view_messages():
    current_user = session.get('user_id')
    if not current_user:
        return redirect(url_for('index'))

    user_messages = messages.get(current_user, [])
    return render_template('messages.html', messages=user_messages)

@user_routes.route('/message/<username>', methods=['GET', 'POST'])
def send_message(username):
    current_user = session.get('user_id')
    if not current_user:
        return redirect(url_for('index'))

    if request.method == 'POST':
        message_content = request.form['message']
        messages[username].append({'from': current_user, 'content': message_content})
        return redirect(url_for('user_routes.user_stats', username=username))
    return render_template('send_message.html', recipient=username)

@user_routes.route('/comment/<entity_type>/<entity_id>', methods=['GET', 'POST'])
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

@user_routes.route('/view_entity/<entity_type>/<entity_id>')
def view_entity(entity_type, entity_id):
    current_user = session.get('user_id')
    if not current_user:
        return redirect(url_for('index'))
    
    entity_comments = []
    for user, entities in comments.items():
        entity_comments.extend(entities.get(entity_id, []))
    
    return render_template('view_entity.html', entity_type=entity_type, entity_id=entity_id, comments=entity_comments)

@user_routes.route('/like/<entity_type>/<entity_id>')
def like(entity_type, entity_id):
    current_user = session.get('user_id')
    if not current_user:
        return redirect(url_for('index'))

    likes[entity_id][current_user] += 1
    return redirect(url_for('user_routes.view_entity', entity_type=entity_type, entity_id=entity_id))

@user_routes.route('/rate/<entity_type>/<entity_id>', methods=['GET', 'POST'])
def rate(entity_type, entity_id):
    current_user = session.get('user_id')
    if not current_user:
        return redirect(url_for('index'))

    if request.method == 'POST':
        rating = int(request.form['rating'])
        if 1 <= rating <= 5:
            ratings[entity_id][current_user].append(rating)
        return redirect(url_for('user_routes.view_entity', entity_type=entity_type, entity_id=entity_id))
    
    return render_template('rate.html', entity_type=entity_type, entity_id=entity_id)
