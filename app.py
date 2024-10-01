# app.py
from flask import Flask, request, jsonify
from datetime import datetime
from aggregates import User
from repository import LeadRepository
from events import LeadCreatedEvent

app = Flask(__name__)

# Database configuration
db_config = {
    'dbname': 'event_points_test',
    'user': 'postgres',
    'password': 'postgres',
    'host': 'localhost',
    'port': '5432'
}

repository = LeadRepository(db_config)
users = {}

@app.route('/create_lead', methods=['POST'])
def create_lead():
    user_id = request.json['user_id']
    lead_id = request.json['lead_id']

    if user_id not in users:
        users[user_id] = User(user_id, repository)

    user = users[user_id]
    user.create_lead(lead_id)

    # Create and save the event
    event = LeadCreatedEvent(user_id=user_id, lead_id=lead_id, created_at=datetime.now())
    repository.save_event(event)

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
    with repository.conn.cursor() as cursor:
        cursor.execute('SELECT * FROM events_log WHERE user_id = %s', (user_id,))
        events = cursor.fetchall()
        events_list = [
            {
                "id": event[0],
                "event_type": event[2],
                "lead_id": event[3],
                "points": event[4],
                "created_at": event[5]
            } for event in events
        ]
    return jsonify({"user_id": user_id, "events": events_list}), 200

if __name__ == '__main__':
    app.run(debug=True)
