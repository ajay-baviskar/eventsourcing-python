import psycopg2
from datetime import datetime
import json  # For storing events


class LeadRepository:
    def __init__(self, db_config):
        self.conn = psycopg2.connect(**db_config)
        self.create_tables()

    def create_tables(self):
        with self.conn.cursor() as cursor:
            # Creating projects table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP
                )
                """
            )

            # Creating user_register table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS user_register (
                    id SERIAL PRIMARY KEY,
                    project_id INTEGER,
                    mobile VARCHAR,
                    user_id INTEGER,
                    role VARCHAR,
                    lead_count INTEGER DEFAULT 0,
                    points INTEGER DEFAULT 0,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id)
                )
                """
            )

            # Creating token_programs table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS token_programs (
                    id SERIAL PRIMARY KEY,
                    project_id INTEGER,
                    name VARCHAR,
                    type VARCHAR,
                    is_created VARCHAR,
                    created_at TIMESTAMP,
                    updated_at TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id)
                )
                """
            )

            # Creating event_data table
            cursor.execute(
                """
    CREATE TABLE IF NOT EXISTS event_data (
        id SERIAL PRIMARY KEY,
        user_id INTEGER,  -- Assuming user_id refers to an existing users table
        project_id INTEGER,
        token_program_id INTEGER,  -- Added token_program_id definition
        event_name VARCHAR,
        count INTEGER,
        type VARCHAR,
        points INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- Automatically set to current time if not provided
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- Automatically set to current time if not provided
        FOREIGN KEY (project_id) REFERENCES projects(id),
        FOREIGN KEY (token_program_id) REFERENCES token_programs(id)
    )
    """
            )

            # Creating leads table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS leads (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR NOT NULL,
                    lead_id VARCHAR NOT NULL,
                    created_at TIMESTAMP NOT NULL
                )
                """
            )

            # Creating user_points table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS user_points (
                    user_id VARCHAR PRIMARY KEY,
                    points INTEGER NOT NULL DEFAULT 0,
                    lead_count INTEGER NOT NULL DEFAULT 0
                )
                """
            )

            # Creating events_log table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS events_log (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR NOT NULL,
                    event_type VARCHAR NOT NULL,
                    lead_id VARCHAR,
                    points INTEGER,
                    created_at TIMESTAMP NOT NULL
                )
                """
            )

            # Creating generic_events table
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS generic_events (
                    id SERIAL PRIMARY KEY,
                    user_id VARCHAR NOT NULL,
                    event_data JSON NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW()
                )
                """
            )
        self.conn.commit()

    def save_event(self, user_id: str, event_data: dict):
        with self.conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO generic_events (user_id, event_data, created_at)
                VALUES (%s, %s, NOW())
                """,
                (user_id, json.dumps(event_data)),  # Convert dict to JSON
            )
        self.conn.commit()

    def update_points_and_lead_count(self, user_id: str, points: int, lead_count: int):
        with self.conn.cursor() as cursor:
            cursor.execute(
                """
            INSERT INTO user_points (user_id, points, lead_count)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id) DO UPDATE 
            SET points = user_points.points + EXCLUDED.points,
                lead_count = user_points.lead_count + EXCLUDED.lead_count
            """,
                (user_id, points, lead_count),
            )

        self.conn.commit()

    def log_event(
        self,
        project_id: int,
        token_program_id: int,
        event_name: str,
        count: int,
        event_type: str,
        points: int,
    ):
        with self.conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO event_data (project_id, token_program_id, event_name, count, type, points, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
            """,
                (project_id, token_program_id, event_name, count, event_type, points),
            )
            self.conn.commit()

    def register_user(self, project_id, mobile, user_id, role):
        with self.conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO user_register (project_id, mobile, user_id, role, created_at, updated_at)
                VALUES (%s, %s, %s, %s, NOW(), NOW())
                """,
                (project_id, mobile, user_id, role),
            )
        self.conn.commit()

    def create_project(self, name):
        with self.conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO projects (name, created_at, updated_at)
                VALUES (%s, NOW(), NOW())
                """,
                (name,),
            )
        self.conn.commit()

    def create_token_program(self, project_id, name, type, is_created):
        with self.conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO token_programs (project_id, name, type, is_created, created_at, updated_at)
                VALUES (%s, %s, %s, %s, NOW(), NOW())
                """,
                (project_id, name, type, is_created),
            )
        self.conn.commit()

    def get_project_events(self, project_id):
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM generic_events WHERE user_id = %s", (project_id,)
            )
            events = cursor.fetchall()
        return events

    def get_users_by_project(self, project_id):
        with self.conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM user_register WHERE project_id = %s", (project_id,)
            )
            users = cursor.fetchall()
        return users
