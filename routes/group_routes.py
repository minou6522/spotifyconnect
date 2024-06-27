#Manages groups, allowing users to join, leave, and share recommendations within groups.

from flask import Blueprint, request, jsonify, session, redirect, url_for, render_template
from collections import defaultdict

group_routes = Blueprint('group_routes', __name__)

# In-memory store for group data
groups = defaultdict(dict)  # {group_name: {members: set(), recommendations: list()}}

@group_routes.route('/')
def view_groups():
    current_user = session.get('user_id')
    if not current_user:
        return redirect(url_for('index'))

    user_groups = [group_name for group_name, data in groups.items() if current_user in data['members']]
    return render_template('groups.html', groups=user_groups)

@group_routes.route('/create', methods=['GET', 'POST'])
def create_group():
    current_user = session.get('user_id')
    if not current_user:
        return redirect(url_for('index'))

    if request.method == 'POST':
        group_name = request.form['group_name']
        if group_name in groups:
            return "Group already exists", 400
        groups[group_name] = {'members': {current_user}, 'recommendations': []}
        return redirect(url_for('group_routes.view_groups'))

    return render_template('create_group.html')

@group_routes.route('/<group_name>/join')
def join_group(group_name):
    current_user = session.get('user_id')
    if not current_user:
        return redirect(url_for('index'))

    if group_name not in groups:
        return "Group not found", 404

    groups[group_name]['members'].add(current_user)
    return redirect(url_for('group_routes.view_groups'))

@group_routes.route('/<group_name>/leave')
def leave_group(group_name):
    current_user = session.get('user_id')
    if not current_user:
        return redirect(url_for('index'))

    if group_name not in groups or current_user not in groups[group_name]['members']:
        return "Group not found or not a member", 404

    groups[group_name]['members'].remove(current_user)
    return redirect(url_for('group_routes.view_groups'))

@group_routes.route('/<group_name>/recommend', methods=['GET', 'POST'])
def recommend_to_group(group_name):
    current_user = session.get('user_id')
    if not current_user:
        return redirect(url_for('index'))

    if group_name not in groups or current_user not in groups[group_name]['members']:
        return "Group not found or not a member", 404

    if request.method == 'POST':
        recommendation = request.form['recommendation']
        groups[group_name]['recommendations'].append({'from': current_user, 'content': recommendation})
        return redirect(url_for('group_routes.view_group_recommendations', group_name=group_name))

    return render_template('recommend_to_group.html', group_name=group_name)

@group_routes.route('/<group_name>/recommendations')
def view_group_recommendations(group_name):
    current_user = session.get('user_id')
    if not current_user:
        return redirect(url_for('index'))

    if group_name not in groups or current_user not in groups[group_name]['members']:
        return "Group not found or not a member", 404

    group_recommendations = groups[group_name]['recommendations']
    return render_template('group_recommendations.html', group_name=group_name, recommendations=group_recommendations)
