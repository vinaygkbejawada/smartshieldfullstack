from flask import Flask, render_template, request
import pickle
import sqlite3

app = Flask(__name__)

# 🔥 Load trained ML model
with open("spam_model.pkl", "rb") as f:
    model = pickle.load(f)


# 🔥 Initialize SQLite Database
def init_db():
    conn = sqlite3.connect("threat_data.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT UNIQUE,
            count INTEGER
        )
    """)
    conn.commit()
    conn.close()

init_db()


@app.route("/")
def landing():
    return render_template("landing.html")


@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():

    original_message = ""

    result = {
        "spam_prob": 10,
        "phishing_risk": "SAFE",
        "keyword_count": 0,
        "url_risk": "NONE",
        "final_score": 15,
        "risk_level": "SAFE",
        "recommendation": "✅ System Ready. Enter a message to analyze.",
        "threat_info": ""
    }

    if request.method == "POST":
        original_message = request.form["message"]
        message = original_message.lower()

        # 🔥 1️⃣ ML Prediction
        probability = model.predict_proba([message])[0][1]
        final_score = int(probability * 100)

        # 🔥 2️⃣ Phishing Keyword Boost
        phishing_keywords = [
            "bank", "account", "verify", "login",
            "password", "urgent", "suspended",
            "update", "click", "confirm"
        ]

        keyword_count = sum(word in message for word in phishing_keywords)
        final_score += keyword_count * 5

        # 🔥 3️⃣ URL Detection Boost
        if "http" in message or "www" in message:
            final_score += 10
            url_risk = "HIGH"
        else:
            url_risk = "LOW"

        # Cap score
        if final_score > 100:
            final_score = 100

        # 🔥 4️⃣ Risk Classification
        if final_score < 30:
            risk_level = "SAFE"
            recommendation = "✅ This message appears safe to open."
        elif final_score < 55:
            risk_level = "MEDIUM"
            recommendation = "⚠️ Be cautious before clicking links."
        elif final_score < 75:
            risk_level = "HIGH"
            recommendation = "❗ Suspicious content detected. Avoid interacting."
        else:
            risk_level = "CRITICAL"
            recommendation = "🚨 Dangerous message detected! Block sender immediately."

        # 🔥 5️⃣ SQLite Threat Intelligence
        conn = sqlite3.connect("threat_data.db")
        cursor = conn.cursor()

        cursor.execute("SELECT count FROM messages WHERE content = ?", (message,))
        row = cursor.fetchone()

        if row:
            threat_count = row[0] + 1
            cursor.execute(
                "UPDATE messages SET count = ? WHERE content = ?",
                (threat_count, message)
            )
        else:
            threat_count = 1
            cursor.execute(
                "INSERT INTO messages (content, count) VALUES (?, ?)",
                (message, threat_count)
            )

        conn.commit()
        conn.close()

        # Threat Intelligence Message
        if threat_count > 1:
            threat_info = (
                f"⚠ This message has already been encountered by {threat_count} users. "
                f"Repeated occurrences indicate potential coordinated spam activity."
            )
        else:
            threat_info = "🟢 This message has not been previously reported."

        result = {
            "spam_prob": final_score,
            "phishing_risk": risk_level,
            "keyword_count": keyword_count,
            "url_risk": url_risk,
            "final_score": final_score,
            "risk_level": risk_level,
            "recommendation": recommendation,
            "threat_info": threat_info
        }

    # 🔥 REAL-TIME PLATFORM ANALYTICS (ALWAYS RUN)
    conn = sqlite3.connect("threat_data.db")
    cursor = conn.cursor()

    # Total unique messages analyzed
    cursor.execute("SELECT SUM(count) FROM messages")
    total_messages = cursor.fetchone()[0]
    if total_messages is None:
        total_messages = 0

    # Repeated threats (messages that appeared more than once)
    cursor.execute("SELECT COUNT(*) FROM messages WHERE count > 1")
    repeated_threats = cursor.fetchone()[0]

    # High risk alerts (we approximate using repeated threats + high classification)
    cursor.execute("SELECT COUNT(*) FROM messages")
    high_risk_alerts = cursor.fetchone()[0]

    conn.close()

    return render_template(
        "index.html",
        result=result,
        message=original_message,
        total_messages=total_messages,
        repeated_threats=repeated_threats,
        high_risk_alerts=high_risk_alerts
    )


import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)