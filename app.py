from flask import Flask, request, jsonify
from datetime import datetime
from aggregates import User
from repository import LeadRepository

app = Flask(__name__)

# Database configuration
db_config = {
    'dbname': 'ev_test_1',
    'user': 'postgres',
    'password': 'postgres',
    'host': 'localhost',
    'port': '5432'
}

repository = LeadRepository(db_config)
users = {}

# Existing Lead Creation and Points APIs

@app.route('/create_lead', methods=['POST'])
def create_lead():
    user_id = request.json['user_id']
    lead_id = request.json['lead_id']

    if user_id not in users:
        users[user_id] = User(user_id, repository)

    user = users[user_id]
    user.create_lead(lead_id)

    return jsonify({"message": "Lead created", "user_id": user_id}), 201

@app.route('/points/<user_id>', methods=['GET'])
def get_user_points(user_id):
    with repository.conn.cursor() as cursor:
        cursor.execute('SELECT points FROM user_points WHERE user_id = %s', (user_id,))
        result = cursor.fetchone()
        points = result[0] if result else 0
    return jsonify({"user_id": user_id, "points": points}), 200

@app.route('/events/<user_id>', methods=['GET'])
def get_user_events(user_id):
    events = repository.get_project_events(user_id)
    events_list = [
        {
            "id": event[0],
            "user_id": event[1],
            "event_data": event[2],
            "created_at": event[3]
        } for event in events
    ]
    return jsonify({"user_id": user_id, "events": events_list}), 200

# New APIs for user_register, projects, token_programs

@app.route('/register_user', methods=['POST'])
def register_user():
    data = request.json
    project_id = data['project_id']
    mobile = data['mobile']
    user_id = data['user_id']
    role = data['role']
    repository.register_user(project_id, mobile, user_id, role)
    return jsonify({"message": "User registered successfully"}), 201

@app.route('/create_project', methods=['POST'])
def create_project():
    data = request.json
    project_name = data['name']
    repository.create_project(project_name)
    return jsonify({"message": "Project created successfully"}), 201

@app.route('/create_token_program', methods=['POST'])
def create_token_program():
    data = request.json
    project_id = data['project_id']
    name = data['name']
    token_type = data['type']
    is_created = data['is_created']
    repository.create_token_program(project_id, name, token_type, is_created)
    return jsonify({"message": "Token program created successfully"}), 201

@app.route('/insert_event_data', methods=['POST'])
def insert_event_data():
    data = request.json
    try:
        project_id = data['project_id']
        token_program_id = data['token_program_id']
        event_name = data['event_name']
        count = data['count']
        event_type = data['type']
        points = data['points']

        # Call the repository method to insert event data
        repository.log_event(project_id, token_program_id, event_name, count, event_type, points)

        return jsonify({"message": "Event data inserted successfully"}), 201
    except KeyError as e:
        return jsonify({"error": f"Missing key: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
