from flask import Flask, request, jsonify, render_template
import tensorflow as tf
import numpy as np

app = Flask(__name__)

users_data = {
    'user1': [1, 2, 3, 4, 5],
    'user2': [2, 3, 4, 5, 6],
    'user3': [5, 4, 3, 2, 1],
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/authenticate', methods=['POST'])
def authenticate():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if username in users_data:
        return jsonify(success=True)
    else:
        return jsonify(success=False), 401

@app.route('/recommendations', methods=['POST'])
def recommendations():
    data = request.json
    user_data = users_data.get(data.get('username'))
    
    if not user_data:
        return jsonify(error="User data not found"), 404

    model = build_model()
    recommendations = model.predict(np.array([user_data]))
    
    similar_users = find_similar_users(user_data)
    
    return jsonify(recommendations=similar_users)

def build_model():
    model = tf.keras.Sequential([
        tf.keras.layers.Dense(64, activation='relu', input_shape=(5,)),
        tf.keras.layers.Dense(64, activation='relu'),
        tf.keras.layers.Dense(5, activation='softmax')
    ])
    
    model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])
    return model

def find_similar_users(user_data):
    similarities = {}
    for username, data in users_data.items():
        similarity = np.dot(user_data, data) / (np.linalg.norm(user_data) * np.linalg.norm(data))
        similarities[username] = similarity
    
    sorted_users = sorted(similarities.items(), key=lambda x: x[1], reverse=True)
    return [user for user, sim in sorted_users if sim > 0.5]

if __name__ == '__main__':
    app.run(debug=True)
