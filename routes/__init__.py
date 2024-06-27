from flask import Blueprint

user_routes = Blueprint('user_routes', __name__)
playlist_routes = Blueprint('playlist_routes', __name__)
recommendation_routes = Blueprint('recommendation_routes', __name__)
group_routes = Blueprint('group_routes', __name__)

from . import user_routes, playlist_routes, recommendation_routes, group_routes
