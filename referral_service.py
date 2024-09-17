from database import get_db_connection

def track_referral(referrer_id, referred_user_id):
    connection = get_db_connection()
    cursor = connection.cursor()

    # Check if this referral already exists
    cursor.execute("""
        SELECT * FROM referrals WHERE referrer_id = %s AND referred_user_id = %s;
    """, (referrer_id, referred_user_id))
    existing_referral = cursor.fetchone()

    if not existing_referral:
        # Insert a new referral record
        cursor.execute("""
            INSERT INTO referrals (referrer_id, referred_user_id)
            VALUES (%s, %s);
        """, (referrer_id, referred_user_id))
        connection.commit()

        # Count the number of referrals made by this referrer
        cursor.execute("""
            SELECT COUNT(*) FROM referrals WHERE referrer_id = %s;
        """, (referrer_id,))
        referral_count = cursor.fetchone()[0]

        if referral_count == 3:
            # Award points to the referrer for making 3 referrals
            cursor.execute("""
                SELECT points FROM user_points WHERE user_id = %s;
            """, (referrer_id,))
            user_points = cursor.fetchone()

            if user_points:
                # Update points
                new_points = user_points[0] + 50
                cursor.execute("""
                    UPDATE user_points SET points = %s WHERE user_id = %s;
                """, (new_points, referrer_id))
            else:
                # Insert new user with points if not exists
                cursor.execute("""
                    INSERT INTO user_points (user_id, points) VALUES (%s, %s);
                """, (referrer_id, 50))

            connection.commit()
            cursor.close()
            return f"50 points awarded to user {referrer_id} for 3 referrals!"
        cursor.close()
        return f"Referral tracked for user {referrer_id}. Current referral count: {referral_count}"

    cursor.close()
    return "Referral already exists."
