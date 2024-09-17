def create_tables():
    connection = get_db_connection()
    cursor = connection.cursor()

    # Referrals table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS referrals (
        id SERIAL PRIMARY KEY,
        referrer_id INT NOT NULL,
        referred_user_id INT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # User points table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_points (
        user_id INT PRIMARY KEY,
        points INT DEFAULT 0
    );
    """)

    connection.commit()
    cursor.close()
