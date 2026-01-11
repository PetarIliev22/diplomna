from flask import Flask, render_template, jsonify
from flask_cors import CORS
from threading import Thread

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)

latest_plate = {"text": "-", "valid": False}

def update_plate(text, valid):
    latest_plate["text"] = text
    latest_plate["valid"] = valid

@app.route("/")
def index():
    return render_template("display.html")

@app.route("/plate")
def plate():
    return jsonify(latest_plate)

def run_flask():
    app.run(host="0.0.0.0", port=5000, debug=False)
