import psycopg2

def get_db_connection():
    connection = psycopg2.connect(
        host="localhost",
        database="referral_system",
        user="postgres",
        password="postgres"
    )
    return connection
