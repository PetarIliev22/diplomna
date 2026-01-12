from flask import Flask, render_template, jsonify, Response
from flask_cors import CORS
from threading import Event
import time
import json

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)
plate_event = Event()
latest_plate = {"text": "-", "valid": False}

def update_plate(text, valid):
    global latest_plate
    latest_plate = {"text": text, "valid": valid}
    print(f"Updated plate: {latest_plate}")
    plate_event.set()
    
@app.route("/")
def index():
    return render_template("display.html")

@app.route("/plate")
def plate():
    return jsonify(latest_plate)

@app.route("/plate/stream")
def plate_stream():
    def event_stream():
        last_sent = {"text": None, "valid": None}
        while True:
            plate_event.wait()
            if latest_plate != last_sent:
                data = json.dumps(latest_plate)
                yield f"data: {data}\n\n"
                last_sent = latest_plate.copy()
            time.sleep(0.1) 
            plate_event.clear()
    return Response(event_stream(), mimetype="text/event-stream")

def run_flask():
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
