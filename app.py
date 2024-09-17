from flask import Flask, request, jsonify
from referral_service import track_referral
from database import get_db_connection

app = Flask(__name__)


@app.route("/share_link", methods=["GET"])
def share_link():
    referrer_id = request.args.get("referrer_id")
    referral_link = f"https://google.com?referrer_id={referrer_id}"
    return jsonify({"code": 200, "status": True, "Referral link": referral_link})


@app.route("/track_referral", methods=["GET"])
def track_referral_endpoint():
    referrer_id = request.args.get("referrer_id")
    referred_user_id = request.args.get("referred_user_id")
    message = track_referral(referrer_id, referred_user_id)
    return jsonify({"code": 200, "status": True, "message": message})


@app.route("/user_points", methods=["GET"])
def user_points():
    user_id = request.args.get("user_id")
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT points FROM user_points WHERE user_id = %s;
    """,
        (user_id,),
    )
    user = cursor.fetchone()

    cursor.close()
    connection.close()

    if user:
        return (
            jsonify(
                {
                    "code": 200,
                    "status": True,
                    "data": {"user_id": user_id, "points": user[0]},
                }
            ),
            200,
        )
    return jsonify({"code": 404, "status": False, "message": "User not found."}), 404


if __name__ == "__main__":
    app.run(debug=True)
