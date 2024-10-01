# repository.py
import psycopg2
from datetime import datetime
from events import LeadCreatedEvent

class LeadRepository:
    def __init__(self, db_config):
        self.conn = psycopg2.connect(**db_config)
        self.create_tables()

    def create_tables(self):
        with self.conn.cursor() as cursor:
            # Create leads table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS leads (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR NOT NULL,
                    lead_id VARCHAR NOT NULL,
                    created_at TIMESTAMP NOT NULL
                )
            ''')
            # Create user_points table with lead_count
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_points (
                    user_id VARCHAR PRIMARY KEY,
                    points INTEGER NOT NULL DEFAULT 0,
                    lead_count INTEGER NOT NULL DEFAULT 0
                )
            ''')
            # Create events_log table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS events_log (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR NOT NULL,
                    event_type VARCHAR NOT NULL,
                    lead_id VARCHAR,
                    points INTEGER,
                    created_at TIMESTAMP NOT NULL
                )
            ''')
            self.conn.commit()

    def save_event(self, event: LeadCreatedEvent):
        with self.conn.cursor() as cursor:
            cursor.execute('''
                INSERT INTO leads (user_id, lead_id, created_at)
                VALUES (%s, %s, %s)
            ''', (event.user_id, event.lead_id, event.created_at))
            self.conn.commit()

    def update_points_and_lead_count(self, user_id: str, points: int, lead_count: int):
        with self.conn.cursor() as cursor:
            # Update points and lead count or insert new entry if user_id doesn't exist
            cursor.execute('''
                INSERT INTO user_points (user_id, points, lead_count)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id) DO UPDATE 
                SET points = user_points.points + EXCLUDED.points,
                    lead_count = user_points.lead_count + EXCLUDED.lead_count
            ''', (user_id, points, lead_count))
            self.conn.commit()

    def log_event(self, user_id: str, event_type: str, lead_id: str = None, points: int = None):
        with self.conn.cursor() as cursor:
            cursor.execute('''
                INSERT INTO events_log (user_id, event_type, lead_id, points, created_at)
                VALUES (%s, %s, %s, %s, %s)
            ''', (user_id, event_type, lead_id, points, datetime.now()))
            self.conn.commit()
